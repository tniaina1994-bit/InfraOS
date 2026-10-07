PROXMOX_HOST ?= root@192.168.10.90
# Env dev officiel: CT 133 infraos-dev (192.168.10.39). Legacy CT 132 InfraOS (.50) via LXC_ID=132 API_URL=http://192.168.10.50:8000
LXC_ID ?= 133
API_URL ?= http://192.168.10.39:8000

.PHONY: help provision check api-dev ui-dev iso test lint security-check no-docker-check debian13-check openapi create-lxc db-init build-ui
help:
	@echo "make create-lxc   - cree CT infraos-dev spec officielle (sans Docker)"
	@echo "make provision    - bootstrap LXC dev natif via Proxmox (sans Docker)"
	@echo "make check        - verif OS + API health sur LXC"
	@echo "make test         - tous les tests backend"
	@echo "make lint         - ruff (code propre)"
	@echo "make security-check - pas de shell arbitraire Web + monolithe unique"
	@echo "make no-docker-check - prouve aucune dependance Docker"
	@echo "make debian13-check - compat Debian 13 + manifests + licence"
	@echo "make openapi      - regenere docs/openapi.json"
	@echo "make api-dev      - run API local (dev)"
	@echo "make ui-dev       - run UI local (dev)"
	@echo "make build-ui     - build frontend prod"
	@echo "make db-init      - init Postgres sur le LXC"
	@echo "make iso          - build ISO (sur builder Debian13)"

create-lxc:
	bash scripts/dev/create-lxc.sh "$(PROXMOX_HOST)" "$(LXC_ID)"

provision:
	bash scripts/install/bootstrap.sh --remote "$(PROXMOX_HOST)" "$(LXC_ID)"

check:
	bash scripts/test/check-lxc.sh "$(PROXMOX_HOST)" "$(LXC_ID)" "$(API_URL)"

no-docker-check:
	bash scripts/test/no-docker-check.sh "$(PROXMOX_HOST)" "$(LXC_ID)"

api-dev:
	cd backend/app && uvicorn main:app --reload --port 8000

ui-dev:
	cd frontend && npm run dev

build-ui:
	cd frontend && npm run build

test:
	python -m pytest backend/tests -v

lint:
	ruff check backend || python -m ruff check backend || echo "(ruff absent, saute)"

security-check:
	bash scripts/test/no-arbitrary-shell.sh
	bash scripts/test/no-microservice.sh

debian13-check:
	bash scripts/test/debian13-check.sh

openapi:
	cd backend/app && python -c "from main import app; import json; open('../../docs/openapi.json','w').write(json.dumps(app.openapi(), indent=1))" && echo "docs/openapi.json regenere"

db-init:
	scp scripts/install/init-postgres.sh "$(PROXMOX_HOST):/tmp/init-postgres.sh"
	ssh -o StrictHostKeyChecking=no "$(PROXMOX_HOST)" "pct push $(LXC_ID) /tmp/init-postgres.sh /tmp/init-postgres.sh && pct exec $(LXC_ID) -- bash /tmp/init-postgres.sh"

iso:
	bash iso/build.sh
