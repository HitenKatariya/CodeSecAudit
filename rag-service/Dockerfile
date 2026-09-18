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

EXPOSE 7860

CMD ["uvicorn", "rag_service.main:app", "--host", "0.0.0.0", "--port", "7860"]
