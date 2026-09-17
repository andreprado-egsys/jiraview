#!/usr/bin/env python3
"""
egSYS JiraView — Gerador do Deck Executivo Exclusivo Santa Catarina (PMSC) — v0.4.1
Padrão Canônico de 8 Slides Widescreen (16:9) em Dark Glass / Modern Slate.
Focado na Gestão PMSC: João Mário Mazzola, Ilclemar Vieira, Alex Sandro de Oliveira e Cap Thiesen.
Destaque absoluto para as melhorias em relação ao painel legado do Jira:
- Trilha da jornada (esteira de ação de 8 etapas + tempo em cada fase + posse da bola)
- Dashboards e observabilidade visual (gráficos interativos + banner de síntese)
- Construtor de filtros e persistência de filtros salvos pelo gestor da PMSC
- Exportação corporativa (.xlsx, .md, .csv) com numeração # 1 a N
- Rastreabilidade com tarefas técnicas da engenharia de software (PSC)
"""

import os
import sys
import subprocess
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

# ==============================================================================
# 1. PALETA DE CORES CANÔNICA (Tema Dark Glass / Modern Slate)
# ==============================================================================
COLOR_BG = RGBColor(8, 17, 31)             # #08111F
COLOR_CARD_DARK = RGBColor(16, 32, 56)     # #102038
COLOR_CARD_BLUE = RGBColor(19, 38, 65)     # #132641
COLOR_BORDER = RGBColor(42, 62, 92)        # #2A3E5C
COLOR_BORDER_CYAN = RGBColor(53, 208, 255)
COLOR_BORDER_LIME = RGBColor(200, 255, 74)

COLOR_TEXT_LIGHT = RGBColor(245, 248, 252) # #F5F8FC
COLOR_TEXT_MUTED = RGBColor(157, 176, 199) # #9DB0C7
COLOR_CYAN = RGBColor(53, 208, 255)        # #35D0FF (Acentos Técnicos)
COLOR_LIME = RGBColor(200, 255, 74)        # #C8FF4A (Big Numbers / ROI)
COLOR_WARN = RGBColor(255, 184, 77)        # #FFB84D (Alerta)
COLOR_RED = RGBColor(255, 92, 92)          # #FF5C5C (Risco Crítico)

FONT_DISPLAY = "Aptos Display"
FONT_BODY = "Aptos"


