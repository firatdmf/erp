// The CRM record pages — contact, company and supplier detail — share
// this one script (and crm/css/record_detail.css). Everything a page
// needs from the server arrives in window.RECORD_DETAIL, written by
// crm/components/_record_detail_scripts.html: the record, its URLs and
// the translated strings. Functions are global on purpose: the markup,
// and the history component the server re-renders, call them from
// inline handlers.

const RD = window.RECORD_DETAIL;

// Store original HTML for cancel
const taskOriginalHTML = {};
const noteOriginalHTML = {};

// Re-read parts of this page from the server and swap them in place.
// For lists whose rows the server renders — buttons, pills and all —
// and which are changed by a request that answers in JSON.
function refreshFromPage(ids) {
  return fetch(window.location.href, {headers: {'X-Requested-With': 'XMLHttpRequest'}})
    .then(response => response.text())
    .then(html => {
      const page = new DOMParser().parseFromString(html, 'text/html');
      ids.forEach(id => {
        const fresh = page.getElementById(id);
        const current = document.getElementById(id);
        if (fresh && current) current.innerHTML = fresh.innerHTML;
      });
      syncAttachedCounts();
    });
}

// Inline task editing
function editTask(taskId, name, description, dueDate) {
  const contentDiv = document.getElementById(`task-content-${taskId}`);

  taskOriginalHTML[taskId] = contentDiv.innerHTML;

  contentDiv.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:10px;width:100%;">
      <div>
        <label style="display:block;font:600 11.5px var(--font-sans);color:var(--gray-700);margin-bottom:5px;">${RD.i18n.taskName}</label>
        <input type="text" id="edit-task-name-${taskId}" style="width:100%;box-sizing:border-box;padding:9px 12px;border:1px solid var(--nejum-teal-500);border-radius:8px;font:600 13px var(--font-sans);outline:none;box-shadow:0 0 0 3px rgba(20,127,116,0.12);" />
      </div>
      <div>
        <label style="display:block;font:600 11.5px var(--font-sans);color:var(--gray-700);margin-bottom:5px;">${RD.i18n.descriptionOptional}</label>
        <textarea id="edit-task-desc-${taskId}" style="width:100%;box-sizing:border-box;min-height:70px;padding:9px 12px;border:1px solid #E0E6EE;border-radius:8px;font:500 12.5px var(--font-sans);outline:none;resize:vertical;">${description || ''}</textarea>
      </div>
      <div>
        <label style="display:block;font:600 11.5px var(--font-sans);color:var(--gray-700);margin-bottom:5px;">${RD.i18n.dueDate}</label>
        <input type="date" id="edit-task-date-${taskId}" value="${dueDate}" style="padding:9px 12px;border:1px solid #E0E6EE;border-radius:8px;font:500 13px var(--font-sans);outline:none;" />
      </div>
      <div style="display:flex;gap:8px;">
        <button type="button" onclick="saveTask(${taskId})" class="ord-btn primary" style="padding:7px 13px;font-size:12.5px;">
          <i class="fa fa-check"></i> ${RD.i18n.save}
        </button>
        <button type="button" onclick="cancelTaskEdit(${taskId})" class="ord-btn ghost" style="padding:7px 13px;font-size:12.5px;">
          <i class="fa fa-times"></i> ${RD.i18n.cancel}
        </button>
      </div>
    </div>
  `;

  const nameInput = document.getElementById(`edit-task-name-${taskId}`);
  nameInput.value = name;
  nameInput.focus();
  nameInput.setSelectionRange(nameInput.value.length, nameInput.value.length);
}

function cancelTaskEdit(taskId) {
  if (taskOriginalHTML[taskId]) {
    document.getElementById(`task-content-${taskId}`).innerHTML = taskOriginalHTML[taskId];
    delete taskOriginalHTML[taskId];
  }
}

function saveTask(taskId) {
  const name = document.getElementById(`edit-task-name-${taskId}`).value;
  const description = document.getElementById(`edit-task-desc-${taskId}`).value;
  const dueDate = document.getElementById(`edit-task-date-${taskId}`).value;

  if (!name.trim()) {
    alert(RD.i18n.taskNameEmpty);
    return;
  }

  if (!dueDate) {
    alert(RD.i18n.dueDateRequired);
    return;
  }

  fetch(`/todo/tasks/${taskId}/update_ajax/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': RD.csrf,
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: `name=${encodeURIComponent(name)}&description=${encodeURIComponent(description)}&due_date=${dueDate}`
  }).then(response => response.json())
    .then(data => {
      if (data.success && data.task) {
        document.getElementById(`task-content-${taskId}`).innerHTML = `
          <div class="od-task-body">
            <h3 class="od-task-name task-name">${data.task.name}</h3>
            ${data.task.description ? `<p class="od-task-desc task-description">${data.task.description}</p>` : ''}
            <div class="od-task-meta task-meta">
              <span class="pill due task-due"><i class="fa fa-calendar"></i>${data.task.due_date}</span>
              ${data.task.overdue_badge || ''}
            </div>
          </div>
        `;
      } else {
        alert(RD.i18n.failedSaveTask + ': ' + (data.error || 'Unknown error'));
      }
    }).catch(err => {
      alert(RD.i18n.failedSaveTask);
      console.error(err);
    });
}

