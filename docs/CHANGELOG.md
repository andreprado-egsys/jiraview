# egSYS JiraView — Changelog

## [0.4.3] — 2026-09-17 (PSEI-311)

### Fixed
- `fix(funil-search): Alinhamento Canônico entre Cards e Busca (/issues?funil_stage)` — correção na cláusula de consulta do estágio `novas` para contemplar tarefas no status `Validação N2` (pertencente à categoria Atlassian *In Progress* / Etapa 2 de 8, ex: `HDPMSC-403` e `HDPMSC-388`). O endpoint `/issues` agora utiliza a mesma lógica semântica `_detectar_fase` do `/dashboard`, eliminando a discrepância de "0 solicitações encontradas" ao clicar no card.
- `fix(pagination): Implementação de Cursor Pagination via 'nextPageToken' (Atlassian v3)` — correção no cliente `JSMService` (`backend/app/core/security.py`) adicionando o método `search_full`. O Jira Cloud depreciou o deslocamento numérico (`startAt`), o que causava duplicação de páginas em consultas com mais de 100 itens (exibindo 2.000 chamados duplicados em 12 meses). Com o cursor tokenizado, as consultas trazem com exatidão a totalidade desduplicada de chamados (209 em 12m e 105 no Ano Atual 2026).
- `fix(rbac-reporters): Visibilidade Integral da Carteira Estadual para Gestores Contratuais` — remoção da injeção incondicional da lista de contas do portal do cliente no JQL em `backend/app/api/v1.py`. Gestores Estaduais (perfil `manager`, como o Sr. Mazzola) agora enxergam a esteira técnica completa de Santa Catarina (demandas abertas pela PM e demandas técnicas abertas pela engenharia egSYS para a PMSC), preservando o seletor `Origem: Todas / Cliente (portal)` para quando o cliente desejar isolar apenas as suas aberturas.
- `fix(temporal-consistency): Unificação Estrita de Período nos Cards, Backlog Ativo e Tabela` — equalização definitiva da régua temporal: ao selecionar um período (ex.: `90d`), todos os cards (Novas: 2, Em Atendimento: 20, Ativas: 22, Concluídas: 23, Total Geral: 45) e a listagem de chamados refletem com 100% de precisão as tarefas daquela janela. O painel do cliente/gestor estadual restringe o seletor estritamente às janelas contratuais operacionais (30d, 60d, 90d padrão, 6m, ano atual e 12m), preservando a opção "Todos os Períodos (Histórico Completo)" (58 ativas, 292 concluídas, 350 no total) como ferramenta exclusiva da governança no painel da coordenação (`coordenador.html`).
- `fix(pagination-cap): Fim do Truncamento de 50 Itens em /issues` — ampliação do teto e integração nativa com `search_full` (cap padrão 250), garantindo que ao clicar em qualquer card do Dashboard (Card 4: 58 ativas, Card 2: 56 em atendimento) a tabela liste 100% dos chamados sem cortes.
- `fix(ui-placeholders): Remoção de Valores Estáticos Hardcoded no Banner de Síntese` — neutralização dos textos iniciais no banner executivo (`index.html`) para evitar exibição de números desatualizados antes da resposta da API.

## [0.4.2] — 2026-09-17 (PSEI-310)

