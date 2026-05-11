/* ─────────────────────────────────────────────────────────
   FreeSystemDoctor — Threat Intelligence feed (client-side)
   - Maintains an anonymized list of file-scan verdicts
     in localStorage (key: FSD_CTI_v1).
   - Records contain only:
       ts, sha256, sha1, md5, size, ext, verdict, country
     No filenames, no IPs, no user identifiers.
   - Provides FSD_CTI.append / recent / all / clear / stats
   - Seeds the store on first load with sample data so the
     feed page is not empty on first visit.
   ───────────────────────────────────────────────────────── */
(function () {
  'use strict';

  const KEY = 'FSD_CTI_v1';
  const MAX = 500;

  function read() {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : null;
    } catch (_) { return null; }
  }
  function write(items) {
    try { localStorage.setItem(KEY, JSON.stringify(items.slice(0, MAX))); } catch (_) {}
  }

  /* Seed sample — illustrative records so the feed is not empty
     on a fresh device. EICAR is a real public test signature. */
  const SEED = [
    {
      ts: Date.now() - 1000 * 60 * 6,
      sha256: '275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f',
      sha1:   'cf8bd9dfddff007f75adf4c2be48005cea317c62',
      md5:    '44d88612fea8a8f36de82e1278abb02f',
      size:   68, ext: 'com', verdict: 'malicious', country: 'EU',
      family: 'EICAR-Test-File',
    },
    {
      ts: Date.now() - 1000 * 60 * 22,
      sha256: '0f9d3e2b6c1a4f78b5d6e9a3c72f8b1a4d6e9c2f5a8b7d3e1c0f9b8a7d6e5c4b',
      sha1:   '3a7f8b2c1d6e5f9a4b3c2d1e0f9a8b7c6d5e4f3a',
      md5:    '8b1a4d6e9c2f5a8b7d3e1c0f9b8a7d6e',
      size:   2_138_592, ext: 'exe', verdict: 'suspicious', country: 'US',
      family: 'Generic.PUA.Loader',
    },
    {
      ts: Date.now() - 1000 * 60 * 47,
      sha256: 'a3f1c5b9d8e7f6a4b2c1d0e9f8a7b6c5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9',
      sha1:   '9e8d7c6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d',
      md5:    'a1b2c3d4e5f6071829384a5b6c7d8e9f',
      size:   415_232, ext: 'docm', verdict: 'malicious', country: 'AS',
      family: 'Macro.Downloader.Emotet',
    },
    {
      ts: Date.now() - 1000 * 60 * 91,
      sha256: 'fbb1c8e0c7d3a1234b5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c',
      sha1:   '6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b',
      md5:    'd1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6',
      size:   18_432, ext: 'js', verdict: 'suspicious', country: 'EU',
      family: 'JS.Obfuscated.Dropper',
    },
    {
      ts: Date.now() - 1000 * 60 * 128,
      sha256: 'c9f8e7d6b5a4f3e2d1c0b9a8f7e6d5c4b3a2f1e0d9c8b7a6f5e4d3c2b1a09f8e',
      sha1:   '7c6d5e4f3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d',
      md5:    'fedcba9876543210fedcba9876543210',
      size:   97_842, ext: 'pdf', verdict: 'clean', country: 'US',
    },
    {
      ts: Date.now() - 1000 * 60 * 200,
      sha256: '11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff',
      sha1:   '00112233445566778899aabbccddeeff00112233',
      md5:    'ffeeddccbbaa99887766554433221100',
      size:   12_034, ext: 'txt', verdict: 'clean', country: 'AF',
    },
    {
      ts: Date.now() - 1000 * 60 * 310,
      sha256: '7e6c5b4a39281f0e9d8c7b6a5f4e3d2c1b0a9988776655443322110ffeeddccbb',
      sha1:   'aa11bb22cc33dd44ee55ff6677889900aabbccdd',
      md5:    '11aa22bb33cc44dd55ee66ff77889900',
      size:   3_512_876, ext: 'msi', verdict: 'malicious', country: 'OC',
      family: 'PUP.InstallCore',
    },
    {
      ts: Date.now() - 1000 * 60 * 425,
      sha256: 'deadbeefcafebabe1234567890abcdef0fedcba9876543210ffeeddccbbaa9988',
      sha1:   'abc123def456abc123def456abc123def456abc1',
      md5:    'abc123def456abc123def456abc123de',
      size:   532, ext: 'lnk', verdict: 'suspicious', country: 'EU',
      family: 'LNK.Suspicious.PowershellLauncher',
    },
    {
      ts: Date.now() - 1000 * 60 * 580,
      sha256: 'bada55c0ffee1337beefdeaf0ddba115beef13371deadc0debada55c0ffee123',
      sha1:   '1337c0debada55c0ffee1337c0debada55c0ffee',
      md5:    'cafe1337bada55c0ffee1234bada55c0',
      size:   8_482, ext: 'ps1', verdict: 'malicious', country: 'AS',
      family: 'PS.AMSI.Bypass',
    },
    {
      ts: Date.now() - 1000 * 60 * 690,
      sha256: 'e7d6c5b4a39281f0e9d8c7b6a5f4e3d2c1b0a9988776655443322110ffeeddc1',
      sha1:   'bb22cc33dd44ee55ff6677889900aabbccddeefa',
      md5:    '22bb33cc44dd55ee66ff7788990000aa',
      size:   265_312, ext: 'apk', verdict: 'suspicious', country: 'AS',
      family: 'Android.SmsSpy',
    },
  ];

  function ensureSeed() {
    if (read() == null) write(SEED);
  }

  ensureSeed();

  const FSD_CTI = {
    /** Append n records, return how many were actually stored. */
    append(records) {
      if (!Array.isArray(records) || records.length === 0) return 0;
      const cur = read() || [];
      const sanitized = records.map(r => ({
        ts: Number(r.ts) || Date.now(),
        sha256: String(r.sha256 || '').slice(0, 64),
        sha1:   String(r.sha1   || '').slice(0, 40),
        md5:    String(r.md5    || '').slice(0, 32),
        size:   Math.max(0, Number(r.size) || 0),
        ext:    String(r.ext || '').slice(0, 12),
        verdict: ['malicious','suspicious','clean'].includes(r.verdict) ? r.verdict : 'clean',
        country: String(r.country || 'XX').slice(0, 4),
        family:  r.family ? String(r.family).slice(0, 64) : undefined,
      }));
      const merged = sanitized.concat(cur);
      write(merged);
      return sanitized.length;
    },
    recent(n = 20) {
      const items = read() || [];
      return items.slice().sort((a, b) => b.ts - a.ts).slice(0, n);
    },
    all() { return (read() || []).slice().sort((a, b) => b.ts - a.ts); },
    clear() { write([]); },
    reseed() { write(SEED); },
    stats() {
      const items = read() || [];
      const by = { malicious: 0, suspicious: 0, clean: 0 };
      const ext = {}; const country = {}; const families = {};
      let last24 = 0; const cutoff = Date.now() - 86_400_000;
      for (const r of items) {
        by[r.verdict] = (by[r.verdict] || 0) + 1;
        ext[r.ext || '?'] = (ext[r.ext || '?'] || 0) + 1;
        country[r.country || 'XX'] = (country[r.country || 'XX'] || 0) + 1;
        if (r.family) families[r.family] = (families[r.family] || 0) + 1;
        if (r.ts >= cutoff) last24++;
      }
      const top = (obj, n) => Object.entries(obj).sort((a,b)=>b[1]-a[1]).slice(0, n);
      return {
        total: items.length,
        last24,
        verdicts: by,
        topExt: top(ext, 8),
        topCountry: top(country, 8),
        topFamilies: top(families, 6),
      };
    },
  };

  window.FSD_CTI = FSD_CTI;
})();
