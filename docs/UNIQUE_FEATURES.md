# What FreeSystemDoctor has that the competition doesn't

Researched August 2026 against Razer Cortex, IObit Advanced SystemCare, Hone.gg,
Wise Care 365, Glary Utilities, CCleaner, Mem Reduct and ISLC.

Everything below is implemented and verified on real hardware — no roadmap items.

---

## 1. Automatic A/B verification with auto-rollback

**Nobody else does this.** Every optimizer applies changes and asserts they helped.
FreeSystemDoctor measures the machine, applies one tweak, measures again, and
**automatically undoes any tweak that made things measurably worse**.

The honest part is the noise margin: it takes several baseline samples first and
derives the threshold from your machine's own measured variance, so a verdict
means something. A tweak only counts as harmful when it moves a metric further
than your PC's own noise.

*Closest competitor:* Vax Tweaker advertises "drift detection + rollback", but the
rollback is manual — nothing measures and decides for you.

## 2. Measured before/after proof, not claims

Boost results are reported as real numbers: MB of RAM freed, kernel timer in ms,
DPC latency percentage — measured before and after, shown side by side.

Competitors show a progress bar and the word "Boosted!".

## 3. ISLC-class RAM engine with per-stage proof

The full Windows native memory API, the same one Mem Reduct and ISLC use:

| Technique | What it frees |
|---|---|
| `MemoryEmptyWorkingSets` | process working sets (protected processes skipped) |
| `MemoryFlushModifiedList` | dirty pages awaiting write-out |
| `MemoryPurgeStandbyList` | the cached standby list |
| `MemoryPurgeLowPriorityStandbyList` | low-priority cache only (gentler) |
| `SetSystemFileCacheSize` | the system file cache |

**And each stage reports the MB it actually freed separately**, so you can see
which technique did the work. Mem Reduct and ISLC do the cleaning but report one
lumped total; mainstream optimizers only trim working sets and call it "RAM freed".

## 4. Live memory composition

A single bar showing In use / Modified / Standby / Free with real MB values, so
you can see that "used" RAM in Task Manager is largely reclaimable cache. No
consumer optimizer visualizes this.

## 5. Smart standby auto-policy (opt-in)

Automatic standby purging that only fires under genuine pressure — low free RAM
**and** a large standby list worth reclaiming. Off by default, because the standby
list is a disk cache and purging it eagerly makes a PC slower, not faster.
Tools that purge on a timer routinely do more harm than good.

## 6. Undo Center — a receipt for every change

A chronological record of every setting the app changed, with per-item undo and
one button to put everything back. Optimizers change dozens of settings and then
forget which; this is the audit trail.

## 7. DPC / interrupt latency diagnostic

Measures kernel DPC time, DPCs queued/sec and interrupt time using real Windows
performance counters. High DPC latency causes stutter and input lag **even at high
FPS** — and no consumer optimizer measures it.

## 8. MSI interrupt mode manager

Switches GPU, network, USB and storage controllers to message-signalled
interrupts, which measurably reduces DPC latency and input lag.

## 9. Hidden power settings via `powercfg /qh`

Energy-Performance Preference, turbo boost policy, hybrid P-core scheduling and
CPU idle states — settings Windows hides and `powercfg /q` silently omits.
On the test machine, boost policy was capped at 60% out of the box.

## 10. PCIe link power management, one click

Stops the PCIe link to the GPU dropping into low-power states mid-frame. Real
stutter source; nothing mainstream touches it.

## 11. Honest VBS/HVCI control

Virtualisation-based security costs roughly 2–8% FPS. Offered with an explicit
security trade-off warning rather than silently disabled or ignored entirely.

## 12. Live CPU and GPU proof cards

Actual current clock including turbo (via `% Processor Performance`, which exceeds
100% when boosting) and real GPU telemetry — clocks, load, temperature, power.

## 13. WinSxS component store deep clean

Including `/ResetBase`. Mainstream cleaners skip the component store entirely,
which is often several GB.

## 14. Full-stack one-click revert

Every layer — system, CPU, GPU, RAM, network — unwound in reverse order from
per-module backups, with a restore point taken first.

---

## Honest limitations

- Native memory-list calls, MMAgent and most registry tweaks **require
  administrator rights**. Without elevation the app says so rather than
  pretending to succeed.
- Verification needs an otherwise-idle PC; it says so before starting.
- Some changes (HAGS, kernel timer flag, prefetcher, NTFS flags) only take full
  effect after a reboot, and each says so.
- Standby/modified figures need Windows performance counters; if they're
  unavailable the app reports "n/a" instead of guessing.
