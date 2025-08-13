from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple


@dataclass
class Message:
    role: str
    content: str


class ShortTermMemory:
    def __init__(self) -> None:
        self._messages: List[Message] = []

    def add(self, role: str, content: str) -> None:
        self._messages.append(Message(role=role, content=content))

    def history(self) -> List[Message]:
        return list(self._messages)


class LongTermMemory:
    def __init__(self, path: str) -> None:
        self.path = path
        self._docs: List[Dict] = []
        self._index: Dict[str, List[Tuple[int, float]]] = {}
        self._doc_len: List[int] = []
        self._df: Dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            self._save()
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._docs = data.get("docs", [])
        except Exception:
            self._docs = []
        self._rebuild_index()

    def _save(self) -> None:
        data = {"docs": self._docs}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _tokenize(self, text: str) -> List[str]:
        text = text.lower()
        text = re.sub(r"[^a-záéíóúüñ0-9 ]+", " ", text)
        return [t for t in text.split() if t]

    def _rebuild_index(self) -> None:
        self._index.clear()
        self._df.clear()
        self._doc_len = []
        for i, doc in enumerate(self._docs):
            tokens = self._tokenize(doc.get("text", ""))
            self._doc_len.append(len(tokens))
            seen = set()
            for token in tokens:
                self._index.setdefault(token, []).append((i, 1.0))
                if token not in seen:
                    self._df[token] = self._df.get(token, 0) + 1
                    seen.add(token)

    def add_document(self, text: str, metadata: Dict | None = None) -> int:
        doc = {"text": text, "metadata": metadata or {}}
        self._docs.append(doc)
        self._save()
        self._rebuild_index()
        return len(self._docs) - 1

    def search(self, query: str, k: int = 5) -> List[Dict]:
        tokens = self._tokenize(query)
        scores: Dict[int, float] = {}
        N = max(1, len(self._docs))
        for token in tokens:
            postings = self._index.get(token, [])
            df = max(1, self._df.get(token, 0))
            idf = math.log((N + 1) / df)
            for doc_id, _ in postings:
                scores[doc_id] = scores.get(doc_id, 0.0) + idf
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:k]
        return [
            {"doc_id": doc_id, "score": round(score, 3), "text": self._docs[doc_id]["text"], "metadata": self._docs[doc_id].get("metadata", {})}
            for doc_id, score in ranked
        ]