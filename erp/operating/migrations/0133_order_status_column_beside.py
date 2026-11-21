from django.db import migrations


# Step 1 of renaming the order_status column to status without a broken
# minute while Railway swaps releases (migrate runs while the old release
# still serves). A status column sits beside order_status and a trigger
# copies whichever one a write changed into the other, so a release that
# knows either name reads and writes the same value. 0134 fills it; the
# next release moves the model onto status; the one after drops the
# trigger and order_status.
SYNC = """
CREATE FUNCTION operating_order_status_sync() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.status := COALESCE(NEW.status, NEW.order_status);
        NEW.order_status := COALESCE(NEW.order_status, NEW.status);
    ELSIF NEW.status IS DISTINCT FROM OLD.status THEN
        NEW.order_status := NEW.status;
    ELSIF NEW.order_status IS DISTINCT FROM OLD.order_status THEN
        NEW.status := NEW.order_status;
    END IF;
    RETURN NEW;
END
$$ LANGUAGE plpgsql;

CREATE TRIGGER operating_order_status_sync
BEFORE INSERT OR UPDATE ON operating_order
FOR EACH ROW EXECUTE FUNCTION operating_order_status_sync();
"""

UNSYNC = """
DROP TRIGGER IF EXISTS operating_order_status_sync ON operating_order;
DROP FUNCTION IF EXISTS operating_order_status_sync();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("operating", "0132_drop_retired_order_status_column"),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE operating_order ADD COLUMN status varchar(32) NULL",
            "ALTER TABLE operating_order DROP COLUMN status",
        ),
        migrations.RunSQL(SYNC, UNSYNC),
    ]