### Added
- `feat(multi-space-client): Suporte a Múltiplos Espaços para Clientes & Gestores Estaduais` — arquitetura que permite configurar múltiplos espaços Jira autorizados por usuário no banco SQLite (`auth.db`) através da coluna `espacos` (ex.: `HDPMSC,SSC` para o gestor Mazzola — João Mário Mazzola). No painel do cliente (`/painel_sc` / `index.html`), o sistema detecta a configuração e exibe a barra executiva interativa com chips dinâmicos: `Todos os Meus Espaços (HDPMSC + SSC)`, `PMSC [HDPMSC]` e `Suporte SC [SSC]`.
- `feat(multi-space-coord): Seletor e Customização Multi-Espaço Simultânea para Coordenação` — ferramenta de seleção personalizada no painel da coordenação (`coordenador.html`) permitindo selecionar e consolidar quaisquer combinações entre os 73 projetos corporativos do Jira ao mesmo tempo (com atalhos rápidos de 1 clique: PMSC + Suporte SC, Santa Catarina Completo, Tocantins, Amazonas, Rondônia, Paraná, Operações Internas).
- `feat(dashboard-multi): Métricas, Banner, Funil e Gráficos Consolidados em Tempo Real` — cálculo automático de equação matemática do backlog (`Novas + Em Atendimento + Aguardando Cliente = Backlog Ativo`), KPIs e gráficos comparativos side-by-side de volume por espaço e esteira de 8 etapas na união dos projetos selecionados.
- `feat(table-badges): Identificação de Espaço por Chamado` — renderização automática de coluna e badge semântica (`t.espaco`) na tabela de chamados sempre que múltiplos espaços estão em visualização.
- `feat(auth-mgmt): Gestão Completa de Espaços e Edição de Usuários na Coordenação` — inclusão de campo de espaços no formulário de cadastro de novo usuário, coluna de badges de espaços na tabela de usuários e modal moderno de edição (`#modalEditarUsuario`) para atualizar dados cadastrais, perfil, estado e espaços autorizados via `PUT /api/v1/auth/users/{id}`.

### Changed
- `api(v1): Suporte a Parâmetros 'projetos' e 'espacos' com Validação Estrita RBAC` — endpoints `/issues`, `/dashboard`, `/charts` e `/meta` atualizados para aceitar listas de projetos separadas por vírgula, garantindo acesso irrestrito para coordenação e contenção rigorosa aos espaços autorizados para perfis de cliente/gestor.
- `db(auth): Migração Idempotente de Coluna 'espacos TEXT DEFAULT '''` — garantia de integridade do banco `data/auth.db` via `PRAGMA table_info` com seeding do usuário corporativo `mazzola`.

## [0.4.1] — 2026-09-15 (PSEI-309)

