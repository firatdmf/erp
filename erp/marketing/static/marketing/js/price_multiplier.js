// The price multiplier box: "Price = cost × [4/3]". Shows, as it is typed,
// what the formula comes to and what it does to a cost — worked in exact
// fractions, as marketing/pricing.py does on the server, so 3.60 × 4/3
// reads 4.80 here too and never 4.85 from a floating-point slip.
//
// <input data-multiplier-preview="ID_OF_PREVIEW"
//        data-example-cost="3.60"        (optional; else 100)
//        data-fallback="4/3"             (optional; used while blank)
//        data-fallback-label="group">    (optional; names the fallback)
(function () {
  const T = window.PRICE_MULTIPLIER_T || {};
  const t = (key, fallback) => T[key] || fallback;

  // ── exact fractions, BigInt numerator / denominator ──
  const gcd = (a, b) => { a = a < 0n ? -a : a; b = b < 0n ? -b : b; while (b) [a, b] = [b, a % b]; return a; };
  const frac = (n, d) => { if (d === 0n) throw new Error('÷0'); if (d < 0n) { n = -n; d = -d; } const g = gcd(n, d) || 1n; return [n / g, d / g]; };
  const add = (a, b) => frac(a[0] * b[1] + b[0] * a[1], a[1] * b[1]);
  const sub = (a, b) => frac(a[0] * b[1] - b[0] * a[1], a[1] * b[1]);
  const mul = (a, b) => frac(a[0] * b[0], a[1] * b[1]);
  const div = (a, b) => frac(a[0] * b[1], a[1] * b[0]);
  const fromDecimal = (s) => {
    const [whole, part = ''] = s.split('.');
    return frac(BigInt((whole || '0') + part), 10n ** BigInt(part.length));
  };

  // ── numbers, + - × ÷ and brackets; anything else is not a formula ──
  function parse(text) {
    const src = String(text || '').replace(/,/g, '.').replace(/×/g, '*').replace(/÷/g, '/').replace(/\s+/g, '');
    if (!src || src.length > 40) throw new Error('empty');
    let i = 0;
    const peek = () => src[i];
    function number() {
      const m = /^\d*\.?\d+|^\d+\./.exec(src.slice(i));
      if (!m) throw new Error('number');
      i += m[0].length;
      return fromDecimal(m[0].replace(/\.$/, ''));
    }
    function factor() {
      if (peek() === '+') { i++; return factor(); }
      if (peek() === '-') { i++; const v = factor(); return [-v[0], v[1]]; }
      if (peek() === '(') { i++; const v = expr(); if (peek() !== ')') throw new Error(')'); i++; return v; }
      return number();
    }
    function term() {
      let v = factor();
      while (peek() === '*' || peek() === '/') { const op = src[i++]; const r = factor(); v = op === '*' ? mul(v, r) : div(v, r); }
      return v;
    }
    function expr() {
      let v = term();
      while (peek() === '+' || peek() === '-') { const op = src[i++]; const r = term(); v = op === '+' ? add(v, r) : sub(v, r); }
      return v;
    }
    const value = expr();
    if (i !== src.length) throw new Error('trailing');
    if (value[0] <= 0n) throw new Error('not above zero');
    return value;
  }

  // cost × multiplier, rounded UP to the next 0.05, as "4.80".
  function price(cost, m) {
    const raw = mul(fromDecimal(cost), m);              // dollars
    const steps = div(raw, [1n, 20n]);                   // in 0.05s
    let n = steps[0] / steps[1];
    if (steps[0] % steps[1] !== 0n && steps[0] > 0n) n += 1n;
    const cents = n * 5n;
    return `${cents / 100n}.${String(cents % 100n).padStart(2, '0')}`;
  }
  const percent = (m) => {
    const p = Number((m[0] - m[1]) * 1000000n / m[1]) / 10000;   // to 4 places
    return (p >= 0 ? '+' : '') + p.toLocaleString(undefined, { maximumFractionDigits: 2 }) + '%';
  };

  function render(input) {
    const out = document.getElementById(input.dataset.multiplierPreview);
    if (!out) return;
    let text = input.value.trim();
    let via = '';
    if (!text && input.dataset.fallback) {
      text = input.dataset.fallback;
      via = `${input.dataset.fallbackLabel || t('group', 'group')}: × ${text} · `;
    }
    if (!text) { out.textContent = t('empty', 'Type what the cost is multiplied by, e.g. 4/3.'); out.className = 'pm-preview'; return; }
    let m;
    try { m = parse(text); } catch (e) {
      out.textContent = t('invalid', 'Not a formula — use numbers, + − × ÷ and brackets, e.g. 4/3.');
      out.className = 'pm-preview bad';
      return;
    }
    const example = input.dataset.exampleCost || '100';
    const below = m[0] < m[1];
    out.textContent = `${via}${percent(m)} ${t('on_cost', 'on cost')} · $${example} → $${price(example, m)}`
      + (below ? ` · ${t('below_cost', 'below cost')}` : '');
    out.className = 'pm-preview' + (below ? ' bad' : '');
  }

  function wire() {
    document.querySelectorAll('input[data-multiplier-preview]').forEach((input) => {
      input.addEventListener('input', () => render(input));
      render(input);
    });
  }
  window.priceMultiplierPreview = { parse, price, render };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', wire);
  else wire();
})();