// Inline note editing
function editNote(noteId, currentContent) {
  const contentDiv = document.getElementById(`note-content-${noteId}`);

  // The onclick attribute that invoked us was rendered server-side
  // and never updates after a save, so it carries the original
  // content. Prefer the live DOM text — that always reflects the
  // most recent saveNote() result.
  const liveTextEl = contentDiv.querySelector('.note-text');
  if (liveTextEl) {
    currentContent = liveTextEl.textContent;
  }

  noteOriginalHTML[noteId] = contentDiv.innerHTML;

  contentDiv.innerHTML = `
    <div class="note-meta">
      <span class="note-date" style="color:var(--gray-500);font:500 11.5px var(--font-sans);margin-bottom:8px;display:block;">${RD.i18n.editing}</span>
    </div>
    <textarea id="edit-textarea-${noteId}" style="width:100%;box-sizing:border-box;min-height:90px;padding:9px 12px;border:1px solid var(--nejum-teal-500);border-radius:8px;font:500 13px var(--font-sans);outline:none;resize:vertical;box-shadow:0 0 0 3px rgba(20,127,116,0.12);">${currentContent}</textarea>
    <div style="display:flex;gap:8px;margin-top:10px;">
      <button type="button" onclick="saveNote(${noteId})" class="ord-btn primary" style="padding:7px 13px;font-size:12.5px;">
        <i class="fa fa-check"></i> ${RD.i18n.save}
      </button>
      <button type="button" onclick="cancelEdit(${noteId})" class="ord-btn ghost" style="padding:7px 13px;font-size:12.5px;">
        <i class="fa fa-times"></i> ${RD.i18n.cancel}
      </button>
    </div>
  `;

  document.getElementById(`edit-textarea-${noteId}`).focus();
}

function cancelEdit(noteId) {
  if (noteOriginalHTML[noteId]) {
    document.getElementById(`note-content-${noteId}`).innerHTML = noteOriginalHTML[noteId];
    delete noteOriginalHTML[noteId];
  }
}

function saveNote(noteId) {
  const newContent = document.getElementById(`edit-textarea-${noteId}`).value;

  if (!newContent.trim()) {
    alert(RD.i18n.noteEmpty);
    return;
  }

  fetch(`/crm/notes/${noteId}/update_ajax/`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
      'X-CSRFToken': RD.csrf,
      'X-Requested-With': 'XMLHttpRequest'
    },
    body: `content=${encodeURIComponent(newContent)}`
  }).then(response => response.json())
    .then(data => {
      if (data.success) {
        document.getElementById(`note-content-${noteId}`).innerHTML = `
          <div class="note-meta">
            <span class="note-date" style="color:var(--gray-500);font:500 11.5px var(--font-sans);margin-bottom:6px;display:block;">${data.date}</span>
          </div>
          <p class="note-text" style="margin:0;font:500 13px var(--font-sans);color:var(--ink);line-height:1.55;word-break:break-word;">${data.content}</p>
        `;
      } else {
        alert(RD.i18n.failedSaveNote);
      }
    });
}

