# OVP v0.1 — Lock Notice

**`OVP_v0.1_OBSERVABLE_VALIDATION_PROTOCOL.md` is LOCKED as v0.1.**

- **Lock tag:** `ovp-v0.1-lock` (signed annotated tag; carries the authoritative lock semantics)
- **Lock date:** 2026-06-04
- **Clearing review:** fifth external cold pass — returned **no lock-blocker** (four non-blocker findings, queued for v0.x in `OVP_DESIGN_HISTORY.md`).
- **Pre-committed lock bar:** pinned at commit `c806c2e`, *before* the clearing read — Option 1 ("no lock-blocker = lock") with a pre-defined lock-blocker taxonomy. The fix-author did not serve as the clearing reader.

**Why the spec body still reads "working draft — not locked":** by design. The lock bar pinned before the read required the locked artifact to be **byte-identical** to the version the cold reader cleared. Editing the spec's own status line — even to announce the lock — would break that property and open "exactly" to exceptions. So the lock is carried by the signed git tag, this notice, and the design-history record, **not** by modifying the reviewed file. Anyone inspecting the repo sees: (a) the signed tag, (b) this notice, (c) the lock entry in `OVP_DESIGN_HISTORY.md` — an unambiguous, externally-documented lock over an unmodified artifact.

See `OVP_DESIGN_HISTORY.md` for the full five-pass review history, the pre-committed bar, and the v0.x revision queue.
