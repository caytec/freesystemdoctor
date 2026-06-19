# Materiały do sklepów aplikacji / Store listing assets

Wszystko gotowe pod **Google Play**, **Samsung Galaxy Store**, **Amazon Appstore**, **Huawei AppGallery** i **APKPure**. Te same materiały działają we wszystkich.

## Co tu jest

| Plik | Wymiary | Wymagany przez |
|---|---|---|
| `../assets/icon-512.svg` | 512 × 512 | Google Play, wszystkie |
| `../assets/feature-graphic.svg` | 1024 × 500 | Google Play |
| `../assets/og.svg` | 1200 × 630 | Open Graph (social media) |
| `../assets/screens/01-dashboard.svg` | 360 × 740 (9:19.5) | screenshot #1 |
| `../assets/screens/02-cleaner.svg`   | 360 × 740 | screenshot #2 |
| `../assets/screens/03-tools.svg`     | 360 × 740 | screenshot #3 |
| `../assets/screens/04-insights.svg`  | 360 × 740 | screenshot #4 |
| `../assets/screens/05-vault.svg`     | 360 × 740 | screenshot #5 |
| `description-pl.md` | — | polski opis |
| `description-en.md` | — | angielski opis |

## Jak skonwertować SVG → PNG (wymagane przez Google Play)

Google Play **wymaga PNG/JPG**. SVG zrobione tu są wektorowe, więc dowolny rozmiar wyjdzie ostro.

### Opcja A — bezpłatnie, lokalnie (rekomendowane)

```bash
# Zainstaluj rsvg-convert (Linux/macOS):
sudo apt install librsvg2-bin   # Debian/Ubuntu
brew install librsvg            # macOS

# Renderuj:
cd android-web
rsvg-convert -w 512  -h 512  assets/icon-512.svg          -o store-listing/icon-512.png
rsvg-convert -w 1024 -h 500  assets/feature-graphic.svg   -o store-listing/feature-graphic.png
rsvg-convert -w 1200 -h 630  assets/og.svg                -o store-listing/og.png
for f in assets/screens/*.svg; do
  name=$(basename "$f" .svg)
  rsvg-convert -w 1080 -h 2220 "$f" -o "store-listing/$name.png"
done
```

### Opcja B — w przeglądarce (najprostsze)

1. Otwórz SVG w Chrome / Firefox
2. Powiększ na 100% (lub większy zoom)
3. PrintScreen lub narzędzie „pełny zrzut" → przytnij
4. Zapisz jako PNG

### Opcja C — online

`https://svgtopng.com` lub `https://cloudconvert.com/svg-to-png` — wklej SVG, pobierz PNG.

## Dwie wersje językowe screenshotów (PL + EN)

Wszystkie SVG mają domyślnie **angielskie napisy**. Aby zrobić wersję polską, podmień w pliku tekstów:

| Klucz w SVG | EN (domyślne) | PL |
|---|---|---|
| `dashboard.title` | Device health | Stan urządzenia |
| `dashboard.gauge` | HEALTH SCORE | KONDYCJA |
| `dashboard.storage` | STORAGE | PAMIĘĆ |
| `dashboard.storage_sub` | free of 128 GB | wolne z 128 GB |
| `dashboard.ram` | RAM | RAM |
| `dashboard.ram_sub` | used of 8 GB | zajęte z 8 GB |
| `dashboard.battery` | BATTERY | BATERIA |
| `dashboard.battery_sub` | 28°C · charging | 28°C · ładowanie |
| `dashboard.device` | DEVICE | URZĄDZENIE |
| `dashboard.cta` | RUN HEALTH CHECK | SPRAWDŹ KONDYCJĘ |
| `cleaner.title` | Junk cleaner | Czyszczenie |
| `cleaner.reclaimable` | RECLAIMABLE | DO ODZYSKANIA |
| `cleaner.subtitle` | cache + leftover APKs + temp files | cache + APK + pliki tymczasowe |
| `cleaner.cat_cache` | App cache (this app) | Cache (ta aplikacja) |
| `cleaner.cat_apk` | Leftover APK files | Pozostałe pliki APK |
| `cleaner.cat_temp` | Temp & log files | Pliki tymczasowe i logi |
| `cleaner.cat_empty` | Empty folders | Puste foldery |
| `cleaner.safe` | SAFE | BEZPIECZNE |
| `cleaner.confirm` | CONFIRM | POTWIERDŹ |
| `cleaner.honest_title` | No fake gigabytes. | Bez fake-gigabajtów. |
| `cleaner.honest_body` | We show the real amount you can free. | Pokazujemy realnie zwolnione MB. |
| `cleaner.clean` | CLEAN 2.4 GB | WYCZYŚĆ 2.4 GB |
| `tools.title` | Tools | Narzędzia |
| `tools.group_files` | FILES & STORAGE | PLIKI I PAMIĘĆ |
| `tools.group_apps` | APPS | APLIKACJE |
| `tools.group_system` | SYSTEM | SYSTEM |
| `tool.duplicates` | Duplicates | Duplikaty |
| `tool.large_files` | Large files | Duże pliki |
| `tool.recycle` | Recycle bin | Kosz |
| `tool.recycle_sub` | 7 items | 7 elementów |
| `tool.hidden` | Hidden cache | Ukryta pamięć |
| `tool.files` | Folder analyzer | Analiza folderów |
| `tool.files_sub` | SAF | SAF |
| `tool.shredder` | Shredder | Niszczarka |
| `tool.usage` | Screen time | Czas ekranowy |
| `tool.insights` | App insights | Wgląd w apki |
| `tool.insights_sub` | 7-day | 7 dni |
| `tool.vault` | App vault | Sejf |
| `tool.memory` | Memory | Pamięć RAM |
| `tool.battery` | Battery | Bateria |
| `tool.alarms` | Battery alarms | Alarmy baterii |
| `insights.title` | App insights | Wgląd w apki |
| `insights.weekly_total` | SCREEN TIME (7 DAYS) | CZAS EKRANOWY (7 DNI) |
| `insights.recent` | RECENTLY INSTALLED | OSTATNIO ZAINSTALOWANE |
| `insights.installed` | Installed | Zainstalowano |
| `insights.updated` | Updated | Zaktualizowano |
| `insights.hidden` | APPS WITHOUT A LAUNCHER | APLIKACJE BEZ LAUNCHERA |
| `day.mon` | Mon | Pon |
| `day.tue` | Tue | Wt |
| `day.wed` | Wed | Śr |
| `day.thu` | Thu | Czw |
| `day.fri` | Fri | Pt |
| `day.sat` | Sat | Sob |
| `day.sun` | Sun | Nd |
| `vault.title` | App vault | Sejf |
| `vault.banner_title` | Encrypted on-device sandbox | Zaszyfrowany sandbox |
| `vault.banner_body1` | AES/GCM with an Android Keystore key. | AES/GCM z kluczem w Keystore. |
| `vault.banner_body2` | Nothing leaves this device. | Nic nie opuszcza urządzenia. |
| `vault.locked` | Locked | Zablokowane |
| `vault.locked_sub` | Authenticate to view contents. | Uwierzytelnij, by zobaczyć zawartość. |
| `vault.unlock` | Unlock with biometrics | Odblokuj biometrią |
| `vault.add_file` | + Add file (encrypted) | + Dodaj plik (zaszyfrowany) |
| `vault.disclaimer1` | Key bound to this device — reset wipes vault. | Klucz powiązany z urządzeniem — reset = utrata sejfu. |
| `vault.disclaimer2` | Back up sensitive files externally. | Wrażliwe pliki backupuj osobno. |
| `nav.dashboard` | Dashboard | Pulpit |
| `nav.cleaner` | Clean | Czyszczenie |
| `nav.storage` | Storage | Pamięć |
| `nav.apps` | Apps | Aplikacje |
| `nav.tools` | Tools | Narzędzia |

