# Reproduce the name check

Use the repository revision that publishes this report.
The script checks the parser, plan, and source hashes before parsing the manuscript.
Use Python 3 and the standard library.

From the repository root, make the input directories.

```sh
mkdir -p data/raw results/solar-lunar-name-check-v1
cp docs/plans/solar-lunar-name-check-v1.md results/solar-lunar-name-check-v1/plan.md
```

Get the two public transcriptions.
Keep any existing files that already have the hashes in the plan.

```sh
curl --fail --location https://www.voynich.nu/data/ZL3b-n.txt -o data/raw/ZL3b-n.txt
curl --fail --location https://www.voynich.nu/data/IT2a-n.txt -o data/raw/IT2a-n.txt
```

Run the fixed calculation with a new output path.
The script refuses to replace an existing output.

```sh
PYTHONPATH=src python scripts/check_solar_lunar_names.py results/solar-lunar-name-check-v1/replay.json
sha256sum results/solar-lunar-name-check-v1/replay.json
```

The expected SHA-256 is `3d29e4100d51f24f16a82561adcc839179fd71505d84738cb0ee3af7201c6f66`.
All twelve reported intersections are empty.
The output contains manuscript text and must remain outside public commits.
The [public receipt](result.json) contains only counts and source references.

The two executions before publication gave identical files.
The result is conditional on the selections and readings in the [report](../SOLAR_LUNAR_NAMES.md).
