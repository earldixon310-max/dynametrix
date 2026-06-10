# OVP v0.2 — Reference Judge/Harness/Guard Template

Reference implementation of `docs/standards/OVP_v0.2_TEMPLATE_HARDENING_DRAFT.md` (rev7). Per §6, **this code + its test suite — not the spec prose — is the artifact the two-pass lock bar attaches to.** The spec argues the properties; these tests *execute* them.

**Claim scope (R-1):** every guarantee is **accident-prevention**, never tamper-resistance. A forged tag or an edited-out guard defeats it; that residual is the signature/human-trust layer's job, disclaimed by design.

## Architecture — `(sealed-loader, synthetic-loader, shared compute-core)`

- `compute_core.py` — the **pure, IO-free, seeded** sealed computation. Imported by **both** judge and harness, so H1's un-smoke-testability (the judge can't run pre-lock) is resolved: the harness exercises this exact code on synthetic data.
- `judge_template.py` — sealed-loader (H1-gated) + shared core. The guard is the **first action** in `main()`, before any candidate load; the full closure chain is wired as one unit.
- `smoke_template.py` — synthetic-loader + shared core, under the **closed-world** input guard. H1-exempt; reads no candidate; writes no results.
- `ovp_guard.py` — the guards: `assert_locked_or_refuse` (H1), `output_exists_or_refuse` (single-execution), `verify_input_hashes` (right-data), `closed_world_io` (B2 deny-by-default).

## The locked set (per study)

In the atomic lock commit, hashed in the manifest: **pre-registration, every sealed-path source file (the judge + the shared `compute_core.py` + `ovp_guard.py`), the smoke harness, the manifest, and `.gitattributes`** (the `-text` filter-free pin). **rev2 correction (cold-pass-A finding 1):** H1 verifies *every* sealed-path source at runtime, not just the judge — so an accidental post-lock edit to the shared core refuses instead of silently corrupting the verdict. The earlier "five files" count omitted the imported core and the guard; the locked set is "pre-reg + manifest + `.gitattributes` + *all* sealed-path sources + harness."

## Instantiate a study

1. Copy `judge_template.py`, `smoke_template.py`, `compute_core.py`, `ovp_guard.py`, `.gitattributes`.
2. Fill `compute_core.compute_sealed` with the study's estimator (keep it **pure + seeded**).
3. In the judge: pin `LOCK_TAG`, `LOCKED_PATH`, `OUT_PATH`, `EXPECTED_INPUT_SHA256`, and **`SEALED_SOURCES`** (every source file on the sealed path — judge + core + guard; a lint should assert it covers all sealed-path imports) **as constants in the file**; implement `sealed_loader`. (`EXPECTED_INPUT_SHA256` empty ⇒ the judge refuses.)
4. In the harness: pin the synthetic seed (or the hashed fixture path); never read the candidate.
5. Lock: atomic commit of all sealed-path sources + harness + manifest + `.gitattributes`, then `git tag -s <LOCK_TAG>`. Run the judge **once**.

## Run the tests

```
python3 test_ovp_guard.py      # 14 unit properties (incl. widened closed-world, empty-input refuse)
python3 test_integration.py    # 3 end-to-end (smoke pre-lock; judge across lock; post-lock core edit REFUSES)
python3 test_ovp_attest.py     # 7 attestation (tiers/temporal/claim-scope/binding/tamper/honest-label)
```
24 properties total, all asserted by execution (rev2).

## Properties verified by execution (mapping to spec + cold-pass findings)

| # | property | spec |
|---|---|---|
| 1 | locked + byte-identical computes; **fixpoint** (tag named in bytes, OID resolved dynamically) | §1 |
| 2 | pre-lock (no tag) **refuses** | §1 |
| 3 | working bytes modified after lock **refuses** | §1 |
| 4 | not a git work tree **refuses** (fail-closed) | §1 B1 |
| 5 | git binary absent **refuses** (fail-closed) | §1 (3a) |
| 6 | `autocrlf` CRLF work-tree **passes** via filter-aware compare (raw byte hash would fail) | §1 (2/3a) |
| 7 | `-text`-pinned path **passes** (deterministic) | §1 (3b) |
| 8 | moved byte-identical **passes**; moved-AND-modified **refuses** (hashes the running bytes) | §1 (3c) |
| 9 | output-exists: first run permits, same-output re-run **refuses** | §1b |
| 10 | input-hash: pinned match permits, mismatch **refuses** | §1b (3c) |
| 11 | closed-world harness: fixture open OK, **absolute-path read refuses** | §2 B2 (3a/3b/3d) |
| 12 | `info/attributes` is out-of-locked-set — the R-1 accident-model boundary | §1 (3d) |
| 13 | smoke runs pre-lock, exits 0, writes **no** results | §1c/§2 |
| 14 | judge end-to-end: pre-lock refuses, **post-lock computes** | §1/§1c |

