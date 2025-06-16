import sys
from django.core.management.base import BaseCommand

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "erp.settings")
django.setup()

from marketing.models import ProductFile

# MEDIA_ROOT = "/absolute/path/to/your/project/media/"
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
print("your media root is", MEDIA_ROOT)
# sys.exit()
from collections import defaultdict


class Command(BaseCommand):
    help = "Populate file_path fields for ProductFile objects"

    def handle(self, *args, **options):

        # Group ProductFiles by (product_id, product_variant_id)
        file_groups = defaultdict(list)
        for pf in ProductFile.objects.all():
            key = (pf.product_id, pf.product_variant_id)
            file_groups[key].append(pf)

        for (product_id, variant_id), product_files in file_groups.items():
            try:
                # Get product and variant SKUs
                product = product_files[0].product
                product_sku = product.sku
                variant_sku = None
                if variant_id:
                    variant_sku = product_files[0].product_variant.variant_sku

                # Build pattern
                if variant_sku:
                    pattern = f"productSKU_{product_sku}_variantSKU_{variant_sku}"
                else:
                    pattern = f"productSKU_{product_sku}_"

                folder = os.path.join(
                    MEDIA_ROOT, "product_files", product_sku, "images"
                )
                if not os.path.exists(folder):
                    print(f"⚠️ Folder does not exist: {folder}")
                    continue

                # Get all files matching the pattern, sorted for consistency
                files = sorted([f for f in os.listdir(folder) if pattern in f])

                for pf, fname in zip(sorted(product_files, key=lambda x: x.id), files):
                    full_path = os.path.join(folder, fname)
                    pf.file_path = full_path
                    pf.save(update_fields=["file_path"])
                    print(f"✅ Matched {fname} to ProductFile ID {pf.id}")

            except Exception as e:
                print(f"⚠️ Skipped group {product_id}, {variant_id} due to error: {e}")

        # for pf in ProductFile.objects.all():
        #     try:
        #         product_sku = pf.product.sku
        #         variant_sku = pf.product_variant.variant_sku if pf.product_variant else None

        #         if variant_sku:
        #             pattern = f"productSKU_{product_sku}_variantSKU_{variant_sku}"
        #         else:
        #             pattern = f"productSKU_{product_sku}_"

        #         folder = os.path.join(MEDIA_ROOT, "product_files", product_sku, "images")

        #         for fname in os.listdir(folder):
        #             if pattern in fname:
        #                 full_path = os.path.join(folder, fname)
        #                 pf.file_path = full_path  # <-- we're setting this now
        #                 #  it is not strictly necessary to use update_fields=["file_path"] in this context, but it is a good practice if you are only updating a single field.
        #                 # This can make the update slightly more efficient and avoids accidentally overwriting other fields that may have changed in memory but not intended for saving.
        #                 pf.save(update_fields=["file_path"])
        #                 print(f"✅ Matched and saved for ProductFile ID {pf.id}")
        #                 break
        #     except Exception as e:
        #         print(f"⚠️ Skipped ID {pf.id} due to error: {e}")
