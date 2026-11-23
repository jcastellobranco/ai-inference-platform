# ATLAS local-first golden paths. No cloud provisioning.
.DEFAULT_GOAL := help
COMPOSE := docker compose
BASE := -f docker-compose.fullstack.yml
RAG := $(BASE) -f docker-compose.integrated.yml
AGENT := $(RAG) -f docker-compose.agents.yml
REDIS := $(AGENT) -f docker-compose.redis.yml
OBSERVABILITY := $(REDIS) -f docker-compose.observability.yml

# `compose run` recreates shared services (backend, worker, agent) whose config
# differs from the files passed. Smoke targets therefore reuse the largest
# overlay already running, so a smoke run never strips observability or Redis
# settings from a live stack. Override with SMOKE_LAYER=observability|redis|agent|rag.
SMOKE_LAYER ?= $(shell sh scripts/atlas_smoke_layer.sh $(OBSERVABILITY))
smoke_files = $(if $(filter observability,$(SMOKE_LAYER)),$(OBSERVABILITY),$(if $(filter redis,$(SMOKE_LAYER)),$(REDIS),$(if $(filter agent,$(SMOKE_LAYER)),$(AGENT),$(1))))

.PHONY: help doctor init config-minimal config-rag config-agent config-redis config-observability up up-rag up-agent up-redis up-observability stop-observability start-observability ps ps-observability logs logs-observability down down-observability smoke-rag smoke-agent smoke-observability smoke-alerts new-service atlas-create

help:
	@printf '%s\n' 'ATLAS local developer commands:' '  make atlas-create NAME=foo AUTH=jwt OBSERVABILITY=metrics - generate full service' '  make doctor       - check local prerequisites (no containers)' '  make init         - create .env and untracked local Redis secret' '  make config-*     - validate Compose without starting containers' '  make up           - start minimal stack' '  make up-rag       - add RAG and evaluation' '  make up-agent     - add agent and MCP' '  make up-redis     - add Redis cache and quotas' '  make up-observability - add Prometheus, Grafana, Loki, Alloy and RAG/worker metrics' '  make stop-observability - pause ATLAS containers without removing them or volumes' '  make start-observability - resume existing ATLAS containers without rebuilding' '  make ps           - inspect minimal stack' '  make logs         - tail minimal stack logs' '  make down         - stop minimal stack (preserves volumes)' '  make smoke-rag    - run RAG smoke profile (reuses the largest running overlay)' '  make smoke-agent  - run agent smoke profile (reuses the largest running overlay)' '  make smoke-observability - verify Grafana and four Prometheus targets' '  make smoke-alerts  - verify four provisioned Grafana alert rules'
atlas-create:
	@test -n "$(NAME)" || (echo "Usage: make atlas-create NAME=my-api RUNTIME=fastapi AUTH=jwt OBSERVABILITY=metrics" && exit 2)
	@python3 scripts/atlas.py create-service "$(NAME)" --runtime "$(or $(RUNTIME),fastapi)" --database "$(or $(DATABASE),none)" --cache "$(or $(CACHE),none)" --auth "$(or $(AUTH),none)" --observability "$(or $(OBSERVABILITY),none)"
new-service:
	@test -n "$(NAME)" || (echo "Usage: make new-service NAME=my-api RUNTIME=fastapi [POSTGRES=1] [REDIS=1]" && exit 2)
	@python3 scripts/scaffold_service.py "$(NAME)" --runtime "$(or $(RUNTIME),fastapi)" $(if $(filter 1,$(POSTGRES)),--postgres,) $(if $(filter 1,$(REDIS)),--redis,)
doctor:
	@python3 scripts/atlas_dev.py doctor
init:
	@python3 scripts/atlas_dev.py init
config-minimal:
	@$(COMPOSE) $(BASE) config --quiet
config-rag:
	@$(COMPOSE) $(RAG) config --quiet
config-agent:
	@$(COMPOSE) $(AGENT) config --quiet
config-redis:
	@$(COMPOSE) $(REDIS) config --quiet
config-observability:
	@$(COMPOSE) $(OBSERVABILITY) config --quiet
up:
	@$(COMPOSE) $(BASE) up -d --build
up-rag:
	@$(COMPOSE) $(RAG) up -d --build
up-agent:
	@$(COMPOSE) $(AGENT) up -d --build
up-redis:
	@$(COMPOSE) $(REDIS) up -d --build
up-observability:
	@$(COMPOSE) $(OBSERVABILITY) up -d --build
stop-observability:
	@$(COMPOSE) $(OBSERVABILITY) stop
start-observability:
	@$(COMPOSE) $(OBSERVABILITY) start
ps:
	@$(COMPOSE) $(BASE) ps
ps-observability:
	@$(COMPOSE) $(OBSERVABILITY) ps
logs:
	@$(COMPOSE) $(BASE) logs -f --tail=100
logs-observability:
	@$(COMPOSE) $(OBSERVABILITY) logs -f --tail=100 grafana prometheus loki alloy docker-proxy backend worker rag evaluation agent
down:
	@$(COMPOSE) $(BASE) down
down-observability:
	@$(COMPOSE) $(OBSERVABILITY) down
smoke-rag:
	@$(COMPOSE) $(call smoke_files,$(RAG)) --profile smoke run --rm integration-smoke
smoke-agent:
	@$(COMPOSE) $(call smoke_files,$(AGENT)) --profile smoke run --rm agent-smoke
smoke-observability:
	@python3 scripts/atlas_observability_smoke.py
smoke-alerts:
	@python3 scripts/atlas_alerts_smoke.py
