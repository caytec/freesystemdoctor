# FreeSystemDoctor — Android

Darmowa aplikacja do czyszczenia i dbania o telefon z Androidem — odpowiednik windowsowego
FreeSystemDoctor. **Nie wymaga roota.** Kotlin + Jetpack Compose (Material 3), polski i angielski.

A free, no-root phone cleaning & maintenance app — the Android counterpart of the Windows
FreeSystemDoctor. Kotlin + Jetpack Compose (Material 3), Polish & English.

## Funkcje główne / Core features

| Ekran | Co robi | Wymagane uprawnienia |
|-------|---------|----------------------|
| **Dashboard / Pulpit** | Pamięć, RAM, bateria (poziom/temp/napięcie), info o urządzeniu, wynik kondycji | brak |
| **Cleaner / Czyszczenie** | Czyszczenie własnego cache + pliki APK/.tmp/.log (MediaStore, z potwierdzeniem) | media (do mediów) |
| **Storage / Pamięć** | Podział wolumenu + rozmiary app/data/cache per aplikacja | dostęp do statystyk użycia |
| **Apps / Aplikacje** | Lista aplikacji wg rozmiaru/nazwy, odinstalowanie, deep-link do ustawień (force-stop/clear cache) | dostęp do statystyk użycia |
| **Tools / Narzędzia** | Hub z dodatkowymi narzędziami (poniżej) | zależnie od narzędzia |

## Narzędzia (hub Tools)

| Narzędzie | Co robi | Uprawnienia |
|-----------|---------|-------------|
| **Duplikaty plików** | Wykrywa identyczne pliki (rozmiar → SHA-256), usuwa nadmiarowe z potwierdzeniem | media |
| **Duże pliki** | Lista największych plików multimedialnych, kasowanie pojedynczo | media |
| **Pamięć wg typu** | Zużycie wg obrazów/wideo/audio/dokumentów/archiwów | media |
| **Czas ekranowy** | Czas użycia aplikacji na pierwszym planie (7 dni) | dostęp do statystyk użycia |
| **Rzadko używane** | Aplikacje nieuruchamiane od 30 dni + szybkie odinstalowanie | dostęp do statystyk użycia |
| **Audyt uprawnień** | Aplikacje z przyznanymi uprawnieniami wrażliwymi | brak |
| **Backup APK** | Eksport APK zainstalowanej aplikacji do Pobranych | brak |
| **Czyszczenie schowka** | Czyści schowek systemowy | brak |
| **Harmonogram** | Automatyczne czyszczenie cache + powiadomienie (WorkManager) | powiadomienia |
| **Asystent AI** | Analiza kondycji urządzenia przez LLM (klucz API użytkownika) | internet |

Dodatkowo: **kafelek Szybkich ustawień** (szybkie czyszczenie cache) i **widżet ekranu głównego**
(wolne miejsce + przycisk czyszczenia).

## Narzędzia zaawansowane (Wave 2)

Część funkcji wymaga uprawnień wrażliwych i jest ukryta za przełącznikiem **„Tryb zaawansowany"**
w Ustawieniach (domyślnie wyłączony).

| Narzędzie | Co robi | Uprawnienia |
|-----------|---------|-------------|
| **Analiza folderów** | SAF: rozmiar folderu, przeglądanie, usuwanie pustych folderów | dostęp do folderu (SAF) |
| **Zużycie danych** | Dane komórkowe + Wi-Fi per aplikacja (`NetworkStatsManager`) | dostęp do statystyk użycia |
| **Info o urządzeniu** | Model, jądro, patch, CPU (taktowanie), ABI, lista czujników | brak |
| **Niszczarka plików** *(zaawansowane)* | Nadpisanie losowymi danymi + usunięcie (best-effort) | dostęp do pliku (SAF) |
| **Dostrojenia systemu** *(zaawansowane)* | Deep-linki: optymalizacja baterii, zużycie danych, autostart OEM | — |
| **Monitor na pasku stanu** *(zaawansowane)* | Trwałe powiadomienie z RAM i wolnym miejscem | usługa pierwszoplanowa, powiadomienia |

## Narzędzia do zdjęć i sieci (Wave 3)

