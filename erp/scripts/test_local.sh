#!/bin/sh
# Run the test suite against local Postgres, in parallel, keeping the test
# database between runs.
#
#   scripts/test_local.sh                      # accounting crm operating marketing erp
#   scripts/test_local.sh crm accounting.tests.test_x
#
# Why each piece:
# - Local Postgres: erp/.env points at production; a bare `manage.py test`
#   would build its test database on the production server.
# - The test database is named after a fingerprint of every migration file,
#   so a run reuses it (--keepdb) only when the migrations are the same.
#   Code with a migration another run lacks gets its own database instead of
#   inheriting the wrong schema. The name starts "ckdb_", not "nejum": a
#   cleanup elsewhere drops nejum* test databases mid-run.
# - --parallel needs tblib (requirements-dev.txt) to report failures.
# Run it from the erp/ folder of the checkout or worktree under test.
set -e
cd "$(dirname "$0")/.."
FP=$(find . -path '*/migrations/*.py' -not -path './vir_env/*' | LC_ALL=C sort | xargs cat | shasum | cut -c1-10)
SETTINGS_DIR=$(mktemp -d)
printf 'from erp.settings import *  # noqa\nDATABASES["default"]["TEST"] = {"NAME": "ckdb_%s"}\n' "$FP" \
    > "$SETTINGS_DIR/local_test_settings.py"
[ $# -eq 0 ] && set -- accounting crm operating marketing erp
PYTHONPATH="$SETTINGS_DIR" \
DB_ENGINE=django.db.backends.postgresql DB_NAME=postgres DB_USER="${USER}" \
DB_PASSWORD= DB_HOST=127.0.0.1 DB_PORT=5432 \
python manage.py test "$@" --parallel "${TEST_PROCESSES:-8}" --keepdb --noinput \
    --settings=local_test_settings
