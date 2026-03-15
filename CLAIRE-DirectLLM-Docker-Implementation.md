# CLAIRE-DirectLLM-Docker Implementation Document

## 1. Project Overview

CLAIRE-DirectLLM-Docker is a containerized distribution of the CLAIRE-DirectLLM system, which sends cybersecurity questions directly to OpenAI's API with no retrieval, no knowledge graph, and no database. It serves as the simplest baseline for the CLAIRE project's comparative evaluation.

The system exists solely to compare against CLAIRE-KG (knowledge graph approach) and CLAIRE-RAG (retrieval-augmented generation). It is not intended for production cybersecurity analysis -- testing showed a 10% automated pass rate and 15% human-validated pass rate on cross-framework queries, compared to 100%/95% for CLAIRE-KG.

### Repository

- GitHub: https://github.com/jkirc001/CLAIRE-DirectLLM-Docker
- Source pinned to commit `375a60e3c85a354e754a700d97f53877b00a2515` of the main [CLAIRE-DirectLLM](https://github.com/jkirc001/CLAIRE-DirectLLM) repository.

---

## 2. Development Environment

### Hardware

- **Machine:** MacBook Pro 16-inch, 2019 ([specs](https://support.apple.com/en-us/111932))
- **CPU:** 2.3 GHz 8-Core Intel Core i9
- **Graphics:** AMD Radeon Pro 5500M 4 GB, Intel UHD Graphics 630 1536 MB
- **Memory:** 32 GB 2667 MHz DDR4
- **OS:** macOS Sequoia 15.7.4 (Darwin 24.6.0)

### Software

- **Docker:** Docker Desktop for Mac with Docker Compose v2
- **Python (container):** 3.13-slim (Debian base)
- **Build system:** uv_build (source repo uses uv; Docker image installs dependencies directly via pip)
- **Package manager (source repo):** uv
- **Container registry:** GitHub Container Registry (GHCR) at `ghcr.io/jkirc001/claire-directllm-app`
- **CI/CD:** GitHub Actions (not yet configured)

---

## 3. Architecture

### 3.1 System Design

CLAIRE-DirectLLM is the simplest of the three CLAIRE systems. It has no retrieval pipeline, no vector database, and no re-ranking. The full architecture is:

1. User submits a question via the `./ask` wrapper script
2. The question is wrapped in a minimal prompt (no context injection)
3. The prompt is sent to OpenAI with a cybersecurity system message
4. The raw LLM response is returned to the user

This means the system relies entirely on the LLM's parametric knowledge (training data) with no grounding in external data. This is the fundamental limitation the CLAIRE project is designed to expose.

### 3.2 Compare Mode

A second CLI command (`./compare`) sends the same question to multiple models and displays results side-by-side. This is useful for evaluating how different models perform on the same cybersecurity query. It extracts CVSS scores from answers when present and displays token usage and cost estimates.

### 3.3 Data Flow

```
User -> ./ask script -> docker compose run --rm -> Python CLI -> OpenAI API -> stdout
```

Unlike CLAIRE-RAG-Docker (which runs a persistent FastAPI server), CLAIRE-DirectLLM-Docker uses the simple `docker compose run --rm` pattern. This is acceptable because there are no ML models to load -- the only latency is the OpenAI API call itself (~1-3s).

---

## 4. Package Structure

```
CLAIRE-DirectLLM-Docker/
  src/
    claire_directllm/
      __init__.py                # Package init, version 0.1.0
      ask.py                     # CLI for asking questions (typer + rich)
      compare_models.py          # CLI for multi-model comparison
      llm/
        __init__.py              # Exports LLMClient, get_llm_client, build_direct_prompt
        client.py                # OpenAI client with config, cost calculation, model validation
        prompts.py               # Prompt builder (minimal, no context)
  config/
    settings.yaml                # LLM provider, model, temperature, max_tokens
    models.yaml                  # Allowed models list, evaluation model
  ask                            # Wrapper script for asking questions
  compare                        # Wrapper script for model comparison
  Dockerfile
  docker-compose.yml
  docker-compose.override.yml    # Local build override (gitignored)
  pyproject.toml
  .env.example
  .gitignore
  .dockerignore
  VERSION                        # Pinned source commit SHA
  LICENSE                        # GPL-3.0
  README.md
  notes.md                       # Development rules (gitignored in some contexts)
  docker-plan.md                 # Implementation plan
```

---

## 5. Dependencies and Library Choices

### 5.1 Runtime Dependencies

| Library | Version Constraint | Purpose | Decision Rationale |
|---------|-------------------|---------|-------------------|
| `openai` | `>=2.11.0` | OpenAI API client | v2.x API for chat completions. Newer than CLAIRE-RAG (which uses v1.x) because DirectLLM was built later and needs support for newer models (gpt-5.x, o1). |
| `pydantic` | `>=2.12.5` | Data validation | Used internally by the OpenAI client and for structured data. |
| `python-dotenv` | `>=1.2.1` | Environment variable loading from .env | Loads OPENAI_API_KEY. |
| `pyyaml` | `>=6.0.3` | YAML config file parsing | Reads settings.yaml and models.yaml. |
| `tiktoken` | `>=0.12.0` | Token counting for cost estimation | Used in stub mode to estimate token counts. |
| `typer` | `>=0.20.0` | CLI framework | Provides argument parsing and help text for ask and compare commands. |
| `rich` | (transitive via typer) | Terminal formatting | Used for colored output, tables, and panels in the CLI. |

### 5.2 Key Difference from CLAIRE-RAG-Docker

CLAIRE-DirectLLM has **no ML dependencies** -- no PyTorch, no sentence-transformers, no HuggingFace models. This makes the Docker image dramatically smaller and eliminates the cold start problem that required server mode in CLAIRE-RAG-Docker.

### 5.3 Build System

The source repository uses `uv_build` as the build backend. In the Docker image, dependencies are installed directly via pip by parsing `pyproject.toml` with Python's `tomllib` module rather than using `pip install .`. This avoids needing to install uv or change the build backend.

```dockerfile
RUN pip install --no-cache-dir \
    $(python3 -c "import tomllib; print(' '.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))")
```

This approach reads the dependency list from `pyproject.toml` and installs them directly, bypassing the build system entirely.

---

## 6. Docker Implementation

### 6.1 Base Image

`python:3.13-slim` was chosen because:
- DirectLLM has no PyTorch dependency, so Python 3.13 compatibility is not a concern
- The `-slim` variant minimizes image size
- No C/C++ compilers needed (no native extensions to build)

### 6.2 Dockerfile

The Dockerfile is minimal:

1. Copy `pyproject.toml`, `src/`, and `config/`
2. Install dependencies by parsing pyproject.toml
3. Set `PYTHONPATH=/app/src` so Python can find the `claire_directllm` package
4. Set entrypoint to `python -m` with default command `claire_directllm.ask --help`

### 6.3 Image Size

The Docker image is small compared to CLAIRE-RAG-Docker (~2.93 GB):

- Python 3.13-slim base: ~150 MB
- OpenAI + dependencies: ~100 MB
- Application source: <1 MB
- **Estimated total: ~300-400 MB**

### 6.4 No Server Mode Needed

Unlike CLAIRE-RAG-Docker, there is no need for a persistent server. The system has no ML models to load -- every invocation is just a Python process that makes an API call. The `docker compose run --rm` pattern is appropriate here because:

- No cold start penalty (no model loading)
- Each query is independent
- Container startup + API call is ~2-3s total

### 6.5 Docker Compose Configuration

The `docker-compose.yml` defines a single service with no ports, no volumes, no healthchecks:

- **Image:** `ghcr.io/jkirc001/claire-directllm-app:latest`
- **Environment:** Loaded from `.env` file (contains `OPENAI_API_KEY`)

A `docker-compose.override.yml` (gitignored) adds `build: .` for local development.

---

## 7. Wrapper Scripts

### 7.1 `./ask`

The ask script:
1. Loads environment variables from `.env`
2. Validates `OPENAI_API_KEY` is set
3. Runs `docker compose run --rm app claire_directllm.ask "$@"`

The entrypoint is `python -m`, so passing `claire_directllm.ask` as the first argument runs the ask module.

### 7.2 `./compare`

The compare script:
1. Loads environment variables from `.env`
2. Validates `OPENAI_API_KEY` is set
3. Runs `docker compose run --rm app claire_directllm.compare_models "$@"`

### 7.3 Supported CLI Options

**ask:**

| Flag | Default | Description |
|------|---------|-------------|
| `--debug` | false | Show token usage, cost estimates, system message, and prompt |
| `--model`, `-m` | gpt-4o-mini | Override model (e.g., gpt-4o, gpt-5.2) |
| `--eval` | false | Evaluation mode (forces gpt-4o) |
| `--stub` | false | Stub mode, no API calls |

**compare:**

| Flag | Default | Description |
|------|---------|-------------|
| `--debug` | false | Show detailed token/cost info per model |
| `--models`, `-m` | all allowed | Comma-separated model list |
| `--output`, `-o` | (none) | Save results to JSON file |

---

## 8. Configuration

### 8.1 settings.yaml

| Setting | Value | Description |
|---------|-------|-------------|
| `llm.provider` | `openai` | LLM provider |
| `llm.model` | `gpt-4o-mini` | Default model for development mode |
| `llm.temperature` | `0.2` | Low temperature for consistent answers |
| `llm.max_tokens` | `2048` | Maximum response tokens |

### 8.2 models.yaml

**Allowed models:** gpt-4o, gpt-4o-mini, gpt-4.1-mini, gpt-4.1, gpt-5, gpt-5-mini, gpt-5.1, gpt-5.2

**Evaluation model:** gpt-4o

The allowed models list is broader than CLAIRE-RAG because DirectLLM was built later and includes newer model families (gpt-5.x).

### 8.3 Config Path Resolution

Configuration files are resolved using `Path(__file__).parent.parent.parent.parent / "config"`, navigating from `src/claire_directllm/llm/client.py` up to the project root. With `PYTHONPATH=/app/src`, the source is at `/app/src/claire_directllm/llm/client.py`, so config resolves to `/app/config/`.

### 8.4 Model-Specific API Parameter Handling

The LLM client handles differences between OpenAI model generations:

- **Newer models (gpt-5.x, o1, gpt-4.1):** Use `max_completion_tokens` instead of `max_tokens`
- **Some models (gpt-5, gpt-5-mini):** Do not accept custom temperature values (default 1.0 only)
- **Cost calculation:** Includes estimated pricing for newer models

### 8.5 System Message

All queries use the system message: `"You are an expert cybersecurity knowledge assistant."`

This is the same system message used by CLAIRE-RAG and CLAIRE-KG, ensuring a fair comparison across the three systems.

---

## 9. Decisions Made During Implementation

### 9.1 Direct pip Install Instead of Build Backend

The source repo uses `uv_build` as the build backend, which is not compatible with standard `pip install .`. Rather than changing the build backend to `hatchling` (as recommended in the plan), the Dockerfile parses `pyproject.toml` directly with `tomllib` to extract the dependency list and installs packages individually. This avoids modifying the source repo's build configuration.

### 9.2 No Server Mode

The plan did not include a server mode, and none was added. Since there are no ML models to load, each invocation starts in <1 second. The `docker compose run --rm` pattern is sufficient.

### 9.3 ENTRYPOINT Design

The Dockerfile uses `ENTRYPOINT ["python", "-m"]` with `CMD ["claire_directllm.ask", "--help"]`. This allows the wrapper scripts to pass different module names:
- `./ask` passes `claire_directllm.ask "question"`
- `./compare` passes `claire_directllm.compare_models "question"`

This is different from CLAIRE-RAG-Docker (which uses a specific entrypoint) because DirectLLM has two distinct CLI commands.

### 9.4 PYTHONPATH Instead of pip install

The source code lives in `src/claire_directllm/` (src layout). Instead of installing the package with pip, the Dockerfile sets `ENV PYTHONPATH=/app/src`. This allows `python -m claire_directllm.ask` to find the package directly. This avoids build system complications with uv_build.

### 9.5 Python 3.13 (Not 3.11)

Unlike CLAIRE-RAG-Docker (which requires Python 3.11 for PyTorch compatibility), DirectLLM has no ML dependencies and can use the latest Python. Python 3.13-slim provides a smaller base image and includes `tomllib` in the standard library (used for parsing pyproject.toml in the Dockerfile).

### 9.6 Broader Model Support

The `models.yaml` includes gpt-5.x and o1 models that don't appear in CLAIRE-RAG's config. This reflects that DirectLLM was developed later and is designed to test against the latest available models. The client handles API differences between model generations automatically.

### 9.7 Rich Terminal Output

DirectLLM uses the `rich` library (via typer) for formatted terminal output including colored text, panels, and tables. CLAIRE-RAG uses plain text output. This difference exists because DirectLLM was developed with a different focus on the comparison/debugging experience.

### 9.8 No Data Files

Unlike CLAIRE-RAG-Docker (which requires a 330 MB vectorstore download), CLAIRE-DirectLLM-Docker has no data files at all. There is no `fetch-vectorstore.sh` equivalent, no GitHub Release data asset, and no volume mounts. This is the key architectural simplification.

---

## 10. Comparison with CLAIRE-RAG-Docker

| Aspect | CLAIRE-DirectLLM-Docker | CLAIRE-RAG-Docker |
|--------|------------------------|-------------------|
| **Purpose** | Direct LLM baseline (no retrieval) | RAG baseline (vector search + re-ranking) |
| **Database** | None | ChromaDB (file-based, 330 MB) |
| **ML Models** | None | sentence-transformers + cross-encoder (~160 MB) |
| **PyTorch** | Not required | CPU-only torch 2.1.2 |
| **Image Size** | ~300-400 MB | ~2.93 GB |
| **Python Version** | 3.13 | 3.11 (torch compatibility) |
| **Runtime Mode** | CLI per invocation (`docker compose run --rm`) | Persistent FastAPI server |
| **Cold Start** | <1s (no models to load) | ~10s (PyTorch + HF model loading) |
| **Per-Query Time** | 1-3s (OpenAI API only) | 3-6s (retrieval + ranking + OpenAI API) |
| **Data Download** | None | vectorstore.tar.gz (176 MB) |
| **Volume Mounts** | None | ./vectorstore:/app/vectorstore |
| **Ports** | None | 8000 (FastAPI) |
| **Healthcheck** | None | HTTP GET /health |
| **Docker Services** | Single (run and exit) | Single (persistent) |
| **Wrapper Scripts** | `./ask`, `./compare` | `./ask` |
| **Build Backend** | uv_build (bypassed with PYTHONPATH) | hatchling |
| **OpenAI SDK** | v2.x (>=2.11.0) | v1.x (>=1.0.0) |

---

## 11. CI/CD Pipeline

### 11.1 Current State

The GitHub Actions workflow for automated GHCR builds has not yet been configured. The `.github/workflows/` directory exists but contains no workflow files. The `docker-compose.override.yml` enables local builds as a workaround.

### 11.2 Planned Workflow

When implemented, the workflow should mirror CLAIRE-RAG-Docker's approach:
- Trigger on GitHub Release publish
- Build multi-arch images (linux/amd64 + linux/arm64) via QEMU
- Push to GHCR at `ghcr.io/jkirc001/claire-directllm-app`
- Tag with semver + `latest`

---

## 12. Git History

```
3b0c2c0 Add warning about unreliable answers to README
1efa9db Initial CLAIRE-DirectLLM Docker distribution
6e8832f Initial commit
```

---

## 13. Files Copied from Source Repository

**Included:**
- `src/claire_directllm/` -- Complete application source package
- `config/settings.yaml` -- Runtime configuration
- `config/models.yaml` -- Model configuration and allowed models list
- `pyproject.toml` -- Build configuration and dependencies
- `LICENSE` -- GPL-3.0

**Excluded:**
- `docs/` -- Documentation
- `tests/` -- Test suite
- `.taskmaster/` -- Task management
- `.cursor/` -- IDE config
- `config/.env`, `config/.env.example` -- Replaced by root-level `.env`
- `test_results.json`, `test_cvss.json`, `all_models_test.json` -- Test output files
- `TEST_SUMMARY_EMAIL.md`, `CLAIRE-DirectLLM-JSON-Schema.md` -- Documentation
- `uv.lock` -- uv lockfile
- `.venv/` -- Virtual environment

**Added for Docker distribution:**
- `ask` -- Wrapper script for questions
- `compare` -- Wrapper script for model comparison
- `Dockerfile`
- `docker-compose.yml`
- `docker-compose.override.yml`
- `.env.example`, `.gitignore`, `.dockerignore`
- `VERSION`
- `README.md`
- `notes.md`
- `docker-plan.md`
