#!/bin/sh
# Copies every pilot_request row from the old website Postgres to the shared PostGIS database
# (docs/runbook-db-switch.md step 3). Operator-only; never a pre-deploy command or a service job.
#
# Usage (in a shell that reaches both databases, e.g. `railway ssh` into PostGIS-cXKk):
#   OLD_DB_URL=<old Postgres URL> NEW_DB_URL=<PostGIS superuser URL> sh ops/copy-pilot-requests.sh
# Both URLs carry credentials: set them in that shell only, never in git, chat or a service variable.
#
# Safe by design:
# - reads the old database only; writes the new one in ONE transaction;
# - idempotent: rows whose id already exists are skipped (ON CONFLICT (id) DO NOTHING), so rows
#   the website wrote to PostGIS after the switch are kept and a rerun copies nothing;
# - before commit, compares an md5 of the staged rows with the same rows in pilot_request and
#   aborts ("mismatch: rolled back") on any difference; nothing is written then.
# Output: three lines old|N|md5, staged|N|md5, landed|N|md5 (all equal), then "copy: committed".
# Rollback to the old database: run again with OLD_DB_URL and NEW_DB_URL swapped.
set -eu
: "${OLD_DB_URL:?set OLD_DB_URL}"
: "${NEW_DB_URL:?set NEW_DB_URL}"

COLS="id, created_at, locale, full_name, email, country, farm_size_text, main_crop, notes, consent_at, consent_text, status, deleted_at"
DIGEST="count(*), md5(coalesce(string_agg(t::text, '|' order by id), ''))"

psql "$OLD_DB_URL" -v ON_ERROR_STOP=1 -At \
  -c "select 'old', $DIGEST from (select $COLS from pilot_request) t"

psql "$OLD_DB_URL" -v ON_ERROR_STOP=1 \
  -c "\copy (select $COLS from pilot_request) to stdout with (format csv)" \
| psql "$NEW_DB_URL" -v ON_ERROR_STOP=1 -1 -At \
  -c "create temp table pr_in (like pilot_request) on commit drop" \
  -c "\copy pr_in ($COLS) from pstdin with (format csv)" \
  -c "insert into pilot_request ($COLS) select $COLS from pr_in on conflict (id) do nothing" \
  -c "select 'staged', $DIGEST from (select $COLS from pr_in) t" \
  -c "select 'landed', $DIGEST from (select $COLS from pilot_request where id in (select id from pr_in)) t" \
  -c "do \$\$ begin
        if (select md5(coalesce(string_agg(t::text, '|' order by id), '')) from (select $COLS from pr_in) t)
           is distinct from
           (select md5(coalesce(string_agg(t::text, '|' order by id), ''))
              from (select $COLS from pilot_request where id in (select id from pr_in)) t)
        then raise exception 'mismatch: rolled back'; end if;
      end \$\$"

echo "copy: committed"
