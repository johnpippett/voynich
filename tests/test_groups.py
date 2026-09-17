import hashlib
import json
import pathlib
import unittest

from voynich.groups import group_id, grouping_config, split_bucket, split_name


PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]


class GroupTests(unittest.TestCase):
    def test_manifest_components_cover_all_known_numeric_folios(self):
        config = grouping_config()

        self.assertEqual(config["version"], "ivtff-bifolio-metadata-v3")
        self.assertEqual(config["group_count"], 52)
        self.assertEqual(config["numeric_folio_count"], 102)
        self.assertEqual(len(config["components"]), 52)
        mapped = {}
        for component in config["components"]:
            group = component["group"]
            self.assertEqual(group, str(component["representative_numeric_folio"]))
            for number in component["numeric_folios"]:
                mapped[number] = group_id(f"f{number}r")
        self.assertEqual(set(mapped), set(map(int, config["folio_map"])))
        self.assertEqual(set(mapped.values()), {component["group"] for component in config["components"]})

    def test_each_bifolio_component_stays_in_one_group_and_split(self):
        config = grouping_config()
        for component in config["components"]:
            groups = {group_id(f"f{number}v1") for number in component["numeric_folios"]}
            buckets = {split_bucket(group) for group in groups}
            self.assertEqual(groups, {component["group"]})
            self.assertEqual(len(buckets), 1)

    def test_same_b_number_in_different_quires_remains_distinct(self):
        self.assertNotEqual(group_id("f1r"), group_id("f9r"))
        self.assertNotEqual(group_id("f69r"), group_id("f71r"))

    def test_rosettes_alias_joins_the_manifest_group(self):
        self.assertEqual(group_id("f85r1"), group_id("f86v3"))
        self.assertEqual(group_id("fRos"), "85")
        self.assertEqual(split_bucket("86"), split_bucket("85"))

    def test_split_hash_uses_the_versioned_salt(self):
        config = grouping_config()
        self.assertEqual(config["split_hash_salt"], "voynich-bifolio-408-v3:")
        digest = hashlib.sha256((config["split_hash_salt"] + "1").encode()).digest()
        self.assertEqual(split_bucket("1"), int.from_bytes(digest[:8], "big") % 10)
        self.assertEqual(split_bucket("7"), split_bucket("2"))
        self.assertEqual(split_name(0), "test")
        self.assertEqual(split_name(1), "test")
        self.assertEqual(split_name(2), "validation")
        self.assertEqual(split_name(9), "train")

    def test_config_records_manifest_evidence_and_limits(self):
        config = grouping_config()
        manifest_path = PROJECT_ROOT / config["manifest_path"]
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes)
        self.assertEqual(
            config["manifest_sha256"],
            "998cb3d6c8327ff0bdf786d52968fa3bec9f5fa9b05ba7ae56065fc9639fad72",
        )
        self.assertEqual(config["manifest_sha256"], hashlib.sha256(manifest_bytes).hexdigest())
        self.assertTrue(config["complete_provider_coverage"])
        self.assertFalse(config["independent_conservation_verification"])
        self.assertEqual(
            manifest["cross_corpus_agreement"]["shared_page_QB_mismatches"], []
        )
        self.assertEqual(
            config["evidence"]["cross_corpus_agreement"]["shared_page_QB_mismatches"],
            manifest["cross_corpus_agreement"]["shared_page_QB_mismatches"],
        )
        self.assertTrue(manifest["cross_corpus_agreement"]["all_ZL3b_locus_records_have_QB"])
        self.assertTrue(manifest["cross_corpus_agreement"]["all_IT2a_locus_records_have_QB"])
        self.assertIn("PDF pages 19-20", config["evidence"]["format_specification"]["location"])
        self.assertEqual(config["legacy_foldout_metadata"]["confirmed_cross_number_foldout"], [85, 86])

    def test_config_is_returned_as_an_independent_copy(self):
        first = grouping_config()
        first["components"][0]["numeric_folios"].append(999)
        first["folio_map"]["1"] = "changed"
        first["evidence"]["cross_corpus_agreement"]["shared_page_QB_mismatches"].append("bad")

        second = grouping_config()
        self.assertNotIn(999, second["components"][0]["numeric_folios"])
        self.assertEqual(second["folio_map"]["1"], "1")
        self.assertEqual(second["evidence"]["cross_corpus_agreement"]["shared_page_QB_mismatches"], [])

    def test_unknown_folio_identifiers_are_rejected(self):
        for value in ["", "unknown", None, "abc85r", "f12r", "f74r", "f999r", "fRos2"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                group_id(value)

    def test_invalid_groups_and_buckets_are_rejected(self):
        with self.assertRaises(ValueError):
            split_bucket("74")
        with self.assertRaises(ValueError):
            split_bucket("Q/1")
        with self.assertRaises(ValueError):
            split_name(-1)
        with self.assertRaises(ValueError):
            split_name(10)


if __name__ == '__main__':
    unittest.main()
