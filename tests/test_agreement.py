"""Tests for bounded agreement between IVTFF transcription records."""

from __future__ import annotations

import pathlib
import sys
import unittest


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from voynich.agreement import compare_transcriptions


def _record(
    folio: str,
    locus: str,
    raw: str,
    tokens: list[str],
    *,
    kind: str = "P0",
    excluded_tokens: int = 0,
    transcriber: str | None = None,
) -> dict:
    return {
        "folio": folio,
        "locus": locus,
        "kind": kind,
        "text_raw": raw,
        "tokens": tokens,
        "excluded_tokens": excluded_tokens,
        "transcriber": transcriber,
    }


class AgreementTests(unittest.TestCase):
    def test_token_insertion_and_deletion_have_one_sequence_edit_each(self) -> None:
        left = [
            _record("f84r", "f84r.1,@P0", "a.b.c", ["a", "b", "c"]),
            _record("f84r", "f84r.2,@P0", "a.b.c", ["a", "b", "c"]),
        ]
        right = [
            _record("f84r", "f84r.1,+P0", "a.b.c.d", ["a", "b", "c", "d"]),
            _record("f84r", "f84r.2,+P0", "a.c", ["a", "c"]),
        ]

        result = compare_transcriptions(left, right)

        self.assertEqual(result["counts"]["aligned"], 2)
        self.assertEqual(result["counts"]["eligible"], 2)
        self.assertEqual(result["agreement"]["raw"]["identical"], 0)
        self.assertEqual(result["agreement"]["tokens"]["identical"], 0)
        self.assertEqual(result["agreement"]["token_edit_distance"]["sum"], 2)
        self.assertEqual(
            [item["token_edit_distance"] for item in result["mismatch_examples"]],
            [1, 1],
        )

    def test_duplicate_alignment_key_is_rejected_before_comparison(self) -> None:
        left = [
            _record("f84r", "f84r.1,@P0", "a", ["a"], transcriber="ZL"),
            _record("f84r", "f84r.1,+P0", "b", ["b"], transcriber="IT"),
        ]
        right = [_record("f84r", "f84r.1,+P0", "a", ["a"])]

        with self.assertRaisesRegex(ValueError, "duplicate alignment key"):
            compare_transcriptions(left, right)

    def test_eligibility_excludes_uncertain_rare_and_interrupted_pairs(self) -> None:
        left = [
            _record("f1r", "f1r.1,@P0", "ok", ["ok"]),
            _record("f1r", "f1r.2,+P0", "uncertain", ["uncertain"], excluded_tokens=1),
            _record("f1r", "f1r.3,+P0", "<!rare note>rare", ["rare"]),
            _record("f1r", "f1r.4,+P0", "a<->b", ["a", "b"]),
        ]
        right = [
            _record("f1r", "f1r.1,+P0", "ok", ["ok"]),
            _record("f1r", "f1r.2,@P0", "uncertain", ["uncertain"]),
            _record("f1r", "f1r.3,@P0", "rare", ["rare"]),
            _record("f1r", "f1r.4,@P0", "a<->b", ["a", "b"]),
        ]

        result = compare_transcriptions(left, right)

        self.assertEqual(result["counts"]["aligned"], 4)
        self.assertEqual(result["counts"]["eligible"], 1)
        self.assertEqual(result["eligibility"]["excluded"]["uncertain_or_rare_tokens"], 2)
        self.assertEqual(result["eligibility"]["excluded"]["interrupted"], 1)
        self.assertEqual(result["agreement"]["raw"]["coverage"], 1.0)
        self.assertEqual(result["agreement"]["tokens"]["coverage"], 1.0)

    def test_alignment_reports_unmatched_loci_and_kind_mismatch_counts(self) -> None:
        left = [
            _record("f2r", "f2r.1,@P0", "one", ["one"], kind="P0"),
            _record("f2r", "f2r.3,@P0", "three", ["three"], kind="P0"),
        ]
        right = [
            _record("f2r", "f2r.1,+P1", "one", ["one"], kind="P1"),
            _record("f2r", "f2r.2,+P0", "two", ["two"], kind="P0"),
        ]

        result = compare_transcriptions(left, right)

        self.assertEqual(result["counts"]["aligned"], 1)
        self.assertEqual(result["counts"]["unmatched"]["left"], 1)
        self.assertEqual(result["counts"]["unmatched"]["right"], 1)
        self.assertEqual(result["kind_mismatches"]["count"], 1)
        self.assertEqual(result["kind_mismatches"]["pairs"], {"P0->P1": 1})
        self.assertEqual(result["unmatched"]["left"][0]["locus_index"], 3)
        self.assertEqual(result["unmatched"]["right"][0]["locus_index"], 2)

    def test_f84r_focus_contains_every_input_row_with_raw_and_tokens(self) -> None:
        left = [
            _record("f84r", "f84r.1,@Lt", "left-one", ["leftone"]),
            _record("f84r", "f84r.3,@P0", "left-three", ["leftthree"]),
        ]
        right = [
            _record("f84r", "f84r.1,+Ln", "right-one", ["rightone"]),
            _record("f84r", "f84r.2,+P0", "right-two", ["righttwo"]),
        ]

        result = compare_transcriptions(left, right)

        self.assertEqual(result["focus"]["folio"], "f84r")
        rows = result["focus"]["rows"]
        self.assertEqual([row["locus_index"] for row in rows], [1, 2, 3])
        self.assertEqual(rows[0]["left"]["raw"], "left-one")
        self.assertEqual(rows[0]["right"]["tokens"], ["rightone"])
        self.assertIsNone(rows[1]["left"])
        self.assertIsNone(rows[2]["right"])

    def test_mismatch_examples_are_bounded_at_twenty(self) -> None:
        left = [
            _record("f3r", f"f3r.{index},@P0", f"left-{index}", ["left"])
            for index in range(1, 23)
        ]
        right = [
            _record("f3r", f"f3r.{index},+P0", f"right-{index}", ["right"])
            for index in range(1, 23)
        ]

        result = compare_transcriptions(left, right)

        self.assertEqual(result["mismatch_counts"]["total"], 22)
        self.assertEqual(len(result["mismatch_examples"]), 20)
        self.assertIn("left_raw", result["mismatch_examples"][0])
        self.assertIn("right_tokens", result["mismatch_examples"][0])

    def test_non_numeric_folio_names_sort_without_affecting_alignment(self) -> None:
        left = [_record("fRos", "fRos.1,@P0", "left", ["left"])]
        right = [_record("fRos", "fRos.1,+P0", "right", ["right"])]

        result = compare_transcriptions(left, right)

        self.assertEqual(result["counts"]["aligned"], 1)
        self.assertEqual(result["mismatch_examples"][0]["folio"], "fRos")


if __name__ == "__main__":
    unittest.main()
