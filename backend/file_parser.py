"""file_parser.py — plain-text extraction from uploaded documents.

Runtime-dependency policy (docs/principles.md §1 — minimal, audited runtime
surface): the ONLY third-party runtime package used here is ``pypdf``, because
parsing the PDF binary format by hand is not realistic. DOCX is handled with the
Python standard library alone (``zipfile`` + ``xml.etree``) — a .docx file is
just a ZIP archive containing XML, so pulling in ``python-docx`` (which drags in
the large, platform-specific ``lxml`` wheel) would grow the runtime surface and
break the hash-pinned install in ``requirements.txt`` for no real benefit.
"""
import xml.etree.ElementTree as ET
import zipfile

from pypdf import PdfReader

# WordprocessingML namespace — every text-bearing element in word/document.xml
# lives here. Declared once so the element lookups below stay readable.
_W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

# Guard against zip bombs: a .docx whose document.xml expands to something absurd
# would otherwise be read fully into memory. 50 MB of XML is far beyond any
# legitimate text document while still leaving generous headroom.
MAX_DOCX_XML_BYTES = 50 * 1024 * 1024


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
    """Extracts text from a DOCX file stream using only the standard library.

    A .docx is a ZIP archive; the body text lives in ``word/document.xml`` as
    WordprocessingML. We walk the paragraph (``w:p``) elements in document order
    and concatenate their text runs, so the output matches what a reader sees:
    one line per paragraph.
    """
    with zipfile.ZipFile(file_stream) as archive:
        try:
            info = archive.getinfo('word/document.xml')
        except KeyError:
            # A ZIP without the main document part is not a usable .docx.
            raise ValueError('Not a valid DOCX file: word/document.xml is missing')

        if info.file_size > MAX_DOCX_XML_BYTES:
            raise ValueError('DOCX document body is too large to parse')

        xml_bytes = archive.read('word/document.xml')

    # ElementTree does not fetch external entities, but rejecting declarations
    # explicitly keeps untrusted DOCX input fail-closed and makes that security
    # assumption auditable before using the stdlib parser.
    upper_xml = xml_bytes.upper()
    if b'<!DOCTYPE' in upper_xml or b'<!ENTITY' in upper_xml:
        raise ValueError('DOCX document contains an unsafe XML declaration')

    # B314 is narrowly suppressed because both declaration forms are rejected above.
    root = ET.fromstring(xml_bytes)  # nosec B314

    paragraphs = []
    for paragraph in root.iter(f'{{{_W_NS}}}p'):
        parts = []
        # Iterate the paragraph's descendants in document order so text inside
        # tables, hyperlinks, and nested runs is preserved, and so tabs/breaks
        # keep words from being glued together.
        for node in paragraph.iter():
            tag = node.tag
            if tag == f'{{{_W_NS}}}t':
                parts.append(node.text or '')
            elif tag == f'{{{_W_NS}}}tab':
                parts.append('\t')
            elif tag in (f'{{{_W_NS}}}br', f'{{{_W_NS}}}cr'):
                parts.append('\n')
        paragraphs.append(''.join(parts))

    # Trailing newline per paragraph mirrors the previous python-docx behaviour,
    # keeping downstream chunking/RAG output byte-compatible.
    return ''.join(f'{p}\n' for p in paragraphs)
