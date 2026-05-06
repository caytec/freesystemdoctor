# FreeSystemDoctor — landing page

Strona pod `caytec.github.io/freesystemdoctor`.

## Pliki

- `index.html` — landing z hookami i porównaniem z konkurencją
- `changelog.html` — auto-aktualizowana historia zmian
- `changelog.json` — dane zasilające changelog (regenerowane przez GitHub Action)
- `style.css` — ciemny motyw zgodny z aplikacją

## Włączenie GitHub Pages (jednorazowo)

1. Push tego repo na GitHub.
2. Ustawienia repo → Pages → Source: **GitHub Actions**.
3. Pierwszy push do `main` automatycznie odpali workflow `deploy-pages.yml`.
4. Po ~1 minucie strona dostępna pod: `https://caytec.github.io/freesystemdoctor/`

## Auto-changelog

Workflow `update-changelog.yml` wykonuje się przy każdym pushu na `main`:

1. Czyta `git log` (ostatnie 500 commitów, bez merge'y).
2. Generuje `docs/changelog.json` z polami `sha`, `date`, `msg`.
3. Commituje plik z prefixem `[skip ci]`, żeby nie zapętlić workflow.
4. Następnie `deploy-pages.yml` publikuje aktualną stronę.

Changelog klasyfikuje commity po prefiksach:
- `feat:` / `add:` / `nowy:` → zielona etykieta **feat**
- `fix:` / `napraw:` / `popraw:` → czerwona etykieta **fix**
- `docs:` → niebieska etykieta **docs**
- `refactor:` → żółta etykieta **refactor**
- pozostałe → szara **chore**

Używaj conventional commits, żeby changelog wyglądał czysto.

## Lokalny podgląd

Otwórz `index.html` bezpośrednio w przeglądarce **albo** uruchom prosty serwer:

```bash
cd docs
python -m http.server 8000
```

Następnie http://localhost:8000.
