# Segurança — egSYS JiraView

## Princípios (espelho egSYS Orion — pentest ACH-001..011)
1. **Zero credencial em código/repo**: `.gitignore` bloqueia `.env*`, `*.bak*`, `*.db`, `deploy/env|ssh|resources`; token Jira somente por variável de ambiente (`JIRA_TOKEN`), `chmod 600`.
2. **Backend-only**: cliente jamais vê credencial; API Jira acessada só no servidor.
3. **RBAC Mínimo Privilégio em 5 Níveis**:
   - `coordenador` (Nível 4): Acesso global irrestrito, relatórios executivos e administração plena de usuários.
   - `n2` (Nível 3): Acesso operacional e gestão delegada de usuários (`n1`, `monitor`, clientes). Bloqueio estrito de escalada de privilégios (proibido criar/alterar `coordenador` ou `n2`).
   - `n1` (Nível 2): Acesso restrito e fixo às telas operacionais do NOC (Certificados SSL, Triagem N1/N2 e Desenvolvimento).
   - `monitor` (Nível 1): Kiosk/Wallboard de telas públicas com as mesmas visualizações do N1, dotado de token de longa duração (365 dias) e isento de troca compulsória de senha (`must_change_password=0`).
   - `viewer` / `manager` (Nível 1): Escopo estritamente restrito ao respectivo estado (`state` no JWT, ex.: `/painel_sc`).
4. **Armazenamento de Senhas (Padrão NIST)**: banco SQLite ultraleve com hashing PBKDF2-HMAC-SHA256 (100.000 iterações com salt criptográfico de 16 bytes).
5. **Troca Obrigatória de Senha no 1º Acesso (SOC 2 / Padrão Orion)**: flag `must_change_password` embutida no payload JWT e na base de dados. Modal bloqueante impede navegação em qualquer painel até a definição de nova senha pessoal (mínimo 6 caracteres). Usuários de sistema/kiosk (`monitor`) são explicitamente isentados (`must_change_password=0`).
6. **Headers defensivos**: HSTS (prod), X-Frame-Options SAMEORIGIN, X-Content-Type-Options nosniff, Referrer-Policy no-referrer, CSP frame-ancestors 'self', Server egSYS-Shield, X-Robots-Tag noindex/nofollow.
7. **Rate Limiting & Anti-Brute Force**: proteção ativa no gateway Traefik (100 req/s com burst de 50) e isolamento de rotas sensíveis.
8. **Somente-leitura do Jira na API**: `GET` apenas; escrita só via script `--apply` com `--dry-run` + snapshot (rollback) e autorização explícita.
9. **Contenção de recursos (container)**: `mem_limit 512m`, `mem_reservation 128m`, `cpus 1.0`, `cpu_shares 512`, `pids_limit 150`, `no-new-privileges`, logs rotativos 10m×3.
10. **Rede**: container na rede `webproxy` (Traefik); `expose` interno, sem porta pública; TLS via Let's Encrypt (cert já existente do domínio).
11. **Persistência**: banco `auth.db` e layouts em volume montado `./data:/app/data` (0600), fora do repositório git.
12. **Resiliência do Auto-Refresh Contínuo**: o ciclo de polling a cada 45s respeita o estado do DOM (pausa se `#drawer.open` ou modal aberto) e trata silenciosamente falhas de rede transitórias sem ejetar o operador.

## Rotas sensíveis / mudanças de estado
- **Sem DML de tickets na API**: o painel não altera issues no Jira. As correções de tickets divergentes são feitas por `scripts/portal-jsm/corrige_divergentes.py` (dry-run → snapshot → apply autorizado) e `restore_divergentes.py` (rollback).
- **Gestão de Usuários Protegida com Anti-Escalação**: endpoints `/api/v1/auth/users*` protegidos por `require_user_manager` (`coordenador` e `n2`). Operadores N2 não podem criar, editar, resetar senha ou excluir contas de nível $\ge 3$ (`coordenador` ou `n2`), retornando **HTTP 403 Forbidden**. Auto-exclusão é terminantemente bloqueada para qualquer usuário.

## Auditoria (fluxo de commit)
- Varredura de segredos no diff (`password=|senha=|secret|bearer`).
- Pós-push: auditoria nas branches do GitHub empresarial (`git ls-tree | grep`) contra pattern de proibidos.
