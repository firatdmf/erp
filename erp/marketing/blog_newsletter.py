"""Tell the newsletter when a blog post is published.

The website's subscribe box promises "don't miss the next post", and
nothing wrote to anyone. The first time a post is published, every
active subscriber with an email address is sent a short note about it,
in the language they signed up in. `subscribers_notified_at` is stamped
before the first email leaves, so a post is announced once — taking it
down and putting it back up does not write to the list again.

Mail goes out the way order emails do: through the connected Gmail
account, falling back to SMTP.
"""
import threading
from urllib.parse import quote

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import connection
from django.utils import timezone
from django.utils.html import escape

from . import blog_preview
from .models import BlogPost, NewsletterSubscription

TEXT = {
    "label": {"en": "New on the blog", "tr": "Blogda yeni", "ru": "Новое в блоге"},
    "button": {"en": "Read the post", "tr": "Yazıyı oku", "ru": "Читать статью"},
    "why": {
        "en": "You are receiving this because you subscribed at demfirat.com.",
        "tr": "Bu e-postayı demfirat.com üzerinden abone olduğunuz için alıyorsunuz.",
        "ru": "Вы получили это письмо, потому что подписались на demfirat.com.",
    },
    "unsubscribe": {"en": "Unsubscribe", "tr": "Abonelikten çık", "ru": "Отписаться"},
}


def announce(post):
    """Write to the list about `post` if it is published and has not been
    announced yet. Returns how many people are being written to."""
    if not post.pk or not post.is_published:
        return 0
    # Claim the announcement in one statement: two saves racing each other
    # cannot both win it.
    claimed = BlogPost.objects.filter(
        pk=post.pk, is_published=True, subscribers_notified_at__isnull=True,
    ).update(subscribers_notified_at=timezone.now())
    if not claimed:
        return 0
    recipients = list(
        NewsletterSubscription.objects
        .filter(is_active=True, email__isnull=False)
        .exclude(email="")
        .values_list("email", "language")
    )
    if recipients:
        _in_background(_send_all, post.pk, recipients)
    return len(recipients)


def _in_background(target, *args):
    """Sending takes a second or two per subscriber; the person who
    pressed Publish does not wait for it."""
    threading.Thread(target=target, args=args, daemon=True).start()


def _send_all(post_pk, recipients):
    try:
        post = BlogPost.objects.get(pk=post_pk)
        sent = sum(1 for email, language in recipients if _send_one(post, email, language))
        print(f"[blog_newsletter] post #{post_pk}: sent {sent} of {len(recipients)}")
    except Exception as exc:
        print(f"[blog_newsletter] post #{post_pk}: stopped on {exc}")
    finally:
        connection.close()


def language_for(post, language):
    """The language to write in: the subscriber's own when the post and
    the website both have it, else the website's, else English."""
    for candidate in (language, getattr(settings, "STOREFRONT_LANGUAGE", "tr"), "en"):
        if (candidate in blog_preview.SITE_LANGUAGES
                and getattr(post, f"title_{candidate}", "")
                and getattr(post, f"content_{candidate}", "")):
            return candidate
    return "en"


def message_for(post, email, language):
    """(subject, html, text, unsubscribe_url) for one subscriber."""
    lang = language_for(post, language)
    base = getattr(settings, "STOREFRONT_URL", "https://www.demfirat.com").rstrip("/")
    if lang != blog_preview.SITE_DEFAULT_LANGUAGE:
        base = f"{base}/{lang}"
    post_url = f"{base}/blog/{post.slug}"
    unsubscribe_url = f"{base}/unsubscribe?email={quote(email)}"

    title = getattr(post, f"title_{lang}") or post.title_en
    excerpt = getattr(post, f"excerpt_{lang}") or post.excerpt_en
    image = post.cover_image or post.hero_image
    sans = "'Montserrat',Arial,sans-serif"
    picture = (
        f'<tr><td style="padding:0 40px 24px;"><a href="{escape(post_url)}">'
        f'<img src="{escape(image)}" alt="" width="520" '
        f'style="display:block;width:100%;max-width:520px;height:auto;border-radius:8px;"></a></td></tr>'
    ) if image else ""

    html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#f5f2ec;font-family:{sans};">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f2ec;padding:30px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;background:white;border-radius:12px;overflow:hidden;">
        <tr><td style="background:rgb(250,245,235);padding:28px 0;text-align:center;">
          <span style="font-family:'Jost',{sans};font-size:28px;font-weight:500;color:#944f05;letter-spacing:2px;">DEMFIRAT</span>
        </td></tr>
        <tr><td style="padding:36px 40px 20px;">
          <p style="margin:0 0 10px;font-size:12px;font-weight:600;letter-spacing:1.5px;text-transform:uppercase;color:#b8956a;">{TEXT["label"][lang]}</p>
          <h1 style="margin:0 0 14px;font-family:Georgia,'Times New Roman',serif;font-size:24px;line-height:1.3;color:#1a1a1a;">{escape(title)}</h1>
          <p style="margin:0;font-size:15px;line-height:1.6;color:#555;">{escape(excerpt)}</p>
        </td></tr>
        {picture}
        <tr><td style="padding:0 40px 36px;">
          <a href="{escape(post_url)}" style="display:inline-block;padding:13px 32px;background:#944f05;color:white;text-decoration:none;border-radius:6px;font-size:14px;font-weight:600;">{TEXT["button"][lang]}</a>
        </td></tr>
        <tr><td style="background:rgb(250,245,235);padding:16px 40px;text-align:center;">
          <p style="font-size:11px;line-height:1.5;color:#999;margin:0 0 8px;">{TEXT["why"][lang]}</p>
          <a href="{escape(unsubscribe_url)}" style="font-size:11px;color:#999;text-decoration:underline;">{TEXT["unsubscribe"][lang]}</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    text = (
        f"{TEXT['label'][lang]}: {title}\n\n{excerpt}\n\n"
        f"{TEXT['button'][lang]}: {post_url}\n\n"
        f"{TEXT['why'][lang]}\n{TEXT['unsubscribe'][lang]}: {unsubscribe_url}\n"
    )
    return f"{TEXT['label'][lang]}: {title}", html, text, unsubscribe_url


def _send_one(post, email, language):
    try:
        from accounting.services_accounts import brand_name_for
        from erp.branding import brand
        from operating.order_notifications import _send_via_gmail_oauth

        subject, html, text, unsubscribe_url = message_for(post, email, language)
        brand_name = brand_name_for()
        brand_email = brand("BRAND_EMAIL")
        unsubscribe = f"<{unsubscribe_url}>"

        if _send_via_gmail_oauth(
            email, subject, html, None, None,
            text_body=text, from_name=brand_name,
            reply_to=brand_email or None, list_unsubscribe=unsubscribe,
        ):
            return True

        host_user = getattr(settings, "EMAIL_HOST_USER", "") or ""
        if not host_user:
            print(f"[blog_newsletter] no mailbox connected and SMTP not configured; skipped {email}")
            return False
        from email.utils import formataddr
        message = EmailMultiAlternatives(
            subject=subject, body=text,
            from_email=formataddr((brand_name, host_user)) if brand_name else host_user,
            to=[email], reply_to=[brand_email] if brand_email else None,
            headers={"List-Unsubscribe": unsubscribe},
        )
        message.attach_alternative(html, "text/html")
        message.send(fail_silently=False)
        return True
    except Exception as exc:
        print(f"[blog_newsletter] could not write to {email}: {exc}")
        return False
