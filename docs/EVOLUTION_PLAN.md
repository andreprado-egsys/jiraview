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
| F2.1 — Observabilidade & Jornada | Funil de 4 estágios + Drawer lateral com Stepper Canônico de 8 etapas + Posse da bola + SLA + Rastreabilidade | ✅ |
| F3 — Deploy prod | Traefik `/painel_sc` + hardening (512m/150pids) + roteamento com prioridade soberana | ✅ |
| F4 — Identidade & RBAC | Login unitário real + SQLite nativo + 1º acesso obrigatório + 10 usuários ativos auditados | ✅ |
| F4.1 — Coordenação Global | Painel da Coordenação com 73 espaços + Gestão de Usuários e Acessos | ✅ |
| F4.2 — Exportação & 1-Click | Exportação Multi-Formato (.MD, .XLSX, .CSV) + Links 1-Click Jira Cloud + Derivações técnicas | ✅ |
| F4.3 — Síntese & Sincronia | Síntese de 52 tarefas abertas + Numeração `#` + sync_db.py soberano (v0.4.1) | ✅ |
| F4.4 — Multi-Espaços | Múltiplos espaços cliente (Mazzola) + customização dinâmica coordenação (v0.4.2) | ✅ |
| F4.5 — Paridade & Coerência Temporal | Cursor pagination v3 + unificação estrita de período nos cards e tabela (v0.4.3) | ✅ |
| F5 — Extensões Modulares & Absorção Node-RED | Esteira Dev + Triagem N1/N2 + Relatórios SMTP + Monitor SSL + Layouts Persistentes + Ergonomia TV (v0.5.9) | ✅ |
| F6 — Governança & Multi-Estado Pleno | Descomissionamento definitivo Node-RED + Automação JSM + SLAs corporativos | ⏳ v0.6 |

## Invariantes (gate canônico)
1. **1 container único = todos os estados** (anti-desvio inegociável).
2. **Zero credencial** em repositório ou client (apenas env backend-only).
3. **RBAC estrito** por estado (JWT HS256).
4. **Read-only da API Jira** (escrita apenas via script `--apply` com dry-run e snapshot).
5. **Sanitização corporativa** padrão Orion (sem dados sensíveis ou de IA nas tasks/docs públicos).
6. **Hardening Cgroups** (512MB RAM / 1.0 CPU / 150 PIDs / no-new-privileges).
7. **Observabilidade não-poluente** (tabela resumida + gaveta lateral de detalhes).
