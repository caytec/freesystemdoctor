# FreeSystemDoctor

> Darmowy, open-source optymalizator Windows. 62 moduły silnika. 45 narzędzi w GUI. Zero reklam, zero subskrypcji.

[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)]()

🌐 **Strona projektu:** [caytec.github.io/freesystemdoctor](https://caytec.github.io/freesystemdoctor)

## Pobierz

Najnowszy build: [`dist/FreeSystemDoctor.exe`](dist/FreeSystemDoctor.exe) (25 MB, x64)

Lub z [Releases](https://github.com/caytec/freesystemdoctor/releases/latest).

## Co to jest

Pojedyncza aplikacja Windows z 45 modułami narzędzi:

- **Czyszczenie:** śmieci, rejestr, duplikaty, puste foldery, duże pliki
- **Optymalizacja:** RAM, sieć (TCP/DNS), autostart, usługi, profile wydajności
- **Prywatność:** ślady przeglądarek, shredder DOD 5220.22-M, drive wipe
- **Bezpieczeństwo:** Defender, firewall, ochrona kamerki
- **Monitoring:** real-time CPU/RAM/Dysk, hardware monitor, benchmark
- **Zaawansowane:** Smart Defrag (SSD-aware), file recovery, asystent AI

## Uruchomienie ze źródeł

```bash
pip install -r requirements.txt
python main.py
```

## Build .exe

```bash
pip install pyinstaller
pyinstaller FreeSystemDoctor.spec
```

Wynik: `dist/FreeSystemDoctor.exe`.

## Licencja

MIT — zobacz [LICENSE](LICENSE).