### Added
- `docs(presentation-sc): Tríade Executiva de Apresentação Exclusiva PMSC (PPTX + PDF + MD) (`docs/egSYS-JiraView-PMSC-Executivo.*`)` — elaboração de deck sob medida de 8 slides para o Comando e TI da Polícia Militar de Santa Catarina (Mazzola, Ilclemar, Alex Sandro, Cap Thiesen), detalhando a decomposição exata dos 25 chamados ativos (0 Novas + 24 Em Atendimento + 1 Aguardando Validação PMSC), o isolamento do histórico de 25 concluídas no ciclo de 90 dias, a navegação nas 4 frentes da PM (Cidadão 190/Mobile, SADE CAD, Integração e Operações), a esteira de 8 etapas com Posse da Bola e a exportação nativa em Excel (.xlsx). Script gerador dedicado em `scripts/generate_jiraview_sc_deck.py`.
- `docs(presentation): Tríade Executiva de Apresentação (PPTX + PDF + MD) no Padrão CEO (`docs/egSYS-JiraView-CEO-Executivo.*`)` — geração de deck de alta densidade visual (16:9 Widescreen, Dark Glass / Slate, Aptos Display) composto por 8 slides canônicos: 1) Capa & Executive Brief, 2) O Desafio & Riscos Legados, 3) A Virada Arquitetural (Container Único), 4) Impacto Mensurado & ROI (-90% Diagnóstico, 100% Precisão Backlog com 25 ativas e 25 entregas), 5) Raio-X & Metodologia de Evidências, 6) Operação Blindada & Esteira de 8 Etapas, 7) Escala Multi-Estado (<15min onboarding, Cgroups 512MB) e 8) Roadmap & Síntese de Valor. Exportação automatizada de PDF vetorial via LibreOffice headless e script gerador parametrizado (`scripts/generate_jiraview_ceo_deck.py`).
- `docs(executive): Documento Executivo Canônico e Pleno de Projeto (`docs/DOCUMENTO_EXECUTIVO_PROJETO.md`)` — elaboração de documento executivo amplo e abrangente estruturado nos 4 pilares: Engenharia de Software (Clean Architecture, container único multi-estado em `estados.yaml`, esteira canônica de 8 etapas, `issuelinks`), Observabilidade & Psicologia da Informação (3 níveis cognitivos, banner de síntese matemática de backlog com 25 tarefas ativas e isolamento de 25 concluídas no ciclo de 90 dias, teoria da posse da bola), SRE & Infraestrutura (Cgroups 512MB/1.0 CPU/150 PIDs, Traefik prioridade 1000, hardening ACH-011, paridade via `sync_db.py`, SLO/SLA) e Gestão, Governança & DevSecOps (RBAC por estado, hashing NIST PBKDF2-HMAC-SHA256, 1º acesso obrigatório, RACI e governança Docs-as-Code).
- `feat(dashboard): Banner Executivo de Síntese Matemática do Backlog` — incorporação de banner de síntese executiva no topo de todos os painéis (`coordenador.html` e `index.html`), evidenciando a decomposição matemática exata da carteira ativa do cliente: `0 Novas + 24 Em Atendimento + 1 Aguardando Validação = 25 Chamados em Aberto`, com isolamento explícito do histórico de 25 entregas finalizadas no ciclo padrão de 90 dias.
- `feat(filters): Filtros Temporais Granulares e Governança de Histórico` — introdução de seletores de período de 30 dias (`30d`), 60 dias (`60d`), 90 dias (`90d` - padrão contratual), 6 meses (`6m`), 12 meses (`12m`) e ano atual (`ano`), mantendo a opção de `Todos os Períodos (Histórico Completo)` restrita estritamente ao painel da coordenação (`coordenador.html`), sem poluir a visão operacional do cliente.
- `feat(dashboard): Card Total Backlog Ativo & Badges Semânticas do Funil` — card dedicado de fechamento da conta (`Total Backlog Ativo`) e inclusão de badges categorizando os componentes da esteira (`Componente 1/3, 2/3 e 3/3 do Backlog Ativo` vs `Histórico Fora do Backlog Aberto`).
- `feat(ui): Numeração Sequencial (#: 1 a N) em Todas as Listagens e Exportações` — coluna `#` numerada de 1 a N nas tabelas e integrada aos arquivos exportados (`Markdown`, `Excel` e `CSV`) em ambos os painéis.
- `feat(ops): Script Canônico de Pareamento e Sincronização de Banco (`scripts/sync_db.py`)` — ferramenta de automação com suporte a `--status`, `--pull` e `--push` para garantir paridade contínua e backups preventivos entre o banco SQLite local e a produção (`monitoramento-egsys`).

### Fixed
- `fix(classifier): Derivação Determinística de Estágios do Ticket` — implementação da função `derivarEstagio(t)` nos painéis (`coordenador.html`), garantindo que tickets já concluídos (`etapaNum: 8`, ex: HDPMSC-401) ou em fases técnicas da engenharia (ex: HDPMSC-400) nunca caiam erroneamente na coluna "Novas / Triagem (N1/N2)".
- `fix(stepper): Reatividade Imediata de Status e Etapas no Drawer Lateral` — sincronização em tempo real na memória e na linha da tabela assim que a radiografia de workflow retorna da API/Jira Cloud.
- `fix(cache): Paridade da Base PMSC com 77 Chamados (52 Abertos + 25 Concluídos)` — atualização fidedigna do snapshot e alinhamento do chamado `HDPMSC-388` na Etapa 2 (Triagem N2).

## [0.4.0] — 2026-09-14 (PSEI-305)

