# API — egSYS JiraView

Base: `https://suporte-monitor.egsys.siseg.tech/painel_sc` (prod) · local `:8090`
Auth: `Authorization: Bearer <JWT>` (RBAC: `viewer` < `manager` < `admin` por estado).

## Endpoints Atuais

### GET `/api/v1/health`
Alive + checagem leve do Jira. **Público** (sem auth).
```json
{"status":"ok","jira":true}
```

### GET `/api/v1/overview`
Visão resumida das solicitações do estado do usuário logado (`role >= viewer`).
Retorna: `role`, `state`, `issues[]`.

### GET `/api/v1/issues?estado=sc&status_filter=&tipo=&origem=&jql=&abertas=true&periodo=90d&max_results=50`
Listagem principal do painel com colunas normalizadas. **Auth obrigatório** (viewer do estado).
- `status_filter` / `tipo` — filtros visuais por dropdown
- `origem` — filtro por tipo de solicitante (`cliente` para contas `qm:*` vs `interno` para agentes)
- `jql` — filtro JQL livre ou composto pelo construtor visual
- `abertas=true` — aplica `resolution is EMPTY`
- `periodo` — janela de criação (`ano`, `90d`, `6m`, `12m`)
Resposta:
```json
{
  "issues": [
    {
      "tipo": "Incidente",
      "origem": "cliente",
      "referencia": "HDPMSC-1234",
      "resumo": "Lentidão na consulta CAD",
      "status": "Em Atendimento",
      "statusCategoria": "indeterminate",
      "solicitante": "Capitão Silva",
      "responsavel": "Equipe Sustentação SADE",
      "prioridade": "Alta",
      "atualizacao": "2026-09-09",
      "criacao": "2026-09-08",
      "entrega": "2026-09-15",
      "resolucao": null
    }
  ],
  "total": 1
}
```

### GET `/api/v1/dashboard?estado=sc&periodo=90d`
Cards métricos agregados estilo Jira Dashboard:
- `abertas` (novas / statusCategory `new`)
- `em_andamento` (em tratamento / statusCategory `indeterminate`)
- `fechadas_7d` (concluídas nos últimos 7 dias)
- `por_status` (mapa nome_status ➔ total)
- `por_origem` (`cliente_new`, `cliente_ind`, `cliente_done`, `interno_new`, etc.)
- `por_tipo` (mapa nome_tipo ➔ total)
- `total_geral` e `total_com_resolucao`

### GET `/api/v1/charts?estado=sc&periodo=90d`
Agregados formatados para renderização no Chart.js:
- `por_status` (Top 15 status mais frequentes)
- `por_prioridade` (distribuição por criticidade)
- `por_solicitante` (Top 6 solicitantes)
- `por_tipo` (distribuição por tipo de chamado)
- `por_dia` (série cronológica dos últimos 15 dias para gráfico de linha)
- `total`

### GET `/api/v1/meta?estado=sc`
Metadados dinâmicos populados diretamente do Jira:
- `statuses[]` (`[{name: "Em Atendimento", tickets: 23}, ...]`)
- `tipos[]` (`["Incidente", "Melhoria", "Dúvida", ...]`)

### GET|POST `/api/v1/filtros?estado=sc` · DELETE `/api/v1/filtros/{id}?estado=sc`
CRUD de filtros JQL personalizados salvos por gestor e por estado (persistência em `data/filtros.json`, 0600).
POST/DELETE exigem `role >= manager`.

### POST `/api/v1/demo-token` — ⚠️ **DEV ONLY** (produção: substituir por auth real)

---

## Endpoints Planejados (v0.2 — Observabilidade & Jornada)

### GET `/api/v1/issues/{key}/journey?estado=sc`
Retorna a jornada do ticket para alimentar o **Drawer Lateral (Gaveta de Observabilidade)**:
```json
{
  "key": "HDPMSC-1234",
  "etapa_atual": 2,
  "etapas": [
    {"num": 1, "nome": "Triagem", "status": "concluido", "data_inicio": "2026-09-08T09:00:00", "duracao": "2h 15m"},
    {"num": 2, "nome": "Em Análise / Dev", "status": "em_andamento", "data_inicio": "2026-09-08T11:15:00", "duracao": "1d 4h"},
    {"num": 3, "nome": "Validação Interna / QA", "status": "pendente"},
    {"num": 4, "nome": "Homologação Cliente", "status": "pendente"},
    {"num": 5, "nome": "Concluído", "status": "pendente"}
  ],
  "posse_bola": {
    "responsavel": "egSYS - Suporte / Dev",
    "tipo": "egsys",
    "desde": "2026-09-08T11:15:00"
  },
  "historico_transicoes": [
    {"de": "Aberto", "para": "Em Atendimento", "quando": "2026-09-08T11:15:00", "autor": "Atendente N1"}
  ]
}
```

---

## Segurança
- RBAC por estado; token nunca exposto; credencial Jira backend-only.
- Headers defensivos: HSTS (prod), X-Frame-Options DENY, nosniff, CSP, Referrer-Policy.
- Limite de escrita: nenhum na API pública — API somente leitura do Jira (transições executadas apenas por script com `--apply` autorizado + snapshot).
