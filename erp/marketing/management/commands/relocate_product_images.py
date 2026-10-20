"""Move product photos into the folder their SKU and use call for, and
delete the files earlier moves retired once their wait is over.

Neither needs running by hand: the product page does both after a save,
and an hourly sweep set off by the storefront's calls catches the rest.
This is for when you'd rather not wait the hour:

    python manage.py relocate_product_images --product 157
    python manage.py relocate_product_images --all
    python manage.py relocate_product_images --delete-expired

See marketing/product_images.py.
"""
from django.core.management.base import BaseCommand, CommandError

from marketing import product_images


class Command(BaseCommand):
    help = "Move product photos to the folders their SKUs and use call for."

    def add_arguments(self, parser):
        parser.add_argument("--product", type=int, action="append", default=[],
                            help="A product id; may be given more than once.")
        parser.add_argument("--all", action="store_true",
                            help="Every product with a photo in the SKU-folder layout.")
        parser.add_argument("--delete-expired", action="store_true",
                            help="Delete retired files whose wait is over.")

    def handle(self, *args, **options):
        if not (options["product"] or options["all"] or options["delete_expired"]):
            raise CommandError("Name products with --product, or pass --all or --delete-expired.")

        if options["all"]:
            self.stdout.write(f"moved {product_images.sweep()}")
        for pid in sorted(set(options["product"])):
            self.stdout.write(f"product {pid}: moved {product_images.relocate(pid)}")
        if options["delete_expired"]:
            self.stdout.write(f"deleted {product_images.delete_expired()} retired file(s)")