### Added
- `feat(stepper): Esteira Canônica de 8 Etapas` — desacoplamento estrito e oficial da etapa `5. Testes de Qualidade (QA)` (homologação técnica e automações de testes do time de QA) da etapa `6. Validação Interna (Suporte N1)` (conferência do analista de sustentação e encerramento operacional).
- `feat(export): Exportação Multi-Formato (.MD, .XLSX, .CSV)` — componente dropdown corporativo de exportação (`btn-export`) com download direto das tabelas e métricas consolidadas em Markdown, Excel nativo (`xlsx`) e CSV padronizado.
- `feat(links): Navegação 1-Click Direta ao Jira Cloud` — links de acesso direto com a URL oficial (`https://egsys.atlassian.net/browse/{chave}`) nos badges de chamados e derivações técnicas no modal e tabelas.
- `feat(traceability): Exibição Unificada de Derivações Técnicas (issuelinks)` — mapeamento dinâmico e renderização visual das tarefas vinculadas da engenharia de software tanto no painel estadual (`/painel_sc`) quanto na visão executiva de coordenação (`/coordenador`).
- `feat(filters): Filtro Temporal 60 Dias e Governança de Janela Irrestrita` — inclusão da opção `60d` (últimos 60 dias) e restrição estrita da opção `todos` (sem restrição de data) exclusivamente para os painéis de coordenação/administração, prevenindo degradação de performance nos painéis de clientes.
- `feat(auth): Sincronização e Auditoria de Usuários em Produção` — persistência e sincronização de 10 usuários ativos na base de produção (`auth.db`), incluindo perfis estaduais (SC, TO, AM, RO, PR, MT, GM) e coordenação geral.

### Changed
- `infra(traefik): Prioridade Soberana no Roteamento (priority: 1000)` — configuração explícita de prioridade na regra do Traefik (`/var/egsys-docker/container/traefik/dynamic/jiraview.yml`) para garantir que o router de produção do JiraView sobreponha containers legados no host (`egsys-noc-jira`).
- `infra(compose): Limpeza de Hostname Inexistente` — remoção da label de rota órfã `painel.egsys.siseg.tech` de `docker-compose.prod.yml`.

### Fixed
- `fix(stepper): Resolução Dinâmica de Estados e Projetos em /journey` — flexibilização do endpoint de radiografia de jornada para resolver o estado automaticamente a partir do código do projeto (ex.: `HDPMSC`), sigla de estado (`sc`) ou prefixo da chave, com acesso irrestrito aos 73 espaços do Jira para perfis de coordenação e administração.
- `fix(coordenador): Sincronização Reativa do Drawer e Tabela com Status ao Vivo` — atualização dinâmica do status, esteira de 8 etapas, posse da bola, tempos e linha da tabela no painel do coordenador (`coordenador.html`) assim que os dados do Jira Cloud são recebidos, eliminando discrepâncias com snapshots estáticos.
- `fix(stepper): Mapeamento Canônico de Status N2 para Etapa 2 (Triagem N2)` — cobertura exaustiva de variações de N2 (`Triagem (N2)`, `Triagem N2`, `Validação N2`, `Suporte N2`, `N2`) direcionando com precisão para a Etapa 2.
- `fix(cache): Atualização do Chamado HDPMSC-388 para Triagem (N2)` — correção no snapshot local `jira_real_cache.json` e servidor de desenvolvimento refletindo a transição de validação para a Etapa 2.
- `fix(traefik): Resolução de 'Cannot GET /coordenador'` — eliminação definitiva do conflito de hostname entre Node-RED e JiraView no Traefik do host de monitoramento.
- `fix(stepper): Mapeamento de Status JSM para Fase 6 de Validação N1` — inclusão cirúrgica de status como `Validação N1`, `Desenvolvimento Concluído` e `Resolução Suporte` na etapa de validação interna.

## [0.3.0] — 2026-09-10

