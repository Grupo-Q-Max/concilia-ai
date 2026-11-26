
# CONCILIA_V5_PDF_LAYOUT_26C1

from decimal import Decimal
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    Paragraph,
    LongTable,
    TableStyle,
    Spacer,
)

NAVY = colors.HexColor("#17365D")
BLUE = colors.HexColor("#2563EB")
SLATE = colors.HexColor("#475569")
LIGHT = colors.HexColor("#F1F5F9")
BORDER = colors.HexColor("#CBD5E1")
GREEN = colors.HexColor("#166534")
RED = colors.HexColor("#991B1B")
AMBER = colors.HexColor("#92400E")

PAGE_SIZE = landscape(A4)
MARGIN = 32
CONTENT_WIDTH = PAGE_SIZE[0] - 2 * MARGIN - 12


def brl(value):

    if value is None or value == "":
        return "-"

    number = Decimal(str(value))

    if not number.is_finite():
        raise ValueError("Valor monetario invalido.")

    number = number.quantize(Decimal("0.01"))

    formatted = f"{abs(number):,.2f}"

    formatted = (
        formatted.replace(",", "#")
        .replace(".", ",")
        .replace("#", ".")
    )

    sign = "-" if number < 0 else ""

    return f"{sign}R$ {formatted}"


def percentage(value):

    if value is None or value == "":
        return "-"

    number = Decimal(str(value))

    if not number.is_finite():
        raise ValueError("Percentual invalido.")

    return f"{number:.2f}".replace(".", ",") + "%"


def safe_text(value):

    if value is None or value == "":
        return "-"

    if isinstance(value, bool):
        return "SIM" if value else "NAO"

    text = str(value)

    text = "".join(
        char if ord(char) >= 32 or char in "\n\t"
        else " "
        for char in text
    )

    return text


def date_br(value):

    if value is None or value == "":
        return "-"

    text = str(value)

    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).strftime("%d/%m/%Y")

    except ValueError:
        return text


def create_styles():

    return {

        "title": ParagraphStyle(
            "V5Title",
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=29,
            textColor=NAVY,
            spaceAfter=12,
        ),

        "subtitle": ParagraphStyle(
            "V5Subtitle",
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=SLATE,
            spaceAfter=8,
        ),

        "section": ParagraphStyle(
            "V5Section",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceBefore=10,
            spaceAfter=10,
            keepWithNext=True,
        ),

        "body": ParagraphStyle(
            "V5Body",
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=SLATE,
            spaceAfter=6,
        ),

        "header": ParagraphStyle(
            "V5Header",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_LEFT,
        ),

        "cell": ParagraphStyle(
            "V5Cell",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=NAVY,
            splitLongWords=True,
        ),

        "money": ParagraphStyle(
            "V5Money",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=NAVY,
            alignment=TA_RIGHT,
        ),

        "negative": ParagraphStyle(
            "V5Negative",
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=RED,
            alignment=TA_RIGHT,
        ),

        "success": ParagraphStyle(
            "V5Success",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=GREEN,
        ),

        "warning": ParagraphStyle(
            "V5Warning",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=AMBER,
        ),

        "danger": ParagraphStyle(
            "V5Danger",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=11,
            textColor=RED,
        ),
    }


def paragraph(value, style):

    text = escape(safe_text(value))

    text = text.replace("\n", "<br/>")

    return Paragraph(text, style)


def status_style(value):

    status = str(value).strip().upper()

    if status in {
        "VALIDADO",
        "QUITADO",
        "CONCILIADO",
        "CONFIRMED",
    }:
        return "success"

    if status in {
        "PARCIAL",
        "PARTIAL",
        "PENDENTE DE APROVACAO",
        "NAO COMPROVADO",
        "NAO ANEXADO",
        "EM_ABERTO",
    }:
        return "warning"

    if status in {
        "DIVERGENTE",
        "DIVERGENCIA_NF",
        "REVISAR",
        "SEM_PROVISAO",
        "BAIXA_EVIDENCIA",
    }:
        return "danger"

    return "cell"


def format_cell(value, kind, styles):

    if kind == "money":

        text = brl(value)

        style = (
            "negative"
            if text.startswith("-R$")
            else "money"
        )

        return paragraph(text, styles[style])

    if kind == "percentage":

        return paragraph(
            percentage(value),
            styles["money"]
        )

    if kind == "date":

        return paragraph(
            date_br(value),
            styles["cell"]
        )

    if kind == "status":

        return paragraph(
            value,
            styles[status_style(value)]
        )

    return paragraph(value, styles["cell"])


def build_table(records, columns, styles=None):

    styles = styles or create_styles()

    records = list(records)

    if not records:

        return paragraph(
            "Nenhum registro nesta secao.",
            styles["body"]
        )

    if not columns:
        raise ValueError("Tabela sem colunas.")

    weights = [float(c[2]) for c in columns]

    if any(weight <= 0 for weight in weights):
        raise ValueError("Largura de coluna invalida.")

    total_weight = sum(weights)

    widths = [
        CONTENT_WIDTH * weight / total_weight
        for weight in weights
    ]

    data = [[
        paragraph(c[1], styles["header"])
        for c in columns
    ]]

    for record in records:

        row = []

        for key, label, weight, kind in columns:

            row.append(
                format_cell(
                    record.get(key),
                    kind,
                    styles
                )
            )

        data.append(row)

    table = LongTable(
        data,
        colWidths=widths,
        repeatRows=1,
        splitByRow=1,
        splitInRow=1,
        hAlign="LEFT",
    )

    table.setStyle(TableStyle([

        ("BACKGROUND", (0, 0), (-1, 0), NAVY),

        ("ROWBACKGROUNDS",
            (0, 1), (-1, -1),
            [colors.white, LIGHT]),

        ("VALIGN",
            (0, 0), (-1, -1), "TOP"),

        ("LINEBELOW",
            (0, 0), (-1, 0), 1, BLUE),

        ("LINEBELOW",
            (0, 1), (-1, -1), 0.25, BORDER),

        ("LEFTPADDING",
            (0, 0), (-1, -1), 6),

        ("RIGHTPADDING",
            (0, 0), (-1, -1), 6),

        ("TOPPADDING",
            (0, 0), (-1, -1), 6),

        ("BOTTOMPADDING",
            (0, 0), (-1, -1), 6),

    ]))

    return table


def section_heading(number, title, styles):

    return paragraph(
        f"{number:02d}. {title}",
        styles["section"]
    )


def draw_page(canvas, document):

    width, height = PAGE_SIZE

    canvas.saveState()

    canvas.setFillColor(NAVY)

    canvas.rect(
        0,
        height - 32,
        width,
        32,
        fill=1,
        stroke=0
    )

    canvas.setFillColor(colors.white)

    canvas.setFont("Helvetica-Bold", 10)

    canvas.drawString(
        MARGIN,
        height - 20,
        "CONCILIA AI V5 INTELLIGENT"
    )

    canvas.setFont("Helvetica", 8)

    canvas.drawRightString(
        width - MARGIN,
        height - 20,
        "RELATORIO DE CONCILIACAO CONTABIL"
    )

    canvas.setStrokeColor(BORDER)

    canvas.line(
        MARGIN,
        32,
        width - MARGIN,
        32
    )

    canvas.setFillColor(SLATE)

    canvas.setFont("Helvetica", 8)

    canvas.drawString(
        MARGIN,
        19,
        "Documento de uso contabil - Valores em reais (BRL)"
    )

    canvas.drawRightString(
        width - MARGIN,
        19,
        f"Pagina {document.page}"
    )

    canvas.restoreState()
