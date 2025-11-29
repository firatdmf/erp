from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
import time
from django.views import View, generic
from django.views.generic.edit import ModelFormMixin
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, Http404
from django.db import transaction
from django.db import models
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
import json

from .models import (
    Product,
    ProductVariant,
    ProductVariantAttribute,
    ProductVariantAttributeValue,
    ProductFile,
    ProductCategory,
)
from .forms import ProductForm, ProductFileFormSet
from cloudinary.uploader import upload as cloudinary_upload
from cloudinary.exceptions import Error as CloudinaryError


# ----------------------------------------------
# Base Views
# ----------------------------------------------
@method_decorator(login_required, name="dispatch")
class Index(generic.TemplateView):
    template_name = "marketing/index.html"


class ProductList(generic.ListView):
    model = Product
    template_name = "marketing/product_list.html"
    context_object_name = "products"
    paginate_by = 25  # Show 25 products per page
    
    def get_queryset(self):
        from django.db.models import Count
        
        queryset = super().get_queryset()
        search_query = self.request.GET.get('search', '').strip()
        
        if search_query:
            # Search by title, SKU, or barcode (case-insensitive)
            queryset = queryset.filter(
                models.Q(title__icontains=search_query) |
                models.Q(sku__icontains=search_query) |
                models.Q(barcode__icontains=search_query)
            )
        
        # Optimize: Annotate variant count (single query) + select_related
        return queryset.select_related(
            'category', 
            'primary_image', 
            'supplier'
        ).annotate(
            variant_count=Count('variants')  # Efficient count in SQL
        ).order_by('title')


class ProductDetail(generic.DetailView):
    model = Product
    template_name = "marketing/product_detail.html"
    context_object_name = "product"
    
    def dispatch(self, request, *args, **kwargs):
        """Log total view execution time"""
        self.view_start_time = time.time()
        print("\n" + "="*80)
        print(f"🔍 ProductDetail View Started - PK: {kwargs.get('pk')}")
        print("="*80)
        response = super().dispatch(request, *args, **kwargs)
        total_time = time.time() - self.view_start_time
        print("="*80)
        print(f"⏱️  TOTAL VIEW TIME: {total_time:.4f} seconds")
        print("="*80 + "\n")
        return response
    
    def get_queryset(self):
        """Optimize query to prevent N+1 problems"""
        query_start = time.time()
        print("\n📊 Building queryset...")
        
        # Use Prefetch objects for better control and ordering
        from django.db.models import Prefetch
        
        queryset = Product.objects.select_related(
            'category',
            'primary_image',
            'supplier'
        ).prefetch_related(
            # Prefetch product files
            Prefetch(
                'files',
                queryset=ProductFile.objects.select_related('product_variant').order_by('sequence', 'pk')
            ),
            'collections',
            'variants',  # Prefetch variants first
            # Then prefetch variant files with ordering - single query for ALL variant files
            Prefetch(
                'variants__files',
                queryset=ProductFile.objects.order_by('sequence', 'pk')
            ),
            # Prefetch variant attributes with related attribute names - single query
            Prefetch(
                'variants__product_variant_attribute_values',
                queryset=ProductVariantAttributeValue.objects.select_related('product_variant_attribute')
            ),
            # Prefetch variant product attributes (ProductAttribute model)
            'variants__attributes',
            # Prefetch product-level attributes
            'attributes'
        )
        
        query_time = time.time() - query_start
        print(f"   ✓ Queryset built: {query_time:.4f}s")
        return queryset
    
    def get_object(self, queryset=None):
        """Fetch the product object and measure time"""
        fetch_start = time.time()
        print("\n🔎 Fetching product object...")
        
        obj = super().get_object(queryset)
        
        fetch_time = time.time() - fetch_start
        print(f"   ✓ Product fetched: {fetch_time:.4f}s")
        print(f"   📦 Product: {obj.title} (SKU: {obj.sku})")
        
        return obj
    
    def get_context_data(self, **kwargs):
        context_start = time.time()
        print("\n📝 Building context...")
        
        context = super().get_context_data(**kwargs)
        
        # Pre-evaluate and cache querysets to avoid repeated DB hits in template
        context['product_files'] = list(self.object.files.all())  # Cache files
        context['product_variants'] = list(self.object.variants.all())  # Cache variants
        context['product_collections'] = list(self.object.collections.all())  # Cache collections
        
        # Clear session cleanup URLs after displaying them in template
        if 'cloudinary_cleanup_urls' in self.request.session:
            # Let template access it once, then schedule for deletion
            context['cleanup_triggered'] = True
        
        context_time = time.time() - context_start
        print(f"   ✓ Context built: {context_time:.4f}s")
        
        return context
    
    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        
        # Clear cleanup URLs after template has rendered
        if 'cloudinary_cleanup_urls' in request.session:
            del request.session['cloudinary_cleanup_urls']
            print("🗑️ Cleared Cloudinary cleanup URLs from session")
        
        return response


