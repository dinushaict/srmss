# Hugging Face Spaces (Docker) deployment for SRMSS.
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Hugging Face Spaces routes traffic to port 7860.
ENV PORT=7860
EXPOSE 7860

CMD ["python", "run.py"]
