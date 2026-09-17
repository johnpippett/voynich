# Source-bound cyclic quotient control review

Date: 2026-09-17

This review covers the source-bound control runner and its stated protocol. It
uses synthetic inputs only. It does not read a reference corpus or a
manuscript stream.

The first review used `control_study.py` hash
`7b9c2487eead3a320453845e88498f9c1bdf410bf66c13567bedb6aff815eaa3` and test
hash `7a07106d75c4a7e5262312f095e2832aa235ee1fcff1ba8dd6e9a0f595514124`.
This update reviews the final child hashes recorded below.

## Findings

### 1. Earlier finding: core evidence was replaced during source binding

The first snapshot called `_bind_source_records` after `run_study`. That
function changed `quotient.json` and replaced `fit.json` and `fit.keys.json`.
This conflicted with the immutable quotient and exclusive key requirements.

The final snapshot removes that writer. `run_corpus` now keeps the pure
quotient, fit, and key bytes from `run_study`. It validates the durable key,
then opens the test stream. The updated synthetic success test saves each
pure record and checks its bytes and hash after diagnostics.

**Resolution: passed.** Source and freeze identity now stay in diagnostics
and the outer supervisor receipt. The pure fit hash remains the pure fit hash.

### 2. Earlier finding: an uncertified feasible solver result reached the test boundary

The first review treated test encryption after a feasible budget stop as a
protocol failure. The protocol text does not forbid this sequence. It says
that a budget-exhausted lower bound is not certified and that the run must
report an inconclusive status unless the solver certifies the score.

The final child keeps the key durable before test encryption. It returns
`status=budget_exhausted`. Its diagnostics retain `fit_status=budget_exhausted`,
`completion=incomplete_search`, and `score_certified=false`.

**Resolution: no protocol violation found.** The word `complete` in the
diagnostic record means that post-fit diagnostics completed. It does not mean
that the solver score is certified. The outer `complete` status means that
output processing completed. Readers must use the fit status and diagnostic
fields to assess score certification.

### 3. Freeze gate boundary

`run_frozen.verify_freeze_manifest` hashes the allow-listed files before it
launches the child. `run_controls` calls this check before child imports or
source parsing. This satisfies the required public-entry hash order.

`control_study.run_corpus` does not repeat this byte check. Its
`load_freeze_metadata` function checks the freeze record shape and records its
raw hash. A direct call to `control_study` can therefore bypass the outer
gate. This is a boundary limitation, not a failure of the canonical public
entry. Keep the child command behind the verified outer entry. Do not describe
the child module as a stand-alone freeze gate.

## Checks that passed

The fit receives train words and validation ciphertext only. The validation
plaintext is used to make the synthetic validation ciphertext, and the test
plaintext is used only after the saved key passes validation.

The capacity-one class map is checked for complete class coverage, injective
letters, and a matching induced observed-unit map. The objective uses counts
from transformed validation words. Test scoring counts mapped positions,
unmapped positions, complete words, and finite-lexicon hits with explicit
denominators.

The saved key is durable before test encryption. Quotient ambiguity and
quotient infeasibility return before test encryption. Fit infeasibility also
returns before test encryption. A malformed saved key raises before test
encryption. The corrected Latin validation stream pin in the runner is
`eb03e98b086b9f8bc883f349afaee968bfeaeee8c95be5f66bec320e54b419b2`.

## Synthetic boundary checks

| Case | Result | Encryption calls | Diagnostic file |
| --- | --- | --- | --- |
| Certified feasible fit | `bound_certified` | validation, test | present |
| Ambiguous quotient | `abstained` | validation | absent |
| Malformed key binding | `ValueError` | validation | absent |
| Feasible budget stop | `budget_exhausted` | validation, test | present; incomplete status retained |

The repository suite passed all six child tests and all eight outer supervisor
tests. A separate synthetic run covered the certified, abstention,
malformed-key, and budget-inconclusive cases.

## Reviewed source hashes

| File | SHA-256 |
| --- | --- |
| `experiments/cyclic_quotient/control_study.py` | `231f0488eb97d809d898dc6ece3e0bd8bdc166849b5531d42b1885f98ad61bc5` |
| `experiments/cyclic_quotient/test_control_study.py` | `df3e22ccc2a18d5fcd96b09820aed9fd1112d3a8a74c1520fbf0836cbbe6a9ee` |
| `experiments/cyclic_quotient/study.py` | `69ee883e0d1ca92f95cb96664c018e925836244fde83cfbfd0ce43b4ed79db1d` |
| `experiments/cyclic_quotient/quotient.py` | `8186751798ae74884d0071735612844ab65819e90d9e9a4aadff7b85721f249e` |
| `experiments/cyclic_quotient/run_frozen.py` | `0dfff592d77fe0d810124d5fc39d390ca9f888b6e3843d0d1744a11a27a542d2` |
| `experiments/cyclic_pairing/study.py` | `73f18f96627d47d5a8d02e7499af726d69f0bc5f65c825bfc4b61b756b7db0b3` |
| `experiments/homophonic/controls.py` | `4845d1de4e766c5d63b23919bab2715db24b431ba502112494e477a1740fd896` |
| `src/voynich/reference.py` | `97e173c761b137d3653a827315b62a68af3e96abd189afdecc46e9759d2b94d9` |