**Szybki sposób na 2 wersje**: skopiuj cały katalog `assets/screens/` do `assets/screens-pl/` i podmień napisy w nowych plikach (np. sed-em).

Skrypt do automatycznej generacji wersji polskiej:

```bash
mkdir -p assets/screens-pl
for f in assets/screens/*.svg; do
  name=$(basename "$f")
  sed -e 's|>Device health<|>Stan urządzenia<|' \
      -e 's|>HEALTH SCORE<|>KONDYCJA<|' \
      -e 's|>STORAGE<|>PAMIĘĆ<|' \
      -e 's|>RAM<|>RAM<|' \
      -e 's|>BATTERY<|>BATERIA<|' \
      -e 's|>DEVICE<|>URZĄDZENIE<|' \
      -e 's|>RUN HEALTH CHECK<|>SPRAWDŹ KONDYCJĘ<|' \
      -e 's|>Junk cleaner<|>Czyszczenie<|' \
      -e 's|>RECLAIMABLE<|>DO ODZYSKANIA<|' \
      -e 's|>Tools<|>Narzędzia<|' \
      -e 's|>Dashboard<|>Pulpit<|' \
      -e 's|>Clean<|>Czyszczenie<|' \
      -e 's|>Apps<|>Aplikacje<|' \
      -e 's|>App insights<|>Wgląd w apki<|' \
      -e 's|>App vault<|>Sejf<|' \
      -e 's|>Locked<|>Zablokowane<|' \
      -e 's|>Mon<|>Pon<|;s|>Tue<|>Wt<|;s|>Wed<|>Śr<|;s|>Thu<|>Czw<|;s|>Fri<|>Pt<|;s|>Sat<|>Sob<|;s|>Sun<|>Nd<|' \
      "$f" > "assets/screens-pl/$name"
done
```

## Co wgrać do Google Play Console

1. **Ikona aplikacji**: `icon-512.png` (512×512 PNG, max 1 MB, nieprzezroczyste)
2. **Grafika promocyjna (feature graphic)**: `feature-graphic.png` (1024×500 PNG/JPG)
3. **Screenshoty telefonu** (min 2, max 8):
   - Wgraj 5 PNG-ów z folderu `store-listing/` przekonwertowanych z SVG przez `rsvg-convert -w 1080 -h 2220`
   - Wgraj osobno dla wersji EN i PL (zakładka „Add language" → Polish)
4. **Tytuł i opis**: skopiuj z `description-pl.md` (dla PL) i `description-en.md` (dla EN)
5. **Link do polityki prywatności**: `https://freeandroiddoctor.pl/privacy.html`

## Inne sklepy

- **Samsung Galaxy Store** (seller.samsungapps.com) — przyjmuje te same assety
- **Amazon Appstore** (developer.amazon.com) — przyjmuje te same, screenshot min 800×480
- **APKPure** — wystarczy AAB/APK i opis
- **F-Droid** — wymaga FOSS bez AdMob/billingu (potencjalnie osobny build flavor w przyszłości)
