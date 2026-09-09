# egSYS JiraView — Changelog

## [Unreleased] — 2026-09-09

### Added
- `feat: criar app egSYS Painel do Cliente Jira` — FastAPI + SPA multi-estado (container único), RBAC JWT, serviço Jira read-only.
- `feat: endpoints de painel` — `/issues` (colunas Tipo/Referência/Resumo/Status/Solicitante/Prioridade/Atualização/Entrega), `/dashboard` (cards), `/charts` (agregados: status, prioridade, solicitante, série 15d), `/meta` (status+tipos), `/filtros` (CRUD JQL por gestor/estado).
- `feat: construtor visual de filtros` — campo/operador/valor + multiseleção → gera JQL (padrão Jira) + campo JQL livre.
- `feat: gráficos estilo Jira Dashboard` — barras por status, donut prioridade, polar por solicitante, linha de tempo.
- `feat: multi-estado por config` — `deploy/estados.yaml` (estado = bloco config; 1 único container).
- `feat: deploy prod` — Traefik path-prefix em `suporte-monitor.egsys.siseg.tech/painel_sc`, hardening 512m/1.0cpu/150pids, no-new-privileges.
- `feat: PSEI-277 correlato` — correção de 19+18 tickets divergentes (done sem resolução) via script idempotente + timer systemd; salvaguardas com snapshot/restore.

### Security
- `security: headers defensivos` — HSTS (prod), X-Frame-Options DENY, nosniff, CSP, Referrer-Policy.
- `security: token backend-only` — credenciais Jira injetadas por env; nunca expostas ao client.
- `security: .env chmod 600 e gitignored`; persistência de filtros em `data/filtros.json` 0600.

### Fixed
- `fix: CORS multi-método` (GET/POST/DELETE/OPTIONS) e origem correta de produção.
- `fix: /meta sem consulta interna inválida` — dropdowns populados (14 status + 8 tipos).
- `fix: boot do frontend` — cards, gráficos e meta carregam todos (um `boot()`).
- `fix: UX de busca vazia` — mensagem explicativa quando JQL não retorna resultados.
