"""
PDF Generator for Tax Filing Documents
Generates professional, Nigerian Tax Authority compliant PDF documents
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfgen import canvas
import qrcode
from io import BytesIO
from datetime import datetime
import os

class TaxFilingPDFGenerator:
    """Generate professional tax filing PDF documents"""
    
    def __init__(self):
        self.page_width, self.page_height = A4
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='KusmusTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#1a1a1a'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))
        
        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor('#0072ff'),
            spaceAfter=6,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            borderPadding=5,
            backColor=colors.HexColor('#f0f8ff')
        ))
        
        # Body text
        self.styles.add(ParagraphStyle(
            name='KusmusBody',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#333333'),
            spaceAfter=6
        ))
    
    def generate_tax_filing(self, output_path: str, data: dict) -> str:
        """
        Generate tax filing PDF
        
        Args:
            output_path: Path to save PDF
            data: {
                "taxpayer_info": {...},
                "income_sources": [...],
                "reliefs": [...],
                "tax_calculation": {...},
                "citations": [...]
            }
        
        Returns:
            Path to generated PDF
        """
        # Create PDF document
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Build content
        story = []
        
        # Header
        story.extend(self._build_header(data))
        story.append(Spacer(1, 0.5*cm))
        
        # Section A: Taxpayer Information
        story.extend(self._build_taxpayer_section(data.get("taxpayer_info", {})))
        story.append(Spacer(1, 0.3*cm))
        
        # Section B: Income Sources
        story.extend(self._build_income_section(data.get("income_sources", [])))
        story.append(Spacer(1, 0.3*cm))
        
        # Section C: Reliefs & Deductions
        story.extend(self._build_reliefs_section(data.get("reliefs", [])))
        story.append(Spacer(1, 0.3*cm))
        
        # Section D: Tax Calculation
        story.extend(self._build_calculation_section(data.get("tax_calculation", {})))
        story.append(Spacer(1, 0.3*cm))
        
        # Footer with QR code
        story.extend(self._build_footer(data))
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_watermark, onLaterPages=self._add_watermark)
        
        return output_path
    
    def _build_header(self, data):
        """Build document header"""
        elements = []
        
        # Title
        title = Paragraph("NIGERIAN TAX AUTHORITY", self.styles['KusmusTitle'])
        elements.append(title)
        
        subtitle = Paragraph(
            f"Personal Income Tax Return - {data.get('tax_year', 2025)}",
            self.styles['KusmusBody']
        )
        elements.append(subtitle)
        
        elements.append(Spacer(1, 0.3*cm))
        
        # Horizontal line
        line_table = Table([['']], colWidths=[16*cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, 0), 2, colors.HexColor('#0072ff')),
        ]))
        elements.append(line_table)
        
        return elements
    
    def _build_taxpayer_section(self, taxpayer_info):
        """Build Section A: Taxpayer Information"""
        elements = []
        
        elements.append(Paragraph("SECTION A: TAXPAYER INFORMATION", self.styles['SectionHeader']))
        
        data = [
            ['Name:', taxpayer_info.get('name', 'N/A')],
            ['Tax Identification Number (TIN):', taxpayer_info.get('tin', 'N/A')],
            ['Address:', taxpayer_info.get('address', 'N/A')],
            ['Email:', taxpayer_info.get('email', 'N/A')],
            ['Phone:', taxpayer_info.get('phone', 'N/A')]
        ]
        
        table = Table(data, colWidths=[6*cm, 10*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f5f5f5')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_income_section(self, income_sources):
        """Build Section B: Income Sources"""
        elements = []
        
        elements.append(Paragraph("SECTION B: INCOME SOURCES", self.styles['SectionHeader']))
        
        data = [['Source', 'Amount (₦)']]
        total = 0
        
        for source in income_sources:
            data.append([source['name'], f"{source['amount']:,.2f}"])
            total += source['amount']
        
        # Add total row
        data.append(['GROSS INCOME', f"{total:,.2f}"])
        
        table = Table(data, colWidths=[10*cm, 6*cm])
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0072ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            # Total row
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f8ff')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#0072ff')),
            # General
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_reliefs_section(self, reliefs):
        """Build Section C: Reliefs & Deductions"""
        elements = []
        
        elements.append(Paragraph("SECTION C: RELIEFS & DEDUCTIONS", self.styles['SectionHeader']))
        
        data = [['Relief Type', 'Amount (₦)', 'Legal Citation']]
        total = 0
        
        for relief in reliefs:
            data.append([
                relief['name'],
                f"{relief['amount']:,.2f}",
                relief.get('citation', 'N/A')
            ])
            total += relief['amount']
        
        # Add total row
        data.append(['TOTAL RELIEFS', f"{total:,.2f}", ''])
        
        table = Table(data, colWidths=[6*cm, 4*cm, 6*cm])
        table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0072ff')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            # Data rows
            ('BACKGROUND', (0, 1), (-1, -2), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
            ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -2), 8),
            # Total row
            ('BACKGROUND', (0, -1), (1, -1), colors.HexColor('#f0f8ff')),
            ('FONTNAME', (0, -1), (1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#0072ff')),
            # General
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_calculation_section(self, tax_calc):
        """Build Section D: Tax Calculation"""
        elements = []
        
        elements.append(Paragraph("SECTION D: TAX CALCULATION", self.styles['SectionHeader']))
        
        data = [
            ['Gross Income', f"₦ {tax_calc.get('gross_income', 0):,.2f}"],
            ['Less: Total Reliefs', f"₦ {tax_calc.get('total_reliefs', 0):,.2f}"],
            ['Taxable Income', f"₦ {tax_calc.get('taxable_income', 0):,.2f}"],
            ['Tax Due', f"₦ {tax_calc.get('tax_due', 0):,.2f}"],
            ['Less: WHT Paid', f"₦ {tax_calc.get('wht_paid', 0):,.2f}"],
            ['BALANCE DUE', f"₦ {tax_calc.get('balance_due', 0):,.2f}"]
        ]
        
        table = Table(data, colWidths=[10*cm, 6*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -2), colors.white),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ffe600')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 0), (-1, -2), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.HexColor('#0072ff')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        
        elements.append(table)
        return elements
    
    def _build_footer(self, data):
        """Build document footer with QR code"""
        elements = []
        
        elements.append(Spacer(1, 0.5*cm))
        
        # Generation info
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M WAT")
        footer_text = Paragraph(
            f"<i>Generated by Kusmus AI Tax Agent | {gen_time}</i>",
            self.styles['KusmusBody']
        )
        elements.append(footer_text)
        
        # QR Code (verification)
        qr_data = f"TAX_FILING_{data.get('taxpayer_info', {}).get('tin', 'N/A')}_{data.get('tax_year', 2025)}"
        qr_img = self._generate_qr_code(qr_data)
        if qr_img:
            elements.append(Spacer(1, 0.2*cm))
            elements.append(qr_img)
        
        return elements
    
    def _generate_qr_code(self, data: str, size: int = 3):
        """Generate QR code image"""
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to ReportLab Image
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            return Image(buffer, width=size*cm, height=size*cm)
        except Exception as e:
            print(f"QR Code generation failed: {e}")
            return None
    
    def _add_watermark(self, canvas_obj, doc):
        """Add watermark to page"""
        canvas_obj.saveState()
        canvas_obj.setFont('Helvetica', 60)
        canvas_obj.setFillColorRGB(0.9, 0.9, 0.9, alpha=0.1)
        canvas_obj.rotate(45)
        canvas_obj.drawCentredString(400, 100, "KUSMUS AI")
        canvas_obj.restoreState()
