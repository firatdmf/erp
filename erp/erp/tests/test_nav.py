# to run this test, use the command:
# python manage.py test erp.test_nav

import re

from django.contrib.auth.models import AnonymousUser
from django.template.loader import render_to_string
from django.test import RequestFactory, TestCase

from erp.nav import MOBILE_FIRST, NAV_SECTIONS, mobile_sections

# Surfaces the drawer owns that the desktop sidebar has no equivalent
# for: Settings/Sign out live in the desktop TOP BAR, and the favourites
# sheet mirrors the top bar's favourites dropdown. Both are documented
# in _mobile_shell.html.
MOBILE_ONLY_LABELS = {"Settings", "Sign Out"}

DESKTOP_ITEM = re.compile(
    r'<a class="nj-fly-item"\s*(?:href="([^"]*)")?\s*(?:onclick="([^"]*)")?[^>]*>'
    r'.*?<span class="nj-fi-label">(.*?)</span>', re.S)
DESKTOP_LINK = re.compile(
    r'<a class="nj-nav-item[^"]*" href="([^"]*)">\s*<i data-lucide="[^"]*"></i>'
    r'\s*<span class="nj-label">(.*?)</span>', re.S)
MOBILE_ITEM = re.compile(
    r'<a class="m-drawer-item"\s*(?:href="([^"]*)")?\s*(?:onclick="([^"]*)")?[^>]*>'
    r'.*?<span class="m-drawer-label">(.*?)</span>', re.S)


def _entry(href, onclick, label):
    """(label, href, js-function) — the identity of a menu entry,
    independent of which menu rendered it."""
    fn = (onclick or "").replace("mobileToggleDrawer(); ", "").split("(")[0]
    return (re.sub(r"\s+", " ", label).strip(),
            "" if href in ("#", None) else href,
            fn)


class NavDefinitionTest(TestCase):
    def test_every_item_points_somewhere(self):
        for section in NAV_SECTIONS:
            for group in section.get("groups", []):
                for item in group["items"]:
                    ways = [k for k in ("url", "href", "action") if item.get(k)]
                    self.assertEqual(
                        len(ways), 1,
                        f"{item['label']!r} needs exactly one of url/href/action, got {ways}")
            if not section.get("groups"):
                self.assertTrue(section.get("url"), f"{section['key']!r} has neither groups nor url")

    def test_mobile_arrangement_keeps_every_item(self):
        def items(sections):
            return sorted(
                str(i["label"])
                for s in sections
                for g in s.get("groups", [])
                for i in g["items"]
            ) + sorted(str(s["label"]) for s in sections if not s.get("groups"))

        # The drawer folds the link-only sections into "Workspace", so
        # compare the flattened label multiset, not the shape.
        desktop = sorted(items(NAV_SECTIONS))
        mobile = sorted(items(mobile_sections()))
        self.assertEqual(desktop, mobile)

    def test_daily_flow_sections_come_first_on_mobile(self):
        # Checked against MOBILE_FIRST rather than a hardcoded pair. Sections
        # keep absorbing each other — current account went into accounting, procurement
        # into operating — and a literal list here goes stale silently every
        # time one does, which is how this test came to expect a "current account"
        # section that no longer existed.
        for key in MOBILE_FIRST:
            section = next((s for s in NAV_SECTIONS if s["key"] == key), None)
            self.assertIsNotNone(section, f"MOBILE_FIRST names {key!r}, which is not a section")
            self.assertTrue(section.get("groups"), f"{key!r} has no groups, so the drawer cannot lead with it")
        self.assertEqual(
            [s["key"] for s in mobile_sections()][:len(MOBILE_FIRST)],
            list(MOBILE_FIRST),
        )


class RenderedMenusMatchTest(TestCase):
    """The point of erp/nav.py: what a phone shows and what a desktop
    shows are the same menu in different clothes."""

    def setUp(self):
        request = RequestFactory().get("/")
        request.user = AnonymousUser()
        self.desktop_html = render_to_string(
            "components/_sidebar_nejum.html", {}, request=request)
        self.mobile_html = render_to_string(
            "components/_mobile_shell.html", {}, request=request)

    def desktop_entries(self):
        return {_entry(h, o, l) for h, o, l in DESKTOP_ITEM.findall(self.desktop_html)} | \
               {_entry(h, None, l) for h, l in DESKTOP_LINK.findall(self.desktop_html)}

    def mobile_entries(self):
        body = self.mobile_html.split('id="mobileDrawerBody"', 1)[1]
        entries = {_entry(h, o, l) for h, o, l in MOBILE_ITEM.findall(body)}
        return {e for e in entries if e[0] not in MOBILE_ONLY_LABELS
                and "toggleFavorites" not in e[2]}

    def test_no_desktop_item_is_missing_from_mobile(self):
        missing = self.desktop_entries() - self.mobile_entries()
        self.assertEqual(missing, set(),
                         f"in the sidebar but not the drawer: {sorted(missing)}")

    def test_no_mobile_item_is_missing_from_desktop(self):
        extra = self.mobile_entries() - self.desktop_entries()
        self.assertEqual(extra, set(),
                         f"in the drawer but not the sidebar: {sorted(extra)}")

    def test_creating_a_task_is_reachable_from_both(self):
        # The gap that started all this.
        task = ("Task", "", "openTaskSidebar")
        self.assertIn(task, self.desktop_entries())
        self.assertIn(task, self.mobile_entries())
