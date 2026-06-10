# OVP v0.2 — Reference Judge/Harness/Guard Template

Reference implementation of `docs/standards/OVP_v0.2_TEMPLATE_HARDENING_DRAFT.md` (rev7). Per §6, **this code + its test suite — not the spec prose — is the artifact the two-pass lock bar attaches to.** The spec argues the properties; these tests *execute* them.

**Claim scope (R-1):** every guarantee is **accident-prevention**, never tamper-resistance. A forged tag or an edited-out guard defeats it; that residual is the signature/human-trust layer's job, disclaimed by design.

## Architecture — `(sealed-loader, synthetic-loader, shared compute-core)`

- `compute_core.py` — the **pure, IO-free, seeded** sealed computation. Imported by **both** judge and harness, so H1's un-smoke-testability (the judge can't run pre-lock) is resolved: the harness exercises this exact code on synthetic data.
- `judge_template.py` — sealed-loader (H1-gated) + shared core. The guard is the **first action** in `main()`, before any candidate load; the full closure chain is wired as one unit.
- `smoke_template.py` — synthetic-loader + shared core, under the **closed-world** input guard. H1-exempt; reads no candidate; writes no results.
- `ovp_guard.py` — the guards: `assert_locked_or_refuse` (H1), `output_exists_or_refuse` (single-execution), `verify_input_hashes` (right-data), `closed_world_io` (B2 deny-by-default).

## The locked set (per study)

Five files in the atomic lock commit, hashed in the manifest: **pre-registration, judge, smoke harness, manifest, `.gitattributes`** (the `-text` filter-free pin that makes the guard's comparison deterministic and forecloses lossy-filter collisions under the accident model).

## Instantiate a study

1. Copy `judge_template.py`, `smoke_template.py`, `compute_core.py`, `ovp_guard.py`, `.gitattributes`.
2. Fill `compute_core.compute_sealed` with the study's estimator (keep it **pure + seeded**).
3. In the judge: pin `LOCK_TAG`, `LOCKED_PATH`, `OUT_PATH`, and `EXPECTED_INPUT_SHA256` **as constants in the file** (so H1's blob check covers the input hashes); implement `sealed_loader`.
4. In the harness: pin the synthetic seed (or the hashed fixture path); never read the candidate.
5. Lock: atomic commit of the five files, then `git tag -s <LOCK_TAG>`. Run the judge **once**.

## Run the tests

```
python3 test_ovp_guard.py      # 12 unit properties (each builds a real temp git repo)
python3 test_integration.py    # 2 end-to-end (smoke pre-lock; judge across the lock boundary)
```

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

## Built vs. still spec'd (honest scope)

- **Built + tested:** the guard, the full closure chain (H1 + output-exists + input-hash + closed-world), the `(sealed-loader, synthetic-loader, shared-core)` factoring, the judge/harness skeletons.
- **Spec'd (§3), not yet implemented:** the **signed additive attestation tool** for grandfathered #1–#4 — the two schema-enforced distinctions (verifiable/attested; anchored/unanchored). It's additive metadata tooling, separable from the judge path; the next build item.
- **Documented boundary, not mechanized:** the hostile-`info/attributes` lossy-filter case is out-of-model tamper (R-1); test 12 asserts the boundary (locked `.gitattributes` tracked, `info/attributes` untracked) rather than constructing the collision.
