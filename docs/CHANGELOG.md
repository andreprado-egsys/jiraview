# egSYS JiraView — Changelog

## [Unreleased] — 2026-09-09

### Added
- `feat: Modo Escuro Full-Window (padrão Orion)` — suporte a tema escuro/claro em 100% da viewport (`color-scheme: dark !important`, script anti-FOUC no `<head>`, variáveis de tema aplicadas em todos os elementos estruturais e formulários, persistência em `localStorage`).
- `feat: Calibração de contraste no Chart.js` — suporte a paleta dinâmica com fundo transparente (`ticks.backdropColor: "transparent"`) no gráfico polar de solicitantes, ticks contrastantes (`#f0f6fc`), grids e angleLines (`#30363d`), tooltips dark e legendas claras para legibilidade absoluta em modo escuro.
- `feat: Tríade de Skills Corporativas egSYS Jiraview` — automações propagadas para todas as CLIs (`~/.agents/skills/`, `.agent/skills/`, OpenCode, Hermes, Kiro, Claude e Gemini):
  - `jiraview-commit`: commit autônomo, sanitização rigorosa e sincronização dual-path (`origin` empresa vs `privado`) com auditoria remota de branches.
  - `jiraview-docs-sync`: protocolo de governança Docs-as-Code em 3 camadas, histórico cumulativo (`history.md`), sessões e active learning.
  - `jiraview-jira-sync`: sincronização e mapeamento de tarefas no Jira corporativo sanitizado (sem dados de IA, senhas ou clientes).
- `feat: Configuração Git Dual-Path (padrão Orion)` — vinculação de remotes `origin` (empresa sanitizado: `git@github.com:egsys-dev/jiraview.git`) e `privado` (backup completo: `git@github.com:andreprado-egsys/jiraview.git`).
- `feat: criar app egSYS Painel do Cliente Jira` — FastAPI + SPA multi-estado (container único), RBAC JWT, serviço Jira read-only.
- `feat: endpoints de painel` — `/issues` (colunas Tipo/Origem/Referência/Resumo/Status/Solicitante/Prioridade/Atualização/Entrega), `/dashboard` (cards com particionamento por origem e categoria), `/charts` (agregados: status, prioridade, solicitante, série 15d), `/meta` (status+tipos), `/filtros` (CRUD JQL por gestor/estado).
- `feat: construtor visual de filtros` — campo/operador/valor + multiseleção → gera JQL (padrão Jira) + campo JQL livre.
- `feat: gráficos estilo Jira Dashboard` — barras por status, donut prioridade, polar por solicitante, linha de tempo.
- `feat: multi-estado por config` — `deploy/estados.yaml` (estado = bloco config; 1 único container).
- `feat: deploy prod` — Traefik path-prefix em `suporte-monitor.egsys.siseg.tech/painel_sc`, hardening 512m/1.0cpu/150pids, no-new-privileges.
- `feat: PSEI-277 correlato` — correção de 19+18 tickets divergentes (done sem resolução) via script idempotente + timer systemd; salvaguardas com snapshot/restore.

### Changed
- `refactor: limpeza de imports e escopo de overview` — remoção de imports duplicados em `backend/app/main.py` e busca dinâmica de projetos por estado no `/overview`.

### Security
- `security: headers defensivos` — HSTS (prod), X-Frame-Options DENY, nosniff, CSP, Referrer-Policy.
- `security: token backend-only` — credenciais Jira injetadas por env; nunca expostas ao client.
- `security: .env chmod 600 e gitignored`; persistência de filtros em `data/filtros.json` 0600.

### Fixed
- `fix: contraste do gráfico polar no modo escuro` — remoção de caixas brancas nos ticks e restauração de rótulos visíveis.
- `fix: escopo de estilo modo escuro` — aplicação de classes e atributos no `<html>` e `<body>`, corrigindo fundo que permanecia claro.
- `fix: CORS multi-método` (GET/POST/DELETE/OPTIONS) e origem correta de produção.
- `fix: /meta sem consulta interna inválida` — dropdowns populados (14 status + 8 tipos).
- `fix: boot do frontend` — cards, gráficos e meta carregam todos (um `boot()`).
- `fix: UX de busca vazia` — mensagem explicativa quando JQL não retorna resultados.
