FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt 'scikit-learn==1.6.1'
COPY *.py pl.json icon.png ./
COPY data/catalog.json data/sentiment.json data/historical_events.json ./data/
COPY ml/regime_model.pkl ./ml/
COPY logs/regime_report.json logs/regime_report.txt ./logs/
COPY deploy/container_start.py ./deploy/container_start.py
RUN useradd --system --create-home --uid 10001 blackbox && chown -R blackbox:blackbox /app
USER blackbox
EXPOSE 8090
CMD ["python", "deploy/container_start.py"]
