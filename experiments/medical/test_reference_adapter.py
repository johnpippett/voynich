"""Synthetic tests for the Celsus reference partition adapter."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from experiments.medical.reference_adapter import (  # noqa: E402
    ReferenceAdapterError,
    adapt_projected_paragraphs,
    normalize_projected_text,
)


def record(book: str, chapter: int, ordinal: int, text: str) -> dict[str, object]:
    chapter_id = f"c{chapter}"
    return {
        "book_id": book,
        "chapter_id": chapter_id,
        "chapter_key": f"{book}:{chapter_id}",
        "local_paragraph_ordinal": ordinal,
        "text": text,
    }


def chapters(book: str, count: int, text: str = "A") -> list[dict[str, object]]:
    return [record(book, chapter, 1, f"{text}{chapter}")
            for chapter in range(1, count + 1)]


class ReferenceAdapterTests(unittest.TestCase):
    def test_combining_marks_and_run_boundaries(self) -> None:
        tokens, rejected, romans = normalize_projected_text(
            "A\u0301 e\u0301 bC—word42/IV"
        )
        self.assertEqual(tokens, ("a", "e", "bc", "word", "iv"))
        self.assertEqual(rejected, 0)
        self.assertEqual(romans, 1)

    def test_unicode_rejection_and_roman_letters(self) -> None:
        tokens, rejected, romans = normalize_projected_text(
            "Latin—Ω beta² IV/X CD"
        )
        self.assertEqual(tokens, ("latin", "beta", "iv", "x", "cd"))
        self.assertEqual(rejected, 1)
        self.assertEqual(romans, 3)

    def test_eight_books_use_floor_chapter_split_and_keep_input(self) -> None:
        source = [item for book in range(1, 9) for item in chapters(f"b{book}", 5)]
        before = deepcopy(source)
        result = adapt_projected_paragraphs(source)
        self.assertEqual(source, before)
        self.assertEqual(
            {split: result.manifest["partitions"][split]["paragraph_count"]
             for split in ("train", "validation", "test")},
            {"train": 24, "validation": 8, "test": 8},
        )
        self.assertEqual(
            result.manifest["split"]["chapter_assignments"]["train"][:3],
            ["b1:c1", "b1:c2", "b1:c3"],
        )
        for book in {item["book_id"] for item in source}:
            assignments = {item.split for item in result.paragraphs
                           if item.book_id == book}
            self.assertEqual(assignments, {"train", "validation", "test"})

    def test_all_paragraphs_in_a_chapter_share_one_split(self) -> None:
        source = [
            record("b", 1, 1, "first"),
            record("b", 1, 2, "second"),
            *chapters("b", 4)[1:],
        ]
        result = adapt_projected_paragraphs(source)
        first_chapter = [item for item in result.paragraphs
                         if item.chapter_key == "b:c1"]
        self.assertEqual({item.split for item in first_chapter}, {"train"})
        self.assertEqual([item.local_paragraph_ordinal for item in first_chapter], [1, 2])

    def test_colon_in_book_ids_does_not_merge_books(self) -> None:
        source = chapters("a:x", 5) + chapters("a:y", 5)
        result = adapt_projected_paragraphs(source)
        assignments = result.manifest["split"]["chapter_assignments"]
        for book in ("a:x", "a:y"):
            self.assertEqual(
                {split: sum(key.startswith(f"{book}:") for key in assignments[split])
                 for split in ("train", "validation", "test")},
                {"train": 3, "validation": 1, "test": 1},
            )

    def test_uneven_books_use_integer_floors(self) -> None:
        source = chapters("short", 6) + chapters("long", 11)
        result = adapt_projected_paragraphs(source)
        assignments = result.manifest["split"]["chapter_assignments"]
        def split_counts(book: str) -> dict[str, int]:
            return {split: sum(key.startswith(f"{book}:")
                               for key in assignments[split])
                    for split in ("train", "validation", "test")}

        self.assertEqual(split_counts("short"), {"train": 3, "validation": 1, "test": 2})
        self.assertEqual(split_counts("long"), {"train": 6, "validation": 2, "test": 3})

    def test_empty_and_cross_split_dedup_preserve_within_split_duplicates(self) -> None:
        source = [
            record("b", 1, 1, "Same"),
            record("b", 2, 1, "same"),
            record("b", 3, 1, ""),
            record("b", 4, 1, "SAME"),
            record("b", 5, 1, "same"),
        ]
        result = adapt_projected_paragraphs(source)
        self.assertEqual(result.partitions["train"], ("same", "same"))
        self.assertEqual(result.partitions["validation"], ())
        self.assertEqual(result.partitions["test"], ())
        by_chapter = {item.chapter_id: item for item in result.paragraphs}
        self.assertTrue(by_chapter["c1"].retained)
        self.assertTrue(by_chapter["c2"].retained)
        self.assertEqual(by_chapter["c3"].exclusion, "empty_after_normalization")
        self.assertEqual(by_chapter["c4"].exclusion, "duplicate_cross_partition")
        self.assertEqual(by_chapter["c5"].exclusion, "duplicate_cross_partition")
        self.assertEqual(
            result.manifest["exclusions"]["duplicate_cross_partition_by_split"],
            {"train": 0, "validation": 1, "test": 1},
        )

    def test_rejected_runs_are_counted_and_empty(self) -> None:
        result = adapt_projected_paragraphs(
            [record("b", 1, 1, "Ω"), record("b", 2, 1, "IV")]
        )
        self.assertFalse(result.paragraphs[0].retained)
        self.assertEqual(result.paragraphs[0].rejected_run_count, 1)
        self.assertEqual(result.paragraphs[1].roman_like_count, 1)

    def test_invalid_fields_order_and_duplicate_keys_fail(self) -> None:
        valid = record("b", 1, 1, "word")
        for bad in (
            {key: value for key, value in valid.items() if key != "text"},
            {**valid, "extra": 1},
            {**valid, "chapter_key": "wrong"},
            {**valid, "local_paragraph_ordinal": True},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ReferenceAdapterError):
                    adapt_projected_paragraphs([bad])
        with self.assertRaises(ReferenceAdapterError):
            adapt_projected_paragraphs([valid, dict(valid)])
        with self.assertRaises(ReferenceAdapterError):
            adapt_projected_paragraphs(
                [record("b", 1, 1, "one"), record("b", 1, 3, "three")]
            )
        with self.assertRaises(ReferenceAdapterError):
            adapt_projected_paragraphs(
                chapters("b", 1) + chapters("c", 1)
                + [record("b", 2, 1, "again")]
            )

    def test_manifest_is_deterministic_and_public_safe(self) -> None:
        source = chapters("b", 5, "SecretText")
        first = adapt_projected_paragraphs(source)
        second = adapt_projected_paragraphs(source)
        self.assertEqual(first.manifest, second.manifest)
        self.assertFalse(first.manifest["raw_text_included"])
        encoded = json.dumps(first.manifest, ensure_ascii=False)
        self.assertNotIn("SecretText", encoded)
        self.assertEqual(
            first.manifest["source"]["record_count"], len(source)
        )


if __name__ == "__main__":
    unittest.main()
