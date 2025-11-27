FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
RUN pip install --no-cache-dir pip && pip install .
COPY raeburn_brain raeburn_brain
RUN adduser --disabled-password --gecos "" --uid 1001 appuser \
    && chown -R appuser:appuser /app
USER appuser
CMD ["uvicorn", "raeburn_brain.server:create_app", "--host", "0.0.0.0", "--port", "8080"]
