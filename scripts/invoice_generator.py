import os
import random
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, darkblue, gray

def create_complex_invoice(file_path, data):
    c = canvas.Canvas(file_path, pagesize=A4)
    width, height = A4
    
    # 1. Randomized Header Layout (Simulate different vendor templates)
    layout_style = random.choice(['classic', 'modern'])
    
    if layout_style == 'classic':
        # Left-aligned classic header
        c.setFont("Helvetica-Bold", 24)
        c.setFillColor(darkblue)
        c.drawString(1 * inch, height - 1 * inch, data['vendor'])
        c.setFillColor(black)
        c.setFont("Helvetica", 10)
        c.drawString(1 * inch, height - 1.3 * inch, "TRN: 100-555-999-222")
    else:
        # Centered modern header
        c.setFont("Times-Bold", 28)
        c.drawCentredString(width / 2, height - 1 * inch, data['vendor'])
        c.setFont("Times-Roman", 10)
        c.drawCentredString(width / 2, height - 1.3 * inch, "Dubai Silicon Oasis, UAE")

    # 2. Invoice Meta Data (Mixed locations)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(width - 2.5 * inch, height - 2 * inch, f"NO: {data['inv_id']}")
    c.drawString(width - 2.5 * inch, height - 2.2 * inch, f"DATE: {data['date']}")
    c.setFillColor(gray)
    c.drawString(width - 2.5 * inch, height - 2.4 * inch, f"DUE: {data['due_date']}")
    c.setFillColor(black)

    # 3. Line Items (Table)
    y = height - 3.5 * inch
    c.setLineWidth(1)
    c.line(1 * inch, y + 10, width - 1 * inch, y + 10)
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(1 * inch, y, "ITEM DESCRIPTION")
    c.drawRightString(width - 1 * inch, y, "TOTAL (AED)")
    
    y -= 20
    c.setFont("Helvetica", 10)
    
    for item, price in data['items']:
        # Wrap long text logic (simplified)
        if len(item) > 50:
            c.drawString(1 * inch, y, item[:50] + "...")
        else:
            c.drawString(1 * inch, y, item)
            
        c.drawRightString(width - 1 * inch, y, f"{price:,.2f}")
        y -= 20

    # 4. Totals & Notes
    y -= 20
    c.setLineWidth(2)
    c.line(1 * inch, y + 10, width - 1 * inch, y + 10)
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(4 * inch, y - 20, "GRAND TOTAL:")
    c.drawRightString(width - 1 * inch, y - 20, f"AED {data['total']:,.2f}")
    
    # 5. Status Stamp
    c.saveState()
    c.translate(width / 2, height / 2)
    c.rotate(45)
    c.setFont("Helvetica-Bold", 50)
    
    status = data['status']
    if status == "Paid":
        c.setFillColorRGB(0, 0.6, 0, 0.3) # Transparent Green
    elif status == "Overdue":
        c.setFillColorRGB(0.8, 0, 0, 0.3) # Transparent Red
    else:
        c.setFillColorRGB(0.5, 0.5, 0.5, 0.3) # Transparent Grey
        
    c.drawCentredString(0, 0, status.upper())
    c.restoreState()

    c.save()
    print(f"✅ Generated: {os.path.basename(file_path)}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_dir = os.path.join(base_dir, "data")
    if not os.path.exists(data_dir): os.makedirs(data_dir)

    # TEST CASE 1
    create_complex_invoice(os.path.join(data_dir, "inv_construction.pdf"), {
        "vendor": "BuildRight Construction",
        "inv_id": "CONS-9901",
        "date": "2025-10-01",
        "due_date": "2025-10-15",
        "items": [("Office Renovation - Phase 1 Materials", 6500.00), ("Labor Charges (5 Workers)", 3000.00)],
        "total": 9500.00,
        "status": "Pending"
    })

    # TEST CASE 2
    create_complex_invoice(os.path.join(data_dir, "inv_saas.pdf"), {
        "vendor": "CloudHost Inc",
        "inv_id": "SUB-2211",
        "date": "2025-11-01",
        "due_date": "2025-11-01",
        "items": [("Enterprise Server Hosting - Nov 2025", 450.00)],
        "total": 450.00,
        "status": "Paid"
    })

    # TEST CASE 3
    create_complex_invoice(os.path.join(data_dir, "inv_office_supplies.pdf"), {
        "vendor": "PaperClipz Stationery",
        "inv_id": "SUP-8822",
        "date": "2025-12-10",
        "due_date": "2025-12-24",
        "items": [
            ("A4 Paper Reams (x50 boxes) - High quality white paper for office printers", 1200.00),
            ("Black Ink Cartridges (x10) - HP Compatible", 800.50),
            ("Whiteboard Markers set of 4 colors", 45.00)
        ],
        "total": 2045.50,
        "status": "Overdue"
    })
