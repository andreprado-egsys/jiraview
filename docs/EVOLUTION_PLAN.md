# Evolução — egSYS JiraView (espelho Orion)

## Visão
Substituir a dependência do portal fixo do JSM e do Node-RED herdado por um
painel corporativo próprio: **1 container**, multi-estado por configuração,
com RBAC, métricas visuais (estilo Jira Dashboard) e filtros no padrão Jira
(construtor visual + JQL do gestor), tudo sanitizado (sem credenciais no client).

## Fases
| Fase | Entrega | Status |
|---|---|---|
| F0 — Diagnóstico/JSM | análise do portal, causas (done sem resolução), correção 19+18, snapshots | ✅ |
| F1 — Base app | FastAPI + SPA + RBAC JWT + Jira read-only + estados.yaml (SC) | ✅ |
| F2 — Painel completo | cards + 4 gráficos + listagem colunas + filtros visuais + JQL salvos | ✅ |
| F3 — Deploy prod | Traefik `/painel_sc` + hardening + cert existente | ✅ |
| F4 — Identidade | login real + seed papéis por estado + rate limiting | ⏳ v0.2 |
| F5 — Multi-estado | TO/AM/PR/GM ativados (YAML + papéis) + visão consolidada | ⏳ v0.4 |
| F6 — Automação | automação JSM de conclusão + SLA por área + migração Node-RED | ⏳ v0.5 |

## Invariantes (gate canônico)
1. 1 container único por estado zero (anti-desvio). 2. Zero credencial em repo/client.
3. RBAC por estado. 4. Read-only da API Jira (escrita só script autorizado).
5. Sanitização Jira/Git igual Orion. 6. Hardening 512m/1cpu/150pids.
