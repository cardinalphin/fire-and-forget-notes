from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple
import pickle
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import Normalizer
from sklearn.pipeline import make_pipeline
import numpy as np

@dataclass
class Chunk:
    note_path: str
    note_title: str
    note_created: str
    text: str
    chunk_id: str

@dataclass
class Index:
    chunks: List[Chunk]
    vectorizer: TfidfVectorizer
    lsa: any
    matrix: any  # np.ndarray

def chunk_text(text: str, max_chars: int = 900, overlap: int = 120) -> List[str]:
    t = (text or "").strip()
    if not t:
        return []
    # split by blank lines first
    parts = re.split(r"\n\s*\n+", t)
    chunks: List[str] = []
    cur = ""
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if len(cur) + len(part) + 2 <= max_chars:
            cur = (cur + "\n\n" + part).strip()
        else:
            if cur:
                chunks.append(cur)
            if len(part) <= max_chars:
                cur = part
            else:
                # hard wrap long parts
                for i in range(0, len(part), max_chars - overlap):
                    chunks.append(part[i:i+max_chars])
                cur = ""
    if cur:
        chunks.append(cur)
    return chunks

def build_index(notes: List[dict]) -> Index:
    chunks: List[Chunk] = []
    for n in notes:
        ctexts = chunk_text(n["body"])
        for i, ct in enumerate(ctexts):
            chunks.append(Chunk(
                note_path=str(n["path"]),
                note_title=n["title"],
                note_created=n["created"],
                text=ct,
                chunk_id=f"{n['id']}:{i}"
            ))
    texts = [c.text for c in chunks] or [""]
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1,2), max_features=50000)
    tfidf = vectorizer.fit_transform(texts)
    # LSA for semantic-ish matching on CPU
    n_comp = min(256, max(2, tfidf.shape[1]//4), tfidf.shape[0]-1 if tfidf.shape[0] > 1 else 2)
    if n_comp < 2:
        n_comp = 2
    svd = TruncatedSVD(n_components=min(n_comp, tfidf.shape[1]-1) if tfidf.shape[1] > 2 else 2, random_state=0)
    lsa = make_pipeline(svd, Normalizer(copy=False))
    mat = lsa.fit_transform(tfidf)
    return Index(chunks=chunks, vectorizer=vectorizer, lsa=lsa, matrix=mat)

def save_index(idx: Index, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as f:
        pickle.dump(idx, f)

def load_index(path: Path) -> Optional[Index]:
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            return pickle.load(f)
    except Exception:
        return None

def search(idx: Index, query: str, top_k: int = 10) -> List[Tuple[Chunk, float]]:
    q = (query or "").strip()
    if not q or not idx.chunks:
        return []
    qv = idx.vectorizer.transform([q])
    qmat = idx.lsa.transform(qv)  # shape (1, d)
    # cosine similarity since normalized
    sims = (idx.matrix @ qmat.T).ravel()
    # top_k indices
    if len(sims) <= top_k:
        order = np.argsort(-sims)
    else:
        order = np.argpartition(-sims, top_k)[:top_k]
        order = order[np.argsort(-sims[order])]
    results = []
    for i in order:
        results.append((idx.chunks[int(i)], float(sims[int(i)])))
    return results