// Always-open note composer in the History section
function syncNoteComposer(el) {
  document.getElementById('noteComposerSubmit').disabled = !el.value.trim();
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 320) + 'px';
}

function noteComposerSaved() {
  const input = document.getElementById('noteComposerInput');
  input.value = '';
  input.style.height = '';
  document.getElementById('noteComposerSubmit').disabled = true;
  htmx.ajax('GET', RD.urls.notesPartial, {target: '#notesSection', swap: 'outerHTML'});
  input.focus();
}

// Attached items: "Attach an item" dropdown
function toggleAttachMenu(event) {
  event.stopPropagation();
  const menu = document.getElementById('attachMenu');
  menu.hidden = !menu.hidden;
}

// The panels that open inside the Attached items card, by menu item.
const ATTACH_PANELS = {
  task: 'attachTaskSection',
  contact: 'attachContactSection'
};

function openAttachSection(type) {
  document.getElementById('attachMenu').hidden = true;
  if (type === 'file') {
    // The Files group starts collapsed, so open it first — otherwise the
    // file the user is about to pick would arrive somewhere they cannot
    // see, and only the count beside the header would move.
    expandAttachGroup('attachmentsList');
    document.getElementById('attachFileInput').click();
    return;
  }
  if (type === 'task' && RD.taskAttach) {
    // A task goes through the same sidebar form as everywhere else, with
    // this record already picked under "Attach to".
    openTaskSidebar();
    setTaskAttachment(RD.taskAttach.type, RD.pk, RD.taskAttach.name);
    return;
  }
  const section = document.getElementById(ATTACH_PANELS[type]);
  if (section) {
    section.style.display = 'block';
    section.scrollIntoView({behavior: 'smooth', block: 'nearest'});
    const first = section.querySelector('input[type="text"], textarea');
    if (first) first.focus();
  }
}

function toggleAttachSection(type) {
  const section = document.getElementById(ATTACH_PANELS[type]);

  // Hide all sections first
  Object.values(ATTACH_PANELS).forEach(id => {
    const el = document.getElementById(id);
    if (el && el !== section) {
      el.style.display = 'none';
    }
  });

  // Toggle current section
  if (section) {
    section.style.display = section.style.display === 'none' ? 'block' : 'none';
  }
}

// The sidebar saves over fetch() and leaves the page as it was, so the
// list is re-read from the server: it renders each row's buttons and
// overdue pill, and drops a task that was assigned to someone else.
document.addEventListener('task:created', function () {
  refreshFromPage(['tasksList']).then(() => expandAttachGroup('tasksList'));
});

// Dropped files are handed to the hidden input, so the upload goes out
// through the same HTMX form as a click-to-choose upload.
function dropAttachments(event, form) {
  event.preventDefault();
  form.classList.remove('over');
  const input = document.getElementById('attachFileInput');
  input.files = event.dataTransfer.files;
  if (input.files.length) input.dispatchEvent(new Event('change', {bubbles: true}));
}

// A file the server refused (too large) comes back as an HX-Trigger on
// the swapped list, since a Django message would only surface later.
document.body.addEventListener('attachmentError', function (e) {
  alert(e.detail.value);
});

function deleteAttachment(id) {
  const row = document.getElementById(`attachment-${id}`);
  fetch(`/crm/attachments/${id}/delete/`, {
    method: 'POST',
    headers: {'X-CSRFToken': RD.csrf, 'X-Requested-With': 'XMLHttpRequest'}
  }).then(res => {
    if (!res.ok || !row) return;
    row.style.transition = 'all 0.25s ease';
    row.style.opacity = '0';
    row.style.transform = 'translateX(-16px)';
    setTimeout(() => { row.remove(); syncAttachedCounts(); }, 250);
  });
}