| Narzędzie | Co robi | Uprawnienia |
|-----------|---------|-------------|
| **Podobne zdjęcia** | Grupuje wizualnie podobne zdjęcia (hash percepcyjny aHash + Hamming), usuwa nadmiarowe | media |
| **Zrzuty i rozmyte** | Wykrywa zrzuty ekranu (ścieżka/nazwa) i rozmyte zdjęcia (wariancja Laplace'a) | media |
| **Kompresja zdjęć** | Tworzy mniejsze kopie JPEG w Pictures/FreeSystemDoctor (oryginał zostaje) | media |
| **Analizator WiFi** *(zaawansowane)* | Sieci w pobliżu: pasmo, kanał, siła, zabezpieczenie | lokalizacja, stan WiFi |
| **Menedżer powiadomień** *(zaawansowane)* | Przegląd i odrzucanie aktywnych powiadomień | dostęp do powiadomień |

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

## Roadmap (kolejne fale)

Funkcje wymagające uprawnień wrażliwych będą ukryte za przełącznikiem **„Tryb zaawansowany"**
(domyślnie wyłączony), z jasnym wyjaśnieniem.

## Dodatkowe narzędzia (Wave 4)

| Narzędzie | Co robi | Uprawnienia |
|-----------|---------|-------------|
| **Pamięć RAM** | Realne zużycie + uczciwe „zwolnij aplikacje w tle" (bez zawyżania) | brak |
| **Bateria** | Poziom, status, temperatura, napięcie, technologia, licznik ładunku + wyłączenie optymalizacji | brak |
| **Test prędkości** | Pomiar prędkości pobierania (plik testowy 10 MB) | internet |
| **Duplikaty audio** | Filtr „tylko audio" w ekranie duplikatów | media |
| **Duże wideo** | Filtr „tylko wideo" w ekranie dużych plików | media |

## Kopia zapasowa (Wave 5)

| Narzędzie | Co robi | Uprawnienia |
|-----------|---------|-------------|
| **Kopia kontaktów i SMS** *(zaawansowane)* | Wykrywanie duplikatów kontaktów, eksport kontaktów do vCard (.vcf) i SMS-ów do JSON w Pobranych | kontakty, SMS |

Tylko odczyt — nic nie jest zmieniane, usuwane ani wysyłane. Funkcja za „Trybem zaawansowanym".

## Monetyzacja / Monetization

Model freemium zgodny z zasadami Google Play:

- **Reklamy AdMob** (tylko dla użytkowników bez Pro, po zgodzie UMP):
  - Baner adaptacyjny na dole wszystkich ekranów
  - Reklama pełnoekranowa po zakończonym czyszczeniu i przy wchodzeniu w narzędzia (limit 1/45 s)
  - **Reklama app-open** przy powrocie do aplikacji (limit 1/4 min, nigdy przy starcie ani nad oknami systemu)
  - Reklama nagradzana: odblokowanie narzędzi zaawansowanych na 24h
- **Google Play Billing** — „Pro":
  - Subskrypcja miesięczna (`fsd_pro_monthly`) i roczna (`fsd_pro_yearly`)
  - Zakup dożywotni (`fsd_pro_lifetime`)
  - Pro = brak reklam + wszystkie narzędzia zaawansowane + harmonogram + monitor
- **Zgoda UMP** (User Messaging Platform) uruchamiana przed reklamami (wymóg EOG/UK).

Tryb zaawansowany jest teraz odblokowywany przez Pro **lub** reklamę nagradzaną (24h), zamiast
zwykłego przełącznika.

### Bezpieczeństwo dla Play (agresywne, ale w granicach polityki)

Reklamy są agresywne, ale każda z nich respektuje zasady Google Play:
- pełnoekranowe i app-open **tylko w naturalnych punktach przejścia** (nigdy podczas ładowania,
  podczas akcji, ani przy zamykaniu aplikacji),
- **limity częstotliwości** (pełnoekranowa 1/45 s, app-open 1/4 min),
- app-open **nie pojawia się przy pierwszym uruchomieniu** ani gdy wracasz z okien wywołanych przez
  apkę (płatność, dialog usuwania) — mechanizm `suppressNextShow`,
- nigdy nie nakładają się dwie reklamy naraz,
- brak reklam dla użytkowników Pro i przed uzyskaniem zgody UMP.

### Jak zarejestrować się w sieciach reklamowych

Najłatwiejsza i najbezpieczniejsza dla Play jest **Google AdMob** (już zintegrowana):
1. Wejdź na **admob.google.com**, zaloguj kontem Google, „Zarejestruj się" → zaakceptuj warunki.
2. **Apps → Add app** → Android → wpisz nazwę (apkę możesz dodać przed publikacją w Play).
3. **Ad units → Create** dla każdego formatu: Banner, Interstitial, Rewarded, App open.
4. Skopiuj **App ID** i 4 **Ad unit ID** do `strings.xml` (`admob_app_id`) i `ads/AdUnits.kt`.
5. W **Privacy & messaging** skonfiguruj komunikat zgody (UMP) — kod już go wywołuje.
6. Podłącz konto **AdSense/płatności** (wypłaty po progu 100 USD/EUR).

Aby zwiększyć wypełnienie i przychód, włącz **AdMob Mediation** (bez dodatkowego kodu poza
adapterami) — najłatwiejsze do dołączenia sieci z niskim progiem wejścia:
- **AppLovin (MAX/AppLovin)** — szybka akceptacja, wysokie wypełnienie.
- **Unity Ads** — łatwa rejestracja (unity.com), dobre dla nagradzanych.
- **Liftoff/Vungle**, **Mintegral**, **Pangle (TikTok)** — łatwe, wysokie eCPM na reklamy wideo.
- **Start.io (dawniej StartApp)** — bardzo niski próg wejścia, akceptuje małe aplikacje.
- **Meta Audience Network** — wyższe stawki, ale trudniejsza/wolniejsza weryfikacja.

W AdMob: **Mediation → Create mediation group** dla każdego formatu, dodaj powyższe sieci,
wklej ich identyfikatory i (w razie potrzeby) pobierz adaptery przez Gradle. Sam kod apki
się nie zmienia — AdMob pełni rolę pośrednika.

### Konfiguracja przed publikacją (Play Console / AdMob)

Kod używa **testowych** ID AdMob (bezpieczne w developmencie). Przed wydaniem produkcyjnym:

1. **AdMob:** utwórz konto, aplikację i jednostki reklamowe; podmień:
   - `res/values/strings.xml` → `admob_app_id` (App ID)
   - `ads/AdUnits.kt` → `BANNER`, `INTERSTITIAL`, `REWARDED`
   ⚠️ Klikanie własnych żywych reklam = strike. Nie używaj prawdziwych ID w testach.
2. **Play Console → Monetyzacja:** utwórz produkty o ID `fsd_pro_monthly`, `fsd_pro_yearly`
   (subskrypcje) i `fsd_pro_lifetime` (produkt jednorazowy), ustaw ceny.
3. **Polityka prywatności** (wymagana przy reklamach) + formularz **Bezpieczeństwo danych**
   (Data safety) w Play Console (zbierany Advertising ID).
4. Reklamy serwowane są dopiero po zgodzie UMP — skonfiguruj komunikat o prywatności w AdMob.

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
