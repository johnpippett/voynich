"""Check certificate scope and the decision-before-test boundary."""

from collections import Counter
from contextlib import redirect_stdout
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.homophonic.controls import encrypt_words, seeded_control_key
from experiments.identifiability import run_assessment as runner
from experiments.lexicon.run_pilot import canonical_bytes, canonical_hash, objective_weights


def fixture():
    words = {"train": ["ab", "ba"], "validation": ["ab", "ba"], "test": ["aa", "ab", "ba"]}
    planted = seeded_control_key("cap2", 7000)
    cipher = {split: encrypt_words(value, planted) for split, value in words.items()}
    counts = Counter(cipher["validation"])
    _weights, tokens, types, denominator = objective_weights(counts)
    units = {unit for word in counts for unit in word}
    key = {"family": "cap2", "seed": 7000,
           "key": {unit: planted["cipher_to_plain"][unit] for unit in units}}
    report = {
        "kind": "synthetic_reference_control", "family": "cap2", "seed": 7000,
        "metadata": {"language": "latin_llct"},
        "solver": {"score": denominator, "score_certified": True,
                   "lower_bound": denominator, "upper_bound": denominator, "config": {"capacity": 2}},
        "objective": {"denominator": denominator},
        "stream_sha256": {
            **{f"plaintext_{split}": canonical_hash(value) for split, value in words.items()},
            **{f"cipher_{split}": canonical_hash(value) for split, value in cipher.items()},
        },
        "train_lexicon": {"sha256": canonical_hash(sorted(set(words["train"])))},
        "fit_input": {"sha256": canonical_hash(cipher["validation"]), "token_count": tokens,
                      "type_count": types, "unit_count": len(units)},
        "key_record_sha256": canonical_hash(key),
    }
    return report, key, words


class AssessmentRunnerTests(unittest.TestCase):
    def test_fit_scope_and_certificate_match_without_test_access(self):
        report, key, words = fixture()
        class ForbiddenTest:
            def __iter__(self):
                raise AssertionError("test data entered problem preparation")
        words["test"] = ForbiddenTest()
        problem, selected, target, certificate = runner.prepare_problem(report, key, words)
        self.assertEqual(target, problem.root_bound)
        self.assertEqual(selected, key["key"])
        self.assertEqual(certificate["problem_fingerprint"], problem.problem_fingerprint)

    def test_changed_fit_inputs_and_uncertified_scores_fail(self):
        report, key, words = fixture()
        for change in ("stream", "lexicon", "bounds", "capacity", "key"):
            with self.subTest(change=change):
                r, k, w = copy.deepcopy((report, key, words))
                if change == "stream":
                    w["validation"].reverse()
                elif change == "lexicon":
                    w["train"].append("bb")
                elif change == "bounds":
                    r["solver"]["upper_bound"] += 1
                elif change == "capacity":
                    r["solver"]["config"]["capacity"] = 1
                else:
                    k["key"].pop(next(iter(k["key"])))
                with self.assertRaises(ValueError):
                    runner.prepare_problem(r, k, w)

    def test_decisions_exist_before_test_is_iterated_and_counts_cover_all(self):
        report, key, words = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "new-run"
            original = words["test"]
            class GuardedTest:
                def __iter__(self):
                    decision = json.loads((output / "decisions.json").read_bytes())
                    self_count = len(key["key"])
                    if len(decision["query_sha256"]) != self_count:
                        raise AssertionError("not all decisions were fixed")
                    return iter(original)
            words["test"] = GuardedTest()
            with redirect_stdout(io.StringIO()):
                result = runner.run_assessment(report, key, words, output_dir=output, node_budget=50)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(sum(result["decisions"]["counts"].values()), len(key["key"]))
            diag = result["post_query_diagnostics"]
            self.assertEqual(sum(x["test_positions"] for x in diag.values()), 6)
            self.assertEqual(sum(x["test_errors"] for x in diag.values()), 0)
            self.assertEqual(runner.sha256_path(output / "decisions.json"), result["decisions_sha256"])
            with self.assertRaises(FileExistsError):
                runner.run_assessment(report, key, words, output_dir=output)

    def test_missing_query_preserves_partial_run_without_test_scoring(self):
        report, key, words = fixture()
        class ForbiddenTest:
            def __iter__(self):
                raise AssertionError("incomplete query run scored test data")
        words["test"] = ForbiddenTest()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "partial"
            with self.assertRaisesRegex(ValueError, "omitted"):
                runner.run_assessment(report, key, words, output_dir=output,
                                      query_iterator=lambda *args, **kwargs: iter(()))
            self.assertTrue((output / "run.json").exists())
            self.assertFalse((output / "decisions.json").exists())
            self.assertFalse((output / "assessment.json").exists())

    def test_changed_test_stream_fails_after_fixed_decisions(self):
        report, key, words = fixture()
        words["test"] = ["bb"]
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "wrong-test"
            with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "test stream mismatch"):
                runner.run_assessment(report, key, words, output_dir=output, node_budget=0)
            self.assertTrue((output / "decisions.json").exists())
            self.assertFalse((output / "assessment.json").exists())

    def test_unobserved_test_units_remain_unassigned_and_counted(self):
        report, key, words = fixture()
        words["test"] = ["z"]
        report["stream_sha256"]["plaintext_test"] = canonical_hash(words["test"])
        report["stream_sha256"]["cipher_test"] = canonical_hash(
            encrypt_words(words["test"], seeded_control_key("cap2", 7000)))
        with tempfile.TemporaryDirectory() as temporary, redirect_stdout(io.StringIO()):
            result = runner.run_assessment(report, key, words,
                                          output_dir=Path(temporary) / "unobserved", node_budget=0)
        self.assertEqual(result["post_query_diagnostics"]["unobserved"], {
            "unit_count": 1, "unit_assignments_correct": 0,
            "test_positions": 1, "test_correct": 0, "test_errors": 1,
        })

    def test_published_records_and_code_are_checked_before_use(self):
        report, key, _words = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "source.py").write_text("synthetic source\n")
            protocol = root / "docs/plans/visual-homophonic-pilot.md"
            protocol.parent.mkdir(parents=True)
            protocol.write_text("synthetic protocol\n")
            report["code_sha256"] = {"source.py": runner.sha256_path(root / "source.py")}
            report["protocol_sha256"] = runner.sha256_path(protocol)
            path = root / runner.BASELINE
            path.parent.mkdir(parents=True)
            path.write_bytes(canonical_bytes(report))
            path.with_suffix(".keys.json").write_bytes(canonical_bytes(key))
            with patch.object(runner, "BASELINE_SHA256", canonical_hash(report)):
                actual, actual_key = runner.verify_baseline_files(root)
                self.assertEqual(actual, report)
                self.assertEqual(actual_key, key)
                (root / "source.py").write_text("changed source\n")
                with self.assertRaisesRegex(ValueError, "source hash mismatch"):
                    runner.verify_baseline_files(root)


if __name__ == "__main__":
    unittest.main()
