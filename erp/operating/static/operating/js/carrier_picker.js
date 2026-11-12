// The carrier combobox (operating/partials/_carrier_picker.html), on the
// order page and the Ship part page. Filtering ignores case and Turkish
// accents, so "yurtici" finds "Yurtiçi Kargo" and "IS" doesn't miss an "iş".
(function () {
  const fold = (t) => (t || '').toLocaleLowerCase('tr').replace(/\u0131/g, 'i')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '');

  // Wires one .od-cbx; returns what a page needs to keep it in step with
  // a background save or a cancelled edit.
  function attach(root) {
    const sel = document.getElementById(root.dataset.select);
    if (!sel) return null;
    const box = root.querySelector('.od-cbx-box');
    const input = box.querySelector('input');
    const list = box.querySelector('.od-cbx-list');
    const chip = root.querySelector('.od-cbx-chip');
    const ADD_LABEL = root.dataset.addLabel || 'Add';
    const optId = (i) => list.id + '-opt-' + i;
    const options = Array.from(sel.options).filter(o => o.value)
      .map(o => ({ value: o.value, label: o.text, key: fold(o.text + ' ' + o.value) }));
    let shown = [], active = -1;

    function render() {
      const typed = input.value.trim().replace(/\s+/g, ' ');
      const q = fold(typed);
      shown = options.filter(o => !q || o.key.includes(q));
      // A carrier that isn't on the list: offer to add it. It posts as the
      // typed name, and the server adds it to the list on save (or reuses
      // one whose name only differs in case or accents).
      if (q && !options.some(o => fold(o.label) === q)) {
        shown.push({ value: typed, label: typed, isNew: true });
      }
      active = shown.length ? 0 : -1;
      list.innerHTML = '';
      if (!shown.length) { close(); return; }
      shown.forEach((o, i) => {
        const li = document.createElement('li');
        li.id = optId(i);
        li.setAttribute('role', 'option');
        if (o.isNew) {
          li.className = 'add';
          li.innerHTML = '<i class="fa fa-plus"></i>';
          li.appendChild(document.createTextNode(ADD_LABEL + ' \u201c' + o.label + '\u201d'));
        } else {
          li.innerHTML = '<i class="fa fa-truck"></i>';
          li.appendChild(document.createTextNode(o.label));
        }
        // mousedown, not click: it lands before the input's blur closes the list.
        li.addEventListener('mousedown', (e) => { e.preventDefault(); pick(o); });
        list.appendChild(li);
      });
      highlight();
      list.hidden = false;
      input.setAttribute('aria-expanded', 'true');
    }
    function highlight() {
      list.querySelectorAll('li[role="option"]').forEach((li, i) => {
        li.classList.toggle('active', i === active);
        li.setAttribute('aria-selected', i === active ? 'true' : 'false');
      });
      const cur = document.getElementById(optId(active));
      if (cur) { cur.scrollIntoView({ block: 'nearest' }); input.setAttribute('aria-activedescendant', cur.id); }
      else input.removeAttribute('aria-activedescendant');
    }
    function close() {
      list.hidden = true;
      input.setAttribute('aria-expanded', 'false');
    }
    function pick(o) {
      if (o.isNew && !Array.from(sel.options).some(opt => opt.value === o.value)) {
        const added = new Option(o.label, o.value);
        added.dataset.added = '1';
        sel.add(added);
      }
      sel.value = o.value;
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      chip.querySelector('span').textContent = o.label;
      chip.hidden = false; box.hidden = true;
      input.value = ''; close();
    }

    chip.querySelector('.od-cbx-clear').addEventListener('click', () => {
      sel.value = '';
      sel.dispatchEvent(new Event('change', { bubbles: true }));
      chip.hidden = true; box.hidden = false;
      input.focus();
    });
    input.addEventListener('focus', render);
    input.addEventListener('input', render);
    // Leaving the box with a name typed but not picked keeps it — the
    // carrier it names, or a new one as "Add" would — instead of letting
    // it look chosen while the form posts no carrier. Picking from the
    // list never blurs (mousedown is cancelled), so this only catches
    // a name typed and then walked away from, e.g. to a submit button.
    input.addEventListener('blur', () => {
      const typed = input.value.trim().replace(/\s+/g, ' ');
      if (typed) {
        const q = fold(typed);
        pick(options.find(o => fold(o.label) === q || fold(o.value) === q)
             || { value: typed, label: typed, isNew: true });
      } else {
        close();
      }
    });
    input.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        if (list.hidden) return render();
        if (!shown.length) return;
        active = (active + (e.key === 'ArrowDown' ? 1 : -1) + shown.length) % shown.length;
        highlight();
      } else if (e.key === 'Enter') {
        // Never submit the form from here — Enter picks.
        e.preventDefault();
        if (!list.hidden && shown[active]) pick(shown[active]);
      } else if (e.key === 'Escape') {
        if (!list.hidden) { e.stopPropagation(); close(); }
      }
    });

    return {
      // A background save: the carrier it stored (a typed name may have
      // matched one already on the list) is now the saved one.
      saved(carrier, label) {
        sel.querySelectorAll('option[data-added]').forEach(opt => opt.remove());
        if (carrier && !Array.from(sel.options).some(opt => opt.value === carrier)) {
          sel.add(new Option(label, carrier));
          options.push({ value: carrier, label, key: fold(label + ' ' + carrier) });
        }
        Array.from(sel.options).forEach(opt => { opt.defaultSelected = !!carrier && opt.value === carrier; });
      },
      // Back to the carrier the order was saved with.
      reset() {
        sel.querySelectorAll('option[data-added]').forEach(opt => opt.remove());
        const saved = Array.from(sel.options).find(opt => opt.defaultSelected && opt.value);
        sel.value = saved ? saved.value : '';
        chip.querySelector('span').textContent = saved ? saved.text : '';
        chip.hidden = !saved; box.hidden = !!saved;
        input.value = ''; close();
      },
    };
  }

  window.NjCarrierPicker = { attach };
})();
