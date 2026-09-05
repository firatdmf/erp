"""Create the standard chart of accounts. Safe to run repeatedly.

Only ever ADDS. An account that already exists is left exactly as it is —
including its name, which someone may have translated or reworded, and
which a deploy has no business rewriting.

    python manage.py seed_chart_of_accounts          # report only
    python manage.py seed_chart_of_accounts --apply
"""
from django.core.management.base import BaseCommand

from accounting.models_ledger import ChartAccount
from accounting.services_ledger import STANDARD_CHART, ensure_chart


class Command(BaseCommand):
    help = "Create any missing standard chart-of-accounts rows."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply", action="store_true",
            help="Actually create them. Without this the command only reports.",
        )

    def handle(self, *args, **opts):
        existing = set(ChartAccount.objects.values_list("code", flat=True))
        missing = [row for row in STANDARD_CHART if row[0] not in existing]

        if not missing:
            self.stdout.write(self.style.SUCCESS(
                f"Chart is complete — all {len(STANDARD_CHART)} standard "
                f"accounts present."))
            return

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"{len(missing)} account(s) missing:"))
        for code, name, type_, is_control in missing:
            tag = " [control]" if is_control else ""
            self.stdout.write(f"    {code}  {name:<30} {type_}{tag}")

        if not opts["apply"]:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "Dry run — nothing created. Re-run with --apply."))
            return

        created = ensure_chart()
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Created {len(created)}: {', '.join(created)}"))