### Added
- `feat(auth): Tela de Login Unitária (/login)` — interface unificada e responsiva com direcionamento dinâmico de gestores por estado (`/painel_sc`, `/painel_to`, etc.) e coordenação (`/coordenador`), script anti-FOUC e tema Dark/Light persistente.
- `feat(auth): Banco de Dados Ultraleve SQLite Nativo (auth.db)` — persistência leve e independente sem dependências externas pesadas (`backend/app/core/db.py`), com hashing NIST PBKDF2-HMAC-SHA256 (100.000 iterações com salt seguro), migração automática de schema e persistência garantida no volume `/app/data/auth.db` mapeado em `./data/auth.db`.
- `feat(auth): Gestão de Usuários no Painel da Coordenação` — aba administrativa dedicada em `/coordenador` com listagem em tempo real, formulário de cadastro com auto-preenchimento de rotas estaduais, badges visuais de perfil e status, ativação/desativação imediata e redefinição administrativa de senhas.
- `feat(auth): Troca Obrigatória de Senha no 1º Acesso (Padrão egSYS Orion / SOC 2)` — validação de primeiro acesso via flag `must_change_password`, modal bloqueante central com `backdrop-filter: blur(6px)`, validação em tempo real de tamanho mínimo (>= 6 caracteres) e coincidência, e endpoint seguro `POST /api/v1/auth/change-password` que renova o JWT sem pendência.
- `feat(coordenador): Painel com 73 Espaços do Jira (PSEI-280)` — seletor global para coordenação de suporte com capacidade de navegar por todos os espaços do Jira vinculados à conta da coordenação, visão consolidada e cache local de alta performance (`todos_projetos_jira.json` e `jira_real_cache.json`).
- `feat(traefik): Compatibilidade Universal de Rotas` — inclusão de routers FastAPI com e sem prefixo `/painel_sc` (`backend/app/main.py`), viabilizando tráfego unificado com ou sem middleware `stripPrefix` do Traefik.

### Changed
- `ui(sc): Filtros de Tempo Restritos a 4 Opções Executivas` — no painel de Santa Catarina (`frontend/index.html`), manutenção estrita dos filtros de tempo: `90 dias` (padrão), `6 meses`, `12 meses` e `Ano atual` (calculado dinamicamente no backend via ano corrente), removendo a opção ilimitada 'Tudo'.
- `infra(traefik): Roteamento Global com Hardening` — consolidação da regra de roteamento no Traefik para o host completo `suporte-monitor.egsys.siseg.tech` com middleware de Rate Limiting (100 req/s, burst 50) e Security Headers defensivos (`Server: egSYS-Shield`, HSTS 1 ano, no-sniff, frameDeny).

## [0.2.0] — 2026-09-10

### Added
- `feat: Modo Escuro Full-Window (padrão Orion)` — suporte a tema escuro/claro em 100% da viewport (`color-scheme: dark !important`, script anti-FOUC no `<head>`, variáveis de tema aplicadas em todos os elementos estruturais e formulários, persistência em `localStorage`).
- `feat: Calibração de contraste no Chart.js` — suporte a paleta dinâmica com fundo transparente (`ticks.backdropColor: "transparent"`) no gráfico polar de solicitantes, ticks contrastantes (`#f0f6fc`), grids e angleLines (`#30363d`), tooltips dark e legendas claras para legibilidade absoluta em modo escuro.
- `feat: Tríade de Skills Corporativas egSYS Jiraview` — automações propagadas para todas as CLIs (`~/.agents/skills/`, `.agent/skills/`, OpenCode, Hermes, Kiro, Claude e Gemini):
  - `jiraview-commit`: commit autônomo, sanitização rigorosa e sincronização dual-path (`origin` empresa vs `privado`) com auditoria remota de branches.
  - `jiraview-docs-sync`: protocolo de governança Docs-as-Code em 3 camadas, histórico cumulativo (`history.md`), sessões e active learning.
  - `jiraview-jira-sync`: sincronização e mapeamento de tarefas no Jira corporativo sanitizado (sem dados de IA, senhas ou clientes).