class JiraViewPMSCDeckBuilder:
    def __init__(self, output_pptx="egSYS-JiraView-PMSC-Executivo.pptx"):
        self.output_pptx = output_pptx
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.50)
        self.blank_layout = self.prs.slide_layouts[6]

    def add_slide(self):
        slide = self.prs.slides.add_slide(self.blank_layout)
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.50))
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLOR_BG
        bg.line.fill.background()
        return slide

    def add_header(self, slide, tag_text, title_text, subtitle_text=None, slide_num_str=None, tag_color=COLOR_CYAN):
        # Tag Superior
        tx_tag = slide.shapes.add_textbox(Inches(0.75), Inches(0.35), Inches(8.5), Inches(0.28))
        tf_t = tx_tag.text_frame
        tf_t.word_wrap = True
        tf_t.margin_left = tf_t.margin_top = tf_t.margin_right = tf_t.margin_bottom = 0
        p_t = tf_t.paragraphs[0]
        r_t = p_t.add_run()
        r_t.text = tag_text.upper()
        r_t.font.name = FONT_BODY
        r_t.font.size = Pt(10.5)
        r_t.font.bold = True
        r_t.font.color.rgb = tag_color

        # Número do Slide
        if slide_num_str:
            tx_num = slide.shapes.add_textbox(Inches(11.8), Inches(0.35), Inches(0.78), Inches(0.28))
            tf_n = tx_num.text_frame
            tf_n.word_wrap = True
            tf_n.margin_left = tf_n.margin_top = tf_n.margin_right = tf_n.margin_bottom = 0
            p_n = tf_n.paragraphs[0]
            p_n.alignment = PP_ALIGN.RIGHT
            r_n = p_n.add_run()
            r_n.text = slide_num_str
            r_n.font.name = FONT_BODY
            r_n.font.size = Pt(11)
            r_n.font.bold = True
            r_n.font.color.rgb = COLOR_TEXT_MUTED

        # Título do Slide
        tx_title = slide.shapes.add_textbox(Inches(0.75), Inches(0.68), Inches(11.83), Inches(0.75))
        tf_title = tx_title.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        r_title = p_title.add_run()
        r_title.text = title_text
        r_title.font.name = FONT_DISPLAY
        r_title.font.size = Pt(25.0)
        r_title.font.bold = True
        r_title.font.color.rgb = COLOR_TEXT_LIGHT

        # Subtítulo do Slide
        if subtitle_text:
            tx_sub = slide.shapes.add_textbox(Inches(0.75), Inches(1.48), Inches(11.83), Inches(0.50))
            tf_sub = tx_sub.text_frame
            tf_sub.word_wrap = True
            tf_sub.margin_left = tf_sub.margin_top = tf_sub.margin_right = tf_sub.margin_bottom = 0
            p_sub = tf_sub.paragraphs[0]
            r_sub = p_sub.add_run()
            r_sub.text = subtitle_text
            r_sub.font.name = FONT_BODY
            r_sub.font.size = Pt(13.5)
            r_sub.font.color.rgb = COLOR_TEXT_LIGHT

    def add_footer(self, slide, left_text="egSYS JIRAVIEW — SANTA CATARINA", right_text="POLÍCIA MILITAR DE SANTA CATARINA (PMSC)"):
        rule = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.75), Inches(7.02), Inches(11.83), Inches(0.01))
        rule.fill.solid()
        rule.fill.fore_color.rgb = COLOR_BORDER
        rule.line.color.rgb = COLOR_BORDER

        tx_box = slide.shapes.add_textbox(Inches(0.75), Inches(7.10), Inches(4.5), Inches(0.3))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = left_text
        r.font.name = FONT_BODY
        r.font.size = Pt(8.5)
        r.font.bold = True
        r.font.color.rgb = COLOR_TEXT_MUTED

        tx_box_r = slide.shapes.add_textbox(Inches(7.5), Inches(7.10), Inches(5.08), Inches(0.3))
        tf_r = tx_box_r.text_frame
        tf_r.word_wrap = True
        tf_r.margin_left = tf_r.margin_top = tf_r.margin_right = tf_r.margin_bottom = 0
        p_r = tf_r.paragraphs[0]
        p_r.alignment = PP_ALIGN.RIGHT
        r_r = p_r.add_run()
        r_r.text = right_text
        r_r.font.name = FONT_BODY
        r_r.font.size = Pt(8.0)
        r_r.font.bold = True
        r_r.font.color.rgb = COLOR_TEXT_MUTED

    def add_card(self, slide, left, top, width, height, fill_color=COLOR_CARD_DARK, border_color=COLOR_BORDER):
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        card.fill.solid()
        card.fill.fore_color.rgb = fill_color
        card.line.color.rgb = border_color
        card.line.width = Pt(1)
        return card

    def add_callout(self, slide, left, top, width, height, text, accent_color=COLOR_WARN):
        card = self.add_card(slide, left, top, width, height, fill_color=COLOR_CARD_BLUE, border_color=COLOR_BORDER)
        tf = card.text_frame
        tf.word_wrap = True
        tf.margin_left = Inches(0.2)
        tf.margin_right = Inches(0.2)
        tf.margin_top = Inches(0.08)
        tf.margin_bottom = Inches(0.08)
        p = tf.paragraphs[0]
        r = p.add_run()
        r.text = text
        r.font.name = FONT_BODY
        r.font.size = Pt(10.5)
        r.font.bold = True
        r.font.color.rgb = accent_color
        return card

    # ==============================================================================
    # SLIDE 1: CAPA & EXECUTIVE BRIEF (SANTA CATARINA - PMSC)
    # ==============================================================================
    def build_slide_1(self):
        slide = self.add_slide()
        self.add_header(
            slide,
            tag_text="egSYS & PMSC  /  RELATÓRIO EXECUTIVO 2026",
            title_text="Painel do Cliente PMSC: Visibilidade, Métricas e Jornada do Chamado",
            subtitle_text="Superando o portal legado do Jira: trilha da jornada em 8 etapas, gráficos de observabilidade e filtros salvos para a PMSC.",
            tag_color=COLOR_CYAN,
        )

        # Card de Destaque Superior
        c_destaque = self.add_card(slide, 0.75, 2.30, 11.83, 1.35, fill_color=COLOR_CARD_BLUE, border_color=COLOR_BORDER_CYAN)
        tf_d = c_destaque.text_frame
        tf_d.word_wrap = True
        tf_d.margin_left = tf_d.margin_right = Inches(0.35)
        tf_d.margin_top = Inches(0.25)
        p_d1 = tf_d.paragraphs[0]
        r_d1 = p_d1.add_run()
        r_d1.text = "⚡ BACKLOG ATIVO: 25 CHAMADOS   •   📊 OBSERVABILIDADE VISUAL TOTAL   •   🛡️ ESTEIRA COM POSSE DA BOLA"
        r_d1.font.name = FONT_DISPLAY
        r_d1.font.size = Pt(17.0)
        r_d1.font.bold = True
        r_d1.font.color.rgb = COLOR_LIME

        p_d2 = tf_d.add_paragraph()
        p_d2.space_before = Pt(8)
        r_d2 = p_d2.add_run()
        r_d2.text = "Ambiente exclusivo homologado para a gestão da PMSC (João Mário Mazzola, Ilclemar Vieira, Alex Sandro e Cap Thiesen)."
        r_d2.font.name = FONT_BODY
        r_d2.font.size = Pt(11.5)
        r_d2.font.color.rgb = COLOR_TEXT_MUTED

        # Card de Decisão & Resultados
        c_decisao = self.add_card(slide, 0.75, 3.90, 11.83, 2.70, fill_color=COLOR_CARD_DARK, border_color=COLOR_BORDER)
        tf_dec = c_decisao.text_frame
        tf_dec.word_wrap = True
        tf_dec.margin_left = tf_dec.margin_right = Inches(0.35)
        tf_dec.margin_top = Inches(0.25)

        p_h = tf_dec.paragraphs[0]
        r_h = p_h.add_run()
        r_h.text = "O SALTO DE TRANSPARÊNCIA E FUNCIONALIDADES FRENTE AO JIRA LEGADO"
        r_h.font.name = FONT_BODY
        r_h.font.size = Pt(12)
        r_h.font.bold = True
        r_h.font.color.rgb = COLOR_CYAN

        bullets = [
            ("Trilha Visual da Jornada PMSC: ", "O chamado deixa de ser um rótulo estático. O gestor visualiza em 1 clique em qual das 8 etapas a demanda se encontra e há quantos dias está na fase."),
            ("Dashboard Gráfico das 4 Frentes Policiais: ", "Gráficos de status, prioridade e tendência nas áreas Cidadão (190/Mobile), SADE (CAD), Integração e Operações."),
            ("Filtros Salvos pelo Gestor da PM: ", "Possibilidade de criar e salvar listagens personalizadas no perfil do usuário (/filtros) para pautas de reuniões, ausente no Jira legado."),
            ("Síntese Matemática Incontestável: ", "Decomposição exata de 25 chamados ativos (0 Novas + 24 Em Atendimento egSYS + 1 Aguardando Validação PMSC), isolando 25 entregas finalizadas no ciclo de 90 dias."),
        ]

        for b_title, b_desc in bullets:
            p = tf_dec.add_paragraph()
            p.space_before = Pt(7)
            r1 = p.add_run()
            r1.text = "• " + b_title
            r1.font.name = FONT_BODY
            r1.font.size = Pt(11)
            r1.font.bold = True
            r1.font.color.rgb = COLOR_TEXT_LIGHT

            r2 = p.add_run()
            r2.text = b_desc
            r2.font.name = FONT_BODY
            r2.font.size = Pt(10.5)
            r2.font.color.rgb = COLOR_TEXT_MUTED

        self.add_footer(slide)

    # ==============================================================================
    # SLIDE 2: O DESAFIO HISTÓRICO NA PMSC (LIMITAÇÕES DO JIRA LEGADO)
    # ==============================================================================
    def build_slide_2(self):
        slide = self.add_slide()
        self.add_header(
            slide,
            tag_text="ANTES DO NOVO PAINEL  /  LIMITAÇÕES DO JIRA PADRÃO",
            title_text="O portal legado do Jira mantinha a PMSC sem visão do fluxo real.",
            subtitle_text="Sem gráficos, sem esteira de ação, sem filtros salvos e com a falsa impressão de atrasos generalizados.",
            slide_num_str="02",
            tag_color=COLOR_WARN,
        )

        riscos = [
            (0.75, 2.35, "🔴 SEM VISUALIZAÇÃO DA TRILHA", "Status Estático e Opaco", "O gestor da PM via apenas um rótulo básico ('Em Andamento'). Impossível saber se a demanda estava em triagem técnica, codificação de software, testes de QA ou aguardando a própria PM."),
            (6.85, 2.35, "🔴 SEM GRÁFICOS OU DASHBOARDS", "Ausência Total de Observabilidade", "Nenhum gráfico disponível ao cliente no portal Jira padrão. O gestor recebia uma lista crua em formato de planilha, sem visão de gargalos por área policial e sem divisão por severidade."),
            (0.75, 4.35, "🔴 SEM FILTROS SALVOS PELO CLIENTE", "Zero Personalização de Trabalho", "Buscas rudimentares que truncavam dados. O gestor da PMSC não conseguia salvar suas listagens filtradas e tinha que reconstruir filtros manuais em toda reunião."),
            (6.85, 4.35, "🔴 A ILUSÃO DOS 77 CHAMADOS", "Ambiguidade & Sem Posse da Bola", "O portal somava 25 chamados já entregues com os abertos, criando a falsa impressão de 77 pendências sem deixar claro quem detinha a responsabilidade da próxima ação."),
        ]

        for left, top, tag, title, desc in riscos:
            card = self.add_card(slide, left, top, 5.73, 1.80)
            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.25)
            tf.margin_top = Inches(0.18)

            p1 = tf.paragraphs[0]
            r1 = p1.add_run()
            r1.text = tag
            r1.font.name = FONT_BODY
            r1.font.size = Pt(10)
            r1.font.bold = True
            r1.font.color.rgb = COLOR_RED

            p2 = tf.add_paragraph()
            p2.space_before = Pt(3)
            r2 = p2.add_run()
            r2.text = title
            r2.font.name = FONT_DISPLAY
            r2.font.size = Pt(13)
            r2.font.bold = True
            r2.font.color.rgb = COLOR_TEXT_LIGHT

            p3 = tf.add_paragraph()
            p3.space_before = Pt(4)
            r3 = p3.add_run()
            r3.text = desc
            r3.font.name = FONT_BODY
            r3.font.size = Pt(9.5)
            r3.font.color.rgb = COLOR_TEXT_MUTED

        self.add_callout(
            slide,
            0.75, 6.35, 11.83, 0.48,
            "⚠️ Impacto Anterior: Reuniões tensas de conferência manual de tickets em vez de foco na evolução da tecnologia das viaturas e guarnições.",
            accent_color=COLOR_WARN,
        )
        self.add_footer(slide)

    # ==============================================================================
    # SLIDE 3: A SOLUÇÃO: O NOVO PAINEL DO CLIENTE PMSC
    # ==============================================================================
    def build_slide_3(self):
        slide = self.add_slide()
        self.add_header(
            slide,
            tag_text="A SOLUÇÃO  /  NOVO PAINEL EXCLUSIVO PMSC",
            title_text="O JiraView entrega à PMSC o controle que o Jira legado não dava.",
            subtitle_text="Dashboards gráficos, trilha da jornada em gaveta lateral e filtros personalizados para a gestão policial.",
            slide_num_str="03",
            tag_color=COLOR_CYAN,
        )

        pilares = [
            (0.75, 2.25, 3.75, 4.00, "VISÃO POR ÁREA POLICIAL", "Abas Especializadas na PM", [
                ("🏷️ Cidadão: ", "Aplicativo de viatura mobile e PMSC Cidadão (190)."),
                ("🏷️ SADE: ", "Despacho operacional CAD, telas de atendimento e servidores."),
                ("🏷️ Integração: ", "Barramentos, APIs Detran/SSP e webservices externos."),
                ("🏷️ Operações: ", "Programação operacional, escalas e ferramentas de apoio."),
            ]),
            (4.79, 2.25, 3.75, 4.00, "FILTROS SALVOS & JQL VISUAL", "Módulo de Personalização", [
                ("Filtros Salvos pelo Gestor: ", "Módulo (/filtros) para salvar e reusar visões em 1 clique."),
                ("Construtor Visual de Filtros: ", "Filtre por campo, operador e valor sem decorar sintaxe."),
                ("Janelas Temporais: ", "Filtros executivos em 90d (padrão), 6m, 12m e ano corrente."),
                ("Exportação (#: 1 a N): ", "Download imediato em Excel (.xlsx), Markdown e CSV."),
            ]),
            (8.83, 2.25, 3.75, 4.00, "TRILHA & OBSERVABILIDADE", "Gaveta Lateral (Drawer)", [
                ("Trilha da Jornada: ", "Esteira de 8 etapas exibida em 1 clique sem reload de tela."),
                ("Cálculo de Tempo por Fase: ", "Veja quantos dias o chamado permaneceu em cada etapa."),
                ("Indicador de Posse da Bola: ", "Clareza se a ação é da egSYS ou da equipe da PMSC."),
                ("Links 1-Click ao Jira: ", "Abertura direta do chamado oficial em nova aba."),
            ]),
        ]

        for left, top, width, height, tag, title, bullets in pilares:
            card = self.add_card(slide, left, top, width, height)
            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.25)
            tf.margin_top = Inches(0.22)

            p1 = tf.paragraphs[0]
            r1 = p1.add_run()
            r1.text = tag
            r1.font.name = FONT_BODY
            r1.font.size = Pt(10)
            r1.font.bold = True
            r1.font.color.rgb = COLOR_CYAN

            p2 = tf.add_paragraph()
            p2.space_before = Pt(3)
            r2 = p2.add_run()
            r2.text = title
            r2.font.name = FONT_DISPLAY
            r2.font.size = Pt(13.5)
            r2.font.bold = True
            r2.font.color.rgb = COLOR_TEXT_LIGHT

            for b_label, b_text in bullets:
                p = tf.add_paragraph()
                p.space_before = Pt(7)
                rb1 = p.add_run()
                rb1.text = "• " + b_label
                rb1.font.name = FONT_BODY
                rb1.font.size = Pt(10)
                rb1.font.bold = True
                rb1.font.color.rgb = COLOR_TEXT_LIGHT

                rb2 = p.add_run()
                rb2.text = b_text
                rb2.font.name = FONT_BODY
                rb2.font.size = Pt(9.5)
                rb2.font.color.rgb = COLOR_TEXT_MUTED

        self.add_callout(
            slide,
            0.75, 6.38, 11.83, 0.48,
            "🎯 Resultado: O gestor da PMSC obtém a resposta exata sobre qualquer demanda em menos de 3 segundos.",
            accent_color=COLOR_LIME,
        )
        self.add_footer(slide)

    # ==============================================================================
    # SLIDE 4: RADIOGRAFIA MATEMÁTICA DO BACKLOG PMSC (CICLO DE 90 DIAS)
    # ==============================================================================
    def build_slide_4(self):
        slide = self.add_slide()
        self.add_header(
            slide,
            tag_text="MÉTRICAS ATIVAS  /  CARTEIRA PMSC",
            title_text="A decomposição exata da carteira ativa da PMSC: 25 chamados.",
            subtitle_text="Apresentação aritmética auditada eliminando qualquer divergência entre a PMSC e a equipe técnica da egSYS.",
            slide_num_str="04",
            tag_color=COLOR_LIME,
        )

        bignumbers = [
            (0.75, 2.25, "25", "TOTAL DO BACKLOG ATIVO PMSC", "Somatório real e auditado de todas as solicitações ativas no ciclo contratual de 90 dias."),
            (6.85, 2.25, "0", "NOVAS SOLICITAÇÕES EM TRIAGEM", "Todas as demandas encaminhadas para atendimento técnico e engenharia de software."),
            (0.75, 4.30, "24", "EM ATENDIMENTO TÉCNICO & ENGENHARIA", "Chamados em análise profunda, codificação ativa e testes de qualidade pela engenharia egSYS."),
            (6.85, 4.30, "1", "AGUARDANDO VALIDAÇÃO DA PMSC", "Demanda entregue em homologação aguardando aceite formal pela equipe da PM."),
        ]

        for left, top, num, title, desc in bignumbers:
            card = self.add_card(slide, left, top, 5.73, 1.90)
            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.25)
            tf.margin_top = Inches(0.18)

            p_num = tf.paragraphs[0]
            r_num = p_num.add_run()
            r_num.text = num
            r_num.font.name = FONT_DISPLAY
            r_num.font.size = Pt(38)
            r_num.font.bold = True
            r_num.font.color.rgb = COLOR_LIME

            p_title = tf.add_paragraph()
            p_title.space_before = Pt(2)
            r_title = p_title.add_run()
            r_title.text = title
            r_title.font.name = FONT_BODY
            r_title.font.size = Pt(10.5)
            r_title.font.bold = True
            r_title.font.color.rgb = COLOR_CYAN

            p_desc = tf.add_paragraph()
            p_desc.space_before = Pt(4)
            r_desc = p_desc.add_run()
            r_desc.text = desc
            r_desc.font.name = FONT_BODY
            r_desc.font.size = Pt(9.5)
            r_desc.font.color.rgb = COLOR_TEXT_MUTED

        self.add_callout(
            slide,
            0.75, 6.38, 11.83, 0.48,
            "📈 Isolamento do Histórico: 25 chamados já foram entregues com sucesso no ciclo de 90 dias e permanecem catalogados para fins de auditoria.",
            accent_color=COLOR_LIME,
        )
        self.add_footer(slide)

    # ==============================================================================
    # SLIDE 5: AUDITORIA DE INDICADORES DA PMSC (RAIO-X DE EVIDÊNCIAS)
    # ==============================================================================
    def build_slide_5(self):
        slide = self.add_slide()
        self.add_header(
            slide,
            tag_text="AUDITORIA DE INDICADORES  /  EVIDÊNCIAS PMSC",
            title_text="Raio-X da base PMSC: lastro técnico e rastreabilidade total.",
            subtitle_text="Como cada número e status da PMSC é auditado em tempo real com base nos registros do Jira Cloud.",
            slide_num_str="05",
            tag_color=COLOR_CYAN,
        )

        evidencias = [
            (0.75, 2.25, "⚡ BACKLOG ATIVO PMSC (25 CHAMADOS EM ABERTO)",
             "ESCOPO: Demandas ativas do projeto HDPMSC no ciclo de 90 dias.  |  EVIDÊNCIA: 24 em Atendimento Técnico egSYS + 1 Aguardando Validação da PMSC. 25 entregas segregadas no histórico (total 50)."),
            (0.75, 3.30, "🎯 AGUARDANDO VALIDAÇÃO PMSC (1 CHAMADO - POSSE DA BOLA PMSC)",
             "ESCOPO: Demanda concluída pela egSYS em ambiente de testes da PMSC.  |  EVIDÊNCIA: Status 'Homologação Cliente'; ação pendente com a equipe técnica da PM."),
            (0.75, 4.35, "⚙️ EM TRATAMENTO TÉCNICO EGSYS (24 CHAMADOS - POSSE DA BOLA EGSYS)",
             "ESCOPO: Chamados sob responsabilidade direta dos desenvolvedores da egSYS.  |  EVIDÊNCIA: Itens nas fases de Análise de Dev, Em Desenvolvimento e Testes de Qualidade (QA)."),
            (0.75, 5.40, "💾 FILTROS TEMPORAIS PRECISOS & EXPORTAÇÃO (# 1 A N)",
             "ESCOPO: Autonomia de análise por período (30d a 1 ano) e download executivo.  |  EVIDÊNCIA: Seletor temporal calibrado no painel e módulo de exportação em Excel nativo (.xlsx), MD e CSV."),
        ]

        for left, top, tag_title, content in evidencias:
            card = self.add_card(slide, left, top, 11.83, 0.95)
            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.25)
            tf.margin_top = Inches(0.12)

            p1 = tf.paragraphs[0]
            r1 = p1.add_run()
            r1.text = tag_title
            r1.font.name = FONT_DISPLAY
            r1.font.size = Pt(11)
            r1.font.bold = True
            r1.font.color.rgb = COLOR_LIME

            p2 = tf.add_paragraph()
            p2.space_before = Pt(3)
            r2 = p2.add_run()
            r2.text = content
            r2.font.name = FONT_BODY
            r2.font.size = Pt(9.5)
            r2.font.color.rgb = COLOR_TEXT_LIGHT

        self.add_callout(
            slide,
            0.75, 6.45, 11.83, 0.42,
            "🔍 Rigor de Auditoria: Dados extraídos diretamente do projeto oficial HDPMSC e sincronizados em tempo real.",
            accent_color=COLOR_CYAN,
        )
        self.add_footer(slide)

    # ==============================================================================
    # SLIDE 6: A ESTEIRA DE 8 ETAPAS & AS NOVAS FUNCIONALIDADES DO PAINEL PMSC
    # ==============================================================================
    def build_slide_6(self):
        slide = self.add_slide()
        self.add_header(
            slide,
            tag_text="CATÁLOGO DE MELHORIAS  /  FUNCIONALIDADES PMSC",
            title_text="A jornada na esteira de ação e os recursos de observabilidade.",
            subtitle_text="Todas as ferramentas que a PMSC precisava e que o portal padrão do Jira nunca ofereceu.",
            slide_num_str="06",
            tag_color=COLOR_CYAN,
        )

        # Painel Esquerdo: Esteira de 8 Etapas e Posse da Bola
        card_l = self.add_card(slide, 0.75, 2.25, 5.73, 4.55)
        tf_l = card_l.text_frame
        tf_l.word_wrap = True
        tf_l.margin_left = tf_l.margin_right = Inches(0.25)
        tf_l.margin_top = Inches(0.20)

        p_lt = tf_l.paragraphs[0]
        r_lt = p_lt.add_run()
        r_lt.text = "A TRILHA DO CAMINHO (ESTEIRA DE 8 ETAPAS)"
        r_lt.font.name = FONT_DISPLAY
        r_lt.font.size = Pt(13)
        r_lt.font.bold = True
        r_lt.font.color.rgb = COLOR_CYAN

        p_lsub = tf_l.add_paragraph()
        r_lsub = p_lsub.add_run()
        r_lsub.text = "A jornada completa do chamado PMSC com Posse da Bola:"
        r_lsub.font.name = FONT_BODY
        r_lsub.font.size = Pt(9.5)
        r_lsub.font.color.rgb = COLOR_TEXT_MUTED

        etapas = [
            ("01. Triagem (N1)", "Recepção e conferência dos dados da ocorrência."),
            ("02. Triagem (N2)", "Diagnóstico técnico avançado e reprodução de logs."),
            ("03. Análise de Dev", "Refinamento de arquitetura pelos engenheiros de software."),
            ("04. Em Desenvolvimento", "Construção de código e correção de funcionalidades."),
            ("05. QA & Testes", "Homologação técnica e testes automatizados de qualidade."),
            ("06. Validação Interna N1", "Conferência final pelo analista antes da liberação."),
            ("07. Homologação PMSC", "AÇÃO DA PMSC: Validação e homologação pelo órgão."),
            ("08. Concluído", "FINALIZADO: Liberação em produção policial e encerramento."),
        ]

        for num_nome, desc in etapas:
            p = tf_l.add_paragraph()
            p.space_before = Pt(3)
            r1 = p.add_run()
            r1.text = "• " + num_nome + " ➔ "
            r1.font.name = FONT_BODY
            r1.font.size = Pt(9.5)
            r1.font.bold = True
            r1.font.color.rgb = COLOR_LIME if "07" in num_nome or "08" in num_nome else COLOR_TEXT_LIGHT

            r2 = p.add_run()
            r2.text = desc
            r2.font.name = FONT_BODY
            r2.font.size = Pt(9.0)
            r2.font.color.rgb = COLOR_TEXT_MUTED

        # Painel Direito: Lista Completa de Melhorias Funcionais
        card_r = self.add_card(slide, 6.85, 2.25, 5.73, 4.55)
        tf_r = card_r.text_frame
        tf_r.word_wrap = True
        tf_r.margin_left = tf_r.margin_right = Inches(0.25)
        tf_r.margin_top = Inches(0.20)

        p_rt = tf_r.paragraphs[0]
        r_rt = p_rt.add_run()
        r_rt.text = "FUNCIONALIDADES EXCLUSIVAS DO PAINEL PMSC"
        r_rt.font.name = FONT_DISPLAY
        r_rt.font.size = Pt(13)
        r_rt.font.bold = True
        r_rt.font.color.rgb = COLOR_CYAN

        p_rsub = tf_r.add_paragraph()
        r_rsub = p_rsub.add_run()
        r_rsub.text = "Recursos de observabilidade ausentes no portal legado:"
        r_rsub.font.name = FONT_BODY
        r_rsub.font.size = Pt(9.5)
        r_rsub.font.color.rgb = COLOR_TEXT_MUTED

        melhorias = [
            ("Gaveta Lateral de Diagnóstico (Drawer): ", "Abre em 1 clique sem reload, exibindo a esteira, o tempo exato acumulado em cada etapa e a posse da bola."),
            ("Módulo de Filtros Salvos pelo Gestor da PM: ", "Permite criar filtros personalizados e salvá-los no perfil (/filtros) para reuso diário com um clique."),
            ("Dashboard com 4 Gráficos Interativos: ", "Gráficos Chart.js (status, prioridade, solicitantes e linha temporal) atualizados em tempo real."),
            ("Rastreabilidade de Engenharia (issuelinks): ", "Vínculo visual direto com tarefas de desenvolvimento (PSC) ligadas ao chamado HDPMSC."),
            ("Exportação Corporativa (# 1 a N): ", "Download imediato em Excel (.xlsx), Markdown e CSV com índice sequencial (#) para pautas de reunião da PM."),
        ]

        for m_title, m_desc in melhorias:
            p = tf_r.add_paragraph()
            p.space_before = Pt(6)
            r1 = p.add_run()
            r1.text = "• " + m_title
            r1.font.name = FONT_BODY
            r1.font.size = Pt(9.5)
            r1.font.bold = True
            r1.font.color.rgb = COLOR_TEXT_LIGHT

            r2 = p.add_run()
            r2.text = m_desc
            r2.font.name = FONT_BODY
            r2.font.size = Pt(9.0)
            r2.font.color.rgb = COLOR_TEXT_MUTED

        self.add_footer(slide)

    # ==============================================================================
    # SLIDE 7: AS 4 ÁREAS DE ATENDIMENTO DA TECNOLOGIA POLICIAL
    # ==============================================================================
    def build_slide_7(self):
        slide = self.add_slide()
        self.add_header(
            slide,
            tag_text="FRENTES DE TECNOLOGIA  /  ÁREAS PMSC",
            title_text="Atendimento especializado por área de negócio da Polícia Militar.",
            subtitle_text="Classificação automática de chamados garantindo que cada especialista da PM acompanhe suas demandas.",
            slide_num_str="07",
            tag_color=COLOR_CYAN,
        )

        # Painel Esquerdo: 4 Áreas da PMSC
        card_l = self.add_card(slide, 0.75, 2.25, 7.50, 4.55)
        tf_l = card_l.text_frame
        tf_l.word_wrap = True
        tf_l.margin_left = tf_l.margin_right = Inches(0.25)
        tf_l.margin_top = Inches(0.20)

        p_lt = tf_l.paragraphs[0]
        r_lt = p_lt.add_run()
        r_lt.text = "AS 4 FRENTES ESTRATÉGICAS DE SUSTENTAÇÃO PMSC"
        r_lt.font.name = FONT_DISPLAY
        r_lt.font.size = Pt(13)
        r_lt.font.bold = True
        r_lt.font.color.rgb = COLOR_CYAN

        p_lsub = tf_l.add_paragraph()
        r_lsub = p_lsub.add_run()
        r_lsub.text = "Mapeamento inteligente derivado dos componentes e labels do Jira:"
        r_lsub.font.name = FONT_BODY
        r_lsub.font.size = Pt(9.5)
        r_lsub.font.color.rgb = COLOR_TEXT_MUTED

        areas_info = [
            ("🏷️ CIDADÃO (190 & Mobile Policial)", "Aplicativo PMSC Cidadão, tablets operacionais embarcados em viaturas, geolocalização e despachos móveis de campo."),
            ("🏷️ SADE (Sistema de Atendimento e Despacho de Emergência)", "Núcleo CAD de atendimento 190, despacho de viaturas em mapa, servidores de aplicação e balanceamento de chamadas."),
            ("🏷️ INTEGRAÇÃO (APIs & Barramentos)", "Barramento de serviços com Detran, SSP/SC, Poder Judiciário, sistemas de boletins de ocorrência e webservices externos."),
            ("🏷️ OPERAÇÕES (Gestão & Escalas Operacionais)", "Programação operacional, módulos de escala de serviço, viaturas, efetivos e relatórios gerenciais da corporação."),
        ]

        for a_title, a_desc in areas_info:
            p = tf_l.add_paragraph()
            p.space_before = Pt(7)
            r1 = p.add_run()
            r1.text = a_title + "\n"
            r1.font.name = FONT_BODY
            r1.font.size = Pt(10.5)
            r1.font.bold = True
            r1.font.color.rgb = COLOR_LIME

            r2 = p.add_run()
            r2.text = a_desc
            r2.font.name = FONT_BODY
            r2.font.size = Pt(9.5)
            r2.font.color.rgb = COLOR_TEXT_MUTED

        # Painel Direito Superior: Diagnóstico Instantâneo
        card_ru = self.add_card(slide, 8.55, 2.25, 4.03, 2.15)
        tf_ru = card_ru.text_frame
        tf_ru.word_wrap = True
        tf_ru.margin_left = tf_ru.margin_right = Inches(0.20)
        tf_ru.margin_top = Inches(0.18)

        p_ru1 = tf_ru.paragraphs[0]
        r_ru1 = p_ru1.add_run()
        r_ru1.text = "≤ 3 seg"
        r_ru1.font.name = FONT_DISPLAY
        r_ru1.font.size = Pt(32)
        r_ru1.font.bold = True
        r_ru1.font.color.rgb = COLOR_LIME

        p_ru2 = tf_ru.add_paragraph()
        r_ru2 = p_ru2.add_run()
        r_ru2.text = "TEMPO DE DIAGNÓSTICO POR ÁREA"
        r_ru2.font.name = FONT_BODY
        r_ru2.font.size = Pt(10)
        r_ru2.font.bold = True
        r_ru2.font.color.rgb = COLOR_CYAN

        p_ru3 = tf_ru.add_paragraph()
        p_ru3.space_before = Pt(3)
        r_ru3 = p_ru3.add_run()
        r_ru3.text = "O gestor clica na aba da sua área (ex: Cidadão ou SADE) e visualiza instantaneamente os chamados abertos e o status de cada um."
        r_ru3.font.name = FONT_BODY
        r_ru3.font.size = Pt(9.0)
        r_ru3.font.color.rgb = COLOR_TEXT_MUTED

        # Painel Direito Inferior: Compatibilidade com Intranet
        card_rd = self.add_card(slide, 8.55, 4.65, 4.03, 2.15)
        tf_rd = card_rd.text_frame
        tf_rd.word_wrap = True
        tf_rd.margin_left = tf_rd.margin_right = Inches(0.20)
        tf_rd.margin_top = Inches(0.18)

        p_rd1 = tf_rd.paragraphs[0]
        r_rd1 = p_rd1.add_run()
        r_rd1.text = "100%"
        r_rd1.font.name = FONT_DISPLAY
        r_rd1.font.size = Pt(32)
        r_rd1.font.bold = True
        r_rd1.font.color.rgb = COLOR_LIME

        p_rd2 = tf_rd.add_paragraph()
        r_rd2 = p_rd2.add_run()
        r_rd2.text = "COMPATIBILIDADE COM A INTRANET PM"
        r_rd2.font.name = FONT_BODY
        r_rd2.font.size = Pt(10)
        r_rd2.font.bold = True
        r_rd2.font.color.rgb = COLOR_CYAN

        p_rd3 = tf_rd.add_paragraph()
        p_rd3.space_before = Pt(3)
        r_rd3 = p_rd3.add_run()
        r_rd3.text = "Gráficos e bibliotecas vendored localmente sem dependência de internet aberta. Alta estabilidade mesmo sob firewalls rígidos."
        r_rd3.font.name = FONT_BODY
        r_rd3.font.size = Pt(9.0)
        r_rd3.font.color.rgb = COLOR_TEXT_MUTED

        self.add_footer(slide)

    # ==============================================================================
    # SLIDE 8: COMPROMISSOS OPERACIONAIS & PRÓXIMOS PASSOS PMSC
    # ==============================================================================
    def build_slide_8(self):
        slide = self.add_slide()
        self.add_header(
            slide,
            tag_text="COMPROMISSO CONTÍNUO  /  PRÓXIMOS PASSOS PMSC",
            title_text="egSYS & PMSC: Parceria estratégica em tecnologia de missão crítica.",
            subtitle_text="Alinhamento contínuo para garantir estabilidade, segurança e agilidade nas operações da Polícia Militar.",
            slide_num_str="08",
            tag_color=COLOR_CYAN,
        )

        colunas = [
            (0.75, 2.25, 3.75, 4.55, "ENTREGUE À PMSC (v0.4.1)", "Transparência Consolidada", [
                ("Painel Exclusivo PMSC: ", "Acesso seguro via suporte-monitor.egsys.siseg.tech/painel_sc."),
                ("Trilha da Jornada em 8 Etapas: ", "Esteira visual com cálculo de tempo por fase e posse da bola."),
                ("Dashboards & 4 Gráficos: ", "Gráficos Chart.js responsivos no padrão Dark Glass."),
                ("Filtros Salvos pelo Gestor: ", "Módulo CRUD (/filtros) para salvar visões favoritas da PM."),
                ("Exportação Corporativa: ", "Relatórios em Excel (.xlsx) numerados sequencialmente (# 1 a N)."),
            ]),
            (4.79, 2.25, 3.75, 4.55, "PRÓXIMOS PASSOS CONJUNTOS", "Evolução Contínua (2026/2027)", [
                ("Reuniões Periódicas Ágeis: ", "Uso das planilhas exportadas como pauta oficial de alinhamento."),
                ("Alertas Proativos de SLA: ", "Notificação antecipada de demandas prioritárias da corporação."),
                ("Priorização de Homologações: ", "Aceleração conjunta do chamado com posse da PMSC."),
                ("Módulo de Capacitação N1: ", "Redução de reaberturas por meio de orientações operacionais."),
                ("Evolução Contínua Mobile: ", "Acompanhamento em tempo real dos patches de APK de viatura."),
            ]),
            (8.83, 2.25, 3.75, 4.55, "SÍNTESE DE VALOR PMSC", "Retorno para a Gestão Policial", [
                ("⚡ VELOCIDADE: ", "Diagnóstico de qualquer chamado em ≤ 3 segundos sem atrito."),
                ("🛡️ CONFIANÇA: ", "Apresentação aritmética auditada sem divergência de números."),
                ("🤝 PARCERIA: ", "Trabalho em conjunto com foco em destravar homologações da PM."),
                ("📈 PREVISIBILIDADE: ", "Acompanhamento transparente das entregas de software."),
                ("🚔 MISSÃO CRÍTICA: ", "Garantia de tecnologia estável para o policial militar na ponta."),
            ]),
        ]

        for left, top, width, height, tag, title, bullets in colunas:
            card = self.add_card(slide, left, top, width, height)
            tf = card.text_frame
            tf.word_wrap = True
            tf.margin_left = tf.margin_right = Inches(0.25)
            tf.margin_top = Inches(0.22)

            p1 = tf.paragraphs[0]
            r1 = p1.add_run()
            r1.text = tag
            r1.font.name = FONT_BODY
            r1.font.size = Pt(10)
            r1.font.bold = True
            r1.font.color.rgb = COLOR_CYAN

            p2 = tf.add_paragraph()
            p2.space_before = Pt(3)
            r2 = p2.add_run()
            r2.text = title
            r2.font.name = FONT_DISPLAY
            r2.font.size = Pt(13)
            r2.font.bold = True
            r2.font.color.rgb = COLOR_TEXT_LIGHT

            for b_label, b_text in bullets:
                p = tf.add_paragraph()
                p.space_before = Pt(6)
                rb1 = p.add_run()
                rb1.text = "• " + b_label
                rb1.font.name = FONT_BODY
                rb1.font.size = Pt(9.5)
                rb1.font.bold = True
                rb1.font.color.rgb = COLOR_LIME if "VELOCIDADE" in b_label or "CONFIANÇA" in b_label or "MISSÃO" in b_label else COLOR_TEXT_LIGHT

                rb2 = p.add_run()
                rb2.text = b_text
                rb2.font.name = FONT_BODY
                rb2.font.size = Pt(9.0)
                rb2.font.color.rgb = COLOR_TEXT_MUTED

        self.add_footer(slide)

    def generate_all(self):
        print("Montando Slide 1 (Capa & Briefing PMSC)...")
        self.build_slide_1()
        print("Montando Slide 2 (Diagnóstico Histórico PMSC)...")
        self.build_slide_2()
        print("Montando Slide 3 (A Solução: Painel do Cliente)...")
        self.build_slide_3()
        print("Montando Slide 4 (Radiografia Matemática do Backlog)...")
        self.build_slide_4()
        print("Montando Slide 5 (Auditoria de Indicadores PMSC)...")
        self.build_slide_5()
        print("Montando Slide 6 (A Esteira de 8 Etapas & Funcionalidades)...")
        self.build_slide_6()
        print("Montando Slide 7 (As 4 Áreas da Tecnologia Policial)...")
        self.build_slide_7()
        print("Montando Slide 8 (Compromissos & Próximos Passos)...")
        self.build_slide_8()

        self.prs.save(self.output_pptx)
        print(f"✅ PPTX salvo com sucesso em: {self.output_pptx}")

        out_dir = os.path.dirname(os.path.abspath(self.output_pptx)) or "."
        try:
            print(f"Executando conversão headless para PDF via LibreOffice...")
            subprocess.run(
                ["libreoffice", "--headless", "--convert-to", "pdf", self.output_pptx, "--outdir", out_dir],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            pdf_path = os.path.splitext(self.output_pptx)[0] + ".pdf"
            print(f"✅ PDF gerado com sucesso em: {pdf_path}")
        except Exception as e:
            print(f"⚠️ Aviso na conversão LibreOffice para PDF: {e}")


if __name__ == "__main__":
    target_pptx = sys.argv[1] if len(sys.argv) > 1 else "/home/prado/Documents/egSYS-JiraView-PMSC-Executivo.pptx"
    builder = JiraViewPMSCDeckBuilder(target_pptx)
    builder.generate_all()
