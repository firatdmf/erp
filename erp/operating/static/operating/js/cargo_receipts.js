// Cargo receipts waiting to upload, for any form that posts them as
// cargo_receipts (the order page's cargo card, the Ship part page). The
// markup is operating/partials/_cargo_receipt_picker.html.
//
// Three ways in — the picker, the phone camera, a paste — and every file
// ends up in a hidden input of its own inside the form, posting as
// cargo_receipts. The picker and camera inputs are emptied after each use
// (their files copied out), so a second pick adds to the first instead of
// replacing it, and any one file can be taken off again. The previews are
// drawn from the parked inputs. Without DataTransfer (a very old browser)
// none of this runs, and the picker and camera post their files as they are.
(function () {
  // A phone photo is 3–5 MB and the server keeps a 2400 px JPEG of it
  // (DOCUMENT in erp/image_optimizer.py — the same edge and quality here), so
  // it is made that size before it is sent: a tenth of the upload.
  // What the browser can't draw (HEIC outside Safari, a damaged file)
  // goes up as it is and the server converts it.
  const SHRINK_EDGE = 2400, SHRINK_QUALITY = 0.82, ALREADY_SMALL_BYTES = 700000;
  async function shrink(file) {
    if (file.type === 'application/pdf' || /\.pdf$/i.test(file.name)) return file;
    const url = URL.createObjectURL(file);
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      const w = img.naturalWidth, h = img.naturalHeight;
      const scale = Math.min(1, SHRINK_EDGE / Math.max(w, h));
      const isJpeg = file.type === 'image/jpeg';
      if (isJpeg && scale === 1 && file.size <= ALREADY_SMALL_BYTES) return file;
      const draw = (src, cw, ch, white) => {
        const c = document.createElement('canvas');
        c.width = cw; c.height = ch;
        const ctx = c.getContext('2d');
        // A transparent PNG goes onto white, as it would print.
        if (white) { ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, cw, ch); }
        ctx.imageSmoothingQuality = 'high';
        ctx.drawImage(src, 0, 0, cw, ch);
        return c;
      };
      const tw = Math.max(1, Math.round(w * scale)), th = Math.max(1, Math.round(h * scale));
      // Halved in steps on the way down: one big jump blurs small print.
      let src = img, sw = w, sh = h;
      while (sw / 2 >= tw && sh / 2 >= th) {
        sw = Math.floor(sw / 2); sh = Math.floor(sh / 2);
        src = draw(src, sw, sh, false);
      }
      const blob = await new Promise(done => draw(src, tw, th, true).toBlob(done, 'image/jpeg', SHRINK_QUALITY));
      if (!blob || (isJpeg && blob.size >= file.size)) return file;
      return new File([blob], file.name.replace(/\.[^.]*$/, '') + '.jpg',
                      { type: 'image/jpeg', lastModified: file.lastModified });
    } catch (e) {
      return file;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function setFile(input, f) {
    const dt = new DataTransfer();
    dt.items.add(f);
    input.files = dt.files;
  }

  // A file's preview; its object URL is noted in `urls` to be revoked.
  function thumbFor(f, urls) {
    if (f.type === 'application/pdf') {
      const pdf = document.createElement('span');
      pdf.className = 'od-rcpt-thumb pdf';
      pdf.innerHTML = '<i class="fa fa-file-pdf"></i>';
      return pdf;
    }
    const thumb = document.createElement('img');
    thumb.className = 'od-rcpt-thumb';
    thumb.alt = '';
    const url = URL.createObjectURL(f);
    urls.push(url);
    thumb.src = url;
    // HEIC won't draw outside Safari; it is converted on upload.
    thumb.onerror = () => {
      const icon = document.createElement('span');
      icon.className = 'od-rcpt-thumb';
      icon.innerHTML = '<i class="fa fa-image"></i>';
      thumb.replaceWith(icon);
    };
    return thumb;
  }

  const PASTE_TYPES = { 'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp',
                        'image/heic': 'heic', 'image/heif': 'heif', 'application/pdf': 'pdf' };
  let pastedCount = 0;

  // Wires the picker inside `field` (a .od-rcpt-field element). Returns
  // null when the browser can't hold files in inputs — the plain inputs
  // then post as they are.
  function attach(field) {
    const shots = field.querySelector('.od-rcpt-shots');
    const pending = field.querySelector('.od-rcpt-pending');
    if (!shots || !pending || !window.DataTransfer) return null;
    const removeLabel = field.dataset.removeLabel || 'Remove';
    let previewUrls = [];

    const parked = () => Array.from(shots.querySelectorAll('input.od-rcpt-parked'));

    function render() {
      previewUrls.forEach(u => URL.revokeObjectURL(u));
      previewUrls = [];
      pending.innerHTML = '';
      const inputs = parked();
      inputs.forEach(input => {
        const f = input.files[0];
        const item = document.createElement('div');
        item.className = 'od-rcpt-item pending';
        const name = document.createElement('span');
        name.className = 'od-rcpt-name';
        name.textContent = f.name;
        const del = document.createElement('button');
        del.type = 'button';
        del.className = 'od-rcpt-del';
        del.title = removeLabel; del.setAttribute('aria-label', removeLabel);
        del.innerHTML = '<i class="fa fa-xmark"></i>';
        del.addEventListener('click', () => { input.remove(); render(); });
        item.append(thumbFor(f, previewUrls), name, del);
        pending.appendChild(item);
      });
      shots.hidden = !inputs.length;
    }

    function park(files) {
      files.forEach(f => {
        const input = document.createElement('input');
        input.type = 'file'; input.name = 'cargo_receipts'; input.hidden = true;
        input.className = 'od-rcpt-parked';
        setFile(input, f);
        shots.insertBefore(input, pending);
        // Shrunk while the rest of the form is filled in; a form that
        // waits for it (ready()) sends the small copy.
        input.shrunk = shrink(f).then(small => {
          if (small === f) return;
          setFile(input, small);
          if (input.isConnected) render();
        });
      });
      render();
    }

    field.querySelectorAll('.od-rcpt-pick input[type=file]').forEach(src => {
      src.removeAttribute('name');  // its files post from the parked copy
      src.addEventListener('change', () => { park(Array.from(src.files)); src.value = ''; });
    });

    // Paste: an image copied anywhere (a screenshot, a photo in an email,
    // the carrier's page) and pasted on the page joins the receipts while
    // the picker is on screen. A paste that carries text into a text field
    // (a tracking number) stays a text paste.
    document.addEventListener('paste', (e) => {
      if (!field.offsetParent || !e.clipboardData) return;
      const files = Array.from(e.clipboardData.files || []).filter(f => PASTE_TYPES[f.type]);
      if (!files.length) return;
      const t = e.target;
      const typing = t && (t.isContentEditable || /^(INPUT|TEXTAREA)$/.test(t.tagName));
      if (typing && (e.clipboardData.getData('text/plain') || '').trim()) return;
      e.preventDefault();
      // A clipboard image is always "image.png" — name it for where it
      // came from, and so the next one doesn't clash.
      park(files.map(f => new File([f], 'pasted-receipt-' + (++pastedCount) + '.' + PASTE_TYPES[f.type],
                                   { type: f.type })));
      const picks = field.querySelector('.od-rcpt-picks');
      if (picks) {
        picks.classList.add('pasted');
        setTimeout(() => picks.classList.remove('pasted'), 900);
      }
    });

    return {
      parked,
      render,
      thumbFor,
      // Every waiting receipt shrunk (or given up on).
      ready: () => Promise.all(parked().map(i => i.shrunk)),
      // Puts taken-out inputs back, in front of the previews.
      putBack: (inputs) => { inputs.forEach(i => shots.insertBefore(i, pending)); render(); },
      clear: () => { parked().forEach(i => i.remove()); render(); },
    };
  }

  window.NjCargoReceipts = { attach, shrink };
})();
