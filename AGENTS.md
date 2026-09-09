# AGENTS.md — egsys-jiraview

`egSYS Painel do Cliente Jira` — painel JSM multi-estado (1 container único), com
RBAC, controle de acesso por estado e hardening no padrão egSYS Orion. Foco inicial: SC (PMSC).

## Regra de produto (anti-desvio — INEGOCIÁVEL)
- **1 container = todos os estados.** Proibido criar serviço/container por estado.
  Estado novo = bloco novo em `deploy/estados.yaml` (projetos, clientes, papéis, áreas) — sem código novo de infra.
- O produto é `jiraview` (egSYS Painel do Cliente Jira); estados (SC/TO/AM/...) são dados.

## Comandos
- Build: `docker compose -f docker-compose.prod.yml up -d --build` (no host `monitoramento-egsys`)
- Rodar local dev: `cd backend && uvicorn app.main:app --reload --port 8090`
- Testes: `cd backend && pytest -q`
- Lint: `ruff check backend`
- Door (gate):
  1. `pytest -q` verde; 2. `ruff check backend` verde; 3. `scripts/portal-jsm/corrige_divergentes.py --audit` sem divergências
- Deploy: `ssh monitoramento-egsys` → `cd /var/egsys-docker/container/jiraview` → `docker compose -f docker-compose.prod.yml up -d --build`

## Git (dual-path, padrão Orion)
- `origin` = empresa (sanitizado): `git@github.com:egsys-dev/jiraview.git`
- `privado` = completo: `git@github.com:andreprado-egsys/jiraview.git`
- Antes de qualquer commit: auditoria de secrets (regex no diff) + auditoria de sanitização
  nas branches do GitHub da empresa (ver skill `jiraview-commit`).
- Conventional Commits: `tipo(escopo): descrição sem acento`.
- **Nunca commitar**: docs/SESSION_*, history.md, .env*, *.bak*, *.db, deploy/env|ssh|resources,
  scripts/portal-jsm/snapshots/, metadados de agente (.opencode/.hermes/.kiro/openspec/graphify-out).

## Segurança (espelho Orion, ACH-001..011)
- RBAC mínimo privilégio por estado; JWT HS256; `Depends(get_current_user)` em toda rota (exceto /health).
- Credencial Jira backend-only (env), nunca no client. `.env` 0600 e gitignored.
- Headers defensivos (HSTS prod, X-Frame-Options DENY, nosniff, CSP, Referrer-Policy).
- API somente-leitura do Jira; escrita só via script `--apply` autorizado com `--dry-run` + snapshot.
- Container hardening: 512m / 1.0 cpu / 150 pids / no-new-privileges; rede webproxy (sem porta pública).

## Jira (padrão PSEI, sanitizado)
- Tasks sanitizadas (padrão orion-jira-sync): sem IA, sem credenciais, sem dados de cliente/empresa,
  sem GitHub privado, sem SESSION/.env/agent paths. Ver skill `jiraview-jira-sync`.
