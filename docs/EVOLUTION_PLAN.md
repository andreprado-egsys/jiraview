# Evolução — egSYS JiraView (espelho Orion)

## Visão
Substituir a dependência do portal fixo do JSM e do Node-RED herdado por um
painel corporativo próprio: **1 container**, multi-estado por configuração,
com RBAC, métricas visuais (estilo Jira Dashboard), filtros no padrão Jira
(construtor visual + JQL do gestor), observabilidade transparente da jornada do ticket
e total sanitização (sem credenciais no client).

## Fases
| Fase | Entrega | Status |
|---|---|---|
| F0 — Diagnóstico/JSM | Análise do portal, causas (done sem resolução), correção 19+18, snapshots | ✅ |
| F1 — Base app | FastAPI + SPA + RBAC JWT + Jira read-only + estados.yaml (SC) | ✅ |
| F2 — Painel & UX | Cards + 4 gráficos + Modo Escuro Full-Window + Calibração Chart.js + Filtros JQL + Skills | ✅ |
| F2.1 — Observabilidade & Jornada | Funil de 4 estágios (eliminação da ambiguidade "abertas") + Drawer lateral com Stepper de 5 etapas + Posse da bola + SLA de etapa | ⏳ v0.2 |
| F3 — Deploy prod | Traefik `/painel_sc` + hardening (512m/150pids) + cert existente | ✅ |
| F4 — Identidade & RBAC | Login real + seed papéis por estado + rate limiting | ⏳ v0.2 |
| F5 — Multi-estado | TO/AM/PR/GM ativados (YAML + papéis) + visão consolidada | ⏳ v0.4 |
| F6 — Automação | Automação JSM de conclusão + SLA por área + migração Node-RED | ⏳ v0.5 |

## Invariantes (gate canônico)
1. **1 container único = todos os estados** (anti-desvio inegociável).
2. **Zero credencial** em repositório ou client (apenas env backend-only).
3. **RBAC estrito** por estado (JWT HS256).
4. **Read-only da API Jira** (escrita apenas via script `--apply` com dry-run e snapshot).
5. **Sanitização corporativa** padrão Orion (sem dados sensíveis ou de IA nas tasks/docs públicos).
6. **Hardening Cgroups** (512MB RAM / 1.0 CPU / 150 PIDs / no-new-privileges).
7. **Observabilidade não-poluente** (tabela resumida + gaveta lateral de detalhes).
