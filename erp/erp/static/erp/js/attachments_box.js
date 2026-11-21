/* A record's files box — components/attachments_box.html, one script for
   every box (erp.attachments).

     var box = NejumFiles.box(element);
     box.add(fileList);          // upload now, or hold until the record exists
     box.uploadTo(recordId);     // send what was held; always resolves

   With a record (data-url set) files go up as they are picked or dropped.
   Without one they wait in the box, and the page's save hands them over
   with uploadTo once the record is saved. The server answers each upload
   and delete with the list's HTML, swapped in whole. */
(function () {
  if (window.NejumFiles) return;

  function esc(s) {
    var d = document.createElement('div'); d.textContent = s; return d.innerHTML;
  }

  function box(el) {
    var list = el.querySelector('.nf-list');
    var status = el.querySelector('.nf-status');
    var zone = el.querySelector('.nf-add');
    var T = {
      uploading: el.dataset.tUploading, failed: el.dataset.tFailed, sure: el.dataset.tSure,
      waiting: el.dataset.tWaiting, remove: el.dataset.tRemove,
    };
    var headers = { 'X-CSRFToken': el.dataset.csrf, 'X-Requested-With': 'XMLHttpRequest' };
    var url = el.dataset.url;
    var pending = [];

    function say(text, isErr) {
      status.textContent = text || '';
      status.classList.toggle('err', !!isErr);
    }
    function showPending() {
      list.innerHTML = pending.map(function (f, i) {
        return '<div class="nf-doc waiting"><span class="nf-doc-ico"><i class="fa fa-file"></i></span>' +
          '<span class="nf-doc-body"><span class="nf-doc-name">' + esc(f.name) + '</span>' +
          '<span class="nf-doc-meta">' + esc(T.waiting) + '</span></span>' +
          '<button type="button" class="nf-doc-del" title="' + esc(T.remove) + '" data-unqueue="' + i + '">' +
          '<i class="fa fa-times"></i></button></div>';
      }).join('');
    }
    function answer(r) {
      return r.json().then(function (d) {
        if (d && d.html !== undefined) list.innerHTML = d.html;
        var errors = (d && d.errors) || [];
        say(errors.join('\n'), errors.length > 0);
        return d;
      });
    }
    function send(files) {
      var body = new FormData();
      files.forEach(function (f) { body.append('files', f); });
      say(T.uploading);
      return fetch(url, { method: 'POST', body: body, headers: headers }).then(answer);
    }
    function add(fileList) {
      var files = Array.prototype.slice.call(fileList || []);
      if (!files.length) return;
      if (url) {
        send(files).catch(function () { say(T.failed, true); });
        return;
      }
      pending.push.apply(pending, files);
      window.npDirty = true;
      showPending();
    }

    el.querySelectorAll('[data-pick]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        el.querySelector('[data-input="' + btn.dataset.pick + '"]').click();
      });
    });
    el.querySelectorAll('[data-input]').forEach(function (input) {
      input.addEventListener('change', function () { add(input.files); input.value = ''; });
    });
    zone.addEventListener('dragover', function (e) { e.preventDefault(); zone.classList.add('over'); });
    zone.addEventListener('dragleave', function () { zone.classList.remove('over'); });
    zone.addEventListener('drop', function (e) {
      e.preventDefault(); zone.classList.remove('over');
      if (e.dataTransfer && e.dataTransfer.files.length) add(e.dataTransfer.files);
    });
    list.addEventListener('click', function (e) {
      var held = e.target.closest('[data-unqueue]');
      if (held) { pending.splice(+held.dataset.unqueue, 1); showPending(); return; }
      var del = e.target.closest('[data-delete-url]');
      if (!del || !confirm(T.sure.replace('{name}', del.dataset.name))) return;
      del.disabled = true;
      fetch(del.dataset.deleteUrl, { method: 'POST', headers: headers })
        .then(answer).catch(function () { del.disabled = false; say(T.failed, true); });
    });

    return {
      add: add,
      // The files picked before the record existed, sent to it now. Always
      // resolves, with the errors (if any) for the page to report: the
      // record is saved either way.
      uploadTo: function (recordId) {
        if (!pending.length) return Promise.resolve({ errors: [] });
        if (!recordId) return Promise.resolve({ errors: [T.failed] });
        url = el.dataset.urlTpl.replace('/0/', '/' + recordId + '/');
        return send(pending.splice(0)).then(function (d) {
          return { errors: (d && d.errors) || [] };
        }).catch(function () { return { errors: [T.failed] }; });
      },
    };
  }

  window.NejumFiles = { box: box };
})();
