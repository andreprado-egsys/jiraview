#!/usr/bin/env python3
"""
Gera os arquivos de auditoria em .md, .xlsx e .csv para as tarefas de Santa Catarina (PMSC / HDPMSC)
"""
import io
import json
import os
import zipfile

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, "frontend", "assets", "jira_real_cache.json")
DOCS_DIR = os.path.join(BASE_DIR, "docs")

with open(CACHE_FILE, "r", encoding="utf-8") as f:
    db = json.load(f)

tks = db.get("HDPMSC", {}).get("tickets", [])

headers = [
    "Chave", "Tipo", "Área", "Macro-Fase", "Status Jira",
    "Posse da Bola", "Estágio Funil", "SLA", "Tempo na Fase",
    "Tempo Total", "Resumo", "Classificação 37 vs 34"
]

rows = []
for t in tks:
    st = t.get("status", "")
    if st in ["Concluído", "Cancelada"]:
        grupo = "13 Concluídas/Canceladas no Jira"
    else:
        grupo = "37 Demandas Sem Resolução (Backlog Operacional)"

    res = (t.get("resumo") or "").replace('"', '""')
    fase_str = f"Etapa {t.get('etapaNum', '')}/8 ({t.get('etapaNome', '')})"
    sla_str = "Em dia" if t.get("sla") == "ok" else "Atenção SLA"

    rows.append([
        t.get("chave", ""),
        t.get("tipo", ""),
        t.get("area", ""),
        fase_str,
        st,
        t.get("posseLabel", ""),
        t.get("estagio", ""),
        sla_str,
        t.get("tempoFase", ""),
        t.get("tempoTotal", ""),
        res,
        grupo
    ])

# 1. Gerar CSV
csv_lines = [";".join(f'"{h}"' for h in headers)]
for r in rows:
    csv_lines.append(";".join(f'"{c}"' for c in r))

csv_path = os.path.join(DOCS_DIR, "auditoria_sc_pmsc_tasks.csv")
with open(csv_path, "w", encoding="utf-8-sig") as f:
    f.write("\r\n".join(csv_lines) + "\r\n")
print(f"Salvo: {csv_path}")

# 2. Gerar Markdown
md_lines = [
    "# 📊 Relatório de Auditoria e Comparativo de Tarefas — SC (PMSC)",
    "",
    "**Data da Extração**: 14/09/2026  ",
    "**Espaço Jira**: `HDPMSC` (Helpdesk PMSC)  ",
    "**Total Mapeado**: 50 Tarefas  ",
    "**Total Sem Resolução Formal (`resolution is EMPTY`)**: 37 Tarefas  ",
    "**Total Concluídas/Canceladas**: 13 Tarefas  ",
    "",
    "---",
    "",
    "## 🔍 Diagnóstico Executivo: Divergência 37 vs 34 Tarefas",
    "",
    "### 1. Decomposição das 37 Tarefas em Aberto",
    "* **22 em Análise de Desenvolvimento** (egSYS)",
    "* **6 em Desenvolvimento concluído** (concluídas tecnicamente, mas sem campo `resolution` no Jira Cloud)",
    "* **6 em Resolução Suporte** (resolvidas pelo suporte, mas sem campo `resolution` no Jira Cloud)",
    "* **1 em Executando** (egSYS)",
    "* **1 em Validação N1** (egSYS)",
    "* **1 em Aguardando Informações** (Ação com o Cliente / PMSC)",
    "",
    "$$\\text{Total Sem Resolução} = 22 + 6 + 6 + 1 + 1 + 1 = 37\\text{ tarefas}$$",
    "",
    "### 2. Por que o Mazzola informou em torno de 34 tarefas?",
    "1. **Filtro Individual vs Filtro de Organização (Causa Raiz Mais Provável)**:",
    "   * No Portal JSM, se o Mazzola estiver filtrando por *\"Criadas por mim\"*, ele visualiza apenas as solicitações abertas pelo seu próprio usuário (`qm:5ba24cb3...`).",
    "   * No nosso painel institucional (`deploy/estados.yaml`), o escopo de Santa Catarina abrange os 4 gestores cadastrados da PMSC:",
    "     * **João Mário Mazzola**",
    "     * **Ilclemar Vieira**",
    "     * **Alex Sandro de Oliveira**",
    "     * **Cap Thiesen**",
    "   * Quando outro militar ou o suporte abre chamados vinculados à PMSC (delta de 3 chamados), o Mazzola não os vê na aba individual.",
    "   * **Conclusão**: **O Mazzola está com um número menor que a realidade global do órgão.**",
    "",
    "2. **Tickets em Resolução Suporte / Desenvolvimento concluído**:",
    "   * Dependendo do mapeamento de transição do Customer Portal JSM, tickets em *Resolução Suporte* ou *Desenvolvimento concluído* podem ser movidos para a aba *\"Resolvidas/Fechadas\"* da visão do cliente, enquanto no backend Jira o motor de busca com `resolution is EMPTY` continua contabilizando-os.",
    "",
    "---",
    "",
    "## 📋 Tabela Completa dos 50 Chamados Mapeados",
    "",
    "| # | Chave | Tipo | Área | Macro-Fase | Status Jira | Posse | SLA | Resumo | Grupo |",
    "|:---:|:---:|:---:|:---:|---|---|:---:|:---:|---|---|"
]

