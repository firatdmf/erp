"""Alt text for a blog post's cover and hero images.

The post holds each image as a bare URL, and the website fell back on the
post's title to describe both. The description lives on a BlogFile row —
one per post and image type — so the blog form can ask for it and the
post API can hand it to the website. A post without one still gets its
title as alt text there.
"""
from .models import BlogFile

IMAGE_TYPES = ("cover", "hero")


def image_alts(post):
    """{"cover": text, "hero": text}; reads `post.files`, so prefetch it
    when asking for many posts."""
    alts = dict.fromkeys(IMAGE_TYPES, "")
    for file in post.files.all():
        if file.file_type in alts and file.alt_text:
            alts[file.file_type] = file.alt_text
    return alts


def save_image_alts(post, data):
    """Store the `cover_image_alt` / `hero_image_alt` a form posted."""
    for image_type in IMAGE_TYPES:
        text = (data.get(f"{image_type}_image_alt") or "").strip()[:255]
        rows = BlogFile.objects.filter(blog_post=post, file_type=image_type)
        if not text:
            # A queryset delete: the row goes, the image on the CDN stays.
            rows.delete()
            continue
        url = getattr(post, f"{image_type}_image")
        if not rows.update(file_url=url, alt_text=text):
            BlogFile.objects.create(
                blog_post=post, file_type=image_type, file_url=url, alt_text=text,
            )
