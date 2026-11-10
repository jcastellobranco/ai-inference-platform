# ATLAS local-first golden paths. No cloud provisioning.
.DEFAULT_GOAL := help
COMPOSE := docker compose
BASE := -f docker-compose.fullstack.yml
RAG := $(BASE) -f docker-compose.integrated.yml
AGENT := $(RAG) -f docker-compose.agents.yml
REDIS := $(AGENT) -f docker-compose.redis.yml

.PHONY: help doctor init config-minimal config-rag config-agent config-redis up up-rag up-agent up-redis ps logs down smoke-rag smoke-agent

help:
	@printf '%s\n' 'ATLAS local developer commands:' '  make doctor       - check local prerequisites (no containers)' '  make init         - create .env and untracked local Redis secret' '  make config-*     - validate Compose without starting containers' '  make up           - start minimal stack' '  make up-rag       - add RAG and evaluation' '  make up-agent     - add agent and MCP' '  make up-redis     - add Redis cache and quotas' '  make ps           - inspect minimal stack' '  make logs         - tail minimal stack logs' '  make down         - stop minimal stack (preserves volumes)' '  make smoke-rag    - run RAG smoke profile' '  make smoke-agent  - run agent smoke profile'
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
up:
	@$(COMPOSE) $(BASE) up -d --build
up-rag:
	@$(COMPOSE) $(RAG) up -d --build
up-agent:
	@$(COMPOSE) $(AGENT) up -d --build
up-redis:
	@$(COMPOSE) $(REDIS) up -d --build
ps:
	@$(COMPOSE) $(BASE) ps
logs:
	@$(COMPOSE) $(BASE) logs -f --tail=100
down:
	@$(COMPOSE) $(BASE) down
smoke-rag:
	@$(COMPOSE) $(RAG) --profile smoke run --rm integration-smoke
smoke-agent:
	@$(COMPOSE) $(AGENT) --profile smoke run --rm agent-smoke