# ----------------------------------------------
# Base class for product create/edit views
# ----------------------------------------------
class BaseProductView(ModelFormMixin):
    model = Product
    form_class = ProductForm

    def get_success_url(self):
        return reverse("marketing:product_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context["productfile_formset"] = ProductFileFormSet(
                self.request.POST, self.request.FILES, instance=self.object
            )
        else:
            context["productfile_formset"] = ProductFileFormSet(instance=self.object)
        return context

    def save_product_files(self, product, formset):
        if formset.is_valid():
            formset.instance = product
            formset.save()
    
    def handle_attributes(self, product):
        """
        Handle Product Attributes from POST data
        Expects: attribute_names[] and attribute_values[] arrays
        """
        from marketing.models import ProductAttribute
        
        attribute_names = self.request.POST.getlist('attribute_names[]')
        attribute_values = self.request.POST.getlist('attribute_values[]')
        
        if not attribute_names:
            # No attributes submitted, clear existing
            product.attributes.all().delete()
            print("🗑️ Cleared all product attributes (none submitted)")
            return
        
        # Delete all existing attributes for clean slate
        product.attributes.all().delete()
        
        # Create new attributes
        for idx, (name, value) in enumerate(zip(attribute_names, attribute_values)):
            if name.strip() and value.strip():  # Skip empty entries
                ProductAttribute.objects.create(
                    product=product,
                    name=name.strip(),
                    value=value.strip(),
                    sequence=idx
                )
                print(f"✅ Created attribute: {name} = {value}")

    def handle_variants(self, product, variants_json):
        """
        Creates or updates ProductVariant and links shared ProductVariantAttributeValue.
        """
        # print("\n=== handle_variants called ===")
        # print(f"variants_json type: {type(variants_json)}")
        # print(f"variants_json content: {variants_json}")
        
        if not variants_json:
            # print("No variants_json provided")
            return

        try:
            variants_json = json.loads(variants_json)
            # print(f"Parsed variants_json: {variants_json}")
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            raise ValueError(
                {"JSON": "failed to parse json: variants.json from variant_form.js"}
            )
        
        # Handle if variants_json is a list (empty variants) instead of dict
        if isinstance(variants_json, list):
            if len(variants_json) == 0:
                # No variants to process
                return
            # If it's a list with items, wrap it in expected format
            variants_json = {"product_variant_list": variants_json}

        # ---------------------------- this runs when we have no variants. --------------------------------------------
        delete_all_variants = variants_json.get("delete_all_variants", False)
        if delete_all_variants:
            product.variants.all().delete()
            # delete the files that marked as deleted by user and were not linked to any variant
            deleted_files_pks = variants_json.get("deleted_files", [])
            if len(deleted_files_pks) > 0:
                print("these files will be deleted:", deleted_files_pks)
                ProductFile.objects.filter(pk__in=deleted_files_pks).delete()
            if len(self.request.FILES.getlist("no_variant_file")) == 0:
                product.primary_image = None

            # add the no_variant_files to product files
            uploaded_files = []
            for index, file_obj in enumerate(self.request.FILES.getlist("no_variant_file")):
                try:
                    folder = f"media/product_images/product_{product.sku}"
                    upload_result = cloudinary_upload(
                        file_obj, folder=folder, resource_type="image"
                    )
                    url = upload_result.get("secure_url")
                    if url:
                        product_file = ProductFile.objects.create(
                            product=product,
                            file_url=url,
                            is_primary=False,  # Will be set below based on order
                            sequence=index,
                        )
                        uploaded_files.append(product_file)
                except CloudinaryError:
                    print(
                        f"There was a cloudinary error in uploading file: {file_obj}, but we will continue"
                    )
                    continue
            
            # Handle image ordering - first image is primary (ONLY for main product images, not variants)
            image_order = self.request.POST.get('image_order')
            if image_order:
                try:
                    order_list = json.loads(image_order)
                    if order_list:
                        # Clear all is_primary flags for main product images only
                        ProductFile.objects.filter(product=product, product_variant__isnull=True).update(is_primary=False)
                        # Set first image as primary (must be a main product image, not variant)
                        first_image_id = order_list[0]
                        primary_file = ProductFile.objects.get(pk=first_image_id, product=product, product_variant__isnull=True)
                        primary_file.is_primary = True
                        primary_file.save()
                        product.primary_image = primary_file
                        product.save()
                        print(f"Set primary image to {first_image_id} (main product image) based on order")
                except (ValueError, ProductFile.DoesNotExist, json.JSONDecodeError) as e:
                    print(f"Error setting primary from order: {e}")
            else:
                # If no order specified, set first available MAIN PRODUCT image as primary
                first_file = ProductFile.objects.filter(product=product, product_variant__isnull=True).order_by('sequence', 'pk').first()
                if first_file:
                    ProductFile.objects.filter(product=product, product_variant__isnull=True).update(is_primary=False)
                    first_file.is_primary = True
                    first_file.save()
                    product.primary_image = first_file
                    product.save()
                    print(f"Set first available main product image {first_file.pk} as primary")
            
            return

        # --------------------------------------------------------------------------------------------------------------------

        import time
        handle_start = time.time()
        
        variants_data = variants_json.get("product_variant_list", [])
        import os
        DEBUG_PERF = os.getenv('DEBUG_PERFORMANCE', 'false').lower() == 'true'
        
        if DEBUG_PERF:
            print(f"\n⏱️  Processing {len(variants_data)} variants...")

        # product's existing variants' SKUs
        delete_start = time.time()
        existing_skus = set(self.object.variants.values_list("variant_sku", flat=True))
        # SKU's submitted in the form
        submitted_skus = {
            v["variant_sku"] for v in variants_data if v.get("variant_sku")
        }
        # delete variants that are no longer with us.
        deleted_count = ProductVariant.objects.filter(
            product=self.object, variant_sku__in=(existing_skus - submitted_skus)
        ).delete()[0]
        print(f"  ✓ Deleted {deleted_count} variants: {time.time() - delete_start:.3f}s")
        
        # Pre-fetch ALL data in one go to minimize queries
        prefetch_start = time.time()
        all_attr_names = set()
        all_attr_value_pairs = set()
        all_variant_skus = [v.get("variant_sku") for v in variants_data if v.get("variant_sku")]
        
        for variant_data in variants_data:
            variant_attribute_values_dict = variant_data.get("variant_attribute_values", {})
            for attr_name, attr_value in variant_attribute_values_dict.items():
                normalized_name = str(attr_name).lower().replace(" ", "")
                normalized_value = str(attr_value).lower().replace(" ", "")
                all_attr_names.add(normalized_name)
                all_attr_value_pairs.add((normalized_name, normalized_value))
        
        # Fetch existing attributes (don't create yet)
        existing_attrs = {a.name: a for a in ProductVariantAttribute.objects.filter(name__in=all_attr_names)}
        
        # Create missing attributes in bulk
        attrs_to_create = [ProductVariantAttribute(name=name) for name in all_attr_names if name not in existing_attrs]
        if attrs_to_create:
            created = ProductVariantAttribute.objects.bulk_create(attrs_to_create, ignore_conflicts=True)
            # Refetch to get IDs
            for attr in ProductVariantAttribute.objects.filter(name__in=all_attr_names):
                existing_attrs[attr.name] = attr
        
        attr_cache = existing_attrs
        
        # Fetch only needed attribute values, not all
        attr_value_cache = {}
        if all_attr_value_pairs:
            # Build Q objects for exact matches only
            from django.db.models import Q
            q_objects = Q()
            for attr_name, attr_value in all_attr_value_pairs:
                attr_obj = attr_cache.get(attr_name)
                if attr_obj:
                    q_objects |= Q(
                        product_variant_attribute=attr_obj,
                        product_variant_attribute_value=attr_value
                    )
            
            existing_values = ProductVariantAttributeValue.objects.filter(
                q_objects
            ).select_related('product_variant_attribute')
            
            for val_obj in existing_values:
                key = (val_obj.product_variant_attribute.name, val_obj.product_variant_attribute_value)
                attr_value_cache[key] = val_obj
        
        # Create missing values in bulk
        values_to_create = []
        for attr_name, attr_value in all_attr_value_pairs:
            if (attr_name, attr_value) not in attr_value_cache:
                attr_obj = attr_cache[attr_name]
                values_to_create.append(ProductVariantAttributeValue(
                    product_variant_attribute=attr_obj,
                    product_variant_attribute_value=attr_value
                ))
        
        if values_to_create:
            created_values = ProductVariantAttributeValue.objects.bulk_create(values_to_create, ignore_conflicts=True)
            # If DB supports returning IDs, use them directly; otherwise refetch only created ones
            if created_values and created_values[0].id:
                for val_obj in created_values:
                    key = (val_obj.product_variant_attribute.name, val_obj.product_variant_attribute_value)
                    attr_value_cache[key] = val_obj
            else:
                # Fallback: refetch only missing values
                missing_pairs = [p for p in all_attr_value_pairs if p not in attr_value_cache]
                if missing_pairs:
                    q_objects = Q()
                    for attr_name, attr_value in missing_pairs:
                        attr_obj = attr_cache.get(attr_name)
                        if attr_obj:
                            q_objects |= Q(
                                product_variant_attribute=attr_obj,
                                product_variant_attribute_value=attr_value
                            )
                    for val_obj in ProductVariantAttributeValue.objects.filter(q_objects).select_related('product_variant_attribute'):
                        key = (val_obj.product_variant_attribute.name, val_obj.product_variant_attribute_value)
                        attr_value_cache[key] = val_obj
        
        print(f"  ✓ Pre-fetched all data: {len(attr_cache)} attrs, {len(attr_value_cache)} values: {time.time() - prefetch_start:.3f}s")
        
        # Fetch variants WITH files in ONE query (combines 385 and 399)
        variant_create_start = time.time()
        variant_skus = [v.get("variant_sku") for v in variants_data if v.get("variant_sku")]
        existing_variants = ProductVariant.objects.filter(
            product=self.object, variant_sku__in=variant_skus
        ).prefetch_related('files')
        
        existing_variants_dict = {}
        variant_files_cache = {}
        for var in existing_variants:
            existing_variants_dict[var.variant_sku] = var
            variant_files_cache[var.variant_sku] = {f.pk: f for f in var.files.all()}
        
        # Create missing variants in bulk
        variants_to_create = []
        for sku in variant_skus:
            if sku not in existing_variants_dict:
                variants_to_create.append(ProductVariant(product=self.object, variant_sku=sku))
        
        if variants_to_create:
            created = ProductVariant.objects.bulk_create(variants_to_create)
            for v in created:
                existing_variants_dict[v.variant_sku] = v
        
        # Now update all variant fields and collect for bulk_update
        variants_to_update = []
        changed_fields = set()  # Track which fields actually changed
        
        # Fields that are not part of the model (form-only fields)
        non_model_fields = {"variant_sku", "variant_attribute_values", "variant_images", "primary_image_index", "product_attributes"}
        
        for variant_data in variants_data:
            variant_sku = variant_data.get("variant_sku")
            if not variant_sku:
                continue
            
            variant = existing_variants_dict.get(variant_sku)
            if not variant:
                continue
            
            has_changes = False
            # Update variant fields and track changes
            for key, value in variant_data.items():
                if key not in non_model_fields:
                    old_value = getattr(variant, key, None)
                    if old_value != value:
                        setattr(variant, key, value)
                        changed_fields.add(key)
                        has_changes = True
                elif key == "product_attributes":
                    # Track that we have product attributes to process later
                    # but don't add to model fields
                    pass
            
            # Only add to update list if something changed
            if has_changes:
                variants_to_update.append(variant)
        
        # Bulk update only changed fields
        if variants_to_update and changed_fields:
            ProductVariant.objects.bulk_update(variants_to_update, list(changed_fields))
        
        print(f"  ✓ Created/updated {len(variants_to_update)} variants: {time.time() - variant_create_start:.3f}s")
        
        # Prepare M2M relationships using direct through table manipulation
        attr_bulk_start = time.time()
        
        # Get the through model
        ThroughModel = ProductVariant.product_variant_attribute_values.through
        
        # Always delete/recreate M2M relationships to ensure attributes are updated correctly
        # (e.g. if user changes "Pink" to "Gold", we must remove "Pink" association)
        variant_ids = [v.id for v in existing_variants_dict.values()]
        if variant_ids:
            ThroughModel.objects.filter(productvariant_id__in=variant_ids).delete()
        else:
            # No variants, skip M2M entirely
            print(f"  ✓ Skipped M2M (no variants): {time.time() - attr_bulk_start:.3f}s")
            variant_ids = []
        
        # Prepare all M2M entries for bulk creation
        m2m_entries = []
        for variant_data in variants_data:
            variant_sku = variant_data.get("variant_sku")
            if not variant_sku:
                continue
            
            variant = existing_variants_dict.get(variant_sku)
            if not variant:
                continue
            
            variant_attribute_values_dict = variant_data.get("variant_attribute_values", {})
            
            for attr_name, attr_value in variant_attribute_values_dict.items():
                normalized_name = str(attr_name).lower().replace(" ", "")
                normalized_value = str(attr_value).lower().replace(" ", "")
                value_obj = attr_value_cache.get((normalized_name, normalized_value))
                if value_obj:
                    m2m_entries.append(ThroughModel(
                        productvariant_id=variant.id,
                        productvariantattributevalue_id=value_obj.id
                    ))
        
        # Bulk create all M2M relationships at once
        if m2m_entries:
            ThroughModel.objects.bulk_create(m2m_entries, ignore_conflicts=True)
        
        print(f"  ✓ Set M2M relationships ({len(m2m_entries)} entries): {time.time() - attr_bulk_start:.3f}s")
        
        # Handle Product Attributes for variants (variant-specific attribute values)
        variant_attr_start = time.time()
        from marketing.models import ProductAttribute
        
        for variant_data in variants_data:
            variant_sku = variant_data.get("variant_sku")
            if not variant_sku:
                continue
            
            variant = existing_variants_dict.get(variant_sku)
            if not variant:
                continue
            
            # Get variant's product attributes (if provided)
            variant_product_attrs = variant_data.get("product_attributes", [])
            
            # Clear existing variant attributes
            variant.attributes.all().delete()
            
            # Create new attributes for this variant
            if variant_product_attrs:
                for idx, attr_data in enumerate(variant_product_attrs):
                    attr_name = attr_data.get("name", "").strip()
                    attr_value = attr_data.get("value", "").strip()
                    if attr_name and attr_value:
                        ProductAttribute.objects.create(
                            product_variant=variant,
                            name=attr_name,
                            value=attr_value,
                            sequence=idx
                        )
        
        print(f"  ✓ Handled variant product attributes: {time.time() - variant_attr_start:.3f}s")
        
        # Pre-fetch all unlinked files (uploaded but not assigned to variants) - ONCE
        all_image_ids = set()
        for variant_data in variants_data:
            variant_image_info = variant_data.get("variant_images", [])
            for img_info in variant_image_info:
                img_id = img_info.get("id")
                if img_id:
                    try:
                        all_image_ids.add(int(img_id))
                    except (ValueError, TypeError):
                        pass
        
        # Fetch ALL files by ID (including those already linked to other variants)
        # This allows sharing images across variants (shared pool)
        all_files_dict = {}
        if all_image_ids:
            all_files = ProductFile.objects.filter(
                pk__in=all_image_ids,
                product=self.object
                # NO product_variant__isnull filter - allow linking ANY file
            )
            all_files_dict = {f.pk: f for f in all_files}
            print(f"  ✓ Fetched {len(all_files_dict)} files from shared pool (for linking)")
        
        variant_loop_start = time.time()
        index = 0
        total_variant_time = 0
        total_attr_time = 0
        total_image_time = 0
        
        # Collect all images to create/update across all variants
        all_images_to_create = []  # New copies for sharing
        all_images_to_update = []  # Updates for existing files
        
        for variant_data in variants_data:
            variant_sku = variant_data.get("variant_sku")
            if not variant_sku:
                continue
            
            variant = existing_variants_dict.get(variant_sku)
            if not variant:
                continue

            # Handle variant images from JSON (includes sequence info)
            image_start = time.time()
            variant_image_info = variant_data.get("variant_images", [])
            
            print(f"\n🖼️  Processing images for variant {variant_sku}:")
            print(f"   Found {len(variant_image_info)} images in JSON")
            for img_info in variant_image_info:
                print(f"   - Image ID: {img_info.get('id')}, Sequence: {img_info.get('sequence')}")
            
            if variant_image_info:
                for img_info in variant_image_info:
                    img_id = img_info.get("id")
                    img_sequence = img_info.get("sequence", 0)
                    
                    if img_id:
                        try:
                            img_id = int(img_id)
                        except (ValueError, TypeError):
                            pass

                        # Get source file from shared pool
                        source_file = all_files_dict.get(img_id)
                        if source_file:
                            # Check if this file already belongs to this variant
                            if source_file.product_variant_id == variant.id:
                                # Just update sequence/primary
                                source_file.sequence = img_sequence
                                source_file.is_primary = (img_sequence == 0)
                                all_images_to_update.append(source_file)
                                print(f"✅ Updated file {img_id} for variant {variant_sku} (seq={img_sequence})")
                            elif source_file.product_variant_id is None:
                                # File is unlinked (not assigned to any variant yet)
                                # Link it directly instead of creating a copy
                                source_file.product_variant = variant
                                source_file.sequence = img_sequence
                                source_file.is_primary = (img_sequence == 0)
                                all_images_to_update.append(source_file)
                                print(f"🔗 Linked unlinked file {img_id} to variant {variant_sku} (seq={img_sequence})")
                            else:
                                # File belongs to another variant - create a NEW copy (allows multi-variant sharing)
                                new_file = ProductFile(
                                    product=self.object,
                                    product_variant=variant,
                                    file_url=source_file.file_url,
                                    sequence=img_sequence,
                                    is_primary=(img_sequence == 0)
                                )
                                all_images_to_create.append(new_file)
                                print(f"🔄 Created copy of file {img_id} for variant {variant_sku} (seq={img_sequence})")
                        else:
                            print(f"❌ WARNING: Image {img_id} not found in shared pool")
            
            image_time = time.time() - image_start
            total_image_time += image_time
            
            # NOTE: Images are already uploaded to product via instant_upload_file API
            # and linked here via unlinked_files_dict above. No need for file upload here.
            index += 1
        
        # Bulk create new file copies (for multi-variant sharing)
        if all_images_to_create:
            ProductFile.objects.bulk_create(all_images_to_create)
        
        # Bulk update existing files (including product_variant link for newly assigned files)
        if all_images_to_update:
            ProductFile.objects.bulk_update(all_images_to_update, ['product_variant', 'sequence', 'is_primary'])
        
        variant_loop_time = time.time() - variant_loop_start
        print(f"  ✓ Processed variant images: {variant_loop_time:.3f}s (created {len(all_images_to_create)}, updated {len(all_images_to_update)} files)")
        print(f"    - Images: {total_image_time:.3f}s")
        
        # Handle primary variant image selection
        primary_start = time.time()
        primary_variant_index = self.request.POST.get('primary_variant_image')
        if primary_variant_index:
            try:
                primary_variant_index = int(primary_variant_index)
                # Index in form is 1-based, convert to 0-based for list
                if 0 < primary_variant_index <= len(variants_data):
                    primary_variant_sku = variants_data[primary_variant_index - 1].get("variant_sku")
                    if primary_variant_sku:
                        # Get the first file of the primary variant
                        primary_variant = ProductVariant.objects.get(variant_sku=primary_variant_sku, product=self.object)
                        primary_file = ProductFile.objects.filter(product_variant=primary_variant).first()
                        if primary_file:
                            # Clear all is_primary flags
                            ProductFile.objects.filter(product=self.object).update(is_primary=False)
                            # Set new primary
                            primary_file.is_primary = True
                            primary_file.save()
                            self.object.primary_image = primary_file
                            self.object.save()
                            print(f"Set primary image to variant {primary_variant_sku}")
            except (ValueError, ProductVariant.DoesNotExist, IndexError) as e:
                print(f"Error setting primary variant image: {e}")

        primary_time = time.time() - primary_start
        if primary_variant_index:
            print(f"  ✓ Primary variant selection: {primary_time:.3f}s")
        
        # Handle unlinking (variant image removal) passed via json data.
        # Note: We unlink from variant (set product_variant=None), not delete from DB or Cloudinary
        delete_files_start = time.time()
        deleted_files_pks = variants_json.get("deleted_files", [])
        print(f"deleted files pks: {deleted_files_pks}")
        if len(deleted_files_pks) > 0:
            # Unlink from variant instead of deleting (files stay in manage files)
            ProductFile.objects.filter(pk__in=deleted_files_pks).update(product_variant=None)
            print(f"  ✓ Unlinked {len(deleted_files_pks)} files from variants: {time.time() - delete_files_start:.3f}s")
        
        # IMPORTANT: Upload main product images even when variants exist
        upload_start = time.time()
        uploaded_main_files = []
        for index, file_obj in enumerate(self.request.FILES.getlist("no_variant_file")):
            try:
                folder = f"media/product_images/product_{self.object.sku}"
                upload_result = cloudinary_upload(
                    file_obj, folder=folder, resource_type="image"
                )
                url = upload_result.get("secure_url")
                if url:
                    product_file = ProductFile.objects.create(
                        product=self.object,
                        file_url=url,
                        is_primary=False,  # Will be set below
                        sequence=index,
                    )
                    uploaded_main_files.append(product_file)
                    print(f"Uploaded main product file {product_file.pk} with variants")
            except CloudinaryError:
                print(
                    f"There was a cloudinary error in uploading file: {file_obj}, but we will continue"
                )
                continue
        
        upload_time = time.time() - upload_start
        if uploaded_main_files:
            print(f"  ✓ Uploaded {len(uploaded_main_files)} main files: {upload_time:.3f}s")
        
        # After handling variants, ALWAYS use first variant's first image as product primary
        # This ignores any main product images if variants exist
        set_primary_start = time.time()
        # Always handle main product image ordering if provided
        # User request: "primary imagei oradan seçelim" (select primary image from Product Images section)
        image_order = self.request.POST.get('image_order')
        if image_order:
            try:
                order_list = json.loads(image_order)
                if order_list:
                    # Clear all is_primary flags
                    ProductFile.objects.filter(product=self.object).update(is_primary=False)
                    
                    # Set first image as primary
                    first_image_id = order_list[0]
                    primary_file = ProductFile.objects.get(pk=first_image_id, product=self.object)
                    primary_file.is_primary = True
                    primary_file.save()
                    self.object.primary_image = primary_file
                    self.object.save()
                    print(f"Set primary image to {first_image_id} based on order")
            except (ValueError, ProductFile.DoesNotExist, json.JSONDecodeError) as e:
                print(f"Error setting primary from order: {e}")
        
        set_primary_time = time.time() - set_primary_start
        print(f"  ✓ Set primary image: {set_primary_time:.3f}s")
        
        total_handle_time = time.time() - handle_start
        print(f"\n⏱️  TOTAL handle_variants: {total_handle_time:.3f}s")


