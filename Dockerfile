FROM prom/prometheus:v3.15.0 AS prometheus
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN useradd --uid 10001 --create-home academy
COPY --from=prometheus /bin/prometheus /app/.tools/prometheus
COPY --from=prometheus /bin/promtool /app/.tools/promtool
COPY pyproject.toml ./
COPY academy ./academy
RUN pip install --no-cache-dir .
COPY . .
RUN mkdir -p /app/.runtime && chown -R academy:academy /app
USER academy
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
