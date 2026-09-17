# Publication check

Audit date: 2026-09-16.

This record describes the original publication audit.
The [later attribution correction](<../../wiki/30-39 Integrations & Tooling/32 Integration Notes/32.02 Commit Attribution.md>) supersedes its Git identity statement.

The audit covered the 43 paths in the staged tree. It checked staged names and
content only. It made no network request and did not publish the repository.

The local Git identity was `Voynich Research` with the GitHub no-reply address.
The staged content has no personal email address, phone contact, credential
marker, private key block, access token, or secret assignment. The public
repository URL in `README.md` is allowed: `https://github.com/johnpippett/voynich`.

The staged tree contains no `data/raw/` files, raw IVTFF bytes, full parsed
record files, or result directories. The source manifest contains source
metadata and hashes. The folio source file contains Yale metadata and public
Yale URLs. Its local asset names refer to the Yale folio images. It contains no
user image asset or user attachment metadata. The staged `.gitignore` excludes
`assets/`, `data/raw/`, and `results/`.

The first review flagged two absolute paths in an export test fixture:

- `tests/test_export.py:24` and `tests/test_export.py:35` contain absolute local
  paths used to test path removal. They were synthetic examples, not source
  evidence. The final fixture uses `/synthetic/private/fixture.txt`.

The final pre-commit check covered 51 prospective public files, including the
generated reports. All 28 local Markdown links resolved. All JSON files parsed.
The source-code hashes matched the three aggregate reports. The archived run
protocol matched the recorded design hash.

The final content scan found no user paths, attachment identifiers, private key
blocks, or GitHub token patterns. The aggregate reports contain no raw text,
model vocabulary, complete fitted models, or absolute paths. This check covers
the inspected files and patterns. It is not a guarantee against every possible
disclosure.

These checks preceded the public push. Remote publication and clean-clone
checks require separate verification.
