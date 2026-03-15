"""LLM integration module for CLAIRE-DirectLLM."""

from claire_directllm.llm.client import LLMClient, get_llm_client
from claire_directllm.llm.prompts import build_direct_prompt

__all__ = ["LLMClient", "get_llm_client", "build_direct_prompt"]