# ----------------------------------------------
# Product Create / Edit Views
# ----------------------------------------------
@method_decorator(login_required, name="dispatch")
class ProductCreate(BaseProductView, generic.CreateView):
    template_name = "marketing/product_create.html"
    template_name = "marketing/product_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_update"] = False
        return context

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            
            # Link temporary files from session to product
            temp_files = self.request.session.get('temp_product_files', {})
            temp_variant_files_map = {}  # Map temp_id -> actual ProductFile ID
            
            if temp_files:
                print(f"📎 Linking {len(temp_files.get('main_images', []))} main images from temp storage")
                
                # Link main product images AND add to temp_variant_files_map
                # (so variants can reference them)
                for file_data in temp_files.get('main_images', []):
                    product_file = ProductFile.objects.create(
                        product=self.object,
                        file_url=file_data['url'],
                        sequence=file_data['sequence'],
                        is_primary=(file_data['sequence'] == 0)
                    )
                    # Map temp public_id to real DB ID (for variant references)
                    temp_variant_files_map[file_data['public_id']] = product_file.pk
                    print(f"✓ Created main ProductFile {product_file.pk}, mapped from {file_data['public_id']}")
                
                # Create ProductFile records for ALL temp variant images FIRST
                # This way handle_variants() can find them by real DB ID
                variant_images_temp = temp_files.get('variant_images', {})
                for variant_temp_id, file_list in variant_images_temp.items():
                    for file_data in file_list:
                        # Create ProductFile (unlinked to variant yet)
                        product_file = ProductFile.objects.create(
                            product=self.object,
                            file_url=file_data['url'],
                            sequence=file_data['sequence'],
                            is_primary=False  # Will be set by handle_variants
                        )
                        # Map temp public_id to real DB ID
                        temp_variant_files_map[file_data['public_id']] = product_file.pk
                        print(f"✓ Created ProductFile {product_file.pk} for temp variant {variant_temp_id}")
                
                # Clear temp files from session
                del self.request.session['temp_product_files']
                self.request.session.modified = True
                print("✓ Temporary files linked and session cleared")
            
            # Update variants_json to replace temp IDs with real DB IDs
            variants_json_str = self.request.POST.get("variants_json", "[]")
            print(f"\n🔍 DEBUG: variants_json_str = {variants_json_str[:200] if variants_json_str else 'None'}...")
            print(f"🔍 DEBUG: temp_variant_files_map = {temp_variant_files_map}")
            
            if temp_variant_files_map and variants_json_str and variants_json_str != "[]":
                try:
                    variants_json = json.loads(variants_json_str)
                    print(f"🔍 DEBUG: Parsed variants_json, type = {type(variants_json)}")
                    
                    if isinstance(variants_json, dict) and "product_variant_list" in variants_json:
                        print(f"🔍 DEBUG: Found {len(variants_json['product_variant_list'])} variants")
                        
                        for idx, variant_data in enumerate(variants_json["product_variant_list"]):
                            variant_images = variant_data.get("variant_images", [])
                            print(f"🔍 DEBUG: Variant {idx} has {len(variant_images)} images")
                            
                            for img_idx, img_info in enumerate(variant_images):
                                temp_id = img_info.get("id")
                                print(f"🔍 DEBUG: Image {img_idx} temp_id = {temp_id} (type: {type(temp_id)})")
                                
                                if temp_id:
                                    # Check if it's a string temp ID
                                    if isinstance(temp_id, str) and temp_id in temp_variant_files_map:
                                        old_id = temp_id
                                        img_info["id"] = temp_variant_files_map[temp_id]
                                        print(f"✅ Mapped temp ID '{old_id}' -> real ID {img_info['id']}")
                                    else:
                                        print(f"⚠️ Temp ID '{temp_id}' not found in map or not string")
                        
                        # Re-serialize updated JSON
                        variants_json_str = json.dumps(variants_json)
                        print(f"✅ Updated variants_json_str")
                except json.JSONDecodeError as e:
                    print(f"❌ JSON decode error: {e}")
                except Exception as e:
                    print(f"❌ Error updating variants_json: {e}")
            
            # Check if it's an AJAX request (sidebar submission)
            if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                # Handle primary image upload from sidebar
                primary_image_file = self.request.FILES.get('primary_image')
                if primary_image_file:
                    try:
                        folder = f"media/product_images/product_{self.object.sku}"
                        upload_result = cloudinary_upload(
                            primary_image_file, folder=folder, resource_type="image"
                        )
                        url = upload_result.get("secure_url")
                        if url:
                            product_file = ProductFile.objects.create(
                                product=self.object,
                                file_url=url,
                                is_primary=True
                            )
                            self.object.primary_image = product_file
                            self.object.save()
                    except CloudinaryError as e:
                        print(f"Cloudinary error uploading primary image: {e}")
                
                # Handle variants from sidebar
                variants_json = self.request.POST.get("variants_json", "[]")
                if variants_json and variants_json != "[]":
                    self.handle_variants(self.object, variants_json)
                
                return JsonResponse({
                    'success': True,
                    'redirect_url': self.get_success_url()
                })
            
            # Full form with files and variants
            context = self.get_context_data()
            self.save_product_files(self.object, context["productfile_formset"])

            # Handle product attributes
            self.handle_attributes(self.object)

            # Use updated variants_json_str (with temp IDs replaced) or original
            if not variants_json_str:
                variants_json_str = self.request.POST.get("variants_json", "[]")
            self.handle_variants(self.object, variants_json_str)

        return super().form_valid(form)

    def form_invalid(self, form):
        # Check if it's an AJAX request
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors.as_json()
            })
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


