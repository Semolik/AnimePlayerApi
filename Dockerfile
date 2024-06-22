FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

CMD uvicorn src.main:app --host 0.0.0.0 --reload --port 8000