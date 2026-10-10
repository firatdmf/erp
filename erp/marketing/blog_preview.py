"""A draft blog post can be read on the website through a signed link.

The website only ever asks for published posts, so a draft could not be
seen in its real layout until it was live. A preview link carries a token
signed for that one post; the post API answers a draft when the token
checks out, and the blog pages in the ERP hand the link to whoever is
editing. The token is signed, not stored, and stops working after
PREVIEW_MAX_AGE — the blog pages mint a fresh one each time they load.
"""
from datetime import timedelta

from django.conf import settings
from django.core import signing

PREVIEW_SALT = "marketing.blog-preview"
PREVIEW_MAX_AGE = timedelta(days=7)
PREVIEW_PARAM = "preview"

# The languages the website serves. English is its default and carries no
# prefix; a post's Polish text is stored but has no page yet.
SITE_LANGUAGES = ("en", "tr", "ru")
SITE_DEFAULT_LANGUAGE = "en"


def preview_token(post):
    return signing.dumps(post.pk, salt=PREVIEW_SALT)


def opens_preview(post, token):
    """Is `token` a live preview token for this very post?"""
    if not token:
        return False
    try:
        pk = signing.loads(token, salt=PREVIEW_SALT, max_age=PREVIEW_MAX_AGE)
    except signing.BadSignature:
        return False
    return pk == post.pk


def site_links(post):
    """[(language, url)] for each language the website serves that the
    post is written in. A published post gets its public address, a draft
    its preview link."""
    base = getattr(settings, "STOREFRONT_URL", "https://www.demfirat.com").rstrip("/")
    query = "" if post.is_published else f"?{PREVIEW_PARAM}={preview_token(post)}"
    links = []
    for language in SITE_LANGUAGES:
        if not getattr(post, f"content_{language}"):
            continue
        prefix = "" if language == SITE_DEFAULT_LANGUAGE else f"/{language}"
        links.append((language, f"{base}{prefix}/blog/{post.slug}{query}"))
    return links
