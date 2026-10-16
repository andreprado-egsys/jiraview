#!/usr/bin/env python3
"""
Servidor de desenvolvimento local ultraleve para teste dos painéis.
Roteia:
  - /coordenador -> frontend/coordenador.html
  - /painel_sc   -> frontend/index.html
  - /login       -> frontend/login.html
  - /assets/*    -> frontend/assets/*
  - /vendor/*    -> frontend/vendor/*
  - /api/v1/*    -> mock inteligente com suporte a login e navegação
"""
import http.server
import json
import os
import sys
import urllib.parse

PORT = 8090
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
CACHE_FILE = os.path.join(FRONTEND_DIR, "assets", "jira_real_cache.json")


class JiraViewDevHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=FRONTEND_DIR, **kwargs)

    def translate_path(self, path):
        clean = path.split("?")[0].rstrip("/")
        if clean in ("", "/login"):
            path = "/login.html"
        elif clean == "/coordenador":
            path = "/coordenador.html"
        elif clean == "/painel_sc":
            path = "/index.html"
        return super().translate_path(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if "/api/v1/" in path:
            subpath = path.split("/api/v1/")[-1]
            return self._handle_api_post(subpath)

        self.send_response(404)
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        # Mock API v1 para teste local dos painéis
        if "/api/v1/" in path:
            subpath = path.split("/api/v1/")[-1]
            return self._handle_api_get(subpath, urllib.parse.parse_qs(parsed.query))

        return super().do_GET()

    def _handle_api_post(self, subpath):
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        if subpath == "auth/login":
            username = str(body.get("username", "")).strip().lower()
            if not username:
                username = "coordenador"

            is_coord = any(k in username for k in ("coord", "admin", "publio"))
            dest_url = "/coordenador" if is_coord else "/painel_sc"
            role = "admin" if is_coord else "manager"
            nome = "Coordenação de Suporte egSYS" if is_coord else f"Gestão PMSC ({username})"
            estado = "todos" if is_coord else "sc"

            resp_data = {
                "token": f"dev-token-{username}-valid",
                "token_type": "bearer",
                "redirect_url": dest_url,
                "user": {
                    "username": username,
                    "nome": nome,
                    "role": role,
                    "estado": estado,
                    "painel_url": dest_url,
                    "must_change_password": False,
                }
            }
            self._send_json(resp_data, status=200)
            return

        if subpath == "auth/change-password":
            resp_data = {
                "status": "ok",
                "message": "Senha alterada com sucesso!",
                "token": "dev-token-renewed",
                "user": {
                    "username": "coordenador",
                    "nome": "Coordenação de Suporte egSYS",
                    "role": "admin",
                    "estado": "todos",
                    "painel_url": "/coordenador",
                    "must_change_password": False
                }
            }
            self._send_json(resp_data, status=200)
            return

        # Default POST handler
        self._send_json({"status": "ok"}, status=200)

    def _handle_api_get(self, subpath, query):
        if subpath == "auth/me":
            self._send_json({
                "username": "coordenador",
                "nome": "Coordenação de Suporte egSYS",
                "role": "admin",
                "estado": "todos",
                "painel_url": "/coordenador",
                "must_change_password": False
            })
            return

        if subpath == "auth/users":
            self._send_json({
                "users": [
                    {"id": 1, "username": "coordenador", "nome": "Coordenação de Suporte egSYS", "role": "admin", "estado": "todos", "painel_url": "/coordenador", "is_active": 1, "must_change_password": 0},
                    {"id": 2, "username": "gestor.sc", "nome": "Gestão PMSC (Santa Catarina)", "role": "manager", "estado": "sc", "painel_url": "/painel_sc", "is_active": 1, "must_change_password": 0}
                ]
            })
            return

        if not os.path.exists(CACHE_FILE):
            self._send_json({"error": "Cache nao encontrado"}, status=500)
            return

        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            cache = json.load(f)

        tickets = cache.get("HDPMSC", {}).get("tickets", [])

        if subpath == "issues":
            solic_query = query.get("solicitante", [""])[0].lower() if isinstance(query, dict) and "solicitante" in query else ""
            abertas_param = query.get("abertas", ["true"])[0] == "true" if isinstance(query, dict) and "abertas" in query else True
            funil_stage = query.get("funil_stage", [""])[0] if isinstance(query, dict) and "funil_stage" in query else ""
            st_filter = query.get("status_filter", [""])[0] if isinstance(query, dict) and "status_filter" in query else ""
            tipo_filter = query.get("tipo", [""])[0] if isinstance(query, dict) and "tipo" in query else ""
            posse_filter = query.get("posse_filter", [""])[0] if isinstance(query, dict) and "posse_filter" in query else ""
            p = query.get("periodo", ["90d"])[0] if isinstance(query, dict) and "periodo" in query else "90d"
            from datetime import datetime, timedelta
            hoje = datetime.now().date()
            if p == "30d":
                limite_p_str = (hoje - timedelta(days=30)).isoformat()
            elif p == "60d":
                limite_p_str = (hoje - timedelta(days=60)).isoformat()
            elif p == "90d":
                limite_p_str = (hoje - timedelta(days=90)).isoformat()
            elif p == "6m":
                limite_p_str = (hoje - timedelta(days=180)).isoformat()
            elif p == "12m":
                limite_p_str = (hoje - timedelta(days=365)).isoformat()
            elif p == "ano":
                limite_p_str = f"{hoje.year}-01-01"
            else:
                limite_p_str = "2000-01-01"

            limite_7d_dt = (hoje - timedelta(days=7)).isoformat()
            chaves_abertas_semana = {
                t.get("chave") for t in tickets
                if (t.get("criacao") or "")[:10] >= limite_7d_dt
            }

            out = []
            for t in tickets:
                solic_nome = t.get("solicitante") or t.get("reporter") or "Cliente PMSC"
                if solic_query and solic_query not in solic_nome.lower():
                    continue
                is_done = t.get("statusCategoria") == "done" or bool(t.get("resolucao"))

                if funil_stage in ("concluidas", "fechadas_7d", "abertas_7d"):
                    pass
                elif abertas_param and is_done:
                    continue

                if st_filter and t.get("status") != st_filter:
                    continue

                if tipo_filter and t.get("tipo") != tipo_filter:
                    continue

                if posse_filter and t.get("posse") != posse_filter:
                    continue

                # Janela de período (quando não filtrado por cards específicos de 7 dias)
                if funil_stage not in ("abertas_7d", "fechadas_7d"):
                    cr_str = (t.get("criacao") or "")[:10]
                    if p not in ("todos", "all") and cr_str and cr_str < limite_p_str:
                        continue

                etapa_num = t.get("etapaNum", 1)
                if funil_stage == "novas":
                    if is_done or etapa_num not in (1, 2):
                        continue
                elif funil_stage == "em_atendimento":
                    if is_done or etapa_num not in (3, 4, 5, 6):
                        continue
                elif funil_stage == "aguardando_validacao":
                    if is_done or (etapa_num != 7 and t.get("posse") != "cliente"):
                        continue
                elif funil_stage == "concluidas":
                    if not is_done:
                        continue
                elif funil_stage == "abertas_7d":
                    if t.get("chave") not in chaves_abertas_semana:
                        continue
                elif funil_stage == "fechadas_7d":
                    dt = (t.get("dataResolucao") or t.get("atualizacao") or t.get("criacao") or "")[:10]
                    if not is_done or dt < limite_7d_dt:
                        continue

                out.append({
                    "tipo": t.get("tipo", "Demanda"),
                    "origem": "cliente",
                    "referencia": t.get("chave"),
                    "resumo": t.get("resumo"),
                    "status": t.get("status"),
                    "statusCategoria": "done" if is_done else "indeterminate",
                    "area": t.get("area", "Operações"),
                    "faseNum": etapa_num,
                    "faseNome": t.get("etapaNome", "Triagem"),
                    "posse": t.get("posse", "egsys"),
                    "posseLabel": t.get("posseLabel", "🔵 Ação com egSYS"),
                    "solicitante": solic_nome,
                    "responsavel": t.get("responsavel") or "Engenharia egSYS",
                    "prioridade": t.get("prioridade") or "Normal",
                    "atualizacao": t.get("atualizacao") or t.get("criacao", "2026-10-01"),
                    "criacao": t.get("criacao", "2026-09-01"),
                    "entrega": None,
                    "resolucao": t.get("resolucao")
                })
            self._send_json({"issues": out, "total": len(out)})
            return

        if subpath == "dashboard":
            p = query.get("periodo", ["90d"])[0] if isinstance(query, dict) and "periodo" in query else "90d"
            from datetime import datetime, timedelta
            hoje = datetime.now().date()
            limite_7d_dt = (hoje - timedelta(days=7)).isoformat()

            # Chamados abertos/criados nos últimos 7 dias corridos (conforme solicitação do Coordenador André)
            abertas_semana_tickets = [
                t for t in tickets
                if (t.get("criacao") or "")[:10] >= limite_7d_dt
            ]
            abertas_7d = len(abertas_semana_tickets)

            fechadas_7d = 0
            for t in tickets:
                if t.get("statusCategoria") == "done" or t.get("resolucao"):
                    dt = (t.get("dataResolucao") or t.get("atualizacao") or t.get("criacao") or "")[:10]
                    if dt >= limite_7d_dt:
                        fechadas_7d += 1

            # Janela de data para o período selecionado
            if p == "30d":
                limite_p = hoje - timedelta(days=30)
            elif p == "60d":
                limite_p = hoje - timedelta(days=60)
            elif p == "90d":
                limite_p = hoje - timedelta(days=90)
            elif p == "6m":
                limite_p = hoje - timedelta(days=180)
            elif p == "12m":
                limite_p = hoje - timedelta(days=365)
            elif p == "ano":
                limite_p = datetime(hoje.year, 1, 1).date()
            else: # "todos"
                limite_p = datetime(2000, 1, 1).date()

            funil = {"novas": 0, "em_atendimento": 0, "aguardando_validacao": 0, "concluidas": 0}
            por_status = {}
            por_origem = {"cliente_new": 0, "cliente_ind": 0, "cliente_done": 0, "interno_new": 0, "interno_ind": 0, "interno_done": 0}
            por_tipo = {}

            tickets_periodo = []
            for t in tickets:
                cr_str = (t.get("criacao") or "")[:10]
                try:
                    if datetime.fromisoformat(cr_str).date() >= limite_p:
                        tickets_periodo.append(t)
                except Exception:
                    if p in ("todos", "all"):
                        tickets_periodo.append(t)

            for t in tickets_periodo:
                st = t.get("status") or "Novo"
                cat = t.get("statusCategoria") or "new"
                resolvido = cat == "done" or bool(t.get("resolucao"))
                etapa_num = t.get("etapaNum", 1)

                por_status[st] = por_status.get(st, 0) + 1
                tp = t.get("tipo", "Demanda")
                por_tipo[tp] = por_tipo.get(tp, 0) + 1

                if resolvido or etapa_num == 8:
                    funil["concluidas"] += 1
                elif etapa_num == 7 or t.get("posse") == "cliente":
                    funil["aguardando_validacao"] += 1
                elif etapa_num in (3, 4, 5, 6):
                    funil["em_atendimento"] += 1
                else:
                    funil["novas"] += 1

            self._send_json({
                "estado": "Santa Catarina — PMSC",
                "projetos": ["HDPMSC"],
                "funil": funil,
                "abertas": funil["novas"],
                "em_andamento": funil["em_atendimento"],
                "aguardando_validacao": funil["aguardando_validacao"],
                "concluidas": funil["concluidas"],
                "abertas_7d": abertas_7d,
                "fechadas_7d": fechadas_7d,
                "por_status": por_status,
                "por_origem": por_origem,
                "por_tipo": por_tipo,
                "total_geral": len(tickets_periodo),
                "total_com_resolucao": funil["concluidas"],
                "periodo": p
            })
            return

        if subpath == "meta":
            self._send_json({
                "statuses": [
                    {"name": "Análise de Desenvolvimento", "tickets": 22},
                    {"name": "Concluído", "tickets": 10},
                    {"name": "Desenvolvimento concluído", "tickets": 6},
                    {"name": "Resolução Suporte", "tickets": 6},
                    {"name": "Cancelada", "tickets": 3},
                    {"name": "Aguardando Informações", "tickets": 1},
                    {"name": "Validação N1", "tickets": 1},
                    {"name": "Executando", "tickets": 1}
                ],
                "tipos": ["Bug Suporte", "Melhoria", "Incidente"],
                "solicitantes": [
                    "João Mário Mazzola",
                    "Murilo Ramos Brenner",
                    "Ilclemar Vieira",
                    "Alex sandro de oliveira",
                    "João Vitor Sopran",
                    "André Antônio Prado da Silva",
                    "Erick Vinicius Ferreira da Silva",
                    "Cássia Letícia Da Luz Domingos"
                ]
            })
            return

        if subpath.startswith("issues/") and "journey" in subpath:
            parts = subpath.split("/")
            issue_key = parts[1] if len(parts) > 1 else "HDPMSC-388"
            
            t_match = next((t for t in tickets if t.get("chave") == issue_key), None)
            resumo = t_match.get("resumo") if t_match else f"Demanda {issue_key}"
            status = t_match.get("status") if t_match else "Em Análise"
            area = t_match.get("area") if t_match else "SADE"
            etapa_num = t_match.get("etapaNum", 3) if t_match else 3
            tempo_fase = t_match.get("tempoFase", "4h 20m") if t_match else "4h 20m"
            tempo_total = t_match.get("tempoTotal", "1d 18h") if t_match else "1d 18h"
            posse = t_match.get("posse", "egsys") if t_match else "egsys"

            derivacoes = []
            if "388" in issue_key:
                etapa_num = 2
                status = "Triagem (N2)"
                derivacoes.append({
                    "chave": "PSC-3742",
                    "resumo": "Correção de concorrência e sobreposição de protocolos no SADE PMSC",
                    "tipo": "Bug de Engenharia",
                    "status_raw": "Validação QA",
                    "status_executivo": "Validação QA (Testes de Qualidade)",
                    "status_cor": "var(--yellow, #d29922)",
                    "responsavel": "Equipe de Engenharia egSYS",
                    "prioridade": "Alta",
                    "relacao": "bloqueia / is blocked by",
                    "tipo_link": "Bloqueador",
                    "total_subtasks": 3,
                    "subtasks_concluidas": 2
                })
            elif "387" in issue_key or "389" in issue_key or "399" in issue_key:
                derivacoes.append({
                    "chave": f"PSC-{int(issue_key.split('-')[-1]) + 3350}",
                    "resumo": f"Refatoração de serviço de mensageria e geocodificação vinculado a {issue_key}",
                    "tipo": "Tarefa de Desenvolvimento",
                    "status_raw": "Em Desenvolvimento",
                    "status_executivo": "Em Desenvolvimento",
                    "status_cor": "var(--blue, #58a6ff)",
                    "responsavel": "Engenharia de Backend egSYS",
                    "prioridade": "Normal",
                    "relacao": "derivado de / relates to",
                    "tipo_link": "Relação Técnica",
                    "total_subtasks": 2,
                    "subtasks_concluidas": 1
                })
            elif etapa_num in (3, 4, 5, 6):
                derivacoes.append({
                    "chave": f"PSC-38{issue_key.split('-')[-1][-2:]}",
                    "resumo": f"Demanda de engenharia vinculada ao chamado {issue_key}",
                    "tipo": "Demanda Dev",
                    "status_raw": status,
                    "status_executivo": "Em Andamento",
                    "status_cor": "var(--blue, #58a6ff)",
                    "responsavel": "Equipe de Desenvolvimento egSYS",
                    "prioridade": "Normal",
                    "relacao": "vinculada a",
                    "tipo_link": "Derivação",
                    "total_subtasks": 1,
                    "subtasks_concluidas": 0
                })

            etapas_nomes = [
                (1, "Triagem (N1)"),
                (2, "Triagem (N2)"),
                (3, "Análise de Desenvolvimento"),
                (4, "Em Desenvolvimento"),
                (5, "Testes de Qualidade (QA)"),
                (6, "Validação Interna (Suporte N1)"),
                (7, "Validação / Homologação Cliente"),
                (8, "Concluído"),
            ]
            etapas = []
            for num, nome_etapa in etapas_nomes:
                if num < etapa_num:
                    st_et = "concluido"
                elif num == etapa_num:
                    st_et = "ativo"
                else:
                    st_et = "pendente"
                etapas.append({"num": num, "nome": nome_etapa, "estado": st_et})

            self._send_json({
                "referencia": issue_key,
                "resumo": resumo,
                "status": status,
                "statusCategoria": "indeterminate" if etapa_num < 8 else "done",
                "area": area,
                "tipo": t_match.get("tipo", "Bug Suporte") if t_match else "Bug Suporte",
                "origem": "cliente",
                "solicitante": "João Mário Mazzola",
                "responsavel": "Engenharia egSYS",
                "prioridade": "Normal",
                "criacao": "2026-09-01",
                "atualizacao": "2026-09-12",
                "entrega": None,
                "resolucao": "Concluído" if etapa_num == 8 else None,
                "etapa_atual": etapa_num,
                "etapas": etapas,
                "derivacoes_engenharia": derivacoes,
                "posse": {
                    "tipo": posse,
                    "label": "🔵 Ação com egSYS" if posse == "egsys" else "🟡 Ação com Cliente",
                    "responsavel": "Engenharia egSYS" if posse == "egsys" else "João Mário Mazzola",
                    "tempo_etapa": tempo_fase,
                    "tempo_total": tempo_total,
                },
                "transicoes": [
                    {"de": "Em Atendimento", "para": status, "quando": "2026-09-12 10:30:00", "autor": "Engenharia egSYS"},
                    {"de": "Triagem N1", "para": "Em Atendimento", "quando": "2026-09-11 14:15:00", "autor": "Suporte egSYS"}
                ]
            })
            return

        if subpath == "charts":
            from collections import Counter, defaultdict
            from datetime import datetime, timedelta
            por_status = Counter()
            por_prioridade = Counter()
            por_solicitante = Counter()
            por_tipo = Counter()
            por_dia = defaultdict(int)
            hoje = datetime.now()
            for t in tickets:
                st = t.get("status") or "Novo"
                por_status[st] += 1
                por_tipo[t.get("tipo", "Demanda")] += 1
                por_prioridade[t.get("prioridade", "Normal")] += 1
                sol = t.get("solicitante") or t.get("reporter") or "Cliente PMSC"
                por_solicitante[sol] += 1
                cr = t.get("criacao") or "2026-09-01"
                try:
                    dia = datetime.fromisoformat(cr[:10]).date()
                    por_dia[dia] += 1
                except Exception:
                    pass
            serie = []
            for i in range(14, -1, -1):
                d = (hoje - timedelta(days=i)).date()
                serie.append({"dia": d.isoformat(), "count": por_dia[d]})
            self._send_json({
                "por_status": dict(por_status.most_common(15)),
                "por_prioridade": dict(por_prioridade.most_common()),
                "por_solicitante": dict(por_solicitante.most_common(15)),
                "por_tipo": dict(por_tipo.most_common()),
                "por_dia": serie,
                "total": len(tickets),
            })
            return

        if subpath == "filtros":
            self._send_json({"filtros": []})
            return

        self._send_json({"status": "ok"})

    def _send_json(self, data, status=200):
        resp = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(resp)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(resp)


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), JiraViewDevHandler)
    print(f"JiraView Dev Server ativo em http://localhost:{PORT}")
    print(f" -> http://localhost:{PORT}/login")
    print(f" -> http://localhost:{PORT}/coordenador")
    print(f" -> http://localhost:{PORT}/painel_sc")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor finalizado.")
        server.server_close()
