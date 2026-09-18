import gzip
import json
import logging
import os
from typing import Optional

import numpy as np
import requests

logger = logging.getLogger(__name__)

DEFAULT_DATASET_REPO = "hitenvk22/CodeSecAudit-RAG-Shuffled"
DEFAULT_CORPUS_FILE = "rag/rag_corpus.jsonl.gz"
# Display label only — vectors come from the ONNX build below.
DEFAULT_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_ONNX_REPO = "Xenova/all-MiniLM-L6-v2"
DEFAULT_ONNX_FILE = "onnx/model_quantized.onnx"
DEFAULT_TOKENIZER_REPO = "sentence-transformers/all-MiniLM-L6-v2"


class OnnxEmbedder:
    """MiniLM embedder on ONNX Runtime + HF tokenizers — no torch.

    Replicates sentence-transformers mean-pooling for all-MiniLM-L6-v2
    (masked average of last hidden state, L2-normalized), so vectors stay
    cosine-compatible with the previous PyTorch backend at ~1/3 the RAM.
    """

    def __init__(self, onnx_repo: str, onnx_file: str, tokenizer_repo: str):
        from huggingface_hub import hf_hub_download
        import onnxruntime as ort
        from tokenizers import Tokenizer

        logger.info("Downloading ONNX weights: %s/%s", onnx_repo, onnx_file)
        model_path = hf_hub_download(repo_id=onnx_repo, filename=onnx_file)

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
        opts.log_severity_level = 3
        self.session = ort.InferenceSession(
            model_path, sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self._input_names = [i.name for i in self.session.get_inputs()]

        self.tokenizer = Tokenizer.from_pretrained(tokenizer_repo)
        self.tokenizer.enable_truncation(max_length=256)
        self.tokenizer.enable_padding()
        logger.info("ONNX embedder ready (inputs=%s)", self._input_names)

    def encode(self, texts, batch_size: int = 64) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        outs = []
        for i in range(0, len(texts), batch_size):
            outs.append(self._encode_batch(texts[i : i + batch_size]))
        return np.concatenate(outs) if outs else np.zeros((0, 384), dtype=np.float32)

    def _encode_batch(self, batch: list[str]) -> np.ndarray:
        enc = self.tokenizer.encode_batch(batch)
        ids = np.array([e.ids for e in enc], dtype=np.int64)
        mask = np.array([e.attention_mask for e in enc], dtype=np.int64)

        feed: dict = {}
        if "input_ids" in self._input_names:
            feed["input_ids"] = ids
        if "attention_mask" in self._input_names:
            feed["attention_mask"] = mask
        if "token_type_ids" in self._input_names:
            feed["token_type_ids"] = np.array(
                [e.type_ids for e in enc], dtype=np.int64
            )

        last_hidden = self.session.run(None, feed)[0]  # [B, T, H]
        weights = mask[..., None].astype(np.float32)
        summed = (last_hidden * weights).sum(axis=1)
        counts = weights.sum(axis=1).clip(min=1e-9)
        emb = summed / counts
        norms = np.linalg.norm(emb, axis=1, keepdims=True).clip(min=1e-12)
        return (emb / norms).astype(np.float32)


class RagIndex:
    def __init__(self):
        self.dataset_repo: str = os.getenv("RAG_DATASET_REPO", DEFAULT_DATASET_REPO)
        self.corpus_file: str = os.getenv("RAG_CORPUS_FILE", DEFAULT_CORPUS_FILE)
        self.embed_model_name: str = os.getenv("RAG_EMBEDDING_MODEL", DEFAULT_EMBED_MODEL)
        self.onnx_repo: str = os.getenv("RAG_ONNX_REPO", DEFAULT_ONNX_REPO)
        self.onnx_file: str = os.getenv("RAG_ONNX_FILE", DEFAULT_ONNX_FILE)
        self.tokenizer_repo: str = os.getenv("RAG_TOKENIZER_REPO", DEFAULT_TOKENIZER_REPO)
        self.max_results: int = int(os.getenv("RAG_MAX_RESULTS", "8"))

        self._embedder: Optional[OnnxEmbedder] = None
        self._chunks: list[dict] = []
        self._embeddings: Optional[np.ndarray] = None

    @property
    def embedder(self) -> OnnxEmbedder:
        if self._embedder is None:
            logger.info("Loading ONNX embedder: %s/%s", self.onnx_repo, self.onnx_file)
            self._embedder = OnnxEmbedder(self.onnx_repo, self.onnx_file, self.tokenizer_repo)
        return self._embedder

    def load_corpus(self) -> int:
        url = f"https://huggingface.co/datasets/{self.dataset_repo}/resolve/main/{self.corpus_file}"
        logger.info("Downloading corpus from %s", url)
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        raw = gzip.decompress(resp.content)
        chunks = []
        for line in raw.decode("utf-8").splitlines():
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
        self._chunks = chunks
        logger.info("Loaded %d chunks", len(chunks))
        return len(chunks)

    def build_index(self) -> None:
        logger.info("Embedding %d chunks (%s) ...", len(self._chunks), self.onnx_file)
        texts = [c.get("content", "") or c.get("text", "") for c in self._chunks]
        self._embeddings = self.embedder.encode(texts)
        logger.info("Index built: shape=%s", self._embeddings.shape)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        if self._embeddings is None or not self._chunks:
            return []

        k = min(top_k, self.max_results, len(self._chunks))
        query_vec = self.embedder.encode([query])[0]
        scores = np.dot(self._embeddings, query_vec) / (
            np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(query_vec) + 1e-12
        )
        top_indices = np.argsort(scores)[::-1][:k]

        results = []
        for rank, idx in enumerate(top_indices, 1):
            c = self._chunks[idx]
            results.append({
                "rank": rank,
                "score": float(scores[idx]),
                "title": c.get("title", ""),
                "section_title": c.get("section_title", "") or c.get("section", ""),
                "cwe_id": c.get("cwe_id", ""),
                "content": c.get("content", "") or c.get("text", ""),
                "source_file": c.get("source_file", "") or c.get("source", ""),
            })
        return results

    @property
    def is_loaded(self) -> bool:
        return self._embeddings is not None

    @property
    def embedding_count(self) -> int:
        return len(self._embeddings) if self._embeddings is not None else 0

    @property
    def document_count(self) -> int:
        return len(self._chunks)

    @property
    def total_chunks(self) -> int:
        return len(self._chunks)
