# Segurança — egSYS JiraView

## Princípios (espelho egSYS Orion — pentest ACH-001..011)
1. **Zero credencial em código/repo**: `.gitignore` bloqueia `.env*`, `*.bak*`, `*.db`, `deploy/env|ssh|resources`; token Jira somente por variável de ambiente (`JIRA_TOKEN`), `chmod 600`.
2. **Backend-only**: cliente jamais vê credencial; API Jira acessada só no servidor.
3. **RBAC mínimo privilégio**: `viewer` consulta estado; `manager` salva filtros; `admin` total. Escopo por estado (`state` no JWT).
4. **Headers defensivos**: HSTS (prod), X-Frame-Options DENY, X-Content-Type-Options nosniff, Referrer-Policy no-referrer, CSP frame-ancestors none.
5. **Somente-leitura do Jira na API**: `GET` apenas; escrita só via script `--apply` com `--dry-run` + snapshot (rollback) e autorização explícita.
6. **Contenção de recursos (container)**: `mem_limit 512m`, `mem_reservation 128m`, `cpus 1.0`, `cpu_shares 512`, `pids_limit 150`, `no-new-privileges`, logs rotativos 10m×3.
7. **Rede**: container na rede `webproxy` (Traefik); `expose` interno, sem porta pública; TLS via Let's Encrypt (cert já existente do domínio).
8. **Persistência**: filtros em `data/filtros.json` (0600), fora do repo; snapshots de correção localizados em `scripts/portal-jsm/snapshots/` (não versionados).

## Rotas sensíveis / mudanças de estado
- **Sem DML na API**: o painel não altera issues. As correções de tickets
  divergentes são feitas por `scripts/portal-jsm/corrige_divergentes.py`
  (dry-run → snapshot → apply autorizado) e `restore_divergentes.py` (rollback).

## Auditoria (fluxo de commit)
- Varredura de segredos no diff (`password=|senha=|secret|bearer`).
- Pós-push: auditoria nas branches do GitHub empresarial (`git ls-tree | grep`) contra pattern de proibidos.
