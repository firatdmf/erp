from django.db import migrations


def empty_client(apps, schema_editor):
    """Each connected Google account kept its own copy of the OAuth client
    ID and secret. The client now comes from settings, so the copies only
    expose the secret; clear them."""
    GoogleChatCredentials = apps.get_model("authentication", "GoogleChatCredentials")
    GoogleChatCredentials.objects.update(client_id="", client_secret="")


class Migration(migrations.Migration):

    dependencies = [
        ("authentication", "0026_google_credentials_client_unused"),
    ]

    operations = [
        migrations.RunPython(empty_client, migrations.RunPython.noop),
    ]
