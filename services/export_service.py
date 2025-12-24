import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


class ExportService:
    """Gestisce l'export di transazioni in PDF e Excel"""

    def __init__(self):
        self.exports_dir = "exports"
        if not os.path.exists(self.exports_dir):
            os.makedirs(self.exports_dir)

    def export_to_pdf(self, transactions, property_name=None, start_date=None, end_date=None):
        """Esporta transazioni in PDF"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transazioni_{timestamp}.pdf"
        filepath = os.path.join(self.exports_dir, filename)

        # Crea documento PDF in landscape per più spazio
        doc = SimpleDocTemplate(
            filepath,
            pagesize=landscape(A4),
            rightMargin=1.5 * cm,
            leftMargin=1.5 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm
        )

        # Elementi del documento
        elements = []
        styles = getSampleStyleSheet()

        # Stile personalizzato per il titolo
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1e7be7'),
            spaceAfter=20,
            alignment=TA_CENTER
        )

        # Titolo
        title = Paragraph("📊 Report Transazioni", title_style)
        elements.append(title)

        # Info periodo
        info_style = ParagraphStyle(
            'Info',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#666666'),
            alignment=TA_CENTER
        )

        info_text = f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        if property_name:
            info_text += f" | Proprietà: {property_name}"
        if start_date and end_date:
            info_text += f" | Periodo: {start_date} - {end_date}"

        elements.append(Paragraph(info_text, info_style))
        elements.append(Spacer(1, 0.5 * cm))

        # Calcola totali
        totale_entrate = sum(t['amount'] for t in transactions if t['type'] == 'Entrata')
        totale_uscite = sum(t['amount'] for t in transactions if t['type'] == 'Uscita')
        saldo = totale_entrate - totale_uscite

        # Box riepilogo
        summary_data = [
            ['Totale Entrate', 'Totale Uscite', 'Saldo Netto'],
            [f'€ {totale_entrate:,.2f}', f'€ {totale_uscite:,.2f}', f'€ {saldo:,.2f}']
        ]

        summary_table = Table(summary_data, colWidths=[6 * cm, 6 * cm, 6 * cm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (0, 1), colors.HexColor('#d4edda')),
            ('BACKGROUND', (1, 1), (1, 1), colors.HexColor('#f8d7da')),
            ('BACKGROUND', (2, 1), (2, 1), colors.HexColor('#d1ecf1') if saldo >= 0 else colors.HexColor('#f8d7da')),
            ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#333333')),
            ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, 1), 14),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('TOPPADDING', (0, 1), (-1, 1), 10),
            ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.8 * cm))

        # Ordina transazioni per data (più recenti prima)
        sorted_transactions = sorted(transactions, key=lambda x: x['date'], reverse=True)

        # Tabella transazioni
        table_data = [['Data', 'Tipo', 'Categoria', 'Fornitore', 'Importo']]

        for trans in sorted_transactions:
            table_data.append([
                trans['date'],
                trans['type'],
                trans.get('service', 'N/A'),
                trans.get('provider', 'N/A'),
                f"€ {trans['amount']:,.2f}"
            ])

        # Crea tabella
        transactions_table = Table(table_data, colWidths=[3 * cm, 3 * cm, 5 * cm, 6 * cm, 3.5 * cm])

        # Stile tabella
        table_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 0), (4, -1), 'RIGHT'),  # Importo allineato a destra
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ]

        # Colora righe in base al tipo
        for i, trans in enumerate(sorted_transactions, start=1):
            if trans['type'] == 'Entrata':
                table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#2ecc71')))
            else:
                table_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#e74c3c')))

        transactions_table.setStyle(TableStyle(table_style))
        elements.append(transactions_table)

        # Costruisci PDF
        doc.build(elements)
        return filepath

    def export_to_excel(self, transactions, property_name=None, start_date=None, end_date=None):
        """Esporta transazioni in Excel con formattazione"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transazioni_{timestamp}.xlsx"
        filepath = os.path.join(self.exports_dir, filename)

        wb = Workbook()

        # Rimuovi il foglio default
        wb.remove(wb.active)

        # === FOGLIO 1: RIEPILOGO ===
        ws_summary = wb.create_sheet("Riepilogo")

        # Stili
        title_font = Font(name='Arial', size=16, bold=True, color='1E7BE7')
        header_font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
        header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
        border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )

        # Titolo
        ws_summary['A1'] = '📊 Report Transazioni'
        ws_summary['A1'].font = title_font
        ws_summary.merge_cells('A1:E1')

        # Info
        ws_summary['A3'] = f"Generato il: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        if property_name:
            ws_summary['A4'] = f"Proprietà: {property_name}"
        if start_date and end_date:
            ws_summary['A5'] = f"Periodo: {start_date} - {end_date}"

        # Calcola totali
        totale_entrate = sum(t['amount'] for t in transactions if t['type'] == 'Entrata')
        totale_uscite = sum(t['amount'] for t in transactions if t['type'] == 'Uscita')
        saldo = totale_entrate - totale_uscite

        # Tabella riepilogo
        row = 7
        ws_summary[f'A{row}'] = 'Tipo'
        ws_summary[f'B{row}'] = 'Importo'
        for cell in [ws_summary[f'A{row}'], ws_summary[f'B{row}']]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        row += 1
        ws_summary[f'A{row}'] = 'Totale Entrate'
        ws_summary[f'B{row}'] = totale_entrate
        ws_summary[f'B{row}'].number_format = '€#,##0.00'
        ws_summary[f'B{row}'].fill = PatternFill(start_color='D4EDDA', end_color='D4EDDA', fill_type='solid')

        row += 1
        ws_summary[f'A{row}'] = 'Totale Uscite'
        ws_summary[f'B{row}'] = totale_uscite
        ws_summary[f'B{row}'].number_format = '€#,##0.00'
        ws_summary[f'B{row}'].fill = PatternFill(start_color='F8D7DA', end_color='F8D7DA', fill_type='solid')

        row += 1
        ws_summary[f'A{row}'] = 'Saldo Netto'
        ws_summary[f'B{row}'] = saldo
        ws_summary[f'B{row}'].number_format = '€#,##0.00'
        ws_summary[f'B{row}'].font = Font(bold=True)
        saldo_color = 'D1ECF1' if saldo >= 0 else 'F8D7DA'
        ws_summary[f'B{row}'].fill = PatternFill(start_color=saldo_color, end_color=saldo_color, fill_type='solid')

        # Bordi
        for r in range(7, row + 1):
            for c in ['A', 'B']:
                ws_summary[f'{c}{r}'].border = border

        # Larghezza colonne
        ws_summary.column_dimensions['A'].width = 20
        ws_summary.column_dimensions['B'].width = 18

        # === FOGLIO 2: TRANSAZIONI ===
        ws_trans = wb.create_sheet("Transazioni")

        # Header
        headers = ['Data', 'Tipo', 'Categoria', 'Fornitore', 'Importo']
        for col, header in enumerate(headers, start=1):
            cell = ws_trans.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal='center')
            cell.border = border

        # Dati - Ordina per data (più recenti prima)
        sorted_transactions = sorted(transactions, key=lambda x: x['date'], reverse=True)

        for row_idx, trans in enumerate(sorted_transactions, start=2):
            # Data
            ws_trans.cell(row=row_idx, column=1, value=trans['date'])

            # Tipo
            tipo_cell = ws_trans.cell(row=row_idx, column=2, value=trans['type'])
            if trans['type'] == 'Entrata':
                tipo_cell.font = Font(color='2ECC71', bold=True)
            else:
                tipo_cell.font = Font(color='E74C3C', bold=True)

            # Categoria
            ws_trans.cell(row=row_idx, column=3, value=trans.get('service', 'N/A'))

            # Fornitore
            ws_trans.cell(row=row_idx, column=4, value=trans.get('provider', 'N/A'))

            # Importo
            amount_cell = ws_trans.cell(row=row_idx, column=5, value=trans['amount'])
            amount_cell.number_format = '€#,##0.00'
            if trans['type'] == 'Entrata':
                amount_cell.font = Font(color='2ECC71', bold=True)
            else:
                amount_cell.font = Font(color='E74C3C', bold=True)

            # Bordi e colore alternato
            bg_color = 'FFFFFF' if row_idx % 2 == 0 else 'F8F9FA'
            for col in range(1, 6):
                cell = ws_trans.cell(row=row_idx, column=col)
                cell.border = border
                cell.fill = PatternFill(start_color=bg_color, end_color=bg_color, fill_type='solid')
                cell.alignment = Alignment(horizontal='left' if col < 5 else 'right')

        # Larghezza colonne
        ws_trans.column_dimensions['A'].width = 12
        ws_trans.column_dimensions['B'].width = 12
        ws_trans.column_dimensions['C'].width = 25
        ws_trans.column_dimensions['D'].width = 30
        ws_trans.column_dimensions['E'].width = 15

        # Salva
        wb.save(filepath)
        return filepath