**Lesson surfaced by execution (not prose):** numpy's lazy submodule imports open `.pyc` files, which the closed-world audit correctly refuses if they happen *inside* the data phase — so the harness must **warm libraries before** the closed-world block. This is exactly the "benign library-load IO vs data IO" distinction rev7 flagged as a reference-suite assertion; the test that caught it is why §6 is right that execution beats prose here.

## The §3 attestation tool (`ovp_attest.py`)

Signed, study-bound, **additive** attestation (zero re-tagging → immutability preserved) for a study's smoke harness. `build_attestation` emits a structured record with the two mandatory distinctions; `verify_attestation` re-derives the verifiable claims from the repo. A real run creates the additive record as a **signed** tag (`git tag -s …-harness-attest <lock-commit>`); signature authenticity is the separate `git tag -v` human-trust step.

| # | property | spec |
|---|---|---|
| A | anchored → **proof-grade**; anchoring VERIFIED, **binding** VERIFIED (recorded sha256 == actual blob), claim-scope well-formed | §3 |
| B | unanchored grandfathered (harness after lock) → **attestation-grade**, temporal "not before lock" | §3 (3d) |
| C | unanchored, harness blob in history at/before lock date → temporal bound **holds** | §3 (3d) |
| D | forged "anchored" → **CONTRADICTED** (blob not in lock tree) | §3 |
| E | `non_execution` over-claimed verifiable → **CONTRADICTED** | §3 |
| F | recorded sha256 ≠ actual blob bytes → **binding CONTRADICTED** (rev2, cold-pass-A finding 3) | §3 |
| G | candidate-reading harness → source-synthetic label **HONEST** ("read-the-blob, NOT machine-confirmed"), never rubber-stamped VERIFIED (rev2) | §3 |

**rev2 honesty fix (cold-pass-A finding 3):** `verify_attestation` now cross-checks the recorded sha256 against the actual blob bytes (binding), and does **not** machine-claim source-synthetic — synthetic-ness is a read-the-blob property, so the tool reports the *binding* as verified and the synthetic claim as human-readable, never rubber-stamping a candidate-reading harness.

## Scope notes (honest)

- **Built + tested (24 properties):** H1 over all sealed-path sources; the full closure chain (H1 + output-exists + input-hash + closed-world); the `(sealed-loader, synthetic-loader, shared-core)` factoring; the judge/harness skeletons; **the §3 signed additive attestation tool**.
- **Closed-world is IO-closed, not merely file-open-closed (rev2, cold-pass-A finding 2):** `closed_world_io` denies `open` outside the allowlist **and** directory enumeration, network, subprocess, and exec audit events during the data phase. Residual (R-1 reference-suite assertion, not a guarantee): C-level libc reads in an arbitrary extension that bypass the audit events — numpy's own readers raise them and are covered.
- **Documented boundary, not mechanized:** the hostile-`info/attributes` lossy-filter case is out-of-model tamper (R-1); test 12 asserts the boundary.
- **Human-trust layer (by design, R-1, not this code's job):** git signature verification (`git tag -v`) on both the lock tag and the attestation tag — the identity layer the guards explicitly disclaim. The *signed* path (`git tag -s`) is exercised by the operator; tests use `git tag -a` and verify content, not signature.
- **Known scoped limitation (cold-pass-A):** the input-hash check verifies a path on disk; coupling it to the exact bytes `sealed_loader` loads (closing the TOCTOU) is left to the study's loader, which should hash the bytes it actually reads.

## rev2 — cold-pass-A disposition (one reader, blocker; reset to two fresh passes)

cold-pass-A reader #1 ran all suites green, then *demonstrated* three findings by probe. All folded: **(1)** H1 now covers every sealed-path source — the post-lock-core-edit wrong-compute is reproduced as a refusal (integration test 17); **(2)** closed-world widened to IO-closed (guard test 14); **(3)** attestation binding cross-check + honest source-synthetic label (attest tests F/G). Secondaries: empty input-hash refuses (test 13); test-6 raw-hash divergence now asserted. A blocker resets the count → rev2 re-routes **two fresh** passes; author cannot clear.
