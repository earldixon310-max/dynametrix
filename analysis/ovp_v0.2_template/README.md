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
3. In the judge: pin `LOCK_TAG`, `LOCKED_PATH`, `OUT_PATH`, `EXPECTED_INPUT_SHA256`, and **`SEALED_SOURCES`** **as constants in the file**; implement `sealed_loader`. (`EXPECTED_INPUT_SHA256` empty ⇒ the judge refuses.) **`SEALED_SOURCES` completeness is operator-asserted** (cold-pass-A reader #4): it must list *every* source file reachable on the sealed path — judge + core + guard + `.gitattributes`; a study that adds a sealed-path import but forgets the dict entry gets a silent H1 gap, so a CI lint checking `SEALED_SOURCES` against the judge's actual imports is **recommended** (not provided here). Keys are **repo-relative** paths (a study under `analysis/study_x/` uses `analysis/study_x/compute_core.py`, not the bare name).
4. In the harness: pin the synthetic seed (or the hashed fixture path); never read the candidate.
5. Lock: atomic commit of all sealed-path sources + harness + manifest + `.gitattributes`, then `git tag -s <LOCK_TAG>`. Run the judge **once**.

## Run the tests

```
python3 test_ovp_guard.py      # 18 unit (closed-world open/listdir/socket/subprocess/os.system/numpy; absent-path; empty-input)
python3 test_integration.py    # 5 end-to-end (smoke; FULL chain across lock; post-lock core/.gitattributes/input edits REFUSE)
python3 test_ovp_attest.py     # 10 attestation (tiers/temporal-derived/claim-scope/binding/tamper/honest-label/grade-derived/emit)
```
33 properties total, all asserted by execution (rev6). (Confirm by *running* — don't trust a stated count.)

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
| H | honest `unanchored` + forged `grade="proof-grade"` → **grade CONTRADICTED** — grade is **derived** from anchoring, never trusted (rev3, cold-pass-A reader #2) | §3 |
| I | forged `temporal_bound` → **CONTRADICTED** — temporal is **re-derived** (`git log --find-object`), never trusted (rev4, cold-pass-A reader #3) | §3 |
| J | `emit_sign_command` produces the `git tag -s …-harness-attest` command bound to the lock commit | §3 |

**rev2 honesty fix (cold-pass-A finding 3):** `verify_attestation` now cross-checks the recorded sha256 against the actual blob bytes (binding), and does **not** machine-claim source-synthetic — synthetic-ness is a read-the-blob property, so the tool reports the *binding* as verified and the synthetic claim as human-readable, never rubber-stamping a candidate-reading harness.

## Scope notes (honest)

- **Built + tested (33 properties):** H1 over **all** sealed-path sources **including `.gitattributes`** (rev4); the full closure chain run end-to-end as one coupled unit (H1 + output-exists + input-hash + closed-world); the `(sealed-loader, synthetic-loader, shared-core)` factoring; **the §3 signed additive attestation tool** (binding, anchoring, grade, and temporal all **re-derived, never trusted**). `emit_sign_command` is exercised at the **command-string** level (test J); the actual `git tag -s` / `git tag -v` signing is the operator's R-1 human-trust step, **not** tested here.
- **Closed-world: the `open` allowlist is the provable guarantee; spawn/network/enumeration are best-effort (rev5–6, cold-pass-A readers #4/#5).** The **allowlist on `open`** is genuinely deny-by-default — any non-allowlisted file read refuses, including `os.open` and **numpy's readers** (`np.load` of a non-allowlisted path refuses; tested, test 18). **`ctypes` `dlopen` does NOT route through `open`** — it is the on-ramp to the C-level libc residual and is **uncovered**. Enumeration/network/spawn are denied via a **denylist of only confirmed-live audit events** (`os.listdir/scandir`, `socket.*`, `subprocess.Popen`, `os.system`, `os.popen`, `os.posix_spawn`, `os.exec`, `shutil.copyfile`). A denylist **cannot be exhaustive** (the spec warned this; rev5's `os.spawnv` entry was a *dead string* removed in rev6 — `os.spawnv` fork+execs in a way the parent's hook doesn't observe; `os.fork` without exec is *bounded* because the child inherits this hook). **The real closure for spawn/network/`dlopen` exfiltration is the operator's external sandbox** (no-network, restricted process) for the canonical run; the audit denylist is defense-in-depth, not a guarantee.
- **Guard bootstrap asymmetry (rev3, cold-pass-A reader #2 — named honestly):** `ovp_guard.py` is in the sealed set and verifies its own on-disk bytes, but it is already imported (running) when it does so. An *accidental* edit is still caught (the running code hashes the edited file and sees the mismatch); a *deliberate* edit that disables the check is R-1 tamper, out of model.
- **Documented boundary, not mechanized:** the hostile-`info/attributes` lossy-filter case is out-of-model tamper (R-1); test 12 asserts the boundary.
- **Human-trust layer (by design, R-1, not this code's job):** git signature verification (`git tag -v`) on both the lock tag and the attestation tag — the identity layer the guards explicitly disclaim. The *signed* path (`git tag -s`) is exercised by the operator; tests use `git tag -a` and verify content, not signature.
- **Known scoped limitation (cold-pass-A):** the input-hash check verifies a path on disk; coupling it to the exact bytes `sealed_loader` loads (closing the TOCTOU) is left to the study's loader, which should hash the bytes it actually reads.

## rev2 — cold-pass-A disposition (one reader, blocker; reset to two fresh passes)

cold-pass-A reader #1 ran all suites green, then *demonstrated* three findings by probe. All folded: **(1)** H1 now covers every sealed-path source — the post-lock-core-edit wrong-compute is reproduced as a refusal (integration test 17); **(2)** closed-world widened to IO-closed (guard test 14); **(3)** attestation binding cross-check + honest source-synthetic label (attest tests F/G). Secondaries: empty input-hash refuses (test 13); test-6 raw-hash divergence now asserted. A blocker resets the count → rev2 re-routes **two fresh** passes; author cannot clear.

**rev3 — cold-pass-A reader #2.** Two process errors (packet omitted `ovp_guard.py`/`ovp_attest.py`; charge carried stale rev1 "12/2/5" + "five-file" counts) plus one real static finding: `verify_attestation` *trusted* `record["grade"]` instead of deriving it — a forged grade on honest anchoring would pass. Folded: grade is now **derived** from re-derived anchoring and cross-checked (attest test H). Backfills the reader named: closed-world **subprocess** probe (guard test 15), **path-absent-from-tagged-tree** refusal (guard test 16). The guard **bootstrap asymmetry** is now documented. Route fix: send the **whole committed directory**, not pasted files, with the rev3 counts (**16/3/8 = 27**). Reader #2 could not execute (modules absent) so it isn't a clearing pass; rev3 still needs **two fresh executing passes**.

**rev4 — cold-pass-A reader #3 (executing pass, 27/27 reproduced).** Two blocker-class findings, both "trusted-not-derived," both folded: **(1)** `verify_attestation` now **re-derives the temporal bound** (`git log --find-object`) instead of echoing the record — a forged temporal claim is CONTRADICTED (attest test I); **(2)** **`.gitattributes` is now in runtime `SEALED_SOURCES`** — an accidental post-lock edit to the filter-governing file refuses (integration test 18). Plus: the full closure chain now runs end-to-end in one judge with `verify_input_hashes` (test 16) and a post-lock input tamper refuses (test 19); `emit_sign_command` is exercised (test J); the README "24" stale count is corrected to **31** (`16/5/10`). A blocker resets → rev4 re-routes **two fresh executing passes**; author cannot clear. The invariant reader #3 named — *every checkable claim is derived, never trusted* — now holds across binding, anchoring, grade, and temporal.

**rev5 — cold-pass-A reader #4 (executing pass, reproduced 31/31).** One blocker-class finding: a **demonstrated `os.system` exfiltration** through the closed-world block (the audit event wasn't in the denylist; the read happens in the child outside the parent's hook). Folded honestly on both counts: `os.system`/`os.popen`/`os.spawnv`/`os.posix_spawnp` added to the denylist with a test (guard test 17, exploit closed), **and** the README claim narrowed — `open` is the *provable* allowlist guarantee; spawn/network/enumeration are a best-effort denylist that *cannot be exhaustive* (per the spec's own warning), with the external sandbox as the real spawn/network closure. Minors: `SEALED_SOURCES` completeness documented as operator-asserted (CI lint recommended, not provided); the fragile `samefile`/`judge_oid` construct cleaned up; the stale charge "27" noted (artifact is 32). A blocker resets → rev5 re-routes **two fresh executing passes** with counts **17/5/10 = 32**; author cannot clear.

**rev6 — cold-pass-A reader #5 (executing pass, 32/32 reproduced).** The finding was an **accuracy** defect, not a new mechanism hole: rev5's `os.spawnv` denylist entry was a **dead string** (advertised coverage it never delivered — a child genuinely exec'd), and the README wrongly listed `ctypes dlopen` as routing through `open`. Both corrected: `_DENY_EVENTS` trimmed to only confirmed-live events; the README now states `dlopen` is uncovered (the C-residual on-ramp), `os.fork`-without-exec is bounded, and the external sandbox is the real spawn/network/`dlopen` closure. Backed the numpy claim with a real test (np.load non-allowlisted refuses, test 18); fixed the stale "31" → 33 and the `emit_sign_command` "exercised" wording → "command-string built." **This is the bar in action:** the finding was blocker-class because the artifact *overstated coverage* (inaccuracy), not because a *disclosed* best-effort limit has another hole — those fold non-blocking. 33/33; rev6 re-routes two fresh executing passes.
