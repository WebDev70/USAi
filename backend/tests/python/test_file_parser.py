"""Unit tests for backend/file_parser.py — stdlib-only DOCX extraction.

These tests exist because DOCX parsing moved off ``python-docx`` onto the Python
standard library (``zipfile`` + ``xml.etree``). They build .docx archives by hand
so the parser is exercised without any third-party helper, and they cover the
failure paths (missing document part, oversized body) that the guard rails in
``extract_text_from_docx`` are there to catch.

Stdlib `unittest` only — no third-party deps.
"""

import io
import sys
import unittest
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / 'backend'))

import file_parser  # noqa: E402

W_NS = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'

# Minimal OPC parts. Word will not open an archive missing these, so the test
# fixtures include them to stay faithful to a real .docx.
CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/vnd'
    '.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    '</Types>'
)
RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Target="word/document.xml" Type="http://schemas'
    '.openxmlformats.org/officeDocument/2006/relationships/officeDocument"/>'
    '</Relationships>'
)


def _document_xml(body):
    """Wrap a WordprocessingML body fragment in a valid document.xml."""
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>{body}</w:body></w:document>'
    )


def _docx_bytes(body, include_document=True):
    """Build an in-memory .docx (ZIP) around the given body fragment."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('[Content_Types].xml', CONTENT_TYPES)
        archive.writestr('_rels/.rels', RELS)
        if include_document:
            archive.writestr('word/document.xml', _document_xml(body))
    buffer.seek(0)
    return buffer


def _paragraphs(*texts):
    """Build simple single-run paragraphs from plain strings."""
    return ''.join(
        f'<w:p><w:r><w:t>{escape(t)}</w:t></w:r></w:p>' for t in texts
    )


class ExtractDocxTests(unittest.TestCase):
    """FP-1…FP-7: stdlib DOCX text extraction behaviour."""

    def test_fp1_single_paragraph_round_trip(self):
        """FP-1: one paragraph comes back as one trailing-newline line."""
        stream = _docx_bytes(_paragraphs('Hello USAi'))
        self.assertEqual(file_parser.extract_text_from_docx(stream), 'Hello USAi\n')

    def test_fp2_multiple_paragraphs_keep_document_order(self):
        """FP-2: paragraph order and one-line-per-paragraph layout are preserved."""
        stream = _docx_bytes(_paragraphs('First', 'Second', 'Third'))
        self.assertEqual(
            file_parser.extract_text_from_docx(stream),
            'First\nSecond\nThird\n',
        )

    def test_fp3_multiple_runs_join_without_extra_spacing(self):
        """FP-3: a paragraph split across runs is rejoined verbatim."""
        body = (
            '<w:p>'
            '<w:r><w:t>Split </w:t></w:r>'
            '<w:r><w:t>across </w:t></w:r>'
            '<w:r><w:t>runs</w:t></w:r>'
            '</w:p>'
        )
        stream = _docx_bytes(body)
        self.assertEqual(
            file_parser.extract_text_from_docx(stream),
            'Split across runs\n',
        )

    def test_fp4_tabs_and_breaks_become_whitespace(self):
        """FP-4: w:tab, w:br, and w:cr keep words from being glued together."""
        body = (
            '<w:p>'
            '<w:r><w:t>Name</w:t><w:tab/><w:t>Value</w:t></w:r>'
            '<w:r><w:br/><w:t>after-break</w:t><w:cr/><w:t>after-cr</w:t></w:r>'
            '</w:p>'
        )
        stream = _docx_bytes(body)
        self.assertEqual(
            file_parser.extract_text_from_docx(stream),
            'Name\tValue\nafter-break\nafter-cr\n',
        )

    def test_fp5_table_and_hyperlink_text_is_captured(self):
        """FP-5: text nested in tables and hyperlinks is not dropped."""
        body = (
            '<w:tbl><w:tr><w:tc>'
            '<w:p><w:r><w:t>Cell A</w:t></w:r></w:p>'
            '</w:tc><w:tc>'
            '<w:p><w:hyperlink><w:r><w:t>Linked</w:t></w:r></w:hyperlink></w:p>'
            '</w:tc></w:tr></w:tbl>'
        )
        stream = _docx_bytes(body)
        self.assertEqual(
            file_parser.extract_text_from_docx(stream),
            'Cell A\nLinked\n',
        )

    def test_fp5b_empty_paragraph_yields_blank_line(self):
        """FP-5b: an empty paragraph still produces its blank line."""
        body = _paragraphs('Above') + '<w:p/>' + _paragraphs('Below')
        stream = _docx_bytes(body)
        self.assertEqual(
            file_parser.extract_text_from_docx(stream),
            'Above\n\nBelow\n',
        )

    def test_fp6_missing_document_part_raises_value_error(self):
        """FP-6: a ZIP without word/document.xml is not a usable .docx."""
        stream = _docx_bytes('', include_document=False)
        with self.assertRaises(ValueError) as ctx:
            file_parser.extract_text_from_docx(stream)
        self.assertIn('word/document.xml', str(ctx.exception))

    def test_fp7_oversized_body_is_rejected(self):
        """FP-7: the zip-bomb guard trips before the XML is read into memory."""
        stream = _docx_bytes(_paragraphs('tiny'))
        original_limit = file_parser.MAX_DOCX_XML_BYTES
        file_parser.MAX_DOCX_XML_BYTES = 1  # 1 byte — any real body exceeds it
        try:
            with self.assertRaises(ValueError) as ctx:
                file_parser.extract_text_from_docx(stream)
        finally:
            file_parser.MAX_DOCX_XML_BYTES = original_limit
        self.assertIn('too large', str(ctx.exception))

    def test_fp7b_non_zip_input_is_rejected(self):
        """FP-7b: random bytes are not a ZIP, so zipfile refuses them."""
        with self.assertRaises(zipfile.BadZipFile):
            file_parser.extract_text_from_docx(io.BytesIO(b'not a zip at all'))


class ExtractDispatchTests(unittest.TestCase):
    """FP-8…FP-11: extension dispatch in extract_text_from_file."""

    def test_fp8_docx_extension_routes_to_docx_parser(self):
        stream = _docx_bytes(_paragraphs('Routed'))
        self.assertEqual(
            file_parser.extract_text_from_file(stream, '.docx'),
            'Routed\n',
        )

    def test_fp9_txt_extension_decodes_utf8(self):
        stream = io.BytesIO('café — ok'.encode('utf-8'))
        self.assertEqual(
            file_parser.extract_text_from_file(stream, '.txt'),
            'café — ok',
        )

    def test_fp10_unknown_extension_returns_empty_string(self):
        """Unknown/binary types return '' rather than raising, so uploads of
        unsupported files degrade gracefully instead of 500-ing."""
        stream = io.BytesIO(b'\x00\x01\x02binary')
        self.assertEqual(file_parser.extract_text_from_file(stream, '.bin'), '')

    def test_fp11_pdf_extension_routes_to_pdf_parser(self):
        """FP-11: dispatch reaches extract_text_from_pdf (patched, so this test
        asserts routing only and never depends on a real PDF fixture)."""
        calls = []
        original = file_parser.extract_text_from_pdf
        file_parser.extract_text_from_pdf = lambda s: calls.append(s) or 'pdf-text'
        try:
            stream = io.BytesIO(b'%PDF-1.4 stub')
            result = file_parser.extract_text_from_file(stream, '.pdf')
        finally:
            file_parser.extract_text_from_pdf = original
        self.assertEqual(result, 'pdf-text')
        self.assertEqual(calls, [stream])


class NoPythonDocxDependencyTests(unittest.TestCase):
    """FP-12: guard the runtime-surface decision so it cannot silently regress."""

    def test_fp12_file_parser_does_not_import_python_docx(self):
        source = (PROJECT_ROOT / 'backend' / 'file_parser.py').read_text()
        self.assertNotIn('import docx', source)
        self.assertNotIn('from docx', source)

    def test_fp12b_requirements_does_not_list_python_docx(self):
        """Only the actual requirement lines are inspected — the file's comments
        legitimately mention python-docx/lxml to explain why they are absent."""
        lines = (PROJECT_ROOT / 'requirements.txt').read_text().lower().splitlines()
        declared = [
            line for line in lines
            if line.strip() and not line.lstrip().startswith('#')
        ]
        for banned in ('python-docx', 'python_docx', 'lxml'):
            for line in declared:
                self.assertNotIn(banned, line)


if __name__ == '__main__':
    unittest.main()
