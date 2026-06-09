FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt --break-system-packages

COPY . /app

ENV HOST=0.0.0.0
ENV PORT=8000

CMD ["bash", "-lc", "uvicorn app.main:app --host ${HOST} --port ${PORT}"]

