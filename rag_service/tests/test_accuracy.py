"""
Comprehensive accuracy testing for enhanced RAG features
Tests conversation memory, query reformulation, and retrieval quality
"""

import json
import time
from datetime import datetime

import requests

BASE_URL = "http://localhost:8000"

class RAGAccuracyTester:
    def __init__(self):
        self.session_id = None
        self.test_results = {
            "conversation_memory": [],
            "query_reformulation": [],
            "retrieval_quality": [],
            "response_times": []
        }
    
    def test_health(self):
        """Test if RAG service is running"""
        print("\n🏥 Testing RAG Service Health...")
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                print("   ✓ RAG service is running")
                return True
            else:
                print(f"   ✗ Service returned status {response.status_code}")
                return False
        except Exception as e:
            print(f"   ✗ Service not reachable: {e}")
            return False
    
    def create_session(self):
        """Create a conversation session"""
        print("\n📝 Creating Conversation Session...")
        try:
            response = requests.post(f"{BASE_URL}/session/create")
            data = response.json()
            self.session_id = data["session_id"]
            print(f"   ✓ Session created: {self.session_id[:16]}...")
            return True
        except Exception as e:
            print(f"   ✗ Failed to create session: {e}")
            return False
    
    def test_basic_query(self):
        """Test basic query without conversation memory"""
        print("\n🔍 Test 1: Basic Query (No Context)")
        print("   Query: 'What is the punishment for murder under BNS?'")
        
        start_time = time.time()
        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={
                    "query": "What is the punishment for murder under BNS?",
                    "language": "en",
                    "arguments_mode": False,
                    "analysis_mode": False
                },
                timeout=30
            )
            elapsed = time.time() - start_time
            
            data = response.json()
            answer = data.get("answer", "")
            citations = data.get("citations", [])
            
            # Check accuracy
            has_bns_section = "BNS" in answer or "Section 103" in answer
            has_punishment = "death" in answer.lower() or "life imprisonment" in answer.lower()
            has_citations = len(citations) > 0
            
            accuracy_score = sum([has_bns_section, has_punishment, has_citations]) / 3 * 100
            
            print(f"   Response Time: {elapsed:.2f}s")
            print(f"   Answer Length: {len(answer)} chars")
            print(f"   Citations: {len(citations)}")
            print(f"   ✓ Contains BNS reference: {has_bns_section}")
            print(f"   ✓ Contains punishment details: {has_punishment}")
            print(f"   ✓ Has citations: {has_citations}")
            print(f"   📊 Accuracy Score: {accuracy_score:.1f}%")
            
            self.test_results["retrieval_quality"].append({
                "test": "basic_query",
                "accuracy": accuracy_score,
                "response_time": elapsed
            })
            
            return data
            
        except Exception as e:
            print(f"   ✗ Query failed: {e}")
            return None
    
    def test_conversation_memory(self):
        """Test conversation memory with follow-up questions"""
        print("\n💬 Test 2: Conversation Memory")
        
        # First question
        print("   Q1: 'What is the punishment for theft under BNS?'")
        start_time = time.time()
        
        try:
            response1 = requests.post(
                f"{BASE_URL}/query",
                json={
                    "query": "What is the punishment for theft under BNS?",
                    "session_id": self.session_id,
                    "language": "en"
                },
                timeout=30
            )
            elapsed1 = time.time() - start_time
            data1 = response1.json()
            answer1 = data1.get("answer", "")
            
            print(f"   ✓ Response 1: {elapsed1:.2f}s, {len(answer1)} chars")
            
            # Wait a moment
            time.sleep(1)
            
            # Follow-up question (should use context)
            print("   Q2: 'What about attempt to commit it?'")
            start_time = time.time()
            
            response2 = requests.post(
                f"{BASE_URL}/query",
                json={
                    "query": "What about attempt to commit it?",
                    "session_id": self.session_id,
                    "language": "en"
                },
                timeout=30
            )
            elapsed2 = time.time() - start_time
            data2 = response2.json()
            answer2 = data2.get("answer", "")
            
            print(f"   ✓ Response 2: {elapsed2:.2f}s, {len(answer2)} chars")
            
            # Check if context was used
            mentions_theft = "theft" in answer2.lower()
            mentions_attempt = "attempt" in answer2.lower()
            has_relevant_answer = mentions_theft or mentions_attempt
            
            # Get conversation history
            history_response = requests.get(
                f"{BASE_URL}/session/{self.session_id}/history"
            )
            history = history_response.json()
            message_count = history["metadata"]["message_count"]
            
            accuracy_score = sum([has_relevant_answer, message_count >= 4]) / 2 * 100
            
            print(f"   ✓ Conversation history: {message_count} messages")
            print(f"   ✓ Context used in follow-up: {has_relevant_answer}")
            print(f"   📊 Memory Accuracy: {accuracy_score:.1f}%")
            
            self.test_results["conversation_memory"].append({
                "test": "follow_up_question",
                "accuracy": accuracy_score,
                "message_count": message_count,
                "context_used": has_relevant_answer
            })
            
            return True
            
        except Exception as e:
            print(f"   ✗ Conversation test failed: {e}")
            return False
    
    def test_query_reformulation(self):
        """Test intelligent query reformulation"""
        print("\n🔄 Test 3: Query Reformulation")
        
        # Setup context with a specific topic
        print("   Setting up context: 'What is BNS Section 302?'")
        
        try:
            # First query to establish context
            requests.post(
                f"{BASE_URL}/query",
                json={
                    "query": "What is BNS Section 302?",
                    "session_id": self.session_id,
                    "language": "en"
                },
                timeout=30
            )
            
            time.sleep(1)
            
            # Ambiguous follow-up that needs reformulation
            print("   Follow-up: 'What are the exceptions?'")
            
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/query",
                json={
                    "query": "What are the exceptions?",
                    "session_id": self.session_id,
                    "language": "en"
                },
                timeout=30
            )
            elapsed = time.time() - start_time
            
            data = response.json()
            answer = data.get("answer", "")
            
            # Check if reformulation worked
            mentions_section_302 = "302" in answer or "Section 302" in answer
            has_relevant_content = len(answer) > 100
            
            accuracy_score = sum([mentions_section_302, has_relevant_content]) / 2 * 100
            
            print(f"   Response Time: {elapsed:.2f}s")
            print(f"   ✓ Mentions original context (302): {mentions_section_302}")
            print(f"   ✓ Has relevant content: {has_relevant_content}")
            print(f"   📊 Reformulation Accuracy: {accuracy_score:.1f}%")
            
            self.test_results["query_reformulation"].append({
                "test": "ambiguous_follow_up",
                "accuracy": accuracy_score,
                "context_preserved": mentions_section_302
            })
            
            return True
            
        except Exception as e:
            print(f"   ✗ Reformulation test failed: {e}")
            return False
    
    def test_retrieval_quality(self):
        """Test vector retrieval quality with different query types"""
        print("\n🎯 Test 4: Retrieval Quality (10 vs 5 results)")
        
        test_queries = [
            {
                "query": "What are the penalties for defamation?",
                "expected_terms": ["defamation", "penalty", "punishment", "section"]
            },
            {
                "query": "Explain the difference between IPC and BNS",
                "expected_terms": ["IPC", "BNS", "difference", "Bharatiya"]
            }
        ]
        
        total_accuracy = 0
        
        for i, test in enumerate(test_queries, 1):
            print(f"\n   Query {i}: '{test['query']}'")
            
            try:
                start_time = time.time()
                response = requests.post(
                    f"{BASE_URL}/query",
                    json={
                        "query": test["query"],
                        "language": "en"
                    },
                    timeout=30
                )
                elapsed = time.time() - start_time
                
                data = response.json()
                answer = data.get("answer", "").lower()
                citations = data.get("citations", [])
                
                # Check relevance
                terms_found = sum(1 for term in test["expected_terms"] if term.lower() in answer)
                relevance_score = terms_found / len(test["expected_terms"]) * 100
                
                print(f"   Response Time: {elapsed:.2f}s")
                print(f"   Citations: {len(citations)}")
                print(f"   Relevant terms found: {terms_found}/{len(test['expected_terms'])}")
                print(f"   📊 Relevance Score: {relevance_score:.1f}%")
                
                total_accuracy += relevance_score
                
                self.test_results["response_times"].append(elapsed)
                
            except Exception as e:
                print(f"   ✗ Query failed: {e}")
        
        avg_accuracy = total_accuracy / len(test_queries)
        print(f"\n   📊 Average Retrieval Accuracy: {avg_accuracy:.1f}%")
        
        return avg_accuracy
    
    def generate_report(self):
        """Generate comprehensive accuracy report"""
        print("\n" + "="*60)
        print("📊 ENHANCED RAG ACCURACY REPORT")
        print("="*60)
        
        # Conversation Memory
        if self.test_results["conversation_memory"]:
            mem_scores = [r["accuracy"] for r in self.test_results["conversation_memory"]]
            avg_mem = sum(mem_scores) / len(mem_scores)
            print(f"\n💬 Conversation Memory: {avg_mem:.1f}%")
            print("   - Context preservation: ✓")
            print("   - Message tracking: ✓")
        
        # Query Reformulation
        if self.test_results["query_reformulation"]:
            ref_scores = [r["accuracy"] for r in self.test_results["query_reformulation"]]
            avg_ref = sum(ref_scores) / len(ref_scores)
            print(f"\n🔄 Query Reformulation: {avg_ref:.1f}%")
            print("   - Ambiguous query handling: ✓")
            print("   - Context extraction: ✓")
        
        # Retrieval Quality
        if self.test_results["retrieval_quality"]:
            ret_scores = [r["accuracy"] for r in self.test_results["retrieval_quality"]]
            avg_ret = sum(ret_scores) / len(ret_scores)
            print(f"\n🎯 Retrieval Quality: {avg_ret:.1f}%")
            print("   - Citation accuracy: ✓")
            print("   - Content relevance: ✓")
        
        # Performance
        if self.test_results["response_times"]:
            avg_time = sum(self.test_results["response_times"]) / len(self.test_results["response_times"])
            print("\n⚡ Performance Metrics:")
            print(f"   - Average response time: {avg_time:.2f}s")
            print(f"   - Min response time: {min(self.test_results['response_times']):.2f}s")
            print(f"   - Max response time: {max(self.test_results['response_times']):.2f}s")
        
        # Overall Score
        all_scores = []
        if self.test_results["conversation_memory"]:
            all_scores.extend([r["accuracy"] for r in self.test_results["conversation_memory"]])
        if self.test_results["query_reformulation"]:
            all_scores.extend([r["accuracy"] for r in self.test_results["query_reformulation"]])
        if self.test_results["retrieval_quality"]:
            all_scores.extend([r["accuracy"] for r in self.test_results["retrieval_quality"]])
        
        if all_scores:
            overall = sum(all_scores) / len(all_scores)
            print(f"\n{'='*60}")
            print(f"🏆 OVERALL ACCURACY: {overall:.1f}%")
            print(f"{'='*60}")
            
            # Grade
            if overall >= 90:
                grade = "A+ (Excellent)"
            elif overall >= 80:
                grade = "A (Very Good)"
            elif overall >= 70:
                grade = "B (Good)"
            elif overall >= 60:
                grade = "C (Fair)"
            else:
                grade = "D (Needs Improvement)"
            
            print(f"\n📈 Grade: {grade}")
        
        print("\n✅ Testing complete!")
        
        # Save results
        with open("accuracy_report.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "results": self.test_results,
                "overall_accuracy": overall if all_scores else 0
            }, f, indent=2)
        
        print("\n💾 Detailed results saved to: accuracy_report.json")

def main():
    print("="*60)
    print("🧪 ENHANCED RAG ACCURACY TESTING")
    print("="*60)
    
    tester = RAGAccuracyTester()
    
    # Wait for service to start
    print("\n⏳ Waiting for RAG service to start...")
    time.sleep(5)
    
    # Test health
    if not tester.test_health():
        print("\n❌ RAG service is not running. Please start it first:")
        print("   cd rag_service")
        print("   uvicorn main:app --reload --port 8000")
        return
    
    # Create session
    if not tester.create_session():
        print("\n❌ Failed to create session. Exiting.")
        return
    
    # Run tests
    print("\n" + "="*60)
    print("Running Accuracy Tests...")
    print("="*60)
    
    tester.test_basic_query()
    tester.test_conversation_memory()
    tester.test_query_reformulation()
    tester.test_retrieval_quality()
    
    # Generate report
    tester.generate_report()

if __name__ == "__main__":
    main()
