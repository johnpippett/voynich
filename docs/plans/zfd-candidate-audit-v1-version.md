# Execution path check

Date: 2026-09-29. No decoder execution preceded this check.

The original plan remains unchanged. Its SHA-256 is `2331bb8c7a5dc6df26771ec06bc33558fa34315875105e436d1dc2e09ce85b24`.

At commit `3f030a9293b8db15dc2c7b0d0e7c703e71711f62`, the README corpus command calls `06_Pipelines/regenerate_corpus.py`.
That file imports `ZFDDecoder` from `zfd_decoder_v2.py`.
The decoder uses `08_Final_Proofs/Master_Key/unified_lexicon_v3.json` by default.
The corpus command therefore uses the decoder and lexicon specified in the original plan.
The older decoder filename does not identify an obsolete corpus path.

The source SHA-256 for `regenerate_corpus.py` is `ebf24d65d9a4909d5954f2e5fa0725752d074119a15c2c80108f39510f276f46`.

The separate blind-test command uses `ZFDPipeline`, two CSV lexicons, and its own configuration.
The planned checks do not test that separate pipeline or reproduce its statistical claims.
The planned checks also do not regenerate the complete corpus.

The implementation worker paused before implementation or source execution while this path was checked.
The coordinator now authorizes the unchanged fixed plan.
