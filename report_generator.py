import io
import logging
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

logger = logging.getLogger(__name__)

class ReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
        # Добавляем стили
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Title'],
            fontSize=18,
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        self.header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=10
        )
        
        self.normal_style = ParagraphStyle(
            'CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        )

    def generate_estimate_report(self, estimate: Dict[str, Any], items: List[Dict[str, Any]], totals: Dict[str, float]) -> io.BytesIO:
        """Генерация PDF отчета по смете"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
        
        elements = []
        
        # Заголовок
        title = Paragraph(f"Смета: {estimate['title']}", self.title_style)
        elements.append(title)
        elements.append(Spacer(1, 12))
        
        # Информация о смете
        if estimate.get('description'):
            desc_para = Paragraph(f"<b>Описание:</b> {estimate['description']}", self.normal_style)
            elements.append(desc_para)
        
        created_date = datetime.fromisoformat(estimate['created_at'].replace('Z', '+00:00'))
        date_para = Paragraph(f"<b>Дата создания:</b> {created_date.strftime('%d.%m.%Y %H:%M')}", self.normal_style)
        elements.append(date_para)
        elements.append(Spacer(1, 20))
        
        # Таблица с позициями
        if items:
            # Заголовок таблицы
            table_header = Paragraph("Позиции сметы", self.header_style)
            elements.append(table_header)
            
            # Данные для таблицы
            table_data = [
                ['№', 'Наименование работ/услуг', 'Время (ч)', 'Стоимость (₽)']
            ]
            
            for i, item in enumerate(items, 1):
                table_data.append([
                    str(i),
                    item['name'],
                    f"{item['duration']:.1f}",
                    f"{item['cost']:.2f}"
                ])
            
            # Создание таблицы
            table = Table(table_data, colWidths=[1*cm, 10*cm, 2.5*cm, 3*cm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 20))
        
        # Итоги
        totals_header = Paragraph("Итоги", self.header_style)
        elements.append(totals_header)
        
        total_duration_para = Paragraph(f"<b>Общее время:</b> {totals['total_duration']:.1f} часов", self.normal_style)
        elements.append(total_duration_para)
        
        total_cost_para = Paragraph(f"<b>Общая стоимость:</b> {totals['total_cost']:.2f} ₽", self.normal_style)
        elements.append(total_cost_para)
        
        if totals['total_duration'] > 0:
            avg_rate = totals['total_cost'] / totals['total_duration']
            avg_rate_para = Paragraph(f"<b>Средняя ставка:</b> {avg_rate:.2f} ₽/час", self.normal_style)
            elements.append(avg_rate_para)
        
        elements.append(Spacer(1, 30))
        
        # Подпись
        signature_para = Paragraph("Отчет сгенерирован автоматически", ParagraphStyle(
            'Signature',
            parent=self.styles['Normal'],
            fontSize=8,
            alignment=TA_RIGHT,
            textColor=colors.grey
        ))
        elements.append(signature_para)
        
        # Сборка документа
        doc.build(elements)
        buffer.seek(0)
        
        return buffer

    def generate_text_report(self, estimate: Dict[str, Any], items: List[Dict[str, Any]], totals: Dict[str, float]) -> str:
        """Генерация текстового отчета по смете"""
        
        lines = []
        lines.append("=" * 50)
        lines.append(f"СМЕТА: {estimate['title']}")
        lines.append("=" * 50)
        lines.append("")
        
        if estimate.get('description'):
            lines.append(f"Описание: {estimate['description']}")
            lines.append("")
        
        created_date = datetime.fromisoformat(estimate['created_at'].replace('Z', '+00:00'))
        lines.append(f"Дата создания: {created_date.strftime('%d.%m.%Y %H:%M')}")
        lines.append("")
        
        if items:
            lines.append("ПОЗИЦИИ СМЕТЫ:")
            lines.append("-" * 50)
            lines.append(f"{'№':<3} {'Наименование':<25} {'Время (ч)':<10} {'Стоимость (₽)':<12}")
            lines.append("-" * 50)
            
            for i, item in enumerate(items, 1):
                name = item['name'][:22] + "..." if len(item['name']) > 25 else item['name']
                lines.append(f"{i:<3} {name:<25} {item['duration']:<10.1f} {item['cost']:<12.2f}")
            
            lines.append("-" * 50)
        
        lines.append("")
        lines.append("ИТОГИ:")
        lines.append(f"Общее время: {totals['total_duration']:.1f} часов")
        lines.append(f"Общая стоимость: {totals['total_cost']:.2f} ₽")
        
        if totals['total_duration'] > 0:
            avg_rate = totals['total_cost'] / totals['total_duration']
            lines.append(f"Средняя ставка: {avg_rate:.2f} ₽/час")
        
        lines.append("")
        lines.append("=" * 50)
        
        return "\n".join(lines) 