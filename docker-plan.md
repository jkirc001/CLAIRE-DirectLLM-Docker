# CLAIRE-DirectLLM Docker Distribution Plan

**Purpose:** Deliver CLAIRE-DirectLLM as a containerized experience. End users need only Docker and an OpenAI API key to ask cybersecurity questions directly to an LLM (no database, no retrieval).

**Audience:** An intern or contractor implementing the Docker distribution.

**Decision context:** Separate repo (fresh, not a fork) to keep the main CLAIRE-DirectLLM repo focused on research.

---

## 1. Background: What CLAIRE-DirectLLM Is

CLAIRE-DirectLLM is the **direct LLM baseline** for the CLAIRE project. It sends cybersecurity questions directly to OpenAI (no knowledge graph, no RAG) and returns answers. It exists to compare against CLAIRE-KG and CLAIRE-RAG.

**How it runs today:**
- User runs `uv run python -m claire_directllm.ask "question"` on the host
- Requires Python 3.11+, uv, and dependencies from `pyproject.toml`
- Needs `OPENAI_API_KEY` in `.env` or environment
- Reads config from `config/models.yaml` and `config/settings.yaml`
- No database, no data files, no external services except OpenAI

**Two CLI commands:**
- `ask "question"` -- ask a single question
- `compare_models "question"` -- test the same question across multiple models

---

## 2. Goal

The new repository should provide:

1. **App in a container** -- the CLI runs inside Docker. No Python or uv needed on the host.
2. **Single dependency: Docker** -- plus an OpenAI API key.
3. **Simple:** No database, no data download, no dump restore. Just build/pull and run.

---

## 3. What the New Repo Must Deliver

| Deliverable | Description |
|-------------|-------------|
| **Dockerfile** | Python 3.13-slim, copy `src/`, `config/`, `pyproject.toml`, `README.md`, run `pip install .`. Entrypoint: `python -m claire_directllm.ask`. |
| **docker-compose.yml** | Single app service. `env_file: .env` for OPENAI_API_KEY. No other services needed. Default to GHCR image. |
| **docker-compose.override.yml** | For local builds (not committed to git). |
| **.env.example** | `OPENAI_API_KEY=` |
| **.dockerignore** | Exclude .git, tests, docs, .env, etc. |
| **README** | How to set API key, run ask, run compare_models. Link to main repo. |
| **ask wrapper script** | `./ask "question"` that runs `docker compose run --rm app ask "$@"`. Check for OPENAI_API_KEY. |
| **compare wrapper script** | `./compare "question"` that runs `docker compose run --rm app compare_models "$@"`. |
| **VERSION** | Pinned commit SHA from main repo. |
| **GitHub Action + GHCR** | Multi-arch build on release, push to GHCR. |

---

## 4. Technical Plan

### 4.1 What Makes This Simpler Than CLAIRE-KG-Docker

- No database (no Neo4j, no healthchecks, no dump restore)
- No data files to download
- No entrypoint scripts
- Single container, no compose networking concerns
- Config files (`config/models.yaml`, `config/settings.yaml`) are small and can be baked into the image

### 4.2 Dockerfile

```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ src/
COPY config/ config/
RUN pip install --no-cache-dir .
ENTRYPOINT ["python", "-m", "claire_directllm.ask"]
CMD ["--help"]
```

**Important:** The app loads config from `config/` relative to the source. The config directory must be in the image. Check `client.py` to verify how config paths are resolved -- if it uses `__file__`-based paths, `config/` must be at the right relative location. If it uses CWD, set WORKDIR appropriately.

### 4.3 Docker Compose

```yaml
services:
  app:
    image: ghcr.io/jkirc001/claire-directllm-app:latest
    container_name: claire-directllm-app
    env_file: .env
```

No ports, no volumes, no healthchecks, no depends_on. Just run and exit.

### 4.4 Wrapper Scripts

**ask:**
```bash
#!/bin/bash
set -e
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
fi
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY is not set."
    exit 1
fi
docker compose run --rm app "$@"
```

**compare:**
```bash
#!/bin/bash
set -e
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
fi
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OPENAI_API_KEY is not set."
    exit 1
fi
docker compose run --rm --entrypoint "python -m claire_directllm.compare_models" app "$@"
```

### 4.5 Files to Copy from Main Repo

**Include:**
- `src/` -- application source
- `config/models.yaml` -- model configuration
- `config/settings.yaml` -- LLM settings
- `pyproject.toml` -- build config
- `uv.lock` -- optional, for reference
- `LICENSE`

**Omit:**
- `docs/`, `tests/`, `.cursor/`, `.taskmaster/`
- `config/.env`, `config/.env.example` (create new `.env.example` in repo root)
- `test_results.json`, `test_cvss.json`, `all_models_test.json`
- `TEST_SUMMARY_EMAIL.md`, `CLAIRE-DirectLLM-JSON-Schema.md`
- Any IDE or local config

### 4.6 Build System Note

The main repo uses `uv_build` as build backend in `pyproject.toml`:
```toml
[build-system]
requires = ["uv_build>=0.8.17,<0.9.0"]
build-backend = "uv_build"
```

The Docker image uses `pip install .` which needs a pip-compatible build backend. Either:
- Install `uv` in the image and use `uv pip install .`, or
- Change the build-backend to `hatchling` in the Docker repo's copy of pyproject.toml

Recommend changing to `hatchling` (same as CLAIRE-KG-Docker) to keep it simple.

---

## 5. Step-by-Step Implementation Checklist

- [ ] **5.1** Create new empty GitHub repo `CLAIRE-DirectLLM-Docker`.
- [ ] **5.2** Copy `src/`, `config/models.yaml`, `config/settings.yaml`, `pyproject.toml`, `uv.lock`, `LICENSE` from main repo. Do not copy docs, tests, or config/.env.
- [ ] **5.3** Update `pyproject.toml` build-backend from `uv_build` to `hatchling` if needed.
- [ ] **5.4** Create `.env.example` (repo root), `.gitignore`, `.dockerignore`.
- [ ] **5.5** Write Dockerfile. Build and test: `docker build -t claire-directllm-app:dev .`
- [ ] **5.6** Write `docker-compose.yml` (GHCR image default) and `docker-compose.override.yml` (local build, gitignored).
- [ ] **5.7** Write `ask` and `compare` wrapper scripts. Make executable.
- [ ] **5.8** Write Docker-only README.
- [ ] **5.9** Create `VERSION` file with pinned commit SHA from main repo.
- [ ] **5.10** Test end-to-end: `./ask "What is CWE-79?"` should return a direct LLM answer.
- [ ] **5.11** Set up GitHub Action for multi-arch GHCR builds on release.
- [ ] **5.12** Create first release to trigger GHCR build. Verify `docker compose pull app` works.

---

## 6. End User Experience

```bash
git clone https://github.com/jkirc001/CLAIRE-DirectLLM-Docker.git
cd CLAIRE-DirectLLM-Docker
cp .env.example .env
# Edit .env and set OPENAI_API_KEY
./ask "What is CWE-79?"
./compare "What is SQL injection?" --debug
```

No data downloads, no database setup, no waiting for services to start.
