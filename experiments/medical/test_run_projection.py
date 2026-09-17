"""Synthetic tests for the source-bound Celsus validation runner."""

from __future__ import annotations

import json
import inspect
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.medical import run_projection as runner

from experiments.medical.run_projection import (
    AUDIT_RECEIPT_SHA256,
    FREEZE_FILES,
    PROTOCOL,
    RunnerFailure,
    SOURCE_COMMIT,
    SOURCE_BYTES,
    SOURCE_REPOSITORY,
    SOURCE_SHA256,
    SOURCE_URL,
    TraversalResult,
    _assert_source_targets,
    _canonical_json_bytes,
    _failure_receipt,
    _implementation_pins,
    _independent_projected_content,
    _manual_locations,
    _manual_outputs,
    _sha256,
    _traverse_independently,
    _validate_structure,
    _verify_audit_receipt,
    _verify_freeze_manifest,
    _write_exclusive,
    run_validation,
    validate_bytes,
)
from experiments.medical.tei_projection import TEI_NS, XML_NS


def document(body: str) -> bytes:
    return (
        f'<TEI xmlns="{TEI_NS}" xmlns:xml="{XML_NS}">'
        f"<teiHeader/><text><body>{body}</body></text></TEI>"
    ).encode("utf-8")


def chapter(body: str, *, book: str = "1", chapter_id: str = "1") -> str:
    return (
        f'<div subtype="book" n="{book}">'
        f'<div subtype="chapter" n="{chapter_id}">{body}</div>'
        "</div>"
    )


def wrapped_document(*, language: str = "lat", extra: str = "") -> bytes:
    return document(
        f'<div type="edition" xml:lang="{language}">'
        '<div type="textpart" subtype="book" n="1">'
        '<div type="textpart" subtype="chapter" n="1"><p>x</p></div>'
        f"</div>{extra}</div>"
    )


def freeze_fixture(root: Path) -> bytes:
    entries = []
    for index, relative_path in enumerate(FREEZE_FILES):
        target = root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        data = f"fixture-{index}".encode("ascii")
        target.write_bytes(data)
        entries.append(
            {
                "path": relative_path.as_posix(),
                "sha256": _sha256(data),
            }
        )
    return _canonical_json_bytes(
        {
            "schema_version": 1,
            "protocol": PROTOCOL,
            "files": entries,
        }
    )


