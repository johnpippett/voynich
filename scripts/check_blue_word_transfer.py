"""Count exact key tokens outside the fixed plant-feature groups."""

import argparse
import ast
from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "docs/plans/blue-word-transfer-v1.md": "bfd6126b2f1420dd576dae6f46f5bffc1b7187a88c5f82c0b04ae31a1e6a48a8",
    "src/voynich/groups.py": "15b77e967ce296634a36a3deacba660c14a4d4615c99597949b5586d682bdef0",
    "data/bifolio_manifest.json": "998cb3d6c8327ff0bdf786d52968fa3bec9f5fa9b05ba7ae56065fc9639fad72",
}
ROLES = {"plant_features", "color_tags", "corpus"}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def literal_map(data, name):
    tree = ast.parse(data.decode("utf-8"))
    assignments = []
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                assignments.append(node.value)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == name:
                assignments.append(node.value)
    if len(assignments) != 1:
        raise ValueError("Expected one literal assignment for " + name)
    value = ast.literal_eval(assignments[0])
    if not isinstance(value, dict) or not value:
        raise ValueError("Expected a nonempty map for " + name)
    if any(not isinstance(folio, str) or not isinstance(tags, dict) for folio, tags in value.items()):
        raise ValueError("Invalid folio map for " + name)
    return value


def calculate(manifest_bytes, source_root):
    for relative, expected in PINS.items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise ValueError("Project hash mismatch: " + relative)
    spec = importlib.util.spec_from_file_location("blue_word_groups", ROOT / "src/voynich/groups.py")
    groups = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(groups)

    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), dict):
        raise ValueError("Invalid source manifest.")
    if set(manifest["sources"]) != ROLES:
        raise ValueError("The manifest must contain the three fixed source roles.")
    sources = {}
    for role in sorted(ROLES):
        entry = manifest["sources"][role]
        if not isinstance(entry, dict) or any(not isinstance(entry.get(k), str) for k in ("path", "sha256", "url")):
            raise ValueError("Invalid source entry: " + role)
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("Source paths must be relative to the source root.")
        data = (source_root / relative).read_bytes()
        if digest(data) != entry["sha256"]:
            raise ValueError("Source hash mismatch: " + role)
        sources[role] = data

    features = literal_map(sources["plant_features"], "PLANT_FEATURES")
    colors = literal_map(sources["color_tags"], "COLOR_TAGS")
    corpus = json.loads(sources["corpus"])
    if not isinstance(corpus, dict) or not isinstance(corpus.get("sentences"), list):
        raise ValueError("The corpus must have a sentence list.")
    metadata = corpus.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("The corpus must have a folio metadata map.")
    by_folio = defaultdict(list)
    for row in corpus["sentences"]:
        if not isinstance(row, dict) or not isinstance(row.get("folio"), str):
            raise ValueError("Invalid sentence folio.")
        by_folio[row["folio"]].append(row)

    discovery = [{"folio": folio, "group_id": groups.group_id(folio)} for folio in sorted(features)]
    discovery_groups = {row["group_id"] for row in discovery}
    decisions = []
    for folio in sorted(colors):
        group = groups.group_id(folio)
        row = {"folio": folio, "group_id": group, "decision": "excluded"}
        if group in discovery_groups:
            row["reason"] = "discovery_group"
        elif folio not in metadata:
            row["reason"] = "missing_metadata"
        else:
            info = metadata[folio]
            if not isinstance(info, dict) or not isinstance(info.get("illustration"), str):
                raise ValueError("Invalid metadata for " + folio)
            if info["illustration"] != "H":
                row["reason"] = "nonherbal"
            else:
                words = []
                for sentence in by_folio[folio]:
                    part = sentence.get("words")
                    if not isinstance(part, list) or any(not isinstance(word, str) for word in part):
                        raise ValueError("Invalid word list for " + folio)
                    words.extend(part)
                if not words:
                    row["reason"] = "missing_text"
                else:
                    row.update(decision="kept", category="blue_tag" if "B" in colors[folio] else "no_blue_tag",
                               token_count=len(words), key_count=words.count("key"))
        decisions.append(row)

    categories = {}
    for category in ("blue_tag", "no_blue_tag"):
        rows = [row for row in decisions if row.get("category") == category]
        categories[category] = {
            "folio_count": len(rows),
            "distinct_group_count": len({row["group_id"] for row in rows}),
            "token_count": sum(row["token_count"] for row in rows),
            "key_count": sum(row["key_count"] for row in rows),
            "folios_with_key": [row["folio"] for row in rows if row["key_count"]],
        }
    return {
        "schema_version": 1,
        "status": "complete",
        "candidate": "key",
        "plan_sha256": PINS["docs/plans/blue-word-transfer-v1.md"],
        "script_sha256": digest(Path(__file__).read_bytes()),
        "manifest_sha256": digest(manifest_bytes),
        "source_hashes": {role: digest(sources[role]) for role in sorted(ROLES)},
        "grouping": {
            "version": groups.grouping_config()["version"],
            "group_code_sha256": PINS["src/voynich/groups.py"],
            "bifolio_manifest_sha256": PINS["data/bifolio_manifest.json"],
            "independent_conservation_verification": False,
        },
        "discovery_folios": discovery,
        "discovery_groups": sorted(discovery_groups, key=int),
        "folio_decisions": decisions,
        "categories": categories,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("source_root", type=Path)
    parser.add_argument("new_output", type=Path)
    args = parser.parse_args()
    try:
        if args.new_output.exists():
            raise ValueError("Output already exists.")
        result = calculate(args.manifest.read_bytes(), args.source_root)
        serialized = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        with args.new_output.open("x", encoding="utf-8") as output:
            output.write(serialized)
    except (OSError, ValueError, SyntaxError, TypeError) as error:
        print("error: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result["categories"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
