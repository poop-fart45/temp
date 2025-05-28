import pymupdf
from typing import Dict, List


class PDFProcessor:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.text_content = None

    def extract_text(self) -> str:
        """Extract text content from the PDF file."""
        doc = pymupdf.open(self.pdf_path)
        text = ""
        
        for page in doc:
            text += page.get_text()
        
        doc.close()
        self.text_content = text
        return text

    def extract_tables(self) -> List[Dict]:
        """Extract tables from the PDF file."""
        doc = pymupdf.open(self.pdf_path)
        tables = []
        
        for page in doc:
            # Extract tables using PyMuPDF's table detection
            # This is a placeholder - actual implementation will depend on PDF structure
            pass
        
        doc.close()
        return tables

    def get_metadata(self) -> Dict:
        """Extract metadata from the PDF file."""
        doc = pymupdf.open(self.pdf_path)
        metadata = doc.metadata
        doc.close()
        return metadata 