@method_decorator(login_required, name="dispatch")
class ProductEdit(BaseProductView, generic.UpdateView):
    template_name = "marketing/product_edit.html"
    template_name = "marketing/product_form.html"
    
    def dispatch(self, request, *args, **kwargs):
        """Log total view execution time"""
        self.view_start_time = time.time()
        response = super().dispatch(request, *args, **kwargs)
        total_time = time.time() - self.view_start_time
        if total_time > 0.5:  # Only log if slow
            print(f"\n⚠️  ProductEdit took {total_time:.4f}s for PK: {kwargs.get('pk')}")
        return response
    
    def get_queryset(self):
        """Optimize query to prevent N+1 problems"""
        from django.db.models import Prefetch
        
        return Product.objects.select_related(
            'category',
            'primary_image',
            'supplier'
        ).prefetch_related(
            # Prefetch product files
            Prefetch(
                'files',
                queryset=ProductFile.objects.select_related('product_variant').order_by('sequence', 'pk')
            ),
            'collections',
            'variants',  # Prefetch variants first
            # Prefetch all variant files in single query
            Prefetch(
                'variants__files',
                queryset=ProductFile.objects.order_by('sequence', 'pk')
            ),
            # Prefetch variant attributes in single query
            Prefetch(
                'variants__product_variant_attribute_values',
                queryset=ProductVariantAttributeValue.objects.select_related('product_variant_attribute')
            ),
            # Prefetch variant product attributes (ProductAttribute model)
            'variants__attributes',
            # Prefetch product-level attributes
            'attributes'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_update"] = True
        # Variants are already prefetched in get_queryset(), no need to force evaluation
        # Forcing evaluation with list() can cause cursor issues
        context["variants"] = self.object.variants.all()
        return context

    # # This sends data to the form.
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["is_update"] = True
        return kwargs

    def form_valid(self, form):
        import time
        form_valid_start = time.time()
        
        # Check if only variant images changed (no SKU/price/attribute changes)
        variants_json_str = self.request.POST.get("variants_json", "[]")
        only_images_changed = False
        
        try:
            variants_json = json.loads(variants_json_str) if variants_json_str and variants_json_str != "[]" else {}
            if isinstance(variants_json, dict) and "product_variant_list" in variants_json:
                # Quick check: if all variants exist with same SKU and we're just reordering images
                variant_skus = [v.get("variant_sku") for v in variants_json["product_variant_list"] if v.get("variant_sku")]
                existing_skus = set(self.object.variants.values_list("variant_sku", flat=True))
                if set(variant_skus) == existing_skus and len(variant_skus) == len(existing_skus):
                    # Same variants, likely just image reordering
                    only_images_changed = True
        except:
            pass
        
        with transaction.atomic():
            # print(self.request.POST)
            save_start = time.time()
            self.object = form.save()
            save_time = time.time() - save_start
            if save_time > 0.05:
                print(f"\n⏱️  Form save: {save_time:.3f}s")
            
            # Handle deleted product files from hidden input
            delete_main_start = time.time()
            deleted_files_json = self.request.POST.get("deleted_files", "")
            cloudinary_urls_to_delete = []  # Collect URLs for async deletion
            
            if deleted_files_json:
                try:
                    deleted_file_pks = json.loads(deleted_files_json)
                    if deleted_file_pks:
                        print(f"\n🗑️ Deleting {len(deleted_file_pks)} main files with bulk delete")
                        # Get URLs before deleting from DB
                        fetch_start = time.time()
                        files_to_delete = list(ProductFile.objects.filter(pk__in=deleted_file_pks))
                        print(f"   🔍 Fetched files in {(time.time() - fetch_start):.3f}s")
                        
                        cloudinary_urls_to_delete.extend([f.file_url for f in files_to_delete if f.file_url])
                        print(f"   📎 Collected {len(cloudinary_urls_to_delete)} URLs for async cleanup")
                        
                        # Raw SQL delete - fastest (bypasses Django ORM completely)
                        bulk_start = time.time()
                        from django.db import connection
                        with connection.cursor() as cursor:
                            pks_str = ','.join(map(str, deleted_file_pks))
                            cursor.execute(f"DELETE FROM marketing_productfile WHERE id IN ({pks_str})")
                        print(f"   ⚡ Raw SQL delete took {(time.time() - bulk_start):.3f}s")
                        print(f"⏱️  TOTAL main files deletion: {time.time() - delete_main_start:.3f}s")
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing deleted_files: {e}")
            
            # Handle deleted variant files from hidden input
            delete_variant_start = time.time()
            deleted_variant_files_json = self.request.POST.get("deleted_variant_files", "")
            if deleted_variant_files_json:
                try:
                    deleted_variant_file_pks = json.loads(deleted_variant_files_json)
                    if deleted_variant_file_pks:
                        print(f"\n🗑️ Deleting {len(deleted_variant_file_pks)} variant files with bulk delete")
                        # Get URLs before deleting from DB
                        variant_files_to_delete = list(ProductFile.objects.filter(pk__in=deleted_variant_file_pks))
                        cloudinary_urls_to_delete.extend([f.file_url for f in variant_files_to_delete if f.file_url])
                        
                        # Raw SQL delete - fastest
                        from django.db import connection
                        with connection.cursor() as cursor:
                            pks_str = ','.join(map(str, deleted_variant_file_pks))
                            cursor.execute(f"DELETE FROM marketing_productfile WHERE id IN ({pks_str})")
                        print(f"⏱️  TOTAL variant files deletion: {time.time() - delete_variant_start:.3f}s")
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing deleted_variant_files: {e}")
            
            context_start = time.time()
            context = self.get_context_data()
            print(f"⏱️  Get context: {time.time() - context_start:.3f}s")
            
            formset_start = time.time()
            self.save_product_files(self.object, context["productfile_formset"])
            print(f"⏱️  Save product files formset: {time.time() - formset_start:.3f}s")

            # Handle product attributes
            attr_start = time.time()
            self.handle_attributes(self.object)
            print(f"⏱️  Handle attributes: {time.time() - attr_start:.3f}s")

            variants_json = self.request.POST.get("variants_json", "[]")
            # Always process variants (needed for image changes)
            if variants_json and variants_json != "[]":
                self.handle_variants(self.object, variants_json)
            
            # AUTO-UPDATE PRIMARY IMAGE LOGIC:
            # If product has variants → primary_image = first variant's first image
            # If no variants → primary_image = product's first image (sequence=0)
            primary_update_start = time.time()
            first_variant = self.object.variants.order_by('id').first()
            
            if first_variant:
                # Has variants: Use first variant's first image
                first_variant_file = ProductFile.objects.filter(
                    product_variant=first_variant
                ).order_by('sequence', 'pk').first()
                
                if first_variant_file:
                    if self.object.primary_image_id != first_variant_file.pk:
                        self.object.primary_image = first_variant_file
                        self.object.save(update_fields=['primary_image'])
                        print(f"✓ Auto-updated primary_image to first variant's image (id={first_variant_file.pk})")
            else:
                # No variants: Use product's first image (sequence=0)
                first_product_file = ProductFile.objects.filter(
                    product=self.object,
                    product_variant__isnull=True
                ).order_by('sequence', 'pk').first()
                
                if first_product_file:
                    if self.object.primary_image_id != first_product_file.pk:
                        self.object.primary_image = first_product_file
                        self.object.save(update_fields=['primary_image'])
                        print(f"✓ Auto-updated primary_image to product's first image (id={first_product_file.pk})")
            
            print(f"⏱️  Primary image update: {time.time() - primary_update_start:.3f}s")
        
        redirect_start = time.time()
        response = super().form_valid(form)
        
        # Pass Cloudinary URLs to be deleted asynchronously after redirect
        if cloudinary_urls_to_delete:
            # Store in session for next page load to trigger cleanup
            self.request.session['cloudinary_cleanup_urls'] = cloudinary_urls_to_delete
            print(f"🗑️  Scheduled {len(cloudinary_urls_to_delete)} Cloudinary files for async deletion")
        
        print(f"⏱️  Redirect response: {time.time() - redirect_start:.3f}s")
        print(f"\n⏱️  TOTAL form_valid: {time.time() - form_valid_start:.3f}s\n")
        return response

    def form_invalid(self, form):
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


# ----------------------------------------------
# Product File Delete
# ----------------------------------------------
@method_decorator(csrf_protect, name="dispatch")
class ProductFileDelete(View):
    def post(self, request, *args, **kwargs):
        product_file_pk = request.POST.get("product_file_pk")
        if not product_file_pk:
            return HttpResponseBadRequest("Missing file ID")
        try:
            file = ProductFile.objects.get(pk=product_file_pk)
            file.delete()
            # return JsonResponse({"status": "ok"})
            # 204 means no content, but successfuly completed
            return HttpResponse("")  # HTMX will remove the element
        except ProductFile.DoesNotExist:
            return HttpResponseBadRequest("File not found")


# ----------------------------------------------
# Product Delete
# ----------------------------------------------
@method_decorator([login_required, csrf_protect], name="dispatch")
class ProductDelete(View):
    def post(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product, pk=pk)
        product_title = product.title
        product.delete()
        
        # Return JSON for AJAX requests
        if request.headers.get('Content-Type') == 'application/json' or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': f'Product "{product_title}" deleted successfully'})
        
        # Fallback to redirect for regular form submissions
        return redirect(reverse("marketing:product_list"))


# ----------------------------------------------
# API Views
# ----------------------------------------------
@require_http_methods(["POST"])
@login_required
def instant_upload_file(request):
    """
    Instant file upload - Upload to Cloudinary and save to DB immediately.
    Used for Shopify-style instant upload during product edit.
    Expects: multipart/form-data with 'file', 'product_id', and optional 'variant_id'
    """
    try:
        # Get file from request
        file = request.FILES.get('file')
        if not file:
            return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
        
        # Get product (required)
        product_id = request.POST.get('product_id')
        if not product_id:
            return JsonResponse({'success': False, 'error': 'No product_id provided'}, status=400)
        
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        
        # Get variant (optional)
        variant_id = request.POST.get('variant_id')
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(pk=variant_id)
            except ProductVariant.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Variant not found'}, status=404)
        
        # Upload to Cloudinary
        try:
            folder = f"media/product_images/product_{product.sku}"
            if variant:
                folder = f"{folder}/variant_{variant.variant_sku}"
            
            upload_result = cloudinary_upload(
                file,
                folder=folder,
                resource_type="image"
            )
            file_url = upload_result.get('secure_url')
            
            if not file_url:
                return JsonResponse({'success': False, 'error': 'Cloudinary upload failed'}, status=500)
            
        except CloudinaryError as e:
            return JsonResponse({'success': False, 'error': f'Cloudinary error: {str(e)}'}, status=500)
        
        # Get next sequence number
        if variant:
            max_seq = ProductFile.objects.filter(product_variant=variant).aggregate(models.Max('sequence'))['sequence__max'] or -1
        else:
            max_seq = ProductFile.objects.filter(product=product, product_variant__isnull=True).aggregate(models.Max('sequence'))['sequence__max'] or -1
        
        # Save to database
        product_file = ProductFile.objects.create(
            product=product,
            product_variant=variant,
            file_url=file_url,
            sequence=max_seq + 1,
            is_primary=False
        )
        
        # If uploading to a variant, always ensure product primary is first variant's first image
        if variant:
            # Get first variant (lowest ID = created first)
            first_variant = ProductVariant.objects.filter(product=product).order_by('id').first()
            if first_variant:
                # Get first image of first variant
                first_variant_file = ProductFile.objects.filter(
                    product_variant=first_variant
                ).order_by('sequence', 'pk').first()
                
                if first_variant_file:
                    # Always set first variant's first image as product primary
                    if product.primary_image_id != first_variant_file.pk:
                        product.primary_image = first_variant_file
                        product.save(update_fields=['primary_image'])
                        print(f"✓ Updated product primary to first variant's image {first_variant_file.pk}")
        
        return JsonResponse({
            'success': True,
            'file': {
                'id': product_file.pk,
                'url': file_url,
                'sequence': product_file.sequence,
                'is_primary': product_file.is_primary
            }
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def instant_delete_file(request):
    """
    Instant file delete - Delete from DB and Cloudinary immediately.
    Used for Shopify-style instant delete during product edit.
    Expects JSON: {"file_id": 123}
    """
    try:
        data = json.loads(request.body)
        file_id = data.get('file_id')
        
        if not file_id:
            return JsonResponse({'success': False, 'error': 'No file_id provided'}, status=400)
        
        try:
            product_file = ProductFile.objects.get(pk=file_id)
        except ProductFile.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'File not found'}, status=404)
        
        # Store product reference before deleting
        product = product_file.product
        was_variant_file = product_file.product_variant is not None
        
        # Delete (will also delete from Cloudinary via model's delete method)
        product_file.delete()
        
        # AUTO-UPDATE PRIMARY IMAGE after deletion
        if product:
            first_variant = product.variants.order_by('id').first()
            
            if first_variant:
                # Has variants: Use first variant's first image
                first_variant_file = ProductFile.objects.filter(
                    product_variant=first_variant
                ).order_by('sequence', 'pk').first()
                
                if first_variant_file and product.primary_image_id != first_variant_file.pk:
                    product.primary_image = first_variant_file
                    product.save(update_fields=['primary_image'])
                elif not first_variant_file:
                    # No variant images left, clear primary
                    product.primary_image = None
                    product.save(update_fields=['primary_image'])
            else:
                # No variants: Use product's first image
                first_product_file = ProductFile.objects.filter(
                    product=product,
                    product_variant__isnull=True
                ).order_by('sequence', 'pk').first()
                
                if first_product_file and product.primary_image_id != first_product_file.pk:
                    product.primary_image = first_product_file
                    product.save(update_fields=['primary_image'])
                elif not first_product_file:
                    # No images left, clear primary
                    product.primary_image = None
                    product.save(update_fields=['primary_image'])
        
        return JsonResponse({
            'success': True,
            'message': 'File deleted successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def instant_delete_variant(request):
    """
    Instant variant delete - Delete variant from DB immediately.
    Also deletes all associated files.
    Expects JSON: {"variant_id": 123} or {"variant_sku": "SKU123", "product_id": 456}
    """
    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
        variant_sku = data.get('variant_sku')
        product_id = data.get('product_id')
        
        # Try to find variant by ID first, then by SKU + product_id
        variant = None
        if variant_id:
            try:
                variant = ProductVariant.objects.get(pk=variant_id)
            except ProductVariant.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Variant not found'}, status=404)
        elif variant_sku and product_id:
            try:
                variant = ProductVariant.objects.get(variant_sku=variant_sku, product_id=product_id)
            except ProductVariant.DoesNotExist:
                return JsonResponse({'success': False, 'error': 'Variant not found'}, status=404)
        else:
            return JsonResponse({'success': False, 'error': 'variant_id or (variant_sku + product_id) required'}, status=400)
        
        # Delete variant (cascade will delete associated files)
        variant.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Variant deleted successfully'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def get_product_files(request):
    """
    Get ALL files for a product (SHARED POOL).
    Returns both product files and all variant files in a single unified list.
    Used by file manager modal to show all available files.
    Expects: GET param 'product_id'
    """
    try:
        product_id = request.GET.get('product_id')
        if not product_id:
            return JsonResponse({'success': False, 'error': 'No product_id provided'}, status=400)
        
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        
        # Get ALL files for this product (both product files and variant files)
        # This creates a SHARED POOL of all images
        files = ProductFile.objects.filter(
            product=product
        ).select_related('product_variant').order_by('sequence', 'pk')
        
        file_list = []
        for f in files:
            # Add metadata about which variant this file belongs to
            variant_info = None
            if f.product_variant:
                variant_info = {
                    'id': f.product_variant.pk,
                    'sku': f.product_variant.variant_sku
                }
            
            file_list.append({
                'id': f.pk,
                'url': f.optimized_url,
                'name': f.file_url.split('/')[-1],
                'is_primary': f.is_primary,
                'sequence': f.sequence,
                'variant': variant_info  # NEW: Shows which variant owns this file (if any)
            })
        
        return JsonResponse({
            'success': True,
            'files': file_list
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def get_variant_files(request):
    """
    Get all files for a variant.
    Used by file manager modal to show existing variant files.
    Expects: GET params 'product_id' and 'variant_id'
    """
    try:
        product_id = request.GET.get('product_id')
        variant_id = request.GET.get('variant_id')
        
        if not product_id or not variant_id:
            return JsonResponse({'success': False, 'error': 'product_id and variant_id required'}, status=400)
        
        try:
            variant = ProductVariant.objects.get(pk=variant_id, product_id=product_id)
        except ProductVariant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Variant not found'}, status=404)
        
        # Get all variant files
        files = ProductFile.objects.filter(
            product_variant=variant
        ).order_by('sequence')
        
        file_list = []
        for f in files:
            file_list.append({
                'id': f.pk,
                'url': f.optimized_url,
                'name': f.file_url.split('/')[-1],
                'is_primary': f.is_primary,
                'sequence': f.sequence
            })
        
        return JsonResponse({
            'success': True,
            'files': file_list
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def link_files_to_variant(request):
    """
    Link existing product files to a variant.
    Used when variant images are selected in the image picker.
    Expects JSON: {"variant_id": 123, "file_ids": [1, 2, 3]}
    """
    try:
        data = json.loads(request.body)
        variant_id = data.get('variant_id')
        file_ids = data.get('file_ids', [])
        
        if not variant_id or not file_ids:
            return JsonResponse({'success': False, 'error': 'variant_id and file_ids required'}, status=400)
        
        try:
            variant = ProductVariant.objects.get(pk=variant_id)
        except ProductVariant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Variant not found'}, status=404)
        
        # Update files to link them to variant
        updated_count = 0
        for file_id in file_ids:
            try:
                product_file = ProductFile.objects.get(pk=file_id, product=variant.product)
                # Only update if not already linked to this variant
                if product_file.product_variant != variant:
                    product_file.product_variant = variant
                    product_file.save()
                    updated_count += 1
            except ProductFile.DoesNotExist:
                continue
        
        return JsonResponse({
            'success': True,
            'message': f'{updated_count} file(s) linked to variant'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def async_delete_cloudinary_files(request):
    """
    AJAX endpoint to delete files from Cloudinary in background.
    Called after page redirect to not block user.
    Expects JSON: {"file_urls": ["url1", "url2", ...]}
    """
    try:
        data = json.loads(request.body)
        file_urls = data.get('file_urls', [])
        
        if not file_urls:
            return JsonResponse({'success': True, 'message': 'No files to delete'})
        
        deleted_count = 0
        errors = []
        
        for file_url in file_urls:
            if file_url:
                # Extract public_id from Cloudinary URL
                import re
                match = re.search(r"/upload/(?:v\d+/)?([^\.]+)", file_url)
                if match:
                    public_id = match.group(1)
                    try:
                        from cloudinary.uploader import destroy as cloudinary_destroy
                        cloudinary_destroy(public_id)
                        deleted_count += 1
                    except Exception as e:
                        errors.append(f"Failed to delete {public_id}: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'deleted': deleted_count,
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def temp_upload_file(request):
    """
    Temporary file upload for product creation (before product_id exists).
    Uploads to Cloudinary and stores URLs in session.
    Returns: {success: true, file_data: {url, public_id, name, sequence}}
    """
    try:
        if 'file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)
        
        file = request.FILES['file']
        file_type = request.POST.get('file_type', 'main_image')  # 'main_image' or 'variant_image'
        variant_temp_id = request.POST.get('variant_temp_id')  # Only for variant images
        sequence = int(request.POST.get('sequence', 0))
        
        # Upload to Cloudinary in a temporary folder
        folder = f"media/temp_product_files/{request.user.username}_{int(time.time())}"
        upload_result = cloudinary_upload(file, folder=folder, resource_type="image")
        
        file_url = upload_result.get('secure_url')
        public_id = upload_result.get('public_id')
        
        if not file_url or not public_id:
            return JsonResponse({'success': False, 'error': 'Upload failed'}, status=500)
        
        # Store in session
        if 'temp_product_files' not in request.session:
            request.session['temp_product_files'] = {'main_images': [], 'variant_images': {}}
        
        file_data = {
            'url': file_url,
            'public_id': public_id,
            'name': file.name,
            'sequence': sequence
        }
        
        if file_type == 'main_image':
            request.session['temp_product_files']['main_images'].append(file_data)
        elif file_type == 'variant_image' and variant_temp_id:
            if variant_temp_id not in request.session['temp_product_files']['variant_images']:
                request.session['temp_product_files']['variant_images'][variant_temp_id] = []
            request.session['temp_product_files']['variant_images'][variant_temp_id].append(file_data)
        
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'file_data': file_data
        })
        
    except CloudinaryError as e:
        return JsonResponse({'success': False, 'error': f'Cloudinary error: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def cleanup_temp_files(request):
    """
    Cleanup temporary files from Cloudinary and session.
    Called when user leaves product creation page without saving.
    """
    try:
        temp_files = request.session.get('temp_product_files', {})
        
        if not temp_files:
            return JsonResponse({'success': True, 'message': 'No temp files to clean up'})
        
        deleted_count = 0
        errors = []
        
        # Delete main images
        for file_data in temp_files.get('main_images', []):
            public_id = file_data.get('public_id')
            if public_id:
                try:
                    from cloudinary.uploader import destroy as cloudinary_destroy
                    cloudinary_destroy(public_id)
                    deleted_count += 1
                except Exception as e:
                    errors.append(f"Failed to delete {public_id}: {str(e)}")
        
        # Delete variant images
        for variant_id, files in temp_files.get('variant_images', {}).items():
            for file_data in files:
                public_id = file_data.get('public_id')
                if public_id:
                    try:
                        from cloudinary.uploader import destroy as cloudinary_destroy
                        cloudinary_destroy(public_id)
                        deleted_count += 1
                    except Exception as e:
                        errors.append(f"Failed to delete {public_id}: {str(e)}")
        
        # Clear session
        del request.session['temp_product_files']
        request.session.modified = True
        
        return JsonResponse({
            'success': True,
            'deleted': deleted_count,
            'errors': errors
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["POST"])
@login_required
def save_product_attributes(request):
    """
    HTMX endpoint to save product attributes instantly.
    Expects JSON: {"product_id": 123, "attributes": [{"name": "...", "value": "..."}, ...]}
    Returns updated attributes list as JSON for frontend sync.
    """
    from marketing.models import ProductAttribute
    
    try:
        data = json.loads(request.body)
        product_id = data.get('product_id')
        attributes = data.get('attributes', [])
        
        if not product_id:
            return JsonResponse({'success': False, 'error': 'Missing product_id'}, status=400)
        
        # Get product
        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        
        # Delete all existing attributes
        product.attributes.all().delete()
        
        # Create new attributes
        created_attrs = []
        for idx, attr_data in enumerate(attributes):
            name = attr_data.get('name', '').strip()
            value = attr_data.get('value', '').strip()
            if name and value:
                attr = ProductAttribute.objects.create(
                    product=product,
                    name=name,
                    value=value,
                    sequence=idx
                )
                created_attrs.append({'id': attr.id, 'name': attr.name, 'value': attr.value})
        
        return JsonResponse({
            'success': True,
            'attributes': created_attrs,
            'message': f'Saved {len(created_attrs)} attributes'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@require_http_methods(["GET"])
@login_required
def get_product_attributes(request):
    """
    Get product attributes as JSON.
    Used by variant attributes modal to fetch latest attributes.
    """
    from marketing.models import ProductAttribute
    
    product_id = request.GET.get('product_id')
    
    if not product_id:
        return JsonResponse({'success': False, 'error': 'Missing product_id'}, status=400)
    
    try:
        product = Product.objects.get(pk=product_id)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
    
    attributes = list(product.attributes.all().order_by('sequence').values('id', 'name', 'value'))
    
    return JsonResponse({
        'success': True,
        'attributes': attributes
    })


@require_http_methods(["POST"])
@login_required
def update_variant_image_order(request):
    """
    Lightweight AJAX endpoint to update variant image order without full form processing.
    Expects JSON: {"variant_sku": "SKU123", "images": [{"id": 1, "sequence": 0}, ...]}
    """
    import time
    start = time.time()
    
    try:
        data = json.loads(request.body)
        variant_sku = data.get('variant_sku')
        images = data.get('images', [])
        
        if not variant_sku or not images:
            return JsonResponse({'success': False, 'error': 'Missing variant_sku or images'}, status=400)
        
        # Get variant
        try:
            variant = ProductVariant.objects.get(variant_sku=variant_sku)
        except ProductVariant.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Variant not found'}, status=404)
        
        # Bulk update image sequences
        images_to_update = []
        for img_data in images:
            img_id = img_data.get('id')
            sequence = img_data.get('sequence', 0)
            
            if img_id:
                try:
                    img = ProductFile.objects.get(pk=img_id, product_variant=variant)
                    img.sequence = sequence
                    img.is_primary = (sequence == 0)
                    images_to_update.append(img)
                except ProductFile.DoesNotExist:
                    pass
        
        if images_to_update:
            ProductFile.objects.bulk_update(images_to_update, ['sequence', 'is_primary'])
        
        elapsed = time.time() - start
        return JsonResponse({
            'success': True, 
            'updated': len(images_to_update),
            'time': f'{elapsed:.3f}s'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def get_product_categories(request):
    categories = ProductCategory.objects.all()
    data = [
        {"pk": category.pk, "name": category.name, "image_url": category.image_url, "description": category.description}
        for category in categories
    ]
    return JsonResponse(data, safe=False)


# def get_products(request):
#     product_category = request.GET.get("product_category")
#     # do not show unfeatured products, or products with no primary image
#     # products = Product.objects.filter(featured=True, primary_image__isnull=False)
#     products = Product.objects.filter(featured=True)
#     if product_category:
#         products = products.filter(category__name=product_category.lower())

#     data = [
#         {
#             "id": p.id,
#             "title": p.title,
#             "sku": p.sku,
#             "price": p.price,
#             "primary_image": p.primary_image.file_url if p.primary_image else None,
#         }
#         for p in products
#     ]
#     return JsonResponse(
#         data, safe=False
#     )  # by False, “Yes, I know it’s a list, and I’m okay with returning it as JSON.”


# def get_products(request):
#     start = time.time()
#     product_category = request.GET.get("product_category", None)
#     # print("product_category filter is:", product_category)
#     products = Product.objects.filter(featured=True)
#     if product_category:
#         products = products.filter(
#             category__name=str(product_category).strip().lower().replace(" ", "_")
#         )

#     # Optimize queries
#     products = products.select_related("primary_image", "category").prefetch_related(
#         "files", "variants"
#     )
#     # data = []
#     # attribute_values = []

#     # for product in products:
#     #     data.append(
#     #         {
#     #             "pk": product.pk,
#     #             "title": product.title,
#     #             "sku": product.sku,
#     #             "price": product.price,
#     #             "primary_image": (
#     #                 product.primary_image.file_url if product.primary_image else None
#     #             ),
#     #         }
#     #     )
#     #     for variant in product.variants.all():
#     #         print(variant)
#     #         for attr_value in variant.product_variant_attribute_values.all():
#     #             print("attr_value:", attr_value)
#     #             attribute_values.append(attr_value)
#     # attribute_values = list(set(attribute_values))  # unique values only
#     # print(
#     #     "time to prepare data and attribute values:", time.time() - start
#     # )  # 0.001 sec for 6 products
#     # print("you have this many unique attribute values:", len(attribute_values)) # 11 for 6 products

#     data = [
#         {
#             "pk": product.pk,
#             "title": product.title,
#             "sku": product.sku,
#             "price": product.price,
#             "primary_image": (
#                 product.primary_image.file_url if product.primary_image else None
#             ),
#         }
#         for product in products
#     ]
#     # product_variant_attributes = ProductVariantAttribute.objects.all().prefetch_related(
#     # Optimize: select_related for product in variants
#     product_variants = ProductVariant.objects.filter(
#         product__in=products
#     ).select_related("product")
#     print(len(product_variants), "variants found for these products")
#     variant_ids = list(product_variants.values_list("id", flat=True))
#     print("variant ids are:", variant_ids)
#     # Optimize: select_related for product_variant in attribute values
#     product_variant_attribute_values = ProductVariantAttributeValue.objects.filter(
#         variants__in=product_variants
#     ).prefetch_related("variants", "product_variant_attribute")

#     # product_variant_attribute_values = []
#     # for variant in product_variants:
#     #     pva_values = variant.product_variant_attribute_values.select_related(
#     #         "product_variant_attribute"
#     #     ).all()
#     #     product_variant_attribute_values.extend(pva_values)

#     print(
#         "here comes product_variant_attribute_values", product_variant_attribute_values
#     )

#     # 3. Get all unique attributes used by these variants
#     attribute_ids = product_variant_attribute_values.values_list(
#         "product_variant_attribute_id", flat=True
#     ).distinct()
#     product_variant_attributes = ProductVariantAttribute.objects.filter(
#         id__in=attribute_ids
#     )
#     print("get", product_variant_attributes)

#     return JsonResponse(data, safe=False)


# This is just to try if I can make api calls from my next js application, and it works.
def get_products(request):
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type"
        return response
    
    start = time.time()
    product_category = request.GET.get("product_category", None)

    if product_category:
        try:
            category = ProductCategory.objects.get(name=product_category)
        except ProductCategory.DoesNotExist:
            return JsonResponse(
                {"message": f"The {product_category} category does not exist."},
                status=404,
            )
        products = Product.objects.filter(category=category, featured=True)
    else:
        products = Product.objects.filter(featured=True)

    # Dynamic Attribute Filtering
    # Iterate over GET parameters to find attribute filters
    for key, value in request.GET.items():
        # Skip reserved keys that are not attributes
        if key in ['product_category', 'page', 'limit', 'sort', 'search']:
            continue
            
        # Filter products where ANY variant has the specified attribute value
        # We use iexact for case-insensitive matching
        if value and value.strip():
            print(f"🔍 Filtering by {key}={value}")
            from django.db.models import Q
            
            # Debug: Check if any product has this attribute
            has_attr = Product.objects.filter(attributes__name__iexact=key, attributes__value__iexact=value).exists()
            print(f"   - ProductAttribute match exists? {has_attr}")
            
            has_variant_attr = Product.objects.filter(
                variants__product_variant_attribute_values__product_variant_attribute__name__iexact=key,
                variants__product_variant_attribute_values__product_variant_attribute_value__iexact=value
            ).exists()
            print(f"   - VariantAttribute match exists? {has_variant_attr}")

            products = products.filter(
                Q(variants__product_variant_attribute_values__product_variant_attribute__name__iexact=key,
                  variants__product_variant_attribute_values__product_variant_attribute_value__iexact=value) |
                Q(attributes__name__iexact=key,
                  attributes__value__iexact=value)
            ).distinct()
            print(f"   - Products count after filter: {products.count()}")

    # Optimize: prefetch all related data in a single query chain
    products = products.select_related("primary_image", "category").prefetch_related(
        'variants',
        'variants__product_variant_attribute_values',
        'variants__product_variant_attribute_values__product_variant_attribute'
    )

    # Convert to list to execute query once
    products_list = list(products)
    
    # Collect variants from prefetched data
    product_variants = []
    for product in products_list:
        product_variants.extend(product.variants.all())
    
    # Collect attribute values from prefetched data
    product_variant_attribute_values_set = set()
    attributes_map = {}
    for variant in product_variants:
        for av in variant.product_variant_attribute_values.all():
            product_variant_attribute_values_set.add(av)
            if av.product_variant_attribute_id not in attributes_map:
                attributes_map[av.product_variant_attribute_id] = av.product_variant_attribute

    # Build products data from already fetched list
    products_data = [
        {
            "id": p.id,
            "title": p.title,
            "sku": p.sku,
            "price": p.price,
            "primary_image": p.primary_image.file_url if p.primary_image else None,
        }
        for p in products_list
    ]

    # Build variant data from collected variants (already prefetched)
    product_variants_data = [
        {
            "id": v.id,
            "product_id": v.product_id,
            "variant_sku": v.variant_sku,
            "variant_price": v.variant_price,
            "variant_quantity": v.variant_quantity,
            "product_variant_attribute_values": [
                av.id for av in v.product_variant_attribute_values.all()
            ],
        }
        for v in product_variants
    ]

    # Build attributes data from collected map
    product_variant_attributes_data = [
        {
            "id": a.id,
            "name": a.name,
        }
        for a in attributes_map.values()
    ]

    # Build attribute values from collected set
    product_variant_attribute_values_data = [
        {
            "id": av.id,
            "product_variant_attribute_id": av.product_variant_attribute_id,
            "product_variant_attribute_value": av.product_variant_attribute_value,
        }
        for av in product_variant_attribute_values_set
    ]

    end = time.time()
    print(f"Time taken to get products: {end - start} seconds")

    response = JsonResponse(
        {
            "products": products_data,
            "product_variants": product_variants_data,
            "product_variant_attributes": product_variant_attributes_data,
            "product_variant_attribute_values": product_variant_attribute_values_data,
            "product_category": category.name if product_category else None,
            "product_category_description": category.description if category.description else None,
        }
    )
    response["Access-Control-Allow-Origin"] = "*"
    return response


# def get_product(request):
#     sku = request.GET.get("product_sku")
#     product = get_object_or_404(Product, sku=sku, featured=True)

#     product_files = [
#         {"id": f.id, "file_url": f.file_url, "variant_id": f.product_variant_id}
#         for f in product.files.all()
#     ]

#     variants = []
#     for v in product.variants.all():
#         variants.append(
#             {
#                 "id": v.id,
#                 "sku": v.variant_sku,
#                 "price": v.variant_price,
#                 "quantity": v.variant_quantity,
#                 "attributes": [
#                     {
#                         "name": attr.product_variant_attribute.name,
#                         "value": attr.product_variant_attribute_value,
#                     }
#                     for attr in v.product_variant_attribute_values.all()
#                 ],
#             }
#         )

#     return JsonResponse(
#         {
#             "product": {
#                 "id": product.id,
#                 "title": product.title,
#                 "sku": product.sku,
#                 "price": product.price,
#                 "files": product_files,
#                 "variants": variants,
#             }
#         }
#     )


# ------------------------------------------------------------------------------------------------
def get_product(request):
    product_sku = request.GET.get("product_sku", None)
    try:
        # Optimize: prefetch all related data in one query
        product = Product.objects.select_related(
            'category',
            'primary_image',
            'supplier'
        ).prefetch_related(
            models.Prefetch('files', queryset=ProductFile.objects.order_by('sequence', 'pk')),
            'attributes',  # Product-level attributes
            'variants',
            models.Prefetch('variants__files', queryset=ProductFile.objects.order_by('sequence', 'pk')),
            'variants__attributes',  # Variant-level attributes
            'variants__product_variant_attribute_values',
            'variants__product_variant_attribute_values__product_variant_attribute'
        ).get(sku=product_sku, featured=True)
    except Product.DoesNotExist:
        return JsonResponse({"error": "Product not found"}, status=404)

    product_category = product.category.name if product.category else None

    # Product fields for Product_API
    product_fields = {
        "id": product.id,
        "pk": product.pk,
        "created_at": product.created_at,
        "title": product.title,
        "description": product.description,
        "sku": product.sku,
        "barcode": product.barcode,
        "tags": product.tags,
        "type": product.type,
        "unit_of_measurement": product.unit_of_measurement,
        "quantity": product.quantity,
        "price": product.price,
        "featured": product.featured,
        "selling_while_out_of_stock": product.selling_while_out_of_stock,
        "weight": product.weight,
        "unit_of_weight": product.unit_of_weight,
        "category_id": product.category_id,
        "supplier_id": product.supplier_id,
        # "has_variants": product.has_variants,  # REMOVE THIS LINE
        # "has_variants": product.variants.exists(),  # ADD THIS LINE
        "datasheet_url": product.datasheet_url,
        "minimum_inventory_level": getattr(product, "minimum_inventory_level", None),
        "primary_image": (
            product.primary_image.file_url
            if getattr(product, "primary_image", None)
            else None
        ),
    }

    # product_api = {
    #     "model": "Product",
    #     "pk": product.pk,
    #     "fields": product_fields,
    # }

    # All product files (main and variant) - already ordered by sequence in prefetch
    product_files = [
        {
            "id": pf.id,
            "file": pf.file_url,
            "product_id": pf.product_id,
            "product_variant_id": pf.product_variant_id,
            "sequence": pf.sequence,
            "is_primary": pf.is_primary,
        }
        for pf in product.files.all()
    ]

    # Variants (already prefetched)
    variants = product.variants.all()
    variants_data = []
    for variant in variants:
        # Find primary image for variant (first by sequence) - already ordered in prefetch
        variant_files = list(variant.files.all())
        variant_primary_file = variant_files[0] if variant_files else None
        
        # Get attribute value pks (already prefetched)
        product_variant_attribute_values_pk_list = [
            av.pk for av in variant.product_variant_attribute_values.all()
        ]
        
        variants_data.append(
            {
                "id": variant.id,
                "variant_sku": variant.variant_sku,
                "variant_barcode": variant.variant_barcode,
                "variant_quantity": variant.variant_quantity,
                "variant_price": variant.variant_price,
                "variant_cost": getattr(variant, "variant_cost", None),
                "variant_featured": variant.variant_featured,
                "product_id": variant.product_id,
                "primary_image": (
                    variant_primary_file.file_url if variant_primary_file else None
                ),
                "product_variant_attribute_values": product_variant_attribute_values_pk_list,
            }
        )

    # Attribute values - collect from already prefetched data
    attribute_values_set = set()
    attributes_map = {}
    
    for variant in variants:
        for av in variant.product_variant_attribute_values.all():
            attribute_values_set.add(av)
            # Also collect unique attributes
            if av.product_variant_attribute_id not in attributes_map:
                attributes_map[av.product_variant_attribute_id] = av.product_variant_attribute
    
    attribute_values_data = [
        {
            "id": av.id,
            "product_variant_attribute_value": av.product_variant_attribute_value,
            "product_variant_attribute_id": av.product_variant_attribute_id,
        }
        for av in attribute_values_set
    ]

    # Attributes - from already collected map
    attributes_data = [
        {
            "id": attr.id,
            "name": attr.name,
        }
        for attr in attributes_map.values()
    ]
    
    # Product-level attributes (ProductAttribute model)
    product_attributes_data = [
        {
            "id": attr.id,
            "name": attr.name,
            "value": attr.value,
            "sequence": attr.sequence,
        }
        for attr in product.attributes.all()
    ]
    
    # Variant-level attributes (ProductAttribute model for variants)
    variant_attributes_data = []
    for variant in variants:
        for attr in variant.attributes.all():
            variant_attributes_data.append({
                "id": attr.id,
                "variant_id": variant.id,
                "name": attr.name,
                "value": attr.value,
                "sequence": attr.sequence,
            })
    
    # print("here comes the response")
    # print(product_files)
    # print(
    #     {
    #         "product_category": product_category,
    #         "product": product_fields,
    #         "product_variants": variants_data,
    #         "product_files": product_files,
    #         "product_variant_attributes": attributes_data,
    #         "product_variant_attribute_values": attribute_values_data,
    #     }
    # )

    return JsonResponse(
        {
            "product_category": product_category,
            "product": product_fields,
            "product_variants": variants_data,
            "product_files": product_files,
            "product_variant_attributes": attributes_data,
            "product_variant_attribute_values": attribute_values_data,
            "product_attributes": product_attributes_data,  # Product-level attributes
            "variant_attributes": variant_attributes_data,  # Variant-level attributes
        }
    )
