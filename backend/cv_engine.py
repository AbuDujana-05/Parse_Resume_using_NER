import os
import re
from pathlib import Path
import cv2
import numpy as np
import pytesseract
import docx
import pptx

try:
    from pdf2image import convert_from_path
except ImportError:
    convert_from_path = None

try:
    import pypdfium2 as pdfium
except ImportError:
    pdfium = None


def ensure_tesseract_available() -> None:
    """Configure a standard Windows install and fail clearly when OCR is absent."""
    configured = os.environ.get('TESSERACT_CMD')
    candidates = [
        configured,
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            pytesseract.pytesseract.tesseract_cmd = candidate
            break
    try:
        pytesseract.get_tesseract_version()
    except pytesseract.TesseractNotFoundError as exc:
        raise RuntimeError(
            'Tesseract OCR is required to parse image resumes. Install Tesseract OCR '
            'or set the TESSERACT_CMD environment variable to tesseract.exe.'
        ) from exc


def clean_ocr_text(text: str) -> str:
    """Correct a small set of recurring AI-resume OCR confusions."""
    return re.sub(r'\bAl(?=\s*(?:&\s*ML\b|&\s*Data\b|Fundamentals\b|Tools\b|/ML\b))', 'AI', text)

def extract_text_from_file(file_path: str, file_type: str) -> str:
    """Route document to appropriate Computer Vision / layout extractor."""
    ft = file_type.lower()
    if ft == 'pdf':
        return extract_text_from_pdf(file_path)
    elif ft in ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff']:
        return extract_text_from_image(file_path)
    elif ft == 'docx':
        return extract_text_from_docx(file_path)
    elif ft == 'pptx':
        return extract_text_from_pptx(file_path)
    elif ft in ['txt', 'md']:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    else:
        return ""

def extract_text_from_pdf(file_path: str) -> str:
    """Convert PDF pages to images and process with CV spatial layout engine."""
    images = []
    
    # Method 1: Try pdf2image (poppler)
    if convert_from_path is not None:
        try:
            pages = convert_from_path(file_path)
            for page in pages:
                open_cv_image = np.array(page)
                open_cv_image = open_cv_image[:, :, ::-1].copy()
                images.append(open_cv_image)
        except Exception:
            images = []
            
    # Method 2: Seamless fallback to pypdfium2 (built-in, no external poppler needed)
    if not images and pdfium is not None:
        try:
            pdf = pdfium.PdfDocument(file_path)
            for page in pdf:
                pil_image = page.render(scale=2).to_pil()
                open_cv_image = np.array(pil_image)
                if len(open_cv_image.shape) == 3:
                    open_cv_image = open_cv_image[:, :, ::-1].copy()
                images.append(open_cv_image)
        except Exception as e:
            return f"[ERROR] PDF processing failed: {e}"

    if not images:
        return "[NOTICE] Could not render PDF pages."

    extracted_pages = []
    for img in images:
        page_text = extract_text_from_image(img)
        if page_text:
            extracted_pages.append(page_text)
            
    return "\n\n".join(extracted_pages)

def extract_text_from_image(image_path_or_array) -> str:
    """
    Core Computer Vision Layout Engine:
    1. Grayscale & Otsu's Binarization
    2. Morphological dilation with rectangular kernel
    3. Contour detection for text block identification
    4. Two-pass spatial sorting (top-to-bottom, left-to-right) to preserve column order
    5. OCR text extraction per block
    """
    ensure_tesseract_available()

    if isinstance(image_path_or_array, str):
        img = cv2.imread(image_path_or_array)
    else:
        img = image_path_or_array
        
    if img is None:
        return ""
        
    # Step 1: Grayscale conversion
    if len(img.shape) == 3:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    else:
        gray = img
        
    # Step 2: Otsu's thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # A full-page pass best preserves the reading order of ordinary one-column
    # resumes, including the Education line this project needs to classify.
    try:
        full_page_text = pytesseract.image_to_string(gray, config='--psm 3').strip()
    except Exception:
        full_page_text = ''

    # Step 3: Morphological transformations to merge letters into paragraph/block regions
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (18, 5))
    dilated = cv2.dilate(thresh, kernel, iterations=1)
    
    # Step 4: Contour Detection
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    bounding_boxes = [cv2.boundingRect(c) for c in contours if cv2.boundingRect(c)[2] > 20 and cv2.boundingRect(c)[3] > 10]
    
    if not bounding_boxes:
        # Fallback to direct OCR on full image if no distinct blocks found
        try:
            return clean_ocr_text(full_page_text)
        except Exception:
            return ""
        
    # Step 5: Spatial Sorting
    # Group bounding boxes into horizontal rows by Y-proximity (< 15px vertical threshold)
    sorted_by_y = sorted(bounding_boxes, key=lambda b: b[1])
    rows = []
    current_row = [sorted_by_y[0]]
    
    for box in sorted_by_y[1:]:
        if abs(box[1] - current_row[0][1]) < 18:
            current_row.append(box)
        else:
            rows.append(current_row)
            current_row = [box]
    if current_row:
        rows.append(current_row)
        
    # Sort boxes left-to-right within each row to prevent multi-column bleed
    sorted_boxes = []
    for row in rows:
        row.sort(key=lambda b: b[0])
        sorted_boxes.extend(row)
        
    # Step 6: OCR Extraction per bounded ROI
    extracted_text = []
    for x, y, w, h in sorted_boxes:
        roi = gray[max(0, y-2):min(gray.shape[0], y+h+2), max(0, x-2):min(gray.shape[1], x+w+2)]
        try:
            text = pytesseract.image_to_string(roi, config='--psm 6').strip()
            if text:
                extracted_text.append(text)
        except Exception:
            pass
            
    # Prefer full-page OCR when it has comparable coverage; this avoids changing
    # the sequence of headings, education, and institution text on standard CVs.
    roi_text = "\n".join(extracted_text)
    if full_page_text and len(full_page_text.split()) >= len(roi_text.split()) * 0.75:
        return clean_ocr_text(full_page_text)

    # If ROI OCR failed, fall back to the full-image result.
    if not extracted_text:
        return clean_ocr_text(full_page_text)
            
    return clean_ocr_text(roi_text)

def extract_text_from_docx(file_path: str) -> str:
    """Extract semantic paragraphs and tables from DOCX resumes."""
    try:
        doc = docx.Document(file_path)
        paragraphs = [para.text.strip() for para in doc.paragraphs if para.text.strip()]
        
        # Also extract table cells (common in 2-column DOCX resumes)
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    paragraphs.append(row_text)
                    
        return "\n".join(paragraphs)
    except Exception as e:
        return f"[ERROR] DOCX extraction failed: {e}"

def extract_text_from_pptx(file_path: str) -> str:
    """Extract text shapes from PPTX resumes."""
    try:
        prs = pptx.Presentation(file_path)
        text = []
        for slide in prs.slides:
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    text.append(shape.text.strip())
        return "\n".join(text)
    except Exception as e:
        return f"[ERROR] PPTX extraction failed: {e}"
