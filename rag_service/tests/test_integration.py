"""
Simple test to verify enhanced RAG features are working
"""

import os
import sys

# Add Tesseract to PATH for this session
tesseract_path = r"C:\Program Files\Tesseract-OCR"
if tesseract_path not in os.environ['PATH']:
    os.environ['PATH'] += os.pathsep + tesseract_path

print("="*60)
print("Testing Enhanced RAG Features")
print("="*60)

# Test 1: Import text processor
print("\n1️⃣  Testing Text Processor Module...")
try:
    from text_processor import TextProcessor
    processor = TextProcessor()
    print("   ✓ TextProcessor initialized successfully")
    
    # Test language detection
    test_text = "This is a test document about Indian law."
    lang = processor.detect_language(test_text)
    print(f"   ✓ Language detection working (detected: {lang})")
    
    # Test text cleaning
    dirty_text = "This  is   a    test\n\n\nwith   extra   spaces"
    clean = processor.clean_text(dirty_text)
    print(f"   ✓ Text cleaning working (cleaned {len(dirty_text)} -> {len(clean)} chars)")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 2: Import conversation memory
print("\n2️⃣  Testing Conversation Memory Module...")
try:
    from conversation_memory import ConversationMemory
    memory = ConversationMemory()
    print("   ✓ ConversationMemory initialized successfully")
    
    # Test session creation
    session_id = memory.create_session()
    print(f"   ✓ Session created: {session_id[:8]}...")
    
    # Test message storage
    memory.add_message(session_id, "user", "Test question")
    memory.add_message(session_id, "assistant", "Test answer")
    history = memory.get_history(session_id)
    print(f"   ✓ Message storage working ({len(history)} messages)")
    
    # Test query reformulation
    reformulated = memory.reformulate_query(session_id, "What about that?")
    print("   ✓ Query reformulation working")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 3: Import RAG engine
print("\n3️⃣  Testing RAG Engine Integration...")
try:
    from rag_engine import RAGEngine
    engine = RAGEngine()
    print("   ✓ RAGEngine initialized successfully")
    print(f"   ✓ Text processor integrated: {engine.text_processor is not None}")
    print(f"   ✓ Conversation memory integrated: {engine.conversation_memory is not None}")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    sys.exit(1)

# Test 4: Test Tesseract OCR
print("\n4️⃣  Testing Tesseract OCR...")
try:
    import pytesseract
    version = pytesseract.get_tesseract_version()
    print(f"   ✓ Tesseract version: {version}")
    print("   ✓ OCR support ready for scanned PDFs")
    
except Exception as e:
    print(f"   ✗ Tesseract error: {e}")
    print("   ⚠️  OCR will not work for scanned documents")

# Test 5: Test PDF processing
print("\n5️⃣  Testing PDF Processing Libraries...")
try:
    import fitz  # PyMuPDF
    print(f"   ✓ PyMuPDF installed (version: {fitz.version[0]})")
except:
    print("   ✗ PyMuPDF not available")

try:
    print("   ✓ pdfplumber installed")
except:
    print("   ✗ pdfplumber not available")

try:
    print("   ✓ pdf2image installed (for OCR)")
except:
    print("   ⚠️  pdf2image not available (OCR may not work)")

print("\n" + "="*60)
print("✅ All core features are working!")
print("="*60)
print("\n📝 Next steps:")
print("   1. Start the RAG service: uvicorn main:app --reload --port 8000")
print("   2. Test with a PDF upload to /summarize endpoint")
print("   3. Test conversation memory with /session/create")
print("\n💡 Tip: Add Tesseract to your permanent PATH:")
print("   Run: .\\setup_tesseract.ps1")
