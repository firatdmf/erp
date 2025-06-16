from django.core.management.base import BaseCommand
from marketing.models import ProductFile
from cloudinary.uploader import upload as cloudinary_upload
import os

class Command(BaseCommand):
    help = 'Upload product images to Cloudinary from local file paths.'

    def handle(self, *args, **kwargs):
        # for pf in ProductFile.objects.filter(file_url__isnull=True).exclude(file_path__isnull=True):
        for pf in ProductFile.objects.all().exclude(file_path__isnull=True):
            if os.path.exists(pf.file_path):
                try:
                    result = cloudinary_upload(pf.file_path)
                    pf.file_url = result.get("secure_url")
                    pf.save(update_fields=["file_url"])
                    self.stdout.write(self.style.SUCCESS(f"Uploaded ID {pf.id}"))
                except Exception as e:
                    self.stderr.write(f"❌ Upload failed for ID {pf.id}: {e}")
            else:
                self.stderr.write(f"❌ File does not exist for ID {pf.id}: {pf.file_path}")
