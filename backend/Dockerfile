FROM python:3.11-slim

WORKDIR /app

RUN useradd -m -u 10001 appuser
COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
