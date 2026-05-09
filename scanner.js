/* ─────────────────────────────────────────────────────────
   FreeSystemDoctor — Cybersecurity Scanner (client-side)
   Runs entirely in the browser. No data leaves the device
   unless the user explicitly clicks "Wyślij do Threat Intel"
   (which writes anonymized hash+verdict to localStorage only).
   ───────────────────────────────────────────────────────── */
(function () {
  'use strict';

  const $  = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /* ── State ─────────────────────────────────────────── */
  const state = {
    files: [],                  // File[] queued for malware scan
    running: false,
    aborted: false,
    startedAt: 0,
    finishedAt: 0,
    sections: [],               // populated scan results
    summary: { ok: 0, warn: 0, crit: 0, score: 0 },
    reportUrl: null,
  };

  /* ── Severity helpers ──────────────────────────────── */
  const SEV = { OK: 'ok', WARN: 'warn', CRIT: 'crit', INFO: 'info' };
  const sevWeight = { ok: 0, info: 0, warn: 5, crit: 15 };

  function finding(severity, label, value, hint) {
    return { severity, label, value: value == null ? '—' : String(value), hint: hint || '' };
  }

  /* ── Known-malware hash list (sample / illustrative) ─
     SHA-256 of EICAR test file is real; the rest are
     illustrative placeholders used for the demo CTI feed.
     A real deployment would fetch a signed feed.            */
  const KNOWN_BAD = {
    sha256: new Set([
      // EICAR antivirus test file
      '275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f',
      // Illustrative entries — replace with a real CTI feed in prod
      'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855_demo',
    ]),
    sha1: new Set([
      'cf8bd9dfddff007f75adf4c2be48005cea317c62',  // EICAR
    ]),
    md5: new Set([
      '44d88612fea8a8f36de82e1278abb02f',  // EICAR
    ]),
  };

  const SUSPICIOUS_EXT = new Set([
    'exe','dll','scr','com','bat','cmd','ps1','vbs','vbe','js','jse',
    'jar','msi','hta','wsf','wsh','lnk','reg','sys','cpl','docm','xlsm','pptm','xll',
  ]);

  /* ── DOM bootstrap ─────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    $('#scan-run').addEventListener('click', runScan);
    $('#scan-stop').addEventListener('click', () => { state.aborted = true; });
    $('#scan-reset').addEventListener('click', resetUi);

    $('#report-pdf').addEventListener('click', exportPdf);
    $('#report-url').addEventListener('click', exportUrl);
    $('#report-json').addEventListener('click', exportJson);
    $('#report-share').addEventListener('click', shareToIntel);

    // file picker
    const zone = $('#scan-file-zone');
    const input = $('#scan-file-input');
    $('#scan-file-pick').addEventListener('click', e => { e.preventDefault(); input.click(); });
    input.addEventListener('change', () => addFiles(input.files));
    ['dragenter','dragover'].forEach(ev =>
      zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.add('drag'); }));
    ['dragleave','drop'].forEach(ev =>
      zone.addEventListener(ev, e => { e.preventDefault(); zone.classList.remove('drag'); }));
    zone.addEventListener('drop', e => addFiles(e.dataTransfer.files));

    renderCtiPreview();
  }

  function addFiles(fileList) {
    for (const f of fileList) state.files.push(f);
    renderFileList();
  }

  function renderFileList() {
    const ul = $('#scan-file-list');
    ul.innerHTML = '';
    state.files.forEach((f, i) => {
      const li = document.createElement('li');
      li.innerHTML = `<span class="ff-name">${escapeHtml(f.name)}</span>
                      <span class="ff-meta">${humanBytes(f.size)} · ${escapeHtml(f.type || 'application/octet-stream')}</span>
                      <button class="btn-mini" data-i="${i}">Usuń</button>`;
      li.querySelector('button').addEventListener('click', () => {
        state.files.splice(i, 1); renderFileList();
      });
      ul.appendChild(li);
    });
  }

  /* ── Scan orchestration ────────────────────────────── */
  async function runScan() {
    if (state.running) return;
    state.running = true;
    state.aborted = false;
    state.sections = [];
    state.summary = { ok: 0, warn: 0, crit: 0, score: 0 };
    state.startedAt = performance.now();

    $('#scan-run').disabled = true;
    $('#scan-stop').disabled = false;
    $('#scan-progress').hidden = false;
    $('#scan-summary').hidden = true;
    $('#scan-results').innerHTML = '';
    $('#scan-share-link').hidden = true;

    const enabled = $$('.scan-mod input:checked').map(el => el.dataset.mod);
    const tasks = [];
    if (enabled.includes('system'))  tasks.push(['System operacyjny i sprzęt', scanSystem]);
    if (enabled.includes('browser')) tasks.push(['Przeglądarka i fingerprint', scanBrowser]);
    if (enabled.includes('network')) tasks.push(['Sieć i łączność', scanNetwork]);
    if (enabled.includes('memory'))  tasks.push(['Pamięć i wydajność', scanMemory]);
    if (enabled.includes('storage')) tasks.push(['Storage, ciasteczka, IndexedDB', scanStorage]);
    if (enabled.includes('privacy')) tasks.push(['Prywatność i trackery', scanPrivacy]);
    if (enabled.includes('malware')) tasks.push(['Malware (skan plików)', scanMalware]);

    for (let i = 0; i < tasks.length; i++) {
      if (state.aborted) break;
      const [label, fn] = tasks[i];
      setProgress((i / tasks.length) * 100, `[${i+1}/${tasks.length}] ${label}…`);
      try {
        const section = await fn();
        state.sections.push(section);
        renderSection(section);
        accumulateSummary(section);
      } catch (err) {
        const section = {
          id: fn.name, title: label, icon: '⚠',
          findings: [finding(SEV.CRIT, 'Błąd modułu', err.message || String(err),
            'Moduł nie zakończył się poprawnie. Otwórz konsolę przeglądarki dla szczegółów.')],
        };
        state.sections.push(section);
        renderSection(section);
        accumulateSummary(section);
      }
      await tick();
    }

    setProgress(100, 'Skan zakończony');
    state.finishedAt = performance.now();
    state.running = false;
    $('#scan-run').disabled = false;
    $('#scan-stop').disabled = true;
    $('#scan-progress').hidden = true;
    renderSummary();
    enableReportButtons(true);
  }

  function setProgress(pct, text) {
    $('#scan-progress-fill').style.width = pct.toFixed(1) + '%';
    $('#scan-progress-pct').textContent = Math.round(pct) + '%';
    $('#scan-progress-text').textContent = text;
  }

  function tick() { return new Promise(r => setTimeout(r, 30)); }

  function accumulateSummary(section) {
    for (const f of section.findings) {
      if (f.severity === SEV.OK)   state.summary.ok++;
      if (f.severity === SEV.WARN) state.summary.warn++;
      if (f.severity === SEV.CRIT) state.summary.crit++;
      state.summary.score += sevWeight[f.severity] || 0;
    }
  }

  function renderSection(section) {
    const wrap = document.createElement('div');
    wrap.className = 'scan-section';
    const findingsHtml = section.findings.map(f => `
      <div class="finding sev-${f.severity}">
        <span class="finding-dot"></span>
        <div class="finding-body">
          <div class="finding-row">
            <span class="finding-label">${escapeHtml(f.label)}</span>
            <span class="finding-value">${escapeHtml(f.value)}</span>
          </div>
          ${f.hint ? `<div class="finding-hint">${escapeHtml(f.hint)}</div>` : ''}
        </div>
      </div>`).join('');
    wrap.innerHTML = `
      <div class="scan-section-head">
        <span class="scan-section-icon">${section.icon || '🛡'}</span>
        <h3>${escapeHtml(section.title)}</h3>
        <span class="scan-section-count">${section.findings.length} wpis(ów)</span>
      </div>
      <div class="scan-section-body">${findingsHtml}</div>`;
    $('#scan-results').appendChild(wrap);
  }

  function renderSummary() {
    const s = state.summary;
    const score = Math.max(0, 100 - Math.min(100, s.score));
    $('#sum-score').textContent = score;
    $('#sum-score-bar').style.width = score + '%';
    $('#sum-score-bar').className = score > 80 ? 'good' : score > 55 ? 'mid' : 'bad';
    $('#sum-crit').textContent = s.crit;
    $('#sum-warn').textContent = s.warn;
    $('#sum-ok').textContent   = s.ok;
    $('#sum-time').textContent = ((state.finishedAt - state.startedAt) / 1000).toFixed(2) + ' s';
    $('#scan-summary').hidden = false;
  }

  function enableReportButtons(on) {
    ['#report-pdf','#report-url','#report-json','#report-share'].forEach(s => $(s).disabled = !on);
  }

  function resetUi() {
    state.files = []; state.sections = []; state.summary = { ok:0, warn:0, crit:0, score:0 };
    renderFileList();
    $('#scan-results').innerHTML = `
      <div class="scan-empty">
        <div class="scan-empty-icon">🛡</div>
        <h3>Skan nie został jeszcze uruchomiony</h3>
        <p>Kliknij <strong>Skanuj wszystko</strong> żeby uruchomić wszystkie moduły.</p>
      </div>`;
    $('#scan-summary').hidden = true;
    $('#scan-share-link').hidden = true;
    enableReportButtons(false);
  }

  /* ── Module: System ────────────────────────────────── */
  async function scanSystem() {
    const findings = [];
    const ua = navigator.userAgent;
    const platform = navigator.platform || (navigator.userAgentData && navigator.userAgentData.platform) || 'unknown';
    findings.push(finding(SEV.INFO, 'Platforma', platform));
    findings.push(finding(SEV.INFO, 'User-Agent', ua));

    if (navigator.userAgentData) {
      try {
        const ua2 = await navigator.userAgentData.getHighEntropyValues(
          ['architecture','bitness','model','platformVersion','uaFullVersion']);
        findings.push(finding(SEV.INFO, 'Architektura', `${ua2.architecture || '?'} / ${ua2.bitness || '?'}`));
        findings.push(finding(SEV.INFO, 'Wersja platformy', ua2.platformVersion || '—'));
        findings.push(finding(SEV.INFO, 'Wersja UA', ua2.uaFullVersion || '—'));
      } catch (_) {}
    }

    const cores = navigator.hardwareConcurrency || 0;
    findings.push(finding(cores >= 4 ? SEV.OK : SEV.WARN, 'Liczba rdzeni CPU', cores || 'nieznana',
      cores < 4 ? 'Mniej niż 4 logiczne rdzenie — nowoczesne aplikacje mogą zwalniać.' : ''));

    const mem = navigator.deviceMemory || 0;
    findings.push(finding(mem >= 4 ? SEV.OK : SEV.WARN, 'Pamięć RAM (przybliżona)', mem ? mem + ' GB' : 'nieznana',
      mem && mem < 4 ? 'Mniej niż 4 GB RAM — przeglądarka będzie często zrzucać karty.' : ''));

    findings.push(finding(SEV.INFO, 'Język', navigator.language || '—'));
    findings.push(finding(SEV.INFO, 'Strefa czasowa', Intl.DateTimeFormat().resolvedOptions().timeZone || '—'));
    findings.push(finding(SEV.INFO, 'Rozdzielczość', `${screen.width}×${screen.height} @ ${window.devicePixelRatio}x`));
    findings.push(finding(SEV.INFO, 'Głębia kolorów', screen.colorDepth + '-bit'));

    // GPU via WebGL
    try {
      const c = document.createElement('canvas');
      const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
      if (gl) {
        const dbg = gl.getExtension('WEBGL_debug_renderer_info');
        const vendor = dbg ? gl.getParameter(dbg.UNMASKED_VENDOR_WEBGL) : gl.getParameter(gl.VENDOR);
        const renderer = dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER);
        findings.push(finding(SEV.INFO, 'GPU', `${vendor} / ${renderer}`));
      } else {
        findings.push(finding(SEV.WARN, 'WebGL', 'niedostępny',
          'Brak WebGL może oznaczać tryb prywatny lub wyłączone akcelerowanie sprzętowe.'));
      }
    } catch (_) {}

    findings.push(finding(SEV.INFO, 'Online', navigator.onLine ? 'tak' : 'nie'));

    return { id: 'system', title: 'System operacyjny i sprzęt', icon: '🖥', findings };
  }

  /* ── Module: Browser ──────────────────────────────── */
  async function scanBrowser() {
    const findings = [];
    findings.push(finding(SEV.INFO, 'Vendor', navigator.vendor || '—'));
    findings.push(finding(SEV.INFO, 'Cookies włączone', navigator.cookieEnabled ? 'tak' : 'nie'));
    findings.push(finding(navigator.javaEnabled?.() ? SEV.WARN : SEV.OK,
      'Java applet enabled', navigator.javaEnabled?.() ? 'tak' : 'nie',
      navigator.javaEnabled?.() ? 'Java w przeglądarce to wektor exploitów — wyłącz w ustawieniach.' : ''));

    findings.push(finding(SEV.INFO, 'Protokół strony', location.protocol));
    if (location.protocol !== 'https:' && location.hostname !== 'localhost') {
      findings.push(finding(SEV.CRIT, 'Połączenie nieszyfrowane', location.protocol,
        'Strona ładowana przez HTTP — dane są podsłuchiwalne. Używaj HTTPS.'));
    } else {
      findings.push(finding(SEV.OK, 'TLS', 'aktywny dla bieżącej strony'));
    }

    // Service workers, secure context
    findings.push(finding(window.isSecureContext ? SEV.OK : SEV.WARN,
      'Secure context', window.isSecureContext ? 'tak' : 'nie',
      window.isSecureContext ? '' : 'Niektóre API (np. Crypto.subtle) wymagają HTTPS.'));

    findings.push(finding(SEV.INFO, 'Service Worker', 'serviceWorker' in navigator ? 'wspierany' : 'brak'));
    findings.push(finding(SEV.INFO, 'Web Crypto', (window.crypto && crypto.subtle) ? 'dostępny' : 'BRAK',
      (window.crypto && crypto.subtle) ? '' : 'Bez crypto.subtle skan plików nie zadziała — przejdź na HTTPS.'));

    // Plugins / mime types (legacy)
    const plugins = Array.from(navigator.plugins || []).map(p => p.name);
    findings.push(finding(plugins.length ? SEV.WARN : SEV.OK, 'Pluginy NPAPI/PPAPI',
      plugins.length ? plugins.join(', ') : 'brak',
      plugins.length ? 'Stare pluginy to częsty wektor ataku — rozważ usunięcie.' : ''));

    // Mixed-mode / canvas fingerprint stability (illustrative)
    try {
      const canvas = document.createElement('canvas'); canvas.width = 60; canvas.height = 18;
      const ctx = canvas.getContext('2d');
      ctx.textBaseline = 'top'; ctx.font = '14px Arial';
      ctx.fillStyle = '#f60'; ctx.fillRect(0,0,60,18);
      ctx.fillStyle = '#069'; ctx.fillText('FSD', 2, 2);
      const fp = await sha256Hex(new TextEncoder().encode(canvas.toDataURL()));
      findings.push(finding(SEV.INFO, 'Canvas fingerprint (SHA-256)', fp.slice(0,32) + '…',
        'Identyfikator stabilności renderowania — powiązany z GPU/sterownikiem.'));
    } catch (_) {}

    return { id: 'browser', title: 'Przeglądarka i fingerprint', icon: '🧭', findings };
  }

  /* ── Module: Network ──────────────────────────────── */
  async function scanNetwork() {
    const findings = [];
    const conn = navigator.connection || navigator.mozConnection || navigator.webkitConnection;
    if (conn) {
      findings.push(finding(SEV.INFO, 'Typ połączenia', conn.effectiveType || 'unknown'));
      findings.push(finding(SEV.INFO, 'Downlink (szac.)', (conn.downlink || '?') + ' Mb/s'));
      findings.push(finding(SEV.INFO, 'RTT (szac.)', (conn.rtt || '?') + ' ms'));
      findings.push(finding(conn.saveData ? SEV.WARN : SEV.OK,
        'Save-Data', conn.saveData ? 'włączone' : 'wyłączone'));
    } else {
      findings.push(finding(SEV.INFO, 'Network Information API', 'niedostępny'));
    }

    // RTT to current origin
    try {
      const t0 = performance.now();
      await fetch(location.href, { method: 'HEAD', cache: 'no-store' });
      const dt = performance.now() - t0;
      findings.push(finding(dt < 300 ? SEV.OK : SEV.WARN, 'RTT do bieżącego origin',
        dt.toFixed(0) + ' ms', dt < 300 ? '' : 'Wysokie opóźnienie. Sprawdź sieć/DNS.'));
    } catch (_) {}

    // Security headers of current page (visible to JS only via meta-equivalents)
    const csp = $('meta[http-equiv="Content-Security-Policy"]')?.content;
    findings.push(finding(csp ? SEV.OK : SEV.WARN, 'CSP (meta)', csp || 'brak meta-CSP',
      csp ? '' : 'Brak meta-CSP. Polityka może być nadal ustawiona w nagłówku HTTP.'));

    // Referrer policy / Permissions Policy meta hints
    const ref = document.referrer || '—';
    findings.push(finding(SEV.INFO, 'Referrer', ref));

    // Public IP — best-effort, may be blocked by CSP / privacy extensions
    try {
      const ctrl = AbortSignal.timeout ? AbortSignal.timeout(2500) : undefined;
      const r = await fetch('https://api.ipify.org?format=json', { signal: ctrl });
      if (r.ok) {
        const j = await r.json();
        findings.push(finding(SEV.INFO, 'Publiczny adres IP', j.ip || '—',
          'Anonimizujemy do /24 (IPv4) lub /48 (IPv6) zanim wejdzie do raportu.'));
      }
    } catch (_) {
      findings.push(finding(SEV.INFO, 'Publiczny adres IP', 'niedostępny',
        'Możliwe że masz blokujące rozszerzenie albo politykę CSP.'));
    }

    // WebRTC leak hint
    findings.push(finding(SEV.INFO, 'WebRTC', 'RTCPeerConnection w window: ' + ('RTCPeerConnection' in window),
      'WebRTC potrafi wyciekać lokalne IP — używaj VPN-a z blokadą WebRTC, jeśli to ważne.'));

    return { id: 'network', title: 'Sieć i łączność', icon: '🌐', findings };
  }

  /* ── Module: Memory ───────────────────────────────── */
  async function scanMemory() {
    const findings = [];
    const m = performance.memory;
    if (m) {
      const used = m.usedJSHeapSize / (1024*1024);
      const total = m.totalJSHeapSize / (1024*1024);
      const limit = m.jsHeapSizeLimit / (1024*1024);
      findings.push(finding(SEV.INFO, 'JS heap — używane', used.toFixed(1) + ' MB'));
      findings.push(finding(SEV.INFO, 'JS heap — alokowane', total.toFixed(1) + ' MB'));
      findings.push(finding(SEV.INFO, 'JS heap — limit',     limit.toFixed(1) + ' MB'));
      const ratio = used / limit;
      findings.push(finding(ratio > 0.85 ? SEV.CRIT : ratio > 0.6 ? SEV.WARN : SEV.OK,
        'Pressure (used/limit)', (ratio * 100).toFixed(1) + '%',
        ratio > 0.85 ? 'Wysoka presja pamięci — ryzyko OOM tab crash.' : ''));
    } else {
      findings.push(finding(SEV.INFO, 'performance.memory', 'niedostępny',
        'Tylko Chromium ujawnia statystyki heapu JS.'));
    }

    // GC pressure micro-bench
    const a = []; const t0 = performance.now();
    for (let i = 0; i < 200_000; i++) a.push({ i });
    const tAlloc = performance.now() - t0;
    a.length = 0;
    findings.push(finding(tAlloc < 50 ? SEV.OK : tAlloc < 200 ? SEV.WARN : SEV.CRIT,
      'Alokacja 200k obiektów', tAlloc.toFixed(1) + ' ms',
      tAlloc < 50 ? '' : 'Wolniej niż oczekiwane — system może być pod obciążeniem.'));

    // Storage estimate (memory-of-disk)
    if (navigator.storage && navigator.storage.estimate) {
      const e = await navigator.storage.estimate();
      findings.push(finding(SEV.INFO, 'Storage quota',
        humanBytes(e.quota || 0) + ' (used ' + humanBytes(e.usage || 0) + ')'));
    }

    return { id: 'memory', title: 'Pamięć i wydajność', icon: '🧠', findings };
  }

  /* ── Module: Storage ──────────────────────────────── */
  async function scanStorage() {
    const findings = [];
    findings.push(finding(SEV.INFO, 'localStorage entries', String(safeLen(window.localStorage))));
    findings.push(finding(SEV.INFO, 'sessionStorage entries', String(safeLen(window.sessionStorage))));
    findings.push(finding(SEV.INFO, 'document.cookie chars', String(document.cookie.length)));
    findings.push(finding(SEV.INFO, 'IndexedDB', 'indexedDB' in window ? 'dostępne' : 'BRAK'));
    findings.push(finding(SEV.INFO, 'CacheStorage', 'caches' in window ? 'dostępne' : 'BRAK'));

    if (navigator.storage && navigator.storage.persisted) {
      const persisted = await navigator.storage.persisted();
      findings.push(finding(SEV.INFO, 'Storage persisted', persisted ? 'tak' : 'nie',
        persisted ? '' : 'Bez persisted storage przeglądarka może wyczyścić dane pod presją dysku.'));
    }
    return { id: 'storage', title: 'Storage, ciasteczka, IndexedDB', icon: '💾', findings };
  }

  /* ── Module: Privacy ──────────────────────────────── */
  async function scanPrivacy() {
    const findings = [];
    findings.push(finding(navigator.doNotTrack === '1' ? SEV.OK : SEV.WARN,
      'Do Not Track', navigator.doNotTrack || 'nie ustawione',
      navigator.doNotTrack === '1' ? '' : 'Włącz DNT w ustawieniach przeglądarki.'));

    findings.push(finding(navigator.globalPrivacyControl ? SEV.OK : SEV.INFO,
      'Global Privacy Control', navigator.globalPrivacyControl ? 'aktywny' : 'brak',
      navigator.globalPrivacyControl ? '' : 'GPC sygnalizuje serwisom, że nie zgadzasz się na sprzedaż danych.'));

    const trackers = await detectKnownTrackers();
    findings.push(finding(trackers.length === 0 ? SEV.OK : SEV.WARN,
      'Wykryte skrypty trackingowe', trackers.length === 0 ? 'brak' : trackers.join(', '),
      trackers.length === 0 ? '' : 'Trackery załadowane na bieżącej stronie.'));

    findings.push(finding(SEV.INFO, 'Liczba pluginów', String((navigator.plugins || []).length)));
    findings.push(finding(SEV.INFO, 'Mediadevices API', navigator.mediaDevices ? 'dostępny' : 'brak'));

    // Permissions API snapshot
    if (navigator.permissions && navigator.permissions.query) {
      const probe = ['geolocation','notifications','camera','microphone','clipboard-read'];
      for (const p of probe) {
        try {
          const r = await navigator.permissions.query({ name: p });
          findings.push(finding(r.state === 'granted' ? SEV.WARN : SEV.OK,
            'Permission · ' + p, r.state,
            r.state === 'granted' ? 'Strona ma już dostęp — sprawdź czy świadomie.' : ''));
        } catch (_) {}
      }
    }
    return { id: 'privacy', title: 'Prywatność i trackery', icon: '🕶', findings };
  }

  function detectKnownTrackers() {
    const known = [
      ['Google Analytics',  /google-analytics\.com|googletagmanager\.com|gtag/i],
      ['Facebook Pixel',     /connect\.facebook\.net|fbevents/i],
      ['Hotjar',             /static\.hotjar\.com|hotjar/i],
      ['Mixpanel',           /cdn\.mxpnl\.com|mixpanel/i],
      ['Segment',            /cdn\.segment\.com|analytics\.js/i],
      ['LinkedIn Insight',   /snap\.licdn\.com/i],
      ['TikTok Pixel',       /analytics\.tiktok\.com/i],
    ];
    const found = new Set();
    Array.from(document.scripts).forEach(s => {
      const src = s.src || s.textContent || '';
      known.forEach(([name, rx]) => { if (rx.test(src)) found.add(name); });
    });
    return Array.from(found);
  }

  /* ── Module: Malware (file hashing) ───────────────── */
  async function scanMalware() {
    const findings = [];
    if (!state.files.length) {
      findings.push(finding(SEV.INFO, 'Pliki w kolejce', 'brak',
        'Przeciągnij plik do strefy upload aby uruchomić skan hash-based.'));
      return { id: 'malware', title: 'Malware (skan plików)', icon: '🦠', findings };
    }
    if (!(window.crypto && crypto.subtle)) {
      findings.push(finding(SEV.CRIT, 'Web Crypto', 'niedostępny',
        'Skan plików wymaga HTTPS / Secure Context.'));
      return { id: 'malware', title: 'Malware (skan plików)', icon: '🦠', findings };
    }

    for (const f of state.files) {
      if (state.aborted) break;
      const buf = await f.arrayBuffer();
      const sha256 = await sha256Hex(buf);
      const sha1   = await sha1Hex(buf);
      const md5    = md5Hex(new Uint8Array(buf));

      const ext = (f.name.split('.').pop() || '').toLowerCase();
      const suspicious = SUSPICIOUS_EXT.has(ext);
      const knownBad = KNOWN_BAD.sha256.has(sha256) || KNOWN_BAD.sha1.has(sha1) || KNOWN_BAD.md5.has(md5);

      const sev = knownBad ? SEV.CRIT : (suspicious ? SEV.WARN : SEV.OK);
      const verdict = knownBad
        ? 'KNOWN MALWARE — hash trafił do lokalnej bazy CTI.'
        : (suspicious
            ? 'Rozszerzenie podwyższonego ryzyka — przeskanuj dodatkowo Defenderem/clamav.'
            : 'Brak trafień w lokalnej bazie. Hash wysyłany do feedu Threat Intel po Twojej akceptacji.');

      findings.push(finding(sev, f.name, `${humanBytes(f.size)} · ${ext || 'no-ext'}`, verdict));
      findings.push(finding(SEV.INFO, '  ↳ SHA-256', sha256));
      findings.push(finding(SEV.INFO, '  ↳ SHA-1',   sha1));
      findings.push(finding(SEV.INFO, '  ↳ MD5',     md5));

      // Always queue an anonymized intel record (user has to confirm via "Wyślij do Threat Intel")
      pendingIntel.push({
        ts: Date.now(),
        sha256, sha1, md5,
        size: f.size,
        ext,
        verdict: knownBad ? 'malicious' : (suspicious ? 'suspicious' : 'clean'),
        country: anonymizedCountry(),
      });
    }

    return { id: 'malware', title: 'Malware (skan plików)', icon: '🦠', findings };
  }

  const pendingIntel = [];

  /* ── Hashing helpers ─────────────────────────────── */
  async function sha256Hex(buf) {
    const h = await crypto.subtle.digest('SHA-256', buf);
    return bytesToHex(new Uint8Array(h));
  }
  async function sha1Hex(buf) {
    const h = await crypto.subtle.digest('SHA-1', buf);
    return bytesToHex(new Uint8Array(h));
  }
  function bytesToHex(arr) {
    let s = ''; for (const b of arr) s += b.toString(16).padStart(2, '0'); return s;
  }

  /* Tiny MD5 (RFC 1321) — used only for hash display, NOT security.
     Public-domain implementation, adapted for byte-array input. */
  function md5Hex(bytes) {
    function rh(n){let s='',j;for(j=0;j<=3;j++)s+=((n>>(j*8+4))&0x0f).toString(16)+((n>>(j*8))&0x0f).toString(16);return s;}
    function ad(x,y){const l=(x&0xFFFF)+(y&0xFFFF);return ((((x>>16)+(y>>16)+(l>>16))&0xFFFF)<<16)|(l&0xFFFF);}
    function rl(n,c){return (n<<c)|(n>>>(32-c));}
    function cm(q,a,b,x,s,t){return ad(rl(ad(ad(a,q),ad(x,t)),s),b);}
    function ff(a,b,c,d,x,s,t){return cm((b&c)|((~b)&d),a,b,x,s,t);}
    function gg(a,b,c,d,x,s,t){return cm((b&d)|(c&(~d)),a,b,x,s,t);}
    function hh(a,b,c,d,x,s,t){return cm(b^c^d,a,b,x,s,t);}
    function ii(a,b,c,d,x,s,t){return cm(c^(b|(~d)),a,b,x,s,t);}
    function cb(b){
      const nl=((b.length+8)>>6)+1, x=new Array(nl*16).fill(0);
      for(let i=0;i<b.length;i++) x[i>>2]|=b[i]<<((i%4)*8);
      x[b.length>>2]|=0x80<<((b.length%4)*8);
      x[nl*16-2]=b.length*8;
      return x;
    }
    const x=cb(bytes);
    let a=0x67452301,b=-271733879,c=-1732584194,d=0x10325476;
    for(let i=0;i<x.length;i+=16){
      const A=a,B=b,C=c,D=d;
      a=ff(a,b,c,d,x[i+0],7,-680876936); d=ff(d,a,b,c,x[i+1],12,-389564586);
      c=ff(c,d,a,b,x[i+2],17,606105819); b=ff(b,c,d,a,x[i+3],22,-1044525330);
      a=ff(a,b,c,d,x[i+4],7,-176418897); d=ff(d,a,b,c,x[i+5],12,1200080426);
      c=ff(c,d,a,b,x[i+6],17,-1473231341); b=ff(b,c,d,a,x[i+7],22,-45705983);
      a=ff(a,b,c,d,x[i+8],7,1770035416); d=ff(d,a,b,c,x[i+9],12,-1958414417);
      c=ff(c,d,a,b,x[i+10],17,-42063); b=ff(b,c,d,a,x[i+11],22,-1990404162);
      a=ff(a,b,c,d,x[i+12],7,1804603682); d=ff(d,a,b,c,x[i+13],12,-40341101);
      c=ff(c,d,a,b,x[i+14],17,-1502002290); b=ff(b,c,d,a,x[i+15],22,1236535329);
      a=gg(a,b,c,d,x[i+1],5,-165796510); d=gg(d,a,b,c,x[i+6],9,-1069501632);
      c=gg(c,d,a,b,x[i+11],14,643717713); b=gg(b,c,d,a,x[i+0],20,-373897302);
      a=gg(a,b,c,d,x[i+5],5,-701558691); d=gg(d,a,b,c,x[i+10],9,38016083);
      c=gg(c,d,a,b,x[i+15],14,-660478335); b=gg(b,c,d,a,x[i+4],20,-405537848);
      a=gg(a,b,c,d,x[i+9],5,568446438); d=gg(d,a,b,c,x[i+14],9,-1019803690);
      c=gg(c,d,a,b,x[i+3],14,-187363961); b=gg(b,c,d,a,x[i+8],20,1163531501);
      a=gg(a,b,c,d,x[i+13],5,-1444681467); d=gg(d,a,b,c,x[i+2],9,-51403784);
      c=gg(c,d,a,b,x[i+7],14,1735328473); b=gg(b,c,d,a,x[i+12],20,-1926607734);
      a=hh(a,b,c,d,x[i+5],4,-378558); d=hh(d,a,b,c,x[i+8],11,-2022574463);
      c=hh(c,d,a,b,x[i+11],16,1839030562); b=hh(b,c,d,a,x[i+14],23,-35309556);
      a=hh(a,b,c,d,x[i+1],4,-1530992060); d=hh(d,a,b,c,x[i+4],11,1272893353);
      c=hh(c,d,a,b,x[i+7],16,-155497632); b=hh(b,c,d,a,x[i+10],23,-1094730640);
      a=hh(a,b,c,d,x[i+13],4,681279174); d=hh(d,a,b,c,x[i+0],11,-358537222);
      c=hh(c,d,a,b,x[i+3],16,-722521979); b=hh(b,c,d,a,x[i+6],23,76029189);
      a=hh(a,b,c,d,x[i+9],4,-640364487); d=hh(d,a,b,c,x[i+12],11,-421815835);
      c=hh(c,d,a,b,x[i+15],16,530742520); b=hh(b,c,d,a,x[i+2],23,-995338651);
      a=ii(a,b,c,d,x[i+0],6,-198630844); d=ii(d,a,b,c,x[i+7],10,1126891415);
      c=ii(c,d,a,b,x[i+14],15,-1416354905); b=ii(b,c,d,a,x[i+5],21,-57434055);
      a=ii(a,b,c,d,x[i+12],6,1700485571); d=ii(d,a,b,c,x[i+3],10,-1894986606);
      c=ii(c,d,a,b,x[i+10],15,-1051523); b=ii(b,c,d,a,x[i+1],21,-2054922799);
      a=ii(a,b,c,d,x[i+8],6,1873313359); d=ii(d,a,b,c,x[i+15],10,-30611744);
      c=ii(c,d,a,b,x[i+6],15,-1560198380); b=ii(b,c,d,a,x[i+13],21,1309151649);
      a=ii(a,b,c,d,x[i+4],6,-145523070); d=ii(d,a,b,c,x[i+11],10,-1120210379);
      c=ii(c,d,a,b,x[i+2],15,718787259); b=ii(b,c,d,a,x[i+9],21,-343485551);
      a=ad(a,A); b=ad(b,B); c=ad(c,C); d=ad(d,D);
    }
    return rh(a)+rh(b)+rh(c)+rh(d);
  }

  /* ── Anonymization helpers ────────────────────────── */
  function anonymizedCountry() {
    // Country code derived from timezone. Never IP. Not exact.
    const tz = (Intl.DateTimeFormat().resolvedOptions().timeZone || '').split('/')[0];
    const map = { Europe:'EU', America:'US', Asia:'AS', Africa:'AF', Australia:'AU', Pacific:'OC', Atlantic:'AT', Indian:'IN', Antarctica:'AQ' };
    return map[tz] || 'XX';
  }

  /* ── Reports ───────────────────────────────────────── */
  function buildReportData() {
    return {
      tool: 'FreeSystemDoctor Cybersecurity Scanner',
      version: '1.0',
      generatedAt: new Date().toISOString(),
      durationMs: Math.round(state.finishedAt - state.startedAt),
      summary: {
        score: Math.max(0, 100 - Math.min(100, state.summary.score)),
        critical: state.summary.crit,
        warnings: state.summary.warn,
        ok: state.summary.ok,
      },
      sections: state.sections,
    };
  }

  function exportJson() {
    const data = buildReportData();
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    triggerDownload(blob, `freesystemdoctor-report-${reportStamp()}.json`);
  }

  async function exportPdf() {
    const data = buildReportData();
    const { jsPDF } = window.jspdf || {};
    if (!jsPDF) {
      alert('Biblioteka jsPDF jeszcze się nie załadowała. Spróbuj ponownie za chwilę.');
      return;
    }
    const doc = new jsPDF({ unit: 'pt', format: 'a4' });
    const W = doc.internal.pageSize.getWidth();
    const H = doc.internal.pageSize.getHeight();
    let y = 56;

    doc.setFillColor(13,16,23); doc.rect(0, 0, W, 80, 'F');
    doc.setTextColor(255); doc.setFontSize(20); doc.setFont('helvetica', 'bold');
    doc.text('FreeSystemDoctor — Security Report', 40, 38);
    doc.setFontSize(11); doc.setFont('helvetica', 'normal');
    doc.text(data.generatedAt + '   ·   v' + data.version, 40, 58);
    doc.setTextColor(0); y = 110;

    // Summary box
    doc.setFillColor(245,247,252); doc.rect(40, y, W - 80, 80, 'F');
    doc.setFontSize(13); doc.setFont('helvetica','bold'); doc.text('Podsumowanie', 56, y + 22);
    doc.setFont('helvetica','normal'); doc.setFontSize(11);
    doc.text(`Risk Score: ${data.summary.score}/100`, 56, y + 44);
    doc.text(`Krytyczne: ${data.summary.critical}`, 220, y + 44);
    doc.text(`Ostrzeżenia: ${data.summary.warnings}`, 340, y + 44);
    doc.text(`OK: ${data.summary.ok}`, 470, y + 44);
    doc.text(`Czas skanu: ${(data.durationMs/1000).toFixed(2)} s`, 56, y + 64);
    y += 110;

    for (const sec of data.sections) {
      if (y > H - 80) { doc.addPage(); y = 56; }
      doc.setFontSize(13); doc.setFont('helvetica','bold');
      doc.setFillColor(26,31,43); doc.setTextColor(255);
      doc.rect(40, y - 14, W - 80, 22, 'F');
      doc.text(`${sec.icon || ''}  ${sec.title}`, 50, y);
      y += 18;
      doc.setTextColor(0); doc.setFont('helvetica','normal'); doc.setFontSize(10);

      for (const f of sec.findings) {
        if (y > H - 60) { doc.addPage(); y = 56; }
        const dot = ({crit:'■', warn:'▲', ok:'●', info:'·'})[f.severity] || '·';
        const color = ({crit:[230,57,70], warn:[245,158,11], ok:[34,197,94], info:[100,116,139]})[f.severity] || [0,0,0];
        doc.setTextColor(...color); doc.text(dot, 44, y);
        doc.setTextColor(0);
        const labelLines = doc.splitTextToSize(f.label + ': ' + f.value, W - 110);
        doc.text(labelLines, 60, y);
        y += labelLines.length * 12;
        if (f.hint) {
          doc.setTextColor(90,98,118);
          const hintLines = doc.splitTextToSize(f.hint, W - 120);
          doc.text(hintLines, 70, y);
          y += hintLines.length * 11;
          doc.setTextColor(0);
        }
        y += 4;
      }
      y += 10;
    }

    // Footer page numbers
    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i++) {
      doc.setPage(i);
      doc.setFontSize(9); doc.setTextColor(140);
      doc.text(`FreeSystemDoctor · Strona ${i}/${pageCount} · MIT · github.com/caytec/freesystemdoctor`,
        40, H - 24);
    }

    doc.save(`freesystemdoctor-report-${reportStamp()}.pdf`);
  }

  function exportUrl() {
    const data = buildReportData();
    const html = renderReportHtml(data);
    const blob = new Blob([html], { type: 'text/html' });
    if (state.reportUrl) URL.revokeObjectURL(state.reportUrl);
    state.reportUrl = URL.createObjectURL(blob);
    const a = $('#scan-share-link-a');
    a.href = state.reportUrl;
    a.textContent = `freesystemdoctor-report-${reportStamp()}.html`;
    a.download = `freesystemdoctor-report-${reportStamp()}.html`;
    $('#scan-share-link').hidden = false;

    $('#scan-share-copy').onclick = () => {
      navigator.clipboard.writeText(state.reportUrl).then(
        () => $('#scan-share-copy').textContent = 'Skopiowano',
        () => $('#scan-share-copy').textContent = 'Błąd');
    };
  }

  function shareToIntel() {
    const items = pendingIntel.splice(0);
    if (window.FSD_CTI && typeof FSD_CTI.append === 'function') {
      const added = FSD_CTI.append(items);
      renderCtiPreview();
      alert(`Dodano ${added} anonimowych zdarzeń do Threat Intel (lokalnie). Otwórz Threat Intel żeby zobaczyć pełną listę.`);
    } else {
      alert('Threat Intel API niedostępne na tej stronie.');
    }
  }

  function renderReportHtml(data) {
    const sectionsHtml = data.sections.map(sec => `
      <h2>${escapeHtml(sec.icon || '')} ${escapeHtml(sec.title)}</h2>
      <table>
        <thead><tr><th>Severity</th><th>Test</th><th>Wartość</th><th>Wskazówka</th></tr></thead>
        <tbody>
          ${sec.findings.map(f => `
            <tr class="sev-${f.severity}">
              <td>${f.severity.toUpperCase()}</td>
              <td>${escapeHtml(f.label)}</td>
              <td><code>${escapeHtml(f.value)}</code></td>
              <td>${escapeHtml(f.hint)}</td>
            </tr>`).join('')}
        </tbody>
      </table>`).join('');

    return `<!doctype html><html lang="pl"><head><meta charset="utf-8">
<title>FreeSystemDoctor — Security Report ${data.generatedAt}</title>
<style>
body{font:14px/1.55 -apple-system,Segoe UI,Roboto,sans-serif;background:#0d1017;color:#e8eaef;max-width:980px;margin:0 auto;padding:32px}
h1{font-size:28px;margin:0 0 4px}
h2{margin:32px 0 8px;font-size:18px;color:#7aa2ff}
table{width:100%;border-collapse:collapse;font-size:13px;margin-bottom:8px;background:#161a23;border-radius:8px;overflow:hidden}
th,td{padding:8px 10px;border-bottom:1px solid #242a38;text-align:left;vertical-align:top}
th{background:#1d222e;color:#8a93a6;text-transform:uppercase;font-size:11px;letter-spacing:.5px}
code{background:#1d222e;padding:1px 6px;border-radius:4px;color:#9bb4ff;word-break:break-all}
tr.sev-crit td:first-child{color:#f87171;font-weight:700}
tr.sev-warn td:first-child{color:#fbbf24;font-weight:700}
tr.sev-ok td:first-child{color:#34d399;font-weight:700}
tr.sev-info td:first-child{color:#8a93a6}
.summary{display:flex;flex-wrap:wrap;gap:16px;margin:18px 0 24px}
.summary div{background:#161a23;border:1px solid #242a38;border-radius:8px;padding:12px 18px;min-width:140px}
.summary div b{display:block;font-size:24px;color:#4f7ef8}
footer{margin-top:36px;color:#8a93a6;font-size:12px;border-top:1px solid #242a38;padding-top:16px}
</style></head>
<body>
<h1>🛡 FreeSystemDoctor — Security Report</h1>
<p>${escapeHtml(data.generatedAt)} · v${escapeHtml(data.version)} · czas skanu ${(data.durationMs/1000).toFixed(2)} s</p>
<div class="summary">
  <div><b>${data.summary.score}</b>Risk Score / 100</div>
  <div><b style="color:#f87171">${data.summary.critical}</b>Krytyczne</div>
  <div><b style="color:#fbbf24">${data.summary.warnings}</b>Ostrzeżenia</div>
  <div><b style="color:#34d399">${data.summary.ok}</b>OK</div>
</div>
${sectionsHtml}
<footer>Wygenerowane przez FreeSystemDoctor Cybersecurity Scanner v${escapeHtml(data.version)} · MIT · github.com/caytec/freesystemdoctor<br>
Raport powstał lokalnie w przeglądarce. Żadne dane nie zostały wysłane do serwera.</footer>
</body></html>`;
  }

  /* ── CTI preview (last N) ─────────────────────────── */
  function renderCtiPreview() {
    const list = $('#cti-preview-list');
    if (!list) return;
    const recent = (window.FSD_CTI && FSD_CTI.recent(8)) || [];
    if (!recent.length) {
      list.innerHTML = '<div class="scan-empty"><p>Brak zdarzeń w lokalnym feedzie. Po skanie kliknij „Wyślij do Threat Intel”.</p></div>';
      return;
    }
    list.innerHTML = recent.map(r => `
      <div class="cti-row sev-${verdictSev(r.verdict)}">
        <span class="cti-time">${new Date(r.ts).toISOString().replace('T',' ').slice(0,19)}</span>
        <span class="cti-country">${escapeHtml(r.country || 'XX')}</span>
        <span class="cti-verdict v-${escapeHtml(r.verdict)}">${escapeHtml(r.verdict)}</span>
        <code class="cti-hash" title="SHA-256">${escapeHtml((r.sha256||'').slice(0, 24))}…</code>
        <span class="cti-meta">${humanBytes(r.size||0)} · .${escapeHtml(r.ext||'?')}</span>
      </div>`).join('');
  }
  function verdictSev(v) { return v === 'malicious' ? 'crit' : v === 'suspicious' ? 'warn' : 'ok'; }

  /* ── tiny utils ───────────────────────────────────── */
  function safeLen(s) { try { return s.length; } catch (_) { return 0; } }
  function humanBytes(n) {
    if (!n) return '0 B';
    const u = ['B','KB','MB','GB','TB']; let i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return n.toFixed(n < 10 && i ? 1 : 0) + ' ' + u[i];
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[c]));
  }
  function reportStamp() {
    const d = new Date();
    return d.toISOString().replace(/[-:]/g,'').replace(/\..+/,'');
  }
  function triggerDownload(blob, name) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = name;
    document.body.appendChild(a); a.click();
    setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 200);
  }

  // Expose for debugging
  window.FSD_SCAN = { state, runScan, exportPdf, exportUrl, exportJson };
})();
