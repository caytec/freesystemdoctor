# Anti-PUP / Anti-Adware Compliance Guide — FreeSystemDoctor

This document is the operational checklist that keeps FSD off antivirus
PUP (Potentially Unwanted Program) and adware blocklists while we
monetize via affiliates, native sponsored slots, smart Pro upsells and
an opt-in ad network.

The rules below are non-negotiable — every monetization change must pass
this checklist before shipping. They map directly to the heuristics used
by Microsoft Defender, Malwarebytes, ESET, Avast, Bitdefender and
VirusTotal aggregators.

---

## 1. Distribution & install

| Rule | Implementation |
|---|---|
| **No installer wrapper / bundle** | Ship a single signed `FreeSystemDoctor.exe` from GitHub Releases. No NSIS/Inno installer that offers third-party software during setup. |
| **No silent installs of partners** | All affiliate links open the partner's own website in the user's default browser via `webbrowser.open()`. We never download or execute partner binaries ourselves. |
| **No drive-by browser extension** | We do not bundle, prompt for, or install any browser extension. |
| **No homepage / search hijacking** | Zero changes to default browser, default search engine, new-tab page, or shortcuts. |
| **No registry entries beyond runtime needs** | We may write to `HKCU\Software\FreeSystemDoctor` for settings; we do not touch `Run`, `RunOnce`, Explorer context menus, BHOs, IFEO, AppInit_DLLs, scheduled tasks (unless the user explicitly opts in to scheduling), services, or Winsock LSPs. |
| **Standalone uninstall** | Deleting `FreeSystemDoctor.exe` and `%APPDATA%\FreeSystemDoctor\` fully removes the product. No leftover services / drivers / scheduled tasks. |

## 2. Code signing & reputation

- **Sign every EXE** with a Sectigo / DigiCert OV (or EV) code-signing cert.
  Unsigned binaries trip SmartScreen + Defender Cloud heuristics hard.
- **Stable file hash and metadata**: keep `CompanyName`, `ProductName`,
  `FileDescription`, `OriginalFilename`, version info populated and
  consistent across builds.
- **Submit each release to AV vendors** for whitelisting:
  - Microsoft: <https://www.microsoft.com/wdsi/filesubmission>
  - Malwarebytes: false-positive form
  - ESET: samples@eset.com
  - Bitdefender: <https://www.bitdefender.com/consumer/support/answer/29358/>
  - Avast/AVG: <https://www.avast.com/false-positive-file-form.php>
- **Reproducible builds** via the pinned `FreeSystemDoctor.spec`. Don't
  randomize file structure between releases — that's a classic packer
  red flag.

## 3. Monetization UX

| Rule | Implementation |
|---|---|
| **Global opt-out** | `Settings → Monetization → Wyłącz wszystkie rekomendacje` honoured by `affiliate.is_enabled()`, `ad_network.is_enabled()`, and `sponsored_notifications`. |
| **Granular per-category opt-out** | `affiliate.set_category_enabled(category, bool)` lets users keep useful categories (e.g. AV) and silence ones they don't care about (e.g. Streaming). |
| **Explicit labelling** | Every sponsored unit shows "✦ Sponsored" or "Polecane partnerskie". No dark patterns. |
| **No popups over active work** | Pro upsells are inline cards, not modal dialogs. Triggers require 30 min app uptime and 72 h cooldown between prompts. |
| **No system toasts / balloon notifications** | All sponsored content renders inside the FSD window; we never push Windows toast notifications. |
| **No autoplay / sound / animation flicker** | Tkinter static widgets only. |
| **No tracking pixels, no third-party JS, no iframes** | Affiliate widgets are plain Tk labels + buttons. Only HTTP call is the explicit user-initiated `webbrowser.open()`. |
| **Ad network = opt-in** | `engine/ad_network.py` is off by default and requires explicit user action to enable. Even when on, max 1 fetch per slot per 24 h, server is our own (`ads.freesystemdoctor.pl`). |

## 4. Network behaviour

- App start: **zero outbound HTTP** related to monetization. Only the
  version check and (if enabled) Pro license sync may fire — both
  documented in the privacy policy.
- During idle: **zero outbound HTTP** — no analytics beacons, no
  ad refresh timers, no telemetry.
- During a page open: outbound HTTP only if **(a) ad network is enabled
  AND (b) that page renders an ad slot AND (c) cache is stale**.
- On user click: outbound HTTP only because the user pressed a CTA, and
  it's the partner's URL in the user's default browser — not from our
  process.

## 5. Email capture (newsletter)

- Double opt-in: user types email + ticks GDPR consent + clicks submit.
- Form is hidden after dismissal — never re-prompts.
- Backend: our own newsletter endpoint, payload limited to
  `{ email, locale, source, ts }`. No machine ID, no IP logging beyond
  what the HTTP server already does, no hostname.
- Unsubscribe link in every email; one-click confirmation.

## 6. Telemetry

We collect **zero anonymous usage telemetry** in the free build. The
local click/impression counter in `affiliate.json` exists only so the
developer can read `get_local_stats()` from the GUI — it is never
transmitted.

If we ever add opt-in telemetry, it MUST:
- be off by default,
- be controlled by a single Settings toggle,
- batch every 24 h, not every action,
- exclude personal data (no paths, no filenames, no email addresses).

## 7. Pre-release self-test

Before each tagged release:

1. Build the EXE with the pinned spec.
2. Sign it.
3. Run on a clean Windows 11 VM with: Defender + Malwarebytes + ESET
   trial. Confirm no detections.
4. Submit hash to <https://www.virustotal.com>; investigate any
   detections (>3 hits = block release, fix first).
5. Confirm uninstall = delete EXE + `%APPDATA%\FreeSystemDoctor\` =
   completely removes the product. No leftover services, registry,
   tasks.
6. Confirm `Settings → Monetization → Wyłącz wszystkie` actually stops
   every banner/card/notification in the UI.

## 8. Categories of monetization, ranked by AV-risk

| Surface | AV Risk | Why it stays safe |
|---|---|---|
| Affiliate link-out (`webbrowser.open`) | **Very low** | Just opens a URL in Chrome/Edge; identical to a bookmark. |
| Inline "Sponsored" label inside a page | **Very low** | No different from product news; clearly labelled. |
| Pro upsell card | **Very low** | First-party promotion, inline, dismissible. |
| Tip-of-the-day with sponsored mix | **Low** | Capped at 1/24 h, dismissible per ID. |
| Newsletter capture | **Low** | Explicit consent, no network call until submit. |
| Native ad network (opt-in) | **Medium** | Off by default; safe because of single-server, JSON-only, no JS, 24 h cache, hard timeout. |
| ❌ Installer bundle | **HIGH — never do this** | Instant PUP classification. |
| ❌ Auto-launched browser tabs | **HIGH — never do this** | Triggers adware heuristics. |
| ❌ Tray/balloon ad pushes | **HIGH — never do this** | Triggers adware heuristics. |
| ❌ Background ad polling | **HIGH — never do this** | Triggers behavioural detection. |

## 9. Legal / disclosure

- Landing page (`index.html`) and in-app `Settings → O programie` must
  state plainly: *"FreeSystemDoctor jest darmowy. Część rekomendacji to
  linki afiliacyjne — jeśli klikniesz i kupisz, otrzymamy małą
  prowizję, Ty nie płacisz więcej. Możesz wyłączyć wszystkie
  rekomendacje w Ustawieniach."*
- Privacy policy lists every outbound endpoint by hostname.
- Affiliate disclosures comply with FTC 16 CFR Part 255 and Polish UOKiK
  guidelines on hidden advertising.

---

**Owner:** Kajetan / coopaisolutions@gmail.com
**Last updated:** 2026-05-25
**Review cadence:** every release tag.
