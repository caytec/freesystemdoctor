# FreeSystemDoctor — Android

Darmowa aplikacja do czyszczenia i dbania o telefon z Androidem — odpowiednik windowsowego
FreeSystemDoctor. **Nie wymaga roota.** Kotlin + Jetpack Compose (Material 3), polski i angielski.

A free, no-root phone cleaning & maintenance app — the Android counterpart of the Windows
FreeSystemDoctor. Kotlin + Jetpack Compose (Material 3), Polish & English.

## Funkcje MVP / MVP features

| Ekran | Co robi | Wymagane uprawnienia |
|-------|---------|----------------------|
| **Dashboard / Pulpit** | Pamięć, RAM, bateria (poziom/temp/napięcie), info o urządzeniu, wynik kondycji | brak |
| **Cleaner / Czyszczenie** | Czyszczenie własnego cache + pliki APK/.tmp/.log (MediaStore, z potwierdzeniem) | media (do mediów) |
| **Storage / Pamięć** | Podział wolumenu + rozmiary app/data/cache per aplikacja | dostęp do statystyk użycia |
| **Apps / Aplikacje** | Lista aplikacji wg rozmiaru/nazwy, odinstalowanie, deep-link do ustawień (force-stop/clear cache) | dostęp do statystyk użycia |
| **Assistant / Asystent** | Analiza lokalnego obrazu kondycji urządzenia przez LLM (klucz API użytkownika) | internet (tylko przy analizie) |

## Czego NIE da się zrobić bez roota (świadome ograniczenia)

- **Czyszczenie cache innych aplikacji jednym kliknięciem** — niemożliwe od API 24. Aplikacja kieruje
  do ustawień każdej apki, gdzie użytkownik czyści ręcznie.
- **„RAM boost"** — na nowoczesnym Androidzie nieskuteczny; pokazujemy realne zużycie RAM zamiast
  fałszywego boostera.
- **Temperatura CPU** — praktycznie nieczytelna bez roota.
- **Zużycie baterii (mAh wear)** — nie jest wiarygodnie eksponowane; pokazujemy poziom/temp/napięcie.
- **Kasowanie plików na pamięci współdzielonej (Android 11+)** — wymaga potwierdzenia systemowego
  (`MediaStore.createDeleteRequest`).
- **Dostęp do plików** — używamy uprawnień do mediów + SAF, a nie `MANAGE_EXTERNAL_STORAGE`
  (zgodność z Google Play).

## Roadmap (kolejne wydania)

Auto/zaplanowane czyszczenie (WorkManager), wyszukiwarka dużych plików i duplikatów w UI,
shredder plików (best-effort), menedżer powiadomień, zużycie danych per-app, czas ekranowy,
whitelist optymalizacji baterii, deep-linki autostartu OEM.

## Budowanie / Building

```bash
cd android
./gradlew assembleDebug        # buduje APK (app/build/outputs/apk/debug/)
./gradlew testDebugUnitTest    # testy jednostkowe JVM
./gradlew lintDebug            # lint
```

Wymagania: JDK 17, Android SDK (compileSdk 35). CI (`.github/workflows/android-ci.yml`) buduje APK
i uruchamia testy na każdym push/PR. Pełne testy UI oraz API systemowych (MediaStore,
StorageStatsManager, uprawnienia) wymagają fizycznego urządzenia / emulatora.

## Stack

Kotlin 2.1 (K2) · AGP 8.7.3 · Gradle 8.11.1 · Compose BOM 2024.12 · Material 3 ·
minSdk 26 · targetSdk 35 · MVVM + StateFlow · ręczny ServiceLocator (DI) · OkHttp + kotlinx.serialization (AI).
