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

## v0.2 — Observabilidade & Jornada do Ticket (em planejamento)
- [ ] **Taxonomia do Funil de Atendimento (Eliminação da ambiguidade de "Abertas")**:
  - 📥 **Novas / Não Tratadas** (`statusCategory = new`): tickets recém-criados pelo cliente aguardando triagem/início egSYS.
  - ⚙️ **Em Atendimento / Em Tratamento** (`statusCategory = indeterminate`): tickets em análise, desenvolvimento ou sustentação ativa.
  - ⏸️ **Aguardando Validação / Pendente**: tickets bloqueados aguardando resposta/homologação do cliente ou terceiro.
  - ✅ **Concluídas**: tickets resolvidos no período de referência.
- [ ] **Gaveta Lateral de Observabilidade (Drawer — "Jornada do Ticket")**:
  - Tabela principal permanece ágil e limpa (apenas badges essenciais: Área `🏷️ SADE/Cidadão/Integração/Operações` e Fase resumida `Etapa 2/5`).
  - Clique na linha abre gaveta lateral direita sem poluir a visão geral.
  - **Stepper Visual de 5 Etapas**:
    `1. Triagem (NOC/N1) ➔ 2. Em Análise/Dev (N2/N3) ➔ 3. Validação Interna / QA ➔ 4. Homologação Cliente ➔ 5. Concluído`.
  - **Métricas de Tempo e SLA**: tempo total aberto vs tempo na etapa atual (`SLA da Etapa`).
  - **Posse da Bola (Responsabilidade)**: indicador visual claro de quem está com a ação no momento (`🔵 egSYS - Suporte/Dev` vs `🟡 Cliente - Validação`).
  - **Trilha de Auditoria (Changelog de Movimentações)**: linha do tempo com histórico de transições de status e passagem de bastão extraído do Jira.
- [ ] **Agregação e Estatística Sem Limite Arbitrário no `/meta`**:
  - Eliminar o cap de 100 tickets no cálculo de distribuição de status (`contagem` via agregação completa paginada ou JQL particionado).
- [ ] **Identidade & Acesso (RBAC)**:
  - Login real (credencial → JWT + refresh), sem `demo-token` em produção
  - Seed de usuários/papéis por estado (a partir de `estados.yaml`)
  - Rate limiting + proteção de força bruta no login

## v0.3 — Produtividade do Gestor & Exportação
- [ ] Filtros compartilhados por estado (equipe)
- [ ] Export CSV/Excel da listagem de tickets e métricas consolidadas
- [ ] Widgets de alerta antecipado ("issues em risco de SLA" e "paradas há mais de X dias")
- [ ] Notificação visual de tickets atualizados recentemente

## v0.4 — Federação Multi-Estado
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