document.addEventListener('click', function (e) {
  const menu = document.getElementById('attachMenu');
  if (menu && !menu.hidden && !e.target.closest('.od-attach-menu')) {
    menu.hidden = true;
  }
});

// Attached items: collapsible groups
function toggleAttachGroup(head) {
  const group = head.closest('.od-attach-group');
  const collapsed = group.classList.toggle('collapsed');
  head.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
}

// Open the group a given list belongs to, if it is closed.
function expandAttachGroup(id) {
  const el = document.getElementById(id);
  const group = el && el.closest('.od-attach-group');
  if (!group || !group.classList.contains('collapsed')) return;
  group.classList.remove('collapsed');
  const head = group.querySelector('.od-group-head');
  if (head) head.setAttribute('aria-expanded', 'true');
}

// The lists are re-read after a save and pruned by the delete/complete
// handlers, so each group count has to be recomputed from the DOM.
function syncAttachedCounts() {
  const counts = {
    grpTaskCount: '#tasksList .od-task',
    grpFileCount: '#attachmentsList .od-file',
    grpContactCount: '#contactsList .od-contact-row'
  };
  Object.keys(counts).forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = '(' + document.querySelectorAll(counts[id]).length + ')';
  });
}

// The page's own confirm dialog. `opts`: question, detail, actionText,
// icon, primary (a safe action rather than a destructive one).
// `onConfirm` receives the overlay, to remove once its request is done.
function showConfirmDialog(opts, onConfirm) {
  const iconBg = opts.primary ? '#D1FAE5' : '#FEE2E2';
  const iconColor = opts.primary ? '#0E6E4A' : '#B23B3B';

  const overlay = document.createElement('div');
  overlay.style.cssText = 'position:fixed;inset:0;background:rgba(15,23,31,0.45);display:flex;align-items:center;justify-content:center;z-index:10000;animation:fadeIn 0.15s;font-family:var(--font-sans);';

  const dialog = document.createElement('div');
  dialog.style.cssText = 'background:#fff;border:1px solid #E2E8EE;border-radius:14px;max-width:420px;width:90%;padding:22px;box-shadow:0 20px 60px rgba(15,23,31,0.20);animation:slideIn 0.2s;';
  dialog.innerHTML = `
    <div style="display:flex;gap:12px;align-items:flex-start;margin-bottom:18px;">
      <div style="width:40px;height:40px;border-radius:50%;background:${iconBg};display:flex;align-items:center;justify-content:center;color:${iconColor};flex-shrink:0;">
        <i class="fa ${opts.icon}"></i>
      </div>
      <div>
        <div class="rd-confirm-q" style="font:700 15px var(--font-sans);color:#0F1419;margin-bottom:4px;"></div>
        <div class="rd-confirm-d" style="font:500 12.5px var(--font-sans);color:var(--gray-500);"></div>
      </div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;">
      <button id="cancelBtn" class="ord-btn ghost"></button>
      <button id="confirmBtn" class="ord-btn ${opts.primary ? 'primary' : ''}" style="${opts.primary ? '' : 'background:#EF4444;border:1px solid #B91C1C;color:white;box-shadow:0 1px 2px rgba(15,23,31,0.10),inset 0 1px 0 rgba(255,255,255,0.18);'}"></button>
    </div>
  `;
  // textContent: the detail line can carry a record's name.
  dialog.querySelector('.rd-confirm-q').textContent = opts.question;
  dialog.querySelector('.rd-confirm-d').textContent = opts.detail;
  dialog.querySelector('#cancelBtn').textContent = RD.i18n.cancel;
  dialog.querySelector('#confirmBtn').textContent = opts.actionText;

  if (!document.getElementById('modal-animations')) {
    const style = document.createElement('style');
    style.id = 'modal-animations';
    style.textContent = `
      @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
      @keyframes slideIn { from { transform: translateY(-12px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
    `;
    document.head.appendChild(style);
  }

  overlay.appendChild(dialog);
  document.body.appendChild(overlay);

  dialog.querySelector('#cancelBtn').onclick = () => overlay.remove();
  dialog.querySelector('#confirmBtn').onclick = () => onConfirm(overlay);
}

