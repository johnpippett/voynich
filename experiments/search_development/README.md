# Bounded Italian control development

This experiment measures a tighter root upper bound and two improved complete maps.
It uses the inspected Old Italian control with capacity `2` and encryption seed `7000`.
The [protocol](../../docs/plans/homophonic-search-development-v1.md) fixes its inputs and limits.

The experiment has no manuscript input. It does not score the test partition.
Source loading reads files that contain all three reference partitions.
Only training and validation data enter fitting.

The root calculation groups word types by their smallest cipher unit.
It retains all compatible dictionary candidates.
The local searches start from the two published maps and permit eight accepted improving moves each.

Before a source run, publish the reviewed code, protocol, and external freeze manifest.
Run the fixed supervised entry point from that published revision:

```sh
python -m experiments.search_development.run_frozen
```

The supervisor checks elapsed time and samples child resident memory.
The memory guard can be exceeded between samples. It is not a kernel memory limit.
Read the supervision receipt before interpreting any numeric output.
Keep incomplete output local when supervision fails.

A completed run uses status `development_only`. This status is not an exact-recovery gate.
A smaller finite optimization gap does not establish a manuscript key, language, or translation.
