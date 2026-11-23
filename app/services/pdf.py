import os
from io import BytesIO

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.db.models import Expense
from app.keyboards.categories import UNCATEGORIZED_LABEL
from app.utils.money import format_amount

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "fonts")


def generate_expenses_pdf(expenses: list[Expense], period_label: str) -> BytesIO:
    pdf = FPDF()
    pdf.add_page()

    font_path = os.path.join(FONT_DIR, "DejaVuSans.ttf")
    if os.path.exists(font_path):
        # `uni=True` fpdf2 2.5.1 dan beri eskirgan (Unicode endi standart)
        pdf.add_font("DejaVu", "", font_path)
        pdf.add_font("DejaVu", "B", font_path.replace("Sans", "Sans-Bold"))
        font_name = "DejaVu"
    else:
        font_name = "Helvetica"

    pdf.set_font(font_name, "B", 16)
    # `ln=True` fpdf2 2.5.2 dan beri eskirgan
    pdf.cell(0, 10, f"Xarajatlar - {period_label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(5)

    # Table header
    pdf.set_font(font_name, "B", 10)
    col_widths = [35, 45, 55, 55]
    headers = ["Sana", "Summa (UZS)", "Kategoriya", "Merchant"]
    for w, h in zip(col_widths, headers):
        pdf.cell(w, 8, h, border=1, align="C")
    pdf.ln()

    # Table rows
    pdf.set_font(font_name, "", 9)
    total = 0
    for exp in expenses:
        date = exp.transaction_time or exp.created_at
        date_str = date.strftime("%d.%m.%Y %H:%M") if date else "-"
        # `category` NULL bo'lishi mumkin (userbot avtomatik saqlagan, hali
        # kategoriyalanmagan xarajatlar). Ilgari u to'g'ridan-to'g'ri fpdf'ga
        # berilardi va butun PDF yaratish `AttributeError: 'NoneType' object
        # has no attribute 'encode'` bilan yiqilardi — foydalanuvchi esa hech
        # qanday javob ko'rmasdi.
        category = exp.category or UNCATEGORIZED_LABEL
        merchant = (exp.merchant or "-")[:25]

        pdf.cell(col_widths[0], 7, date_str, border=1)
        pdf.cell(col_widths[1], 7, format_amount(exp.amount), border=1, align="R")
        pdf.cell(col_widths[2], 7, category, border=1)
        pdf.cell(col_widths[3], 7, merchant, border=1)
        pdf.ln()
        total += float(exp.amount)

    # Total
    pdf.set_font(font_name, "B", 10)
    pdf.ln(3)
    pdf.cell(0, 10, f"Jami: {format_amount(total)} UZS",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="R")

    buffer = BytesIO()
    buffer.write(pdf.output())
    buffer.seek(0)
    return buffer
