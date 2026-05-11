/* ─────────────────────────────────────────────────────────
   FreeSystemDoctor — AI Risk Analyst (BYOK, in-browser)
   - Providers: Anthropic (Claude), Groq, Cerebras, custom
     OpenAI-compatible endpoint.
   - Key + provider + model are stored in localStorage.
   - Calls go directly from the user's browser to the chosen
     provider. The site has no backend and never sees the key
     or the prompt. Anthropic browser-direct calls require the
     `anthropic-dangerous-direct-browser-access: true` header.
   ───────────────────────────────────────────────────────── */
(function () {
  'use strict';

  const $ = (sel) => document.querySelector(sel);

  const LS_KEY      = 'FSD_AI_v1';
  const LS_HISTORY  = 'FSD_AI_HISTORY_v1';

  /* ── Provider catalog ──────────────────────────────── */
  const PROVIDERS = {
    anthropic: {
      label: 'Anthropic (Claude)',
      baseUrl: 'https://api.anthropic.com',
      models: [
        { id: 'claude-opus-4-7',  label: 'Claude Opus 4.7 (najlepszy)' },
        { id: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6 (zbalansowany)' },
        { id: 'claude-haiku-4-5',  label: 'Claude Haiku 4.5 (szybki, tani)' },
      ],
      defaultModel: 'claude-opus-4-7',
      keyHint: 'sk-ant-... (ze strony console.anthropic.com)',
      keyUrl: 'https://console.anthropic.com/settings/keys',
    },
    groq: {
      label: 'Groq (OpenAI-compatible)',
      baseUrl: 'https://api.groq.com/openai',
      models: [
        { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 70B (Groq)' },
        { id: 'llama-3.1-8b-instant',    label: 'Llama 3.1 8B (Groq, najszybszy)' },
        { id: 'mixtral-8x7b-32768',      label: 'Mixtral 8x7B (Groq)' },
      ],
      defaultModel: 'llama-3.3-70b-versatile',
      keyHint: 'gsk_... (ze strony console.groq.com)',
      keyUrl: 'https://console.groq.com/keys',
      openaiCompatible: true,
    },
    cerebras: {
      label: 'Cerebras (OpenAI-compatible)',
      baseUrl: 'https://api.cerebras.ai',
      models: [
        { id: 'llama3.1-70b', label: 'Llama 3.1 70B (Cerebras)' },
        { id: 'llama3.1-8b',  label: 'Llama 3.1 8B (Cerebras, najszybszy)' },
      ],
      defaultModel: 'llama3.1-70b',
      keyHint: 'csk-... (ze strony cloud.cerebras.ai)',
      keyUrl: 'https://cloud.cerebras.ai/platform/',
      openaiCompatible: true,
    },
    custom: {
      label: 'Custom (OpenAI-compatible URL)',
      baseUrl: '',
      models: [],
      defaultModel: '',
      keyHint: 'Token bearer dla Twojego endpointu',
      keyUrl: '',
      openaiCompatible: true,
      custom: true,
    },
  };

  /* ── Persistent settings ───────────────────────────── */
  const cfg = loadCfg();
  function loadCfg() {
    try {
      return Object.assign({
        provider: 'anthropic',
        model: 'claude-opus-4-7',
        apiKey: '',
        baseUrl: '',
        rememberKey: true,
      }, JSON.parse(localStorage.getItem(LS_KEY) || '{}'));
    } catch (_) {
      return { provider: 'anthropic', model: 'claude-opus-4-7', apiKey: '', baseUrl: '', rememberKey: true };
    }
  }
  function saveCfg() {
    const persist = Object.assign({}, cfg);
    if (!cfg.rememberKey) persist.apiKey = '';
    try { localStorage.setItem(LS_KEY, JSON.stringify(persist)); } catch (_) {}
  }

  /* ── Conversation state ────────────────────────────── */
  let history = loadHistory();
  function loadHistory() {
    try { return JSON.parse(localStorage.getItem(LS_HISTORY) || '[]'); } catch (_) { return []; }
  }
  function saveHistory() {
    try { localStorage.setItem(LS_HISTORY, JSON.stringify(history.slice(-30))); } catch (_) {}
  }

  /* ── Bootstrap ─────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    if (!$('#ai-panel')) return;       // page without the AI panel

    $('#ai-provider').addEventListener('change', e => {
      cfg.provider = e.target.value;
      cfg.model = PROVIDERS[cfg.provider].defaultModel;
      renderProviderUi();
      saveCfg();
    });
    $('#ai-model').addEventListener('change', e => { cfg.model = e.target.value; saveCfg(); });
    $('#ai-key').addEventListener('input',  e => { cfg.apiKey = e.target.value; saveCfg(); });
    $('#ai-baseurl').addEventListener('input', e => { cfg.baseUrl = e.target.value; saveCfg(); });
    $('#ai-remember').addEventListener('change', e => {
      cfg.rememberKey = e.target.checked; saveCfg();
      if (!cfg.rememberKey) try { localStorage.removeItem(LS_KEY); } catch(_){}
    });

    $('#ai-send').addEventListener('click', () => onSend());
    $('#ai-input').addEventListener('keydown', e => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); onSend(); }
    });
    $('#ai-analyze').addEventListener('click', onAnalyzeReport);
    $('#ai-clear').addEventListener('click', () => {
      if (!confirm('Wyczyścić historię rozmowy?')) return;
      history = []; saveHistory(); renderTranscript();
    });

    renderProviderUi();
    renderTranscript();
  }

  function renderProviderUi() {
    const p = PROVIDERS[cfg.provider];
    $('#ai-provider').value = cfg.provider;
    $('#ai-model').innerHTML = p.models.map(m =>
      `<option value="${m.id}" ${m.id===cfg.model?'selected':''}>${escapeHtml(m.label)}</option>`).join('');
    if (p.custom) {
      $('#ai-model').innerHTML = `<option value="${escapeHtml(cfg.model)}">${escapeHtml(cfg.model || 'wpisz model w URL/baseurl')}</option>`;
    }
    $('#ai-key').value = cfg.apiKey || '';
    $('#ai-key').placeholder = p.keyHint;
    $('#ai-baseurl').value = cfg.baseUrl || '';
    $('#ai-baseurl-row').hidden = !p.custom;
    $('#ai-remember').checked = !!cfg.rememberKey;

    const link = $('#ai-key-link');
    if (p.keyUrl) { link.href = p.keyUrl; link.hidden = false; link.textContent = '↗ Skąd wziąć klucz'; }
    else { link.hidden = true; }
  }

  /* ── Conversation rendering ────────────────────────── */
  function renderTranscript() {
    const tr = $('#ai-transcript');
    if (!history.length) {
      tr.innerHTML = `<div class="ai-empty">
        <strong>Cześć 👋 Jestem Twoim Risk Analystem.</strong>
        <p>Najpierw uruchom skan w sekcji powyżej, potem kliknij <em>„Analizuj raport”</em> — wytłumaczę co znalazł skaner i wskażę priorytety. Możesz też zadać dowolne pytanie o cyberbezpieczeństwo.</p>
      </div>`;
      return;
    }
    tr.innerHTML = history.map(m => `
      <div class="ai-msg ai-msg-${m.role}">
        <div class="ai-msg-head">${m.role === 'user' ? 'Ty' : 'Risk Analyst'}</div>
        <div class="ai-msg-body">${renderMd(m.content)}</div>
      </div>`).join('');
    tr.scrollTop = tr.scrollHeight;
  }

  function renderMd(s) {
    // Tiny safe Markdown: escape HTML, then **bold**, `code`, paragraphs.
    const esc = escapeHtml(s);
    return esc
      .replace(/```([\s\S]+?)```/g, (_, c) => `<pre><code>${c}</code></pre>`)
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      .replace(/^- (.+)$/gm, '• $1')
      .replace(/\n{2,}/g, '</p><p>')
      .replace(/^/, '<p>').replace(/$/, '</p>');
  }

  /* ── Send / streaming ──────────────────────────────── */
  let inFlight = null;

  async function onSend(prefill) {
    const input = $('#ai-input');
    const text = (prefill ?? input.value).trim();
    if (!text) return;
    if (!cfg.apiKey && !PROVIDERS[cfg.provider].custom) {
      alert('Najpierw wpisz klucz API w polu po prawej.');
      return;
    }
    if (inFlight) { alert('Poczekaj aż poprzednia odpowiedź się zakończy.'); return; }

    history.push({ role: 'user', content: text });
    input.value = '';
    renderTranscript();
    saveHistory();

    // Insert empty assistant bubble we'll stream into
    history.push({ role: 'assistant', content: '' });
    renderTranscript();

    setBusy(true);
    try {
      const append = (chunk) => {
        history[history.length - 1].content += chunk;
        renderTranscript();
      };
      if (cfg.provider === 'anthropic') await callAnthropic(append);
      else                              await callOpenAiCompatible(append);
      saveHistory();
    } catch (err) {
      history[history.length - 1].content =
        `❌ **Błąd:** ${err.message || err}\n\nSprawdź klucz API i spróbuj ponownie.`;
      renderTranscript();
      saveHistory();
    } finally {
      setBusy(false);
    }
  }

  function setBusy(busy) {
    inFlight = busy ? true : null;
    $('#ai-send').disabled = busy;
    $('#ai-analyze').disabled = busy;
    $('#ai-send').textContent = busy ? '⏳ Analizuję…' : 'Wyślij (Ctrl/Cmd+Enter)';
  }

  /* ── System prompt ─────────────────────────────────── */
  function buildSystemPrompt() {
    return [
      'Jesteś Risk Analystem w narzędziu FreeSystemDoctor Cybersecurity Scanner.',
      'Pomagasz użytkownikowi zrozumieć wyniki skanu (system, sieć, pamięć, prywatność, malware, strona internetowa).',
      'Odpowiadasz zwięźle, po polsku, w stylu starszego analityka SOC.',
      'Jeśli widzisz raport JSON, podsumuj 3 najważniejsze ryzyka, posortuj według severity, i daj konkretne kroki naprawcze.',
      'Nie twórz fałszywych pewności — gdy dane są niejednoznaczne, powiedz to wprost.',
      'Nigdy nie wymyślaj wartości których nie ma w raporcie. Cytuj wartości pól (np. „CSP: brak”).',
    ].join(' ');
  }

  function onAnalyzeReport() {
    const report = (window.FSD_SCAN && FSD_SCAN.getReport && FSD_SCAN.getReport()) || null;
    if (!report) {
      alert('Najpierw uruchom skan (przycisk „Skanuj wszystko” na górze).');
      return;
    }
    // Trim per-section to avoid blowing context for cheap models
    const trimmed = {
      summary: report.summary,
      durationMs: report.durationMs,
      sections: report.sections.map(s => ({
        title: s.title,
        findings: s.findings.map(f => ({
          severity: f.severity, label: f.label,
          value: (f.value || '').slice(0, 240),
          hint: (f.hint || '').slice(0, 240),
        })),
      })),
    };
    const prompt =
`Oto raport ze skanu (JSON). Przeanalizuj go i odpowiedz:
1) Risk Score i co go obniża (top 3 problemy z severity = "crit" / "warn").
2) 5 konkretnych kroków naprawczych (uporządkuj od największego ryzyka).
3) Czy są ślady kompromitacji albo krytyczne luki (np. mixed content, brak HSTS, znane malware hash, suspicious extension, SPF/DMARC brak)?
4) Czego skaner NIE jest w stanie sprawdzić w przeglądarce — co warto zweryfikować ręcznie / serwerowym narzędziem.

Raport:
\`\`\`json
${JSON.stringify(trimmed, null, 2)}
\`\`\``;
    onSend(prompt);
  }

  /* ── Anthropic Messages API (browser-direct) ──────── */
  async function callAnthropic(append) {
    const url  = 'https://api.anthropic.com/v1/messages';
    // Build messages history (skip the empty trailing assistant placeholder)
    const msgs = history.slice(0, -1).map(m => ({ role: m.role, content: m.content }));
    const body = {
      model: cfg.model,
      max_tokens: 4096,
      stream: true,
      system: buildSystemPrompt(),
      messages: msgs,
    };
    const r = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': cfg.apiKey,
        'anthropic-version': '2023-06-01',
        // Required because we are calling from a browser instead of a server.
        // Each user uses their OWN key, so this is the intended use case.
        'anthropic-dangerous-direct-browser-access': 'true',
      },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const text = await r.text();
      throw new Error(`Anthropic ${r.status}: ${text.slice(0, 240)}`);
    }
    await consumeSse(r, (event) => {
      if (event.type === 'content_block_delta' && event.delta?.type === 'text_delta') {
        append(event.delta.text);
      }
    });
  }

  /* ── OpenAI-compatible (Groq / Cerebras / custom) ── */
  async function callOpenAiCompatible(append) {
    const p = PROVIDERS[cfg.provider];
    const base = (p.custom ? cfg.baseUrl : p.baseUrl).replace(/\/+$/, '');
    if (!base) throw new Error('Brak base URL dla custom providera.');
    const msgs = [{ role: 'system', content: buildSystemPrompt() }]
      .concat(history.slice(0, -1).map(m => ({ role: m.role, content: m.content })));
    const body = { model: cfg.model, messages: msgs, stream: true, max_tokens: 4096 };

    const r = await fetch(`${base}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${cfg.apiKey}`,
      },
      body: JSON.stringify(body),
    });
    if (!r.ok) {
      const text = await r.text();
      throw new Error(`${cfg.provider} ${r.status}: ${text.slice(0, 240)}`);
    }
    await consumeSse(r, (event) => {
      // OpenAI shape: {choices:[{delta:{content:'...'}}]}
      const delta = event.choices?.[0]?.delta?.content;
      if (delta) append(delta);
    });
  }

  /* ── SSE consumer (works for both formats) ────────── */
  async function consumeSse(response, onEvent) {
    const reader = response.body.getReader();
    const dec = new TextDecoder();
    let buf = '';
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      // SSE: split on double newline
      const parts = buf.split(/\r?\n\r?\n/);
      buf = parts.pop();
      for (const part of parts) {
        // Each part may have multiple lines; we care about `data: ...`
        const dataLines = part.split(/\r?\n/).filter(l => l.startsWith('data:'));
        for (const dl of dataLines) {
          const payload = dl.slice(5).trim();
          if (!payload || payload === '[DONE]') continue;
          try { onEvent(JSON.parse(payload)); } catch (_) { /* ignore */ }
        }
      }
    }
  }

  /* ── utils ────────────────────────────────────────── */
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
      '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
    }[c]));
  }
})();
