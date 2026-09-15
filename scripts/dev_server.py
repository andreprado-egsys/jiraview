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
            out = []
            for t in tickets:
                out.append({
                    "tipo": t.get("tipo", "Demanda"),
                    "origem": "cliente",
                    "referencia": t.get("chave"),
                    "resumo": t.get("resumo"),
                    "status": t.get("status"),
                    "statusCategoria": "done" if t.get("estagio") == "concluidas" else "indeterminate",
                    "area": t.get("area", "Operações"),
                    "faseNum": t.get("etapaNum", 1),
                    "faseNome": t.get("etapaNome", "Triagem"),
                    "posse": t.get("posse", "egsys"),
                    "posseLabel": t.get("posseLabel", "🔵 Ação com egSYS"),
                    "solicitante": "João Mário Mazzola",
                    "responsavel": "Engenharia egSYS",
                    "prioridade": "Normal",
                    "atualizacao": "2026-09-10",
                    "criacao": "2026-09-01",
                    "entrega": None,
                    "resolucao": "Concluído" if t.get("estagio") == "concluidas" else None
                })
            self._send_json({"issues": out, "total": len(out)})
            return

        if subpath == "dashboard":
            p = query.get("periodo", ["90d"])[0] if isinstance(query, dict) and "periodo" in query else "90d"
            self._send_json({
                "estado": "Santa Catarina — PMSC",
                "projetos": ["HDPMSC"],
                "funil": {"novas": 0, "em_atendimento": 24, "aguardando_validacao": 1, "concluidas": 25},
                "abertas": 0,
                "em_andamento": 24,
                "aguardando_validacao": 1,
                "concluidas": 25,
                "fechadas_7d": 10,
                "por_status": {"Análise de Desenvolvimento": 22, "Concluído": 10, "Desenvolvimento concluído": 6, "Resolução Suporte": 6, "Cancelada": 3, "Aguardando Informações": 1, "Validação N1": 1, "Executando": 1},
                "por_origem": {"cliente_ind": 25, "cliente_done": 25},
                "por_tipo": {"Bug Suporte": 44, "Melhoria": 5, "Incidente": 1},
                "total_geral": 50,
                "total_com_resolucao": 13,
                "periodo": p
            })
            return

        if subpath == "meta":
            self._send_json({
                "status": [
                    {"name": "Análise de Desenvolvimento", "tickets": 22},
                    {"name": "Concluído", "tickets": 10},
                    {"name": "Desenvolvimento concluído", "tickets": 6},
                    {"name": "Resolução Suporte", "tickets": 6},
                    {"name": "Cancelada", "tickets": 3},
                    {"name": "Aguardando Informações", "tickets": 1},
                    {"name": "Validação N1", "tickets": 1},
                    {"name": "Executando", "tickets": 1}
                ],
                "tipos": ["Bug Suporte", "Melhoria", "Incidente"]
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
