# Supplementary source availability

Check date: 2026-09-29.
This check covers two missing inputs from earlier audits.
It used author and repository records. It did not execute released code.

## Caspari–Faccini supplement

The [OSF preprint record](https://api.osf.io/v2/preprints/8b4we_v1/) still identifies version 1 of *A Key to the Voynich Manuscript*.
Its [file listing](https://api.osf.io/v2/preprints/8b4we_v1/files/osfstorage/) contains only the preprint PDF.
The supplementary [project file listing](https://api.osf.io/v2/nodes/aq7nj/files/osfstorage/) and [component listing](https://api.osf.io/v2/nodes/aq7nj/children/) contain no entries.
The [Max Planck record](https://pure.mpg.de/rest/items/item_3644902) lists the preprint PDF and an empty file item.

These records provide no supplementary reading rules or vocabulary.
The [earlier decision](anchor-audit.md#casparifaccini-reading-rule-check) to stop full automatic replication remains unchanged.
This access result does not establish that no supplement exists elsewhere.

## Zodiac answer files

Zenodo published [version 1.1](https://doi.org/10.5281/zenodo.22874165) on 2026-09-21.
The latest-version endpoint for concept record `21761982` returned record `22874165`.
The new [replication archive](https://zenodo.org/api/records/22874165/files/voynich_replication_v1.zip/content) contains 333 entries and 3,271,637 bytes.
Its SHA-256 is `c01688ebd93e9f6dc99a06dee26f13e27f71054c6672a0cbcc43af32f2865fc2`.

The archive adds answer CSV files for rounds 5 through 9.
Its `voynich_replication/README.md` states that a July 2026 cleanup deleted CSV files for rounds 1, 2, and 4.
The README identifies archived vectors as the remaining source for those rounds.
The packaged evaluation script still requires round 1 and round 2 input files that the archive does not contain.

The new package does not restore the original answer-to-image joins.
The [panel-control result](../../reports/ZODIAC_PANEL_CONTROL.md) remains conditional on the earlier released sequence and table vectors.
This check does not test the new rounds or replace the fixed input to that result.

## Reproduction

The local record keeps the downloaded archive and API responses with their hashes.
The [source manifest](source-availability-2026-09-29.json) records the request URLs and response hashes.
The primary agent confirmed the two empty OSF listings, the latest Zenodo record, the archive hash, and the relevant README passage.
These checks provide source-access evidence. They do not identify a manuscript key, label meaning, or translation.
