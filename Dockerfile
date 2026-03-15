FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src/ src/
COPY config/ config/

RUN pip install --no-cache-dir \
    $(python3 -c "import tomllib; print(' '.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))")

ENV PYTHONPATH=/app/src

ENTRYPOINT ["python", "-m"]
CMD ["claire_directllm.ask", "--help"]
