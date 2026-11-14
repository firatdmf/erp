"""When a repeating task comes round again.

A task repeats every N weeks, months or years. The next one is due one
step after the task it follows, by the schedule rather than by the day it
was ticked: paid late on the 9th, the next monthly bill is still due on
the 1st. A monthly or yearly series remembers the day of the month it was
set for, so a task on the 31st falls on the 30th, or the 28th in
February, and goes back to the 31st in the months that have one.
"""
import calendar
import datetime

from django.utils.translation import ngettext

UNITS = ("week", "month", "year")


def next_due(due, unit, every, day=None):
    """The due date after `due` in a series repeating every `every` `unit`s,
    set for day `day` of the month."""
    every = max(int(every or 1), 1)
    if unit == "week":
        return due + datetime.timedelta(weeks=every)
    months = every * (12 if unit == "year" else 1)
    index = due.month - 1 + months
    year, month = due.year + index // 12, index % 12 + 1
    last = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(day or due.day, last))


def label(unit, every):
    """'Every month', 'Every 3 months' — empty when it does not repeat."""
    every = max(int(every or 1), 1)
    if unit == "week":
        return ngettext("Every week", "Every %(n)d weeks", every) % {"n": every}
    if unit == "month":
        return ngettext("Every month", "Every %(n)d months", every) % {"n": every}
    if unit == "year":
        return ngettext("Every year", "Every %(n)d years", every) % {"n": every}
    return ""


def from_form(data):
    """(unit, every) from a posted form's `repeat_unit` and `repeat_every`.
    Anything unreadable is no repeat, or every 1."""
    unit = (data.get("repeat_unit") or "").strip()
    if unit not in UNITS:
        return "", 1
    try:
        every = int(data.get("repeat_every") or 1)
    except (TypeError, ValueError):
        every = 1
    return unit, min(max(every, 1), 99)