// Fade a row out, drop it, then run `after`.
function removeRow(el, after) {
  if (!el) return;
  el.style.transition = 'all 0.3s ease';
  el.style.opacity = '0';
  el.style.transform = 'translateX(-20px)';
  setTimeout(() => { el.remove(); if (after) after(); }, 300);
}

// Confirm, then delete a note or delete/complete a task
function confirmDelete(action, id) {
  const completing = action === 'complete_task';

  showConfirmDialog({
    question: completing ? RD.i18n.markComplete : RD.i18n.areYouSure,
    detail: RD.i18n.cannotUndo,
    actionText: completing ? RD.i18n.complete : RD.i18n.delete,
    icon: completing ? 'fa-check' : 'fa-trash',
    primary: completing
  }, overlay => {
    let url = '';
    let body = '';

    if (action === 'delete_note') {
      url = `/crm/notes/${id}/delete_note/`;
      body = `note_id=${id}`;
    } else if (action === 'delete_task') {
      url = `/todo/tasks/${id}/delete_task`;
      body = `${RD.kind}_id=${RD.pk}`;
    } else if (action === 'complete_task') {
      url = `/todo/tasks/${id}/complete_task`;
      body = `task_id=${id}`;
    }

    fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-CSRFToken': RD.csrf,
        'X-Requested-With': 'XMLHttpRequest'
      },
      body
    }).then(response => {
      if (completing) {
        return response.json();
      }
      return { success: true };
    }).then(data => {
      overlay.remove();
      if (action === 'delete_note') {
        removeRow(document.getElementById(`note-${id}`));
      } else if (action === 'delete_task') {
        removeRow(document.getElementById(`task-${id}`), syncAttachedCounts);
      } else if (completing && data.success) {
        removeRow(document.getElementById(`task-${id}`), syncAttachedCounts);

        const notesList = document.querySelector('.notes-list');
        if (notesList && data.task) {
          const completedTaskHTML = `
            <div class="note-item completed-task-item" style="opacity:0;transform:translateY(-10px);transition:all 0.3s ease;">
              <div class="note-content">
                <div class="note-meta">
                  <span class="note-date">${data.task.completed_at}</span>
                  <span class="note-badge"><i class="fa fa-check-circle"></i> ${RD.i18n.completed}</span>
                </div>
                <p class="note-text"><strong>${data.task.name}</strong></p>
                ${data.task.description ? `<p class="note-description">${data.task.description}</p>` : ''}
              </div>
            </div>
          `;
          notesList.insertAdjacentHTML('afterbegin', completedTaskHTML);
          setTimeout(() => {
            const newItem = notesList.firstElementChild;
            if (newItem) {
              newItem.style.opacity = '1';
              newItem.style.transform = 'translateY(0)';
            }
          }, 10);
        }
      }
    }).catch(() => overlay.remove());
  });
}

// Tab Switching
function switchTab(tabId) {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.classList.remove('active');
    if (btn.onclick && btn.onclick.toString().includes(`'${tabId}'`)) {
      btn.classList.add('active');
    }
  });

  document.querySelectorAll('.tab-content').forEach(content => {
    content.classList.remove('active');
  });

  const activeContent = document.getElementById(`tab-${tabId}`);
  if (activeContent) {
    activeContent.classList.add('active');
  }
}

// Communication Tab Toggle
function switchCommTab(type) {
  const btns = document.querySelectorAll('.comm-toggle-btn');
  btns.forEach(btn => btn.classList.remove('active'));

  if (type === 'emails') {
    btns[0].classList.add('active');
    htmx.ajax('GET', RD.urls.emails, { target: '#comm-content' });
  } else {
    btns[1].classList.add('active');
    // Only a company keeps shared files with its mail so far.
    if (RD.urls.sharedFiles) {
      htmx.ajax('GET', RD.urls.sharedFiles, { target: '#comm-content' });
    } else {
      alert(RD.i18n.comingSoon);
    }
  }
}

