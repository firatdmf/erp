// Cmd+Enter (Ctrl+Enter off macOS) submits the form being filled in.
//
// The form is the one holding the focused field. Otherwise — nothing focused,
// or focus in a field outside any form — it is the page's only visible form
// that posts — a page with two is ambiguous, so
// the shortcut does nothing there rather than guess.
//
// Forms that already handle the shortcut themselves (the order form, the CRM
// note composer) call preventDefault, and this handler steps aside for them,
// so nothing is submitted twice.
(function () {
  function visible(el) {
    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  }

  function submitterOf(form) {
    return Array.prototype.find.call(form.elements, function (el) {
      return (el.type === 'submit' || el.type === 'image') && visible(el);
    });
  }

  function targetForm(active) {
    var form = active && (active.form || (active.closest && active.closest('form')));
    if (form) return form;
    var candidates = Array.prototype.filter.call(document.forms, function (f) {
      return (f.method || '').toLowerCase() === 'post' && visible(f) && submitterOf(f);
    });
    return candidates.length === 1 ? candidates[0] : null;
  }

  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' || !(e.metaKey || e.ctrlKey)) return;
    if (e.shiftKey || e.altKey || e.isComposing || e.defaultPrevented) return;

    var form = targetForm(document.activeElement);
    if (!form) return;
    var submitter = submitterOf(form);
    // A disabled submit button means the form is not ready — respect it.
    if (submitter && submitter.disabled) return;

    e.preventDefault();
    if (typeof form.requestSubmit === 'function') {
      form.requestSubmit(submitter || undefined);
    } else {
      form.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
    }
  });
})();
