import os
import logging
from typing import Dict, Any, Optional
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger("doc_generator")

# Ensure static directories exist for serving PDF files
STATIC_DOCS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend", "static", "docs")
)

os.makedirs(STATIC_DOCS_DIR, exist_ok=True)

class DocumentGenerator:
    def __init__(self):
        self.output_dir = STATIC_DOCS_DIR
        logger.info(f"PDF Generator initialized. Output directory: {self.output_dir}")

    def _get_pdf_path(self, filename: str) -> str:
        return os.path.join(self.output_dir, filename)

    def _get_download_url(self, filename: str) -> str:
        return f"/static/docs/{filename}"

    def create_custom_pdf(self, filename: str, title: str, content: str) -> Dict[str, Any]:
        pdf_path = self._get_pdf_path(filename)
        doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                                rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            name='TitleStyle',
            fontName='Helvetica-Bold',
            fontSize=24,
            textColor=colors.HexColor('#4F46E5'),
            spaceAfter=20
        )
        
        body_style = ParagraphStyle(
            name='BodyStyle',
            fontName='Helvetica',
            fontSize=11,
            leading=16,
            textColor=colors.HexColor('#374151'),
            spaceAfter=12
        )

        story = [
            Paragraph(title, title_style),
            Spacer(1, 10),
            Paragraph(content.replace("\n", "<br/>"), body_style)
        ]
        
        doc.build(story)
        return {
            "status": "success",
            "pdf_path": pdf_path,
            "download_url": self._get_download_url(filename),
            "filename": filename
        }

    def generate_salary_slip(self, employee: Dict[str, Any], salary: Dict[str, Any]) -> Dict[str, Any]:
        filename = f"salary_slip_{employee['employee_id']}_{salary.get('month', 'current')}.pdf".lower()
        pdf_path = self._get_pdf_path(filename)
        
        doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                                rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            name='TitleStyle',
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#4F46E5'),
            alignment=1, # Center
            spaceAfter=20
        )
        
        bold_style = ParagraphStyle(
            name='BoldStyle',
            fontName='Helvetica-Bold',
            fontSize=10,
            textColor=colors.HexColor('#1F2937')
        )
        
        normal_style = ParagraphStyle(
            name='NormalStyle',
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#374151')
        )

        story = []
        story.append(Paragraph("Aetheris HR Services - Salary Slip", title_style))
        story.append(Spacer(1, 10))

        # Employee details table
        emp_data = [
            [Paragraph("Employee ID:", bold_style), Paragraph(employee['employee_id'], normal_style),
             Paragraph("Employee Name:", bold_style), Paragraph(employee['name'], normal_style)],
            [Paragraph("Designation:", bold_style), Paragraph(employee['designation'], normal_style),
             Paragraph("Department:", bold_style), Paragraph(employee['department'], normal_style)],
            [Paragraph("Month:", bold_style), Paragraph(salary.get('month', 'June'), normal_style),
             Paragraph("Email:", bold_style), Paragraph(employee['email'], normal_style)]
        ]
        
        t1 = Table(emp_data, colWidths=[100, 150, 100, 150])
        t1.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F9FAFB')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        story.append(t1)
        story.append(Spacer(1, 20))

        # Earnings & Deductions Table
        breakdown_data = [
            [Paragraph("Earnings Item", bold_style), Paragraph("Amount ($)", bold_style),
             Paragraph("Deductions Item", bold_style), Paragraph("Amount ($)", bold_style)],
            [Paragraph("Base Salary", normal_style), Paragraph(f"{salary['base_salary']:.2f}", normal_style),
             Paragraph("Tax / Deductions", normal_style), Paragraph(f"{salary['deductions']:.2f}", normal_style)],
            [Paragraph("Allowances", normal_style), Paragraph(f"{salary['allowances']:.2f}", normal_style),
             Paragraph("-", normal_style), Paragraph("-", normal_style)],
            [Paragraph("Total Earnings", bold_style), Paragraph(f"{salary['base_salary'] + salary['allowances']:.2f}", bold_style),
             Paragraph("Total Deductions", bold_style), Paragraph(f"{salary['deductions']:.2f}", bold_style)]
        ]
        
        t2 = Table(breakdown_data, colWidths=[150, 100, 150, 100])
        t2.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F3F4F6')),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('PADDING', (0,0), (-1,-1), 8),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E5E7EB')),
        ]))
        story.append(t2)
        story.append(Spacer(1, 20))

        # Net Pay
        net_pay_data = [
            [Paragraph("Net Take-Home Salary:", bold_style), Paragraph(f"${salary['net_salary']:.2f}", bold_style)]
        ]
        t3 = Table(net_pay_data, colWidths=[150, 350])
        t3.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#EEF2F6')),
            ('PADDING', (0,0), (-1,-1), 10),
            ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#4F46E5')),
        ]))
        story.append(t3)
        story.append(Spacer(1, 40))
        
        story.append(Paragraph("This is a computer-generated salary slip and does not require a physical signature.", normal_style))

        doc.build(story)
        return {
            "status": "success",
            "pdf_path": pdf_path,
            "download_url": self._get_download_url(filename),
            "filename": filename
        }

    def generate_offer_letter(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        filename = f"offer_letter_{employee['employee_id']}.pdf".lower()
        content = (
            f"Dear {employee['name']},\n\n"
            f"We are delighted to offer you the position of {employee['designation']} within the {employee['department']} team "
            f"at Aetheris HR Services.\n\n"
            f"Your proposed joining date will be {employee.get('joining_date', 'August 15, 2026')}.\n\n"
            f"Please return a signed copy of this letter to signify your acceptance of the terms detailed herein.\n\n"
            f"Sincerely,\n"
            f"Priya Sharma\n"
            f"HR Director"
        )
        return self.create_custom_pdf(filename, "Offer Letter", content)

    def generate_extension_letter(self, employee: Dict[str, Any]) -> Dict[str, Any]:
        filename = f"extension_letter_{employee['employee_id']}.pdf".lower()
        content = (
            f"Dear {employee['name']},\n\n"
            f"This letter confirms the extension of your contract/employment as {employee['designation']} in the "
            f"{employee['department']} department.\n\n"
            f"All other terms and conditions of your employment contract remain unchanged.\n\n"
            f"Thank you for your continuous dedication and contribution to Aetheris HR Services.\n\n"
            f"Sincerely,\n"
            f"Priya Sharma\n"
            f"HR Director"
        )
        return self.create_custom_pdf(filename, "Employment Contract Extension", content)
