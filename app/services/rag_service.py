import os
import json
import math
import logging
from typing import List, Dict, Any
from openai import OpenAI
from core.config import settings

logger = logging.getLogger("rag_service")

# Sample corporate knowledge base/policies
KNOWLEDGE_BASE = [
    {
        "id": "policy_leave_01",
        "title": "Maternity Leave Policy",
        "content": (
            "Employees are eligible for up to 90 calendar days of paid Maternity Leave. "
            "Applications must be submitted at least 4 weeks prior to the commencement date. "
            "Manager approval is required, and the HR department handles the final document compliance."
        )
    },
    {
        "id": "policy_leave_02",
        "title": "Casual and Sick Leave Policies",
        "content": (
            "Each employee is credited with 12 casual leave days and 8 sick leave days annually. "
            "Unused casual leaves expire at the end of the fiscal year, while sick leaves can be "
            "carried forward up to a maximum of 30 days."
        )
    },
    {
        "id": "policy_general_01",
        "title": "Office Working Hours & Remote Work",
        "content": (
            "Our core operating hours are 9:00 AM to 6:00 PM local time. "
            "Under the hybrid model, employees can work remotely up to 2 days per week "
            "with manager approval."
        )
    }
]

class RAGService:
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.is_mock = self.api_key == "mock-key-for-hr-ai-copilot" or not self.api_key
        if not self.is_mock:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().replace(".", "").replace(",", "").split()

    def _compute_cosine_similarity(self, text_a: str, text_b: str) -> float:
        """Fallback local TF-IDF cosine similarity calculation."""
        words_a = self._tokenize(text_a)
        words_b = self._tokenize(text_b)
        
        all_words = set(words_a + words_b)
        if not all_words:
            return 0.0
            
        vector_a = [words_a.count(w) for w in all_words]
        vector_b = [words_b.count(w) for w in all_words]
        
        dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = math.sqrt(sum(a * a for a in vector_a))
        norm_b = math.sqrt(sum(b * b for b in vector_b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    async def search(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """Query knowledge base semantically using OpenAI Embeddings or local Cosine Similarity."""
        logger.info(f"RAG search query: '{query}'")
        
        # Load dynamic policies from database
        from db.session import SessionLocal
        from db.models import PolicyDocument
        db = SessionLocal()
        db_docs = []
        try:
            db_docs = [{"id": f"db_{d.id}", "title": d.title, "content": d.content} for d in db.query(PolicyDocument).all()]
        except Exception as e:
            logger.error(f"Failed to query policy documents: {e}")
        finally:
            db.close()
            
        kb_combined = KNOWLEDGE_BASE + db_docs
        
        # If running offline/mock mode, use local TF-IDF Cosine Similarity
        if self.is_mock:
            logger.info("RAG search executing local cosine-similarity pipeline.")
            results = []
            for doc in kb_combined:
                score = self._compute_cosine_similarity(query, doc["content"])
                results.append((doc, score))
            
            # Sort by score descending
            results.sort(key=lambda x: x[1], reverse=True)
            return [res[0] for res in results[:top_k] if res[1] > 0.05]
            
        # Live OpenAI Embedding implementation
        try:
            # Fetch query embedding
            response = self.client.embeddings.create(
                input=[query],
                model="text-embedding-3-small"
            )
            query_vector = response.data[0].embedding
            
            results = []
            for doc in kb_combined:
                doc_resp = self.client.embeddings.create(
                    input=[doc["content"]],
                    model="text-embedding-3-small"
                )
                doc_vector = doc_resp.data[0].embedding
                
                score = sum(q * d for q, d in zip(query_vector, doc_vector))
                results.append((doc, score))
                
            results.sort(key=lambda x: x[1], reverse=True)
            return [res[0] for res in results[:top_k]]
        except Exception as e:
            logger.error(f"Error in RAG live search: {e}. Falling back to local search.")
            self.is_mock = True
            return await self.search(query, top_k)

rag_service = RAGService()
