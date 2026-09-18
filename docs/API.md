# API — egSYS JiraView

Base: `https://suporte-monitor.egsys.siseg.tech` (prod) · local `:8090`
Auth: `Authorization: Bearer <JWT>` (Matriz Canônica de RBAC em 5 Níveis: `monitor` = Nível 1 | `viewer`/`manager` = Nível 1 | `n1` = Nível 2 | `n2` = Nível 3 | `coordenador` = Nível 4).

## Endpoints de Autenticação & Gestão de Acessos

### POST `/api/v1/auth/login`
Autentica usuário cadastrado no banco SQLite e retorna JWT com URL de direcionamento específico e flag de primeiro acesso. **Público**.
- **Perfil Geral**: Token JWT padrão com validade de 24 horas.
- **Perfil Kiosk Wallboard (`monitor`)**: Gera automaticamente **token de longa duração válido por 365 dias**, viabilizando execução ininterrupta em televisores e monitores de sala de suporte sem expiração de sessão e sem exigência de troca de senha (`must_change_password=0`).

Payload:
```json
{"username": "gestor.sc", "password": "egsys@sc2026"}
```
Resposta:
```json
{
  "token": "eyJhbGciOi...",
  "token_type": "bearer",
  "redirect_url": "/painel_sc",
  "user": {
    "username": "gestor.sc",
    "nome": "Gestão PMSC (Santa Catarina)",
    "role": "manager",
    "estado": "sc",
    "painel_url": "/painel_sc",
    "must_change_password": true
  }
}
```

### POST `/api/v1/auth/change-password`
Atualiza a senha do próprio usuário conectado (usado obrigatoriamente no 1º acesso ou em redefinição voluntária). **Auth obrigatório**.
- Valida tamanho mínimo de 6 caracteres (HTTP 400 se menor).
- Invalida a flag de primeiro acesso (`must_change_password = 0`).
- Retorna novo JWT já liberado.
Payload:
```json
{"new_password": "novaSenhaSegura@2026"}
```

### GET `/api/v1/auth/me`
Retorna dados cadastrais do operador autenticado via token Bearer. **Auth obrigatório**.

### GET `/api/v1/auth/users`
Lista todos os usuários cadastrados no banco SQLite. **Acesso autorizado via `require_user_manager` (`coordenador` e `n2`)**.

### POST `/api/v1/auth/users`
Cadastra novo operador no sistema com direcionamento estadual. **Acesso autorizado via `require_user_manager` (`coordenador` e `n2`)**.
- **Salvaguarda N2**: Analistas N2 só podem cadastrar contas com papéis `n1`, `monitor`, `viewer` ou `manager`. Tentativas de criar `coordenador` ou `n2` retornam **HTTP 403 Forbidden**.
Payload:
```json
{
  "username": "gestor.to",
  "password": "egsys@to2026",
  "nome": "Gestão PMTO (Tocantins)",
  "role": "manager",
  "estado": "to",
  "espacos": "HDPMTO,STO",
  "painel_url": "/painel_to",
  "is_active": 1,
  "must_change_password": 1
}
```

### PUT `/api/v1/auth/users/{user_id}`
Atualiza dados cadastrais, espaços autorizados (`espacos`), redefine senha ou ativa/desativa usuário. **Acesso autorizado via `require_user_manager` (`coordenador` e `n2`)**.
- **Salvaguarda N2**: Analistas N2 são estritamente impedidos de alterar ou resetar senhas de usuários com nível hierárquico maior ou igual ao seu (`coordenador` ou `n2`), retornando **HTTP 403 Forbidden**.

### DELETE `/api/v1/auth/users/{user_id}`
Remove usuário da base SQLite. **Acesso autorizado via `require_user_manager` (`coordenador` e `n2`)**.
- Impede que o operador conectado exclua a própria conta.
- **Salvaguarda N2**: Bloqueia exclusão de contas com papel `coordenador` ou `n2` (retorna **HTTP 403 Forbidden**).

## Endpoints de Monitoramento & Métricas JSM

### GET `/api/v1/health`
Alive + checagem leve do Jira. **Público** (sem auth).
```json
{"status":"ok","jira":true}
```

### GET `/api/v1/overview`
Visão resumida das solicitações do estado do usuário logado (`role >= viewer`).
Retorna: `role`, `state`, `issues[]`.

