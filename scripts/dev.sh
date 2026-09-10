#!/usr/bin/env bash
# Run manage.py against the LOCAL copy of the database instead of production.
#
# erp/.env points DB_* at the production Railway Postgres; python-decouple
# reads os.environ first, so these exports win without touching .env.
#
#   ./scripts/dev.sh runserver
#   ./scripts/dev.sh shell
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

export DB_ENGINE=django.db.backends.postgresql
export DB_NAME="${LOCAL_DB:-erp_local}"
export DB_USER="${LOCAL_USER:-$USER}"
export DB_PASSWORD=""
export DB_HOST=127.0.0.1
export DB_PORT=5432

cd "$REPO_ROOT/erp"
exec "$REPO_ROOT/vir_env/bin/python" manage.py "$@"
