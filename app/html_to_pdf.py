import pdfkit
import os
from io import BytesIO

def generate_pdf_from_html(html, output_path=None):
    # Configure pdfkit
    config = pdfkit.configuration(wkhtmltopdf=os.environ.get('WKHTMLTOPDF_PATH', '/usr/bin/wkhtmltopdf'))

    # Generate the PDF from the HTML
    if output_path:
        pdfkit.from_string(html, output_path, configuration=config)
        with open(output_path, 'rb') as f:
            pdf_data = f.read()
    else:
        pdf = pdfkit.from_string(html, False, configuration=config)
        pdf_data = BytesIO(pdf)

    return pdf_data