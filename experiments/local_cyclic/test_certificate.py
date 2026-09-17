"""Synthetic tests for strict local cyclic certificates."""

from __future__ import annotations

import unittest

from .certificate import count_local_certificates, extract_word_spans


class StrictWordTests(unittest.TestCase):
    def test_clean_words_keep_source_offsets_and_case(self) -> None:
        extracted = extract_word_spans("  foo.bar  ")

        self.assertEqual(
            [(item.word_index, item.surface, item.source_start, item.source_end)
             for item in extracted.spans],
            [(0, "foo", 2, 5), (1, "bar", 6, 9)],
        )
        self.assertEqual(extracted.eligible, extracted.spans)
        self.assertEqual(extracted.excluded_counts, ())

    def test_uncertain_comma_invalidates_both_adjacent_words(self) -> None:
        extracted = extract_word_spans("foo,bar.baz")

        self.assertEqual([item.surface for item in extracted.spans], ["foo", "bar", "baz"])
        self.assertEqual(
            [item.exclusion_reason for item in extracted.spans],
            ["uncertain_space", "uncertain_space", None],
        )
        self.assertEqual(extracted.excluded_counts, (("uncertain_space", 2),))

    def test_clean_period_clears_an_empty_comma_neighbor(self) -> None:
        extracted = extract_word_spans("foo,.bar")

        self.assertEqual([item.surface for item in extracted.spans], ["foo", "bar"])
        self.assertEqual(
            [item.exclusion_reason for item in extracted.spans],
            ["uncertain_space", None],
        )

    def test_interior_layout_whitespace_invalidates_one_candidate(self) -> None:
        extracted = extract_word_spans("foo bar.baz")

        self.assertEqual([item.surface for item in extracted.spans], ["foo bar", "baz"])
        self.assertEqual(
            [item.exclusion_reason for item in extracted.spans],
            ["interior_whitespace", None],
        )

    def test_constructs_and_case_are_rejected_without_lowercasing(self) -> None:
        cases = {
            "Aaa": ("uppercase", ["Aaa"]),
            "{cTh}": ("ligature", ["{cTh}"]),
            "qu?x": ("uncertain_reading", ["qu?x"]),
            "a'b": ("apostrophe", ["a'b"]),
            "foo@169;": ("high_ascii", ["foo@169;"]),
            "é": ("non_ascii", ["é"]),
            "foo<->bar": ("diagram_marker", ["foo<->bar"]),
            "foo<!note>bar": ("inline_control", ["foo<!note>bar"]),
        }

        for text, (reason, surfaces) in cases.items():
            with self.subTest(text=text):
                extracted = extract_word_spans(text)
                self.assertTrue(extracted.spans)
                self.assertTrue(all(item.exclusion_reason == reason for item in extracted.spans))
                self.assertEqual([item.surface for item in extracted.spans], surfaces)
                self.assertEqual(extracted.eligible, ())

    def test_unclosed_construct_is_excluded(self) -> None:
        extracted = extract_word_spans("foo[bar:baz")

        self.assertEqual(extracted.spans[0].exclusion_reason, "incomplete_span")
        self.assertEqual(extracted.eligible, ())

    def test_paragraph_controls_touch_adjacent_words(self) -> None:
        extracted = extract_word_spans("<%>foo.bar<$>")

        self.assertEqual(
            [item.exclusion_reason for item in extracted.spans],
            ["inline_control", "inline_control"],
        )

    def test_diagram_marker_rejects_the_whole_candidate(self) -> None:
        extracted = extract_word_spans("foo<->bar")

        self.assertEqual([item.surface for item in extracted.spans], ["foo<->bar"])
        self.assertEqual(
            [item.exclusion_reason for item in extracted.spans],
            ["diagram_marker"],
        )


class CertificateTests(unittest.TestCase):
    def test_positive_control_has_no_adjacent_repeat(self) -> None:
        extracted = extract_word_spans("abab.cthch")

        result = count_local_certificates(extracted.spans, representation="raw")

        self.assertEqual(result.status, "not_falsified_by_local_check")
        self.assertEqual(result.eligible_word_count, 2)
        self.assertEqual(result.eligible_unit_count, 9)
        self.assertEqual(result.adjacent_pair_count, 7)
        self.assertEqual(result.certificate_count, 0)
        self.assertEqual(result.affected_word_count, 0)
        self.assertEqual(result.locations, ())

    def test_overlapping_repeats_are_each_certificates(self) -> None:
        extracted = extract_word_spans("aaa")

        result = count_local_certificates(extracted.spans, representation="raw")

        self.assertEqual(result.status, "falsified_for_fixed_track")
        self.assertEqual(result.adjacent_pair_count, 2)
        self.assertEqual(result.certificate_count, 2)
        self.assertEqual(result.affected_word_count, 1)
        self.assertEqual(
            [(item.word_index, item.unit_index, item.unit, item.unit_span)
             for item in result.locations],
            [(0, 0, "a", None), (0, 1, "a", None)],
        )

    def test_word_boundaries_and_nonconsecutive_units_do_not_count(self) -> None:
        extracted = extract_word_spans("a.a.aba")

        result = count_local_certificates(extracted.spans, representation="raw")

        self.assertEqual(result.certificate_count, 0)
        self.assertEqual(result.adjacent_pair_count, 2)
        self.assertEqual(result.status, "not_falsified_by_local_check")

    def test_excluded_candidate_cannot_supply_partial_repeat(self) -> None:
        extracted = extract_word_spans("aa<->aa.aba")

        result = count_local_certificates(extracted.spans, representation="raw")

        self.assertEqual(result.eligible_word_count, 1)
        self.assertEqual(result.certificate_count, 0)
        self.assertEqual(result.status, "not_falsified_by_local_check")

    def test_visual_spans_use_longest_match_and_round_trip(self) -> None:
        word = "cthckhcphcfhchshq"
        extracted = extract_word_spans(word)
        self.assertEqual(len(extracted.eligible), 1)

        from .certificate import unitize_word

        units = unitize_word(extracted.eligible[0], representation="visual")

        self.assertEqual(
            tuple(item.unit for item in units),
            ("cth", "ckh", "cph", "cfh", "ch", "sh", "q"),
        )
        self.assertEqual("".join(item.raw for item in units), word)
        self.assertEqual(
            [(item.start, item.end) for item in units],
            [(0, 3), (3, 6), (6, 9), (9, 12), (12, 14), (14, 16), (16, 17)],
        )

    def test_visual_repeat_records_half_open_unit_span(self) -> None:
        extracted = extract_word_spans("cthcth")

        result = count_local_certificates(extracted.spans, representation="visual")

        self.assertEqual(result.certificate_count, 1)
        self.assertEqual(result.locations[0].unit, "cth")
        self.assertEqual(result.locations[0].unit_span, (0, 3))

    def test_no_eligible_words_is_inconclusive(self) -> None:
        extracted = extract_word_spans("<%>Aaa")

        result = count_local_certificates(extracted.spans, representation="raw")

        self.assertEqual(result.status, "inconclusive_no_eligible_words")
        self.assertEqual(result.eligible_word_count, 0)
        self.assertEqual(result.certificate_count, 0)


if __name__ == "__main__":
    unittest.main()
