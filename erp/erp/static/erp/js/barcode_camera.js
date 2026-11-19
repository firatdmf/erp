/*
 * The phone camera as a barcode reader — ONE reader for every page.
 *
 * Staff scan with their phones, never a handheld scanner. Every page that
 * reads a barcode reads it through this file; none carries a copy of the
 * camera, the lens choice, the decoder or its loading.
 *
 * Two layers:
 *
 * 1. The reader — the camera and the decoding, for a page with a screen of
 *    its own (the packing page, the warehouse's "Find by barcode"):
 *
 *      var reader = NejumCamera.reader({
 *        video: videoEl,
 *        onCode: function (code) {...},   // each new read, beeped
 *        accept: function () { return !paused; },   // optional
 *        onStatus: function (text) {...}, // "no picture", reader errors
 *        soundOnRead: false,              // the page sounds the outcome:
 *                                         // NejumCamera.sound('ok'|'error')
 *        diag: diagEl,                    // optional small-print line
 *      });
 *      reader.start(); reader.pause(); reader.resume(); reader.stop();
 *      reader.track()                     // the video track (torch)
 *
 *    plus NejumCamera.rearStream(), .decodeImage(imageData) for a still,
 *    and .beep().
 *
 * 2. The popup — a whole scan screen for a page that only needs "read a
 *    code, then do something with it" (the order form, the purchase form):
 *
 *      NejumCamera.open({
 *        title: "Scan barcode",
 *        // What the code is: {ok: true, title, facts: [[label, value]],
 *        // notice} or {ok: false, kind: "warn"|"bad", headline, detail}.
 *        lookup: function (code) {...},
 *        // Do it. Truthy when it worked, or an object like lookup's to
 *        // show on the card instead.
 *        confirm: function (code) {...},
 *        confirmLabel: "Add to order",
 *        doneHeadline: "Added to the order",
 *        failHeadline: "Could not be added",
 *        // Add on a good read instead of asking first; the lookup is
 *        // still the check.
 *        addOnRead: true,
 *        onClose: function () {},
 *      });
 *
 *    A box under the picture takes a typed code for a label the camera
 *    can't read; it goes the same way as a read.
 *
 * The reader stops on each read (the popup pauses it, a page passes
 * `accept`), so one label is one read. Words come from
 * window.NJ_CAMERA_TEXT (components/barcode_camera.html), translated there.
 */
