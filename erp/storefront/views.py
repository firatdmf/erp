"""
ERP içindeki "Mağazam" yönetim sayfaları. Belino site içeriğini buradan
düzenliyoruz; storefront/api.py public API'i sağlıyor.
"""
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse

from .models import (
    Storefront, NavMenu, HomeSection, HomeSectionCard,
    HomeSectionProduct, TrustBadge,
)
from .forms import (
    NavMenuForm, HomeSectionForm,
    HomeSectionCardFormSet, HomeSectionProductFormSet, TrustBadgeFormSet,
)


def _upload_image_to_bunny(uploaded_file, folder: str) -> str:
    """
    Bunny CDN'e yükle. Marketing app'inin bunny_storage helper'ını
    kullanıyoruz; başarısız olursa boş string döner ve form bunu
    sessizce yutup mevcut URL'yi korur (yükleme zorunlu değil).
    """
    if not uploaded_file:
        return ""
    try:
        from marketing.utils.bunny_storage import upload_to_bunny
    except Exception:
        return ""
    safe_name = uploaded_file.name.replace(" ", "_")
    path = f"media/storefront/{folder}/{safe_name}"
    try:
        return upload_to_bunny(uploaded_file, path) or ""
    except Exception:
        return ""


def _active_storefront():
    """
    Bu kurulumdaki aktif storefront. Şimdilik DB_SCHEMA'yı key olarak
    kullanıyoruz: BELINO → 'belino'. İlk çalıştırmada mevcut yoksa
    seed data migration zaten oluşturmuştur.
    """
    schema = getattr(settings, "DB_SCHEMA", "public")
    key = (schema or "public").lower()
    if key == "public":
        key = "demfirat"
    sf, _ = Storefront.objects.get_or_create(
        key=key,
        defaults={"name": key.title(), "is_active": True},
    )
    return sf


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    sf = _active_storefront()
    # "Son güncelleme" — herhangi bir storefront tablosundaki en yeni
    # save'i göster. Tek source-of-truth yok çünkü değişiklik Storefront,
    # NavMenu, HomeSection üçünden birinde olabilir.
    from django.db.models import Max
    nav_last = NavMenu.objects.filter(storefront=sf).order_by("-id").first()
    home_last = HomeSection.objects.filter(storefront=sf).order_by("-id").first()
    last_changed = sf.updated_at
    return render(request, "storefront/dashboard.html", {
        "storefront": sf,
        "nav_count": NavMenu.objects.filter(storefront=sf, parent__isnull=True).count(),
        "home_count": HomeSection.objects.filter(storefront=sf).count(),
        "last_changed": last_changed,
    })


# ---------------------------------------------------------------------------
# Home (anasayfa bölümleri)
# ---------------------------------------------------------------------------
@login_required
def edit_home(request):
    sf = _active_storefront()
    sections = HomeSection.objects.filter(storefront=sf).order_by("order", "id")
    return render(request, "storefront/home_list.html", {
        "storefront": sf,
        "sections": sections,
        "kind_choices": HomeSection.KIND_CHOICES,
    })


@login_required
def jump_home_section(request, kind: str):
    """Visual editor: Belino iframe'i bir section'a tıkladığında, ERP
    bu URL'ye gelir, ilgili kind'a karşılık gelen section'ı bulur ve
    onun edit sayfasına yönlendirir."""
    sf = _active_storefront()
    section = (
        HomeSection.objects.filter(storefront=sf, kind=kind)
        .order_by("order", "id")
        .first()
    )
    if section is None:
        return redirect("storefront:edit_home")
    return redirect("storefront:edit_home_section", pk=section.pk)


@login_required
def create_home_section(request):
    sf = _active_storefront()
    if request.method == "POST":
        form = HomeSectionForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.storefront = sf
            uploaded = form.cleaned_data.get("image_upload")
            if uploaded:
                url = _upload_image_to_bunny(uploaded, f"home/{sf.key}")
                if url:
                    obj.image_url = url
            obj.save()
            messages.success(request, f"{obj} eklendi.")
            return redirect("storefront:edit_home_section", pk=obj.pk)
    else:
        form = HomeSectionForm(initial={"kind": request.GET.get("kind", HomeSection.KIND_FEATURED)})
    return render(request, "storefront/home_section_form.html", {
        "storefront": sf, "form": form, "is_create": True,
    })


