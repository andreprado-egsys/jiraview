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
