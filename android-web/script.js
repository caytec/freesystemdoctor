/* FreeAndroidDoctor Android landing — interactions */
(() => {
  'use strict';

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isTouch = window.matchMedia('(hover: none), (pointer: coarse)').matches;

  /* ─── 1. Custom cursor with eased follow (lerp) ─── */
  if (!isTouch) {
    const dot  = document.querySelector('.cursor-dot');
    const ring = document.querySelector('.cursor-ring');
    if (dot && ring) {
      let mx = window.innerWidth / 2, my = window.innerHeight / 2;
      let dx = mx, dy = my;          // dot — fast
      let rx = mx, ry = my;          // ring — lags
      window.addEventListener('mousemove', (e) => { mx = e.clientX; my = e.clientY; });

      const tick = () => {
        dx += (mx - dx) * 0.55;
        dy += (my - dy) * 0.55;
        rx += (mx - rx) * 0.18;
        ry += (my - ry) * 0.18;
        dot.style.transform  = `translate(${dx}px, ${dy}px) translate(-50%, -50%)`;
        ring.style.transform = `translate(${rx}px, ${ry}px) translate(-50%, -50%)`;
        requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);

      const hoverSel = 'a, button, summary, .phone-frame, .card, input';
      document.querySelectorAll(hoverSel).forEach((el) => {
        el.addEventListener('mouseenter', () => document.body.classList.add('cursor-hover'));
        el.addEventListener('mouseleave', () => document.body.classList.remove('cursor-hover'));
      });
    }
  }

  /* ─── 2. Parallax for elements with [data-depth] ─── */
  if (!prefersReduced) {
    const parallax = document.querySelectorAll('.parallax');
    let ticking = false;
    const update = () => {
      const y = window.scrollY;
      parallax.forEach((el) => {
        const depth = parseFloat(el.dataset.depth || '0.1');
        el.style.transform = `translate3d(0, ${y * depth}px, 0)`;
      });
      ticking = false;
    };
    window.addEventListener('scroll', () => {
      if (!ticking) { requestAnimationFrame(update); ticking = true; }
    }, { passive: true });
  }

  /* ─── 3. Reveal on scroll ─── */
  if (!prefersReduced && 'IntersectionObserver' in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -10% 0px', threshold: 0.05 });
    document.querySelectorAll('.reveal').forEach((el) => io.observe(el));
  } else {
    document.querySelectorAll('.reveal').forEach((el) => el.classList.add('in'));
  }

  /* ─── 4. Language toggle (PL <-> EN) ─── */
  const I18N = {
    pl: {
      // already in HTML as defaults
    },
    en: {
      'nav.features': 'Features',
      'nav.screens':  'Screens',
      'nav.download': 'Download',
      'nav.faq':      'FAQ',

      'hero.badge':       '⚡ Version 1.2 · FOSS · MIT License',
      'hero.title1':      'Your phone',
      'hero.title2':      'deserves an honest cleaner.',
      'hero.sub':         'No fake RAM-boosters. No data harvesting. No subscriptions. 25+ tools that work just as well as their "premium" rivals.',
      'hero.cta_download':'⬇ Download latest APK',
      'hero.cta_more':    'See features',
      'hero.meta_android':'Android 8.0+ · arm64 / arm32 / x86_64',
      'hero.meta_lang':   '🇵🇱 PL · 🇬🇧 EN',

      'stats.tools':    'tools',
      'stats.trackers': 'trackers',
      'stats.price':    'forever',
      'stats.foss':     'open source',

      'why.title1':'Why not just',
      'why.title2':'an ad-promoted "phone booster"?',
      'why.lead':  '99% of free cleaners on Play Store sell your data, show fake "1.5 GB cleaned!" numbers, and pummel you with fullscreen ads. We don\'t. Check the code.',
      'why.c1.t':'Zero data selling',
      'why.c1.b':'Ads exist (AdMob, optionally disabled in Pro), but we never touch your files, contacts, or SMS beyond what you explicitly export.',
      'why.c2.t':'No fake gigabytes',
      'why.c2.b':'We show the actual MB freed, not inflated marketing numbers. No "RAM booster" — it doesn\'t work on modern Android.',
      'why.c3.t':'Every line public',
      'why.c3.b':'All code on GitHub, MIT licensed. Build the APK yourself, audit it, fork it. No binary "magic" engines.',
      'why.c4.t':'No root required',
      'why.c4.b':'Everything via official Android APIs, no system mods. Safe, warranty intact, runs on stock ROMs.',
      'why.c5.t':'Full PL + EN',
      'why.c5.b':'Not one of those apps with "Translate-quality" Polish. PL is first-class.',
      'why.c6.t':'Modern stack',
      'why.c6.b':'Kotlin + Jetpack Compose + Material 3. Animated UI, brand splash, smooth 60+ FPS on any reasonable phone from the last 5 years.',

      'feat.title1':'What you get',
      'feat.title2':'in one app.',
      'feat.g_files':'📁 Files & storage',
      'feat.g_apps': '📦 Apps',
      'feat.g_sys':  '⚙️ System & network',
      'feat.f1.t':'Cleaner','feat.f1.b':'own cache + leftover APK + temp/log via MediaStore',
      'feat.f2.t':'Duplicates','feat.f2.b':'SHA-256, grouped by hash',
      'feat.f3.t':'Large files','feat.f3.b':'filter by type and size',
      'feat.f4.t':'Storage by type','feat.f4.b':'images, video, audio, documents, archives',
      'feat.f5.t':'Folder analyzer','feat.f5.b':'SAF, empty folders, size tree',
      'feat.f6.t':'Recycle bin','feat.f6.b':'Android 11+ MediaStore trash, restore and permanent delete',
      'feat.f7.t':'Hidden caches','feat.f7.b':'presets for WhatsApp, Telegram, Spotify, Discord, IG, TikTok…',
      'feat.f8.t':'Shredder','feat.f8.b':'DoD 5220.22-M, multi-pass overwrite',
      'feat.a1.t':'App manager','feat.a1.b':'sort by size, filter system apps',
      'feat.a2.t':'Screen time','feat.a2.b':'7 days, per-app',
      'feat.a3.t':'Rarely used','feat.a3.b':'apps not opened in 30+ days',
      'feat.a4.t':'Permission audit','feat.a4.b':'apps with mic, camera, location, etc.',
      'feat.a5.t':'APK backup','feat.a5.b':'export an installed app to .apk',
      'feat.a6.t':'Contacts + SMS backup','feat.a6.b':'.vcf + .json to Downloads',
      'feat.a7.t':'App vault','feat.a7.b':'AES/GCM + AndroidKeystore + BiometricPrompt',
      'feat.a8.t':'App insights','feat.a8.b':'7-day chart, recent installs, apps without launcher',
      'feat.s1.t':'Memory','feat.s1.b':'real free RAM, no force-kill',
      'feat.s2.t':'Battery','feat.s2.b':'level, temperature, voltage, current (mA)',
      'feat.s3.t':'Battery alarms','feat.s3.b':'low/full thresholds, every 15 min',
      'feat.s4.t':'Speed test','feat.s4.b':'10 MB sample, real Mb/s',
      'feat.s5.t':'Wi-Fi analyzer','feat.s5.b':'SSID, channel, RSSI',
      'feat.s6.t':'Data usage','feat.s6.b':'mobile + Wi-Fi over last 30 days',
      'feat.s7.t':'Device info','feat.s7.b':'SoC, ABI, sensors, security patch',
      'feat.s8.t':'AI assistant','feat.s8.b':'Your API key (Groq/OpenRouter/Cerebras), nothing sent without consent',

      'scr.title1':'This is',
      'scr.title2':'what it looks like.',
      'scr.lead':  'Material 3, animated backdrop, glass cards, pull-to-refresh, shimmer skeletons.',

      'cmp.title1':'Honest',
      'cmp.title2':'comparison.',
      'cmp.feature':'Feature',
      'cmp.r1':'Free everything',
      'cmp.r2':'Open source',
      'cmp.r3':'No telemetry',
      'cmp.r4':'No fake RAM-boost',
      'cmp.r5':'Recycle bin',
      'cmp.r6':'Biometric vault',
      'cmp.r7':'AI assistant',
      'cmp.r8':'Polish language',

      'dl.title1':'Download',
      'dl.title2':'and see for yourself.',
      'dl.lead':  'Latest APK from GitHub Releases. No signup, no store, no Google account. Just download and install (enable "install from unknown sources").',
      'dl.btn_apk':'⬇ Latest APK',
      'dl.btn_source':'★ Source code',
      'dl.n1.t':'Requirements:','dl.n1.b':'Android 8.0 (API 26) or newer, ~50 MB free',
      'dl.n2.t':'Verification:','dl.n2.b':'Check SHA-256 after download (hashes in release notes on GitHub)',
      'dl.n3.t':'Coming soon:','dl.n3.b':'Google Play, Samsung Galaxy Store, Amazon Appstore, F-Droid',

      'faq.title1':'Frequently asked',
      'faq.title2':'questions.',
      'faq.q1':'Is this really free?',
      'faq.a1':'Yes, fully. We have ads (AdMob) and optional Pro for a one-time donation — Pro removes ads and unlocks 4 tools (Vault, Battery alarms, App Insights, Shredder). Everything else is free, unlimited.',
      'faq.q2':'Does the app sell my data?',
      'faq.a2':'No. AdMob is Google\'s standard ad SDK (shows personalized ads based on your ad ID — you can disable that in Android settings). The app itself doesn\'t log anything to any server, has no telemetry, no user accounts.',
      'faq.q3':'Why no "RAM Boost"?',
      'faq.a3':'Because on modern Android (7.0+), force-stopping apps to "free RAM" actually backfires — the system reloads them moments later, wasting battery. All known "boosters" are placebo or harmful. We show actual free RAM without lies.',
      'faq.q4':'Do I need root?',
      'faq.a4':'No. Everything works on stock Android 8.0+ via official APIs. Some features (clearing other apps\' caches) are limited by the system — that\'s an Android 7.0+ restriction, not ours.',
      'faq.q5':'Why not on Google Play yet?',
      'faq.a5':'We\'re working on Google Play, Samsung Galaxy Store and other markets. For now, get the APK directly from GitHub Releases — same file, just without the middleman.',
      'faq.q6':'Security? Can I trust it?',
      'faq.a6':'All code is public on GitHub. Read every line, build the APK yourself (instructions in README), compare hashes. The encrypted vault uses AES/GCM with a key in Android Keystore (TEE/StrongBox) — the key never leaves the security chip.',
      'faq.q7':'How can I help the project?',
      'faq.a7':'Four ways: ⭐ star on GitHub, ✍️ file bugs/suggestions as Issues, 🌍 fix or add a translation, 💖 buy Pro in-app.',
      'faq.q8':'And the Windows version?',
      'faq.a8':'It exists — much bigger, 62 modules. See <a href="https://freesystemdoctor.pl">freesystemdoctor.pl</a>.',

      'footer.tag':'FOSS · MIT License · 2026',
      'footer.privacy':'Privacy policy',
      'footer.bugs':'Report a bug',
      'footer.windows':'Windows version',
    },
  };

  // Cache original (PL) values so we can toggle back.
  const cache = new WeakMap();
  document.querySelectorAll('[data-i18n]').forEach((el) => cache.set(el, el.innerHTML));

  function apply(lang) {
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-i18n]').forEach((el) => {
      const key = el.dataset.i18n;
      if (lang === 'pl') {
        const original = cache.get(el);
        if (original !== undefined) el.innerHTML = original;
      } else {
        const v = I18N.en[key];
        if (v !== undefined) el.innerHTML = v;
      }
    });
    const btn = document.getElementById('lang-toggle');
    if (btn) btn.textContent = lang === 'pl' ? 'EN' : 'PL';
    try { localStorage.setItem('fsd-lang', lang); } catch (_) {}
    const url = new URL(window.location.href);
    if (lang === 'en') url.searchParams.set('lang', 'en'); else url.searchParams.delete('lang');
    window.history.replaceState({}, '', url.toString());
  }

  // Initial language: URL ?lang=, then localStorage, then PL.
  const urlLang = new URLSearchParams(window.location.search).get('lang');
  let stored = null;
  try { stored = localStorage.getItem('fsd-lang'); } catch (_) {}
  const initial = (urlLang === 'en' || urlLang === 'pl') ? urlLang : (stored || 'pl');
  if (initial !== 'pl') apply(initial);

  const toggleBtn = document.getElementById('lang-toggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      apply(document.documentElement.lang === 'pl' ? 'en' : 'pl');
    });
  }

  /* ─── 5. Download button: prefer the most recent release tag.
         Falls back to the /releases/latest URL which GitHub auto-redirects. ─── */
  // (No-op for now; GitHub /releases/latest already works. Could be extended
  //  to fetch the API and link straight to the .apk asset.)
})();
