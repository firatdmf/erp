// Money inputs that show their thousands grouped while you are not typing in
// them — 1,234,567.89 in English, 1.234.567,89 in Turkish — following the
// app's language (<html lang>), not the browser's.
//
// The input stays a real <input type="number">: it keeps its own value, its
// min/step validation, and its numeric keypad, and everything that reads it
// gets the plain number it always did. A number input cannot *display* a
// grouped value — assigning "1.234,56" to one empties it — so the grouped
// figure is drawn in a span laid over the field, and the field's own text is
// turned transparent underneath. Focus the field and the span goes away,
// leaving the native control exactly as it was.
//
// A value set from script (the exchange-rate converter does this) needs a
// refresh(el) call, because assigning .value fires no event.
(function () {
  var TR = /^tr\b/i.test(document.documentElement.lang || '');
  var LOCALE = TR ? 'tr-TR' : 'en-US';

  // The one place the language turns into separators. Also exported, for
  // read-only figures sitting beside these inputs.
  function format(n, decimals) {
    if (decimals == null) decimals = 2;
    var v = Number(n);
    if (!isFinite(v)) return '';
    return v.toLocaleString(LOCALE, {
      minimumFractionDigits: decimals, maximumFractionDigits: decimals
    });
  }

  // Properties the overlay has to borrow so its text lands exactly where the
  // input's own text would have. Re-read on every draw rather than cached,
  // so a theme or font that loads late is picked up.
  // Longhands, not the `font` shorthand: Chrome computes that to an empty
  // string, which left the figure in the document's default font.
  var COPIED = ['fontFamily', 'fontSize', 'fontWeight', 'fontStyle',
                'fontVariantNumeric', 'lineHeight', 'letterSpacing',
                'textAlign', 'direction'];
  // Padding is not among them: the overlay is stretched to the input's
  // border box, so it has to inset by the border as well as the padding, or
  // the figure sits a border-width to the left of the digits it replaces.
  var SIDES = ['Top', 'Right', 'Bottom', 'Left'];

  function attach(el, opts) {
    if (!el || el.__amount) return el;
    el.__amount = true;
    var decimals = (opts && opts.decimals != null) ? opts.decimals : 2;

    // The colour the input's text would have been. Taken before anything is
    // made transparent, or it would come back "transparent".
    var ink = getComputedStyle(el).color;

    // A wrapper to position against. It takes over the input's place in its
    // parent's layout — width and any flex sizing — so wrapping changes
    // nothing about how the field sits on the page.
    var cs = getComputedStyle(el);
    var wrap = document.createElement('span');
    wrap.className = 'amt-wrap';
    wrap.style.position = 'relative';
    wrap.style.display = 'block';
    wrap.style.width = cs.width === 'auto' ? 'auto' : '100%';
    wrap.style.flex = cs.flexGrow + ' ' + cs.flexShrink + ' ' + cs.flexBasis;
    wrap.style.minWidth = cs.minWidth;
    el.parentNode.insertBefore(wrap, el);
    wrap.appendChild(el);
    el.style.width = '100%';

    var view = document.createElement('span');
    view.setAttribute('aria-hidden', 'true');   // the input is what is read out
    view.style.cssText = 'position:absolute; top:0; right:0; bottom:0; left:0;' +
      'display:none; align-items:center; pointer-events:none;' +
      'overflow:hidden; white-space:nowrap;';
    wrap.appendChild(view);

    function draw(focused) {
      var plain = el.value;
      if (focused || plain === '') {
        view.style.display = 'none';
        el.style.color = '';
        return;
      }
      var s = getComputedStyle(el);
      COPIED.forEach(function (k) { view.style[k] = s[k]; });
      SIDES.forEach(function (side) {
        view.style['padding' + side] =
          (parseFloat(s['padding' + side]) + parseFloat(s['border' + side + 'Width'])) + 'px';
      });
      // The overlay is a flex box, so text-align is honoured through it.
      view.style.justifyContent =
        s.textAlign === 'right' || s.textAlign === 'end' ? 'flex-end' :
        s.textAlign === 'center' ? 'center' : 'flex-start';
      view.style.color = ink;
      view.textContent = format(plain, decimals);
      view.style.display = 'flex';
      el.style.color = 'transparent';
    }

    el.addEventListener('focus', function () { draw(true); });
    el.addEventListener('blur', function () { draw(false); });
    el.addEventListener('input', function () { draw(true); });
    el.addEventListener('change', function () { draw(el === document.activeElement); });

    draw(el === document.activeElement);
    el.__amountDraw = draw;
    return el;
  }

  // For a value assigned from script: .value = x fires no event, so the
  // overlay has to be told.
  function refresh(el) {
    if (el && el.__amountDraw) el.__amountDraw(el === document.activeElement);
  }

  window.NejumAmount = { attach: attach, refresh: refresh, format: format };
})();
