# Google Play — listing, Data safety i checklista

Polityka prywatności (hostowana): **https://freesystemdoctor.pl/privacy-android.html**
Kontakt: coopaisolutions@gmail.com

---

## 1. Wpis w sklepie (Store listing)

### Polski

**Nazwa aplikacji (max 30 zn.):**
`FreeSystemDoctor: Czyszczenie`

**Krótki opis (max 80 zn.):**
`Czyszczenie, optymalizacja i kopie zapasowe telefonu. Bez roota, bez zbędnych danych.`

**Pełny opis:**
```
FreeSystemDoctor to lekki, uczciwy optymalizator telefonu — bez roota i bez fałszywych obietnic.

CZYSZCZENIE I PAMIĘĆ
• Skaner śmieci: cache aplikacji, pliki APK, .tmp/.log
• Duplikaty plików i podobne zdjęcia (hash percepcyjny)
• Duże pliki i duże wideo, pamięć wg typu
• Wykrywanie zrzutów ekranu i rozmytych zdjęć, kompresja zdjęć
• Analiza folderów i usuwanie pustych folderów

APLIKACJE I SYSTEM
• Menedżer aplikacji, rzadko używane, audyt uprawnień
• Czas ekranowy, zużycie danych per aplikacja
• Backup APK, kopia kontaktów (vCard) i SMS
• Szczegółowe info o urządzeniu, test prędkości łącza
• Bateria, pamięć RAM, czyszczenie schowka

AUTOMATYZACJA
• Harmonogram czyszczenia, kafelek Szybkich ustawień, widżet, monitor na pasku

UCZCIWOŚĆ
Nie udajemy „przyspieszania RAM", nie zmyślamy temperatury CPU ani zużycia baterii.
Funkcje wrażliwe są ukryte za „Trybem zaawansowanym" i wymagają Twojej zgody.

Wersja darmowa z reklamami. Pro usuwa reklamy i odblokowuje narzędzia zaawansowane.
```

### English

**App name (max 30):** `FreeSystemDoctor: Cleaner`

**Short description (max 80):**
`Clean, optimize and back up your phone. No root, no unnecessary data.`

**Full description:** (mirror of the Polish text — translate the sections:
Cleaning & storage / Apps & system / Automation / Honesty / Free with ads, Pro removes them.)

**Kategoria:** Narzędzia (Tools)
**Tagi:** cleaner, storage, optimizer, duplicate finder, file manager

---

## 2. Data safety (formularz w Play Console)

> Zasada Google: „zbierane" = wysyłane poza urządzenie. Dane przetwarzane tylko lokalnie
> (kontakty, SMS, pliki, statystyki) **nie** są zbierane i ich tu nie deklarujesz.

**Czy aplikacja zbiera lub udostępnia dane?** → **TAK** (z powodu reklam AdMob).

**Czy dane są szyfrowane w transporcie?** → TAK
**Czy użytkownik może poprosić o usunięcie danych?** → Brak kont; dane reklamowe wg polityki Google.

### Zadeklaruj następujące dane:

| Typ danych | Zbierane | Udostępniane | Cel | Wymagane? |
|------------|----------|--------------|-----|-----------|
| **Identyfikator urządzenia/reklamowy (Advertising ID)** | Tak | Tak | Reklamy / marketing | Opcjonalne (tylko free) |
| **Przybliżona lokalizacja** | Tak | Tak | Reklamy | Opcjonalne |
| **Aktywność w aplikacji** (interakcje) | Tak | Tak | Reklamy, analityka | Opcjonalne |
| **Informacje diagnostyczne / wydajność** | Tak | Tak | Reklamy, stabilność | Opcjonalne |
| **App info & performance (AI)** *(jeśli używasz asystenta)* | Tak | Tak (do dostawcy LLM wybranego przez użytkownika) | Funkcja na żądanie | Opcjonalne |

Źródło zbierania: **Google AdMob** (reklamy) oraz — tylko na żądanie — dostawca AI wskazany przez użytkownika.

**NIE deklaruj** jako zbieranych: kontaktów, SMS, plików, listy aplikacji, statystyk użycia —
są przetwarzane wyłącznie lokalnie i nie opuszczają urządzenia (eksport zapisywany jest w Pobranych
przez samego użytkownika).

### Deklaracje uprawnień wrażliwych (osobne formularze w Play Console)

- **QUERY_ALL_PACKAGES** — nie używamy (zapytania celowane). Nie wymaga deklaracji.
- **Uprawnienia do SMS/Połączeń** — używamy `READ_SMS` tylko do kopii zapasowej na żądanie.
  W Play Console wymagana **Permissions Declaration**: zaznacz „Backup and restore" jako uzasadnienie.
  ⚠️ To uprawnienie jest mocno ograniczane — jeśli chcesz uniknąć formularza, rozważ usunięcie
  funkcji eksportu SMS (kontakty vCard wystarczą).
- **All files access** — NIE używamy (tylko media + SAF), więc brak formularza.
- **Notification access / NotificationListenerService** — uzasadnij funkcją „menedżer powiadomień".
- **REQUEST_IGNORE_BATTERY_OPTIMIZATIONS** — uzasadnij niezawodnością zaplanowanego czyszczenia/monitora.

---

## 3. Reklamy i treści

- **Zawiera reklamy:** TAK (AdMob).
- **Ocena treści (IARC):** wypełnij ankietę → najpewniej PEGI 3 / Everyone.
- **Grupa docelowa:** dorośli/ogólna; NIE oznaczaj jako „dla dzieci" (używamy Advertising ID).
- **Reklamy spersonalizowane:** za zgodą UMP (EOG/UK).

---

## 4. Checklista przed wysłaniem

- [ ] Podmień testowe ID AdMob → prawdziwe (`strings.xml` `admob_app_id`, `ads/AdUnits.kt`)
- [ ] Utwórz produkty: `fsd_pro_monthly`, `fsd_pro_yearly` (subskrypcje), `fsd_pro_lifetime` (jednorazowy)
- [ ] Włącz **Play App Signing**, wgraj **AAB** (`app-release.aab`) do toru wewnętrznego
- [ ] Wklej URL polityki prywatności w Play Console i w AdMob (komunikat zgody UMP)
- [ ] Wypełnij **Data safety** wg tabeli powyżej
- [ ] Permissions Declaration dla SMS (lub usuń eksport SMS) + Notification access
- [ ] Ocena treści, grupa docelowa, kategoria „Narzędzia"
- [ ] Testy na fizycznym urządzeniu: reklamy (test), zakup w torze wewnętrznym, podstawowe funkcje
