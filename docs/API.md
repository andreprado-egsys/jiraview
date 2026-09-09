# API — egSYS JiraView

Base: `https://suporte-monitor.egsys.siseg.tech/painel_sc` (prod) · local `:8090`
Auth: `Authorization: Bearer <JWT>` (RBAC: `viewer` < `manager` < `admin` por estado).

## Endpoints

### GET `/api/v1/health`
Alive + checagem leve do Jira. **Público** (sem auth).
```json
{"status":"ok","jira":true}
```

### GET `/api/v1/issues?estado=sc&status_filter=&tipo=&jql=&abertas=true&max_results=50`
Listagem com colunas do painel. **Auth obrigatório** (viewer do estado).
- `status_filter`/`tipo` — filtros visuais; `jql` — filtro livre do gestor
- `abertas=true` — adiciona `resolution is EMPTY`
Resposta: `issues[{tipo,referencia,resumo,status,statusCategoria,solicitante,responsavel,prioridade,atualizacao,criacao,entrega,resolucao}]`

### GET `/api/v1/dashboard?estado=sc`
Cards: `abertas`, `em_andamento`, `fechadas_7d`, `por_status`, `projetos`.

### GET `/api/v1/charts?estado=sc`
Gráficos: `por_status`, `por_prioridade`, `por_solicitante` (top 6), `por_dia` (série 15 dias), `total`.

### GET `/api/v1/meta?estado=sc`
`statuses[]`, `tipos[]` — opções dos filtros (dinâmico do Jira).

### GET|POST `/api/v1/filtros?estado=sc` · DELETE `/api/v1/filtros/{id}?estado=sc`
Filtros JQL salvos por gestor+estado (persistência `data/filtros.json`, 0600).
POST exige `role >= manager`.

### POST `/api/v1/demo-token` — ⚠️ **DEV ONLY** (produção: substituir por auth real)

## Segurança
- RBAC por estado; token nunca exposto; Jira credencial backend-only.
- Headers: HSTS (prod), X-Frame-Options DENY, nosniff, CSP, Referrer-Policy.
- Limite de escrita: nenhum — API somente leitura do Jira (transições
  executadas apenas por script com `--apply` autorizado + snapshot).
