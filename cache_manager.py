import os
import json
import numpy as np
from vertexai.language_models import TextEmbeddingModel

class CacheManager:
    def __init__(self, cache_file='response_cache.json', model_name="text-embedding-004"):
        self.cache_file = cache_file
        self.model_name = model_name
        self.model = None
        self.cache = self._load_cache()

    def _load_model(self):
        if self.model is None:
            try:
                # Lazy load
                self.model = TextEmbeddingModel.from_pretrained(self.model_name)
            except Exception as e:
                print(f"Error loading embedding model {self.model_name}: {e}")
                # Fallback
                try:
                    fallback = "text-embedding-preview-0409"
                    print(f"Retrying with fallback: {fallback}")
                    self.model = TextEmbeddingModel.from_pretrained(fallback)
                except Exception as e2:
                     print(f"Fallback failed: {e2}")

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading cache: {e}")
                return []
        return []

    def _save_cache(self):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.cache, f)
        except Exception as e:
            print(f"Error saving cache: {e}")

    def _get_embedding(self, text):
        self._load_model()
        if not self.model:
            return None
        try:
            embeddings = self.model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None

    def _cosine_similarity(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def get_cached_response(self, question, threshold=0.9):
        """
        Search for a similar question in the cache.
        Returns the cached response text if found, else None.
        """
        if not self.cache:
            return None

        # Generate embedding for the new question
        question_embedding = self._get_embedding(question)
        if question_embedding is None:
            return None

        best_score = -1
        best_match = None

        for entry in self.cache:
            cached_question = entry.get('question')
            cached_embedding = entry.get('embedding')
            
            # Skip if malformed
            if not cached_question or not cached_embedding:
                continue

            score = self._cosine_similarity(question_embedding, cached_embedding)
            
            if score > best_score:
                best_score = score
                best_match = entry

        if best_score >= threshold:
            print(f"Cache Hit! Score: {best_score:.4f} for question: {question}")
            return best_match.get('response')
        
        return None

    def add_to_cache(self, question, response):
        """
        Add a new question-response pair to the cache.
        """
        embedding = self._get_embedding(question)
        if embedding:
            entry = {
                'question': question,
                'response': response,
                'embedding': embedding
            }
            self.cache.append(entry)
            self._save_cache()
            print(f"Added to cache: {question}")

# Singleton instance
cache_manager = CacheManager()
