# CLAIRE-DirectLLM Docker

Containerized distribution of [CLAIRE-DirectLLM](https://github.com/jkirc001/CLAIRE-DirectLLM) -- the direct LLM baseline for cybersecurity question answering.

> **WARNING: Do not use this system for real cybersecurity analysis. Answers are likely to be incorrect or hallucinated.** This is the direct LLM baseline for the CLAIRE project, provided solely for comparative evaluation against [CLAIRE-KG-Docker](https://github.com/jkirc001/CLAIRE-KG-Docker). For reliable results, use CLAIRE-KG-Docker.

Sends questions directly to OpenAI with no knowledge graph, no RAG, and no database. Exists to compare against CLAIRE-KG and CLAIRE-RAG.

## Prerequisites

- Docker (with Docker Compose)
- OpenAI API key

## Quick Start

```bash
git clone https://github.com/jkirc001/CLAIRE-DirectLLM-Docker.git
cd CLAIRE-DirectLLM-Docker
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY
./ask "What is CWE-79?"
```

## Usage

### Ask a question

```bash
./ask "What is CWE-79?"
./ask "What is SQL injection?" --debug
./ask "Explain buffer overflow" --model gpt-4o
```

### Compare models

```bash
./compare "What is CWE-79?"
./compare "What is SQL injection?" --debug
./compare "Explain XSS" --models "gpt-4o,gpt-4o-mini"
```

### CLI Options

**ask:**
- `--debug` -- Show token usage, cost estimates, system message, and prompt
- `--model`, `-m` -- Override model (e.g., gpt-4o, gpt-5.2)
- `--eval` -- Use evaluation mode (forces gpt-4o)
- `--stub` -- Stub mode, no API calls

**compare:**
- `--debug` -- Show detailed token/cost info per model
- `--models`, `-m` -- Comma-separated model list (default: all allowed models)
- `--output`, `-o` -- Save results to JSON file

## Building Locally

```bash
docker compose build app
```

The `docker-compose.override.yml` file (not tracked by git) enables local builds. To use the pre-built GHCR image instead, remove or rename the override file.

## Source

Application source is pinned to commit `375a60e3c85a354e754a700d97f53877b00a2515` of the main [CLAIRE-DirectLLM](https://github.com/jkirc001/CLAIRE-DirectLLM) repository.
