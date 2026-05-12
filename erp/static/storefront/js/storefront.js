/* ==========================================================
   Storefront ERP UI — drag-drop reordering, inline toggles,
   toast notifications. Uses SortableJS from CDN (loaded by
   each template that needs it).
   ========================================================== */
(function () {
  if (window.__sf_inited) return;
  window.__sf_inited = true;

  // --- CSRF helper ---------------------------------------------------------
  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    if (m) return m[1];
    const input = document.querySelector('input[name=csrfmiddlewaretoken]');
    return input ? input.value : '';
  }

  // --- Toast ---------------------------------------------------------------
  function ensureToastRoot() {
    let root = document.getElementById('sfToastRoot');
    if (!root) {
      root = document.createElement('div');
      root.id = 'sfToastRoot';
      root.className = 'sf-toast-root';
      document.body.appendChild(root);
    }
    return root;
  }
  function toast(msg, kind) {
    const root = ensureToastRoot();
    const el = document.createElement('div');
    el.className = `sf-toast sf-toast-${kind || 'ok'}`;
    el.textContent = msg;
    root.appendChild(el);
    requestAnimationFrame(() => el.classList.add('show'));
    setTimeout(() => {
      el.classList.remove('show');
      setTimeout(() => el.remove(), 240);
    }, 1800);
    // Successful change → notify any listening preview pane to reload.
    if (kind !== 'err') {
      document.dispatchEvent(new CustomEvent('sf:changed'));
    }
  }
  window.sfToast = toast;

  // --- Reorder helper ------------------------------------------------------
  // model: 'navmenu' | 'homesection' | ...; getItems returns [{id, order}]
  async function postReorder(model, items) {
    const url = `/storefront/api/reorder/${model}/`;
    try {
      const res = await fetch(url, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrf(),
        },
        body: JSON.stringify({ items }),
      });
      if (!res.ok) throw new Error(res.status);
      toast('Sıralama kaydedildi');
    } catch (e) {
      toast('Kaydedilemedi — tekrar dene', 'err');
    }
  }

  // --- Initialise SortableJS on every list with [data-sortable] -----------
  // The list must include data-sortable-model="navmenu", and each child must
  // carry data-sortable-id="<pk>". We re-emit `order` based on DOM index.
  function initSortable(list) {
    if (!window.Sortable) return;
    const model = list.getAttribute('data-sortable-model');
    if (!model) return;
    new Sortable(list, {
      animation: 180,
      handle: '[data-sortable-handle]',
      ghostClass: 'sf-sortable-ghost',
      chosenClass: 'sf-sortable-chosen',
      dragClass: 'sf-sortable-drag',
      onEnd: () => {
        const items = Array.from(list.querySelectorAll('[data-sortable-id]')).map(
          (el, idx) => ({ id: parseInt(el.getAttribute('data-sortable-id'), 10), order: idx }),
        );
        // Update visible #order labels in-place (best-effort).
        items.forEach(({ id, order }) => {
          const el = list.querySelector(`[data-sortable-id="${id}"] .sf-menu-order`);
          if (el) el.textContent = `#${order}`;
        });
        postReorder(model, items);
      },
    });
  }

  function ready(fn) {
    if (document.readyState !== 'loading') fn();
    else document.addEventListener('DOMContentLoaded', fn);
  }
  // --- Drop-zone image input ----------------------------------------------
  function initDropZone(drop) {
    const input = drop.querySelector('.sf-drop-input');
    const preview = drop.querySelector('.sf-drop-preview');
    const previewImg = preview ? preview.querySelector('img') : null;
    const zone = drop.querySelector('.sf-drop-zone');
    const clearBtn = drop.querySelector('.sf-drop-clear');
    if (!input || !preview || !previewImg || !zone) return;

    function showFile(file) {
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (e) => {
        previewImg.src = e.target.result;
        preview.hidden = false;
        zone.style.display = 'none';
      };
      reader.readAsDataURL(file);
    }
    input.addEventListener('change', () => {
      if (input.files && input.files[0]) showFile(input.files[0]);
    });
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        input.value = '';
        preview.hidden = true;
        zone.style.display = '';
      });
    }
    // Visual drag highlight (the input already handles drop natively)
    ['dragenter', 'dragover'].forEach((ev) =>
      drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('is-drag'); }),
    );
    ['dragleave', 'drop'].forEach((ev) =>
      drop.addEventListener(ev, () => drop.classList.remove('is-drag')),
    );
  }

  // --- Live preview pane: device switcher + reload --------------------
  function initPreview(root) {
    const wrap = root.querySelector('[data-preview-wrap]');
    const iframe = root.querySelector('[data-preview-iframe]');
    const devices = root.querySelectorAll('.sf-dv');
    const reloadBtn = root.querySelector('[data-preview-reload]');
    const pageSelect = root.querySelector('[data-preview-pageselect]');
    const baseHost = (root.getAttribute('data-preview-base') || 'http://localhost:3010').replace(/\/$/, '');
    if (!wrap || !iframe) return;

    devices.forEach((btn) => {
      btn.addEventListener('click', () => {
        devices.forEach((b) => b.classList.remove('on'));
        btn.classList.add('on');
        wrap.style.maxWidth = btn.getAttribute('data-w') || '100%';
        wrap.style.margin = btn.getAttribute('data-w') === '100%' || !btn.getAttribute('data-w')
          ? '0' : '0 auto';
      });
    });

    function loadPath(path) {
      // Build absolute URL on the Belino origin; always force ?edit=1
      // and a cache-buster. URL() handles existing query strings in
      // `path` (e.g. /products?cat=erkek-corap) — naive concatenation
      // would produce double-`?`.
      const u = new URL(baseHost + (path || '/'));
      u.searchParams.set('edit', '1');
      // base (no cache-buster) for future reloads
      const baseUrl = new URL(baseHost + (path || '/'));
      baseUrl.searchParams.set('edit', '1');
      iframe.setAttribute('data-base-src', baseUrl.toString());
      u.searchParams.set('_t', Date.now().toString());
      iframe.src = u.toString();
      try { localStorage.setItem('sf-preview-path', path || '/'); } catch {}
    }

    function reload() {
      const stored = (() => {
        try { return localStorage.getItem('sf-preview-path') || '/'; } catch { return '/'; }
      })();
      loadPath(stored);
    }
    if (reloadBtn) reloadBtn.addEventListener('click', reload);

    if (pageSelect) {
      // Restore last-selected page on mount.
      let initial = '/';
      try { initial = localStorage.getItem('sf-preview-path') || '/'; } catch {}
      pageSelect.value = initial;
      // Only swap iframe if the current src doesn't already match.
      const currentBase = iframe.getAttribute('data-base-src') || '';
      if (!currentBase.includes(initial)) loadPath(initial);
      pageSelect.addEventListener('change', () => loadPath(pageSelect.value));
    }

    // Auto-reload after a successful in-page action (toast/save).
    document.addEventListener('sf:changed', reload);
  }

  // --- Visual editor postMessage bridge ----------------------------------
  // Storefront iframe (with ?edit=1) sends `{source:'<brand>-editor', type, ...}`
  // for select/reorder/text/image actions. We translate to ERP API + iframe
  // reload. Accept any brand suffix so the same ERP serves multiple stores
  // (belino-editor, demfirat-editor, storefront-editor, …).
  const EDITOR_SOURCES = new Set(['belino-editor', 'demfirat-editor', 'storefront-editor']);
  function initEditorBridge() {
    window.addEventListener('message', async (e) => {
      const msg = e.data;
      if (!msg || !EDITOR_SOURCES.has(msg.source)) return;

      if (msg.type === 'select') {
        const zone = msg.zone;
        if (!zone) return;
        toast(`${zone} açılıyor…`);
        window.location.href = `/storefront/home/jump/${encodeURIComponent(zone)}/`;
        return;
      }

      if (msg.type === 'reorder') {
        const { model, items } = msg;
        if (!model || !items || !items.length) return;
        try {
          const res = await fetch(`/storefront/api/reorder/${model}/`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
            body: JSON.stringify({ items }),
          });
          if (!res.ok) throw new Error(res.status);
          toast('Sıralama kaydedildi');
          reloadPreviewIframe();
        } catch (err) {
          toast('Sıralama kaydedilemedi', 'err');
        }
        return;
      }

      if (msg.type === 'text') {
        const { model, pk, field, value } = msg;
        if (!model || !pk || !field) return;
        try {
          const res = await fetch(`/storefront/api/text/${model}/${pk}/`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
            body: JSON.stringify({ field, value }),
          });
          if (!res.ok) throw new Error(res.status);
          toast('Metin kaydedildi');
        } catch (err) {
          toast('Kaydedilemedi', 'err');
        }
        return;
      }

      if (msg.type === 'image-upload') {
        // Belino sent a file as base64 via postMessage. We rebuild a
        // Blob and POST to the ERP image API on its own origin so the
        // session cookie is sent normally (no cross-origin headache).
        const { model, pk, field, filename, dataUrl } = msg;
        if (!model || !pk || !field || !dataUrl) return;
        try {
          const [meta, b64] = dataUrl.split(',');
          const mime = (meta.match(/data:([^;]+);base64/) || [])[1] || 'image/png';
          const bin = atob(b64);
          const len = bin.length;
          const bytes = new Uint8Array(len);
          for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
          const blob = new Blob([bytes], { type: mime });
          const fd = new FormData();
          fd.append('field', field);
          fd.append('file', blob, filename || 'upload.png');
          const res = await fetch(`/storefront/api/image/${model}/${pk}/`, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': getCsrf() },
            body: fd,
          });
          const data = await res.json().catch(() => ({}));
          if (!res.ok || !data.url) throw new Error(data.error || res.status);
          toast('Görsel güncellendi');
          reloadPreviewIframe();
        } catch (err) {
          toast('Görsel yüklenemedi: ' + (err && err.message ? err.message : err), 'err');
        }
        return;
      }
    });
  }

  function reloadPreviewIframe() {
    const iframe = document.querySelector('[data-preview-iframe]');
    if (!iframe) return;
    const base = iframe.getAttribute('data-base-src') || iframe.src;
    const u = new URL(base, window.location.origin);
    u.searchParams.set('_t', Date.now().toString());
    iframe.src = u.toString();
  }

  ready(() => {
    document.querySelectorAll('[data-sortable]').forEach(initSortable);
    document.querySelectorAll('[data-sf-drop]').forEach(initDropZone);
    document.querySelectorAll('[data-preview-root]').forEach(initPreview);
    initEditorBridge();

    // Inline toggle (aktif/pasif pill).
    document.body.addEventListener('click', async (e) => {
      const btn = e.target.closest('[data-toggle-active]');
      if (!btn) return;
      e.preventDefault();
      const model = btn.getAttribute('data-toggle-active');
      const pk = btn.getAttribute('data-id');
      btn.disabled = true;
      try {
        const res = await fetch(`/storefront/api/toggle/${model}/${pk}/`, {
          method: 'POST',
          credentials: 'same-origin',
          headers: { 'X-CSRFToken': getCsrf() },
        });
        if (!res.ok) throw new Error(res.status);
        const data = await res.json();
        btn.classList.toggle('sf-pill-on', data.is_active);
        btn.classList.toggle('sf-pill-off', !data.is_active);
        btn.textContent = data.is_active ? 'aktif' : 'pasif';
        toast(data.is_active ? 'Aktif edildi' : 'Pasif edildi');
      } catch (err) {
        toast('Değiştirilemedi', 'err');
      } finally {
        btn.disabled = false;
      }
    });
  });
})();
