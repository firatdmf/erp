/* =================================================================
   Nejum sidebar — flyout interactions.
   - hover on a `[data-flyout]` nav-item   → adds .nj-open (auto closes
     after a short delay when the cursor leaves both item and panel)
   - click on the same item                → toggles .nj-pinned (sticks
     open until the user clicks outside or hits Esc)
   - clicking on a flyout link             → closes any pinned panel
     before the link navigates so the next page doesn't load with the
     panel half-open
   - flyout panels are `position: fixed`; we re-anchor them vertically
     to the originating nav item so the arrow always points back at it,
     while clamping inside the viewport.
   ================================================================= */
(function () {
  'use strict';
  if (window.__nejumSidebarInit) return;
  window.__nejumSidebarInit = true;

  const init = () => {
    const sidebar = document.getElementById('njSidebar');
    if (!sidebar) return;

    const items = Array.from(sidebar.querySelectorAll('.nj-nav-item[data-flyout]'));
    let openItem = null;       // currently hovered/visible
    let pinnedItem = null;     // sticky-open via click
    let closeTimer = null;

    // Refresh Lucide icons whenever they appear (initial + after hydrate)
    const refreshIcons = () => {
      if (window.lucide && window.lucide.createIcons) window.lucide.createIcons();
    };
    refreshIcons();
    // Late-arriving Lucide bundle (defer): re-run once it loads
    if (!window.lucide) window.addEventListener('load', refreshIcons, { once: true });

    const positionFlyout = (item) => {
      const panel = item.querySelector(':scope > .nj-flyout');
      const arrow = panel && panel.querySelector(':scope > .nj-fly-arrow');
      if (!panel) return;
      const rect = item.getBoundingClientRect();
      const sb = sidebar.getBoundingClientRect();
      const fh = panel.offsetHeight || 320;
      const margin = 12;
      const itemCenter = rect.top + rect.height / 2;
      let top = itemCenter - 38;
      top = Math.max(margin, Math.min(top, window.innerHeight - fh - margin));
      panel.style.top = top + 'px';
      panel.style.left = (sb.right + 6) + 'px';
      if (arrow) {
        const arrowTop = Math.max(14, Math.min(itemCenter - top - 6, fh - 26));
        arrow.style.top = arrowTop + 'px';
      }
    };

    const open = (item) => {
      if (openItem && openItem !== item) openItem.classList.remove('nj-open');
      openItem = item;
      item.classList.add('nj-open');
      // Wait one frame so the panel has its real height before we
      // compute placement.
      requestAnimationFrame(() => positionFlyout(item));
    };

    const closeNonPinned = () => {
      if (openItem && openItem !== pinnedItem) {
        openItem.classList.remove('nj-open');
        openItem = null;
      }
    };

    const scheduleClose = () => {
      clearTimeout(closeTimer);
      closeTimer = setTimeout(closeNonPinned, 160);
    };
    const cancelClose = () => clearTimeout(closeTimer);

    items.forEach((item) => {
      // Hover behaviour
      item.addEventListener('mouseenter', () => {
        cancelClose();
        if (!pinnedItem || pinnedItem === item) open(item);
      });
      item.addEventListener('mouseleave', scheduleClose);

      // Click toggles pin
      item.addEventListener('click', (e) => {
        // Clicks on actual links inside the flyout should pass through
        // (and close the panel). Pin-toggle only happens when the user
        // clicked the nav-item label/icon area, not the flyout body.
        if (e.target.closest('.nj-flyout')) {
          if (e.target.closest('.nj-fly-item')) {
            // Let the link navigate; tear down pin state.
            pinnedItem = null;
            item.classList.remove('nj-pinned');
            closeNonPinned();
          }
          return;
        }
        e.preventDefault();
        if (pinnedItem === item) {
          pinnedItem = null;
          item.classList.remove('nj-pinned');
          closeNonPinned();
        } else {
          if (pinnedItem) pinnedItem.classList.remove('nj-pinned');
          pinnedItem = item;
          item.classList.add('nj-pinned');
          open(item);
        }
      });

      // Keep panel alive while cursor is over it
      const panel = item.querySelector(':scope > .nj-flyout');
      if (panel) {
        panel.addEventListener('mouseenter', cancelClose);
        panel.addEventListener('mouseleave', scheduleClose);
      }
    });

    // Outside click → unpin
    document.addEventListener('mousedown', (e) => {
      if (!sidebar.contains(e.target)) {
        if (pinnedItem) {
          pinnedItem.classList.remove('nj-pinned');
          pinnedItem = null;
        }
        closeNonPinned();
      }
    });

    // Esc → unpin + close
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        if (pinnedItem) {
          pinnedItem.classList.remove('nj-pinned');
          pinnedItem = null;
        }
        closeNonPinned();
      }
    });

    // Reposition on resize / scroll (sidebar is sticky so scroll is
    // mostly a no-op; resize matters)
    window.addEventListener('resize', () => {
      if (openItem) positionFlyout(openItem);
    });
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
