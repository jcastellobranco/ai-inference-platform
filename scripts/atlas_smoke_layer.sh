#!/bin/sh
# Print the largest ATLAS Compose overlay currently running
# (observability | redis | agent), or nothing if none is running.
# Used by `make smoke-*` so `compose run` does not recreate shared services
# (backend, worker, agent) with a smaller overlay's configuration.
running=$(docker compose "$@" ps --status running --services 2>/dev/null) || exit 0
for pair in prometheus:observability redis:redis agent:agent; do
  if printf '%s\n' "$running" | grep -qx "${pair%%:*}"; then
    echo "${pair##*:}"
    exit 0
  fi
done
