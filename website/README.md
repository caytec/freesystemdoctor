# FreeSystemDoctor — strona one-page (Vite)

Zaawansowana, animowana strona one-page (parallax, scroll-reveal, liczniki,
tilt 3D, dwujęzyczna PL/EN). Kompiluje się do **czystego statycznego HTML/CSS/JS**,
który wrzucasz na dowolny zwykły hosting www.

## Wymagania
- Node.js 18+ (przetestowane na Node 24)

## Komendy

```bash
cd website
npm install        # raz, instaluje Vite
npm run dev        # podgląd na żywo (http://localhost:5173)
npm run build      # buduje do website/dist/
npm run preview    # podgląd zbudowanej wersji (http://localhost:4173)
```

## Wdrożenie na hosting

Po `npm run build` cała strona jest w folderze **`website/dist/`**:

```
dist/
├── index.html
├── favicon.svg
├── robots.txt
├── sitemap.xml
└── assets/
    ├── index-*.css
    └── index-*.js
```

Wgraj **całą zawartość `dist/`** do katalogu głównego swojego hostingu
(np. `public_html/`, `www/`, `htdocs/`) przez FTP, panel hostingu lub `rsync`.
Ścieżki są względne (`./assets/...`), więc działa też w podkatalogu.

### Strony dodatkowe (prawne)
Pliki `privacy.html`, `terms.html`, `affiliate-disclosure.html` z katalogu
głównego repozytorium skopiuj obok `index.html` na hosting — stopka do nich linkuje.

## Co zawiera strona
- **Hero** z animowanym tłem (mesh + grid + orby), parallax i tilt 3D makiety aplikacji
- **Statystyki** z animowanymi licznikami
- **Funkcje** (bento grid) z efektem reflektora pod kursorem
- **Sekcja Lokalne AI** (Ollama, offline) z makietą terminala
- **Jak działa** — 3 kroki
- **Porównanie** z typowym „cleanerem"
- **Cennik** — 3 plany (Free / Pro / Ultimate B2B)
- **FAQ** — akordeon
- **CTA** + stopka
- Przełącznik języka **PL/EN** (zapamiętywany w localStorage, auto-detekcja)
- Pełna responsywność + `prefers-reduced-motion`

## Personalizacja
- Kolory i tokeny: `src/style.css` (sekcja `:root`)
- Treść i tłumaczenia: `index.html` (pary `<span lang="pl">` / `<span lang="en">`)
- Animacje i interakcje: `src/main.js`
