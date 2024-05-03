from flask import render_template
import pdfrw

def generate_pdf(template_name, **kwargs):
    # Render the HTML template with the provided arguments
    html = render_template(template_name, **kwargs)
    # Convert the rendered HTML to PDF
    pdf_file = pdfrw.PdfWriter()
    pdf_file.write(html)
    return pdf_file.stream.getvalue()