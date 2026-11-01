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
# - Two runs at once (two sessions, a checkout and a worktree) must not
#   share those databases: they deadlock each other and fail tests at
#   random. Each run holds a numbered slot while it runs, a lock folder
#   under ~/.cache/nejum-test-locks, and takes the first one free. Slot 0
#   is the plain name, so a lone run keeps reusing its kept database; a
#   second run at the same time gets ckdb_<fp>_s1 and its own clones. A
#   slot whose run has died (its PID gone) is taken back.
# - --parallel needs tblib (requirements-dev.txt) to report failures.
# Run it from the erp/ folder of the checkout or worktree under test.
set -e
cd "$(dirname "$0")/.."
FP=$(find . -path '*/migrations/*.py' -not -path './vir_env/*' | LC_ALL=C sort | xargs cat | shasum | cut -c1-10)

LOCKS="$HOME/.cache/nejum-test-locks"
mkdir -p "$LOCKS"
SLOT=0
while :; do
    LOCK="$LOCKS/$FP.$SLOT"
    if mkdir "$LOCK" 2>/dev/null; then
        echo $$ > "$LOCK/pid"
        break
    fi
    # Held — unless the run holding it is gone.
    HOLDER=$(cat "$LOCK/pid" 2>/dev/null || true)
    if [ -n "$HOLDER" ] && ! kill -0 "$HOLDER" 2>/dev/null; then
        rm -rf "$LOCK"
        continue
    fi
    SLOT=$((SLOT + 1))
done
trap 'rm -rf "$LOCK"' EXIT
trap 'exit 130' INT TERM

DB="ckdb_$FP"
[ "$SLOT" -gt 0 ] && DB="${DB}_s$SLOT"
[ "$SLOT" -gt 0 ] && echo "Another test run holds $FP's databases; this one uses $DB." >&2

SETTINGS_DIR=$(mktemp -d)
printf 'from erp.settings import *  # noqa\nDATABASES["default"]["TEST"] = {"NAME": "%s"}\n' "$DB" \
    > "$SETTINGS_DIR/local_test_settings.py"
[ $# -eq 0 ] && set -- accounting crm operating marketing erp
PYTHONPATH="$SETTINGS_DIR" \
DB_ENGINE=django.db.backends.postgresql DB_NAME=postgres DB_USER="${USER}" \
DB_PASSWORD= DB_HOST=127.0.0.1 DB_PORT=5432 \
python manage.py test "$@" --parallel "${TEST_PROCESSES:-8}" --keepdb --noinput \
    --settings=local_test_settings