### GET `/api/v1/issues?estado=sc&projetos=HDPMSC,SSC&status_filter=&tipo=&origem=&jql=&abertas=true&periodo=90d&max_results=250&funil_stage=`
Listagem principal do painel com colunas normalizadas e paginação oficial por cursor. **Auth obrigatório** (viewer do estado/espaços autorizados).
- `estado` — sigla do estado (`sc`, `to`, `am`, etc.).
- `projetos` ou `espacos` — lista de projetos/espaços Jira separados por vírgula para consolidação multi-espaço (ex.: `HDPMSC,SSC`).
- `status_filter` / `tipo` — filtros visuais por dropdown
- `origem` — filtro por tipo de solicitante (`cliente` para contas `qm:*` vs `interno` para agentes)
- `jql` — filtro JQL livre ou composto pelo construtor visual
- `abertas=true` — aplica `resolution is EMPTY`
- `periodo` — janela temporal estrita (`30d`, `60d`, `90d`, `6m`, `12m`, `ano` nos painéis de clientes; `todos` exclusivo para Coordenação/Admin)
- `max_results` — limite de tickets retornados (padrão `250`, integrado com `search_full` via cursor `nextPageToken` da API Jira Cloud v3, eliminando truncamento)
- `funil_stage` — filtro semântico por estágio da esteira: `novas` (inclui Triagem N1 e Validação N2), `em_atendimento` (Análise de Dev, Executando e QA), `aguardando_validacao` ou `concluidas`
Resposta:
```json
{
  "issues": [
    {
      "tipo": "Bug Suporte",
      "origem": "interno",
      "referencia": "HDPMSC-403",
      "espaco": "HDPMSC",
      "resumo": "ERRO INTEGRAÇÃO SADE WEB E DIFICULDADE DE ACESSO",
      "status": "Validação N2",
      "statusCategoria": "indeterminate",
      "area": "Integração",
      "faseNum": 2,
      "faseNome": "Triagem (N2)",
      "posse": "egsys",
      "posseLabel": "Ação com egSYS",
      "solicitante": "Erick Vinicius Ferreira da Silva",
      "responsavel": "Erick Vinicius Ferreira da Silva",
      "prioridade": "Normal",
      "atualizacao": "2026-09-17",
      "criacao": "2026-09-17",
      "entrega": null,
      "resolucao": null
    }
  ],
  "total": 1
}
```

### GET `/api/v1/dashboard?estado=sc&projetos=HDPMSC,SSC&periodo=90d`
Cards métricos agregados estilo Jira Dashboard com governança estrita de período:
- `funil` — objeto com contagens do funil de atendimento:
  ```json
  {
    "novas": 2,
    "em_atendimento": 20,
    "aguardando_validacao": 0,
    "concluidas": 23
  }
  ```
- `abertas` (novas / Triagem N1-N2: 2)
- `em_andamento` (em tratamento técnico Dev/QA: 20)
- `aguardando_validacao` (homologação cliente: 0)
- `concluidas` (resolvidas no período: 23)
- `fechadas_7d` (concluídas nos últimos 7 dias: 2)
- `por_status` (mapa nome_status ➔ total)
- `por_origem` (`cliente_new`, `cliente_ind`, `cliente_done`, `interno_new`, etc.)
- `por_tipo` (mapa nome_tipo ➔ total)
- `total_geral` (soma exata da carteira ativa + concluídas no período: 45 em 90d; 350 em Todos os Períodos)
- `total_com_resolucao`

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
- **Stepper Canônico de 8 Etapas**:
  1. `Triagem (N1)`
  2. `Triagem (N2)`
  3. `Análise de Desenvolvimento`
  4. `Em Desenvolvimento`
  5. `Testes de Qualidade (QA)` *(Fase autônoma do time de QA)*
  6. `Validação Interna (Suporte N1)` *(Fase de validação do Suporte N1)*
  7. `Validação / Homologação Cliente`
  8. `Concluído (Entregue)`
- **Posse da Bola**: `tipo` (`egsys` | `cliente`), `label`, `responsavel`, `tempo_etapa`, `tempo_total`.
- **Links Diretos 1-Click para o Jira Cloud**: URLs canônicas (`https://egsys.atlassian.net/browse/{key}`) para navegação imediata ao ticket oficial ou itens vinculados.
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
    {"num": 5, "nome": "Testes de Qualidade (QA)", "estado": "pendente"},
    {"num": 6, "nome": "Validação Interna (Suporte N1)", "estado": "pendente"},
    {"num": 7, "nome": "Validação / Homologação Cliente", "estado": "pendente"},
    {"num": 8, "nome": "Concluído (Entregue)", "estado": "pendente"}
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

## Endpoints das Extensões Modulares (NOC, Esteiras, Relatórios & Certificados SSL)

A partir da versão v0.5.0 (PSEI-312 a PSEI-319), o JiraView absorveu e modernizou as esteiras de governança técnica e alertas corporativos. Todos os endpoints abaixo exigem cabeçalho `Authorization: Bearer <JWT>` e permissão modular correspondente.

### GET `/api/v1/modules/catalog`
Retorna o catálogo de módulos operacionais disponíveis no sistema e se estão habilitados para o operador conectado.
```json
{
  "is_admin": true,
  "modules": [
    {"id": "analise_dev", "nome": "Esteira de Análise de Dev", "habilitado": true},
    {"id": "triagem_n1n2", "nome": "Esteira de Triagem N1/N2", "habilitado": true},
    {"id": "relatorio_email", "nome": "Relatórios Executivos & Destinatários", "habilitado": true},
    {"id": "certificados_alert", "nome": "Monitor de Certificados SSL", "habilitado": true}
  ]
}
```

