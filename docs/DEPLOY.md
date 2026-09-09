# Deploy — egSYS JiraView

## Topologia
- **Host:** `monitoramento-egsys` (45.7.171.41) — `/var/egsys-docker/container/jiraview/`
- **Produto único:** 1 container (`egsys-jiraview`), multi-estado via `deploy/estados.yaml`.
- **Rota pública:** `https://suporte-monitor.egsys.siseg.tech/painel_sc`
  (Traefik `dynamic/jiraview.yml` — PathPrefix+stripPrefix; cert existente do domínio).

## Arquivos
- `docker-compose.prod.yml` — build local, rede `webproxy`, hardening, sem labels Traefik (router via dynamic).
- `traefik/dynamic/jiraview.yml` — router/middleware/service (backup do padrão `noc.yml`).

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

## Backup/restauração de divergências (PSEI-277)
- `scripts/portal-jsm/corrige_divergentes.py --dry-run|--apply|--audit`
- `scripts/portal-jsm/restore_divergentes.py --list|--dry-run|--apply`
- Snapshots: `scripts/portal-jsm/snapshots/` (datados, não versionados).

## Extensão multi-estado
Novo estado = bloco em `deploy/estados.yaml` (`projects`, `clientes`, `áreas`)
+ usuários/papéis. Sem container novo.