- `feat: Configuração Git Dual-Path (padrão Orion)` — vinculação de remotes `origin` (empresa sanitizado: `git@github.com:egsys-dev/jiraview.git`) e `privado` (backup completo: `git@github.com:andreprado-egsys/jiraview.git`).
- `feat: criar app egSYS Painel do Cliente Jira` — FastAPI + SPA multi-estado (container único), RBAC JWT, serviço Jira read-only.
- `feat: endpoints de painel` — `/issues` (colunas Tipo/Origem/Referência/Resumo/Status/Solicitante/Prioridade/Atualização/Entrega), `/dashboard` (cards com particionamento por origem e categoria), `/charts` (agregados: status, prioridade, solicitante, série 15d), `/meta` (status+tipos), `/filtros` (CRUD JQL por gestor/estado).
- `feat: construtor visual de filtros` — campo/operador/valor + multiseleção → gera JQL (padrão Jira) + campo JQL livre.
- `feat: gráficos estilo Jira Dashboard` — barras por status, donut prioridade, polar por solicitante, linha de tempo.
- `feat: multi-estado por config` — `deploy/estados.yaml` (estado = bloco config; 1 único container).
- `feat: deploy prod` — Traefik path-prefix em `suporte-monitor.egsys.siseg.tech/painel_sc`, hardening 512m/1.0cpu/150pids, no-new-privileges.
- `feat: PSEI-277 correlato` — correção de 19+18 tickets divergentes (done sem resolução) via script idempotente + timer systemd; salvaguardas com snapshot/restore.
- `docs: arquitetura executiva de observabilidade` — formalização do padrão canônico de transparência, funil de atendimento em 4 estágios e gaveta lateral de jornada do ticket em `docs/RELATORIO_EXECUTIVO_OBSERVABILIDADE.md`.


### Changed
- `ui: simplificacao do dropdown de Origem` — remocao da opcao 'Interno' do filtro de origem, mantendo foco executivo no portal do cliente ('Todas' e 'Cliente (portal)').
- `refactor: limpeza de imports e escopo de overview` — remoção de imports duplicados em `backend/app/main.py` e busca dinâmica de projetos por estado no `/overview`.

### Security
- `security: headers defensivos` — HSTS (prod), X-Frame-Options DENY, nosniff, CSP, Referrer-Policy.
- `security: token backend-only` — credenciais Jira injetadas por env; nunca expostas ao client.
- `security: .env chmod 600 e gitignored`; persistência de filtros em `data/filtros.json` 0600.

### Fixed
- `feat/fix: régua canônica de 7 etapas no ciclo de vida` — consolidação da esteira operacional completa: `1. Triagem (N1)` ➔ `2. Triagem (N2)` ➔ `3. Análise de Desenvolvimento` ➔ `4. Em Desenvolvimento` ➔ `5. Validação Interna / QA` ➔ `6. Validação / Homologação Cliente` ➔ `7. Concluído`.
- `fix: carregamento offline/intranet de gráficos` — vendoring local de `vendor/chart.umd.min.js` (204KB) no frontend com fallback resiliente para CDN e retry assíncrono, garantindo renderização de todos os gráficos mesmo sob bloqueio de CDN, firewalls ou proxies restritos.
- `fix: filtragem do funil de atendimento sem JQL bruta` — criação do parâmetro nativo `funil_stage` (`novas`, `em_atendimento`, `aguardando_validacao`, `concluidas`) no endpoint `/issues`, eliminando erros de sintaxe e aspas simples (`statusCategory = 'In Progress'`) no Jira Cloud.
- `fix: mapeamento e posse da bola no ciclo JSM` — inclusão de `Aguardando Informações` na Fase 6 (Ação do Cliente), `Validação N2` na Fase 2 (Triagem N2), `Análise de Desenvolvimento` na Fase 3, `Em Desenvolvimento` na Fase 4 e `Desenvolvimento concluído` / `Resolução Suporte` na Fase 7 (Concluído).
- `fix: contraste do gráfico polar no modo escuro` — remoção de caixas brancas nos ticks e restauração de rótulos visíveis.
- `fix: escopo de estilo modo escuro` — aplicação de classes e atributos no `<html>` e `<body>`, corrigindo fundo que permanecia claro.
- `fix: CORS multi-método` (GET/POST/DELETE/OPTIONS) e origem correta de produção.
- `fix: /meta sem consulta interna inválida` — dropdowns populados (14 status + 8 tipos).
- `fix: boot do frontend` — cards, gráficos e meta carregam todos (um `boot()`).
- `fix: UX de busca vazia` — mensagem explicativa quando JQL não retorna resultados.
