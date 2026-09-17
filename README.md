# egSYS Painel do Cliente Jira (egsys-jiraview)

Painel operacional de solicitações JSM (Jira Service Management) da **egSYS** — produto único, **um só container**, que monta o ambiente de **todos os estados** (SC, AM, TO, RO, PR, GM...) a partir de configuração interna. O estado é um **escopo de dados**, nunca um serviço/infra separado.

- **1 container** (`egsys-jiraview`) serve todos os estados.
- **Estado = configuração** (`deploy/estados.yaml`): projetos Jira, clientes (RBAC), áreas de atendimento.
- **RBAC**: quem acessa o estado X só enxerga o estado X; o pano de fundo é o mesmo app.
- Hardening no padrão egSYS Orion (pentest black box + Cgroups + contenção de recursos).

**Primeiro estado configurado:** SC (PMSC) — clientes: João Mário Mazzola, Ilclemar Vieira, Alex Sandro de Oliveira, Cap Thiesen.

## Como funciona o multi-estado

```
egsys-jiraview (único container)
├── deploy/estados.yaml   ← CONFIG (todos os estados aqui)
│     sc:  projects=[HDPMSC, SCPMH], clientes=[4 gestores], áreas=[Cidadão, SADE, Integração, Operações]
│     to:  projects=[HDPMTO], ...        ← futuro, mesmo arquivo
├── backend (FastAPI)     ← RBAC + Jira read-only (um só processo)
└── frontend (SPA)        ← troca de "ambiente" no rodapé: estado do usuário
```

**Adicionar um novo estado** = acrescentar um bloco em `estados.yaml` (+ usuários). Sem novo Docker, sem novo servidor.

## Arquitetura

```
egsys-jiraview/
├── backend/            # FastAPI (padrão Orion)
│   └── app/
│       ├── api/        # /api/v1/...
│       ├── core/       # security (RBAC/JWT), config, estados loader
│       ├── models|schemas|scripts
├── frontend/           # SPA Vite/TS
├── deploy/estados.yaml # multi-estado (config, não infra)
├── scripts/portal-jsm/ # corretores idempotentes + snapshots (PSEI-277)
├── docs/
└── docker-compose.*.yml  # 1 serviço + rígida contenção (512m/1.0cpu/150pids)
```

## Decisões (PSEI-277)

- Produto central: **Painel do Cliente Jira** — estados são dados; cliente acessa pelo mesmo endereço e vê "seu ambiente" (RBAC + escopo do estado).
- RBAC: `viewer` / `manager` / `admin` por estado; gestores de SC enxergam os 4 ambientes (Cidadão, SADE, Integração, Operações) — sem segregar organizações JSM.
- Correções (transições/resolução): `--dry-run` → snapshot → `--apply` autorizado; timer systemd roda o mesmo script (escopo estrito do estado configurado).

## 📚 Documentação Técnica & Executiva (Docs-as-Code)

- **[Documento Executivo de Projeto](docs/DOCUMENTO_EXECUTIVO_PROJETO.md)**: Visão plena e ampla cobrindo Engenharia de Software, Observabilidade (3 Níveis e Síntese de Backlog), SRE (Cgroups e Traefik) e Gestão (RBAC, NIST e RACI).
- **[Apresentação Executiva CEO & Diretoria (Tríade PPTX + PDF + MD)](docs/egSYS-JiraView-CEO-Executivo.md)**: Deck executivo geral de 8 slides widescreen em padrão Dark Glass / Slate ([PPTX](docs/egSYS-JiraView-CEO-Executivo.pptx) / [PDF](docs/egSYS-JiraView-CEO-Executivo.pdf)).
- **[Apresentação Executiva Santa Catarina — PMSC (Tríade PPTX + PDF + MD)](docs/egSYS-JiraView-PMSC-Executivo.md)**: Deck executivo dedicado para a PMSC abordando as 4 áreas (Cidadão, SADE, Integração, Operações) e a decomposição exata das 52 tarefas ativas ([PPTX](docs/egSYS-JiraView-PMSC-Executivo.pptx) / [PDF](docs/egSYS-JiraView-PMSC-Executivo.pdf)).
- **[Relatório Executivo de Observabilidade](docs/RELATORIO_EXECUTIVO_OBSERVABILIDADE.md)**: Padrão canônico de transparência e esteira de atendimento.
- **[Manual de API](docs/API.md)**: Especificação formal dos endpoints REST e autenticação JWT.
- **[Segurança & Hardening](docs/SECURITY.md)**: Padrão egSYS Orion (ACH-011), headers defensivos e pentest black box.
- **[Histórico Cumulativo](docs/history.md)**: Registro auditável e cronológico de decisões técnicas e marcos de engenharia.

