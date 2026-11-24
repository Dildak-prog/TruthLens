FROM python:3.11-slim
WORKDIR /app
ENV PORT=7860
ENV HF_HOME=/tmp/huggingface
ENV HF_HUB_ENABLE_HF_TRANSFER=0
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 7860
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