class RunProjectionTests(unittest.TestCase):
    def test_canonical_json_uses_fixed_compact_separators(self) -> None:
        self.assertEqual(
            _canonical_json_bytes({"b": "x", "a": 1}),
            b'{"a":1,"b":"x"}\n',
        )

    def test_module_and_independent_traversals_match(self) -> None:
        source = document(
            chapter(
                '<p>A  <hi>B</hi><pb/> '
                '<choice><sic>old</sic><corr>new</corr>!</choice>'
                '<foreign xml:lang="grc">logos</foreign> C '
                '<note>drop</note> D<milestone/>E</p>'
            )
        )
        document_state, module, independent = validate_bytes(source)
        self.assertEqual(module.records, independent.records)
        self.assertEqual(module.report, independent.report)
        self.assertEqual(
            module.records[0],
            {
                "book_id": "1",
                "chapter_id": "1",
                "chapter_key": "1:1",
                "local_paragraph_ordinal": 1,
                "text": "A B new! C DE",
            },
        )
        self.assertEqual(document_state.report["paragraph_count"], 1)
        self.assertEqual(module.report["boundary_validation"], {"status": "PASS"})
        self.assertEqual(module.report["projected_paragraphs_by_book"], {"1": 1})
        self.assertEqual(module.report["projected_paragraphs_by_chapter"], {"1:1": 1})

    def test_nested_choice_projected_content_keeps_sic_tail(self) -> None:
        source = document(
            chapter(
                '<p><choice><sic>outer</sic><corr>'
                '<choice><sic/>q<corr/></choice>'
                '</corr></choice></p>'
            )
        )
        state = _validate_structure(source, require_source_shape=False)
        outer_corr = next(
            element for element in state.paragraphs[0].iter()
            if element.tag.endswith("corr")
        )
        self.assertTrue(outer_corr.tag.endswith("corr"))
        self.assertEqual(_independent_projected_content(outer_corr), "q")
        independent = _traverse_independently(state)
        self.assertEqual(independent.records[0]["text"], "q")

    def test_empty_correction_checks_boundary_before_later_tail(self) -> None:
        safe = document(chapter("<p>a<choice><sic>x</sic><corr/></choice> b</p>"))
        _document, module, independent = validate_bytes(safe)
        self.assertEqual(module.records[0]["text"], "a b")
        self.assertEqual(module.records, independent.records)

        unsafe = document(chapter("<p>a<choice><sic>x</sic><corr/></choice>b</p>"))
        document_state = _validate_structure(unsafe, require_source_shape=False)
        with self.assertRaises(RunnerFailure) as raised:
            _traverse_independently(document_state)
        self.assertEqual(raised.exception.kind, "retained_boundary")
        self.assertEqual(raised.exception.location["chapter_key"], "1:1")
        with self.assertRaises(RunnerFailure) as raised:
            validate_bytes(unsafe)
        self.assertEqual(raised.exception.kind, "retained_boundary")
        self.assertEqual(raised.exception.location["chapter_key"], "1:1")

    def test_empty_policy_include_keeps_source_location(self) -> None:
        source = document(chapter("<p><note>only removed</note></p><p>kept</p>"))
        _document, module, independent = validate_bytes(source)
        self.assertEqual([item["text"] for item in module.records], ["", "kept"])
        self.assertEqual(module.records, independent.records)
        self.assertEqual(module.report["empty_projected_paragraph_count"], 1)
        self.assertEqual(module.report["dropped_empty_paragraph_count"], 0)

    def test_nested_excluded_counters_match(self) -> None:
        source = document(
            chapter(
                '<p>A <note>x<foreign xml:lang="grc">g</foreign>'
                '<hi>h</hi><note>nested</note></note> B</p>'
            )
        )
        _document, module, independent = validate_bytes(source)
        self.assertEqual(module.report["ancestor_excluded"], {
            "by_tag": {"foreign": 1, "hi": 1, "note": 1},
            "by_path": {
                "foreign|note": 1,
                "hi|note": 1,
                "note|note": 1,
            },
        })
        self.assertEqual(module.report, independent.report)

    def test_wrapper_shape_is_checked_without_source_target_counts(self) -> None:
        state, _module, _independent = validate_bytes(
            wrapped_document(), require_source_shape=False
        )
        self.assertEqual(state.report["edition_wrapper_count"], 1)
        self.assertEqual(state.report["wrapper_book_count"], 1)
        self.assertEqual(state.report["wrapper_pb_count"], 0)

        for bad in (
            wrapped_document(language="grc"),
            wrapped_document(extra='<div type="edition" xml:lang="lat"/>'),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(RunnerFailure):
                    _validate_structure(bad, require_source_shape=False)

    def test_pinned_shape_rejects_fixture_that_is_not_the_pinned_source(self) -> None:
        with self.assertRaisesRegex(RunnerFailure, "source wrapper counts"):
            _validate_structure(wrapped_document(), require_source_shape=True)

    def test_structural_targets_are_a_separate_gate(self) -> None:
        state = _validate_structure(document(chapter("<p>x</p>")), require_source_shape=False)
        broken = dict(state.report)
        broken["paragraph_count"] = 550
        with self.assertRaisesRegex(RunnerFailure, "source structure targets"):
            _assert_source_targets(broken)

    def test_manual_locations_are_fixed_and_deterministic(self) -> None:
        locations = tuple(
            {
                "book_id": str((index - 1) % 8 + 1),
                "chapter_id": str(index),
                "chapter_key": f"{(index - 1) % 8 + 1}:{index}",
                "local_paragraph_ordinal": 1,
                "global_source_paragraph_ordinal": index,
            }
            for index in range(1, 551)
        )
        selected = _manual_locations(locations)
        self.assertEqual(selected, _manual_locations(locations))
        self.assertIn(550, {item["global_source_paragraph_ordinal"] for item in selected})
        self.assertTrue(
            {1 + 36 * index for index in range(16)}.issubset(
                {item["global_source_paragraph_ordinal"] for item in selected}
            )
        )

    def test_manual_checklist_declares_feature_statuses(self) -> None:
        source = document(chapter("<p>fixed</p>"))
        state, module, independent = validate_bytes(source)
        checklist_bytes, context_bytes = _manual_outputs(
            state, module.records, independent.records
        )
        checklist = json.loads(checklist_bytes)
        self.assertEqual(
            checklist["allowed_feature_statuses"], ["PASS", "FAIL", "NOT_PRESENT"]
        )
        self.assertTrue(checklist["feature_names"])
        self.assertEqual(
            set(checklist["checks"][0]["features"]),
            set(checklist["feature_names"]),
        )
        self.assertTrue(all(
            status == "PENDING"
            for status in checklist["checks"][0]["features"].values()
        ))
        self.assertIn(b"source_xml", context_bytes)

    def test_audit_receipt_pin_is_current_and_public(self) -> None:
        receipt_path = Path(__file__).resolve().parents[2] / "reports/celsus-source-audit.json"
        receipt_bytes = receipt_path.read_bytes()
        self.assertEqual(_sha256(receipt_bytes), AUDIT_RECEIPT_SHA256)
        receipt = _verify_audit_receipt(receipt_bytes)
        self.assertEqual(receipt["repository"]["url"], SOURCE_REPOSITORY)
        self.assertEqual(receipt["repository"]["commit"], SOURCE_COMMIT)
        xml_entry = next(item for item in receipt["files"] if item["role"] == "TEI source")
        self.assertEqual(xml_entry["url"], SOURCE_URL)
        self.assertEqual(xml_entry["expected_sha256"], SOURCE_SHA256)

    def test_implementation_pins_are_repo_relative(self) -> None:
        pins = _implementation_pins()
        self.assertEqual(set(pins), {"protocol", "projector", "runner"})
        for entry in pins.values():
            self.assertTrue(entry["available"])
            self.assertEqual(len(entry["sha256"]), 64)
            self.assertNotIn("/home/", entry["path"])

    def test_freeze_manifest_rejects_each_mutated_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = freeze_fixture(root)
            info = _verify_freeze_manifest(manifest, repository_root=root)
            self.assertEqual(info["manifest_path"], "experiments/medical/freeze-v1.json")
            self.assertEqual(info["protocol"], PROTOCOL)
            for relative_path in FREEZE_FILES:
                target = root / relative_path
                original = target.read_bytes()
                target.write_bytes(original + b"-mutated")
                with self.subTest(path=relative_path):
                    with self.assertRaisesRegex(RunnerFailure, "frozen file hash"):
                        _verify_freeze_manifest(manifest, repository_root=root)
                target.write_bytes(original)

    def test_private_jsonl_is_hashable_and_public_record_has_no_text(self) -> None:
        record_bytes = _canonical_json_bytes(
            {
                "book_id": "1",
                "chapter_id": "1",
                "chapter_key": "1:1",
                "local_paragraph_ordinal": 1,
                "text": "private",
            }
        )
        self.assertEqual(record_bytes.count(b"\n"), 1)
        self.assertEqual(_sha256(record_bytes), _sha256(record_bytes))
        failure = _failure_receipt(
            RunnerFailure(
                "retained_boundary",
                "retained letters joined after content exclusion",
                location={"chapter_key": "1:1", "local_paragraph_ordinal": 1},
            )
        )
        public = json.dumps(failure, ensure_ascii=False, sort_keys=True)
        self.assertNotIn("private", public)
        self.assertNotIn("/home/", public)
        self.assertNotIn("source_xml", public)
        self.assertIn("implementation", public)
        self.assertEqual(failure["source"]["url"], SOURCE_URL)
        self.assertEqual(failure["source"]["bytes"], SOURCE_BYTES)

    def test_freeze_failure_stops_before_source_checks_or_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with patch.object(
                runner, "_load_freeze_manifest",
                side_effect=RunnerFailure("freeze_manifest_missing", "freeze manifest is unavailable"),
            ), patch.object(runner, "_verify_source") as source_check, patch.object(
                runner, "validate_bytes"
            ) as projection:
                receipt = run_validation(b"private", b"private", Path(temporary))
            self.assertEqual(receipt["status"], "FAILED")
            self.assertEqual(receipt["failure"]["kind"], "freeze_manifest_missing")
            source_check.assert_not_called()
            projection.assert_not_called()
            self.assertNotIn("freeze_info", inspect.signature(run_validation).parameters)

    def test_failed_run_writes_public_failure_without_source_text(self) -> None:
        receipt_path = Path(__file__).resolve().parents[2] / "reports/celsus-source-audit.json"
        with tempfile.TemporaryDirectory() as temporary:
            receipt = run_validation(
                b"synthetic source",
                receipt_path.read_bytes(),
                Path(temporary),
            )
            self.assertEqual(receipt["status"], "FAILED")
            self.assertEqual(receipt["manual_acceptance"], "PENDING")
            self.assertEqual(receipt["source"]["url"], SOURCE_URL)
            self.assertEqual(receipt["source"]["bytes"], SOURCE_BYTES)
            public = (Path(temporary) / "public-receipt.json").read_text()
            self.assertNotIn("synthetic source", public)
            self.assertNotIn("source_xml", public)
            self.assertNotIn(temporary, public)

    def test_record_mismatch_keeps_detail_private_and_location_public(self) -> None:
        source = document(chapter("<p>original</p>"))
        receipt_path = Path(__file__).resolve().parents[2] / "reports/celsus-source-audit.json"
        original_module = runner._module_traverse

        def mutated_module(source_bytes: bytes) -> TraversalResult:
            result = original_module(source_bytes)
            record = dict(result.records[0])
            record["text"] = "tampered"
            return TraversalResult((record,), result.report)

        with tempfile.TemporaryDirectory() as temporary:
            with patch(
                "experiments.medical.run_projection._verify_audit_receipt",
                return_value={"checks": {}},
            ), patch("experiments.medical.run_projection._verify_source"), patch(
                "experiments.medical.run_projection._load_freeze_manifest",
                return_value={
                    "manifest_path": "experiments/medical/freeze-v1.json",
                    "manifest_sha256": "0" * 64,
                    "protocol": PROTOCOL,
                },
            ), patch(
                "experiments.medical.run_projection._module_traverse",
                side_effect=mutated_module,
            ):
                receipt = run_validation(
                    source,
                    receipt_path.read_bytes(),
                    Path(temporary),
                    require_source_shape=False,
                )
            self.assertEqual(receipt["failure"]["kind"], "traversal_mismatch")
            self.assertEqual(receipt["failure"]["location"]["chapter_key"], "1:1")
            public = (Path(temporary) / "public-receipt.json").read_text()
            self.assertNotIn("tampered", public)
            detail = json.loads((Path(temporary) / "mismatch-detail.json").read_bytes())
            self.assertEqual(detail["details"]["module"]["text"], "tampered")

    def test_counter_mismatch_reports_safe_counter_key(self) -> None:
        source = document(chapter("<p>stable</p>"))
        receipt_path = Path(__file__).resolve().parents[2] / "reports/celsus-source-audit.json"
        original_module = runner._module_traverse

        def mutated_module(source_bytes: bytes) -> TraversalResult:
            result = original_module(source_bytes)
            report = dict(result.report)
            report["actual_retained"] = {"tampered": 1}
            return TraversalResult(result.records, report)

        with tempfile.TemporaryDirectory() as temporary:
            with patch(
                "experiments.medical.run_projection._verify_audit_receipt",
                return_value={"checks": {}},
            ), patch("experiments.medical.run_projection._verify_source"), patch(
                "experiments.medical.run_projection._load_freeze_manifest",
                return_value={
                    "manifest_path": "experiments/medical/freeze-v1.json",
                    "manifest_sha256": "0" * 64,
                    "protocol": PROTOCOL,
                },
            ), patch(
                "experiments.medical.run_projection._module_traverse",
                side_effect=mutated_module,
            ):
                receipt = run_validation(
                    source,
                    receipt_path.read_bytes(),
                    Path(temporary),
                    require_source_shape=False,
                )
            self.assertEqual(receipt["failure"]["kind"], "counter_mismatch")
            counter_key = receipt["failure"]["location"]["counter_key"]
            self.assertTrue(counter_key.startswith("actual_retained."))
            detail = json.loads((Path(temporary) / "mismatch-detail.json").read_bytes())
            self.assertEqual(detail["details"]["counter_key"], counter_key)

    def test_synthetic_unchecked_receipt_is_truthful(self) -> None:
        source = document(chapter("<p>synthetic</p>"))
        receipt_path = Path(__file__).resolve().parents[2] / "reports/celsus-source-audit.json"
        self.assertTrue(inspect.signature(run_validation).parameters["require_source_shape"].default)
        with tempfile.TemporaryDirectory() as temporary:
            with patch(
                "experiments.medical.run_projection._verify_audit_receipt",
                return_value={"checks": {}},
            ), patch("experiments.medical.run_projection._verify_source"), patch(
                "experiments.medical.run_projection._load_freeze_manifest",
                return_value={
                    "manifest_path": "experiments/medical/freeze-v1.json",
                    "manifest_sha256": "0" * 64,
                    "protocol": PROTOCOL,
                },
            ):
                receipt = run_validation(
                    source,
                    receipt_path.read_bytes(),
                    Path(temporary),
                    require_source_shape=False,
                )
            self.assertEqual(receipt["validation_scope"], "synthetic_unchecked")
            self.assertFalse(receipt["checks"]["source_structure_targets"])
            self.assertEqual(
                receipt["checks"]["source_structure_targets_status"], "NOT_RUN"
            )

    def test_existing_output_must_match_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "output.json"
            data = b'{"a":1}\n'
            _write_exclusive(path, data)
            _write_exclusive(path, data)
            with self.assertRaisesRegex(RunnerFailure, "existing output differs"):
                _write_exclusive(path, b'{"a":2}\n')

    def test_independent_preview_does_not_keep_excluded_text(self) -> None:
        source = document(chapter('<p>A<note>hidden</note>B</p>'))
        state = _validate_structure(source, require_source_shape=False)
        note = next(element for element in state.paragraphs[0].iter() if element.tag.endswith("note"))
        self.assertEqual(_independent_projected_content(note), "")


if __name__ == "__main__":
    unittest.main()
