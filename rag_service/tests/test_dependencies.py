"""
Test script to verify all active RAG dependencies are installed correctly
"""

import sys

def test_imports():
    """Test all required imports for active RAG features"""
    print("=" * 60)
    print("Testing Active LegalAi RAG Dependencies")
    print("=" * 60 + "\n")
    
    all_ok = True
    
    # Core Web & API
    print("API & Web Services:")
    for mod, name in [("fastapi", "FastAPI"), ("uvicorn", "Uvicorn"), ("requests", "Requests"), ("dotenv", "python-dotenv")]:
        try:
            __import__(mod)
            print(f"  [OK] {name} installed")
        except ImportError:
            print(f"  [FAIL] {name} not found")
            all_ok = False

    # Vector Database
    print("\nVector Database:")
    try:
        import chromadb
        print("  [OK] ChromaDB installed")
    except ImportError:
        print("  [FAIL] ChromaDB not found")
        all_ok = False

    # PDF & Document Processing
    print("\nPDF Processing:")
    try:
        import pypdf
        print("  [OK] pypdf installed")
    except ImportError:
        print("  [FAIL] pypdf not found")
        all_ok = False

    try:
        import fitz  # PyMuPDF
        print("  [OK] PyMuPDF (fitz) installed")
    except ImportError:
        print("  [FAIL] PyMuPDF not found")
        all_ok = False

    # OCR Support
    print("\nOCR Support:")
    try:
        import pytesseract
        print("  [OK] Pytesseract installed")
    except ImportError:
        print("  [FAIL] Pytesseract not found")
        all_ok = False

    try:
        from pdf2image import convert_from_bytes
        print("  [OK] pdf2image installed")
    except ImportError:
        print("  [FAIL] pdf2image not found")
        all_ok = False

    print("\n" + "=" * 60)
    if all_ok:
        print("All active dependencies installed and verified!")
    else:
        print("Some dependencies are missing. Run: pip install -r rag_service/requirements.txt")
    print("=" * 60)
    return all_ok

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
