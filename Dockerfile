FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt
RUN useradd --create-home --uid 10001 labuser && mkdir /data && chown labuser:labuser /data
COPY lab.py api.py ./
USER labuser
ENV AUDIT_DB=/data/audit.sqlite PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)"
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]

