import io
from docx import Document
from pypdf import PdfReader

def extract_text_from_file(file_stream, file_extension):
    """Extracts text from a file stream based on its extension."""
    if file_extension == '.pdf':
        return extract_text_from_pdf(file_stream)
    elif file_extension == '.docx':
        return extract_text_from_docx(file_stream)
    elif file_extension == '.txt':
        # For plain text files, just decode
        return file_stream.read().decode('utf-8')
    else:
        # For unknown/binary file types, return empty string.
        return ''

def extract_text_from_pdf(file_stream):
    """Extracts text from a PDF file stream."""
    reader = PdfReader(file_stream)
    text = ''
    for page in reader.pages:
        text += page.extract_text() or ''
    return text

def extract_text_from_docx(file_stream):
    """Extracts text from a DOCX file stream."""
    document = Document(file_stream)
    text = ''
    for paragraph in document.paragraphs:
        text += paragraph.text + '\n'
    return text