for idx, r in enumerate(rows, 1):
    res_md = r[10].replace("|", "&#124;")
    md_lines.append(f"| {idx} | **{r[0]}** | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[7]} | {res_md} | {r[11]} |")

md_path = os.path.join(DOCS_DIR, "auditoria_sc_pmsc_tasks.md")
with open(md_path, "w", encoding="utf-8") as f:
    f.write("\n".join(md_lines) + "\n")
print(f"Salvo: {md_path}")

# 3. Gerar XLSX
def make_xlsx(filename, headers, rows):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>""")

        zf.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>""")

        zf.writestr("xl/_rels/workbook.xml.rels", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>""")

        zf.writestr("xl/workbook.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="HDPMSC_PMSC_Tarefas" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>""")

        zf.writestr("xl/styles.xml", """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="3">
    <font><name val="Segoe UI"/><sz val="10"/><color rgb="FF172B4D"/></font>
    <font><b/><color rgb="FFFFFFFF"/><name val="Segoe UI"/><sz val="10"/></font>
    <font><b/><name val="Segoe UI"/><sz val="10"/><color rgb="FF0052CC"/></font>
  </fonts>
  <fills count="4">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF0052CC"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF4F5F7"/></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/></border>
    <border>
      <left style="thin"><color rgb="FFDFE1E6"/></left>
      <right style="thin"><color rgb="FFDFE1E6"/></right>
      <top style="thin"><color rgb="FFDFE1E6"/></top>
      <bottom style="thin"><color rgb="FFDFE1E6"/></bottom>
    </border>
  </borders>
  <cellStyleXfs count="1">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="0"/>
  </cellStyleXfs>
  <cellXfs count="3">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
    <xf numFmtId="0" fontId="0" fillId="3" borderId="1" xfId="0" applyBorder="1" applyFill="1"/>
  </cellXfs>
</styleSheet>""")

        sheet_rows = []
        def esc_xml(val):
            return str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        def col_letter(c_idx):
            res = ""
            while c_idx >= 0:
                res = chr(c_idx % 26 + 65) + res
                c_idx = c_idx // 26 - 1
            return res

        # Header row
        h_cells = []
        for c_idx, h in enumerate(headers):
            ref = f"{col_letter(c_idx)}1"
            h_cells.append(f'<c r="{ref}" t="inlineStr" s="1"><is><t>{esc_xml(h)}</t></is></c>')
        sheet_rows.append('<row r="1">' + ''.join(h_cells) + '</row>')

        # Data rows
        for r_idx, row in enumerate(rows, 2):
            r_cells = []
            s_style = "2" if (r_idx % 2 == 0) else "0"
            for c_idx, val in enumerate(row):
                ref = f"{col_letter(c_idx)}{r_idx}"
                r_cells.append(f'<c r="{ref}" t="inlineStr" s="{s_style}"><is><t>{esc_xml(val)}</t></is></c>')
            sheet_rows.append(f'<row r="{r_idx}">' + ''.join(r_cells) + '</row>')

        sheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {''.join(sheet_rows)}
  </sheetData>
</worksheet>"""
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)

    with open(filename, "wb") as f:
        f.write(buffer.getvalue())
    print(f"Salvo: {filename} ({len(buffer.getvalue())} bytes)")

xlsx_path = os.path.join(DOCS_DIR, "auditoria_sc_pmsc_tasks.xlsx")
make_xlsx(xlsx_path, headers, rows)
print("Concluído!")