### GET `/api/v1/modules/analise-dev/issues`
Retorna todas as tarefas da esteira de Análise de Desenvolvimento em tempo real no Jira Cloud, agrupadas por estado/projeto (SC, PR, AM, TO, RO, GM) com alertas de SLA (&ge; 7d e &ge; 10d).
Retorna: `total`, `hasAlert`, `hasCritico10d`, `grupos[]`, `issues[]`.

### GET `/api/v1/modules/triagem-n1n2/issues`
Retorna todos os tickets em triagem inicial de suporte (N1 e N2) em tempo real, particionados por estado com cálculo de tempo em aberto e severidade.
Retorna: `total`, `hasAlert`, `hasCritico10d`, `grupos[]`, `issues[]`.

### POST `/api/v1/modules/reports/trigger-analise-dev`
Dispara o envio manual do Relatório Executivo semanal da Esteira de Análise de Desenvolvimento por e-mail via SMTP corporativo (`smtp.gmail.com:587`, remetente `orion@egsys.com.br`) para os destinatários cadastrados com `relatorio_executivo = 1`.
Payload opcional:
```json
{"destinatarios": "diretoria@egsys.com.br, gerente@egsys.com.br"}
```

### GET `/api/v1/modules/reports/history`
Retorna os últimos 20 envios de relatórios e alertas efetuados pelo sistema com status, data/hora, quantidade de tarefas e mensagem de resposta do servidor SMTP.

### GET `/api/v1/modules/recipients`
Lista todos os destinatários corporativos de e-mails cadastrados no banco SQLite (`email_recipients`).
Retorna: `recipients: [{"id": 1, "nome": "...", "email": "...", "relatorio_executivo": 1, "alertas_certificados": 1, "ativo": 1}]`.

### POST `/api/v1/modules/recipients`
Cadastra novo destinatário de relatórios e/ou alertas.
Payload:
```json
{
  "nome": "Equipe de Infraestrutura",
  "email": "infra@egsys.com.br",
  "relatorio_executivo": 0,
  "alertas_certificados": 1
}
```

### PUT `/api/v1/modules/recipients/{id}`
Atualiza flags de notificação, nome, e-mail ou ativação (`ativo: 0/1`) de um destinatário existente.

### DELETE `/api/v1/modules/recipients/{id}`
Remove um destinatário do cadastro corporativo.

### GET `/api/v1/modules/certificates`
Retorna a lista completa de domínios e certificados SSL monitorados da infraestrutura egSYS, com cruzamento de dados do Google Sheets e Traefik, validade, dias restantes e cálculo de KPIs:
- `total`: Total de domínios cadastrados (ex.: 92)
- `ok`: Em dia (> 30 dias)
- `alerta`: Janela preventiva (&le; 30 dias)
- `criticos`: Críticos (&le; 15 dias)
- `vencidos`: Já expirados
- `itens_alerta`: Lista de domínios críticos e vencidos contendo `domain`, `host`, `state` (normalizado para agrupamento hierárquico por estado), `vence_em`, `dias` e `precisa_token`.

### POST `/api/v1/modules/certificates/sync`
Sincroniza os domínios com a planilha mestre do Google Sheets (`1yO1L72qkR1-SXSBGrYtTe9xtm1QCSVcfKqRqzSjbtGU`) e executa probe SSL TLS direto via socket para atualizar `valid_from` e `valid_until`.

### POST `/api/v1/modules/certificates/sync-traefik`
Lê os certificados gerenciados automaticamente pelo Traefik (`acme.json`) no host de monitoramento e sincroniza os prazos e emissores Let's Encrypt.

### POST `/api/v1/modules/certificates/send-alert`
Audita todos os certificados em estado crítico ou vencido (&le; 15 dias) e em janela de alerta (&le; 30 dias) e dispara e-mail formatado aos destinatários cadastrados com `alertas_certificados = 1`.

### GET `/api/v1/modules/noc/layout/{tipo}`
Retorna a disposição customizada de colunas e cards salva para a esteira especificada (`tipo: 'dev'`, `'n1n2'` ou `'cert'`).
```json
{
  "status": "ok",
  "layout": {
    "numCols": "3",
    "columns": [["SC", "PR"], ["AM", "TO"], ["RO", "GM"]]
  }
}
```

### POST `/api/v1/modules/noc/layout/{tipo}`
Persiste a disposição customizada de colunas e cards no banco SQLite (`auth.db`), tabela `noc_layouts` (`tipo: 'dev'`, `'n1n2'` ou `'cert'`).
Payload:
```json
{
  "tipo": "cert",
  "num_cols": "3",
  "columns": [["SC", "PR"], ["AM", "TO"], ["RO", "GM"]]
}
```

---

## Segurança
- RBAC por estado; token nunca exposto; credencial Jira backend-only.
- Headers defensivos: HSTS (prod), X-Frame-Options DENY, nosniff, CSP, Referrer-Policy.
- Limite de escrita: nenhum na API pública — API somente leitura do Jira (transições executadas apenas por script com `--apply` autorizado + snapshot).

