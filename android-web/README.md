# FreeSystemDoctor Android — landing page

Statyczna strona promocyjna dla androidowej wersji FreeSystemDoctor.
**Bez build-stepu.** Wszystko czystym HTML/CSS/JS + SVG. Wrzucasz folder na hosting i działa.

## Struktura

```
android-web/
├── index.html              ← główna strona (PL domyślnie, EN przez toggle)
├── style.css               ← style (paleta z apki)
├── script.js               ← animowany kursor, parallax, scroll-reveal, lang toggle
├── privacy.html            ← polityka prywatności (PL+EN w jednym pliku)
├── assets/
│   ├── logo.svg            ← logo (używane w nav, footer, hero)
│   ├── favicon.svg         ← favicon
│   ├── icon-512.svg        ← ikona aplikacji 512×512 (do Play Store)
│   ├── feature-graphic.svg ← banner sklepowy 1024×500
│   ├── og.svg              ← Open Graph 1200×630 (social media)
│   └── screens/
│       ├── 01-dashboard.svg
│       ├── 02-cleaner.svg
│       ├── 03-tools.svg
│       ├── 04-insights.svg
│       └── 05-vault.svg
└── store-listing/
    ├── description-pl.md   ← polski opis do Google Play
    ├── description-en.md   ← angielski opis do Google Play
    └── README.md           ← instrukcja konwersji SVG → PNG dla sklepów
```

## Jak uruchomić lokalnie

Najprościej z dowolnym statycznym serwerem:

```bash
cd android-web
python3 -m http.server 8000
# albo:
npx serve .
```

Otwórz `http://localhost:8000`.

> Otwarcie `index.html` bezpośrednio przez `file://` też zadziała, ale niektóre przeglądarki blokują `<link rel="icon">` i `localStorage` w trybie pliku.

## Jak wrzucić na hosting

**Każdy hosting WWW** (zwykły shared, VPS, GitHub Pages, Netlify, Vercel, Cloudflare Pages) zadziała.

### Wariant A — własny hosting (FTP/SFTP)
1. Połącz się klientem FTP (np. FileZilla, WinSCP)
2. Wgraj cały folder `android-web/` do `public_html/android/` (albo gdziekolwiek)
3. Twoja strona będzie pod `https://twojadomena.pl/android/`

### Wariant B — GitHub Pages (już używasz dla `freesystemdoctor.pl`)
Strona zadziała automatycznie pod `https://freesystemdoctor.pl/android-web/` po pushu na branch `main`. Jeśli chcesz pod krótszym URL-em (`freesystemdoctor.pl/android/`) — utwórz w roocie symlink albo przenieś folder do `android/`.

### Wariant C — Netlify / Vercel / Cloudflare Pages
1. Połącz repo z platformą
2. Build command: `(brak)`
3. Publish directory: `android-web`
4. Deploy

### Wariant D — pojedynczy ZIP do uploadu
```bash
cd /home/user/freesystemdoctor
zip -r android-web.zip android-web/
# Wgraj ZIP → wypakuj na hostingu
```

## Konfiguracja — co warto zmienić przed publikacją

1. **`index.html` linia ~14, ~16** — `og:url` i `canonical` URL: zmień na docelowy adres (np. `https://freesystemdoctor.pl/android/`)
2. **`index.html` link do JSON-LD `downloadUrl`**: docelowy URL releasu na GitHubie
3. **`script.js` linia ~138** — jeśli zmienisz nazwę repo, podmień w przycisku „Pobierz APK"
4. **`privacy.html`** — pole `coopaisolutions@gmail.com` to maila kontaktowy (zostaw lub zmień)

## Funkcje strony

- **Pełna responsywność** — działa od 320 px do 4K
- **Język PL/EN** — toggle w nawigacji, pamiętany w `localStorage`, działa też przez `?lang=en`
- **Animowany kursor** — dot + ring z lerp, mix-blend-mode (auto-ukrycie na touch)
- **Parallax** — hero copy + visual jadą z różną prędkością na scroll
- **Scroll-reveal** — IntersectionObserver z fade+slide na każdej sekcji
- **Animowane tło** — 3 driftujące blob-y z `filter: blur()`
- **Floating phone mockupy** — w hero, animacja `@keyframes float-*`
- **Dostępność** — `prefers-reduced-motion` wyłącza wszystkie animacje
- **SEO** — meta + Open Graph + JSON-LD `MobileApplication`
- **0 zewnętrznych zasobów** — żadnego CDN, fontów Google, trackerów. Strona ładuje się instant.

## Lighthouse / Pagespeed

Strona jest świadomie projektowana pod wynik 95+ na Lighthouse:
- Brak JS frameworków (~12 KB scripted)
- Wszystkie obrazy to SVG (inline-friendly, kilkadziesiąt KB każdy)
- Brak zewnętrznych font-face — używamy stack systemowy
- Lazy-loading dla screenshotów poniżej hero
- `defer` na głównym JS

## Po publikacji

1. Sprawdź w **Google Search Console** (search.google.com/search-console) — dodaj domenę, wgraj sitemap (gen-uj online, jest jeden URL)
2. Dodaj `og:image` do absolutnego URL (Twitter karty wymagają HTTPS absolute):
   ```html
   <meta property="og:image" content="https://twojadomena.pl/android/assets/og.svg">
   ```
3. Test Open Graph: https://www.opengraph.xyz/ wklej swój URL → sprawdź podgląd

## Co dalej

- `download.html` — opcjonalna osobna strona „Pobierz" z hash sumami dla każdego release'u
- `changelog.html` — historia zmian (już istnieje wersja windowsowa pod `/changelog.html` w głównym repo)
- `press.html` — press kit dla mediów (po publikacji w sklepach)
