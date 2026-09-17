"""Tests for planted synthetic homophonic control keys and metrics."""

from __future__ import annotations

from collections import Counter
import json
import random
import string
import unittest


from experiments.homophonic.controls import (
    FAMILY_NAMES,
    cipher_words_to_json,
    decode_words,
    encrypt_words,
    key_to_json,
    recovery_metrics,
    seeded_control_key,
)


ALPHABET = tuple(string.ascii_lowercase)
FAMILIES = tuple(FAMILY_NAMES)


class SyntheticControlTests(unittest.TestCase):
    def test_32_fixed_seeds_create_valid_keys_for_each_family(self) -> None:
        expected_units = {
            "injective": 26,
            "cap2": 52,
            "unlimited": 52,
        }
        for family in FAMILIES:
            for seed in range(32):
                key = seeded_control_key(family, seed)
                self.assertEqual(key["family"], family)
                self.assertEqual(key["seed"], seed)
                self.assertEqual(tuple(key["alphabet"]), ALPHABET)
                self.assertEqual(len(key["units"]), expected_units[family])
                self.assertEqual(
                    set(key["units"]),
                    {f"c{index:02d}" for index in range(expected_units[family])},
                )
                self.assertEqual(set(key["cipher_to_plain"]), set(key["units"]))
                self.assertEqual(
                    set(key["cipher_to_plain"].values()), set(ALPHABET)
                )
                counts = Counter(key["cipher_to_plain"].values())
                if family == "injective":
                    self.assertEqual(set(counts.values()), {1})
                elif family == "cap2":
                    self.assertEqual(set(counts.values()), {2})
                else:
                    self.assertTrue(all(count >= 1 for count in counts.values()))
                    self.assertEqual(
                        set(
                            key["cipher_to_plain"][unit]
                            for unit in key["units"][:26]
                        ),
                        set(ALPHABET),
                    )

                cycles = key["emission_order"]
                self.assertEqual(set(cycles), set(ALPHABET))
                cycle_units = [unit for cycle in cycles.values() for unit in cycle]
                self.assertEqual(len(cycle_units), len(set(cycle_units)))
                self.assertEqual(set(cycle_units), set(key["units"]))
                for letter, cycle in cycles.items():
                    self.assertTrue(cycle)
                    self.assertTrue(
                        all(key["cipher_to_plain"][unit] == letter for unit in cycle)
                    )

    def test_seeded_keys_are_deterministic_and_do_not_change_global_random(self) -> None:
        for family in FAMILIES:
            first = seeded_control_key(family, 17)
            second = seeded_control_key(family, 17)
            self.assertEqual(first, second)

        random.seed(9123)
        before = random.getstate()
        seeded_control_key("cap2", 41)
        after = random.getstate()
        self.assertEqual(before, after)

    def test_multiple_units_are_exercised_by_cyclic_emission(self) -> None:
        for family in ("cap2", "unlimited"):
            for seed in range(32):
                key = seeded_control_key(family, seed)
                self.assertTrue(any(len(cycle) > 1 for cycle in key["emission_order"].values()))
        injective = seeded_control_key("injective", 0)
        self.assertTrue(all(len(cycle) == 1 for cycle in injective["emission_order"].values()))

    def test_encryption_resets_cycles_per_call_and_preserves_boundaries(self) -> None:
        key = seeded_control_key("cap2", 5)
        words = ["ababa", "c", "zzzz"]
        first = encrypt_words(words, key)
        second = encrypt_words(words, key)
        self.assertEqual(first, second)
        self.assertEqual(len(first), len(words))
        self.assertTrue(all(isinstance(unit_word, tuple) for unit_word in first))
        self.assertEqual(first[0], encrypt_words([words[0]], key)[0])
        self.assertEqual(
            encrypt_words(["a"], key)[0],
            encrypt_words(["a"], key)[0],
        )

    def test_known_roundtrip_and_atomic_json_records(self) -> None:
        key = seeded_control_key("unlimited", 8)
        words = ["abacus", "zoo"]
        cipher_words = encrypt_words(words, key)
        self.assertEqual(decode_words(cipher_words, key), words)

        serialized_key = key_to_json(key)
        loaded_key = json.loads(serialized_key)
        self.assertEqual(loaded_key["units"], list(key["units"]))
        self.assertEqual(encrypt_words(words, loaded_key), cipher_words)

        serialized_words = cipher_words_to_json(cipher_words)
        self.assertEqual(json.loads(serialized_words), [list(word) for word in cipher_words])

    def test_recovery_metrics_keep_absent_units_in_full_denominators(self) -> None:
        key = seeded_control_key("cap2", 12)
        plaintext_words = ["aa", "bbbb"]
        cipher_words = encrypt_words(plaintext_words, key)
        fit_units = {cipher_words[0][0]}
        recovered_key = {fit_units.copy().pop(): key["cipher_to_plain"][cipher_words[0][0]]}

        metrics = recovery_metrics(
            cipher_words,
            plaintext_words,
            recovered_key,
            fit_units,
        )
        self.assertEqual(metrics["full_char_total"], 6)
        self.assertEqual(metrics["observed_position_total"], 1)
        self.assertEqual(metrics["unobserved_position_count"], 5)
        self.assertEqual(metrics["full_char_correct"], 1)
        self.assertEqual(metrics["full_char_accuracy"], 1 / 6)
        self.assertEqual(metrics["observed_position_correct"], 1)
        self.assertEqual(metrics["observed_position_accuracy"], 1.0)
        self.assertEqual(metrics["full_token_total"], 2)
        self.assertEqual(metrics["full_token_correct"], 0)
        self.assertEqual(metrics["fully_observed_token_total"], 0)

        no_fit = recovery_metrics(cipher_words, plaintext_words, {}, set())
        self.assertEqual(no_fit["full_char_correct"], 0)
        self.assertEqual(no_fit["full_char_total"], 6)
        self.assertIsNone(no_fit["observed_position_accuracy"])
        self.assertEqual(no_fit["fully_observed_token_total"], 0)

    def test_fully_observed_token_metrics_use_only_fit_units(self) -> None:
        key = seeded_control_key("injective", 2)
        plaintext_words = ["ab", "c"]
        cipher_words = encrypt_words(plaintext_words, key)
        first_units = set(cipher_words[0])
        recovered = {
            unit: key["cipher_to_plain"][unit] for unit in first_units
        }
        metrics = recovery_metrics(
            cipher_words,
            plaintext_words,
            recovered,
            first_units,
        )
        self.assertEqual(metrics["fully_observed_token_total"], 1)
        self.assertEqual(metrics["fully_observed_token_correct"], 1)
        self.assertEqual(metrics["fully_observed_token_accuracy"], 1.0)
        self.assertEqual(metrics["full_token_total"], 2)
        self.assertEqual(metrics["full_token_correct"], 1)
        self.assertEqual(metrics["full_token_accuracy"], 0.5)

    def test_fit_symbols_and_key_may_include_units_absent_from_partition(self) -> None:
        key = seeded_control_key("injective", 3)
        letter = key["cipher_to_plain"]["c00"]
        metrics = recovery_metrics(
            [("c00",)],
            [letter],
            {
                "c00": letter,
                "c01": key["cipher_to_plain"]["c01"],
            },
            {"c00", "c01"},
        )
        self.assertEqual(metrics["fit_unit_count"], 2)
        self.assertEqual(metrics["observed_position_total"], 1)
        self.assertEqual(metrics["observed_position_correct"], 1)
        self.assertEqual(metrics["full_char_accuracy"], 1.0)

    def test_validation_rejects_wrong_text_units_and_key_records(self) -> None:
        key = seeded_control_key("injective", 1)
        with self.assertRaises(ValueError):
            encrypt_words(["A"], key)
        with self.assertRaises(ValueError):
            decode_words([("unknown",)], key)
        with self.assertRaises(ValueError):
            recovery_metrics([("c00",)], ["ab"], {}, {"c00"})
        with self.assertRaises(ValueError):
            seeded_control_key("unknown", 1)
        with self.assertRaises(ValueError):
            seeded_control_key("cap2", -1)


if __name__ == "__main__":
    unittest.main()
