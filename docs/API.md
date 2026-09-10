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

### GET `/api/v1/issues/{key}/journey?estado=sc`
Retorna a jornada completa e rastreabilidade do ticket para alimentar o **Drawer Lateral (Gaveta de Observabilidade)**:
- **Stepper Canônico de 7 Etapas**:
  1. `Triagem (N1)`
  2. `Triagem (N2)`
  3. `Análise de Desenvolvimento`
  4. `Em Desenvolvimento`
  5. `Validação Interna / QA`
  6. `Validação / Homologação Cliente`
  7. `Concluído (Entregue)`
- **Posse da Bola**: `tipo` (`egsys` | `cliente`), `label`, `responsavel`, `tempo_etapa`, `tempo_total`.
- **Rastreabilidade de Engenharia (`derivacoes_engenharia`)**: mapeamento em paralelo via Jira Cloud API de tarefas técnicas vinculadas (`fields.issuelinks` como `PSC-3736` derivado de `HDPMSC-389`), com status executivo sanitizado (`status_executivo`), cor, responsável técnico e progresso de subtarefas (`subtasks_concluidas`/`total_subtasks`).
- **Trilha de Auditoria (`transicoes`)**: histórico cronológico extraído do changelog do Jira com datas, atores e movimentações de status.

Exemplo de Resposta:
```json
{
  "referencia": "HDPMSC-389",
  "resumo": "AIT sem agente autuador",
  "status": "Análise de Desenvolvimento",
  "statusCategoria": "indeterminate",
  "area": "Operações",
  "tipo": "Bug Suporte",
  "origem": "cliente",
  "solicitante": "João Mário Mazzola",
  "responsavel": "Erick Vinicius Ferreira da Silva",
  "prioridade": "Normal",
  "criacao": "2026-08-18",
  "atualizacao": "2026-08-19",
  "entrega": null,
  "resolucao": null,
  "etapa_atual": 3,
  "etapas": [
    {"num": 1, "nome": "Triagem (N1)", "estado": "concluido"},
    {"num": 2, "nome": "Triagem (N2)", "estado": "concluido"},
    {"num": 3, "nome": "Análise de Desenvolvimento", "estado": "ativo"},
    {"num": 4, "nome": "Em Desenvolvimento", "estado": "pendente"},
    {"num": 5, "nome": "Validação Interna / QA", "estado": "pendente"},
    {"num": 6, "nome": "Validação / Homologação Cliente", "estado": "pendente"},
    {"num": 7, "nome": "Concluído (Entregue)", "estado": "pendente"}
  ],
  "derivacoes_engenharia": [
    {
      "chave": "PSC-3736",
      "resumo": "AIT sem agente autuador",
      "tipo": "Bug Suporte",
      "status_raw": "Novo",
      "status_executivo": "📋 Na Fila da Engenharia",
      "status_cor": "var(--text-sub)",
      "responsavel": "Mariana Saldanha Coelho",
      "prioridade": "Normal",
      "relacao": "causes",
      "tipo_link": "Problem/Incident",
      "total_subtasks": 0,
      "subtasks_concluidas": 0
    }
  ],
  "posse": {
    "tipo": "egsys",
    "label": "Ação com egSYS",
    "responsavel": "Erick Vinicius Ferreira da Silva",
    "tempo_etapa": "21d 11h",
    "tempo_total": "22 dias"
  },
  "transicoes": [
    {"de": "Validação N2", "para": "Análise de Desenvolvimento", "quando": "2026-08-19 13:14:21", "autor": "João Vitor Sopran"},
    {"de": "Validação N1", "para": "Validação N2", "quando": "2026-08-19 09:16:18", "autor": "Erick Vinicius Ferreira da Silva"},
    {"de": "Aberto", "para": "Validação N1", "quando": "2026-08-19 09:15:14", "autor": "Erick Vinicius Ferreira da Silva"}
  ]
}
```

---

## Segurança
- RBAC por estado; token nunca exposto; credencial Jira backend-only.
- Headers defensivos: HSTS (prod), X-Frame-Options DENY, nosniff, CSP, Referrer-Policy.
- Limite de escrita: nenhum na API pública — API somente leitura do Jira (transições executadas apenas por script com `--apply` autorizado + snapshot).
