"""Tests for the IVTFF corpus parser."""

import tempfile
import unittest
from pathlib import Path

from voynich.corpus import parse_ivtff


def write_fixture(tmp_path: Path, text: str, name: str = "fixture.txt") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


class CorpusParserTests(unittest.TestCase):
    def test_parse_page_metadata_and_paragraph_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(
                Path(directory),
        """#=IVTFF Eva- 2.0 M
<f1r>      <! $Q=A $P=A $F=a $B=1 $I=T $L=A $H=1>
<f1r.1,@P0> <%>fachys.ykal,ar.<!note>shol<$>
""",
            )

            records = parse_ivtff(path)

            self.assertEqual(
                records,
                [
                    {
                        "folio": "f1r",
                        "locus": "f1r.1,@P0",
                        "kind": "P0",
                        "transcriber": None,
                        "text_raw": "<%>fachys.ykal,ar.<!note>shol<$>",
                        "tokens": ["fachys", "ykal", "ar", "shol"],
                        "metadata": {"Q": "A", "P": "A", "F": "a", "B": "1", "I": "T", "L": "A", "H": "1"},
                        "excluded_tokens": 0,
                        "paragraph_start": True,
                        "paragraph_end": True,
                    }
                ],
            )


    def test_uncertain_and_unreadable_words_are_excluded_and_counted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(
                Path(directory),
        """#=IVTFF Eva- 2.0 M
<f1r> <! $I=T>
<f1r.1,@P0> foo.[bar:baz].qu?x.okay.???
""",
            )

            record = parse_ivtff(path)[0]

            self.assertEqual(record["tokens"], ["foo", "okay"])
            self.assertEqual(record["excluded_tokens"], 3)

    def test_join_mode_keeps_uncertain_space_inside_one_analysis_token(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(
                Path(directory),
                """#=IVTFF Eva- 2.0 M
<f1r>
<f1r.1,@P0> foo,bar.baz
""",
            )

            record = parse_ivtff(path, uncertain_spaces="join")[0]

            self.assertEqual(record["text_raw"], "foo,bar.baz")
            self.assertEqual(record["tokens"], ["foobar", "baz"])


    def test_controls_ligatures_high_ascii_and_wrapped_text(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(
                Path(directory),
        """#=IVTFF Eva- 2.0 M
<f1r> <! $I=T>
<f1r.1,@P0> <%>foo{cTh}.bar<->baz /\t
/ .qux@169;<$>
""",
            )

            record = parse_ivtff(path)[0]

            self.assertEqual(record["text_raw"], "<%>foo{cTh}.bar<->baz.qux@169;<$>")
            self.assertEqual(record["tokens"], ["foocth", "bar", "baz"])
            self.assertEqual(record["excluded_tokens"], 1)
            self.assertTrue(record["paragraph_start"])
            self.assertTrue(record["paragraph_end"])


    def test_text_tags_update_metadata_without_merging_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(
                Path(directory),
        """#=IVTFF Eva- 2.0 M
<f1r> <! $I=T $H=@>
<f1r.1,@P0> <@H=2>foo
<f1r.2,+P0> bar
<f1v> <! $I=H $H=1>
<f1v.1,@P0> baz
""",
            )
            records = parse_ivtff(path)

            self.assertEqual(
                [record["metadata"] for record in records],
                [
                    {"I": "T", "H": "2"},
                    {"I": "T", "H": "2"},
                    {"I": "H", "H": "1"},
                ],
            )

    def test_paragraph_marker_text_inside_free_comment_is_not_structure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(
                Path(directory),
                """#=IVTFF Eva- 2.0 M
<f1r>
<f1r.1,@P0> <!literal <% and <$ text> foo
""",
            )

            record = parse_ivtff(path)[0]

            self.assertFalse(record["paragraph_start"])
            self.assertFalse(record["paragraph_end"])
            self.assertEqual(record["tokens"], ["foo"])


    def test_explicit_transcriber_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(
                Path(directory),
        """#=IVTFF Eva- 2.0 M
<f1r> <! $I=T>
<f1r.1,@P0;Z> foo
""",
            )

            self.assertEqual(parse_ivtff(path)[0]["transcriber"], "Z")

    def test_layout_whitespace_is_ignored_and_source_id_is_kept(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = write_fixture(
                Path(directory),
                """#=IVTFF Eva- 2.0 M
<f1r> <! $I=T>
<f1r.1,@P0> qo kedy . shol
""",
                name="ZL3b-n.txt",
            )

            record = parse_ivtff(path)[0]

            self.assertEqual(record["tokens"], ["qokedy", "shol"])
            self.assertEqual(record["transcriber"], "ZL")


    def test_unexpected_markup_raises(self) -> None:
        for text in (
            "<f1r.1,@P0> foo<bar",
            "<f1r.1,@P0> foo@12;",
            "<f1r.1,@P0> foo{bar",
            "<f1r.1,@P0> foo[bar:baz",
            "<f1r.1,@P0> foo|bar",
        ):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as directory:
                path = write_fixture(Path(directory), "#=IVTFF Eva- 2.0 M\n<f1r>\n" + text + "\n")
                with self.assertRaises(ValueError):
                    parse_ivtff(path)


if __name__ == "__main__":
    unittest.main()
