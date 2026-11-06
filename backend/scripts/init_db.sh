#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 -U app -d platform -f /migrations/001_init.sql
psql -v ON_ERROR_STOP=1 -U app -d platform -f /migrations/002_roles.sql
psql -v ON_ERROR_STOP=1 -U app -d platform -f /migrations/003_seed.sql
