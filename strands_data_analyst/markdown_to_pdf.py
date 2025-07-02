import io
import markdown
from xhtml2pdf import pisa


HTML_DOC = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Generated PDF</title>
    <style>
        /* Basic CSS styling */
        body {{ font-family: sans-serif; line-height: 1.4; }}
        code {{ background-color: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-family: monospace; }}
        pre {{ background-color: #f0f0f0; padding: 10px; border: 1px solid #ccc; overflow: auto; font-family: monospace; }}
        
        /* Basic Table Styling */
        table {{ 
            border-collapse: collapse; /* Merge cell borders */
            width: 100%;           /* Make table take full width */
            margin-bottom: 1em;    /* Add space below the table */
            border: 1px solid #ccc; /* Add outer border */
        }}
        th, td {{ 
            border: 1px solid #ccc; /* Border for cells */
            padding: 8px;          /* Padding inside cells */
            text-align: left;      /* Align text to the left */
        }}
        th {{ 
            background-color: #f2f2f2; /* Light grey background for headers */
            font-weight: bold;       /* Make header text bold */
        }}
        thead {{ /* Ensure header is styled */
             display: table-header-group; /* Helps with page breaks in tables */
        }}
    </style>
</head>
<body>
    {html_body}
</body>
</html>
"""


def markdown_to_pdf(markdown_text):
    """
    Converts Markdown text (including tables) to a PDF BytesIO object.

    Args:
        markdown_text: A string containing Markdown content.

    Returns:
        An io.BytesIO object containing the PDF data, or None if an error occurred.
    """
    try:
        html_body = markdown.markdown(markdown_text, extensions=['tables'])
        html_doc = HTML_DOC.format(html_body=html_body)
    except Exception as e:
        print(f"Error converting Markdown to HTML: {e}")
        return None
    
    pdf_out = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_doc, pdf_out)

    if pisa_status.err:
        print(f"Error generating PDF: {pisa_status.err}")
        print(f"Context: {pisa_status.log}")
        return None

    pdf_out.seek(0)
    return pdf_out