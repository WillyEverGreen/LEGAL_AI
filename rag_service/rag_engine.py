
import os
import re
import time
import pathlib
from urllib.parse import quote
from typing import Any
from dotenv import load_dotenv

import chromadb
import requests
from chromadb.utils import embedding_functions
from conversation_memory import ConversationMemory
from text_processor import TextProcessor

# Load environment from root if present
base_path = pathlib.Path(__file__).parent.parent
load_dotenv(dotenv_path=base_path / ".env")


class RAGEngine:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY")
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
        # Priority: GROQ (ultra-fast ~0.8s) -> NVIDIA NIM -> OpenRouter
        if self.groq_api_key:
            self.api_key = self.groq_api_key
            self.provider = "groq"
            self.model_name = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
            self.model_legal = os.getenv("GROQ_MODEL_LEGAL", "qwen/qwen3.8-27b")
            self.model_simple = os.getenv("GROQ_MODEL_SIMPLE", "qwen/qwen3.8-27b")
            print(f"[RAGEngine] Using GROQ Lightning-Fast API. Model: {self.model_name}")
        elif self.nvidia_api_key:
            self.api_key = self.nvidia_api_key
            self.provider = "nvidia"
            self.model_name = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct")
            self.model_legal = os.getenv("NVIDIA_MODEL_LEGAL", "meta/llama-3.2-11b-vision-instruct")
            self.model_simple = os.getenv("NVIDIA_MODEL_SIMPLE", "meta/llama-3.2-11b-vision-instruct")
            print(f"[RAGEngine] Using NVIDIA NIM API. Models: {self.model_name}")
        else:
            self.api_key = self.openrouter_api_key
            self.provider = "openrouter"
            self.model_name = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")
            self.model_legal = os.getenv("OPENROUTER_MODEL_LEGAL", "nvidia/nemotron-orchestrator-8b")
            self.model_simple = os.getenv("OPENROUTER_MODEL_SIMPLE", "mistralai/mistral-7b-instruct")
            print(f"[RAGEngine] Using OpenRouter API. Models: {self.model_name}")

        if not self.api_key:
            print("[RAGEngine] [WARN] No API Key found (Groq, NVIDIA, or OpenRouter). LLM features disabled.")

        # Initialize Enhanced Text Processor
        self.text_processor = TextProcessor()
        
        # Initialize Conversation Memory
        self.conversation_memory = ConversationMemory()
        # Simple in-memory response cache
        self._cache: dict[str, dict[str, Any]] = {}

        # Initialize ChromaDB Client
        base_dir = os.path.dirname(os.path.abspath(__file__))
        chroma_path = os.path.join(base_dir, "chroma_db")
        
        class NvidiaEmbeddingFunction(chromadb.EmbeddingFunction):
            def __init__(self, api_key):
                self.api_key = api_key
                self.url = "https://integrate.api.nvidia.com/v1/embeddings"
                self.model = os.getenv("NVIDIA_EMBED_MODEL", "nvidia/nemotron-3-embed-1b")
            
            def __call__(self, input: list[str]) -> list[list[float]]:
                headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
                cleaned = [t if (t and t.strip()) else "N/A" for t in input]
                data = {"input": cleaned, "model": self.model}
                response = requests.post(self.url, headers=headers, json=data, timeout=30)
                if response.status_code != 200:
                    raise Exception(f"NVIDIA Embedding Error: {response.text}")
                return [item["embedding"] for item in response.json()["data"]]

        try:
            self.db_client = chromadb.PersistentClient(path=chroma_path)
            
            # Use NVIDIA Cloud Embeddings to save RAM (removes need for local models)
            if self.nvidia_api_key:
                self.ef = NvidiaEmbeddingFunction(self.nvidia_api_key)
                # Use v2 collection for the NVIDIA NIM embedding dimensions (2048)
                collection_name = "legal_knowledge_v2"
            else:
                self.ef = embedding_functions.DefaultEmbeddingFunction()
                collection_name = "legal_knowledge_default"
                
            try:
                self.collection = self.db_client.get_collection(name=collection_name)
            except Exception:
                self.collection = self.db_client.get_or_create_collection(name=collection_name)
            print(f"[RAGEngine] Connected to Vector DB [{collection_name}]. ({self.collection.count()} docs)")
            
            # Simple check: If collection is empty, we would normally ingest here.
            # For now, we prioritize stability and will let the user upload files.
            
        except Exception as e:
             print(f"[RAGEngine] [WARN] Vector DB Connection Error: {e}")
             self.collection = None

    def _classify_query(self, query: str) -> str:
        """
        Classifies query into:
        - 'capability': query about system capabilities / features
        - 'greeting': friendly social interaction (hi, hello, thanks, bye)
        - 'legal': Indian legal statutes, cases, disputes, rights, or procedures requiring RAG
        - 'general': general topics (science, tech, coding, writing, history, everyday questions)
        """
        q = query.lower().strip()
        # Normalize informal abbreviations
        q_norm = re.sub(r'\bu\b', 'you', q)
        q_norm = re.sub(r'\br\b', 'are', q_norm)
        q_norm = re.sub(r'\bur\b', 'your', q_norm)
        q_norm = re.sub(r'\bplz\b', 'please', q_norm)
        
        # 1. Capability checks
        capability_patterns = [
            'what can you do', 'what do you do', 'how can you help',
            'what are your features', 'capabilities', 'tell me about yourself',
            'who made you', 'kya kar sakte ho', 'aap kya kar sakte', 'kaise madad kar sakte',
            'what are you', 'who are you'
        ]
        if any(p in q_norm for p in capability_patterns):
            return 'capability'

        # 2. Pure greetings
        pure_greeting_words = ['hello', 'hi', 'hey', 'namaste', 'pranam', 'halo', 'thanks', 'thank you', 'dhanyavad', 'shukriya', 'good morning', 'good afternoon', 'good evening', 'bye', 'goodbye']
        words = q_norm.split()
        if len(words) <= 3 and any(w in pure_greeting_words for w in [q_norm, ' '.join(words[:2]), words[0]]):
            explicit_legal = ['section', 'bns', 'ipc', 'crpc', 'murder', 'theft', 'cheating', 'fir', 'bail', 'act', 'law']
            if not any(el in q_norm for el in explicit_legal):
                return 'greeting'

        # 3. Explicit Legal Statute Names & Acts
        legal_statute_names = [
            'bns', 'ipc', 'crpc', 'bnss', 'bsa', 'cpc', 'constitution', 'it act', 
            'bharatiya nyaya', 'bharatiya nagarik', 'bharatiya sakshya', 'indian penal code',
            'code of criminal procedure', 'posh act', 'pocso', 'rti', 'motor vehicle',
            'consumer protection', 'arbitration', 'negotiable instruments', 'ni act',
            'companies act', 'contract act', 'hindu marriage', 'special marriage',
            'transfer of property', 'evidence act', 'limitation act', 'drts', 'nclt',
            'rera', 'ndps'
        ]
        if any(re.search(rf'\b{re.escape(name)}\b', q_norm) for name in legal_statute_names):
            return 'legal'

        # Legal concepts, procedure, rights, offences & remedies
        legal_terms = [
            'section', 'sec.', 'article', 'statute', 'ordinance', 'amendment',
            'penalty', 'punishment', 'imprisonment', 'fine', 'bail', 'anticipatory bail',
            'fir', 'police station', 'police complaint', 'complaint', 'petition',
            'writ', 'habeas corpus', 'mandamus', 'quash', 'cognizable', 'non-bailable',
            'court', 'judge', 'magistrate', 'high court', 'supreme court', 'sessions court',
            'tribunal', 'advocate', 'lawyer', 'legal notice', 'draft notice', 'vakalatnama',
            'affidavit', 'tenant', 'landlord', 'rent agreement', 'lease deed', 'nda',
            'non-disclosure', 'contract', 'agreement', 'will', 'probate', 'inheritance',
            'custody', 'divorce', 'alimony', 'maintenance', 'domestic violence', 'dowry',
            'assault', 'murder', 'homicide', 'theft', 'robbery', 'dacoity', 'extortion',
            'fraud', 'cheating', 'defamation', 'forgery', 'perjury', 'cybercrime',
            'hacking', 'phishing', 'posh', 'harassment', 'consumer court', 'deficiency in service',
            'legal rights', 'can i sue', 'sue', 'lawsuit', 'jurisdiction', 'cause of action'
        ]
        if any(re.search(rf'\b{re.escape(term)}\b', q_norm) for term in legal_terms):
            return 'legal'

        # Hindi legal terminology
        hindi_legal_terms = [
            'धारा', 'कानून', 'सजा', 'दण्ड', 'जुर्माना', 'जमानत', 'मुकदमा', 'वकील',
            'अदालत', 'न्यायालय', 'पुलिस', 'शिकायत', 'तलाक', 'अपराध', 'चोरी',
            'धोखाधड़ी', 'विधिक', 'शपथ पत्र', 'किरायानामा'
        ]
        if any(term in query for term in hindi_legal_terms):
            return 'legal'

        # 4. Open-domain general topics (science, tech, coding, writing, business, etc.)
        return 'general'
    
    def _generate_statute_url(self, law: str, section: str) -> str | None:
        """Generate verified legal research URL for Indian statutes."""
        if not law and not section:
            return None
        
        law_str = str(law or "").strip()
        section_str = str(section or "").strip()
        
        # Extract clean section number
        sec_match = re.search(r'\d+[A-Z]*', section_str)
        section_num = sec_match.group() if sec_match else section_str
        
        law_lower = law_str.lower()
        
        # 1. IndiaCode direct section mappings for known statutory acts
        if section_num and section_num.isdigit():
            if 'bns' in law_lower or 'bharatiya nyaya' in law_lower:
                return f'https://www.indiacode.nic.in/show-data?actid=AC_CEN____00023_00000____00000_____&sectionno={section_num}'
            if 'ipc' in law_lower or 'indian penal code' in law_lower:
                return f'https://www.indiacode.nic.in/show-data?actid=AC_CEN_5_23_00037_186045_1523266765688&sectionId=22343&sectionno={section_num}'
            if 'it act' in law_lower or 'information technology' in law_lower:
                return f'https://www.indiacode.nic.in/show-data?actid=AC_CEN_45_76_00001_200021_1517807326986&sectionId=1643&sectionno={section_num}'
            if 'crpc' in law_lower or 'criminal procedure' in law_lower:
                return f'https://www.indiacode.nic.in/show-data?actid=AC_CEN_5_23_00006_197301_1517807320906&sectionId=1826&sectionno={section_num}'

        # 2. Indian Kanoon authoritative search URL as reliable universal fallback
        clean_terms = []
        if law_str and law_str.lower() not in ['statute', 'unknown', 'none', 'null']:
            clean_terms.append(law_str)
        if section_num and section_num.lower() not in ['none', 'null', 'unknown']:
            clean_terms.append(f"Section {section_num}")
            
        search_query = " ".join(clean_terms) if clean_terms else "Indian Law Statute"
        return f'https://indiankanoon.org/search/?formInput={quote(search_query)}'

    def _call_llm(self, messages: list[dict], max_tokens: int = 1000, timeout: int = 30, model_override: str | None = None) -> str:
        """Helper to call LLM API with retries, timeout, and provider fallback."""
        if not self.api_key:
            raise Exception("API Key missing")

        # Define prioritized providers to try
        providers_to_try = []
        if self.groq_api_key:
            providers_to_try.append(("groq", self.groq_api_key, model_override or self.model_name))
        if self.nvidia_api_key:
            nvidia_model = os.getenv("NVIDIA_MODEL", "meta/llama-3.2-11b-vision-instruct")
            providers_to_try.append(("nvidia", self.nvidia_api_key, nvidia_model))
        if self.openrouter_api_key:
            or_model = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct")
            providers_to_try.append(("openrouter", self.openrouter_api_key, or_model))

        if not providers_to_try:
            raise Exception("No active LLM provider configured.")

        last_error = None
        for prov_name, prov_key, prov_model in providers_to_try:
            if prov_name == "groq":
                url = "https://api.groq.com/openai/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {prov_key}",
                    "Content-Type": "application/json"
                }
            elif prov_name == "nvidia":
                url = "https://integrate.api.nvidia.com/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {prov_key}",
                    "Content-Type": "application/json"
                }
            else:
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {prov_key}",
                    "HTTP-Referer": os.getenv("APP_URL", "http://localhost:3000"),
                    "X-Title": "LegalAi",
                    "Content-Type": "application/json"
                }

            data = {
                "model": prov_model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": max_tokens
            }

            for attempt in range(2):
                try:
                    response = requests.post(url, headers=headers, json=data, timeout=timeout)
                    if response.status_code == 200:
                        result = response.json()
                        if 'choices' in result and len(result['choices']) > 0:
                            content = result['choices'][0]['message'].get('content', '')
                            if content:
                                return content
                            return "Error: Received empty content from LLM."
                        raise Exception(f"Unexpected response format: {result}")
                    
                    err_text = response.text
                    print(f"[RAGEngine] {prov_name} attempt {attempt+1} error ({response.status_code}): {err_text[:160]}")
                    last_error = f"{prov_name} Error {response.status_code}: {err_text}"
                    
                    # Retry on 429, 500, 502, 503, 504
                    if response.status_code in [429, 500, 502, 503, 504]:
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    else:
                        break
                except requests.exceptions.Timeout:
                    print(f"[RAGEngine] {prov_name} timed out after {timeout}s")
                    last_error = f"{prov_name} timed out (> {timeout}s)"
                    time.sleep(0.5)
                except Exception as e:
                    print(f"[RAGEngine] {prov_name} attempt {attempt+1} failed: {e}")
                    last_error = str(e)
                    time.sleep(0.5)

        raise Exception(last_error or "LLM generation failed after retries")

    def _clean_text(self, text: str) -> str:
        """Cleans extracted text by normalizing whitespace."""
        return re.sub(r'\s+', ' ', text).strip()

    def _chunk_text(self, text: str, chunk_size: int = 6000) -> list[str]:
        """Splits text into chunks of approx chunk_size characters (roughly 1500 tokens)."""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunks.append(text[i:i + chunk_size])
        return chunks

    async def summarize(self, file_content: bytes, filename: str) -> str:
        """
        Advanced Summarization Pipeline: Extract -> Clean -> Chunk -> Summarize Parts -> Combine.
        Uses enhanced text processor with multi-modal extraction and 12-stage cleaning.
        """
        print(f"[RAGEngine] Processing file: {filename} ({len(file_content)} bytes)")
        
        full_text = ""
        extraction_method = "unknown"
        
        try:
            # 1. Extract Text (Enhanced with multi-modal support)
            if filename.lower().endswith(".pdf"):
                full_text, extraction_method = self.text_processor.extract_text_from_pdf(
                    file_content, filename, max_ocr_pages=100
                )
                
                if extraction_method == "failed":
                    return full_text  # Error message
            else:
                full_text = file_content.decode("utf-8", errors="ignore")
                extraction_method = "text"

            if not full_text.strip():
                return "Error: Could not extract text from document."

            # 2. Clean with 12-stage pipeline
            cleaned_text = self.text_processor.clean_text(full_text)
            print(f"[RAGEngine] Extracted {len(cleaned_text)} characters using {extraction_method}.")
            
            # 3. Detect language
            detected_lang = self.text_processor.detect_language(cleaned_text)
            print(f"[RAGEngine] Detected language: {detected_lang}")

            # 3. Chunk
            chunks = self._chunk_text(cleaned_text, chunk_size=6000)
            print(f"[RAGEngine] Created {len(chunks)} chunks.")

            if not self.api_key:
                return f"LLM not configured. Extracted {len(cleaned_text)} chars. Start: {cleaned_text[:500]}..."

            # 4. Summarize Chunks
            chunk_summaries = []
            
            # SAFEGUARD: Limit chunks to avoid timeouts (Max 4 chunks)
            max_chunks = min(4, len(chunks))
            for i, chunk in enumerate(chunks[:max_chunks]):
                print(f"[RAGEngine] Summarizing chunk {i+1}/{max_chunks}...")
                prompt = (
                    "You are a legal AI assistant.\n"
                    "Summarize the following legal text with:\n"
                    "- Key facts\n"
                    "- Legal issues\n"
                    "- Sections / Acts mentioned (ONLY if explicitly present)\n"
                    "- Court observations (if any)\n\n"
                    "Rules:\n"
                    "- Do NOT infer missing sections\n"
                    "- Do NOT hallucinate citations\n"
                    "- Use neutral legal language\n"
                    "- Bullet points preferred\n\n"
                    f"Text:\n{chunk}"
                )
                try:
                    summary = self._call_llm([{"role": "user", "content": prompt}], max_tokens=600)
                    chunk_summaries.append(summary)
                except Exception as e:
                    print(f"[RAGEngine] Chunk {i+1} failed: {e}")
            
            if not chunk_summaries:
                return "Error: Failed to generate any summaries."

            # 5. Combine -> Final Structured Summary
            print("[RAGEngine] Generating Final Structured Summary...")
            combined_text = "\n\n".join(chunk_summaries)
            
            final_system_prompt = (
                "You are an expert Legal Architect AI. "
                "Using the provided summaries of a legal document, create a single, Master Structured Summary. "
                "Format strictly in Markdown with the following sections:\n"
                "### 📌 Executive Summary\n(A concise overview)\n\n"
                "### 🏷 Case Classification\n"
                "- Nature: Criminal / Civil / Constitutional / Administrative\n"
                "- Cyber Law Applicable: Yes / No\n"
                "- Era: Pre-IT Act / Post-IT Act\n\n"
                "### 📑 Key Legal Sections Referenced\n(List specific Acts and Sections)\n\n"
                "### ⚖️ Critical Observations & Findings\n(Key points, obligations, facts)\n\n"
                "### 📚 Citations & Case Law\n(If any mentioned)\n\n"
                "### 🔮 Legal Implications\n(What this means for the parties)"
            )

            final_summary = self._call_llm([
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": f"Summaries:\n{combined_text}"}
            ], max_tokens=1500)

            return final_summary

        except Exception as e:
            print(f"[RAGEngine] Summarization Pipeline Error: {e}")
            return f"Failed to summarize document: {e!s}"

    async def compare_clauses(self, text1: str, text2: str) -> dict:
        """
        Compares two legal clauses and returns a structured JSON analysis.
        """
        if not self.api_key:
            return {"error": "API Key missing"}

        system_prompt = (
            "You are an expert Legal Analyst specializing in Indian Law (IPC vs BNS). "
            "Compare the two provided legal clauses deeply. "
            "You MUST return the result in valid JSON format with the following structure:\n"
            "{\n"
            '  "change_type": "Renumbered / Modified / New / Removed",\n'
            '  "legal_impact": "A concise summary of the legal impact...",\n'
            '  "penalty_difference": "No substantive change / Increased / Decreased",\n'
            '  "key_changes": ["Bullet point 1", "Bullet point 2"],\n'
            '  "verdict": "Minor procedural change" (or "Major substantive change")\n'
            "}\n"
            "Do not include any Markdown formatting (like ```json). Just the raw JSON string."
        )

        user_query = f"Clause A (Old/IPC): {text1}\n\nClause B (New/BNS): {text2}"

        try:
            response_text = self._call_llm([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ])
            
            # Clean up potential markdown code blocks if the LLM ignores instructions
            cleaned_text = response_text.replace("```json", "").replace("```", "").strip()
            
            import json
            try:
                # Attempt to parse JSON (handling potential trailing commas)
                cleaned_text = re.sub(r',\s*}', '}', cleaned_text)
                analysis_json = json.loads(cleaned_text)
                return analysis_json
            except json.JSONDecodeError:
                print(f"[RAGEngine] JSON Parse Error. Raw: {cleaned_text}")
                # Fallback to simple text if JSON fails
                return {
                    "change_type": "Analysis Generated",
                    "legal_impact": cleaned_text,
                    "penalty_difference": "See analysis",
                    "key_changes": ["Could not parse structured data"],
                    "verdict": "See details"
                }

        except Exception as e:
            print(f"[RAGEngine] Compare Error: {e}")
            return {"error": str(e)}

    async def query(self, query: str, language: str = "en", arguments_mode: bool = False, analysis_mode: bool = False, session_id: str | None = None) -> dict[str, Any]:
        """
        Semantic Search + LLM Generation with Conversation Memory.
        
        Args:
            query: User's question
            language: 'en' or 'hi'
            arguments_mode: Generate balanced arguments
            analysis_mode: Generate neutral analysis
            session_id: Optional session ID for conversation memory
        """
        # Handle conversation memory and query reformulation
        original_query = query
        if session_id:
            # SAFEGUARD: Do not reformulate very long queries (e.g. pasted text)
            if len(query) < 300:
                query = self.conversation_memory.reformulate_query(session_id, query)
                if query != original_query:
                    print(f"[RAGEngine] Query reformulated: '{original_query}' -> '{query}'")
        
        # Safe print for Windows consoles (handles Hindi chars)
        safe_query = query.encode('ascii', 'replace').decode('ascii')
        print(f"[RAGEngine] Semantic Query: {safe_query} (Lang: {language})")

        LONG_TRIGGERS = ["explain", "detail", "elaborate", "analysis", "ingredients"]
        is_long = any(t in query.lower() for t in LONG_TRIGGERS)

        # 0. Smart Routing: rule-based fast path for capabilities, greetings, and general open-domain topics
        query_type = self._classify_query(query)
        if query_type == 'capability':
            intro_answer = (
                "### Welcome to **LegalAi** — Your Intelligent Indian Law Research & Advisory Partner\n\n"
                "I am an advanced legal intelligence system specialized in Indian jurisprudence, statutory transitions, regulatory compliance, and automated drafting, powered by ultra-fast inference.\n\n"
                "#### Core Capabilities:\n\n"
                "1. **Statutory Intelligence & Penal Code Transitions**\n"
                "   • Real-time analysis across the **Bharatiya Nyaya Sanhita (BNS, 2023)**, **Indian Penal Code (IPC, 1860)**, **BNSS / CrPC**, and **Information Technology Act, 2000**.\n"
                "   • Exact section comparisons, statutory shifts, and penalty changes.\n\n"
                "2. **Authoritative Precedents & Citations**\n"
                "   • Rulings backed by landmark Supreme Court judgments, ratios, and verifiable links to IndiaCode & Indian Kanoon.\n\n"
                "3. **Balanced Legal Arguments & Neutral Analysis**\n"
                "   • Prosecution arguments, defense perspectives, and balanced judicial evaluations.\n\n"
                "4. **Automated Legal Drafting**\n"
                "   • Generate formal Legal Demand Notices, NDAs, Rental Agreements, Employment Contracts, and POSH complaints.\n\n"
                "5. **Legal Advisory & Regulatory Problem Solving**\n"
                "   • Practical guidance on commercial compliance, cyber regulations, consumer disputes, and legal rights.\n\n"
                "6. **Document Summarization & PDF Briefs**\n"
                "   • Extract critical clauses from contracts, court petitions, and orders with downloadable PDF research briefs.\n\n"
                "Ask any legal question, describe a dispute or situation, or cite a section to get started!"
            )
            return {
                "answer": intro_answer,
                "citations": [],
                "related_judgments": [],
                "neutral_analysis": None,
                "arguments": None
            }

        if query_type == 'greeting':
            try:
                greeting_prompt = (
                    "You are LegalAi, a prestigious AI legal assistant specializing in Indian Law. "
                    "Respond to the user's greeting warmly, professionally, and concisely in 2 sentences. "
                    "Invite them to ask about Indian statutes (BNS, IPC), legal scenarios, contracts, or statutory compliance."
                )
                routing_response = self._call_llm([
                    {"role": "system", "content": greeting_prompt},
                    {"role": "user", "content": query}
                ], max_tokens=150, timeout=12, model_override=self.model_simple).strip()
                if routing_response:
                    return {
                        "answer": routing_response,
                        "citations": [],
                        "related_judgments": [],
                        "neutral_analysis": None,
                        "arguments": None
                    }
            except Exception as e:
                print(f"[RAGEngine] Simple greeting fallback: {e}")
                return {
                    "answer": "Hello! I am **LegalAi**, your Indian legal assistant. How can I assist you with Indian law, statutes (BNS/IPC), or legal drafting today?",
                    "citations": [],
                    "related_judgments": [],
                    "neutral_analysis": None,
                    "arguments": None
                }

        if query_type == 'general':
            print(f"[RAGEngine] Handling General Topic query: '{safe_query}'")
            general_system_prompt = (
                "You are LegalAi, a dedicated Indian Legal AI Assistant and research partner.\n\n"
                "CORE IDENTITY & DIRECTIVES:\n"
                "1. Maintain your primary persona and authority as LegalAi, firmly rooted in Indian law, jurisprudence, and regulatory knowledge.\n"
                "2. When answering broader topics (such as workplace scenarios, commercial/business decisions, technology/cyber matters, property, agreements, or everyday situations), provide a clear, helpful answer while framing the response through a legal, regulatory, compliance, or rights-management perspective under Indian legal standards.\n"
                "3. If the user asks a pure general knowledge or educational question (e.g., science or history), answer accurately and concisely with professional poise, maintaining your identity as LegalAi and offering legal or statutory context where relevant.\n"
                "4. Structure answers with clear headings, bullet points, and authoritative guidance in Markdown format.\n"
                "5. Always maintain a professional, sharp, and helpful legal counsel demeanor."
            )
            if language == "hi":
                general_system_prompt += (
                    "\n\nभाषा निर्देश:\n- अपना उत्तर पूर्णतः हिंदी (देवनागरी लिपि) में दें।\n- कानूनी और तकनीकी शब्दों का सटीक विधिक अर्थ स्पष्ट रखें।"
                )

            # Check cache
            cache_key = f"gen::{language}|{query.strip()}"
            if cache_key in self._cache:
                cached = self._cache[cache_key]
                return {
                    "answer": cached.get("answer", ""),
                    "citations": [],
                    "related_judgments": [],
                    "neutral_analysis": None,
                    "arguments": None
                }

            messages = [
                {"role": "system", "content": general_system_prompt},
            ]
            if session_id:
                history = self.conversation_memory.get_history(session_id, max_messages=4)
                for msg in history[:-1]:
                    messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": query})

            try:
                raw_answer = self._call_llm(messages, max_tokens=1500, timeout=25, model_override=self.model_simple)
                self._cache[cache_key] = {"answer": raw_answer}
                return {
                    "answer": raw_answer,
                    "citations": [],
                    "related_judgments": [],
                    "neutral_analysis": None,
                    "arguments": None
                }
            except Exception as e:
                print(f"[RAGEngine] General topic LLM error: {e}")
                return {
                    "answer": f"I encountered a temporary error while processing your request: {e}",
                    "citations": [],
                    "related_judgments": [],
                    "neutral_analysis": None,
                    "arguments": None
                }

        context_text = ""
        citations = []
        related_judgments = []
        
        # 0.5 Cross-Lingual Search Optimization
        # If language is Hindi, translate query to English for better Vector Search recall
        search_query = query
        if language == 'hi':
            try:
                print("[RAGEngine] Translating query to English for Search...")
                translation_prompt = f"Translate the following Hindi legal query to precise English legal terms for a database search. Output ONLY the English translation.\nHindi: {query}"
                translated_query = self._call_llm([{"role": "user", "content": translation_prompt}], max_tokens=100).strip()
                safe_translated = translated_query.encode('ascii', 'replace').decode('ascii')
                safe_original = query.encode('ascii', 'replace').decode('ascii')
                print(f"[RAGEngine] Translated: '{safe_original}' -> '{safe_translated}'")
                search_query = translated_query
            except Exception as e:
                print(f"[RAGEngine] Translation failed: {e}. Using original query.")

        # 1. Retrieve from Vector DB (with Hybrid Exact Section Lookup)
        try:
            print(f"[RAGEngine] Starting Vector Search for '{search_query}'...", flush=True)
            
            # Exact section matching for statutory precision
            exact_docs = []
            exact_metas = []
            sec_match = re.search(r'\b(?:section|sec\.?|s\.)\s*(\d+[A-Z]*)', search_query, re.I)
            sec_num = sec_match.group(1) if sec_match else None
            if not sec_num:
                num_law_match = re.search(r'\b(\d+[A-Z]*)\s+(?:bns|ipc|crpc|act)\b', search_query, re.I)
                sec_num = num_law_match.group(1) if num_law_match else None

            if sec_num and self.collection:
                for sec_field in ['bns_section', 'ipc_section', 'section']:
                    try:
                        res_exact = self.collection.get(where={sec_field: sec_num})
                        if res_exact and res_exact.get('documents'):
                            print(f"[RAGEngine] Hybrid match: Found exact {sec_field}={sec_num}")
                            for d, m in zip(res_exact['documents'], res_exact['metadatas']):
                                exact_docs.append(d)
                                exact_metas.append(m)
                            break
                    except Exception as ex:
                        print(f"[RAGEngine] Exact section lookup error: {ex}")

            search_cache_key = f"search::{search_query}"
            if search_cache_key in self._cache:
                 print("[RAGEngine] Using Cached Search Results.")
                 results = self._cache[search_cache_key]
            elif self.collection:
                if self.ef:
                    query_embs = self.ef([search_query])
                    results = self.collection.query(
                        query_embeddings=query_embs,
                        n_results=5,
                        include=["documents", "metadatas", "distances"]
                    )
                else:
                    results = self.collection.query(
                        query_texts=[search_query],
                        n_results=5,
                        include=["documents", "metadatas", "distances"]
                    )
                self._cache[search_cache_key] = results
                print(f"[RAGEngine] Vector Search Complete. Found: {len(results['documents'][0])} docs", flush=True)
                
                raw_docs = results['documents'][0]
                raw_metas = results['metadatas'][0]
                raw_dists = results['distances'][0]

                # Merge exact section matches first, followed by relevant vector matches
                all_candidates = []
                for d, m in zip(exact_docs, exact_metas):
                    all_candidates.append((d, m, 0.0))  # 0 distance for exact match

                for d, m, dist in zip(raw_docs, raw_metas, raw_dists):
                    # Strict distance threshold to reject irrelevant noise
                    if dist <= 0.88:
                        if not any(c[0] == d for c in all_candidates):
                            all_candidates.append((d, m, dist))

                doc_count = 0
                for doc, meta, dist in all_candidates:
                    if doc_count >= 3:
                        break
                    doc_count += 1
                        
                    snippet = doc[:1200]
                    src = meta.get('source', 'Unknown')
                    
                    # Resolve Law Name accurately
                    raw_law = meta.get('law') or ""
                    if not raw_law or str(raw_law).lower() in ['statute', 'unknown', 'none', 'null', '']:
                        snippet_lower = snippet.lower()
                        if 'information technology' in snippet_lower or 'it act' in snippet_lower:
                            raw_law = "Information Technology Act, 2000"
                        elif 'bharatiya nyaya' in snippet_lower or 'bns' in snippet_lower:
                            raw_law = "Bharatiya Nyaya Sanhita, 2023"
                        elif 'indian penal' in snippet_lower or 'ipc' in snippet_lower:
                            raw_law = "Indian Penal Code, 1860"
                        elif 'consumer protection' in snippet_lower or 'cpa' in snippet_lower:
                            raw_law = "Consumer Protection Act, 2019"
                        elif 'code of criminal procedure' in snippet_lower or 'crpc' in snippet_lower:
                            raw_law = "Code of Criminal Procedure, 1973"
                        elif 'constitution' in snippet_lower:
                            raw_law = "Constitution of India"
                        else:
                            raw_law = "Indian Statute"

                    # Resolve Section Number cleanly
                    raw_sec = meta.get('section') or meta.get('bns_section') or meta.get('ipc_section')
                    sec_num = None
                    if raw_sec:
                        sec_match = re.search(r'\d+[A-Z]*', str(raw_sec))
                        if sec_match:
                            sec_num = sec_match.group()
                    if not sec_num:
                        sec_match = re.search(r'(?:Section|Sec\.|§)\s*(\d+[A-Z]*)', snippet, re.IGNORECASE)
                        if sec_match:
                            sec_num = sec_match.group(1)

                    display_section = f"Section {sec_num}" if sec_num else "Key Provision"
                    context_text += f"---\nSource: {raw_law} ({display_section})\nContent: {snippet}\n"
                    
                    if meta.get("type") == "statute" or raw_law != "Indian Statute" or sec_num:
                        citation_url = meta.get("url") or self._generate_statute_url(raw_law, sec_num or "")
                        # Deduplicate
                        if not any(c.get('source') == raw_law and c.get('section') == display_section for c in citations):
                            citations.append({
                                "source": raw_law,
                                "section": display_section,
                                "url": citation_url,
                                "text": snippet[:220].strip() + "..."
                            })
                    elif meta.get("type") == "judgment":
                        title = meta.get("title", "Supreme Court Precedent")
                        if title and title != "Unknown Case":
                            citations.append({
                                "source": "Supreme Court Judgment", 
                                "section": title, 
                                "url": f"https://indiankanoon.org/search/?formInput={quote(title)}",
                                "text": snippet[:220].strip() + "..."
                            })
                            related_judgments.append({
                                "title": title,
                                "summary": snippet[:220].strip() + "...",
                                "case_id": meta.get("case_id", "")
                            })
            else:
                context_text = "Database not available. Answer generically."
        except Exception as e:
            print(f"[RAGEngine] ⚠️ Vector Search Error: {e}")
            context_text = "Search unavailable."

        # 2. Generate Answer with LLM
        answer = "I apologize, but I cannot generate an answer at this moment."
        neutral_analysis = None
        arguments = None
        
        print("[RAGEngine] Preparing LLM request...", flush=True)
        if self.api_key:
            system_prompt = (
                "You are LegalAi, an expert Indian legal research assistant with comprehensive knowledge of Indian law.\n\n"
                "CRITICAL INSTRUCTIONS:\n"
                "1. ALWAYS provide authoritative, professional answers. NEVER mention 'context not available', 'provided context', or data limitations.\n"
                "2. Use the provided Context when available, otherwise rely on your knowledge of Indian Law (IPC, BNS, CrPC, IT Act, Constitution).\n"
                "3. NEVER say 'does not directly relate' or 'not applicable'. If a question is about constitutional law, civil law, or case law, answer it confidently.\n"
                "4. For landmark cases (e.g., Kesavananda Bharati), provide the case name, year, key holding, and citation (AIR/SCC) even if not in the database.\n"
                "5. ACCURACY: Verify facts. IPC 420 = up to 7 years + fine. IPC 302 = Death or Life Imprisonment.\n"
                "6. STRUCTURE:\n"
                "   - Direct Answer (clear, confident)\n"
                "   - Provisions/Key Points (if applicable)\n"
                "   - Punishment/Outcome (if applicable)\n"
                "   - Source/Citation (statute or case law)\n\n"
                "7. NEVER use phrases like:\n"
                "   - 'The provided context does not contain...'\n"
                "   - 'Not applicable as...'\n"
                "   - 'Does not directly relate to...'\n"
                "   Instead, answer the question directly and professionally.\n\n"
                "DISCLAIMER: For informational purposes only. Not legal advice."
            )
            if language == "hi":
                system_prompt += (
                    "\n\nLANGUAGE RULE:\n- Respond fully in Hindi (Devanagari).\n- Section numbers and Act names may remain in English characters.\n"
                    "- Translate legal terms to Hindi where appropriate. Do NOT reply in English."
                )

            if is_long:
                system_prompt += (
                    "\n\nLONG-FORM REQUEST:\n"
                    "- Provide a detailed explanation with additional context when possible."
                )

            if analysis_mode:
                system_prompt += (
                    "\n[NEUTRAL ANALYSIS REQUESTED]\n"
                    "You must also provide a Neutral Analysis section at the end.\n"
                    "Strictly use this format:\n"
                    "[FACTORS]\n- Factor 1\n- Factor 2\n[/FACTORS]\n"
                    "[INTERPRETATIONS]\n- Interpretation 1\n- Interpretation 2\n[/INTERPRETATIONS]"
                )
            
            if arguments_mode:
                system_prompt += (
                    "\n[ARGUMENTS REQUESTED]\n"
                    "You must also provide Balanced Arguments at the end.\n"
                    "Strictly use this format:\n"
                    "[FOR]\n- Argument For 1\n- Argument For 2\n[/FOR]\n"
                    "[AGAINST]\n- Argument Against 1\n- Argument Against 2\n[/AGAINST]"
                )

            user_query = f"Context:\n{context_text}\n\nQuery: {query}\n"
            
            # Append instructions to User Prompt for Recency Bias
            if analysis_mode:
                user_query += (
                    "\n\nIMPORTANT: You MUST also provide a Neutral Analysis at the very end.\n"
                    "Use this EXACT format:\n"
                    "[FACTORS]\n- Factor 1\n- Factor 2\n[/FACTORS]\n"
                    "[INTERPRETATIONS]\n- Interpretation 1\n- Interpretation 2\n[/INTERPRETATIONS]"
                )

            if arguments_mode:
                 user_query += (
                    "\n\nIMPORTANT: You MUST also provide Balanced Arguments at the very end.\n"
                    "Use this EXACT format:\n"
                    "[FOR]\n- Argument For 1\n[/FOR]\n"
                    "[AGAINST]\n- Argument Against 1\n[/AGAINST]"
                )

            try:
                print("[RAGEngine] Calling LLM now...", flush=True)
                # Check cache (keyed by query + language + top sources)
                cache_key = f"{language}|{query.strip()}|{','.join([c.get('source','') for c in citations[:2]])}"
                if cache_key in self._cache:
                    cached = self._cache[cache_key]
                    return {
                        "answer": cached.get("answer", ""),
                        "citations": citations[:3],
                        "related_judgments": related_judgments[:3],
                        "neutral_analysis": cached.get("neutral_analysis"),
                        "arguments": cached.get("arguments")
                    }

                max_tokens = 2000 if is_long else 1500
                raw_answer = self._call_llm([
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ], max_tokens=max_tokens, model_override=self.model_simple)
                print("[RAGEngine] LLM returned response.", flush=True)
                try:
                    print(f"\n[DEBUG] Raw LLM Answer:\n{raw_answer.encode('utf-8', 'replace').decode('utf-8')}\n[DEBUG] End Raw Answer\n", flush=True)
                except Exception:
                     print("\n[DEBUG] Raw LLM Answer: (encoding error)\n[DEBUG] End Raw Answer\n", flush=True)
                
                def extract_tag(text, start_tag, end_tag):
                    # Try exact tag first
                    pattern = f"{re.escape(start_tag)}\\s*(.*?)\\s*{re.escape(end_tag)}"
                    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
                    
                    if not match and "ARGUMENTS" in start_tag:
                         # Fallback for "ARGUMENTS FOR" variations
                         alt_start = start_tag.replace("FOR", "ARGUMENTS FOR").replace("AGAINST", "ARGUMENTS AGAINST")
                         pattern = f"{re.escape(alt_start)}\\s*(.*?)\\s*{re.escape(end_tag)}"
                         match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)

                    if match:
                        content = match.group(1).strip()
                        return [item.strip("- *").strip() for item in content.split("\n") if item.strip()]
                    return []

                if analysis_mode:
                    factors = extract_tag(raw_answer, "[FACTORS]", "[/FACTORS]")
                    interpretations = extract_tag(raw_answer, "[INTERPRETATIONS]", "[/INTERPRETATIONS]")
                    if factors or interpretations:
                        neutral_analysis = {"factors": factors or ["Analysis pending"], "interpretations": interpretations or ["Further research required"]}
                
                if arguments_mode:
                    for_args = extract_tag(raw_answer, "[FOR]", "[/FOR]")
                    against_args = extract_tag(raw_answer, "[AGAINST]", "[/AGAINST]")
                    if for_args or against_args:
                        arguments = {"for": for_args or ["N/A"], "against": against_args or ["N/A"]}

                # Remove the special sections from the main answer to avoid duplication
                # Expanded regex to catch variations like [ARGUMENTS FOR]
                answer = re.sub(r'\[/?(FACTORS|INTERPRETATIONS|FOR|AGAINST|ARGUMENTS FOR|ARGUMENTS AGAINST)\]', '', raw_answer, flags=re.IGNORECASE).strip()
                
                # Robust approach: Split by the first occurrence of any special tag
                # Added NEUTRAL ANALYSIS and BALANCED ARGUMENTS which the LLM was using
                split_patterns = ["[FACTORS]", "[INTERPRETATIONS]", "[FOR]", "[AGAINST]", "[ARGUMENTS FOR]", "[ARGUMENTS AGAINST]", "[NEUTRAL ANALYSIS]", "[BALANCED ARGUMENTS]"]
                for p in split_patterns:
                    # Case insensitive check for splitting
                    idx = answer.upper().find(p)
                    if idx != -1:
                        answer = answer[:idx].strip()

                # Cleanup
                answer = re.sub(r'\n{3,}', '\n\n', answer).strip()
                # Cache the structured result
                self._cache[cache_key] = {
                    "answer": answer,
                    "arguments": arguments,
                    "neutral_analysis": neutral_analysis
                }
                
            except Exception as e:
                print(f"[RAGEngine] LLM Error after retries: {e}")
                # Provide an intelligent statutory synthesis from the retrieved ChromaDB chunks
                if context_text and len(context_text.strip()) > 30:
                    cleaned_snippets = []
                    for c in citations[:3]:
                        t = c.get('text', '').replace('---', '').strip()
                        if t:
                            cleaned_snippets.append(f"• **{c.get('source', 'Statute')} ({c.get('section', 'Key Provision')})**:\n  {t}")
                    
                    answer = (
                        f"### Statutory Research Summary: *{query}*\n\n"
                        f"The statutory knowledge base retrieved the following relevant legal provisions:\n\n"
                        + ("\n\n".join(cleaned_snippets) if cleaned_snippets else context_text[:800])
                        + "\n\n*(Note: Cloud AI inference is experiencing temporary high traffic; direct statutory provisions are cited above for your immediate review.)*"
                    )
                else:
                    answer = (
                        f"I could not complete the full analysis for **'{query}'** due to temporary cloud service latency. "
                        "Please re-submit your query in a few moments."
                    )

        # POST-PROCESSING: Extract statute references from answer and add citations if missing
        if answer and not citations:
            # Extract statute references like "Section 120 IPC", "Article 370", "Section 66A IT Act"
            statute_patterns = [
                r'Section\s+(\d+[A-Z]*)\s+(?:of\s+)?(?:the\s+)?(IPC|Indian Penal Code|BNS|Bharatiya Nyaya Sanhita|IT Act|Information Technology Act|CrPC|Code of Criminal Procedure)',
                r'Article\s+(\d+[A-Z]*)\s+(?:of\s+)?(?:the\s+)?Constitution',
                r'(IPC|BNS)\s+Section\s+(\d+[A-Z]*)',
            ]
            
            for pattern in statute_patterns:
                matches = re.finditer(pattern, answer, re.IGNORECASE)
                for match in matches:
                    if 'Article' in match.group(0):
                        section_num = match.group(1)
                        law_name = "Constitution of India"
                        url = f"https://www.constitutionofindia.net/constitution_of_india/part{section_num[0] if section_num[0].isdigit() else '1'}/articles/Article%20{section_num}"
                    elif len(match.groups()) >= 2:
                        section_num = match.group(1)
                        law_name = match.group(2)
                        url = self._generate_statute_url(law_name, section_num)
                    else:
                        continue
                    
                    # Add citation if not already present
                    if not any(c.get('section', '').endswith(section_num) for c in citations):
                        citations.append({
                            "source": law_name,
                            "section": f"Section {section_num}" if 'Section' in match.group(0) else f"Article {section_num}",
                            "url": url,
                            "text": "Referenced in response"
                        })

        return {
            "answer": answer,
            "citations": citations[:3],
            "related_judgments": related_judgments[:3], 
            "arguments": arguments,
            "neutral_analysis": neutral_analysis,
            "disclaimer": "AI-generated response. For informational purposes only. Consult a qualified lawyer."
        }

    def generate_draft(self, draft_type: str, details: str, language: str = 'en') -> str:
        """
        Generates a formal legal draft based on the user's details.
        """
        templates = {
            "legal_notice": "## LEGAL NOTICE\nThrough Registered Post / Speed Post / Email\nDate: [Date]\n\nTo,\n[Recipient Name]\n[Recipient Address]\n\n### Subject:\nLegal Notice under [Applicable Law] regarding [Issue Brief]\n\nSir/Madam,\n\nUnder instructions and on behalf of my client [Sender Name], residing at [Sender Address], I hereby serve upon you the present legal notice as follows:\n\n1. Facts of the Case\nThat my client [Brief Background].\nThat despite requests, you have [Breach Description].\n\n2. Legal Provisions\nYour actions amount to violation of:\n- [Section Name] of [Act Name]\n- Other applicable provisions of law\n\n3. Cause of Action\nThat the cause of action arose on [Date] and continues to subsist.\n\n4. Demand\nYou are hereby called upon to:\n- [Specific Demand]\nwithin [Time Limit] days from receipt of this notice.\n\n5. Consequences\nFailing compliance, my client shall initiate legal proceedings at your risk.\n\nYours faithfully,\n[Advocate Name]\nAdvocate for [Sender Name]",
            
            "nda": "## NON-DISCLOSURE AGREEMENT (NDA)\n\nThis Agreement is entered into on [Date] between:\n\nParty A: [Party A Name], at [Address A]\nParty B: [Party B Name], at [Address B]\n\n1. Purpose\nThe parties wish to exchange confidential information for [Purpose].\n\n2. Definition of Confidential Information\n'Confidential Information' includes all written, oral, electronic information disclosed.\n\n3. Obligations\nThe Receiving Party shall:\n- Not disclose confidential information to third parties\n- Use the information solely for the stated purpose\n\n4. Exclusions\nInformation publicly available or required by law is excluded.\n\n5. Term\nValid for [Duration] years.\n\n6. Governing Law\nGoverned by laws of India.\n\n7. Jurisdiction\nCourts at [City] shall have exclusive jurisdiction.\n\nIN WITNESS WHEREOF, the parties have signed.\n\nParty A Signature: __________\nParty B Signature: __________",
            
            "rent_agreement": "## RENT AGREEMENT\n\nThis Agreement is made on [Date] between:\n\nLandlord: [Landlord Name]\nTenant: [Tenant Name]\n\n1. Property\nThe Landlord lets out the premises located at [Property Address].\n\n2. Rent\nMonthly rent shall be Rs. [Rent Amount], payable on or before [Due Date].\n\n3. Security Deposit\nTenant shall pay Rs. [Security Deposit] as refundable security deposit.\n\n4. Term\nValid for [Duration] months.\n\n5. Maintenance\nTenant shall maintain the premises and not sublet without permission.\n\n6. Termination\nEither party may terminate with [Notice Period] days notice.\n\nSigned on [Date].\n\nLandlord Signature: _______\nTenant Signature: _______",
            
            "affidavit": "## AFFIDAVIT\n\nI, [Deponent Name], aged [Age], residing at [Address], do hereby solemnly affirm:\n\n1. That I am the deponent herein and competent to swear this affidavit.\n2. That [Statement of Facts].\n3. That the statements made herein are true to my knowledge.\n\nVerified at [Place] on [Date].\n\nDEPONENT SIGNATURE\n\nSolemnly affirmed before me on [Date].\n\nNotary / Oath Commissioner",
            
            "employment_contract": "## EMPLOYMENT AGREEMENT\n\nThis Agreement is entered on [Date] between:\n\nEmployer: [Company Name]\nEmployee: [Employee Name]\n\n1. Designation\nEmployee shall serve as [Designation].\n\n2. Duties\nEmployee shall perform duties assigned from time to time.\n\n3. Salary\nMonthly remuneration shall be Rs. [Salary].\n\n4. Confidentiality\nEmployee shall maintain confidentiality during and after employment.\n\n5. Termination\nEither party may terminate with [Notice Period] days notice.\n\nSigned:\n\nEmployer: _______\nEmployee: _______",
            
            "posh_complaint": "## COMPLAINT UNDER POSH ACT, 2013\n\nTo,\nThe Internal Complaints Committee\n[Organization Name]\n\nSubject: Complaint under Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013\n\n1. Complainant Details\nName: [Complainant Name]\nDesignation: [Designation]\nDepartment: [Department]\n\n2. Respondent Details\nName: [Respondent Name]\nDesignation: [Respondent Designation]\nRelationship with Complainant: [Relationship]\n\n3. Incident Details\nDate of Incident: [Date]\nPlace of Incident: [Place]\nDescription of Incident:\n[Detailed Description of Harassment]\n\n4. Impact\nThe incident has created a hostile work environment and affected my dignity/work performance.\n\n5. Witnesses (if any)\n[List of Witnesses]\n\n6. Evidence (if any)\n[List of Evidence]\n\n7. Relief Sought\nI requested the ICC to conduct an inquiry into this matter and take appropriate action against the respondent under the POSH Act.\n\nI hereby declare that the information provided above is true and correct to the best of my knowledge.\n\nSignature: ______\nDate: ______",
            
            "rti_application": "## APPLICATION UNDER RTI ACT, 2005\n\nTo,\nThe Public Information Officer\n[Department Name]\n\nSubject: Information under RTI Act, 2005\n\nSir/Madam,\n\nKindly provide the following information regarding [Subject Matter]:\n\n1. [Question 1]\n2. [Question 2]\n\nI have enclosed the application fee of Rs. 10.\n\nAddress for correspondence: [Address]\n\nDate: [Date]\nApplicant Signature: _______"
        }

        template = templates.get(draft_type, "Generate a formal legal document for the user.")

        system_prompt = (
            "You are an Indian Legal Drafting Assistant. YOUR GOAL is to fill the provided template accurately.\n\n"
            f"TEMPLATE STRUCTURE (Reference Only):\n{template}\n\n"
            "CRITICAL RULES:\n"
            "1. NO MARKDOWN BOLDING: Do NOT use **bold** or *italic* syntax. Use plain text.\n"
            "2. ADAPTIVE LENGTH: If user provides detailed input, EXPAND the draft. Add extra paragraphs/points to cover all user details. Do NOT truncate user info to fit the template.\n"
            "3. REPLACE PLACEHOLDERS: Replace [Name], [Date] with actual info. Infer missing info reasonably.\n"
            "4. OUTPUT: Return ONLY the filled document content.\n"
            "5. DISCLAIMER: Add a standard disclaimer at the very bottom.\n\n"
        )

        if language == 'hi':
            system_prompt += (
                "CRITICAL HINDI RULES:\n"
                "1. TRANSLATE THE ENTIRE DOCUMENT TO HINDI (Devanagari).\n"
                "2. USE CORRECT LEGAL TERMINOLOGY (Glossary below):\n"
                "   - 'Legal Notice' -> 'विधिक सूचना' (Vidhik Suchna)\n"
                "   - 'Demand' -> 'मांग' (Maang) or 'अपेक्षा' (Apeksha)\n"
                "   - 'Cause of Action' -> 'वाद का कारण' (Vaad ka Kaaran)\n"
                "   - 'Rent Agreement' -> 'किरायानामा' (Kirayanama)\n"
                "   - 'Affidavit' -> 'शपथ पत्र' (Shapath Patra)\n"
                "3. Translate Headers properly (e.g., '1. Purpose' -> '1. उद्देश्य').\n"
                "4. ONLY keep specific Act Names/Section Numbers in English (e.g., 'Section 420 IPC').\n"
                "5. Do NOT use Hinglish. Ensure full grammatical correctness.\n"
            )
        else:
            system_prompt += "Respond in formal English."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Details for draft:\n{details}"}
        ]

        try:
            return self._call_llm(messages, max_tokens=2000, timeout=90, model_override=self.model_simple)
        except Exception as e:
            print(f"[RAGEngine] Drafting failed: {e}")
            return f"Error: Could not generate draft. Reason: {e!s}"
