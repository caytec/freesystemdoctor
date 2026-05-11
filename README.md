# FreeSystemDoctor

> Darmowy, open-source optymalizator Windows. 62 moduły silnika. 45 narzędzi w GUI. Zero reklam, zero subskrypcji.

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue.svg)]()
[![Download](https://img.shields.io/badge/download-25%20MB-blue.svg)](dist/FreeSystemDoctor.exe)

🌐 **Strona projektu:** [caytec.github.io/freesystemdoctor](https://caytec.github.io/freesystemdoctor) · [Changelog](https://caytec.github.io/freesystemdoctor/changelog.html)

## Pobierz

➡️ **[`dist/FreeSystemDoctor.exe`](dist/FreeSystemDoctor.exe?raw=1)** — 25 MB, x64, Windows 10/11

Pojedynczy plik. Bez instalatora. Bez kont. Uruchom i działa.

## Co to jest

Aplikacja Windows z 45 modułami narzędzi:

- **Czyszczenie:** śmieci, rejestr, duplikaty, puste foldery, duże pliki
- **Optymalizacja:** RAM, sieć (TCP/DNS), autostart, usługi, profile wydajności
- **Prywatność:** ślady przeglądarek, shredder DOD 5220.22-M, drive wipe
- **Bezpieczeństwo:** Defender, firewall, ochrona kamerki
- **Monitoring:** real-time CPU/RAM/Dysk, hardware monitor, benchmark
- **Zaawansowane:** Smart Defrag (SSD-aware), file recovery, asystent AI

## Cybersecurity Scanner (online)

Pełny audyt bezpieczeństwa działający w przeglądarce — bez logowania, bez wysyłania danych:

- **Moduły:** system, sieć, pamięć, storage, przeglądarka, prywatność, **strona internetowa (URL)**, malware (skan plików)
- **Website audit:** DNS over HTTPS (A/AAAA/MX/TXT/SPF/DMARC/CAA/NS + DNSSEC AD-flag), HTTPS check, opcjonalny deep-scan przez CORS proxy (HSTS/CSP/X-Frame-Options/cookies/mixed-content/banner disclosure)
- **AI Risk Analyst (BYOK):** chat panel oparty o Claude (Anthropic), Groq, Cerebras albo dowolny endpoint OpenAI-compatible. Klucz przechowywany lokalnie, żądania idą bezpośrednio z przeglądarki — nie mamy serwera. Anthropic używa nagłówka `anthropic-dangerous-direct-browser-access`.
- **Hashing plików:** SHA-256 + SHA-1 + MD5, lokalna baza znanych zagrożeń (m.in. EICAR)
- **Raporty:** PDF (jsPDF) albo lokalny link `blob:` do pobrania, eksport JSON
- **Threat Intel feed:** anonimowe IOC (hash + werdykt + region) — bez nazw plików, bez IP
- 🌐 [`scanner.html`](https://caytec.github.io/freesystemdoctor/scanner.html) · [`threat-intel.html`](https://caytec.github.io/freesystemdoctor/threat-intel.html)

## Wymagania

- Windows 10 (build 1809+) lub Windows 11
- x64
- ~50 MB miejsca na dysku
- ~100 MB RAM podczas pracy

## Licencja

MIT — zobacz [LICENSE](LICENSE).

## Hosting (Railway / Docker)

Repo ma gotowy `Dockerfile` + `Caddyfile` + `railway.json` — strona stawia się jednym kliknięciem.

**Railway:**
1. New Project → Deploy from GitHub repo → wybierz `caytec/freesystemdoctor`.
2. Railway sam wykryje `Dockerfile`. Nie trzeba ustawiać żadnych env vars (Caddy używa `$PORT` ustawionego przez Railway).
3. Po pierwszym deployu otwórz Settings → Networking → Generate Domain (albo dodaj custom domain).

**Lokalnie (sanity check):**
```sh
docker build -t fsd .
docker run --rm -p 8080:8080 -e PORT=8080 fsd
# → http://localhost:8080
```

Caddy ustawia HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy i Permissions-Policy. **CSP jest świadomie pominięty** — AI Risk Analyst pozwala wskazać dowolny endpoint OpenAI-compatible, co bez luźnego `connect-src` by przestało działać. Jeśli wdrażasz pod jeden konkretny zestaw providerów, dostosuj `Caddyfile`.