(function () {
  if (window.NejumCamera) return;

  function T(key, fallback) {
    return (window.NJ_CAMERA_TEXT && window.NJ_CAMERA_TEXT[key]) || fallback;
  }
  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
      return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c];
    });
  }
  function now() { return (window.performance && performance.now) ? performance.now() : Date.now(); }

  // ══ The decoder ═══════════════════════════════════════════════════
  // The decoder is a file of its own, fetched on the first read. The
  // library keeps a failed fetch and answers every later read with it, so
  // one dropped download left the reader dead until the page was
  // reloaded. Until a read has come back, a failure is taken to be that
  // file and it is fetched again, from the next host.
  var zx = null, zxMod = null, zxLoading = null, zxReady = false, zxWasmTry = 0;
  var ZXW_WASM = ['https://unpkg.com/zxing-wasm@3.1.0/dist/reader/zxing_reader.wasm',
    'https://esm.sh/zxing-wasm@3.1.0/dist/reader/zxing_reader.wasm',
    'https://fastly.jsdelivr.net/npm/zxing-wasm@3.1.0/dist/reader/zxing_reader.wasm'];
  var ZXW_OPTS = {tryHarder: true, tryRotate: true, tryDownscale: true, maxNumberOfSymbols: 1,
    formats: ['Code128', 'EAN-13', 'EAN-8', 'UPC-A', 'UPC-E', 'Code39', 'Code93', 'ITF', 'Codabar', 'QRCode']};

  function loadZxw() {
    if (zx) return Promise.resolve(zx);
    if (zxLoading) return zxLoading;
    // The reader-only build: the package's root entry also carries the
    // barcode writer, and half a megabyte more to download.
    var urls = ['https://cdn.jsdelivr.net/npm/zxing-wasm@3.1.0/reader/+esm', 'https://esm.sh/zxing-wasm@3.1.0/reader'];
    function tryNext(i) {
      if (i >= urls.length) return Promise.reject(new Error('zxing load failed'));
      return import(urls[i]).then(function (mod) {
        if (mod && mod.readBarcodes) return mod; throw new Error('no export');
      }).catch(function () { return tryNext(i + 1); });
    }
    // A load that failed is forgotten, so the next open tries again.
    zxLoading = tryNext(0).then(function (mod) { zxMod = mod; zx = mod.readBarcodes; return zx; })
      .catch(function (err) { zxLoading = null; throw err; });
    return zxLoading;
  }
  function zxNextHost() {
    if (!zxMod || !zxMod.prepareZXingModule || zxWasmTry >= ZXW_WASM.length * 2) return false;
    var url = ZXW_WASM[zxWasmTry % ZXW_WASM.length];
    zxWasmTry++;
    try {
      zxMod.prepareZXingModule({overrides: {locateFile: function (path, prefix) {
        return /\.wasm$/.test(path) ? url : prefix + path; }}});
    } catch (e) { return false; }
    return true;
  }
  // Read one frame. Resolves to the text, or '' when there is none; a
  // decoder that failed to fetch is fetched again before giving up.
  function decode(img) {
    return loadZxw().then(function () {
      return zx(img, ZXW_OPTS).then(function (res) {
        zxReady = true;
        return (res && res.length && res[0].text) ? res[0].text.toString().trim() : '';
      }, function (err) {
        if (!zxReady && zxNextHost()) return decode(img);
        throw err;
      });
    });
  }

  // ══ The camera ════════════════════════════════════════════════════
  // The main rear lens: a phone lists several, and its ultra-wide, tele or
  // macro one cannot focus on a label at hand's length. Plain "wide" stays
  // in: the main lens is a wide-angle.
  var BAD_LENS = /ultra|0\.5|tele|macro|depth|truedepth|infrared|fish/i;
  function camIndex(label) { var m = (label || '').match(/camera2?\s*(\d+)/i); return m ? parseInt(m[1], 10) : 999; }
  function applyFocus(stream) {
    try { var tk = stream.getVideoTracks()[0];
      if (tk && tk.applyConstraints) tk.applyConstraints({advanced: [{focusMode: 'continuous'}]}).catch(function () {}); }
    catch (e) {}
    return stream;
  }
  function rearStream() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      return Promise.reject(new Error(T('unsupported', 'The camera is not supported')));
    }
    var W = {ideal: 1920}, H = {ideal: 1080};
    function open(c) { return navigator.mediaDevices.getUserMedia({video: c, audio: false}); }
    return open({facingMode: {ideal: 'environment'}, width: W, height: H}).then(function (stream) {
      if (!navigator.mediaDevices.enumerateDevices) return applyFocus(stream);
      // Not being able to list the lenses is no reason to give up the
      // stream already in hand — it is read as "one camera" instead.
      return navigator.mediaDevices.enumerateDevices().catch(function () { return []; }).then(function (devices) {
        var cams = devices.filter(function (d) { return d.kind === 'videoinput'; });
        if (cams.length < 2) return applyFocus(stream);
        var rear = cams.filter(function (d) { return /back|rear|environment|arka|tras|rück/i.test(d.label || ''); });
        if (!rear.length) rear = cams;
        var pool = rear.filter(function (d) { return !BAD_LENS.test(d.label || ''); }); if (!pool.length) pool = rear;
        var iosMain = pool.filter(function (d) { return /(^|\b)back camera\b/i.test(d.label || ''); });
        var sorted = pool.slice().sort(function (a, b) { return camIndex(a.label) - camIndex(b.label); });
        var pick = iosMain[0] || sorted[0], curId = '';
        try { curId = (stream.getVideoTracks()[0].getSettings() || {}).deviceId || ''; } catch (e) {}
        if (pick && pick.deviceId && pick.deviceId !== curId) {
          stream.getTracks().forEach(function (t) { t.stop(); });
          // The first stream is stopped by now, so a lens that will not
          // open cannot fall back to it: that handed the page a dead
          // stream and a black picture. Ask plainly for a rear camera.
          return open({deviceId: {exact: pick.deviceId}, width: W, height: H})
            .catch(function () { return open({facingMode: {ideal: 'environment'}}); })
            .then(applyFocus);
        }
        return applyFocus(stream);
      });
    });
  }
  var audioCtx = null;
  // What a read came to, by ear: a short high beep when it was found or
  // added, a low double buzz (and a longer vibration) when it was not —
  // so a packer knows without looking at the screen.
  function sound(kind) {
    if (kind !== 'error') { beep(880); return; }
    try { if (navigator.vibrate) navigator.vibrate([90, 60, 90]); } catch (e) {}
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume();
      [0, 0.17].forEach(function (at) {
        var o = audioCtx.createOscillator(), g = audioCtx.createGain(), t0 = audioCtx.currentTime + at;
        o.type = 'square'; o.frequency.value = 196; g.gain.value = 0.05;
        o.connect(g); g.connect(audioCtx.destination); o.start(t0); o.stop(t0 + 0.11);
      });
    } catch (e) {}
  }
  function beep(freq) {
    try { if (navigator.vibrate) navigator.vibrate(55); } catch (e) {}
    try {
      audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
      if (audioCtx.state === 'suspended') audioCtx.resume();
      var o = audioCtx.createOscillator(), g = audioCtx.createGain();
      o.type = 'sine'; o.frequency.value = freq || 880; g.gain.value = 0.07;
      o.connect(g); g.connect(audioCtx.destination); o.start(); o.stop(audioCtx.currentTime + 0.08);
    } catch (e) {}
  }

  // ══ 1. The reader ═════════════════════════════════════════════════
  function reader(cfg) {
    var video = cfg.video, stream = null, raf = null, running = false, lastDecode = 0;
    var debounce = {val: '', t: 0}, canvas = null, frames = 0, decodeErr = '';
    var openedAt = 0, light = -1, diagAt = 0;
    function status(text) { if (cfg.onStatus) cfg.onStatus(text); }

    function diag(t) {
      var el = cfg.diag;
      if (!el || (t - diagAt) < 1000) return;
      diagAt = t;
      var tk = null, st = {};
      try { tk = stream && stream.getVideoTracks()[0]; st = (tk && tk.getSettings && tk.getSettings()) || {}; } catch (e) {}
      el.textContent = [
        (tk && tk.label) || 'no track',
        (st.width || '?') + 'x' + (st.height || '?'),
        'video ' + video.videoWidth + 'x' + video.videoHeight + (video.paused ? ' paused' : ' playing'),
        tk ? tk.readyState + (tk.muted ? ' muted' : '') : '',
        'frames ' + frames,
        light < 0 ? '' : 'light ' + light,
        zxReady ? 'reader ok' : (zx ? 'reader loading' : 'reader not loaded')
      ].filter(Boolean).join(' · ');
    }

    function onDecode(code) {
      code = (code || '').toString().trim();
      if (!code) return;
      if (cfg.accept && !cfg.accept()) return;
      var t = now();
      if (code === debounce.val && (t - debounce.t) < (cfg.debounceMs || 1600)) return;
      debounce = {val: code, t: t};
      // A page that says what the read came to sounds it then, found or
      // not (sound()); one that doesn't beeps on the read itself.
      if (cfg.soundOnRead !== false) beep();
      cfg.onCode(code);
    }

    function loop() {
      if (!running) return;
      var t = now();
      diag(t);
      if (!zx || !video.videoWidth || video.readyState < 2 || (t - lastDecode) < 120) {
        // Five seconds with no frame is not "hold it steadier", it is a
        // camera that never started. Say so instead of the aiming prompt.
        if (openedAt && (t - openedAt) > 5000 && !frames) {
          status(!zx ? T('loadFailed', 'Scanner did not load — check the connection')
                     : T('noPicture', 'No picture is coming from the camera'));
        }
        raf = requestAnimationFrame(loop); return;
      }
      frames++;
      lastDecode = t;
      try {
        canvas = canvas || document.createElement('canvas');
        // The full width (long Code128 labels need their quiet zones) and
        // the middle of the height, at most 1280px wide.
        var vw = video.videoWidth, vh = video.videoHeight;
        var cropH = Math.round(vh * (cfg.cropHeight || 0.60)), sy = Math.round((vh - cropH) / 2);
        var outW = Math.min(1280, vw), outH = Math.max(1, Math.round(cropH * (outW / vw)));
        if (canvas.width !== outW) canvas.width = outW;
        if (canvas.height !== outH) canvas.height = outH;
        var cx = canvas.getContext('2d', {willReadFrequently: true});
        cx.drawImage(video, 0, sy, vw, cropH, 0, 0, outW, outH);
        var img = cx.getImageData(0, 0, outW, outH);
        // How bright the frame given to the reader is, 0–255, off a
        // sparse sample: a black picture over a bright frame is the
        // screen's fault, over a dark one the camera's.
        var px = img.data, sum = 0, n = 0;
        for (var p = 0; p < px.length; p += 4000) { sum += px[p] + px[p + 1] + px[p + 2]; n += 3; }
        light = n ? Math.round(sum / n) : -1;
        zx(img, ZXW_OPTS).then(function (res) {
          zxReady = true;
          if (running && res && res.length && res[0].text) onDecode(res[0].text);
        }).catch(function (err) {
          if (!zxReady && zxNextHost()) return;
          // Once, not once per frame — this fires 8×/second.
          var msg = (err && err.message) || String(err);
          if (msg !== decodeErr) {
            decodeErr = msg;
            console.error('[barcode-camera] decode failed', err);
            status(T('readerError', 'Reader error') + ': ' + msg);
          }
        }).finally(function () { if (running) raf = requestAnimationFrame(loop); });
      } catch (e) { if (running) raf = requestAnimationFrame(loop); }
    }

    function play() {
      // autoplay alone is not enough on a <video> whose container was
      // display:none until this tap — Safari leaves it at readyState 0.
      try { var pl = video.play(); if (pl && pl.catch) pl.catch(function () {}); } catch (e) {}
    }

    var api = {
      start: function () {
        frames = 0; decodeErr = ''; light = -1; diagAt = 0; openedAt = now();
        debounce = {val: '', t: 0};
        if (!zxReady) zxWasmTry = 0;
        if (cfg.diag) cfg.diag.textContent = '';
        if (running) return Promise.resolve(stream);
        return rearStream().then(function (s) {
          stream = s; video.srcObject = s; running = true; lastDecode = 0;
          play();
          loadZxw().then(loop).catch(function (err) {
            console.error('[barcode-camera] zxing load failed', err);
            status(T('loadFailed', 'Scanner did not load — check the connection'));
          });
          return s;
        });
      },
      // Stop reading, keep the stream: resuming is instant, where asking
      // for the camera again is slow and, on iOS, prompts.
      pause: function () { running = false; if (raf) { cancelAnimationFrame(raf); raf = null; } },
      resume: function () {
        debounce = {val: '', t: 0};
        frames = 0; decodeErr = ''; openedAt = now();
        if (stream && video.srcObject) {
          if (running) return Promise.resolve(stream);
          running = true; lastDecode = 0; play();
          loadZxw().then(loop).catch(function () {});
          return Promise.resolve(stream);
        }
        return api.start();
      },
      stop: function () {
        api.pause();
        if (stream) { stream.getTracks().forEach(function (t) { t.stop(); }); stream = null; }
        video.srcObject = null;
      },
      track: function () { try { return stream ? stream.getVideoTracks()[0] : null; } catch (e) { return null; } },
      running: function () { return running; },
    };
    return api;
  }

  // ══ 2. The popup ══════════════════════════════════════════════════
  // Above everything, the create sidebar included (.sidebar-overlay is
  // z-index 10000): opened from inside it, a popup that does not
  // out-stack it runs the camera where nothing is visible.
  var CSS = [
    '.nj-cam-overlay{position:fixed;inset:0;z-index:10050;display:none;align-items:center;justify-content:center;background:rgba(6,10,18,.9);padding:16px;}',
    '.nj-cam-overlay.show{display:flex;}',
    '.nj-cam-shell{width:100%;max-width:460px;background:linear-gradient(180deg,#101826 0%,#0B1220 100%);border:1px solid rgba(94,234,212,.10);border-radius:20px;overflow:hidden;box-shadow:0 24px 70px rgba(0,0,0,.6);display:flex;flex-direction:column;max-height:94vh;}',
    '.nj-cam-head{display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid rgba(255,255,255,.08);flex-shrink:0;}',
    '.nj-cam-title{color:#fff;font:700 14.5px var(--font-sans,sans-serif);display:inline-flex;align-items:center;gap:10px;}',
    '.nj-cam-title i{color:#2DD4BF;}',
    '.nj-cam-close{background:rgba(255,255,255,.08);border:none;color:#fff;width:34px;height:34px;padding:0;border-radius:10px;cursor:pointer;font-size:15px;transition:background .14s;}',
    '.nj-cam-close:hover{background:rgba(255,255,255,.16);}',
    '.nj-cam-view{position:relative;background:#000;width:100%;aspect-ratio:3/4;max-height:52vh;overflow:hidden;}',
    '.nj-cam-view video{width:100%;height:100%;object-fit:cover;display:block;background:#000;}',
    '.nj-cam-guide{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;pointer-events:none;}',
    '.nj-cam-frame{position:relative;width:82%;height:30%;border-radius:16px;box-shadow:0 0 0 2000px rgba(4,10,18,.42);}',
    '.nj-cam-frame .c{position:absolute;width:28px;height:28px;border:3px solid #2DD4BF;filter:drop-shadow(0 0 6px rgba(45,212,191,.55));}',
    '.nj-cam-frame .c1{top:-2px;left:-2px;border-right:none;border-bottom:none;border-top-left-radius:14px;}',
    '.nj-cam-frame .c2{top:-2px;right:-2px;border-left:none;border-bottom:none;border-top-right-radius:14px;}',
    '.nj-cam-frame .c3{bottom:-2px;left:-2px;border-right:none;border-top:none;border-bottom-left-radius:14px;}',
    '.nj-cam-frame .c4{bottom:-2px;right:-2px;border-left:none;border-top:none;border-bottom-right-radius:14px;}',
    '.nj-cam-laser{position:absolute;left:7%;right:7%;top:14%;height:2px;border-radius:2px;background:linear-gradient(90deg,transparent,#2DD4BF 30%,#5EEAD4 50%,#2DD4BF 70%,transparent);box-shadow:0 0 14px 2px rgba(45,212,191,.65);animation:njCamLaser 2.2s ease-in-out infinite;}',
    '@keyframes njCamLaser{0%,100%{top:12%}50%{top:84%}}',
    // Doubles as the status line: the reader writes the live code, and a
    // reader that never starts writes why, in the same place.
    '.nj-cam-hint{margin-top:16px;display:inline-flex;align-items:center;gap:8px;color:#fff;font:600 12.5px var(--font-sans,sans-serif);background:rgba(4,10,18,.62);border:1px solid rgba(255,255,255,.12);padding:6px 14px;border-radius:14px;max-width:86%;overflow:hidden;overflow-wrap:anywhere;}',
    ".nj-cam-hint::before{content:'';width:7px;height:7px;border-radius:50%;background:#2DD4BF;flex-shrink:0;animation:njCamPulse 1.4s ease-in-out infinite;}",
    '@keyframes njCamPulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.35;transform:scale(.7)}}',
    // What the camera and the reader are doing, in small print: a phone
    // showing a black picture can be told apart from a screenshot.
    '.nj-cam-diag{position:absolute;left:0;right:0;bottom:6px;padding:0 10px;text-align:center;pointer-events:none;color:rgba(255,255,255,.55);font:500 10px/1.3 ui-monospace,SFMono-Regular,Menlo,monospace;overflow-wrap:anywhere;}',
    // A label the camera can't read is typed here, and goes as a read.
    '.nj-cam-type{display:flex;gap:8px;padding:12px 14px;border-top:1px solid rgba(255,255,255,.08);}',
    '.nj-cam-type input{flex:1;min-width:0;height:40px;padding:0 12px;border-radius:10px;border:1px solid rgba(255,255,255,.16);background:rgba(255,255,255,.06);color:#fff;font:600 14px ui-monospace,monospace;}',
    '.nj-cam-type input::placeholder{color:rgba(255,255,255,.45);font-family:var(--font-sans,sans-serif);}',
    '.nj-cam-type button{height:40px;padding:0 16px;border:0;border-radius:10px;background:linear-gradient(135deg,#0D9488,#0F766E);color:#fff;font:700 12.5px var(--font-sans,sans-serif);cursor:pointer;}',
    '.nj-cam-result{padding:18px;color:#fff;overflow-y:auto;text-align:center;}',
    '@media (max-width:520px){ .nj-cam-shell{max-width:100%;} }'
  ].join('\n');

  var el = null, rd = null, video, stageEl, panelEl, hitEl, titleEl, typeEl;
  var opts = {}, lastFound = null, camPending = '', camPrevOverflow = '';

  function build() {
    if (el) return;
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);
    el = document.createElement('div');
    el.className = 'nj-cam-overlay';
    el.setAttribute('role', 'dialog');
    el.setAttribute('aria-modal', 'true');
    el.innerHTML =
      '<div class="nj-cam-shell">' +
        '<div class="nj-cam-head">' +
          '<div class="nj-cam-title"><i class="fas fa-barcode"></i><span></span></div>' +
          '<button type="button" class="nj-cam-close" title="' + esc(T('close', 'Close')) + '"><i class="fas fa-times"></i></button>' +
        '</div>' +
        '<div class="nj-cam-stage">' +
          '<div class="nj-cam-view">' +
            '<video playsinline muted autoplay></video>' +
            '<div class="nj-cam-guide">' +
              '<div class="nj-cam-frame"><span class="c c1"></span><span class="c c2"></span>' +
                '<span class="c c3"></span><span class="c c4"></span><div class="nj-cam-laser"></div></div>' +
              '<div class="nj-cam-hint"></div>' +
            '</div>' +
            '<div class="nj-cam-diag"></div>' +
          '</div>' +
          '<form class="nj-cam-type" autocomplete="off">' +
            '<input type="text" inputmode="text" spellcheck="false" placeholder="' + esc(T('typePlaceholder', 'Or type the barcode')) + '">' +
            '<button type="submit">' + esc(T('typeGo', 'Go')) + '</button>' +
          '</form>' +
        '</div>' +
        '<div class="nj-cam-result" style="display:none;"></div>' +
      '</div>';
    // The popup belongs to the body: a transformed parent (the create
    // drawer) would otherwise be what position:fixed fills.
    document.body.appendChild(el);
    video = el.querySelector('video');
    stageEl = el.querySelector('.nj-cam-stage');
    panelEl = el.querySelector('.nj-cam-result');
    hitEl = el.querySelector('.nj-cam-hint');
    titleEl = el.querySelector('.nj-cam-title span');
    typeEl = el.querySelector('.nj-cam-type input');
    rd = reader({
      video: video,
      soundOnRead: false,                   // the outcome is sounded below
      diag: el.querySelector('.nj-cam-diag'),
      onStatus: function (text) { hitEl.textContent = text; },
      onCode: function (code) {
        hitEl.textContent = code;
        // Stop reading and handle this one. One label is one read.
        rd.pause();
        camRead(code);
      },
    });
    el.querySelector('.nj-cam-close').addEventListener('click', close);
    // A click on the backdrop closes; one inside the card does not.
    el.addEventListener('click', function (e) { if (e.target === el) close(); });
    // Escape closes it, like every other modal on the site.
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && el.classList.contains('show')) { e.preventDefault(); close(); }
    });
    // A typed code goes exactly the way a read goes.
    el.querySelector('.nj-cam-type').addEventListener('submit', function (e) {
      e.preventDefault();
      var code = (typeEl.value || '').trim();
      if (!code) { typeEl.focus(); return; }
      typeEl.value = '';
      try { typeEl.blur(); } catch (err) {}
      rd.pause();
      camRead(code);
    });
    // The panel's buttons, delegated: the panel is rewritten per read.
    panelEl.addEventListener('click', function (e) {
      var b = e.target.closest('[data-nj-cam]');
      if (!b) return;
      var act = b.getAttribute('data-nj-cam');
      if (act === 'again') again();
      else if (act === 'done') close();
      else if (act === 'confirm') confirmPending(lastFound);
    });
  }

  // ── The panel: what a read turned out to be ───────────────────────
  function camPanel(html) {
    stageEl.style.display = 'none';
    panelEl.style.display = 'block';
    panelEl.innerHTML = html;
    panelEl.scrollTop = 0;
  }
  function camStage() {
    panelEl.style.display = 'none';
    panelEl.innerHTML = '';
    stageEl.style.display = '';
  }
  function pill(kind, icon, text) {
    var c = kind === 'ok' ? ['rgba(16,185,129,.16)', '#34D399', 'rgba(52,211,153,.38)']
          : kind === 'warn' ? ['rgba(245,158,11,.16)', '#FBBF24', 'rgba(251,191,36,.38)']
          : ['rgba(244,63,94,.16)', '#FB7185', 'rgba(251,113,133,.38)'];
    return '<span style="display:inline-flex;align-items:center;gap:7px;padding:6px 13px;border-radius:999px;' +
      'background:' + c[0] + ';color:' + c[1] + ';border:1px solid ' + c[2] +
      ';font:700 12px var(--font-sans,sans-serif);"><i class="fas ' + icon + '"></i>' + esc(text) + '</span>';
  }
  function codeChip(code) {
    return '<div style="display:flex;align-items:center;justify-content:center;gap:9px;margin:11px 0;' +
      'padding:10px 13px;background:linear-gradient(135deg,rgba(20,127,116,.30),rgba(13,148,136,.10));' +
      'border:1px solid rgba(45,212,191,.35);border-radius:12px;font:800 16px ui-monospace,monospace;' +
      'color:#5EEAD4;letter-spacing:.04em;word-break:break-all;">' +
      '<i class="fas fa-barcode" style="opacity:.8;font-size:14px;flex-shrink:0;"></i>' + esc(code) + '</div>';
  }
  function btn(kind, act, icon, label) {
    var st = kind === 'primary'
      ? 'background:linear-gradient(135deg,#0D9488,#0F766E);color:#fff;box-shadow:0 6px 16px rgba(13,148,136,.35);'
      : 'background:rgba(255,255,255,.10);color:#fff;';
    return '<button type="button" data-nj-cam="' + act + '" style="flex:1;display:inline-flex;align-items:center;' +
      'justify-content:center;gap:7px;padding:11px 12px;border:0;border-radius:11px;cursor:pointer;' +
      'font:700 12.5px var(--font-sans,sans-serif);' + st + '"><i class="fas ' + icon + '"></i>' + esc(label) + '</button>';
  }
  function actions(buttons) { return '<div style="display:flex;gap:9px;margin-top:14px;">' + buttons + '</div>'; }
  function againBtn() { return btn('ghost', 'again', 'fa-rotate-right', T('again', 'Scan again')); }
  function doneBtn() { return btn('ghost', 'done', 'fa-xmark', T('done', 'Done')); }
  function fact(label, value) {
    return '<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;' +
      'padding:7px 0;border-top:1px solid rgba(255,255,255,.09);font:600 12px var(--font-sans,sans-serif);">' +
      '<span style="color:#94A3B8;">' + esc(label) + '</span>' +
      '<span style="color:#fff;font-weight:800;text-align:right;">' + esc(value) + '</span></div>';
  }
  function described(r) {
    return (r && r.notice ? '<div style="margin-bottom:8px;">' + pill('warn', 'fa-shuffle', r.notice) + '</div>' : '') +
      (r && r.title ? '<div style="font:800 14px var(--font-sans,sans-serif);line-height:1.3;margin-bottom:8px;">' +
                      esc(r.title) + '</div>' : '') +
      ((r && r.facts) || []).map(function (f) { return fact(f[0], f[1]); }).join('');
  }
  function spinner(code) {
    return '<div style="padding:22px 0;color:#CBD5E1;font:600 12.5px var(--font-sans,sans-serif);">' +
      '<i class="fas fa-spinner fa-spin"></i> ' + esc(code) + '</div>';
  }
  function refuse(kind, headline, detail, code) {
    sound('error');
    camPanel(
      pill(kind, 'fa-triangle-exclamation', headline) +
      (code ? codeChip(code) : '') +
      (detail ? '<div style="font:600 12.5px var(--font-sans,sans-serif);color:#CBD5E1;line-height:1.45;">' +
                esc(detail) + '</div>' : '') +
      actions(againBtn() + doneBtn()));
  }

  // Read -> look up -> add (addOnRead) or ask. The lookup must change
  // nothing, so a code that is never added leaves no trace.
  function camRead(code) {
    camPending = code;
    camPanel(spinner(code));
    Promise.resolve(opts.lookup ? opts.lookup(code) : {ok: true}).then(function (r) {
      if (camPending !== code) return;          // closed or rescanned meanwhile
      r = r || {ok: true};
      if (!r.ok) {
        refuse(r.kind || 'bad', r.headline || T('cannot', 'Cannot be added'), r.detail || '', code);
        return;
      }
      lastFound = r;
      if (opts.addOnRead) { confirmPending(r); return; }
      sound('ok');
      camPanel(
        pill('ok', 'fa-circle-check', T('read', 'Barcode read')) +
        codeChip(code) + described(r) +
        actions(againBtn() + btn('primary', 'confirm', 'fa-plus', opts.confirmLabel || T('add', 'Add'))));
    }, function () {
      if (camPending !== code) return;
      refuse('bad', T('notChecked', 'Barcode could not be checked'),
             T('checkConnection', 'Check the connection and try again.'), code);
    });
  }

  // The add goes through the page's own add path — its rules live there,
  // and a second copy here would be a second set to keep in step.
  // `found` — what the lookup said, shown on the card once it is added.
  function confirmPending(found) {
    var code = camPending;
    if (!code) return;
    camPanel(spinner(code));
    Promise.resolve(opts.confirm ? opts.confirm(code) : true).then(function (ok) {
      // The page may answer with a card of its own.
      if (ok && typeof ok === 'object') {
        if (ok.ok === false) {
          refuse(ok.kind || 'bad', ok.headline || opts.failHeadline || T('notAdded', 'Could not be added'),
                 ok.detail || '', code);
          return;
        }
        found = ok;
      }
      if (ok) {
        sound('ok');
        camPanel(pill(found && found.kind === 'warn' ? 'warn' : 'ok', 'fa-circle-check',
                      (found && found.headline) || opts.doneHeadline || T('added', 'Added')) +
                 codeChip(code) + described(found) + actions(againBtn() + doneBtn()));
      } else {
        // The page already said why; keep the way forward on screen
        // rather than a live camera that would re-read the same label.
        refuse('bad', opts.failHeadline || T('notAdded', 'Could not be added'), '', code);
      }
    }, function () {
      refuse('bad', opts.failHeadline || T('notAdded', 'Could not be added'), '', code);
    });
  }

  function again() {
    camPending = '';
    camStage();
    hitEl.textContent = T('aim', 'Bring the barcode into the frame');
    rd.resume().catch(function (err) { toast(T('camera', 'Camera') + ': ' + ((err && err.message) || err)); });
  }

  function toast(msg) {
    if (typeof window.showToast === 'function') window.showToast(msg, 'error');
    else alert(msg);
  }

  function open(options) {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      toast(T('unsupported', 'The camera is not supported'));
      return;
    }
    build();
    opts = options || {};
    lastFound = null;
    titleEl.textContent = opts.title || T('title', 'Scan barcode');
    // Remember the page's own scroll lock rather than assume there is
    // none: the create sidebar has already hidden the body's scrollbar,
    // and clearing it on close would let the page behind it scroll.
    // Remembered only on the way in — a reopen while showing would
    // remember our own lock.
    if (!el.classList.contains('show')) camPrevOverflow = document.body.style.overflow;
    el.classList.add('show');
    document.body.style.overflow = 'hidden';
    // A reopen starts on the camera, never on the last read's panel.
    camPending = '';
    camStage();
    typeEl.value = '';
    hitEl.textContent = T('aim', 'Bring the barcode into the frame');
    rd.start().catch(function (err) {
      toast(T('camera', 'Camera') + ': ' + ((err && err.message) || err));
      close();
    });
  }

  function close() {
    if (!el) return;
    camPending = '';
    camStage();
    rd.stop();
    var wasOpen = el.classList.contains('show');
    el.classList.remove('show');
    if (wasOpen) document.body.style.overflow = camPrevOverflow;
    var done = opts.onClose; opts = {};
    if (wasOpen && done) try { done(); } catch (e) {}
  }

  window.NejumCamera = {
    open: open, close: close,
    reader: reader, rearStream: rearStream, decodeImage: decode, beep: beep, sound: sound,
  };
})();