// Open Compose Modal
function openComposeModal(toEmail, toName, subject, companyId, contactId) {
  let url = RD.urls.compose + '?';
  if (toEmail) url += `to=${encodeURIComponent(toEmail)}&`;
  if (toName) url += `name=${encodeURIComponent(toName)}&`;
  if (subject) url += `subject=${encodeURIComponent(subject)}&`;
  if (companyId) url += `company=${companyId}&`;
  if (contactId) url += `contact=${contactId}&`;

  fetch(url, {
    headers: { 'HX-Request': 'true' }
  })
    .then(res => res.text())
    .then(html => {
      document.getElementById('composeModalContainer').innerHTML = html;
    });
}

// View Email Detail
function viewEmailDetail(emailId) {
  openEmailDetailModal(emailId);
}

function openEmailDetailModal(emailId) {
  let container = document.getElementById('emailDetailModal');
  if (!container) {
    container = document.createElement('div');
    container.id = 'emailDetailModal';
    container.className = 'modal-backdrop';
    container.onclick = (e) => {
      if (e.target === container) closeEmailDetailModal();
    };
    document.body.appendChild(container);
  }

  container.style.display = 'flex';
  container.innerHTML = `<div style="margin:auto; background:white; padding:20px; border-radius:12px;font-family:var(--font-sans);"><i class="fa fa-spinner fa-spin"></i> ${RD.i18n.loading}</div>`;

  fetch(`/email/email/${emailId}/`, {
    headers: { 'HX-Request': 'true' }
  })
    .then(res => res.text())
    .then(html => {
      container.innerHTML = `
        <div class="compose-modal" style="position:relative; bottom:auto; right:auto; width:800px; height:80vh;">
          <div class="compose-header">
            <h3>${RD.i18n.emailDetail}</h3>
            <button class="close-btn" onclick="closeEmailDetailModal()"><i class="fa fa-times"></i></button>
          </div>
          <div style="flex:1; overflow:hidden; display:flex; flex-direction:column;">
              ${html}
          </div>
        </div>
      `;
    });
}

function closeEmailDetailModal() {
  const container = document.getElementById('emailDetailModal');
  if (container) {
    container.style.display = 'none';
    container.innerHTML = '';
  }
}

/* ─── Edit sidebar (contact, company) ────────────────────────
   Loads the edit form via AJAX into a slide-in panel, submits
   via fetch, and reloads the page on success. The form partial
   names its own handlers — submitEditContactForm(), and so on —
   so the three functions are published under the record's name.
   The supplier page keeps its own: its form shows field errors. */
(function () {
  const edit = RD.editSidebar;
  if (!edit) return;
  const name = edit.name;

  function open() {
    var overlay = document.getElementById(`edit${name}SidebarOverlay`);
    var body = document.getElementById(`edit${name}SidebarBody`);
    if (!overlay || !body) return;
    body.innerHTML = `<div style="padding:40px;text-align:center;color:var(--gray-500);"><i class="fa fa-spinner fa-spin fa-2x"></i><div style="margin-top:12px;">${RD.i18n.loadingForm}</div></div>`;
    overlay.classList.add('active');
    fetch(edit.url, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        body.innerHTML = html;
        // Run any <script> tags the partial brought in (browsers don't
        // execute scripts inserted via innerHTML automatically).
        body.querySelectorAll('script').forEach(function (s) {
          var n = document.createElement('script');
          if (s.src) n.src = s.src; else n.textContent = s.textContent;
          document.body.appendChild(n).parentNode.removeChild(n);
        });
      })
      .catch(function () {
        body.innerHTML = `<div style="padding:40px;color:#ef4444;text-align:center;">${RD.i18n.failedLoadForm}</div>`;
      });
  }

  function close() {
    var overlay = document.getElementById(`edit${name}SidebarOverlay`);
    if (overlay) overlay.classList.remove('active');
  }

  function submit(event) {
    event.preventDefault();
    var form = document.getElementById(`edit${name}Form`);
    var btn = document.getElementById(`edit${name}SubmitBtn`);
    var btnText = btn ? btn.querySelector('.btn-text') : null;
    var btnSpinner = btn ? btn.querySelector('.btn-spinner') : null;
    function idle() {
      if (btnText) btnText.style.display = 'inline';
      if (btnSpinner) btnSpinner.style.display = 'none';
      if (btn) btn.disabled = false;
    }
    if (btnText) btnText.style.display = 'none';
    if (btnSpinner) btnSpinner.style.display = 'inline-flex';
    if (btn) btn.disabled = true;
    fetch(form.action, {
      method: 'POST',
      body: new FormData(form),
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
      .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, body: d }; }); })
      .then(function (res) {
        if (res.ok && res.body.success) {
          window.location.href = res.body.redirect_url || window.location.pathname;
        } else {
          idle();
          alert(RD.i18n.failedSave + ' ' + JSON.stringify(res.body.errors || res.body));
        }
      })
      .catch(idle);
  }

  window[`openEdit${name}Sidebar`] = open;
  window[`closeEdit${name}Sidebar`] = close;
  window[`submitEdit${name}Form`] = submit;
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
  });
})();

