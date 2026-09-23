import os
import time
import chromadb

print("Testing ChromaDB connection...")
start = time.time()
try:
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
    client = chromadb.PersistentClient(path=path)
    print(f"Client created ({time.time() - start:.2f}s)")
    
    # Check legal_knowledge_v2 (NVIDIA NIM) or legal_knowledge
    try:
        coll = client.get_collection("legal_knowledge_v2")
        print(f"Collection 'legal_knowledge_v2' retrieved. Count: {coll.count()}")
    except Exception:
        coll = client.get_collection("legal_knowledge")
        print(f"Collection 'legal_knowledge' retrieved. Count: {coll.count()}")
    print("SUCCESS")
except Exception as e:
    print(f"FAILED: {e}")
