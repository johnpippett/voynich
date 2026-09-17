"""Tests for the fixed-table Naibbe oracle and candidate enumerator."""

from __future__ import annotations

import csv
import pathlib
import sys
import tempfile
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voynich.naibbe import (  # noqa: E402
    ForwardConfig,
    PUBLISHED_ALPHABET,
    TABLE_NAMES,
    compatibility_aggregate,
    encrypt_fixed,
    load_table_csv,
)


def _synthetic_rows() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for state_index, state in enumerate(("unigram", "prefix", "suffix")):
        for table_index, table in enumerate(TABLE_NAMES):
            for letter in ("a", "b"):
                rows.append(
                    (
                        f"{state}_{table}_{letter}",
                        f"{state[0]}{state_index}{table_index}{letter}",
                    )
                )
    return rows


def _write_table(
    path: pathlib.Path,
    rows: list[tuple[str, str]],
) -> pathlib.Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(("code", "glyphs"))
        writer.writerows(rows)
    return path


class NaibbeTableTests(unittest.TestCase):
    def test_duplicate_glyphs_keep_plaintext_and_table_choices(self) -> None:
        rows = _synthetic_rows()
        overrides = {
            "unigram_alpha_a": "u",
            "unigram_beta1_a": "u",
            "prefix_alpha_a": "p",
            "suffix_alpha_b": "s",
            "prefix_beta1_a": "p",
            "suffix_beta1_b": "s",
            "prefix_beta2_b": "p",
            "suffix_beta2_a": "s",
        }
        rows = [(code, overrides.get(code, glyph)) for code, glyph in rows]

        with tempfile.TemporaryDirectory() as directory:
            path = _write_table(pathlib.Path(directory) / "tables.csv", rows)
            book = load_table_csv(path, alphabet=("a", "b"))

        unigram = book.candidates("u")
        self.assertEqual(unigram.plaintexts, ("a",))
        self.assertTrue(unigram.same_plaintext_ambiguity)
        self.assertTrue(unigram.latent_table_choice_ambiguity)
        self.assertFalse(unigram.plaintext_ambiguity)
        self.assertEqual(
            {candidate.table_choices for candidate in unigram.candidates},
            {("alpha",), ("beta1",)},
        )

        bigram = book.candidates("ps")
        self.assertTrue({"ab", "ba"}.issubset(set(bigram.plaintexts)))
        self.assertTrue(bigram.plaintext_ambiguity)
        self.assertTrue(bigram.latent_table_choice_ambiguity)
        self.assertGreaterEqual(len(bigram.candidates), 3)

    def test_no_parse_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = _write_table(pathlib.Path(directory) / "tables.csv", _synthetic_rows())
            book = load_table_csv(path, alphabet=("a", "b"))

        result = book.candidates("not-in-table")
        self.assertTrue(result.no_parse)
        self.assertEqual(result.candidates, ())
        self.assertEqual(result.to_dict()["candidate_count"], 0)

    def test_malformed_table_is_rejected(self) -> None:
        rows = _synthetic_rows()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)

            missing = _write_table(root / "missing.csv", rows[:-1])
            with self.assertRaisesRegex(ValueError, "incomplete table"):
                load_table_csv(missing, alphabet=("a", "b"))

            duplicate = _write_table(root / "duplicate.csv", rows + [rows[0]])
            with self.assertRaisesRegex(ValueError, "duplicate code"):
                load_table_csv(duplicate, alphabet=("a", "b"))

            empty = [(code, "") if code == rows[0][0] else (code, glyph) for code, glyph in rows]
            empty_path = _write_table(root / "empty.csv", empty)
            with self.assertRaisesRegex(ValueError, "empty"):
                load_table_csv(empty_path, alphabet=("a", "b"))

            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                load_table_csv(missing, alphabet=("a", "b"), expected_sha256="0" * 64)

    def test_fixed_forward_oracle_contains_known_reading_for_multiple_seeds(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = _write_table(pathlib.Path(directory) / "tables.csv", _synthetic_rows())
            book = load_table_csv(path, alphabet=("a", "b"))

        config = ForwardConfig(
            weights=tuple((table, 1) for table in TABLE_NAMES),
            respacing_numerator=1,
            respacing_denominator=2,
            collision_policy="full",
            normalize=False,
        )
        first = encrypt_fixed("ababbaab", book, config=config, seed=0)
        self.assertEqual(first, encrypt_fixed("ababbaab", book, config=config, seed=0))

        for seed in (0, 1, 17, 101):
            result = encrypt_fixed("ababbaab", book, config=config, seed=seed)
            self.assertEqual(sum(len(unit) for unit in result.units), 8)
            for emission in result.emissions:
                candidates = book.candidates(emission.token).candidates
                self.assertIn(
                    next(
                        candidate
                        for candidate in candidates
                        if candidate.plaintext == emission.plaintext_unit
                        and candidate.state == emission.state
                        and candidate.table_choices == emission.table_choices
                    ),
                    candidates,
                )

        with self.assertRaisesRegex(ValueError, "seed must be an integer"):
            encrypt_fixed("ab", book, config=config, seed=None)  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "seed must be an integer"):
            encrypt_fixed("ab", book, config=config, seed=True)  # type: ignore[arg-type]

    def test_aggregate_contains_counts_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = _write_table(pathlib.Path(directory) / "tables.csv", _synthetic_rows())
            book = load_table_csv(path, alphabet=("a", "b"))

        aggregate = compatibility_aggregate(
            ["u00a", "p10as20b", "p10as20b", "unknown"], book
        )
        self.assertEqual(aggregate["token_count"], 4)
        self.assertEqual(aggregate["type_count"], 3)
        self.assertEqual(aggregate["parseable_token_count"], 3)
        self.assertEqual(aggregate["parseable_type_count"], 2)
        self.assertEqual(aggregate["no_parse_token_count"], 1)
        self.assertNotIn("u", aggregate)
        self.assertNotIn("ps", aggregate)

    @unittest.skipUnless(
        (PROJECT_ROOT / "data/raw/naibbe/naibbe-cipher/references/naibbe_tables.csv").exists(),
        "downloaded Naibbe source table is not present",
    )
    def test_published_table_has_expected_shape(self) -> None:
        path = PROJECT_ROOT / "data/raw/naibbe/naibbe-cipher/references/naibbe_tables.csv"
        book = load_table_csv(path)
        self.assertEqual(book.alphabet, PUBLISHED_ALPHABET)
        self.assertEqual(len(book.glyphs), 414)
        self.assertEqual(len(book.bigram_catalog), 18_935)


if __name__ == "__main__":
    unittest.main()
