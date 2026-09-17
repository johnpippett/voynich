"""Synthetic tests for the strict TEI paragraph projector."""

from __future__ import annotations

import json
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.medical.tei_projection import (  # noqa: E402
    ProjectionError,
    TEI_NS,
    XML_NS,
    project_tei,
)


def document(body: str, *, header: str = "") -> str:
    return (
        f'<TEI xmlns="{TEI_NS}" xmlns:xml="{XML_NS}">'
        f"<teiHeader>{header}</teiHeader><text><body>{body}</body></text></TEI>"
    )


def chapter(body: str, *, book: str = "1", chapter_id: str = "1") -> str:
    return f'<div subtype="book" n="{book}"><div subtype="chapter" n="{chapter_id}">{body}</div></div>'


class TeiProjectionTests(unittest.TestCase):
    def test_mixed_content_corr_hi_tails_and_transparent_markers(self) -> None:
        xml = document(
            chapter(
                "<p>α<hi>β<hi>γ</hi>δ</hi><pb/>ε"
                "<choice><sic>old</sic><corr>é</corr>κ</choice>ζ"
                '<foreign xml:lang="grc">λόγος</foreign> η'
                "<note>omit</note> θ<milestone/>ι</p>"
            )
        )
        result = project_tei(xml)
        self.assertEqual(
            [paragraph.to_dict() for paragraph in result.paragraphs],
            [
                {
                    "book_id": "1",
                    "chapter_id": "1",
                    "chapter_key": "1:1",
                    "local_paragraph_ordinal": 1,
                    "text": "αβγδεéκζ η θι",
                }
            ],
        )
        self.assertEqual(result.report["actual_retained"], {
            "choice": 1,
            "corr": 1,
            "hi": 2,
            "milestone": 1,
            "p": 1,
            "pb": 1,
        })
        self.assertEqual(result.report["direct_excluded"], {
            "foreign": 1,
            "note": 1,
            "sic": 1,
        })
        self.assertEqual(result.report["ancestor_excluded"], {
            "by_path": {},
            "by_tag": {},
        })

    def test_identifiers_ordinals_and_cross_book_chapter_reuse(self) -> None:
        xml = document(
            chapter("<p>one</p><p>two</p>", book="1", chapter_id="1")
            + chapter("<p>three</p>", book="2", chapter_id="1")
        )
        result = project_tei(xml)
        self.assertEqual(
            [
                (
                    item.chapter_key,
                    item.local_paragraph_ordinal,
                    item.text,
                )
                for item in result.paragraphs
            ],
            [("1:1", 1, "one"), ("1:1", 2, "two"), ("2:1", 1, "three")],
        )
        self.assertEqual(result.report["book_ids"], ["1", "2"])
        self.assertEqual(result.report["chapter_keys"], ["1:1", "2:1"])

        duplicate_book = document(chapter("<p>x</p>") + chapter("<p>y</p>"))
        with self.assertRaisesRegex(ProjectionError, "duplicate book"):
            project_tei(duplicate_book)

        duplicate_chapter = document(
            '<div subtype="book" n="1">'
            '<div subtype="chapter" n="1"><p>x</p></div>'
            '<div subtype="chapter" n="1"><p>y</p></div>'
            "</div>"
        )
        with self.assertRaisesRegex(ProjectionError, "duplicate chapter"):
            project_tei(duplicate_chapter)

    def test_optional_direct_edition_wrapper_and_its_shape(self) -> None:
        wrapped = document(
            '<div type="edition" xml:lang="lat">'
            '<div type="textpart" subtype="book" n="1">'
            '<div type="textpart" subtype="chapter" n="1"><p>wrapped</p></div>'
            "</div></div>"
        )
        result = project_tei(wrapped)
        self.assertEqual(result.paragraphs[0].text, "wrapped")

        bad_wrappers = (
            '<div type="edition" xml:lang="grc"><div subtype="book" n="1">'
            '<div subtype="chapter" n="1"><p>x</p></div></div></div>',
            '<div type="edition" xml:lang="lat" n="1"><div subtype="book" n="1">'
            '<div subtype="chapter" n="1"><p>x</p></div></div></div>',
            '<div type="edition" xml:lang="lat" subtype="book"><div subtype="book" n="1">'
            '<div subtype="chapter" n="1"><p>x</p></div></div></div>',
            '<div type="edition" xml:lang="lat"><div type="edition" xml:lang="lat">'
            '<div subtype="book" n="1"><div subtype="chapter" n="1">'
            '<p>x</p></div></div></div></div>',
            '<div type="edition" xml:lang="lat"><div subtype="book" n="1">'
            '<div subtype="chapter" n="1"><div type="edition" xml:lang="lat">'
            '<p>x</p></div></div></div></div>',
        )
        for content in bad_wrappers:
            with self.subTest(content=content):
                with self.assertRaises(ProjectionError):
                    project_tei(document(content))

        duplicate_wrappers = (
            '<div type="edition" xml:lang="lat"><div subtype="book" n="1">'
            '<div subtype="chapter" n="1"><p>x</p></div></div></div>'
            '<div type="edition" xml:lang="lat"><div subtype="book" n="2">'
            '<div subtype="chapter" n="1"><p>y</p></div></div></div>'
        )
        with self.assertRaisesRegex(ProjectionError, "duplicate edition"):
            project_tei(document(duplicate_wrappers))

    def test_empty_policy_is_explicit_and_keeps_stable_source_ordinals(self) -> None:
        xml = document(chapter('<p><note>removed</note></p><p>kept</p>'))
        included = project_tei(xml, empty_policy="include")
        self.assertEqual([item.text for item in included.paragraphs], ["", "kept"])
        self.assertEqual(
            [item.local_paragraph_ordinal for item in included.paragraphs], [1, 2]
        )
        self.assertEqual(included.report["empty_projected_paragraph_policy"], "include")
        self.assertEqual(included.report["empty_projected_paragraph_count"], 1)

        dropped = project_tei(xml, empty_policy="drop")
        self.assertEqual([item.text for item in dropped.paragraphs], ["kept"])
        self.assertEqual(dropped.report["dropped_empty_paragraph_count"], 1)
        self.assertEqual(dropped.report["book_ids"], ["1"])
        self.assertEqual(dropped.report["chapter_keys"], ["1:1"])
        with self.assertRaises(ValueError):
            project_tei(xml, empty_policy="silent")

    def test_exclusion_boundary_uses_retained_prefix_and_next_segment(self) -> None:
        cases = (
            "<p>a<note>x</note>b</p>",
            "<p>a<note><del>x</del></note>b</p>",
            "<p>a<note>x</note><figure>y</figure>b</p>",
            "<p>a<note>x</note><pb/>b</p>",
            "<p>a<note>x</note><hi>b</hi></p>",
            "<p>a<note>x</note><choice><sic>old</sic><corr>b</corr></choice></p>",
            "<p>a<choice><sic>x</sic><corr/></choice>b</p>",
            "<p>a<choice><sic>x</sic>z<corr/></choice>b</p>",
            "<p>a<choice><sic>x</sic><corr/>b</choice></p>",
        )
        for content in cases:
            with self.subTest(content=content):
                with self.assertRaisesRegex(ProjectionError, "adjacent letters"):
                    project_tei(document(chapter(content)))

        safe = project_tei(document(chapter("<p>a<note>x</note> b</p>")))
        self.assertEqual(safe.paragraphs[0].text, "a b")

        empty_correction = project_tei(
            document(chapter("<p>a<choice><sic>x</sic><corr/></choice> b</p>")))
        self.assertEqual(empty_correction.paragraphs[0].text, "a b")

        nested_empty_sic = project_tei(
            document(
                chapter(
                    "<p>a<choice><sic>x</sic><corr>"
                    "<choice><sic></sic>q<corr/></choice>"
                    "</corr></choice>b</p>"
                )
            )
        )
        self.assertEqual(nested_empty_sic.paragraphs[0].text, "aqb")

        nested_empty_sic_with_whitespace = project_tei(
            document(
                chapter(
                    "<p>a<choice> <sic>x</sic> <corr>"
                    "<choice> <sic></sic>q<corr/></choice>"
                    "</corr> </choice>b</p>"
                )
            )
        )
        self.assertEqual(
            nested_empty_sic_with_whitespace.paragraphs[0].text, "a q b"
        )

        with self.assertRaisesRegex(ProjectionError, "adjacent letters"):
            project_tei(
                document(
                    chapter(
                        "<p>a<choice><sic>x</sic><corr>"
                        "<choice><sic>y</sic><corr/></choice>"
                        "</corr></choice>b</p>"
                    )
                )
            )

    def test_excluded_subtree_counts_include_nested_shapes(self) -> None:
        xml = document(
            chapter(
                '<p>A <note>x<foreign xml:lang="grc">γ</foreign>'
                '<hi>h</hi><note>nested</note></note> B</p>'
            )
        )
        result = project_tei(xml)
        self.assertEqual(result.paragraphs[0].text, "A B")
        self.assertEqual(result.report["source_counts"], {
            "body": 1,
            "div": 2,
            "foreign": 1,
            "hi": 1,
            "note": 2,
            "p": 1,
        })
        self.assertEqual(result.report["selected_subtree_counts"], {
            "foreign": 1,
            "hi": 1,
            "note": 2,
            "p": 1,
        })
        self.assertEqual(result.report["direct_excluded"], {"note": 1})
        self.assertEqual(result.report["ancestor_excluded"], {
            "by_tag": {"foreign": 1, "hi": 1, "note": 1},
            "by_path": {
                "foreign|note": 1,
                "hi|note": 1,
                "note|note": 1,
            },
        })

    def test_excluded_element_tails_are_retained_in_parent_order(self) -> None:
        xml = document(
            chapter("<p>A <note>first</note> B <note>second</note> C</p>")
        )
        result = project_tei(xml)
        self.assertEqual(result.paragraphs[0].text, "A B C")
        self.assertEqual(result.report["direct_excluded"], {"note": 2})

    def test_both_choice_branch_tails_are_preserved(self) -> None:
        xml = document(
            chapter("<p>a<choice><sic>x</sic>τ<corr>y</corr>κ</choice>b</p>")
        )
        result = project_tei(xml)
        self.assertEqual(result.paragraphs[0].text, "aτyκb")

    def test_validation_runs_before_traversal_in_excluded_subtrees(self) -> None:
        invalid_documents = (
            '<p><note><add>bad</add></note></p>',
            '<p><note><choice><sic>x</sic></choice></note></p>',
            '<p><note><foreign xml:lang="lat">bad</foreign></note></p>',
            '<p><foreign>missing language</foreign></p>',
            '<p><choice><corr>x</corr><sic>y</sic></choice></p>',
            '<p><choice><sic>x</sic><corr>y</corr><corr>z</corr></choice></p>',
            '<p><choice>direct text<sic>x</sic><corr>y</corr></choice></p>',
        )
        for content in invalid_documents:
            with self.subTest(content=content):
                with self.assertRaises(ProjectionError):
                    project_tei(document(chapter(content)))

        unsupported_namespace = (
            '<p><x xmlns="urn:other">bad</x></p>'
        )
        with self.assertRaisesRegex(ProjectionError, "exact TEI namespace"):
            project_tei(document(chapter(unsupported_namespace)))

    def test_scope_and_division_validation_is_strict(self) -> None:
        outside = document('<p>outside</p>' + chapter('<p>inside</p>'))
        with self.assertRaisesRegex(ProjectionError, "direct child of chapter"):
            project_tei(outside)

        no_book = document('<div subtype="chapter" n="1"><p>x</p></div>')
        with self.assertRaisesRegex(ProjectionError, "direct child of book"):
            project_tei(no_book)

        bad_division = document(
            '<div subtype="appendix" n="1"><p>x</p></div>'
        )
        with self.assertRaisesRegex(ProjectionError, "subtype"):
            project_tei(bad_division)

        missing_id = document('<div subtype="book"><div subtype="chapter" n="1"><p>x</p></div></div>')
        with self.assertRaisesRegex(ProjectionError, "book must have"):
            project_tei(missing_id)

        paragraph_in_note = document(
            '<div subtype="book" n="1"><div subtype="chapter" n="1">'
            '<note><p>note text</p></note></div></div>'
        )
        with self.assertRaisesRegex(ProjectionError, "paragraph cannot"):
            project_tei(paragraph_in_note)

        division_in_note = document(
            '<div subtype="book" n="1"><div subtype="chapter" n="1">'
            '<note><div subtype="book" n="2"><div subtype="chapter" n="1">'
            '<p>hidden structure</p></div></div></note></div></div>'
        )
        with self.assertRaisesRegex(ProjectionError, "div cannot"):
            project_tei(division_in_note)

    def test_divisions_and_paragraphs_require_direct_structural_parents(self) -> None:
        wrappers = ("hi", "pb", "milestone")
        for wrapper in wrappers:
            with self.subTest(kind="book", wrapper=wrapper):
                content = (
                    f"<{wrapper}><div subtype=\"book\" n=\"1\">"
                    '<div subtype="chapter" n="1"><p>x</p></div>'
                    f"</div></{wrapper}>"
                )
                with self.assertRaisesRegex(ProjectionError, "direct child of body"):
                    project_tei(document(content))

            with self.subTest(kind="chapter", wrapper=wrapper):
                content = (
                    '<div subtype="book" n="1">'
                    f"<{wrapper}><div subtype=\"chapter\" n=\"1\">"
                    '<p>x</p></div>'
                    f"</{wrapper}></div>"
                )
                with self.assertRaisesRegex(ProjectionError, "direct child of book"):
                    project_tei(document(content))

            with self.subTest(kind="paragraph", wrapper=wrapper):
                content = (
                    '<div subtype="book" n="1"><div subtype="chapter" n="1">'
                    f"<{wrapper}><p>x</p></{wrapper}>"
                    '</div></div>'
                )
                with self.assertRaisesRegex(
                    ProjectionError, "direct child of chapter"
                ):
                    project_tei(document(content))

    def test_unicode_and_xml_whitespace_only_normalisation(self) -> None:
        xml = document(chapter("<p>U  V\nſæ\u00a0iJ</p>"))
        result = project_tei(xml)
        self.assertEqual(result.paragraphs[0].text, "U V ſæ\u00a0iJ")

    def test_result_is_json_serialisable(self) -> None:
        result = project_tei(document(chapter("<p>text</p>")))
        encoded = json.dumps(result.to_dict(), ensure_ascii=False, sort_keys=True)
        self.assertIn('"chapter_key": "1:1"', encoded)


if __name__ == "__main__":
    unittest.main()
