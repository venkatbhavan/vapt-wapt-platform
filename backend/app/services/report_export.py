import os
from io import BytesIO
from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa
from app.models.report import Report
from fastapi import HTTPException

# Configure Jinja2 environment
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
if not os.path.exists(TEMPLATES_DIR):
    os.makedirs(TEMPLATES_DIR, exist_ok=True)

env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)

def render_html_report(report: Report) -> str:
    """Render the report snapshot into an HTML string."""
    if not report.snapshot:
        raise HTTPException(status_code=400, detail="Report snapshot is empty")
    
    template = env.get_template("report.html")
    html_content = template.render(
        report=report,
        dataset=report.snapshot
    )
    return html_content

def generate_pdf_report(report: Report) -> bytes:
    """Generate a PDF document from the report snapshot."""
    html_content = render_html_report(report)
    
    # xhtml2pdf needs a file-like object for destination
    result_file = BytesIO()
    
    # generate PDF
    pisa_status = pisa.CreatePDF(
        html_content,
        dest=result_file,
        encoding='utf-8'
    )
    
    if pisa_status.err:
        raise HTTPException(status_code=500, detail="PDF Generation Failed")
        
    pdf_bytes = result_file.getvalue()
    result_file.close()
    return pdf_bytes
