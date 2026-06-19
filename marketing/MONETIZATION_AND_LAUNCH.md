# FreeSystemDoctor — Monetization & Launch Plan (max exposure)

Master plan tying together **all revenue streams** and the **publication pipeline**.
Companion docs: `MARKETING_KIT.md` (copy), `SUBMISSION_SITES.md` (where to post).
Canonical facts: v2.2.0 · MIT · Win10/11 x64 · ~40 MB · https://freesystemdoctor.com.pl ·
repo `caytec/freesystemdoctor` · downloads via GitHub `releases/latest`.

---

## 1. Revenue streams (all wired in code)

| Stream | Price / model | Where | Code |
|---|---|---|---|
| **Pro license** | **$9.99/yr recurring** (Stripe subscription) | Settings → License; Pro gates | `license_manager.py`, server `frog02.mikr.us:21187`, `_pro_gate.py` |
| **Affiliate** | per-sale/install commission (18 partners) | in-app native cards (opt-in) + `/partners` page + installer thank-you | `affiliate.py` → routes through `PARTNERS_URL` |
| **Native ads** | opt-in, off by default, 1 fetch/24h | Settings toggle | `ad_network.py` |
| **Donations** | Ko-fi | sidebar ☕ + Settings | `app.py`, `page_settings.py` |
| **Newsletter** | list-building for re-marketing | opt-in capture | `email_capture.py` |

**Funnel:** GitHub/portal download → **installer** → **thank-you page** (UTM) → app →
(Pro upsell after 30-min warm-up) + (contextual `/partners` affiliate cards). Every hop is
UTM-tagged so you can see which traffic source converts to which stream.

**Honesty guardrails (keep, or risk PUP flags):** no telemetry · no bundleware · no forced
ads · ads/affiliate opt-in & off by default. Never claim "no ads ever".

---

## 2. Installer (built)

- **Tool:** Inno Setup 6 → `installer/FreeSystemDoctor.iss`, built by `build_installer.ps1`.
- **Output:** `dist_installer/FreeSystemDoctor-Setup-2.2.0.exe` (~41 MB) + `SHA256SUMS.txt`.
- **Affiliate link:** PUP-safe — the **only** outbound link is an opt-out finish-page checkbox
  opening the **thank-you page** (`/thanks?utm_source=installer…`), which itself links to
  `/partners`. No bundled software, no pre-checked partner offers.
- **Behavior:** installs to Program Files (admin), Start-Menu + optional desktop icon,
  uninstaller, EN+PL wizard.
- **Ship both:** the installer **and** the portable `FreeSystemDoctor.exe` (some portals/users
  prefer portable; PortableApps/FossHub require no-installer builds — see STRICT copy).

**Rebuild:** `.\build_installer.ps1 -Rebuild` (rebuilds exe then installer).

---

## 3. Affiliate management — single source of truth

All in-app clicks route to `https://freesystemdoctor.com.pl/partners?ref=<id>` (`affiliate.PARTNERS_URL`).
`website/partners.html` reads `?ref=` and 302-redirects to the **real** affiliate URL.
→ **Swap the 18 placeholder links to your real affiliate URLs in ONE file** (`partners.html`
`LINKS` map) — no app rebuild needed. UTM params pass through. Disclosure + opt-out included.

**TODO before launch:** sign up for the partner programs you'll run (Brave, Proton, NordVPN,
Bitdefender, AdGuard, pCloud, Bitwarden, etc.) and paste real links into `partners.html`.

---

## 4. Publication — distribution pipeline (max exposure)

**Canonical host:** GitHub Releases (website + portals link to `releases/latest`).

### Phase 0 — release artifacts (do once)
1. `.\build_installer.ps1 -Rebuild` → installer + portable exe + SHA256SUMS.
2. Create GitHub Release `v2.2.0`, upload: `FreeSystemDoctor-Setup-2.2.0.exe`,
   `FreeSystemDoctor.exe`, `SHA256SUMS.txt`. Paste `RELEASE_NOTES`.
3. Deploy website (incl. new `partners.html`, `thanks.html`) to freesystemdoctor.com.pl.
4. Verify the website download button → release; verify `/thanks` and `/partners` live.

### Phase 1 — automated channels (in-app Publisher page, 1-click APIs)
GitHub Releases · Winget · Chocolatey · Scoop · SourceForge.

### Phase 2 — launch-day spike (same morning, reply to every comment)
Product Hunt · Show HN · top Reddit subs (r/Windows, r/software, r/opensource) ·
dev.to/Hashnode launch article. (Details in `SUBMISSION_SITES.md` §D.)

### Phase 3 — directories (batch over week 1)
Publisher page's 29 manual portals + the new free targets in `SUBMISSION_SITES.md`
(Soft112, FreewareFiles, OpenAlternative, FSF Directory, AlternativeTo, etc.).
Use the `[STRICT]` no-monetization copy for Softpedia/FossHub/PortableApps/FSF.

### Phase 4 — backlinks / B2B / PL (ongoing)
Capterra/GetApp/G2 + Polish: dobreprogramy, instalki, Komputer Świat, Elektroda, Spider's Web pitch.

---

## 5. Measurement (close the loop)

- **UTM everywhere:** each portal gets `?utm_source=<portal>` on its download link;
  installer→`/thanks`, app→`/partners` already tagged.
- **Watch:** downloads (GitHub release stats) → thank-you page views → `/partners` clicks →
  affiliate dashboards + Stripe Pro sales. Double down on sources where downloads → $ is highest.
- In-app: `affiliate.get_local_stats()` (local only) for impression/click CTR per offer.

---

## 6. Pre-launch checklist

- [ ] Real affiliate links in `website/partners.html`
- [ ] Website redeployed with `partners.html` + `thanks.html`
- [ ] Stripe webhook configured → `…:21187/webhooks/stripe` (+ `STRIPE_WEBHOOK_SECRET`)
- [ ] GitHub Release v2.2.0 with installer + portable + SHA256SUMS
- [ ] `gui/icon.ico` added (brands BOTH installer and exe — currently unbranded) — *nice-to-have*
- [ ] 6 screenshots captured (shot-list in `MARKETING_KIT.md`) for portals/Product Hunt
- [ ] Price/claims consistent ($9.99/yr, 70+ tools) across site/README/listings
- [ ] Code-sign the installer (optional, reduces SmartScreen warnings) — *nice-to-have*