@login_required
def edit_home_section(request, pk: int):
    sf = _active_storefront()
    section = get_object_or_404(HomeSection, pk=pk, storefront=sf)

    # İlgili kind'a göre uygun formset
    formset_classes = {
        HomeSection.KIND_SEASONS: ("cards", HomeSectionCardFormSet),
        HomeSection.KIND_FEATURED: ("featured_products", HomeSectionProductFormSet),
        HomeSection.KIND_TRUST: ("badges", TrustBadgeFormSet),
    }
    formset_attr, FormsetClass = formset_classes.get(section.kind, (None, None))

    if request.method == "POST":
        form = HomeSectionForm(request.POST, request.FILES, instance=section)
        formset = FormsetClass(request.POST, instance=section) if FormsetClass else None
        valid = form.is_valid() and (formset is None or formset.is_valid())
        if valid:
            obj = form.save(commit=False)
            uploaded = form.cleaned_data.get("image_upload")
            if uploaded:
                url = _upload_image_to_bunny(uploaded, f"home/{sf.key}")
                if url:
                    obj.image_url = url
            obj.save()
            if formset is not None:
                formset.save()
            messages.success(request, "Kaydedildi.")
            return redirect("storefront:edit_home_section", pk=section.pk)
    else:
        form = HomeSectionForm(instance=section)
        formset = FormsetClass(instance=section) if FormsetClass else None

    # Anasayfa bölümleri Belino anasayfasında render olur — preview = /
    base = (settings.STOREFRONT_PREVIEW_URL or "").rstrip("/")
    iframe_src = f"{base}/?edit=1"

    return render(request, "storefront/home_section_form.html", {
        "storefront": sf, "section": section, "form": form, "formset": formset,
        "formset_attr": formset_attr, "is_create": False,
        "iframe_src": iframe_src,
        "lock_page": True,
    })


@login_required
def delete_home_section(request, pk: int):
    sf = _active_storefront()
    section = get_object_or_404(HomeSection, pk=pk, storefront=sf)
    if request.method == "POST":
        section.delete()
        messages.success(request, "Bölüm silindi.")
        return redirect("storefront:edit_home")
    return render(request, "storefront/confirm_delete.html", {
        "storefront": sf, "object": section,
        "back_url": reverse("storefront:edit_home"),
    })


# ---------------------------------------------------------------------------
# Menu (header navigasyonu)
# ---------------------------------------------------------------------------
@login_required
def edit_menu(request):
    sf = _active_storefront()
    top_items = (
        NavMenu.objects.filter(storefront=sf, parent__isnull=True)
        .order_by("order", "id")
        .prefetch_related("children")
    )
    return render(request, "storefront/menu_list.html", {
        "storefront": sf, "items": top_items,
    })


@login_required
def create_menu_item(request):
    sf = _active_storefront()
    if request.method == "POST":
        form = NavMenuForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.storefront = sf
            uploaded = form.cleaned_data.get("image_upload")
            if uploaded:
                url = _upload_image_to_bunny(uploaded, f"menu/{sf.key}")
                if url:
                    obj.feature_image_url = url
            obj.save()
            messages.success(request, "Menü öğesi eklendi.")
            return redirect("storefront:edit_menu")
    else:
        parent_id = request.GET.get("parent")
        initial = {}
        if parent_id:
            try:
                initial["parent"] = NavMenu.objects.get(pk=parent_id, storefront=sf)
            except NavMenu.DoesNotExist:
                pass
        form = NavMenuForm(initial=initial)
        # Parent dropdown'u sadece bu storefront'la sınırla
        form.fields["parent"].queryset = NavMenu.objects.filter(storefront=sf, parent__isnull=True)
    return render(request, "storefront/menu_item_form.html", {
        "storefront": sf, "form": form, "is_create": True,
    })


@login_required
def edit_menu_item(request, pk: int):
    sf = _active_storefront()
    item = get_object_or_404(NavMenu, pk=pk, storefront=sf)
    if request.method == "POST":
        form = NavMenuForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save(commit=False)
            uploaded = form.cleaned_data.get("image_upload")
            if uploaded:
                url = _upload_image_to_bunny(uploaded, f"menu/{sf.key}")
                if url:
                    obj.feature_image_url = url
            obj.save()
            messages.success(request, "Kaydedildi.")
            return redirect("storefront:edit_menu")
    else:
        form = NavMenuForm(instance=item)
    form.fields["parent"].queryset = NavMenu.objects.filter(
        storefront=sf, parent__isnull=True
    ).exclude(pk=item.pk)
    # Önizleme URL'i — bu nav item kullanıcıyı hangi sayfaya götürüyorsa
    # (örn. /products?cat=cocuk-corap) iframe oraya açılsın.
    base = (settings.STOREFRONT_PREVIEW_URL or "").rstrip("/")
    href = (item.href or "").lstrip("/")
    target = f"{base}/{href}" if href else f"{base}/"
    sep = "&" if "?" in target else "?"
    iframe_src = f"{target}{sep}edit=1"
    return render(request, "storefront/menu_item_form.html", {
        "storefront": sf, "form": form, "item": item, "is_create": False,
        "iframe_src": iframe_src,
        "lock_page": True,
    })


@login_required
def delete_menu_item(request, pk: int):
    sf = _active_storefront()
    item = get_object_or_404(NavMenu, pk=pk, storefront=sf)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Menü öğesi silindi.")
        return redirect("storefront:edit_menu")
    return render(request, "storefront/confirm_delete.html", {
        "storefront": sf, "object": item,
        "back_url": reverse("storefront:edit_menu"),
    })