// ── Pick rows, then print or export them ───────────────────────────
// Order history and Account history each tick their own rows and carry
// their own pair of buttons. One selector per card, never a shared one:
// both cards sit on the same page, and a single query would have Print
// selected on one card silently carrying the other card's ticks.
function pickedIds(selector) {
  return Array.from(document.querySelectorAll(selector + ':checked'))
              .map(function (cb) { return cb.value; });
}

function syncPickButtons(selector, prefix) {
  const btn = document.getElementById(`print${prefix}Btn`);
  if (!btn) return;
  const n = pickedIds(selector).length;
  btn.disabled = n === 0;
  const xls = document.getElementById(`excel${prefix}Btn`);
  if (xls) xls.disabled = n === 0;
  // Labels come off data- attributes rather than being written into
  // this script: they are translated per page render.
  document.getElementById(`print${prefix}Label`).textContent =
    n ? btn.dataset.labelPicked + ' (' + n + ')' : btn.dataset.labelIdle;
  // Excel exports the same selection, so it carries the same count.
  const xlsLabel = document.getElementById(`excel${prefix}Label`);
  if (xls && xlsLabel) {
    xlsLabel.textContent =
      n ? xls.dataset.labelPicked + ' (' + n + ')' : xls.dataset.labelIdle;
  }
}

// ── Combined order sheet ───────────────────────────────────────────
// Tick several of this client's orders and print them onto one page
// (operating:order_print_combined). It is a document and nothing else
// — no invoice, no ledger row — so the only state there is to keep is
// what happens to be ticked right now.
function syncPrintSelection() { syncPickButtons('.od-order-check', 'Orders'); }

function printSelectedOrders() {
  const ids = pickedIds('.od-order-check');
  if (!ids.length) return;
  window.open(RD.urls.orderPrint + '?ids=' + ids.join(','), '_blank');
}

// The same sheet as a spreadsheet. Navigates rather than opening a
// tab: the response is an attachment, so a new tab would open, take
// the download and sit there blank.
function excelSelectedOrders() {
  const ids = pickedIds('.od-order-check');
  if (!ids.length) return;
  window.location = RD.urls.orderExcel + '?ids=' + ids.join(',');
}

// ── Account history: pick, print, export ────────────────────────────
function syncAccountSelection() { syncPickButtons('.od-account-check', 'Accounts'); }

function printSelectedAccounts() {
  const ids = pickedIds('.od-account-check');
  if (!ids.length) return;
  window.open(RD.urls.statementPrint + '?ids=' + ids.join(','), '_blank');
}

function excelSelectedAccounts() {
  const ids = pickedIds('.od-account-check');
  if (!ids.length) return;
  window.location = RD.urls.statementExcel + '?ids=' + ids.join(',');
}
