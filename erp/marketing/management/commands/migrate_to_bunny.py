"""
Django Management Command: Migrate Cloudinary Images to Bunny CDN

Usage:
    python manage.py migrate_to_bunny --dry-run    # Preview what will be migrated
    python manage.py migrate_to_bunny              # Actually migrate files
    python manage.py migrate_to_bunny --model=ProductFile  # Migrate specific model only
"""

from django.core.management.base import BaseCommand
from django.db import transaction
import requests
import time


class Command(BaseCommand):
    help = 'Migrate all Cloudinary images to Bunny CDN and update database URLs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Preview what would be migrated without making changes',
        )
        parser.add_argument(
            '--model',
            type=str,
            default='all',
            help='Specific model to migrate: ProductFile, ProductCategory, BlogPost, BlogFile, or all',
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Number of files to process in each batch',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        model_filter = options['model']
        batch_size = options['batch_size']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('=== DRY RUN MODE - No changes will be made ===\n'))
        
        # Import models
        from marketing.models import ProductFile, ProductCategory, BlogPost, BlogFile
        from marketing.utils.bunny_storage import upload_to_bunny, get_path_from_cloudinary_url
        from django.conf import settings
        
        # Check Bunny CDN config
        if not getattr(settings, 'BUNNY_CDN_URL', ''):
            self.stdout.write(self.style.ERROR('BUNNY_CDN_URL is not configured!'))
            return
        
        total_migrated = 0
        total_failed = 0
        total_skipped = 0
        
        models_to_migrate = []
        
        if model_filter == 'all' or model_filter == 'ProductFile':
            models_to_migrate.append(('ProductFile', ProductFile, 'file_url'))
        if model_filter == 'all' or model_filter == 'ProductCategory':
            models_to_migrate.append(('ProductCategory', ProductCategory, 'image_url'))
        if model_filter == 'all' or model_filter == 'BlogPost':
            models_to_migrate.append(('BlogPost (cover)', BlogPost, 'cover_image'))
            models_to_migrate.append(('BlogPost (hero)', BlogPost, 'hero_image'))
        if model_filter == 'all' or model_filter == 'BlogFile':
            models_to_migrate.append(('BlogFile', BlogFile, 'file_url'))
        
        for model_name, Model, field_name in models_to_migrate:
            self.stdout.write(f'\n--- Processing {model_name} ---')
            
            # Get all records with Cloudinary URLs
            filter_kwargs = {f'{field_name}__icontains': 'cloudinary.com'}
            queryset = Model.objects.filter(**filter_kwargs)
            count = queryset.count()
            
            if count == 0:
                self.stdout.write(f'  No Cloudinary URLs found in {model_name}')
                continue
            
            self.stdout.write(f'  Found {count} records to migrate')
            
            # Process in batches
            processed = 0
            for obj in queryset.iterator():
                url = getattr(obj, field_name)
                if not url or 'cloudinary.com' not in url:
                    total_skipped += 1
                    continue
                
                # Extract path from Cloudinary URL
                path = get_path_from_cloudinary_url(url)
                if not path:
                    self.stdout.write(self.style.WARNING(f'  Could not extract path from: {url}'))
                    total_failed += 1
                    continue
                
                if dry_run:
                    self.stdout.write(f'  [DRY-RUN] Would migrate: {path}')
                    total_migrated += 1
                else:
                    try:
                        # Download from Cloudinary
                        response = requests.get(url, timeout=30)
                        if response.status_code != 200:
                            self.stdout.write(self.style.WARNING(f'  Failed to download: {url}'))
                            total_failed += 1
                            continue
                        
                        # Upload to Bunny CDN
                        new_url = upload_to_bunny(response.content, path)
                        
                        # Update database
                        setattr(obj, field_name, new_url)
                        obj.save(update_fields=[field_name])
                        
                        self.stdout.write(self.style.SUCCESS(f'  Migrated: {path}'))
                        total_migrated += 1
                        
                        # Small delay to avoid rate limiting
                        time.sleep(0.1)
                        
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f'  Error migrating {path}: {e}'))
                        total_failed += 1
                
                processed += 1
                if processed % batch_size == 0:
                    self.stdout.write(f'  Processed {processed}/{count}...')
        
        # Summary
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'Migration Complete!'))
        self.stdout.write(f'  Migrated: {total_migrated}')
        self.stdout.write(f'  Failed: {total_failed}')
        self.stdout.write(f'  Skipped: {total_skipped}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('\nThis was a dry run. Run without --dry-run to actually migrate.'))
