# egSYS JiraView — Padrão de Projeto (espelho egSYS Orion)

## Git remotes (padrão dual-path Orion)
- **origin (empresa, sanitizado):** `git@github.com:egsys-dev/jiraview.git`
- **privado (completo):** `git@github.com:andreprado-egsys/jiraview.git`

## Regra de sanitização (INEGOCIÁVEL — igual Orion)
**Sobe para `origin` (egsys-dev):** código produto, testes, docs oficiais
(README.md, CHANGELOG.md, API.md, SECURITY.md, DEPLOY.md, ROADMAP.md,
EVOLUTION_PLAN.md, MANUAL_*.md, ARCHITECTURE.md, RUNBOOK_*.md).
**NUNCA sobe:** `docs/SESSION_*`, `docs/history.md`, credenciais/guias internos
(`docs/CREDENCIAIS_*`, `docs/INC_RESPONSE_*`), metadados de agentes
(`.opencode/`, `.hermes/`, `.kiro/`, `graphify-out/`, `openspec/`), `.env*`,
`*.bak*`, `*.db`, `deploy/**/env|ssh|resources`, `scripts/portal-jsm/snapshots/`
e `.agent/` dirs.

## Qualidade
- Conventional Commits: `tipo(escopo): descrição sem acento`
- Testes: pytest + gate (ver AGENTS.md)
- Docs-as-Code: mudança → docs sync → task Jira sanitizada → commit → push dual

## Skills deste projeto (espelham Orion)
- `jiraview-docs-sync` (documentação 3 camadas + history sanitizado)
- `jiraview-jira-sync` (tasks Jira sanitizadas)
- `jiraview-commit` (commit/push dual-path + dupla auditoria de secrets)
