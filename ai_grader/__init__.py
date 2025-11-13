import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
)

__all__ = []
from .api_key_manager import GeminiAPIKeyManager
from .grader import HomeworkGrader
from .pdf2md import pdf_to_markdown
from .plagiarism_or_not import plagiarism_check
from .hw2json import hw_to_json

__all__ = [
    'GeminiAPIKeyManager',
    'HomeworkGrader',
    'pdf_to_markdown',
    'plagiarism_check',
    'hw_to_json',
]