# Builds tests/sample.pdf: native text + a bar chart that exists only as a raster image.
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
im = Image.new("RGB", (900, 520), "white"); d = ImageDraw.Draw(im)
d.text((250, 10), "Quarterly Revenue 2025 (USD M)", fill="black", font=f)
for i, (q, v) in enumerate([("Q1", 42), ("Q2", 58), ("Q3", 73), ("Q4", 91)]):
    x = 120 + i * 190; h = v * 4
    d.rectangle([x, 470 - h, x + 120, 470], fill=(60, 120, 200))
    d.text((x + 35, 470 - h - 30), f"{v}M", fill="black", font=f)
    d.text((x + 40, 480), q, fill="black", font=f)
im.save("tests/chart.png")
c = canvas.Canvas("tests/sample.pdf", pagesize=A4); c.setFont("Helvetica", 12)
c.drawString(60, 780, "Annual Report: Statistics Overview")
c.drawString(60, 760, "This native text must always be extracted. Growth reached 25% year over year.")
c.drawImage("tests/chart.png", 60, 300, width=470, height=272)
c.drawString(60, 280, "Figure 1. Revenue by quarter (image only chart above).")
c.save()
