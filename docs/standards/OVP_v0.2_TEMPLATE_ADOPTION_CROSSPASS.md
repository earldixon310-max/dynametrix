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

## Adoption pass 2 — PENDING (frozen rev6; independent executing reader)
