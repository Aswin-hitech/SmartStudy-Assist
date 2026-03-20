import os
import requests
import mimetypes

def extract_text_from_file(file_stream, filename):
    """
    Sends the file to OCR.space API and returns the extracted text.
    Handles images (PNG, JPG) and PDFs.
    """
    api_key = os.getenv("OCR_API_KEY")
    if not api_key or api_key == "your_key_here":
        raise ValueError("OCR_API_KEY is not configured properly in .env")

    # The OCR.space API endpoint
    url = "https://api.ocr.space/parse/image"

    # Reset file pointer just in case
    file_stream.seek(0)
    
    # Guess mime type based on filename
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = "application/octet-stream"

    # Payload
    payload = {
        "apikey": api_key,
        "language": "eng",
        # isOverlayRequired=False speeds it up. scale=True improves accuracy.
        "isOverlayRequired": "false",
        "scale": "true",
        "OCREngine": "2" # Engine 2 usually better for documents
    }
    
    # Files
    files = {
        "file": (filename, file_stream, content_type)
    }

    try:
        response = requests.post(url, data=payload, files=files)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("IsErroredOnProcessing"):
            error_message = result.get("ErrorMessage", ["Unknown OCR error"])[0]
            raise RuntimeError(f"OCR Error: {error_message}")
            
        # Parse extracted text
        parsed_results = result.get("ParsedResults", [])
        extracted_text = "\n".join([page.get("ParsedText", "") for page in parsed_results])
        
        return extracted_text.strip()
        
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"OCR Request failed: {str(e)}")
