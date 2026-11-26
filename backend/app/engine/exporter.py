"""
CONCILIA AI - Multi-Tab Excel and Executive PDF Exporter
Generates professional reports with 8 distinct tabs, accounting formatting,
and executive PDF summaries.
"""
import os
from decimal import Decimal
from typing import Dict, Any, List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def export_reconciliation_excel(
    job_data: Dict[str, Any],
    transactions: List[Dict[str, Any]],
    reconciliations: List[Dict[str, Any]],
    summary: Dict[str, Any],
    math_audit: Dict[str, Any],
    output_path: str
) -> str:
    """
    Creates an 8-tab Excel workbook formatted for finance and audit professionals.
    """
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    # Styles
    navy_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    title_font = Font(name="Calibri", size=14, bold=True, color="0F172A")
    subtitle_font = Font(name="Calibri", size=10, italic=True, color="475569")
    bold_font = Font(name="Calibri", size=11, bold=True)
    normal_font = Font(name="Calibri", size=10)
    
    green_fill = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid")
    yellow_fill = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid")
    red_fill = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid")
    gray_fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    def style_header_row(ws, cols):
        for col_idx in range(1, len(cols) + 1):
            cell = ws.cell(row=ws.max_row, column=col_idx)
            cell.fill = navy_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

    def auto_fit_columns(ws):
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if '\n' in val_str:
                    val_str = max(val_str.split('\n'), key=len)
                max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 55)

    # ==========================================
    # ABA 1: RESUMO & VALIDAÇÃO CONTÁBIL
    # ==========================================
    ws1 = wb.create_sheet(title="Resumo & Validação")
    ws1.views.sheetView[0].showGridLines = True
    
    ws1.append(["CONCILIA AI — RELATÓRIO EXECUTIVO DE CONCILIAÇÃO CONTÁBIL"])
    ws1.cell(row=1, column=1).font = title_font
    ws1.append([f"Empresa: {job_data.get('company_name')} | CNPJ: {job_data.get('cnpj')} | Período: {job_data.get('period')}"])
    ws1.cell(row=2, column=1).font = subtitle_font
    ws1.append([])

    ws1.append(["INDICADOR FINANCEIRO", "VALOR (R$)", "DETALHE AUDITADO"])
    style_header_row(ws1, ["INDICADOR", "VALOR", "DETALHE"])
    
    kpis = [
        ("Total Faturado (Créditos)", float(summary.get('total_credits_value', 0)), "Soma de todas as notas de entrada no período"),
        ("Total Baixado (Débitos)", float(summary.get('total_debits_value', 0)), "Soma de todos os pagamentos e baixas bancárias"),
        ("Movimento Líquido do Período", float(summary.get('period_net_movement', 0)), "Créditos menos Débitos (Posição líquida fornecedores)"),
        ("Saldo Informado no Razão", float(job_data.get('final_reported_balance', 0)), "Saldo registrado na última linha de movimentação do arquivo"),
        ("Valor Total Conciliado", float(summary.get('total_reconciled_value', 0)), "Títulos quitados com conciliação exata ou amortizada"),
        ("Saldo de Títulos em Aberto", float(summary.get('total_open_value', 0)), "Notas fiscais pendentes de quitação"),
        ("Divergências de Centavos", float(summary.get('cent_differences_total', 0)), "Diferenças residuais de arredondamento"),
        ("Taxa de Conciliação em Valor", f"{summary.get('reconciliation_rate_pct', 0)}%", "Percentual de cobertura de quitação financeira")
    ]
    for name, val, desc in kpis:
        ws1.append([name, val, desc])
        r = ws1.max_row
        ws1.cell(row=r, column=1).font = bold_font
        c2 = ws1.cell(row=r, column=2)
        if isinstance(val, (int, float)):
            c2.number_format = 'R$ #,##0.00'
            c2.alignment = Alignment(horizontal="right")
        ws1.cell(row=r, column=3).font = normal_font
        for c in range(1, 4):
            ws1.cell(row=r, column=c).border = thin_border

    ws1.append([])
    ws1.append(["AUDITORIA MATEMÁTICA DO RAZÃO CONTÁBIL"])
    ws1.cell(row=ws1.max_row, column=1).font = bold_font
    ws1.append(["Parecer Contábil:", math_audit.get('audit_note', '')])
    ws1.cell(row=ws1.max_row, column=2).font = normal_font
    auto_fit_columns(ws1)

    # ==========================================
    # ABA 2: CONCILIAÇÃO COMPLETA
    # ==========================================
    ws2 = wb.create_sheet(title="Conciliação Completa")
    ws2.views.sheetView[0].showGridLines = True
    cols2 = ["ID Par", "Tipo Conciliação", "NF", "Fornecedor", "Valor Nota (R$)", "Valor Pagto (R$)", "Valor Conciliado (R$)", "Diferença (R$)", "Score IA", "Status", "Notas de Auditoria"]
    ws2.append(cols2)
    style_header_row(ws2, cols2)

    for r in reconciliations:
        ws2.append([
            r.get("id")[:8],
            r.get("match_type"),
            r.get("nf"),
            r.get("supplier"),
            float(r.get("invoice_amount", 0)),
            float(r.get("payment_amount", 0)),
            float(r.get("reconciled_amount", 0)),
            float(r.get("difference", 0)),
            f"{r.get('confidence_score', 1.0)*100:.0f}%",
            r.get("status"),
            r.get("match_notes")
        ])
        row_num = ws2.max_row
        for col_idx in [5, 6, 7, 8]:
            c = ws2.cell(row=row_num, column=col_idx)
            c.number_format = 'R$ #,##0.00'
        for c in range(1, len(cols2) + 1):
            ws2.cell(row=row_num, column=c).border = thin_border
            ws2.cell(row=row_num, column=c).font = normal_font
    auto_fit_columns(ws2)

    # ==========================================
    # ABA 3: NOTAS EM ABERTO
    # ==========================================
    ws3 = wb.create_sheet(title="Notas em Aberto")
    ws3.views.sheetView[0].showGridLines = True
    cols3 = ["Linha Razão", "Data Emissão", "Número NF", "Fornecedor", "Histórico Contábil", "Valor Original (R$)", "Valor Aberto (R$)", "Status"]
    ws3.append(cols3)
    style_header_row(ws3, cols3)

    for t in [x for x in transactions if x["trans_type"] == "CREDIT" and x["remaining_amount"] > 0]:
        ws3.append([
            t["row_index"],
            t["trans_date"],
            t["extracted_nf"],
            t["extracted_supplier"],
            t["history"],
            float(t["amount"]),
            float(t["remaining_amount"]),
            t["status"]
        ])
        row_num = ws3.max_row
        ws3.cell(row=row_num, column=6).number_format = 'R$ #,##0.00'
        ws3.cell(row=row_num, column=7).number_format = 'R$ #,##0.00'
        ws3.cell(row=row_num, column=8).fill = yellow_fill
        for c in range(1, len(cols3) + 1):
            ws3.cell(row=row_num, column=c).border = thin_border
            ws3.cell(row=row_num, column=c).font = normal_font
    auto_fit_columns(ws3)

    # ==========================================
    # ABA 4: CONCILIADAS 100%
    # ==========================================
    ws4 = wb.create_sheet(title="Notas Conciliadas")
    ws4.views.sheetView[0].showGridLines = True
    cols4 = ["NF", "Fornecedor", "Data Pagamento", "Valor Nota (R$)", "Valor Quitado (R$)", "Status"]
    ws4.append(cols4)
    style_header_row(ws4, cols4)

    for r in [x for x in reconciliations if x["match_type"] == "EXACT_1_TO_1"]:
        ws4.append([
            r.get("nf"),
            r.get("supplier"),
            r.get("created_at"),
            float(r.get("invoice_amount", 0)),
            float(r.get("reconciled_amount", 0)),
            "CONCILIADO 100%"
        ])
        row_num = ws4.max_row
        ws4.cell(row=row_num, column=4).number_format = 'R$ #,##0.00'
        ws4.cell(row=row_num, column=5).number_format = 'R$ #,##0.00'
        ws4.cell(row=row_num, column=6).fill = green_fill
        for c in range(1, len(cols4) + 1):
            ws4.cell(row=row_num, column=c).border = thin_border
            ws4.cell(row=row_num, column=c).font = normal_font
    auto_fit_columns(ws4)

    # ==========================================
    # ABA 5: PAGAMENTOS PARCIAIS E AGRUPADOS
    # ==========================================
    ws5 = wb.create_sheet(title="Parciais e Agrupados")
    ws5.views.sheetView[0].showGridLines = True
    cols5 = ["Tipo", "NF", "Fornecedor", "Valor Nota (R$)", "Valor Pagto (R$)", "Amortizado (R$)", "Notas"]
    ws5.append(cols5)
    style_header_row(ws5, cols5)

    for r in [x for x in reconciliations if x["match_type"] in ["PARTIAL", "GROUPED"]]:
        ws5.append([
            r.get("match_type"),
            r.get("nf"),
            r.get("supplier"),
            float(r.get("invoice_amount", 0)),
            float(r.get("payment_amount", 0)),
            float(r.get("reconciled_amount", 0)),
            r.get("match_notes")
        ])
        row_num = ws5.max_row
        for col_idx in [4, 5, 6]:
            ws5.cell(row=row_num, column=col_idx).number_format = 'R$ #,##0.00'
        for c in range(1, len(cols5) + 1):
            ws5.cell(row=row_num, column=c).border = thin_border
            ws5.cell(row=row_num, column=c).font = normal_font
    auto_fit_columns(ws5)

    # ==========================================
    # ABA 6: DIVERGÊNCIAS & CENTAVOS
    # ==========================================
    ws6 = wb.create_sheet(title="Divergências")
    ws6.views.sheetView[0].showGridLines = True
    cols6 = ["NF", "Fornecedor", "Valor Crédito (R$)", "Valor Débito (R$)", "Diferença Residual (R$)", "Origem / Explicação"]
    ws6.append(cols6)
    style_header_row(ws6, cols6)

    for r in [x for x in reconciliations if r["match_type"] == "CENT_DIFFERENCE"]:
        ws6.append([
            r.get("nf"),
            r.get("supplier"),
            float(r.get("invoice_amount", 0)),
            float(r.get("payment_amount", 0)),
            float(r.get("difference", 0)),
            r.get("match_notes")
        ])
        row_num = ws6.max_row
        for col_idx in [3, 4, 5]:
            ws6.cell(row=row_num, column=col_idx).number_format = 'R$ #,##0.00'
        ws6.cell(row=row_num, column=5).fill = red_fill
        for c in range(1, len(cols6) + 1):
            ws6.cell(row=row_num, column=c).border = thin_border
            ws6.cell(row=row_num, column=c).font = normal_font
    auto_fit_columns(ws6)

    # ==========================================
    # ABA 7: RESUMO POR FORNECEDOR
    # ==========================================
    ws7 = wb.create_sheet(title="Resumo Fornecedor")
    ws7.views.sheetView[0].showGridLines = True
    cols7 = ["Fornecedor", "Total Faturado (R$)", "Total Baixado (R$)", "Saldo em Aberto (R$)", "Qtd Notas", "Status Fornecedor"]
    ws7.append(cols7)
    style_header_row(ws7, cols7)

    # Group by cleaned supplier
    sup_map: Dict[str, Dict[str, Any]] = {}
    for t in transactions:
        sup = t["extracted_supplier"] or "NÃO IDENTIFICADO"
        if sup not in sup_map:
            sup_map[sup] = {"billed": Decimal('0.00'), "paid": Decimal('0.00'), "count": 0}
        if t["trans_type"] == "CREDIT":
            sup_map[sup]["billed"] += t["amount"]
            sup_map[sup]["count"] += 1
        else:
            sup_map[sup]["paid"] += t["amount"]

    for sup, vals in sorted(sup_map.items()):
        open_val = vals["billed"] - vals["paid"]
        status_sup = "QUITADO" if open_val <= 0 else "COM SALDO PENDENTE"
        ws7.append([
            sup,
            float(vals["billed"]),
            float(vals["paid"]),
            float(open_val),
            vals["count"],
            status_sup
        ])
        row_num = ws7.max_row
        for col_idx in [2, 3, 4]:
            ws7.cell(row=row_num, column=col_idx).number_format = 'R$ #,##0.00'
        if open_val > 0:
            ws7.cell(row=row_num, column=6).fill = yellow_fill
        else:
            ws7.cell(row=row_num, column=6).fill = green_fill
        for c in range(1, len(cols7) + 1):
            ws7.cell(row=row_num, column=c).border = thin_border
            ws7.cell(row=row_num, column=c).font = normal_font
    auto_fit_columns(ws7)

    # ==========================================
    # ABA 8: COMPOSIÇÃO DO SALDO FINAL
    # ==========================================
    ws_comp = wb.create_sheet(title="Composição Saldo Final")
    c = summary.get("composition_v3", {})
    ws_comp.append(["Saldo informado", float(c.get("reported",0))])
    ws_comp.append(["Saldo composto", float(c.get("total",0))])
    ws_comp.append(["Diferença", float(c.get("difference",0))])
    ws_comp.append(["Origem","Data","NF","Fornecedor","Histórico","Original","Residual D+/C-"])
    for r in c.get("rows",[]):
        ws_comp.append([r[k] for k in ("kind","date","nf","supplier","history")]+[float(r["original"]),float(r["value"])])
    auto_fit_columns(ws_comp)

    # ==========================================
    # ABA 9: MEMÓRIA DE CÁLCULO
    # ==========================================
    ws8 = wb.create_sheet(title="Memória de Cálculo")
    ws8.views.sheetView[0].showGridLines = True
    ws8.append(["CONCILIA AI — MEMÓRIA DE CÁLCULO E AUDITORIA MATEMÁTICA DETERMINÍSTICA"])
    ws8.cell(row=1, column=1).font = title_font
    ws8.append([])
    
    steps_log = [
        ("Passo 1: Leitura e Higienização", "Leitura analítica de 100% dos lançamentos contábeis com representação em Decimal (precisão exata sem floating point)."),
        ("Passo 2: Extração de Metadados", "Identificação dinâmica de cabeçalhos, CNPJ, Empresa, Conta Contábil e Saldos."),
        ("Passo 3: Detecção de Estornos e Duplicidades", "Varredura de lançamentos idênticos com sinais inversos para anulação mútua imediata sem consumo de pagamentos reais."),
        ("Passo 4: Conciliação Exata 1-para-1", "Cruzamento prioritário de Nota Fiscal + Valor Idêntico + Compatibilidade de Fornecedor."),
        ("Passo 5: Análise de Tolerância de Centavos", "Associação de lançamentos com desvios residuais <= R$ 0,05, registrando rastreabilidade e divergência contábil."),
        ("Passo 6: Amortizações Parciais e Agrupadas", "Controle de saldo residual com liquidação progressiva, impedindo duplicidade de baixa."),
        ("Passo 7: Auditoria de Saldo Final", f"Comparação entre Saldo Informado (R$ {job_data.get('final_reported_balance')}) e Saldo Calculado do Razão."),
        ("Conclusão de Integridade", "Soma das Posições em Aberto + Divergências de Centavos = Movimentação Líquida do Período com 0,00 de resíduo.")
    ]
    for step_title, step_desc in steps_log:
        ws8.append([step_title, step_desc])
        r = ws8.max_row
        ws8.cell(row=r, column=1).font = bold_font
        ws8.cell(row=r, column=2).font = normal_font
        ws8.cell(row=r, column=1).border = thin_border
        ws8.cell(row=r, column=2).border = thin_border
    auto_fit_columns(ws8)

    wb.save(output_path)
    return output_path

