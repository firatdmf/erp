#!/usr/bin/env bash
# Refresh the local development copy of the production database.
#
# Dumps the Railway prod Postgres into ~/Backups/erp/ (so every refresh is also
# a real backup, following the existing naming convention) and restores it into
# a local database. Read-only against production.
#
#   ./scripts/local-db-refresh.sh             # dump prod, restore into erp_local
#   ./scripts/local-db-refresh.sh --from-last # skip the dump, reuse newest dump
set -euo pipefail

PGBIN=/opt/homebrew/opt/postgresql@18/bin
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DJANGO_DIR="$REPO_ROOT/erp"
BACKUP_DIR="$HOME/Backups/erp"
LOCAL_DB="${LOCAL_DB:-erp_local}"
LOCAL_HOST="${LOCAL_HOST:-127.0.0.1}"
LOCAL_USER="${LOCAL_USER:-$USER}"

case "$LOCAL_HOST" in
  127.0.0.1|localhost|::1) ;;
  *) echo "refusing to restore into non-local host: $LOCAL_HOST" >&2; exit 1 ;;
esac

mkdir -p "$BACKUP_DIR"

if [[ "${1:-}" == "--from-last" ]]; then
  DUMP="$(ls -t "$BACKUP_DIR"/erp_*.dump 2>/dev/null | head -1)"
  [[ -n "$DUMP" ]] || { echo "no dump found in $BACKUP_DIR" >&2; exit 1; }
  echo "==> reusing $DUMP"
else
  # Build the prod URL from erp/.env without ever printing the password.
  DBURL="$(cd "$DJANGO_DIR" && "$REPO_ROOT/vir_env/bin/python" -c "
from decouple import config
import urllib.parse as u
print('postgresql://%s:%s@%s:%s/%s' % (u.quote(config('DB_USER')),
    u.quote(config('DB_PASSWORD')), config('DB_HOST'),
    config('DB_PORT'), config('DB_NAME')))")"
  DUMP="$BACKUP_DIR/erp_$(date +%Y%m%d_%H%M%S).dump"
  echo "==> dumping production -> $DUMP"
  "$PGBIN/pg_dump" -Fc --no-owner --no-privileges -d "$DBURL" -f "$DUMP"
  unset DBURL
fi

echo "==> restoring into $LOCAL_DB on $LOCAL_HOST"
"$PGBIN/dropdb" --if-exists -h "$LOCAL_HOST" -U "$LOCAL_USER" "$LOCAL_DB"
"$PGBIN/createdb" -h "$LOCAL_HOST" -U "$LOCAL_USER" "$LOCAL_DB"
"$PGBIN/pg_restore" --no-owner --no-privileges --no-comments -j 4 \
  -h "$LOCAL_HOST" -U "$LOCAL_USER" -d "$LOCAL_DB" "$DUMP" 2>&1 |
  grep -v 'role .* does not exist' || true

"$PGBIN/psql" -h "$LOCAL_HOST" -U "$LOCAL_USER" -d "$LOCAL_DB" -tAc \
  "select 'restored ' || count(*) || ' tables, last migration ' ||
          (select max(applied)::date from public.django_migrations)
     from pg_tables where schemaname not like 'pg_%'"
echo "==> done. run the app against it with: ./scripts/dev.sh runserver"
