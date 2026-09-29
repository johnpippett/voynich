# Reproduce the Hebrew source check

Use Python 3 and its standard library.
Run these commands from the repository root.

```sh
mkdir -p results/hebrew-key-replay/sources
curl --fail --location https://raw.githubusercontent.com/antenore/voynich-toolkit/cb137630762908517636b7f9ffb98bc5fe0dc05e/src/voynich_toolkit/full_decode.py -o results/hebrew-key-replay/sources/full_decode.py
curl --fail --location https://raw.githubusercontent.com/antenore/voynich-toolkit/cb137630762908517636b7f9ffb98bc5fe0dc05e/src/voynich_toolkit/crib_attack.py -o results/hebrew-key-replay/sources/crib_attack.py
python scripts/check_hebrew_key_source.py results/hebrew-key-replay/sources docs/plans/hebrew-key-check-v1.md results/hebrew-key-replay/result.json
sha256sum results/hebrew-key-replay/result.json
```

The expected output has eleven passing decoder cases and five passing prompt checks.
Its SHA-256 is `fb6255da4463856d3aa497b8d594ac4d674f5ccbea314142e4d887f339c5e5ef`.
Use a new output path for another run.
The checker refuses an existing output and rejects changed source or plan bytes.

The checker executes only three selected functions and reads their literal configuration.
It does not import the complete external modules or call a language-model service.
An empty Italian-output table is sufficient for this check of Hebrew ASCII output.
The check does not test Italian output or the legacy decoder mode.

Read the [fixed plan](../../docs/plans/hebrew-key-check-v1.md), [result](result.json), and [verification record](verification.json).
The [source record](sources.json) gives the captured files and hashes.
The [report](../../docs/research/hebrew-key-audit-2026-09-29.md) states the meaning and limits of these software checks.
