# Deploy — egSYS JiraView

## Topologia
- **Host:** `monitoramento-egsys` (45.7.171.41) — `/var/egsys-docker/container/jiraview/`
- **Produto único:** 1 container (`egsys-jiraview`), multi-estado via `deploy/estados.yaml`.
- **Rotas públicas ativas:**
  - `https://suporte-monitor.egsys.siseg.tech/login` — Tela de login unitária e direcionamento por estado
  - `https://suporte-monitor.egsys.siseg.tech/coordenador` — Painel da coordenação (73 espaços Jira + Gestão de Usuários)
  - `https://suporte-monitor.egsys.siseg.tech/painel_sc` — Painel do cliente Santa Catarina (PMSC)
  - `https://suporte-monitor.egsys.siseg.tech/api/v1/health` — Endpoint público de healthcheck
- **Gateway Traefik:** `traefik/dynamic/jiraview.yml` gerenciando todo o host com rate-limit e security headers defensivos (`Server: egSYS-Shield`).

## Arquivos
- `docker-compose.prod.yml` — build local, rede `webproxy`, hardening (512m RAM, 1.0 CPU, 150 PIDs), volume `./data:/app/data`.
- `traefik/dynamic/jiraview.yml` — router/middleware/service dinâmico para SSL e roteamento de tráfego.

## Subir/atualizar
```bash
ssh monitoramento-egsys
cd /var/egsys-docker/container/jiraview
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml logs -f egsys-jiraview
```

## Variáveis de ambiente (`backend/.env`, 0600)
`APP_ENV/prod, APP_PORT 8090, SECRET_KEY, CORS_ORIGINS, JIRA_URL, JIRA_USER, JIRA_TOKEN, JIRA_PROJECTS, JIRAVIEW_DATA=/app/data`
(.env é gerado a partir de `.env.example` — nunca versionar).

## Rollback
```bash
docker compose -f docker-compose.prod.yml down
# rebuild da imagem anterior (tag) ou restore do checkout git anterior
```
Os dados persistentes (filtros) estão em `./data` (volume).

### Rollback — Tema slate v0.5.17 (coordenador.html + index.html)
Escopo da mudança: somente tokens CSS e cores hardcoded migradas para tokens — zero lógica, zero API, zero schema. Reverter é trocar 2 arquivos de frontend.

**Gatilhos para acionar o rollback (avaliar em até 24h após publicar):**
- Reclamação do NOC/sala de monitoramento de ilegibilidade ou reflexo na TV real;
- Quebra visual em aba não testada (Relatórios, Usuários, Mail, Observabilidade) ou no Painel do Cliente (`/painel_sc`);
- Qualquer regressão funcional (o tema não toca JS de dados, mas a regra `btn-action` escopada pode herdar estilo em contexto não previsto).

**Passo a passo (produção, ~3 min):**
```bash
# 1. Backup pré-deploy é criado ANTES de publicar (obrigatório):
ssh monitoramento-egsys 'cd /var/egsys-docker/container/jiraview && mkdir -p /tmp/jiraview_bkp_tema_$(date +%Y%m%d_%H%M) && cp frontend/coordenador.html frontend/index.html /tmp/jiraview_bkp_tema_$(date +%Y%m%d_%H%M)/'

# 2. Restaurar os 2 arquivos do backup mais recente e rebuildar:
ssh monitoramento-egsys 'cd /var/egsys-docker/container/jiraview && BKP=$(ls -dt /tmp/jiraview_bkp_tema_* | head -1) && cp $BKP/coordenador.html $BKP/index.html frontend/ && docker compose -f docker-compose.prod.yml up -d --build'

# 3. Verificar:
curl -s https://suporte-monitor.egsys.siseg.tech/coordenador | grep -c "0f172a"   # deve ser 0 apos rollback
curl -s https://suporte-monitor.egsys.siseg.tech/api/v1/health                     # {"status":"ok","jira":true}
```

**Caminho git (alternativa canônica):** o tema vive em commit próprio e isolado após `401265b`; rollback = `git revert <sha-tema>` no repo local, push dual-path e re-sync via `git archive` no host (mesmo fluxo do deploy). Rollback parcial (só dark OU só light) é possível editando apenas o bloco `[data-theme="dark"]` ou `:root` correspondente.

**Local (antes de publicar):** `git checkout -- frontend/coordenador.html frontend/index.html` devolve ao estado `401265b`; a versão com tema fica preservada em `/tmp/tema_depois_20261029/`.

## Pareamento e Sincronização de Banco (SQLite)
- `python3 scripts/sync_db.py --status` — Audita paridade e lista usuários entre local e prod
- `python3 scripts/sync_db.py --pull` — Baixa banco de produção com backup local prévio
- `python3 scripts/sync_db.py --push` — Envia banco local para produção com backup remoto prévio

## Backup/restauração de divergências (PSEI-277)
- `scripts/portal-jsm/corrige_divergentes.py --dry-run|--apply|--audit`
- `scripts/portal-jsm/restore_divergentes.py --list|--dry-run|--apply`
- Snapshots: `scripts/portal-jsm/snapshots/` (datados, não versionados).

## Extensão multi-estado
Novo estado = bloco em `deploy/estados.yaml` (`projects`, `clientes`, `áreas`)
+ usuários/papéis. Sem container novo.
