"""Build the illustrated manual offline. Never imports the app or a database.

Requires reportlab and Pillow in the selected artifact runtime. Source material
is docs/manual/conteudo.json; screenshots are browser observations, not renders
of mockups. SVG UML exports and a Markdown edition accompany the PDF.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.graphics import renderSVG
from reportlab.graphics.shapes import Drawing, Ellipse, Line, PolyLine, Rect, String, Circle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs' / 'manual'
INK = colors.HexColor('#101827')
MUTED = colors.HexColor('#4B5563')
BLUE = colors.HexColor('#1648CF')
PALE = colors.HexColor('#EEF3FB')
BORDER = colors.HexColor('#D9D9D9')
PW, PH = A4
LW, LH = landscape(A4)
MARGIN = 40


def fonts():
    font_dir = Path('C:/Windows/Fonts')
    paths = [font_dir / 'arial.ttf', font_dir / 'arialbd.ttf', font_dir / 'ariali.ttf']
    if not all(p.is_file() for p in paths):
        import reportlab
        font_dir = Path(reportlab.__file__).parent / 'fonts'
        paths = [font_dir / 'Vera.ttf', font_dir / 'VeraBd.ttf', font_dir / 'VeraIt.ttf']
    for name, path in zip(('Body', 'BodyBold', 'BodyItalic'), paths):
        pdfmetrics.registerFont(TTFont(name, str(path)))
    pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='BodyItalic', boldItalic='BodyBold')


def styles():
    s = getSampleStyleSheet()
    for name in ('Normal', 'BodyText', 'Title', 'Heading1', 'Heading2', 'Heading3'):
        s[name].fontName = 'Body'
        s[name].textColor = colors.black
    s['BodyText'].fontSize = 10.5
    s['BodyText'].leading = 14.2
    s['BodyText'].spaceAfter = 7
    s['Heading1'].fontName = 'BodyBold'
    s['Heading1'].fontSize = 21
    s['Heading1'].leading = 25
    s['Heading1'].spaceAfter = 10
    s['Heading2'].fontName = 'BodyBold'
    s['Heading2'].fontSize = 12
    s['Heading2'].leading = 15
    s['Heading2'].spaceBefore = 10
    s['Heading2'].spaceAfter = 5
    s['Title'].fontName = 'BodyBold'
    s['Title'].fontSize = 32
    s['Title'].leading = 38
    s.add(ParagraphStyle('Kicker', fontName='BodyBold', fontSize=9, leading=12, textColor=BLUE, spaceAfter=8))
    s.add(ParagraphStyle('Meta', fontName='Body', fontSize=9, leading=12, textColor=MUTED, spaceAfter=8))
    s.add(ParagraphStyle('Caption', fontName='Body', fontSize=8.5, leading=11, textColor=MUTED, spaceBefore=5, spaceAfter=9))
    s.add(ParagraphStyle('Step', parent=s['BodyText'], leftIndent=18, firstLineIndent=-18, spaceAfter=5))
    s.add(ParagraphStyle('Rule', parent=s['BodyText'], fontSize=9.5, leading=12.7, spaceAfter=5))
    s.add(ParagraphStyle('TableBody', parent=s['BodyText'], fontSize=9, leading=12, spaceAfter=0))
    s.add(ParagraphStyle('TableHead', parent=s['TableBody'], fontName='BodyBold', textColor=colors.white))
    s.add(ParagraphStyle('TOC0', fontName='BodyBold', fontSize=10.5, leading=15, spaceBefore=5))
    s.add(ParagraphStyle('TOC1', fontName='Body', fontSize=9.5, leading=13, leftIndent=13, firstLineIndent=0))
    return s


class Manual(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, '_doc_heading'):
            title, key = flowable._doc_heading
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, 0, False)
            if key != 'sumario':
                self.notify('TOCEntry', (0, title, self.page, key))


def footer(canvas, doc):
    w, h = canvas._pagesize
    canvas.saveState()
    canvas.setFont('Body', 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(MARGIN, h - 23, 'FaeHub+ | Documentação funcional e manual do usuário')
    canvas.drawString(MARGIN, 23, 'Edição 22/10/2026 | Capturas em ambiente local de demonstração')
    canvas.drawRightString(w - MARGIN, 23, str(doc.page))
    canvas.restoreState()


def p(text, style):
    return Paragraph(escape(str(text)).replace('\n', '<br/>'), style)


def heading(text, key, s):
    result = p(text, s['Heading1'])
    result._doc_heading = (text, key)
    return result


def table(rows, widths, s, padding=8):
    converted = [[p(cell, s['TableHead' if i == 0 else 'TableBody']) for cell in row] for i, row in enumerate(rows)]
    t = Table(converted, colWidths=widths, repeatRows=1, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), INK),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, PALE]),
        ('GRID', (0, 0), (-1, -1), .45, BORDER),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), padding),
        ('BOTTOMPADDING', (0, 0), (-1, -1), padding),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    return t


ROLE_ROWS = [
    ['Área ou ação', 'Aluno', 'Professor', 'Direção', 'Responsável'],
    ['Boletim e resumo de resultados', 'Próprio', 'Lança N1/N2', 'Relatórios', 'Vinculados'],
    ['Chamada por aula', 'Consulta', 'Registra', 'Relatórios', 'Resumo'],
    ['Atividades', 'Entrega', 'Publica e corrige', 'Sem estúdio docente', 'Sem entrega'],
    ['Diário', 'Sem acesso', 'Registra e envia', 'Valida ou devolve', 'Sem edição'],
    ['Documentos', 'Solicita', 'Sem central', 'Atende e emite', 'Solicita para vinculados'],
    ['Contas e estrutura', 'Sem gestão', 'Consulta vínculos', 'Gerencia', 'Sem gestão'],
    ['Calendário', 'Agenda visível', 'Consulta', 'Publica e cancela', 'Consulta público permitido'],
    ['Mensagens', 'Contatos autorizados', 'Contatos autorizados', 'Contatos autorizados', 'Equipe e vinculados'],
    ['Comunicados', 'Lê e organiza', 'Publica próprios avisos', 'Notificações institucionais', 'Notificações elegíveis'],
    ['Segurança pessoal', 'Própria conta', 'Própria conta', 'Própria conta', 'Própria conta'],
    ['FaeNet federada', 'Se elegível', 'Se elegível', 'Se elegível', 'Se elegível'],
]

PROBLEM_ROWS = [
    ['Situação', 'Conferência e encaminhamento'],
    ['Não consigo entrar', 'Confira perfil, usuário ou e-mail e senha. Conta bloqueada exige atendimento da escola; não crie outra identidade para contornar o bloqueio.'],
    ['Convite não chegou', 'Confira spam e e-mail informado. Peça reenvio à direção. A escola deve conferir o transporte de e-mail antes de declarar o convite enviado.'],
    ['Código de recuperação falhou', 'Use o e-mail confirmado e o código mais recente dentro de 30 minutos. Respeite a espera por excesso de tentativas.'],
    ['Perdi o autenticador', 'Use um código de recuperação privado com a senha. Sem ambos, procure o operador; recuperação de senha não remove o segundo fator.'],
    ['Não aparece uma turma', 'Confira vínculo docente vigente ou matrícula ativa. Solicite correção à direção; não use a conta de outra pessoa.'],
    ['Chamada não salva', 'Confira disciplina, data, início e término; marque todos os alunos. Verifique período aberto, vínculo, aula não futura e ausência de sobreposição. Recarregue em conflito de revisão.'],
    ['Anexo não envia', 'Confira formato e tamanho. Use a ação final de envio e consulte a entrega ou conversa para confirmar se o arquivo ficou salvo.'],
    ['Lista ou histórico vazio', 'Limpe os filtros e confira a base consultada. Sem lançamento, chamada ou resultado normalizado não significa nota zero ou falta automática.'],
    ['Documento não abre', 'Confira situação do protocolo e autorização da matrícula. O arquivo emitido fica disponível conforme o estado permitido.'],
    ['FaeNet não conclui entrada', 'Reabra pela entrada oficial. Conta precisa estar ativa e elegível e a ponte precisa estar configurada nos dois serviços. Não compartilhe senhas ou tokens no suporte.'],
    ['Horário divergente', 'Compare grade publicada, evento e fuso. Informe a escola com a data e as telas envolvidas; não presuma que Tempo livre seja intervalo oficial.'],
]


def line(d, points, label=None, dashed=False):
    d.add(PolyLine(points, strokeColor=MUTED, strokeWidth=.8,
                   strokeDashArray=[4, 3] if dashed else None))
    if label:
        x, y, text = label
        tw = pdfmetrics.stringWidth(text, 'Body', 8.5)
        d.add(Rect(x - tw / 2 - 3, y - 3, tw + 6, 12, fillColor=colors.white, strokeColor=None))
        d.add(String(x, y, text, textAnchor='middle', fontName='Body', fontSize=8.5, fillColor=INK))


def class_box(d, x, y, title, fields, mapping):
    width, height = 210, 110
    d.add(Rect(x, y, width, height, strokeColor=INK, strokeWidth=.8, fillColor=colors.white))
    d.add(Rect(x, y + height - 29, width, 29, strokeColor=None, fillColor=PALE))
    d.add(Line(x, y + height - 29, x + width, y + height - 29, strokeColor=INK, strokeWidth=.6))
    d.add(String(x + width / 2, y + height - 18, title, textAnchor='middle', fontName='BodyBold', fontSize=10, fillColor=INK))
    for i, field in enumerate(fields):
        d.add(String(x + 9, y + height - 44 - i * 12, field, fontName='Body', fontSize=8.8, fillColor=INK))
    d.add(String(x + 9, y + 8, mapping, fontName='BodyItalic', fontSize=7.7, fillColor=MUTED))


def class_drawing(kind):
    d = Drawing(750, 450)
    X = [0, 260, 520]
    Y = [320, 165, 10]
    if kind == 'estrutura':
        nodes = [
            ('AnoLetivo', ['id: inteiro', 'nome: texto', 'inicio, fim: data', 'situacao: estado'], 'academic_years'),
            ('Turma', ['id, anoLetivoId: inteiro', 'cursoId: inteiro opcional', 'codigo, turno: texto', 'capacidade: inteiro'], 'classes'),
            ('Curso', ['id: inteiro', 'codigo, nome: texto', 'descricao: texto', 'ativo: booleano'], 'courses'),
            ('Estudante', ['id: inteiro', 'registro: texto unico', 'nome: texto', 'usuario: texto opcional'], 'students'),
            ('Matricula', ['id, estudanteId: inteiro', 'turmaId: inteiro', 'ingresso, fim: data', 'situacao: estado'], 'enrollments'),
            ('OfertaDisciplina', ['id: inteiro', 'turmaId: inteiro', 'disciplinaId: inteiro', 'cargaMinutos: inteiro opcional'], 'class_subjects'),
            ('Usuario', ['username: texto unico', 'nome, papel: texto', 'ativo: booleano', 'senhaHash: texto privado'], 'users'),
            ('VinculoDocente', ['id: inteiro', 'professor: username', 'ofertaId: inteiro', 'vigenciaInicio, fim: data'], 'teacher_subjects'),
            ('Disciplina', ['id: inteiro', 'codigo, nome: texto', 'cargaMinutos: inteiro opcional', 'ativo: booleano'], 'subjects'),
        ]
        edges = [
            ([210, 375, 260, 375], (235, 384, '1    0..*'), False),
            ([520, 375, 470, 375], (495, 384, '0..*    0..1'), False),
            ([210, 220, 260, 220], (235, 229, '1    0..*'), False),
            ([365, 320, 365, 275], (399, 297, '1 / 0..*'), False),
            ([470, 352, 495, 352, 495, 220, 520, 220], (494, 285, '1 / 0..*'), False),
            ([625, 120, 625, 165], (660, 140, '1 / 0..*'), False),
            ([210, 65, 260, 65], (235, 74, '1    0..*'), False),
            ([625, 165, 625, 145, 495, 145, 495, 65, 470, 65], (553, 145, '1 / 0..*'), False),
            ([105, 165, 105, 120], (148, 141, '0..1 / 0..1'), False),
        ]
    elif kind == 'academico':
        nodes = [
            ('OfertaDisciplina', ['id: inteiro', 'turmaId: inteiro', 'disciplinaId: inteiro'], 'class_subjects'),
            ('HorarioSemanal', ['id, ofertaId: inteiro', 'diaSemana: inteiro', 'inicio, fim: hora', 'sala: texto opcional'], 'schedule_slots'),
            ('Aula', ['id, ofertaId: inteiro', 'professor: username', 'inicio, fim: instante', 'revisaoPresenca: inteiro'], 'lessons'),
            ('DiarioAula', ['id, professor: identificador', 'turma, disciplina: texto', 'data, conteudo: registro', 'situacao: estado'], 'class_diary_entries'),
            ('Matricula', ['id: inteiro', 'estudanteId, turmaId: inteiro', 'ingresso, fim: data', 'situacao: estado'], 'enrollments'),
            ('Presenca', ['id, aulaId: inteiro', 'matriculaId: inteiro', 'situacao: presente ou ausente', 'registradoEm: instante'], 'attendance_records'),
            ('LancamentoNota', ['registroAluno, disciplina: texto', 'n1, n2: decimal', '/media = (n1+n2)/2', 'atualizadoEm: instante'], 'grades | fluxo N1/N2 atual'),
            ('Estudante', ['id: inteiro', 'registro: texto unico', 'nome: texto'], 'students'),
            ('Usuario', ['username: texto unico', 'papel: professor ou outro', 'ativo: booleano'], 'users'),
        ]
        edges = [
            ([210, 375, 260, 375], (235, 384, '1    0..*'), False),
            ([105, 430, 105, 444, 625, 444, 625, 430], (365, 437, 'Oferta 1 / Aulas 0..*'), False),
            ([625, 320, 625, 275], (660, 297, '1 / 0..*'), False),
            ([470, 220, 520, 220], (495, 229, '1    0..*'), False),
            ([365, 120, 365, 165], (400, 141, '1 / 0..*'), False),
            ([260, 65, 210, 65], (235, 74, '1    0..*'), True),
            ([105, 320, 105, 275], (151, 297, 'contexto logico'), True),
            ([730, 65, 744, 65, 744, 375, 730, 375], (708, 145, 'docente 1 / 0..*'), False),
        ]
    else:
        nodes = [
            ('Usuario', ['username, nome: texto', 'papel: texto', 'ativo: booleano'], 'users'),
            ('Exercicio', ['id: inteiro', 'autor: username', 'turma, disciplina, titulo: texto', 'prazo: data'], 'exercises'),
            ('Entrega', ['id, exercicioId: inteiro', 'estudante: username', 'resposta: texto', 'enviadoEm: instante'], 'submissions'),
            ('Mensagem', ['id: inteiro', 'remetente, destinatario: texto', 'assunto, corpo: texto', 'enviadoEm: instante'], 'messages'),
            ('Anexo', ['id, entidadeId: inteiro', 'tipoEntidade: discriminador', 'nome, mime, tamanho: dados', 'conteudo: binario privado'], 'file_attachments'),
            ('DocumentoSolicitado', ['id: inteiro', 'solicitante: username', 'registroAluno, tipo: texto', 'protocolo, situacao: texto'], 'document_requests'),
            ('Notificacao', ['id: inteiro', 'destinatario: opcional', 'publico, titulo, corpo: texto', 'acaoUrl: texto'], 'notifications'),
            ('GrupoMensagem', ['id: inteiro', 'nome, turma: texto', 'criador: username'], 'message_groups'),
            ('IntervencaoPedagogica', ['id: inteiro', 'registroAluno: texto', 'autor: username', 'resumo, plano, situacao: texto'], 'pedagogical_interventions'),
        ]
        edges = [
            ([210, 375, 260, 375], (235, 384, '1    0..*'), False),
            ([470, 375, 520, 375], (495, 384, '1    0..*'), False),
            ([105, 320, 105, 275], (149, 297, 'autor 1 / 0..*'), False),
            ([210, 220, 260, 220], (235, 229, '0..* anexos'), True),
            ([365, 275, 365, 297, 625, 297, 625, 320], (507, 297, 'entidade: entrega'), True),
            ([365, 320, 365, 305, 495, 305, 495, 220, 470, 220], (491, 270, 'exercicio'), True),
        ]
    for points, label, dashed in edges:
        line(d, points, label, dashed)
    for i, (title, fields, mapping) in enumerate(nodes):
        class_box(d, X[i % 3], Y[i // 3], title, fields, mapping)
    return d


def actor(d, x, y, name):
    d.add(Circle(x, y + 18, 8, fillColor=colors.white, strokeColor=INK, strokeWidth=1))
    d.add(Line(x, y + 10, x, y - 16, strokeColor=INK))
    d.add(Line(x - 14, y, x + 14, y, strokeColor=INK))
    d.add(Line(x, y - 16, x - 12, y - 32, strokeColor=INK))
    d.add(Line(x, y - 16, x + 12, y - 32, strokeColor=INK))
    for i, part in enumerate(name.split('|')):
        d.add(String(x, y - 47 - i * 12, part, textAnchor='middle', fontName='BodyBold', fontSize=10))


def usecase_drawing(kind):
    d = Drawing(750, 435)
    d.add(Rect(115, 12, 515, 414, fillColor=colors.white, strokeColor=INK, strokeWidth=.9))
    d.add(String(130, 405, 'FaeHub+', fontName='BodyBold', fontSize=12))
    if kind == 'acesso':
        cases = [
            ('UC01', 'Entrar no campus'), ('UC02', 'Ativar por convite'),
            ('UC03', 'Recuperar acesso'), ('UC04', 'Usar autenticador'),
            ('UC14', 'Conversar'), ('UC15', 'Ler notificações'),
            ('UC38', 'Entrar na FaeNet'), ('UC39', 'Executar backup'),
        ]
        actors = [(48, 270, 'Titular', list(range(7))), (48, 90, 'Operador', [7]),
                  (700, 320, 'Gmail', [1, 2]), (700, 175, 'FaeNet', [6]), (700, 60, 'Drive', [7])]
    elif kind == 'academico':
        cases = [
            ('UC06', 'Consultar Boletim'), ('UC18', 'Lançar N1 e N2'),
            ('UC07', 'Consultar frequência'), ('UC19', 'Realizar chamada'),
            ('UC10', 'Entregar atividade'), ('UC20', 'Registrar Diário'),
            ('UC12', 'Solicitar documento'), ('UC21', 'Publicar e corrigir'),
        ]
        actors = [(48, 310, 'Aluno', [0, 2, 4, 6]), (700, 240, 'Professor', [1, 3, 5, 7]),
                  (48, 100, 'Responsável', [6])]
    else:
        cases = [
            ('UC25', 'Gerenciar contas'), ('UC26', 'Manter estrutura'),
            ('UC27', 'Manter matrículas'), ('UC28 UC29', 'Docentes e horários'),
            ('UC30', 'Atender documentos'), ('UC31 UC20', 'Acompanhar e validar'),
            ('UC32 UC33', 'Períodos e eventos'), ('UC34 UC35 UC36', 'Relatórios e consulta'),
        ]
        actors = [(48, 250, 'Direção', list(range(8))), (700, 150, 'Titular', [4])]
    centers = [(375, 370 - i * 46) for i in range(8)]
    # Association segments deliberately stop on ellipse boundaries.
    for ax, ay, name, indices in actors:
        for index in indices:
            cx, cy = centers[index]
            ex = cx - 170 if ax < cx else cx + 170
            line(d, [ax + (16 if ax < cx else -16), ay - 5, ex, cy])
    for i, ((code, title), (cx, cy)) in enumerate(zip(cases, centers)):
        d.add(Ellipse(cx, cy, 171, 20, fillColor=PALE, strokeColor=INK, strokeWidth=.8))
        d.add(String(cx, cy + 5, code, textAnchor='middle', fontName='BodyBold', fontSize=8.8))
        d.add(String(cx, cy - 9, title, textAnchor='middle', fontName='Body', fontSize=10))
    for ax, ay, name, indices in actors:
        actor(d, ax, ay, name)
    return d


DIAGRAMS = [
    ('casos-acesso', 'Casos de uso de acesso e serviços', 'use', 'acesso',
     'Titular representa os perfis com acesso permitido. Gmail participa de convite e recuperação; FaeNet é o aplicativo de destino; Drive é destino opcional da cópia criptografada. Backup é uma ferramenta operacional externa ao menu. As associações indicam participação, não sequência de execução.'),
    ('casos-academicos', 'Casos de uso acadêmicos', 'use', 'academico',
     'Aluno consulta seus registros e entrega atividades. Professor registra a aula, a presença, as notas e a correção. Responsável participa da solicitação para matrículas vinculadas e consulta resultados pelo seu portal, não pela edição de notas. Autenticação e vínculos válidos são pré-condições dos casos protegidos.'),
    ('casos-direcao', 'Casos de uso da gestão escolar', 'use', 'direcao',
     'A direção mantém cadastros e atende os fluxos institucionais. O titular acompanha o documento solicitado. Algumas elipses agrupam casos relacionados para manter a visão legível; os identificadores individuais constam do catálogo. Não há uma etapa de aprovação da direção na recuperação por e-mail.'),
    ('classes-estrutura', 'Classes do núcleo acadêmico', 'class', 'estrutura',
     'Modelo conceitual UML baseado em academic_core.py e database.py. A linha contínua representa associação; as multiplicidades aparecem entre as classes. As associações referem-se ao modelo de domínio, e não a herança entre papéis. Estudante e conta são distintos; uma matrícula ativa liga o estudante a uma turma.'),
    ('classes-academicas', 'Classes de aulas e resultados', 'class', 'academico',
     'Linha contínua: associação estrutural. Linha tracejada: relação lógica ou por código legado, sem afirmar uma chave estrangeira direta. A frequência atual relaciona Aula e Matricula. LancamentoNota representa o fluxo N1/N2 de grades; não deve ser confundido com assessments e assessment_scores, estruturas normalizadas presentes no projeto. /media é um valor derivado.'),
    ('classes-servicos', 'Classes de aprendizagem e serviços', 'class', 'servicos',
     'Recorte conceitual dos principais registros de database.py e p1_operations.py. Anexo é polimórfico: tipoEntidade e entidadeId identificam mensagem, atividade ou entrega; as linhas tracejadas não são FKs diretas. Usuario também aparece nos atributos de autoria, solicitação e destinatário. Os vínculos auxiliares e o controle de leitura são detalhados na página seguinte.'),
]


def feature(page, story, s, figures, markdown):
    story.extend([p(page['section'].upper(), s['Kicker']), heading(page['title'], page['id'], s)])
    meta = ' | '.join(str(page[k]) for k in ('role', 'path', 'uc') if page.get(k))
    if meta:
        story.append(p(meta, s['Meta']))
    markdown.extend(['## ' + page['title'], '', meta, ''])
    if page.get('intro'):
        story.append(p(page['intro'], s['BodyText']))
        markdown.extend([page['intro'], ''])
    if page.get('shot'):
        name = page['shot'] + '.jpg'
        path = SOURCE / 'capturas' / name
        if not path.is_file():
            raise ValueError(f'Missing observed screenshot: {path}')
        with PILImage.open(path) as im:
            iw, ih = im.size
        width = PW - MARGIN * 2
        height = width * ih / iw
        # A screenshot remains one complete, unmodified viewport with context.
        story.append(Image(str(path), width=width, height=height))
        number = len(figures) + 1
        caption = f'Figura {number} - {page["title"]}. Tela de demonstração; enquadramento do navegador.'
        story.append(p(caption, s['Caption']))
        figures.append((number, name, page['title']))
        markdown.extend([f'![Figura {number} - {page["title"]}](capturas/{name})', ''])
    if page.get('fields'):
        story.append(p('Campos e controles', s['Heading2']))
        story.append(p(page['fields'], s['Rule']))
        markdown.extend(['### Campos e controles', '', page['fields'], ''])
    for block in page.get('blocks', []):
        story.extend([p(block['title'], s['Heading2']), p(block['text'], s['BodyText'])])
        markdown.extend(['### ' + block['title'], '', block['text'], ''])
    if page.get('steps'):
        story.append(p('Como utilizar', s['Heading2']))
        markdown.extend(['### Como utilizar', ''])
        for i, text in enumerate(page['steps'], 1):
            story.append(p(f'{i}. {text}', s['Step']))
            markdown.append(f'{i}. {text}')
        markdown.append('')
    if page.get('kind') == 'roles':
        story.extend([Spacer(1, 4), table(ROLE_ROWS, [155, 77, 92, 100, 91.27], s)])
        markdown.extend(['| ' + ' | '.join(ROLE_ROWS[0]) + ' |', '| ' + ' | '.join(['---'] * 5) + ' |'])
        markdown.extend('| ' + ' | '.join(row) + ' |' for row in ROLE_ROWS[1:])
        markdown.append('')
    if page.get('kind') == 'troubleshooting':
        story.append(table(PROBLEM_ROWS, [130, PW - MARGIN * 2 - 130], s))
        markdown.extend(['| Situação | Conferência e encaminhamento |', '| --- | --- |'])
        markdown.extend('| ' + ' | '.join(row) + ' |' for row in PROBLEM_ROWS[1:])
        markdown.append('')
    if page.get('rules'):
        story.append(p('Regras e cuidados', s['Heading2']))
        markdown.extend(['### Regras e cuidados', ''])
        for text in page['rules']:
            story.append(p(text, s['Rule']))
            markdown.extend([text, ''])
    story.append(PageBreak())


def append_diagrams(story, s, markdown):
    out = SOURCE / 'diagramas'
    out.mkdir(parents=True, exist_ok=True)
    story.append(NextPageTemplate('landscape'))
    # The previous feature already ended the current page. This template switch
    # is applied by the following page transition to avoid a blank page.
    for i, (key, title, kind, variant, note) in enumerate(DIAGRAMS):
        if i == 0:
            story.append(PageBreak())
        story.append(p('MODELOS UML', s['Kicker']))
        story.append(heading(title, key, s))
        drawing = class_drawing(variant) if kind == 'class' else usecase_drawing(variant)
        # Keep diagrams vector-based in both the PDF and editable SVG exports.
        drawing.scale(.90, .90)
        drawing.width *= .90
        drawing.height *= .90
        drawing.hAlign = 'CENTER'
        story.append(drawing)
        story.append(p(note, s['Rule']))
        svg_path = out / (key + '.svg')
        renderSVG.drawToFile(drawing, str(svg_path))
        svg = svg_path.read_text(encoding='utf-8')
        svg = re.sub(r'<!DOCTYPE svg.*?>', '', svg, flags=re.S)
        svg = svg.replace('<title>...</title>', '<title>' + escape(title) + '</title>')
        svg = svg.replace('<desc>...</desc>', '<desc>' + escape(note) + '</desc>')
        svg = svg.replace('font-family: BodyBold;', 'font-family: Arial, Helvetica, sans-serif; font-weight: 700;')
        svg = svg.replace('font-family: BodyItalic;', 'font-family: Arial, Helvetica, sans-serif; font-style: italic;')
        svg = svg.replace('font-family: Body;', 'font-family: Arial, Helvetica, sans-serif;')
        svg_path.write_text(svg, encoding='utf-8')
        markdown.extend(['## ' + title, '', note, '', f'![{title}](diagramas/{key}.svg)', ''])
        if i == len(DIAGRAMS) - 1:
            story.append(NextPageTemplate('portrait'))
        story.append(PageBreak())


def append_model_notes(story, s, markdown):
    title = 'Correspondência entre classes e implementação'
    story.extend([p('MODELOS UML', s['Kicker']), heading(title, 'modelo-notas', s)])
    texts = [
        ('Representação do domínio', 'As classes dos desenhos descrevem conceitos e atributos persistidos. A implementação é predominantemente procedural: rotas Flask chamam funções que consultam tabelas e retornam dicionários. Portanto, os desenhos não são diagramas de herança de classes Python e não inventam métodos orientados a objetos.'),
        ('Cardinalidades e vínculo acadêmico', 'Um ano tem muitas turmas e períodos; um curso pode ter várias turmas. Turma e disciplina se relacionam por OfertaDisciplina. Um estudante pode acumular matrículas históricas, com apenas uma ativa. O professor é um Usuario com papel e vínculo de vigência, não uma subclasse Python de Estudante.'),
        ('Notas e frequência', 'O fluxo visível de N1/N2 usa grades com chave por registro do estudante e disciplina. As estruturas assessments e assessment_scores usam avaliação, período e matrícula no modelo normalizado, mas não equivalem automaticamente ao fluxo atual. attendance mantém a base diária anterior; lessons e attendance_records são a base da chamada por aula.'),
        ('Associações auxiliares', 'message_group_members vincula Usuario e GrupoMensagem; message_receipts registra entrega e leitura por mensagem e usuário; message_reactions registra reação por usuário. submission_reviews relaciona uma correção à entrega e preserva o texto da resposta corrigida. notification_reads e communication_states mantêm leitura por conta; leitura não é atributo global do conteúdo.'),
        ('Identidade e segurança', 'account_identities liga a conta ao e-mail confirmado. account_invitations registra o convite e seu estado. account_mfa e mfa_recovery_codes tratam segundo fator e códigos protegidos. faenet_subjects e faenet_grants sustentam a ponte de identidade. Estes registros não devem ser publicados em capturas ou exportações de documentação.'),
        ('Limites das associações lógicas', 'Documento e Intervencao utilizam identificação do estudante por texto; diário contém turma e disciplina por código; Anexo utiliza tipo e id de entidade. Uma linha tracejada indica essa relação lógica, sem alegar uma FK, composição, exclusão em cascata ou herança inexistente. O diagrama é um recorte dos registros principais, não um inventário de todas as tabelas técnicas.'),
    ]
    markdown.extend(['## ' + title, ''])
    for subtitle, text in texts:
        story.extend([p(subtitle, s['Heading2']), p(text, s['BodyText'])])
        markdown.extend(['### ' + subtitle, '', text, ''])
    story.append(PageBreak())


def append_catalog(pages, story, s, markdown):
    cases = {}
    for page in pages:
        if page.get('uc') and page['uc'] not in cases:
            cases[page['uc']] = page
    rows = [['Caso', 'Objetivo', 'Ator principal', 'Resultado esperado']]
    for code in sorted(cases):
        page = cases[code]
        result = {
            'UC01':'Sessão do perfil autorizado', 'UC02':'E-mail confirmado e conta ativada',
            'UC03':'Identificação enviada ou senha redefinida', 'UC04':'Segundo fator confirmado',
            'UC05':'Resumo da rotina acadêmica consultado',
            'UC06':'Notas por disciplina consultadas ou impressas',
            'UC07':'Chamadas e eventos do mês consultados',
            'UC08':'Aulas e lacunas da grade identificadas',
            'UC09':'Atividade e devolutiva localizadas',
            'UC10':'Resposta ou anexo salvo na atividade', 'UC18':'N1/N2 da linha persistidas',
            'UC11':'Leitura registrada para a conta',
            'UC12':'Protocolo registrado ou documento consultado',
            'UC13':'Condições e canal de inscrição consultados',
            'UC14':'Mensagem ou anexo registrado na conversa',
            'UC15':'Histórico consultado ou leitura registrada',
            'UC16':'Prioridades docentes consultadas',
            'UC17':'Lista da turma autorizada localizada',
            'UC19':'Presenças salvas para uma aula', 'UC20':'Registro pedagógico salvo ou validado',
            'UC21':'Atividade publicada ou entrega corrigida', 'UC25':'Conta ou convite gerenciado',
            'UC22':'Comunicado da turma publicado ou arquivado',
            'UC23':'Anúncio publicado para a turma',
            'UC24':'Indicadores e filas institucionais consultados',
            'UC26':'Cadastros ligados ao ciclo letivo',
            'UC27':'Matrícula criada ou encerrada com histórico',
            'UC28':'Vínculo e vigência registrados',
            'UC29':'Horário publicado sem sobreposição',
            'UC30':'Andamento do protocolo atualizado', 'UC32':'Estado do período e motivo registrados',
            'UC31':'Plano pedagógico registrado e acompanhado',
            'UC33':'Evento publicado para o público escolhido',
            'UC34':'CSV do recorte disponibilizado',
            'UC35':'Identidade institucional atualizada',
            'UC36':'Trajetória consultada por estudante',
            'UC37':'Dados do estudante vinculado consultados',
            'UC38':'Sessão social autorizada se a ponte estiver ativa', 'UC39':'Cópia protegida e evidência de verificação',
        }[code]
        rows.append([code, page['title'], page.get('role', ''), result])
    story.extend([p('ESPECIFICAÇÃO FUNCIONAL', s['Kicker']), heading('Catálogo de casos de uso', 'catalogo-uc', s)])
    story.append(p('Os identificadores acompanham as telas do manual. Consulta é um resultado válido; casos de alteração exigem confirmação do salvamento. A tabela não afirma que cada alternativa tenha sido executada neste ensaio.', s['BodyText']))
    story.append(table(rows, [43, 163, 135, PW - MARGIN * 2 - 341], s, padding=7))
    markdown.extend(['## Catálogo de casos de uso', '', '| Caso | Objetivo | Ator | Resultado |', '| --- | --- | --- | --- |'])
    markdown.extend('| ' + ' | '.join(row) + ' |' for row in rows[1:])
    markdown.append('')
    story.append(PageBreak())
    detailed = [
        ('UC10 Entregar atividade', 'Aluno autenticado, matriculado e autorizado à atividade ativa.',
         'Abrir a atividade; ler o enunciado; preencher resposta ou selecionar arquivo válido; enviar; conferir a entrega ao reabrir.',
         'Sem conteúdo, formato inválido ou excesso de tamanho: revisar o formulário. Prazo vencido: o sistema admite envio e informa que a aceitação depende do professor. Falha de rede: consultar antes de reenviar.',
         'Resposta e anexo ficam ligados à atividade e ao aluno; o envio não atribui nota automaticamente.'),
        ('UC19 Realizar chamada', 'Professor autenticado com vínculo vigente; turma e ano ativos; matrícula abrangendo a data e um único período aberto.',
         'Consultar turma e data; selecionar disciplina e início/fim; carregar se existente; marcar todos; salvar; recarregar a mesma aula.',
         'Futuro, sobreposição, intervalo inválido ou seleção incompleta: corrigir antes de salvar. Revisão desatualizada: recarregar. Aula de outro docente ou término incompatível: procurar o responsável, sem sobrescrever silenciosamente.',
         'Aula e presenças ficam registradas com revisão; aulas distintas no mesmo dia permanecem independentes.'),
        ('UC25 Gerenciar convites', 'Direção pessoal ativada, permissão adequada e transporte de e-mail configurado.',
         'Pesquisar a conta; preparar os dados corretos e o vínculo; enviar convite; titular abre o e-mail e ativa com senha pessoal.',
         'Demo ou identidade inicial não ativada: não convidar como direção confirmada. Falha de envio: cadastro preparado não equivale a convite entregue. Convite vencido ou revogado: emitir novo conforme o fluxo.',
         'Convite e conta mantêm estado verificável; senha continua privada do titular.'),
        ('UC30 Atender documento', 'Direção autenticada e pedido existente; solicitante com matrícula autorizada.',
         'Localizar protocolo; conferir a solicitação; atualizar situação e observação; salvar; abrir quando disponível; registrar entrega quando concluída.',
         'Dados divergentes: conferir com solicitante. Indeferimento: registrar observação. Sem autorização ou documento não disponível: não contornar o acesso com outro usuário.',
         'Andamento persiste por protocolo e o titular acompanha a atualização no seu contexto.'),
        ('UC38 Entrar na FaeNet', 'Conta ativa, ativada e elegível; configuração coordenada nos dois aplicativos e serviços disponíveis.',
         'Abrir FaeNet; autenticar pelo FaeHub; concluir MFA se ativo; na comunidade, personalizar perfil ou confirmar vínculo antigo; abrir destino permitido.',
         'Ponte não configurada: interface pode exibir acesso independente. Demo pública ou conta bloqueada: não libera identidade federada. Erro de vínculo: reabrir a entrada oficial; não mesclar por nome coincidente.',
         'FaeNet recebe identidade mínima autorizada, sem senha ou registros acadêmicos; permissões escolares não viram administração social.'),
    ]
    story.extend([p('ESPECIFICAÇÃO FUNCIONAL', s['Kicker']), heading('Fluxos e alternativas dos casos críticos', 'fluxos-uc', s)])
    markdown.extend(['## Fluxos e alternativas dos casos críticos', ''])
    for title, pre, flow, alt, post in detailed:
        content = [p(title, s['Heading2'])]
        markdown.extend(['### ' + title, ''])
        for label, text in [('Pré-condições', pre), ('Fluxo principal', flow), ('Alternativas', alt), ('Pós-condição', post)]:
            content.append(p(label + ': ' + text, s['Rule']))
            markdown.extend(['**' + label + '**: ' + text, ''])
        story.append(KeepTogether(content))
    story.append(PageBreak())


def append_sources(figures, story, s, markdown):
    story.extend([p('REFERÊNCIAS E EVIDÊNCIAS', s['Kicker']), heading('Fontes e cobertura da leitura', 'fontes', s)])
    texts = [
        'Navegação de referência: 55 enquadramentos de login, recuperação, ativação, quatro perfis, consultas, cadastros e formulários. Foram fotografadas telas e abertos detalhes sem modificar dados de produção. O inventário navegacao.json registra perfil, título e endereço observado; os arquivos de captura são os originais do navegador.',
        'Rotas e menus: app.py, templates/base.html e templates das áreas observadas. Núcleo acadêmico: academic_core.py e school_timetable.py. Registros compatíveis: database.py. Chamada: lesson_attendance.py. Estúdio docente: teacher_studio.py. Serviços escolares: p1_operations.py.',
        'Identidade e acesso: account_enrollment.py, account_recovery.py, account_mfa.py, profile_photos.py e faenet_sso.py. Rotina de backup: backup_service.py e tools/school_backup.py. Contratos complementares: docs/faenet-sso.md e docs/attendance-security-backup.md.',
        'Configuração do ensaio: banco descartável local, e-mail desabilitado e sem chave de MFA ou segredo de federação. Não houve confirmação de entrega Gmail, entrada social federada, tarefa diária, upload Drive ou restauração de produção nesta documentação. Esses fluxos são descritos com os requisitos do projeto, não certificados pela imagem da tela.',
        'O formulário de correção foi conferido no template e no fluxo implementado; a lista capturada estava sem entregas. QR, códigos de recuperação, senha nova e convites privados não foram fotografados. Estados não alcançados na navegação foram descritos pelas regras do código e não apresentados como operações executadas.',
        'Escopo visual: desktop no enquadramento padrão do navegador. O manual não inclui uma certificação de acessibilidade ou uma matriz de testes de dispositivos. As pranchas conceituais enviadas na conversa não foram usadas como substitutas das capturas reais.',
        'Manutenção: atualize conteudo.json, refaça capturas afetadas, execute tools/build_user_documentation.py no runtime de documentos e revise as páginas do PDF. Segredos, bancos, logs e os estados brutos de navegação não fazem parte do material a publicar.',
    ]
    for text in texts:
        story.append(p(text, s['BodyText']))
    story.append(p('Endereços de referência', s['Heading2']))
    for text in ['Aplicativo: https://faehub-plus.onrender.com/', 'Código: https://github.com/ThiagoZotti/faehub-plus', 'Comunidade: https://faenet.onrender.com/']:
        story.append(p(text, s['Rule']))
    markdown.extend(['## Fontes e cobertura da leitura', ''] + [t + '\n' for t in texts])
    story.append(PageBreak())
    story.extend([p('ÍNDICE VISUAL', s['Kicker']), heading('Índice de capturas do manual', 'figuras', s)])
    rows = [['Figura', 'Tela', 'Arquivo observado']]
    rows.extend([str(n), title, name] for n, name, title in figures)
    story.append(table(rows, [45, 255, PW - MARGIN * 2 - 300], s))
    markdown.extend(['## Índice de capturas do manual', '', '| Figura | Tela | Arquivo |', '| --- | --- | --- |'])
    markdown.extend('| ' + ' | '.join(row) + ' |' for row in rows[1:])


def build(output):
    fonts()
    s = styles()
    data = json.loads((SOURCE / 'conteudo.json').read_text(encoding='utf-8'))
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = Manual(str(output), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                 topMargin=42, bottomMargin=40, title=data['title'], author='Projeto FaeHub+',
                 subject='Funcionalidades, capturas, manual de usuário e modelos UML',
                 pageCompression=1)
    doc.addPageTemplates([
        PageTemplate(id='portrait', pagesize=A4, frames=[Frame(MARGIN, 40, PW-2*MARGIN, PH-82, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer),
        PageTemplate(id='landscape', pagesize=landscape(A4), frames=[Frame(MARGIN, 40, LW-2*MARGIN, LH-82, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)], onPage=footer),
    ])
    story = [Spacer(1, 65), p('DOCUMENTAÇÃO DO PROJETO', s['Kicker']), p('FaeHub', s['Title']),
             p('Documentação funcional e manual do usuário', s['Heading1']), Spacer(1, 15),
             p('Guia ilustrado para aluno, professor, direção e responsável', s['BodyText']),
             p(data['edition'], s['Meta']), Spacer(1, 20)]
    cover = SOURCE / 'capturas' / '28-diretor-painel.jpg'
    with PILImage.open(cover) as im:
        iw, ih = im.size
    story.append(Image(str(cover), width=PW-2*MARGIN, height=(PW-2*MARGIN)*ih/iw))
    story.extend([Spacer(1, 20), p('Funcionalidades e instruções de uso', s['Heading2']),
                  p('Capturas da aplicação, matriz de perfis, caminhos de operação, cuidados com dados e diagramas UML de classes e casos de uso.', s['BodyText']),
                  p('Referência local de demonstração. Integrações externas dependem de configuração e verificação operacional.', s['Meta']), PageBreak()])
    story.extend([heading('Sumário', 'sumario', s)])
    toc = TableOfContents()
    toc.levelStyles = [s['TOC0'], s['TOC1']]
    story.extend([toc, PageBreak()])
    markdown = ['# ' + data['title'], '', data['edition'], '',
                'Versão editável do manual ilustrado. Base do código: ' + data['baseline'] + '.', '']
    figures = []
    for page in data['pages']:
        feature(page, story, s, figures, markdown)
    # Replace the final normal break so the first UML page uses landscape.
    story.pop()
    append_diagrams(story, s, markdown)
    append_model_notes(story, s, markdown)
    append_catalog(data['pages'], story, s, markdown)
    append_sources(figures, story, s, markdown)
    doc.multiBuild(story)
    (SOURCE / 'manual.md').write_text('\n'.join(markdown) + '\n', encoding='utf-8')
    manifest = {
        'edition': '2026-10-22', 'baseline': data['baseline'],
        'pdf': str(output.relative_to(ROOT)).replace('\\', '/'),
        'pdf_sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'screenshots_in_manual': len(figures), 'captured_viewports': len(list((SOURCE/'capturas').glob('*.jpg'))),
        'use_cases': len({page['uc'] for page in data['pages'] if page.get('uc')}),
        'diagrams': len(DIAGRAMS),
        'assets': [{'file': name, 'sha256': hashlib.sha256((SOURCE/'capturas'/name).read_bytes()).hexdigest()} for _, name, _ in figures],
    }
    (SOURCE / 'manifesto.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in manifest.items() if k != 'assets'}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'output'/'pdf'/'FaeHub_documentacao_e_manual.pdf')
    args = parser.parse_args()
    build(args.output.resolve())
