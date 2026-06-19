# FreeAndroidDoctor

> Polska aplikacja do czyszczenia, audytu prywatności i optymalizacji telefonu z Androidem. Wszystko działa lokalnie — bez kont, bez śledzenia, bez kompromisów.

[![Android 8.0+](https://img.shields.io/badge/Android-8.0%2B-3DDC84?logo=android&logoColor=white)](https://github.com/caytec/FreeAndroidDoctor/releases)
[![Version](https://img.shields.io/badge/version-2.0.0-green)](https://github.com/caytec/FreeAndroidDoctor/releases/latest)
[![Download APK](https://img.shields.io/badge/Download-APK%204MB-4ade80?logo=android&logoColor=white)](https://github.com/caytec/FreeAndroidDoctor/releases/latest/download/FreeAndroidDoctor-free.apk)

🌐 **Strona projektu:** [caytec.github.io/FreeAndroidDoctor](https://caytec.github.io/FreeAndroidDoctor) · [Polityka prywatności](https://caytec.github.io/FreeAndroidDoctor/privacy-android.html)

## 🚀 Pobierz teraz

📥 **[Pobierz najnowszą wersję (APK, 4 MB)](https://github.com/caytec/FreeAndroidDoctor/releases/latest)**

Wymagania: Android 8.0+ · 15 MB miejsca · brak konta wymagany

## 🎯 Co potrafi

### 🧹 Inteligentne czyszczenie
Automatyczne wykrywanie cache, duplikatów zdjęć, pozostałości po odinstalowanych aplikacjach (CorpseFinder), śmieciowych plików logów. Odzyskaj kilka GB w minutę.

### 🛡️ Audyt prywatności
- **Privacy Score** — punktowa ocena bezpieczeństwa telefonu (0–100)
- **Skaner APK** z bazą znanych trackerów
- **3 profile**: Balanced / Strict / Game Mode
- **Czyszczenie 15+ przeglądarek** (Chrome, Firefox, Brave, Opera, Edge…)
- Kontrola DNS i blokada śledzenia

### ⚡ Tryby i automatyzacja
- **Game / Travel / Focus / Privacy Mode** — jeden przełącznik konfiguruje pół telefonu
- **Auto-reguły** wyzwalane zdarzeniami (niski poziom pamięci, ładowanie, Wi-Fi, godzina)

### 📊 Bateria i wydajność
- Historia cykli ładowania z oceną zdrowia akumulatora
- Monitor zużycia CPU, RAM i temperatury w czasie rzeczywistym
- Ranking aplikacji najbardziej żarłocznych

### 🤖 Asystent AI (opcjonalnie)
Integracja z **Cerebras**, **Groq**, **OpenRouter** — podajesz własny klucz API, dostajesz spersonalizowane rekomendacje. Pełna prywatność — klucz lokalnie, zero pośrednika.

## 🔒 Prywatność

**FreeAndroidDoctor przetwarza wszystkie dane lokalnie na Twoim telefonie.**

- ❌ Nie wymaga konta użytkownika
- ❌ Nie wysyła Twoich plików, kontaktów ani statystyk
- ❌ Nie zbiera danych poza standardowym Advertising ID (tylko w wersji Free, do reklam AdMob)
- ✅ Pełna zgodność z RODO
- ✅ Pełna [polityka prywatności](https://caytec.github.io/FreeAndroidDoctor/privacy-android.html)

## 💎 Wersje aplikacji

| Funkcja | Free | PRO |
|---|---|---|
| Czyszczenie systemu | ✅ | ✅ |
| Audyt prywatności | ✅ (3/dzień) | ✅ bez limitu |
| Tryby pracy | ✅ (1/dzień) | ✅ bez limitu |
| Czyszczenie przeglądarek | ✅ (1×/dzień) | ✅ bez limitu |
| Asystent AI | ✅ | ✅ |
| Reklamy | tak (AdMob) | brak |
| Automatyzacja zaawansowana | — | ✅ |

**Cennik PRO**: 9,99 zł/mies · 49,99 zł/rok · 99 zł jednorazowo (Lifetime)

## 📲 Instalacja

1. Pobierz APK z [zakładki Releases](https://github.com/caytec/FreeAndroidDoctor/releases/latest)
2. Otwórz pobrany plik na telefonie
3. Zezwól na instalację z nieznanego źródła (jednorazowo dla Twojej przeglądarki)
4. Zainstaluj i uruchom — gotowe!

## 🛠️ Budowanie ze źródeł

Wymagania: Android Studio Hedgehog+ · JDK 17 · Android SDK 35

```bash
git clone https://github.com/caytec/FreeAndroidDoctor.git
cd FreeAndroidDoctor/android
cp admob.properties.template admob.properties  # wklej własne unit IDs (lub zostaw test IDs Google)
./gradlew :app:assembleFreeDebug
```

APK ląduje w `android/app/build/outputs/apk/free/debug/`.

## 🤝 Wkład

Pull requesty mile widziane. Przed otwarciem PR:

```bash
./gradlew :app:testFreeDebugUnitTest
./gradlew :app:lintFreeDebug
```

## 📄 Licencja

Proprietary © 2026 caytec. Kod publicznie dostępny do wglądu, audytu bezpieczeństwa i edukacji. Komercyjne wykorzystanie, redystrybucja lub modyfikacja wymagają pisemnej zgody autora.

## 📬 Kontakt

- **Bug reports / feature requests**: [GitHub Issues](https://github.com/caytec/FreeAndroidDoctor/issues)
- **Email**: coopaisolutions@gmail.com
- **Wersja Windows (osobny produkt)**: [freesystemdoctor.pl](https://freesystemdoctor.pl)
