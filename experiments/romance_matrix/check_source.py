"""Check fixed source functions on artificial inputs.

The command runs no app startup code and reads no manuscript file.
It writes one new result file.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import re

HASHES = {
    "voynichapp.py": "3b617100a9f2756dc9c59dda8be011f1ca70f20bd3d000ee626728fe08b64bc4",
    "voynichdatos.py": "591a270bd04ac31091606561a453dedafc835fcf31910c856e2eb389a87f321b",
}
CASES = (
    ("pui cuta", "pui cuta", "plant bark"),
    ("f", "f", "its"),
    ("ff", "ff", "its"),
    ("fff", "fff", "plant"),
    ("ffff", "ffff", "[ffff]"),
    ("qok", "quoqu", "whereby"),
    ("eee", "ei", "if"),
    ("h", "h", "its"),
)
REVERSED_EXPECTED = {"f": "if", "ff": "if", "fff": "air",
                     "pui cuta": "plant bark", "ffff": "[ffff]",
                     "qok": "whereby"}


def read_source(directory, name):
    data = (directory / name).read_bytes()
    if hashlib.sha256(data).hexdigest() != HASHES[name]:
        raise ValueError("Source SHA-256 mismatch: " + name)
    return ast.parse(data, filename=name)


def dictionary(tree, name):
    matches = [node for node in tree.body if isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == name
                       for target in node.targets)]
    if len(matches) != 1:
        raise ValueError("Expected one dictionary assignment: " + name)
    result = ast.literal_eval(matches[0].value)
    if not isinstance(result, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in result.items()):
        raise ValueError("Expected a string dictionary: " + name)
    return result


def run(directory):
    app = read_source(directory, "voynichapp.py")
    data = read_source(directory, "voynichdatos.py")
    english = dictionary(data, "DICCIONARIO_EN")
    spanish = dictionary(data, "DICCIONARIO_ES")
    selected = [node for node in app.body if isinstance(node, ast.FunctionDef)
                and node.name in {"distancia_levenshtein", "traducir_a_romance"}]
    if len(selected) != 2 or any(node.decorator_list for node in selected):
        raise ValueError("Expected two functions without decorators.")
    namespace = {
        "__builtins__": {"len": len, "range": range, "enumerate": enumerate, "min": min},
        "re": re, "idioma": "English",
        "DICCIONARIO_EN": english, "DICCIONARIO_ES": spanish,
    }
    module = ast.Module(body=selected, type_ignores=[])
    exec(compile(module, "voynichapp.py", "exec"), namespace)
    translate = namespace["traducir_a_romance"]
    distance = namespace["distancia_levenshtein"]
    rows = []
    for text, expected_phonetic, expected_gloss in CASES:
        phonetic, gloss = translate(text)
        if (phonetic, gloss) != (expected_phonetic, expected_gloss):
            raise ValueError("Artificial case disagrees with the fixed expectation.")
        words = []
        for word in phonetic.split():
            scores = {key: distance(word, key) for key in english}
            minimum = min(scores.values())
            ties = [key for key, score in scores.items() if score == minimum]
            words.append({"phonetic": word, "exact_entry": word in english,
                          "minimum_distance": minimum, "tied_keys": ties,
                          "selected_key": ties[0] if minimum <= 3 else None})
        rows.append({"input": text, "phonetic": phonetic, "gloss": gloss, "words": words})
    namespace["DICCIONARIO_EN"] = dict(reversed(list(english.items())))
    reverse_rows = []
    for text, expected in REVERSED_EXPECTED.items():
        phonetic, gloss = translate(text)
        if gloss != expected:
            raise ValueError("Dictionary-order case disagrees with the fixed expectation.")
        reverse_rows.append({"input": text, "phonetic": phonetic, "gloss": gloss})
    return {
        "source_sha256": HASHES,
        "dictionary_entries": {"english": len(english), "spanish": len(spanish)},
        "shortest_english_keys": [key for key in english if len(key) == min(map(len, english))],
        "original_order": rows,
        "reversed_dictionary_order": reverse_rows,
        "all_expectations_match": True,
        "app_startup_executed": False,
        "manuscript_inputs_read": False,
        "limit": "These checks describe program behavior. They do not validate word meanings.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("The output path exists.")
    result = run(args.source_directory)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False)
        stream.write("\n")


if __name__ == "__main__":
    main()
