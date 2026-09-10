# Roadmap — egSYS JiraView

## v0.1 (atual) — Base do Painel & Experiência Visual
- [x] Container único multi-estado (FastAPI + SPA, RBAC JWT, Jira read-only)
- [x] Painel estilo Jira Dashboard: cards + gráficos (status/prioridade/solicitante/tempo)
- [x] Listagem com colunas do cliente (Tipo, Referência, Resumo, Status, Solicitante,
      Prioridade, Atualização, Entrega)
- [x] Filtros visuais (campo/operador/valor) + JQL livre + filtros salvos por gestor/estado
- [x] Estado SC configurado (HDPMSC + SCPMH; 4 gestores; áreas Cidadão/SADE/Integração/Operações)
- [x] Deploy prod (Traefik path `/painel_sc`, hardening 512m/150pids, cert existente)
- [x] Correção de divergências PSEI-277 (19+18 tickets) + timer diário + snapshots/rollback
- [x] Modo Escuro Full-Window (padrão Orion: `color-scheme: dark !important`, anti-FOUC, persistência)
- [x] Calibração de contraste do Chart.js (ticks transparentes, grids visíveis e textos em alta legibilidade)
- [x] Tríade de Skills Corporativas (`jiraview-commit`, `jiraview-docs-sync`, `jiraview-jira-sync`)
- [x] Configuração Git Dual-Path (`origin` empresa sanitizado vs `privado` backup)

## v0.2 (atual) — Observabilidade, Ciclo Canônico em 7 Etapas & Rastreabilidade de Engenharia
- [x] **Taxonomia do Funil de Atendimento (Eliminação da ambiguidade de "Abertas")**:
  - 📥 **Novas / Não Tratadas** (`statusCategory = new`): tickets recém-criados pelo cliente aguardando triagem/início egSYS.
  - ⚙️ **Em Atendimento / Em Tratamento** (`statusCategory = indeterminate`): tickets em análise, desenvolvimento ou sustentação ativa.
  - ⏸️ **Aguardando Validação / Pendente**: tickets bloqueados aguardando resposta/homologação do cliente ou terceiro.
  - ✅ **Concluídas**: tickets resolvidos no período de referência.
- [x] **Gaveta Lateral de Observabilidade (Drawer — "Jornada do Ticket")**:
  - Tabela principal permanece ágil e limpa (apenas badges essenciais: Área `🏷️ SADE/Cidadão/Integração/Operações` e Fase resumida `📊 3/7 Análise de Desenvolvimento`).
  - Clique na linha abre gaveta lateral direita sem poluir a visão geral.
  - **Stepper Visual Canônico de 7 Etapas**:
    `1. Triagem (N1) ➔ 2. Triagem (N2) ➔ 3. Análise de Desenvolvimento ➔ 4. Em Desenvolvimento ➔ 5. Validação Interna / QA ➔ 6. Validação / Homologação Cliente ➔ 7. Concluído (Entregue)`.
  - **Métricas de Tempo e SLA**: tempo total aberto vs tempo na etapa atual (`SLA da Etapa`).
  - **Posse da Bola (Responsabilidade & Gargalo)**: indicador visual claro de quem está com a ação no momento (`🔵 Ação com a egSYS` vs `🟡 Ação com o Cliente`).
  - **Rastreabilidade de Engenharia (Derivações de Projeto)**: mapeamento paralelo via Jira API de tarefas técnicas vinculadas (`fields.issuelinks` como `PSC-3736` derivado de `HDPMSC-389`), com status executivo sanitizado, responsável técnico e progresso de subtarefas.
  - **Trilha de Auditoria (Changelog de Movimentações)**: linha do tempo com histórico de transições de status e passagem de bastão extraído do Jira.
- [x] **Agregação e Estatística Sem Limite Arbitrário no `/meta` e `/dashboard`**:
  - Mapeamento particionado por JQL e cálculo de funil dinâmico.
- [x] **Chart.js Localmente Vendored**:
  - Dependência Chart.js vendored em `frontend/vendor/chart.umd.min.js` para autonomia total e conformidade com ambientes offline/air-gapped.
- [x] **Simplificação de Filtros**:
  - Remoção da opção 'Interno' no dropdown de Origem, focando no portal do cliente (`Todas` vs `Cliente (portal)`).
- [x] **Identidade & Acesso (RBAC)**:
  - Login unitário real (`/login`, credencial → JWT seguro PBKDF2-HMAC-SHA256)
  - Banco ultraleve nativo SQLite (`auth.db`) com migração automática e persistência em `/app/data`
  - Gestão de usuários no Painel da Coordenação (`/coordenador`) com CRUD completo
  - Troca Obrigatória de Senha no 1º Acesso (`must_change_password`, padrão Orion / SOC 2)
  - Rate limiting (Traefik 100 req/s, burst 50) + headers defensivos (`Server: egSYS-Shield`)

## v0.3 (concluída) — Painel do Coordenador, 73 Espaços & Governança de Acessos
- [x] Painel da Coordenação (`/coordenador`) com visualização de todos os 73 espaços do Jira (PSEI-280)
- [x] Seletor dinâmico de projetos JSM e PSEI para a coordenação de suporte
- [x] Filtros temporais executivos em SC restritos a 4 opções (90d, 6m, 12m, Ano atual)
- [x] Compatibilidade universal de roteamento Traefik para todo o domínio `suporte-monitor.egsys.siseg.tech`

## v0.4 — Produtividade do Gestor & Exportação
- [ ] Filtros compartilhados por estado (equipe)
- [ ] Export CSV/Excel da listagem de tickets e métricas consolidadas
- [ ] Widgets de alerta antecipado ("issues em risco de SLA" e "paradas há mais de X dias")
- [ ] Notificação visual de tickets atualizados recentemente
- [ ] Estados TO/AM/PR/GM ativados (bloco YAML + clientes + papéis)
- [ ] Dashboard consolidado por estado (seletor multi-estado para perfil gestor global)
- [ ] Mapeamento dinâmico de áreas por tenant

## v0.5 — Automação e Governança
- [ ] Regra de automação JSM (workflow/conclusão) substituindo script-timer quando permitido
- [ ] Métricas de SLA por área/estado com histórico de conformidade
- [ ] Descomissionamento do painel Node-RED `noc-jira` legado

## Backlog técnico
- [ ] Testes pytest (RBAC, chamadas Jira mockadas, cálculo do funil) + gate `ruff`
- [ ] CI (GitHub Actions) com sanitização de segredos e credenciais
- [ ] Migração do token Jira para cofre seguro no servidor

