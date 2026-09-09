# Roadmap — egSYS JiraView

## v0.1 (atual) — Base do Painel
- [x] Container único multi-estado (FastAPI + SPA, RBAC JWT, Jira read-only)
- [x] Painel estilo Jira Dashboard: cards + gráficos (status/prioridade/solicitante/tempo)
- [x] Listagem com colunas do cliente (Tipo, Referência, Resumo, Status, Solicitante,
      Prioridade, Atualização, Entrega)
- [x] Filtros visuais (campo/operador/valor) + JQL livre + filtros salvos por gestor/estado
- [x] Estado SC configurado (HDPMSC + SCPMH; 4 gestores; áreas Cidadão/SADE/Integração/Operações)
- [x] Deploy prod (Traefik path `/painel_sc`, hardening 512m/150pids, cert existente)
- [x] Correção de divergências PSEI-277 (19+18 tickets) + timer diário + snapshots/rollback

## v0.2 — Identidade & Acesso (próximo)
- [ ] Login real (credencial → JWT + refresh), sem `demo-token` em produção
- [ ] Seed de usuários/papéis por estado (a partir de `estados.yaml`)
- [ ] Rate limiting + proteção de força bruta no login
- [ ] Auditoria de acesso (login, filtros usados) com retenção

## v0.3 — Productividade do Gestor
- [ ] Filtros compartilhados por estado (equipe)
- [ ] Export CSV/Excel da listagem
- [ ] Widgets "issues em risco" (due date, SLA)
- [ ] Detalhe do ticket (painel lateral com comentários e transições)

## v0.4 — Multi-estado
- [ ] Estados TO/AM/PR/GM ativados (bloco YAML + clientes + papéis)
- [ ] Dashboard consolidado por estado (seletor) + visão geral corporativa

## v0.5 — Automação e Governança
- [ ] Regra de automação JSM (workflow/conclusão) substituindo script-timer quando permitido
- [ ] Métricas de SLA por área/estado
- [ ] Integração com painel corporativo existente (Node-RED `noc-jira` migrado/descomissionado)

## Backlog técnico
- [ ] Testes pytest (RBAC, chamadas Jira mockadas) + gate `ruff`
- [ ] CI (GitHub Actions) com sanitização de secrets
- [ ] Migração do token Jira para cofre/secrets no servidor
