# OVP v0.2 Template — Adoption Cross-Pass Record (rev6)

**Gate:** two independent **executing** cold passes on **frozen rev6** under the refined bar (`OVP_DESIGN_HISTORY.md`: best-effort artifacts lock against accuracy of claim; reset only on (a) a broken provable guarantee or (b) overstated coverage / too-narrow disclosure; (c) a new instance of a disclosed limit folds without resetting). Fix-author cannot clear. **Two clean (no (a)/(b)) → adopt.**

**FREEZE:** no edits to any packet file — the 10 `analysis/ovp_v0.2_template/` files, `OVP_v0.2_TEMPLATE_HARDENING_DRAFT.md`, or the `OVP_DESIGN_HISTORY.md` bar entry — between the two passes. Folding a non-blocker now would change the bytes and reset the count (queue-don't-fold rule). This record lives outside the packet and is **not** shown to pass 2 (independence).

---

## Adoption pass 1 — CLEAN (executing; no lock-blocker)
Environment: Python 3.10.12, git 2.34.1, numpy 2.2.6. Files reconstructed byte-for-byte; all suites run.
- **Counts confirmed by running:** `test_ovp_guard` 18/18, `test_integration` 5/5, `test_ovp_attest` 10/10 = **33**, exit 0/0/0. README count accurate.
- **Provable guarantees — 0 breaks under adversarial probing:**
  - self-guard fail-closed on every git-error path (incl. probes the suite omits: post-lock edit of `ovp_guard.py` itself and the judge file itself → both refuse; bootstrap asymmetry holds);
  - `open` allowlist deny-by-default (probed beyond the suite: `os.open` read+write to non-allowlisted path refuse — backs the untested README `os.open` claim; `np.load` non-allowlisted refuses; allowlisted fixture + symlink-to-fixture permitted);
  - input-hash + output-exists chain end-to-end in one judge (pre-lock refuse / post-lock compute; post-lock core/`.gitattributes`/input tamper each refuse);
  - attestation derive-never-trust across binding/anchoring/grade/temporal (forging any one → CONTRADICTED + `ok=False`; a record whose `harness_git_oid` secretly points at the judge blob is caught by re-derived anchoring).
- **Findings classified (c) — fold/confirm, NOT reset:** (1) C-level libc `fopen`/`fread` reads candidate bytes inside the block — exactly the disclosed `ctypes`/`dlopen`/C-level residual, external sandbox is the real closure; (2) `os.spawnv` not caught by the parent hook — rev6 honestly removed the dead string and doesn't advertise it (in this CPython the fork-child inherits the hook and its `os.exec` is denied, so the exfil never wrote — effective coverage exceeds the claim, safe direction). **No (a) or (b) found.**
- **Placement / test quality / spec conformance:** guard is first statement before any candidate load; tests are genuine asserts (Test J honestly command-string-scoped); runtime H1 set `{judge, compute_core, ovp_guard, .gitattributes}` conforms to rev7 §2's corrected locked set.
- **Verdict: CLEAN, no lock-blocker.**

## Queued non-blockers (v0.x, POST-adoption — do NOT fold pre-lock; queue per the standing rule)
All non-false; queuing keeps the locked artifact exactly what the two passes read.
1. **`os.open` coverage test** — the README's `os.open`-routes-through-`open` claim is true (probed) but unasserted by the shipped suite; add a one-line test.
2. **Guard/judge self-edit tests** — a post-lock edit of `ovp_guard.py` or the judge file itself refuses (holds by construction + pass-1 probe) but isn't pinned by a shipped integration test; add them.
3. **rev7 §1/§4 stale "five-file/fifth locked artifact" wording** — §2 already corrected the count to "every sealed-path source file"; §1/§4 prose is residual and overridden. Wording-only; does not affect the artifact.

## Adoption pass 2 — BLOCKER (executing); count RESET → rev7
Independent executing reader reproduced 33/33 and every provable guarantee held — but found one **class-(b)** defect: **`os.popen` was a dead string** in `_DENY_EVENTS` (CPython fires only `subprocess.Popen`, never `os.popen`), so the explicit "ONLY events confirmed to fire in-process" claim was **false** — the same accuracy-of-claim defect class the program reset on at rev6 (`os.spawnv`). By the bar and precedent, **(b) resets**; author cannot clear. (Weakest possible (b): no functional gap — `os.popen` is still denied via the live `subprocess.Popen` entry.) The C-level libc read (F2) and `os.spawnv` (F3) were correctly **(c)** — disclosed-residual confirmations, not resets.

**Because the reset was forced, the queue-don't-fold rule no longer pinned the non-blockers** — so rev7 folds the blocker AND everything both passes flagged:
- **F1 (blocker):** removed dead `os.popen`; remaining denylist entries verified live.
- **F3:** corrected the `os.spawnv` reasoning (platform/version-dependent best-effort, not "parent doesn't observe").
- **pass-1 queued #1/#2:** `os.open` + isolated `socket.connect` now tested (guard 19/20); **guard-module and judge self-edit** post-lock cases now pinned by shipped tests (integration 20/21).
- **pass-1/2 queued #3:** rev7 spec §1/§4 "five-file/fifth" wording reconciled to §2's "every sealed-path source."

**rev7 = 37/37 (20/7/10), execution-tested.** Adoption gate **restarts: two fresh executing passes on rev7** under the refined bar; fix-author cannot clear. (This record is superseded; pass 1's rev6-clean status does not carry — rev7 is new bytes.)

## Adoption pass 3 (on rev7) — BLOCKER (executing, mutation-testing); count RESET → rev8
Independent executing reader reproduced 20/7/10=37, confirmed all four provable guarantees hold under adversarial probing, and folded the disclosed limits (ctypes/C-level read; `os.spawnv` child-exec caught; a new `os.rename`/`os.link` instance) as **(c)**. **One class-(b) blocker, caught by MUTATION TESTING:** the rev7-headline integration tests **20/21 passed for the wrong reason** — test 19 left `Bdata.bin` tampered and never restored it, and 20/21 asserted only `returncode==2`, so the refusal came from the input-hash gate, not H1. Mutation proof: with H1's byte-mismatch detection disabled, 17/18 correctly failed but **20/21 still passed** — a hollow assertion / overstated coverage, the same defect *class* the program resets on. The underlying guarantee is sound (isolated, editing either file refuses at H1 naming it); only the test was hollow. **(b) resets.** (Reader confirmed every *other* guard's tests have real teeth via mutation: H1→6 guard+3 integ fails, audit no-op→7, attest always-trust→5.)

**rev8 fix (test-only):** after test 19, **restore `Bdata.bin`** so 20/21 run with intact input (only H1 can refuse them), and **assert the refusal message names the edited file** (`"ovp_guard.py bytes !="` / `"judge_y.py bytes !="`). **Mutation-verified:** breaking H1 now turns 20/21 RED (3/7); restored, 7/7. rev8 = 37/37, the test pair is no longer hollow.

**Adoption gate restarts: two fresh executing passes on rev8.** Author cannot clear.

## Adoption pass 1 (on rev8) — CLEAN (executing, mutation-testing; no lock-blocker)
Independent executing reader (Python 3.10.12, numpy 2.2.6, git 2.34.1). Reproduced **20/7/10 = 37**. The most thorough pass to date:
- **Provable guarantees all hold under direct probing:** git-identity fail-closed on all 7 git-error paths (each via a specific branch; branches *layered* so removing one early branch still fails closed downstream — defense-in-depth, not fail-open); `open` allowlist denied every read attempt (`open`/`os.open`/`np.load`); input-hash + output-exists chain end-to-end (input tamper + same-output re-run both refuse); attestation derive-never-trust across all four fields (forging any → CONTRADICTED).
- **Mutation testing (18 mutations) — no hollow test.** 15 caught outright; the 3 follow-ups resolved as defense-in-depth redundancy + a mis-targeted mutation. **The rev8 20/21 fix confirmed:** "cover only the judge" turns core/`.gitattributes`/`ovp_guard` checks red while the judge check stays green → each sealed source independently pinned.
- **Dead-string class RETIRED:** all 9 `_DENY_EVENTS` verified live, incl. the 5 the suite never exercises; `socket.getaddrinfo` chased down (own event fires first on a warmed call, not a dead string).
- **Findings: zero (a), zero (b).** Class-(c) only — `os.rename`/`replace`/`symlink`/`mkdir` (filesystem mutations, can't read the candidate), `os.spawnv`, ctypes/C-level read — all disclosed residuals → fold.
- **Verdict: CLEAN, no lock-blocker.** Wants a second independent pass before lock.

### Non-blocking queue (POST-adoption; do NOT fold pre-lock — would reset the clean pass)
1. **Add regression tests for the 5 currently-untested-but-live denylist entries** (`os.scandir`, `socket.getaddrinfo`, `os.exec`, `shutil.copyfile`, `os.posix_spawn`) so the "each verified to fire and refuse" claim is self-checking. (Capability delivered + claim accurate → not (b), just completeness.)
2. **`SEALED_SOURCES` completeness lint** (operator-asserted; disclosed; ship a CI lint).
3. **input-hash TOCTOU** — already disclosed scoped limitation; couple the hash to the bytes the loader reads.
4. **Cosmetic:** README version label still reads "rev7" (artifact is rev8, test-only fix); integration check labels run 15–21 (renumber 1–7). Both cosmetic; fix at adoption.

## Adoption pass 2 (on rev8) — PENDING (frozen rev8; independent executing reader; not shown this record)
