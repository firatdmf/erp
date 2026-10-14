/* Dark mode for the pages dark.css has not been written for.
 *
 * Most pages paint their own light colours in their own <style> blocks
 * and inline style="" attributes, so a global stylesheet can't reach
 * them all — and one written per page goes stale the day the page
 * changes. Instead this reads the colours the page itself declares and
 * writes their dark counterparts beside them:
 *
 *   a light background  → a dark surface (white = card, near-white =
 *                          the page behind it, light grey = raised/hover)
 *   dark text           → light text, keeping its hue
 *   a light border      → a dark one
 *
 * Tinted backgrounds (a green "paid" pill, a yellow warning) keep their
 * hue as a dark tint. Colours that are already dark, and light text, are
 * left alone.
 *
 * Every rule written is scoped to html[data-theme="dark"] through
 * :where(), which adds no specificity: it beats the page's own rule only
 * by coming after it, and the hand-written rules in dark.css — more
 * specific, and !important — still win wherever they exist. Because the
 * rules are scoped, they are written once and simply switch on and off
 * with the theme.
 *
 * Opt out on an element whose colour is the content (a colour swatch, a
 * photo's backdrop) with data-keep-colors.
 */
(function () {
  "use strict";

  var SCOPE = ':where(html[data-theme="dark"]) ';
  var PROPS = {
    "background-color": "bg", "background-image": "bg",
    "color": "text", "fill": "text", "stroke": "text", "caret-color": "text",
    "border-top-color": "border", "border-right-color": "border",
    "border-bottom-color": "border", "border-left-color": "border",
    "outline-color": "border"
  };
  var NAMED = {
    white: "#ffffff", black: "#000000", whitesmoke: "#f5f5f5",
    gainsboro: "#dcdcdc", lightgray: "#d3d3d3", lightgrey: "#d3d3d3",
    silver: "#c0c0c0", gray: "#808080", grey: "#808080", ivory: "#fffff0",
    snow: "#fffafa", ghostwhite: "#f8f8ff", aliceblue: "#f0f8ff",
    azure: "#f0ffff", honeydew: "#f0fff0", mintcream: "#f5fffa",
    seashell: "#fff5ee", linen: "#faf0e6", beige: "#f5f5dc",
    floralwhite: "#fffaf0", lavender: "#e6e6fa", lightyellow: "#ffffe0",
    lightblue: "#add8e6", darkgray: "#a9a9a9", dimgray: "#696969",
    darkgrey: "#a9a9a9", dimgrey: "#696969"
  };
  var COLOR_RE = /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)|\b(?:white|black|whitesmoke|gainsboro|lightgr[ae]y|silver|gr[ae]y|ivory|snow|ghostwhite|aliceblue|azure|honeydew|mintcream|seashell|linen|beige|floralwhite|lavender|lightyellow|lightblue|darkgr[ae]y|dimgr[ae]y)\b/g;

  // ── colour maths ────────────────────────────────────────────────
  function parse(s) {
    s = s.trim().toLowerCase();
    if (NAMED[s]) s = NAMED[s];
    var m;
    if (s[0] === "#") {
      var h = s.slice(1);
      if (h.length === 3 || h.length === 4) h = h.split("").map(function (c) { return c + c; }).join("");
      if (h.length !== 6 && h.length !== 8) return null;
      return { r: parseInt(h.slice(0, 2), 16), g: parseInt(h.slice(2, 4), 16), b: parseInt(h.slice(4, 6), 16),
               a: h.length === 8 ? parseInt(h.slice(6, 8), 16) / 255 : 1 };
    }
    if ((m = s.match(/^rgba?\(([^)]*)\)$/))) {
      var p = m[1].split(/[\s,\/]+/).filter(Boolean);
      if (p.length < 3) return null;
      var a = p.length > 3 ? (p[3].indexOf("%") > 0 ? parseFloat(p[3]) / 100 : parseFloat(p[3])) : 1;
      return { r: parseFloat(p[0]), g: parseFloat(p[1]), b: parseFloat(p[2]), a: a };
    }
    if ((m = s.match(/^hsla?\(([^)]*)\)$/))) {
      var q = m[1].split(/[\s,\/]+/).filter(Boolean);
      var rgb = hslToRgb(parseFloat(q[0]) / 360, parseFloat(q[1]) / 100, parseFloat(q[2]) / 100);
      rgb.a = q.length > 3 ? parseFloat(q[3]) : 1;
      return rgb;
    }
    return null;
  }
  function lum(c) { return (0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b) / 255; }
  function rgbToHsl(c) {
    var r = c.r / 255, g = c.g / 255, b = c.b / 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b), h = 0, s = 0, l = (max + min) / 2;
    if (max !== min) {
      var d = max - min;
      s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
      h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
      h /= 6;
    }
    return { h: h, s: s, l: l };
  }
  function hslToRgb(h, s, l) {
    function f(p, q, t) {
      if (t < 0) t += 1; if (t > 1) t -= 1;
      if (t < 1 / 6) return p + (q - p) * 6 * t;
      if (t < 1 / 2) return q;
      if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
      return p;
    }
    if (s === 0) return { r: l * 255, g: l * 255, b: l * 255 };
    var q = l < 0.5 ? l * (1 + s) : l + s - l * s, p = 2 * l - q;
    return { r: f(p, q, h + 1 / 3) * 255, g: f(p, q, h) * 255, b: f(p, q, h - 1 / 3) * 255 };
  }
  function out(h, s, l, a) {
    var c = hslToRgb(h, s, l);
    var rgb = Math.round(c.r) + ", " + Math.round(c.g) + ", " + Math.round(c.b);
    return a < 1 ? "rgba(" + rgb + ", " + (Math.round(a * 1000) / 1000) + ")" : "rgb(" + rgb + ")";
  }
  // Greys get the app's dark palette's faint blue (#1A1F26 and kin).
  function tone(hsl) {
    return hsl.s < 0.08 ? { h: 213 / 360, s: 0.16 } : { h: hsl.h, s: Math.min(hsl.s, 0.45) };
  }

  var MAP = {
    bg: function (c) {
      var L = lum(c);
      if (L < 0.5) return null;                       // already dark, or a strong colour
      var t = tone(rgbToHsl(c)), l;
      if (L >= 0.985) l = 0.125;                      // white: a card
      else if (L >= 0.93) l = 0.1;                    // near-white: the page behind cards
      else l = 0.155 + (0.93 - L) * 0.28;             // light grey: raised, hover, headers
      return out(t.h, t.s, l, c.a);
    },
    text: function (c) {
      var L = lum(c), hsl = rgbToHsl(c);
      if (L >= 0.6) return null;                      // already light
      var s = hsl.s < 0.08 ? 0.1 : Math.min(hsl.s, 0.7), h = hsl.s < 0.08 ? 213 / 360 : hsl.h;
      var l = L < 0.45 ? 0.9 - L * 0.55 : 0.66;
      return out(h, s, l, c.a);
    },
    border: function (c) {
      var L = lum(c);
      if (L < 0.62) return null;
      var t = tone(rgbToHsl(c));
      return out(t.h, Math.min(t.s, 0.25), 0.19 + (1 - L) * 0.25, c.a);
    }
  };

  function convert(value, role) {
    if (!value || value.indexOf("var(") >= 0) return null;
    if (value === "transparent" || value === "inherit" || value === "currentcolor" || value === "none") return null;
    var changed = false;
    var v = value.replace(COLOR_RE, function (tok) {
      var c = parse(tok);
      if (!c || c.a === 0) return tok;
      var m = MAP[role](c);
      if (m === null) return tok;
      changed = true;
      return m;
    });
    return changed ? v : null;
  }

  // ── colour variables ────────────────────────────────────────────
  // Pages often set --ink, --gray-500, --bg-card… to their light values
  // on their own root element, which hides tokens.css's dark ones. What
  // a variable is for is read off its name; a brand colour (teal, red…)
  // is only lifted enough to read on a dark surface and still carry
  // white text when it is a button.
  var ACCENT = /teal|brand|primary|accent|green|red|blue|amber|orange|yellow|purple|violet|indigo|pink|danger|warning|success|info|error/;
  function varRole(name, c) {
    var n = name.toLowerCase();
    if (/border|line|divider|rule|outline|stroke/.test(n)) return "border";
    if (/bg|background|surface|card|paper|panel|page|body|soft|tint|fill|hover|row/.test(n)) return "bg";
    if (/ink|text|fg|font|muted|heading|title|label|caption/.test(n)) return "text";
    var shade = n.match(/-(\d{2,3})$/) || n.match(/^--g(\d{2,3})$/);
    if (ACCENT.test(n)) {
      if (shade && +shade[1] <= 100) return "bg";
      return lum(c) < 0.4 ? "accent" : null;
    }
    if (shade) {
      var k = +shade[1];
      return k <= 100 ? "bg" : k <= 300 ? "border" : "text";
    }
    var L = lum(c);
    return L > 0.9 ? "bg" : L > 0.62 ? "border" : L < 0.45 ? "text" : null;
  }
  MAP.accent = function (c) {
    var hsl = rgbToHsl(c);
    return out(hsl.h, hsl.s, Math.max(hsl.l, 0.36), c.a);
  };
  // Variables a stylesheet already gives a dark value of its own
  // (tokens.css's [data-theme="dark"] block). A page that sets one back
  // to its light value gets that hand-picked dark value, not a guess.
  var handPicked = {};
  function collectHandPicked(rules) {
    for (var i = 0; i < rules.length; i++) {
      var r = rules[i];
      if (r.type === 1 && (r.selectorText || "").indexOf("data-theme") >= 0) {
        for (var j = 0; j < r.style.length; j++)
          if (r.style[j].slice(0, 2) === "--")
            handPicked[r.style[j]] = r.style.getPropertyValue(r.style[j]).trim();
      } else if (r.cssRules) collectHandPicked(r.cssRules);
    }
  }
  function varDecls(style) {
    var decls = [];
    for (var i = 0; i < style.length; i++) {
      var p = style[i];
      if (p.slice(0, 2) !== "--") continue;
      var v = style.getPropertyValue(p).trim();
      if (handPicked[p]) {
        if (v !== handPicked[p]) decls.push(p + ": " + handPicked[p] + (style.getPropertyPriority(p) ? " !important" : ""));
        continue;
      }
      var c = parse(v);
      if (!c) continue;
      var role = varRole(p, c);
      if (!role) continue;
      var m = MAP[role](c);
      if (m) decls.push(p + ": " + m + (style.getPropertyPriority(p) ? " !important" : ""));
    }
    return decls;
  }

  // ── stylesheet rules ────────────────────────────────────────────
  var sheet = null, done = typeof WeakSet === "function" ? new WeakSet() : null;
  function target() {
    if (!sheet) {
      var el = document.createElement("style");
      el.id = "dark-auto";
      el.setAttribute("data-dark-auto", "");
      (document.body || document.head).appendChild(el);
      sheet = el.sheet;
    }
    return sheet;
  }
  function insert(text) {
    try { target().insertRule(text, target().cssRules.length); } catch (e) {}
  }
  function declsFor(style) {
    var decls = [];
    for (var p in PROPS) {
      var v = style.getPropertyValue(p);
      if (!v) continue;
      var nv = convert(v, PROPS[p]);
      if (nv) decls.push(p + ": " + nv + (style.getPropertyPriority(p) ? " !important" : ""));
    }
    return decls;
  }
  function scoped(selectorText) {
    return selectorText.split(",").map(function (s) {
      s = s.trim();
      // Kept as written, so the dark rule has the same weight as the
      // page's own (":root" outweighs "html").
      var root = s.match(/^(html|:root)(?![\w-])/);
      return root ? root[1] + ':where([data-theme="dark"])' + s.slice(root[1].length) : SCOPE + s;
    }).join(", ");
  }
  function walkRules(rules, wrap) {
    for (var i = 0; i < rules.length; i++) {
      var r = rules[i];
      if (r.type === 1) {                                         // style rule
        var sel = r.selectorText || "";
        if (sel.indexOf("data-theme") >= 0 || sel.indexOf("::-webkit-scrollbar") >= 0) continue;
        var d = declsFor(r.style).concat(varDecls(r.style));
        if (d.length) insert(wrap(scoped(sel) + " { " + d.join("; ") + "; }"));
      } else if (r.type === 4 && r.media && !/^print$/.test(r.media.mediaText)) {   // @media
        (function (mt) {
          walkRules(r.cssRules, function (t) { return wrap("@media " + mt + " { " + t + " }"); });
        })(r.media.mediaText);
      } else if (r.cssRules && r.type === 12) {                  // @supports
        (function (ct) {
          walkRules(r.cssRules, function (t) { return wrap("@supports " + ct + " { " + t + " }"); });
        })(r.conditionText);
      }
    }
  }
  function processSheets() {
    var sheets = document.styleSheets;
    for (var k = 0; k < sheets.length; k++) {
      try { if (sheets[k].cssRules) collectHandPicked(sheets[k].cssRules); } catch (e) {}
    }
    for (var i = 0; i < sheets.length; i++) {
      var s = sheets[i], owner = s.ownerNode;
      if (done && done.has(s)) continue;
      if (done) done.add(s);
      if (!owner || owner.hasAttribute("data-dark-auto")) continue;
      if (s.href && /\/dark\.css/.test(s.href)) continue;
      if (s.media && s.media.mediaText && /^print$/.test(s.media.mediaText)) continue;
      var rules;
      try { rules = s.cssRules; } catch (e) { continue; }       // another origin's sheet
      if (rules) walkRules(rules, function (t) { return t; });
    }
  }

  // ── inline style="" ─────────────────────────────────────────────
  var seq = 0, inlineCache = {};
  function isSwatch(el) {
    if (el.hasAttribute("data-keep-colors") || el.closest("[data-keep-colors]")) return true;
    var r = el.getBoundingClientRect();
    return r.width > 0 && r.width <= 48 && r.height <= 48 && !el.textContent.trim();
  }
  function processInline(el) {
    var css = el.getAttribute("style");
    if (!css || !/(background|color|border|fill|stroke)/i.test(css)) return;
    if (el.closest("[data-dark-auto-skip]")) return;
    var key = css + "|" + (el.getAttribute("data-dk") || "");
    if (el.__dk === key) return;
    var decls = declsFor(el.style);
    if (decls.length && isSwatch(el)) decls = decls.filter(function (d) { return !/^background/.test(d); });
    if (!decls.length) { el.__dk = key; return; }
    var body = decls.map(function (d) { return d.replace(/ !important$/, "") + " !important"; }).join("; ");
    var id = inlineCache[body];
    if (!id) {
      id = inlineCache[body] = "d" + (++seq);
      insert(SCOPE + '[data-dk="' + id + '"] { ' + body + "; }");
    }
    el.setAttribute("data-dk", id);
    el.__dk = css + "|" + id;
  }
  // SVG drawn by chart code paints with fill="" / stroke="" attributes:
  // light gridlines and backdrops go dark, dark labels and axes go light,
  // and the data's own colours stay.
  function processSvgPaint(el) {
    if (el.__dkSvg) return;
    el.__dkSvg = true;
    var decls = [];
    ["fill", "stroke"].forEach(function (attr) {
      var v = el.getAttribute(attr), c = v && parse(v);
      if (!c || c.a === 0) return;
      var L = lum(c), m = null;
      if (attr === "fill") m = L > 0.62 ? MAP.bg(c) : L < 0.45 ? MAP.text(c) : null;
      else m = L > 0.62 ? MAP.border(c) : L < 0.45 ? MAP.text(c) : null;
      if (m) decls.push(attr + ": " + m);
    });
    if (!decls.length) return;
    var body = decls.join("; ");
    var id = inlineCache[body];
    if (!id) {
      id = inlineCache[body] = "d" + (++seq);
      insert(SCOPE + '[data-dk="' + id + '"] { ' + body + "; }");
    }
    el.setAttribute("data-dk", id);
  }
  function processTree(root) {
    if (root.nodeType !== 1) return;
    if (root.hasAttribute("style")) processInline(root);
    var els = root.querySelectorAll("[style]");
    for (var i = 0; i < els.length; i++) processInline(els[i]);
    var paint = root.querySelectorAll("svg [fill], svg [stroke]");
    for (var j = 0; j < paint.length; j++) {
      if (!paint[j].closest("[data-keep-colors]")) processSvgPaint(paint[j]);
    }
  }

  // ── run, and keep up with what the page adds later ──────────────
  var pending = false;
  function later() {
    if (pending) return;
    pending = true;
    (window.requestAnimationFrame || setTimeout)(function () {
      pending = false;
      processSheets();
      processTree(document.body);
    });
  }
  function start() {
    processSheets();
    processTree(document.body);
    document.documentElement.classList.remove("dk-pending");
    // Transitions stay off until the dark colours have been painted once,
    // so nothing fades in from white.
    var raf = window.requestAnimationFrame || setTimeout;
    raf(function () { raf(function () { document.documentElement.classList.remove("dk-init"); }); });
    new MutationObserver(function (muts) {
      for (var i = 0; i < muts.length; i++) {
        var m = muts[i];
        if (m.type === "attributes") { if (m.target.nodeType === 1) processInline(m.target); continue; }
        for (var j = 0; j < m.addedNodes.length; j++) {
          var n = m.addedNodes[j];
          if (n.nodeType !== 1) continue;
          if (n.tagName === "STYLE" || n.tagName === "LINK") { later(); continue; }
          processTree(n);
        }
      }
    }).observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ["style"] });
    // Stylesheets that finish loading after the first pass.
    window.addEventListener("load", later);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
