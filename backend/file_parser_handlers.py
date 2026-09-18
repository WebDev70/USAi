"""file_parser_handlers.py — A mixin for file parsing."""
import io
from email import message_from_bytes, errors
from email.policy import HTTP
from pathlib import Path

from .file_parser import extract_text_from_file

class FileParserHandlerMixin:
    """Mixin providing /extract-text handler method."""

    # 25 MB upload limit for PDF/DOCX files. This is a compromise between
    # allowing legitimate large documents and preventing unbounded memory usage.
    MAX_UPLOAD_SIZE = 25 * 1024 * 1024

    def _post_extract_text(self):
        """POST /extract-text — extract text from an uploaded file."""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
        except (ValueError, TypeError):
            self._json_response(400, {'error': 'Invalid Content-Length'})
            return

        if content_length > self.MAX_UPLOAD_SIZE:
            self._json_response(413, {'error': 'Request too large'})
            return
        
        # To avoid reading the entire file into memory twice, we create a
        # single bytes object containing the headers and then append the rfile
        # stream's content.
        headers_bytes = b''
        for key, value in self.headers.items():
            headers_bytes += f'{key}: {value}\r\n'.encode('utf-8')
        
        # The email parser needs a separator between headers and body.
        message_bytes = headers_bytes + b'\r\n' + self.rfile.read(content_length)
        
        msg = message_from_bytes(message_bytes, policy=HTTP)

        if msg.defects:
            self._json_response(400, {'error': 'Malformed multipart/form-data: incomplete body'})
            return

        try:
            for part in msg.iter_parts():
                if part.get_filename():
                    try:
                        file_stream = io.BytesIO(part.get_payload(decode=True))
                        file_extension = Path(part.get_filename()).suffix
                        text = extract_text_from_file(file_stream, file_extension)
                        self._json_response(200, {'text': text})
                        return
                    except UnicodeDecodeError:
                        self._json_response(400, {'error': 'File content is not valid UTF-8 text'})
                        return
                    except Exception as e:
                        self._json_response(500, {'error': f'Error extracting text: {e}'})
                        return
            
            self._json_response(400, {'error': 'Request must include a "file" field'})
        except AttributeError:
            self._json_response(400, {'error': 'Malformed multipart/form-data request'})