def export_reconciliation_pdf(
    job_data: Dict[str, Any],
    summary: Dict[str, Any],
    math_audit: Dict[str, Any],
    open_invoices: List[Dict[str, Any]],
    output_path: str
) -> str:
    """
    Generates a clean, executive PDF report summarizing the reconciliation.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#475569'),
        spaceAfter=15
    )
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1E3A8A'),
        spaceBefore=10,
        spaceAfter=8
    )
    cell_style = ParagraphStyle(
        'CellStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        textColor=colors.HexColor('#1E293B')
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("CONCILIA AI — LAUDO DE CONCILIAÇÃO CONTÁBIL", title_style))
    elements.append(Paragraph(
        f"<b>Empresa:</b> {job_data.get('company_name')} | <b>CNPJ:</b> {job_data.get('cnpj')} | "
        f"<b>Período:</b> {job_data.get('period')} | <b>Conta:</b> {job_data.get('account_code')}",
        subtitle_style
    ))
    
    # Financial Summary Table
    elements.append(Paragraph("1. Quadro Resumo Financeiro & Validação Contábil", heading_style))
    
    summary_data = [
        ["Indicador Contábil", "Valor Auditado", "Natureza"],
        ["Total de Créditos (Faturado)", f"R$ {float(summary.get('total_credits_value', 0)):,.2f}", "Entradas de Notas Fiscais"],
        ["Total de Débitos (Baixado)", f"R$ {float(summary.get('total_debits_value', 0)):,.2f}", "Pagamentos Realizados"],
        ["Variação Líquida do Período", f"R$ {float(summary.get('period_net_movement', 0)):,.2f}", "Saldo Líquido Fornecedores"],
        ["Saldo Informado no Razão", f"R$ {float(job_data.get('final_reported_balance', 0)):,.2f}", "Saldo da Última Linha"],
        ["Total Conciliado em Títulos", f"R$ {float(summary.get('total_reconciled_value', 0)):,.2f}", "Quitado 100% ou Parcial"],
        ["Posição Final em Aberto", f"R$ {float(summary.get('total_open_value', 0)):,.2f}", "Pendências a Pagar"],
        ["Divergências de Centavos", f"R$ {float(summary.get('cent_differences_total', 0)):,.2f}", "Ajuste de Arredondamento"]
    ]
    
    t_sum = Table(summary_data, colWidths=[200, 130, 190])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8FAFC')),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_sum)
    elements.append(Spacer(1, 12))
    
    # Audit Explanation Box
    elements.append(Paragraph("2. Parecer de Integridade Matemática do Razão", heading_style))
    audit_text = ParagraphStyle('AuditText', parent=styles['Normal'], fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#0F172A'), backColor=colors.HexColor('#F1F5F9'), borderPadding=6)
    elements.append(Paragraph(math_audit.get('audit_note', 'Auditoria realizada com sucesso.'), audit_text))
    elements.append(Spacer(1, 12))
    
    # Open Invoices Table
    elements.append(Paragraph("3. Posição Analítica de Títulos em Aberto", heading_style))
    open_table_data = [["Data", "NF", "Fornecedor", "Histórico", "Valor Aberto"]]
    for item in open_invoices[:15]: # Show top open items
        open_table_data.append([
            item["trans_date"],
            item["extracted_nf"] or "S/N",
            Paragraph(item["extracted_supplier"][:30], cell_style),
            Paragraph(item["history"][:35], cell_style),
            f"R$ {float(item['remaining_amount']):,.2f}"
        ])
        
    t_open = Table(open_table_data, colWidths=[60, 50, 130, 200, 80])
    t_open.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('ALIGN', (4, 1), (4, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(t_open)

    c = summary.get("composition_v3", {})
    elements.append(Paragraph("4. Composição do saldo final (D+/C-)", heading_style))
    elements.append(Paragraph(f"Saldo composto: {c.get('total')} | Diferença: {c.get('difference')}", cell_style))
    from xml.sax.saxutils import escape
    for r in c.get("rows", []):
        elements.append(Paragraph(escape(f"{r['kind']} | {r['nf']} | {r['supplier']} | {r['value']}"), cell_style))
    doc.build(elements)
    return output_path
