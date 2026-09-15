# egSYS JiraView — Changelog

## [0.4.1] — 2026-09-15 (PSEI-309)

### Added
- `feat(dashboard): Banner Executivo de Síntese Matemática do Backlog` — incorporação de banner de síntese executiva no topo de todos os painéis (`coordenador.html` e `index.html`), evidenciando a decomposição matemática exata da carteira ativa do cliente: `2 Novas + 46 Em Atendimento + 4 Aguardando Validação = 52 Chamados em Aberto`, com isolamento explícito do histórico de 25 entregas finalizadas.
- `feat(dashboard): Card Total Backlog Ativo & Badges Semânticas do Funil` — card dedicado de fechamento da conta (`Total Backlog Ativo`) e inclusão de badges categorizando os componentes da esteira (`Componente 1/3, 2/3 e 3/3 do Backlog Ativo` vs `Histórico Fora do Backlog Aberto`).
- `feat(ui): Numeração Sequencial (#: 1 a N) em Todas as Listagens e Exportações` — coluna `#` numerada de 1 a N nas tabelas e integrada aos arquivos exportados (`Markdown`, `Excel` e `CSV`) em ambos os painéis.
- `feat(ops): Script Canônico de Pareamento e Sincronização de Banco (`scripts/sync_db.py`)` — ferramenta de automação com suporte a `--status`, `--pull` e `--push` para garantir paridade contínua e backups preventivos entre o banco SQLite local e a produção (`monitoramento-egsys`).

### Fixed
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
