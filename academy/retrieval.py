"""Versioned evidence retrieval: BM25 + local LSA, optional transformer/Chroma index."""

from dataclasses import dataclass, asdict
from functools import lru_cache
import hashlib
import json
import os
import re
import numpy as np
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import TfidfVectorizer, ENGLISH_STOP_WORDS
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import normalize
from academy.models import ROOT, curriculum


@dataclass
class Passage:
    id: str
    title: str
    text: str
    url: str
    level: int | None = None
    score: float = 0.0


def tokens(text):
    return [t for t in re.findall(r"[a-zA-Z_][a-zA-Z_0-9]*", text.lower()) if t not in ENGLISH_STOP_WORDS]


def chunk_text(text: str, size: int = 1500, semantic: bool = True) -> list[str]:
    """Paragraph chunks preserve code fences. Fixed-size chunks are an eval baseline."""
    if not semantic:
        return [text[i : i + size] for i in range(0, len(text), size)]
    chunks, current = [], ""
    blocks = re.split(r"(```[\s\S]*?```)", text)
    for block in blocks:
        units = [block] if block.startswith("```") else re.split(r"\n\s*\n", block)
        for unit in units:
            if current and len(current) + len(unit) > size:
                chunks.append(current.strip())
                current = ""
            current += unit + "\n\n"
    if current.strip():
        chunks.append(current.strip())
    return chunks


def corpus() -> list[Passage]:
    passages = []
    for level in curriculum():
        for i, lesson in enumerate(level.lessons):
            text = "\n\n".join(
                [
                    lesson.definition,
                    "Picture this: " + lesson.analogy,
                    lesson.body,
                    "Remember: " + lesson.remember,
                    "SQL connection: " + lesson.sql_connection,
                    "PromQL: " + lesson.promql,
                ]
            )
            passages.append(Passage(f"lesson-{level.id}-{i}", lesson.title, text, level.sources[0], level.id))
    path = ROOT / "content/reference_docs.json"
    if path.exists():
        for doc in json.loads(path.read_text()):
            for i, chunk in enumerate(chunk_text(doc["text"])):
                ident = hashlib.sha256((doc["url"] + chunk).encode()).hexdigest()[:16]
                passages.append(Passage("doc-" + ident, doc["title"], chunk, doc["url"]))
    return passages


class HybridRetriever:
    def __init__(self):
        self.passages = corpus()
        texts = [p.title + " " + p.text for p in self.passages]
        self.bm25 = BM25Okapi([tokens(t) for t in texts])
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=15000)
        matrix = self.vectorizer.fit_transform(texts)
        self.svd = TruncatedSVD(
            n_components=min(64, matrix.shape[0] - 1, matrix.shape[1] - 1), random_state=42
        )
        self.embeddings = normalize(self.svd.fit_transform(matrix))
        self.mode = "BM25 + local LSA embeddings"
        self.transformer = self.collection = None
        if model := os.getenv("EMBEDDING_MODEL", ""):
            from sentence_transformers import SentenceTransformer
            import chromadb

            self.transformer = SentenceTransformer(model, trust_remote_code=False)
            name = (
                "reference-"
                + hashlib.sha256(
                    (model + "".join(p.id + p.text for p in self.passages)).encode()
                ).hexdigest()[:16]
            )
            self.collection = chromadb.PersistentClient(
                path=str(ROOT / ".runtime/chroma")
            ).get_or_create_collection(name, metadata={"hnsw:space": "cosine"})
            if self.collection.count() != len(self.passages):
                vectors = self.transformer.encode(texts, normalize_embeddings=True)
                self.collection.upsert(
                    ids=[p.id for p in self.passages], embeddings=vectors.tolist(), documents=texts
                )
            self.mode = "BM25 + transformer embeddings / Chroma"

    def search(self, query: str, level: int = 0, k: int = 4, *, hybrid: bool = True) -> list[Passage]:
        words = tokens(query)
        if not words:
            return []
        sparse = self.bm25.get_scores(words)
        if max(sparse, default=0) <= 0:
            return []
        sparse_rank = np.argsort(-sparse)
        ranks = {int(idx): 1 / (60 + rank) for rank, idx in enumerate(sparse_rank[:20]) if sparse[idx] > 0}
        if hybrid:
            if self.collection:
                vector = self.transformer.encode([query], normalize_embeddings=True).tolist()
                ids = self.collection.query(query_embeddings=vector, n_results=min(20, len(self.passages)))[
                    "ids"
                ][0]
                mapping = {p.id: i for i, p in enumerate(self.passages)}
                dense_rank = [mapping[x] for x in ids]
            else:
                vector = normalize(self.svd.transform(self.vectorizer.transform([query])))[0]
                dense_rank = np.argsort(-(self.embeddings @ vector))[:20]
            for rank, idx in enumerate(dense_rank):
                ranks[int(idx)] = ranks.get(int(idx), 0) + 1 / (60 + rank)
        # Transparent lightweight reranker: reward exact technical terms and current lesson.
        for idx in ranks:
            passage = self.passages[idx]
            exact = sum(
                1
                for word in words
                if ("_" in word or word in {"rate", "irate", "le", "bool"}) and word in tokens(passage.text)
            )
            ranks[idx] += min(exact, 3) * 0.005 + (0.004 if passage.level == level else 0)
        best = sorted(ranks, key=lambda idx: ranks[idx], reverse=True)[:k]
        return [Passage(**{**asdict(self.passages[idx]), "score": round(ranks[idx], 4)}) for idx in best]


@lru_cache(maxsize=1)
def retriever():
    return HybridRetriever()
