FROM python:3.11-slim

WORKDIR /app

# Build context = rag-service/  (contains rag_service/ package)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . ./

ENV RAG_BUILD_ON_START=true
ENV RAG_DATASET_REPO=hitenvk22/CodeSecAudit-RAG-Shuffled
ENV RAG_CORPUS_FILE=rag/rag_corpus.jsonl.gz
ENV RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
ENV RAG_ONNX_REPO=Xenova/all-MiniLM-L6-v2
ENV RAG_ONNX_FILE=onnx/model_quantized.onnx
ENV TOKENIZERS_PARALLELISM=false

EXPOSE 7860

# Honor Render's $PORT (defaults to 10000 there); local default stays 7860.
CMD ["sh", "-c", "uvicorn rag_service.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
