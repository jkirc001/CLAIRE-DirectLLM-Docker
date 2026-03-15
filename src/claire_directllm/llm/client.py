"""LLM client for direct question answering without retrieval."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from openai import OpenAI

# System message for the LLM
SYSTEM_MESSAGE = "You are an expert cybersecurity knowledge assistant."


def _load_config(config_dir: Path | None, filename: str) -> dict[str, Any]:
    """Load a YAML configuration file."""
    if config_dir is None:
        config_dir = Path(__file__).parent.parent.parent.parent / "config"
    config_path = config_dir / filename
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path) as f:
        return yaml.safe_load(f)


def _get_model_pricing(model: str) -> tuple[float, float]:
    """
    Get pricing for a model in dollars per 1M tokens (input, output).

    Returns:
        Tuple of (input_price_per_1M, output_price_per_1M)
    """
    pricing = {
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4.1-mini": (0.15, 0.60),  # Use same pricing as gpt-4o-mini
        "gpt-4.1": (2.50, 10.00),  # Estimated, update with actual pricing
        "gpt-5": (5.00, 15.00),  # Estimated, update with actual pricing
        "gpt-5-mini": (0.30, 1.20),  # Estimated, update with actual pricing
        "gpt-5-pro": (10.00, 30.00),  # Estimated, update with actual pricing
        "gpt-5.1": (5.00, 15.00),  # Estimated, update with actual pricing
        "gpt-5.2": (5.00, 15.00),  # Estimated, update with actual pricing
        "gpt-5.2-pro": (10.00, 30.00),  # Estimated, update with actual pricing
        "o1": (15.00, 60.00),  # Estimated, update with actual pricing
        "o1-pro": (30.00, 120.00),  # Estimated, update with actual pricing
    }
    return pricing.get(model, (0.0, 0.0))


class LLMClient:
    """Client for interacting with OpenAI LLM models."""

    def __init__(
        self,
        config_dir: Path | None = None,
        use_stub: bool = False,
        model: str | None = None,
    ):
        """
        Initialize LLM client with configuration.

        Args:
            config_dir: Directory containing config files. If None, uses project config/.
            use_stub: If True, use stub mode (no API calls).
            model: Optional model name to override default/evaluation model.
        """
        self.use_stub = use_stub
        self.config_dir = config_dir or (
            Path(__file__).parent.parent.parent.parent / "config"
        )

        # Load environment variables from config/.env if it exists, otherwise try project root
        # Preserve CLAIRE_ENV if already set (e.g., by --eval flag)
        claire_env_preserved = os.getenv("CLAIRE_ENV")
        env_file = self.config_dir / ".env"
        if env_file.exists():
            # Load from config/.env
            load_dotenv(dotenv_path=str(env_file.resolve()), override=True)
        else:
            # Fall back to project root .env
            load_dotenv()
        # Restore CLAIRE_ENV if it was set before loading .env
        if claire_env_preserved:
            os.environ["CLAIRE_ENV"] = claire_env_preserved

        # Load configuration files
        self.settings = _load_config(self.config_dir, "settings.yaml")
        self.models_config = _load_config(self.config_dir, "models.yaml")

        # Determine mode and model
        if model:
            # Use explicitly provided model
            self.model = model
            self.mode = "custom"  # Mark as custom when model is explicitly set
        else:
            # Use default logic based on mode
            self.mode = os.getenv(
                "CLAIRE_ENV", self.settings.get("mode", "development")
            )
            if self.mode == "evaluation":
                self.model = self.models_config["evaluation_model"]
            else:
                self.model = self.settings["llm"]["model"]

        # Validate model
        allowed_models = self.models_config["allowed_models"]
        if self.model not in allowed_models:
            raise ValueError(
                f"Model '{self.model}' is not in allowed_models: {allowed_models}"
            )

        # Get LLM settings
        llm_settings = self.settings["llm"]
        self.temperature = llm_settings.get("temperature", 0.2)
        self.max_tokens = llm_settings.get("max_tokens", 2048)

        # Store system message
        self.system_message = SYSTEM_MESSAGE

        # Initialize OpenAI client (only if not stub mode)
        if not self.use_stub:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required. "
                    "Set it in .env file or environment."
                )
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = None

    def generate(
        self,
        prompt: str,
        temperature: float | None = None,
        max_tokens: int | None = None,
        return_usage: bool = False,
    ) -> str | tuple[str, dict[str, Any]]:
        """
        Generate text using the configured LLM.

        Args:
            prompt: The prompt to send to the LLM.
            temperature: Override default temperature.
            max_tokens: Override default max_tokens.
            return_usage: If True, return tuple of (text, usage_dict).

        Returns:
            Generated text, or tuple of (text, usage_dict) if return_usage=True.
        """
        if self.use_stub:
            return self.generate_stub(prompt, return_usage)

        temperature = temperature if temperature is not None else self.temperature
        max_tokens = max_tokens if max_tokens is not None else self.max_tokens

        # Some newer models (e.g., gpt-5.2) use max_completion_tokens instead of max_tokens
        # Check if model name suggests it needs the newer parameter
        use_max_completion_tokens = any(
            prefix in self.model for prefix in ["gpt-5", "o1", "gpt-4.1"]
        )

        # Some models (e.g., gpt-5, gpt-5-mini) only support default temperature (1.0)
        # and don't accept custom temperature values
        models_without_temperature = ["gpt-5", "gpt-5-mini"]

        api_params = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": self.system_message,
                },
                {"role": "user", "content": prompt},
            ],
        }

        # Only add temperature if the model supports it
        if not any(
            model_name in self.model for model_name in models_without_temperature
        ):
            api_params["temperature"] = temperature

        if use_max_completion_tokens:
            api_params["max_completion_tokens"] = max_tokens
        else:
            api_params["max_tokens"] = max_tokens

        response = self.client.chat.completions.create(**api_params)

        text = response.choices[0].message.content or ""

        if return_usage:
            usage = response.usage
            usage_dict = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
            return text, usage_dict

        return text

    def generate_stub(
        self, prompt: str, return_usage: bool = False
    ) -> str | tuple[str, dict[str, Any]]:
        """
        Stub implementation for testing without API calls.

        Args:
            prompt: The prompt (ignored in stub mode).
            return_usage: If True, return tuple with mock usage data.

        Returns:
            Mock response text, or tuple of (text, usage_dict) if return_usage=True.
        """
        # Simple mock response
        text = f"[STUB] This is a mock response for the prompt: {prompt[:50]}..."

        if return_usage:
            # Mock usage data
            usage_dict = {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(text.split()),
                "total_tokens": len(prompt.split()) + len(text.split()),
            }
            return text, usage_dict

        return text

    def calculate_cost(self, usage: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate cost based on token usage.

        Args:
            usage: Dictionary with prompt_tokens, completion_tokens, total_tokens.

        Returns:
            Dictionary with cost breakdown.
        """
        input_price, output_price = _get_model_pricing(self.model)

        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)

        input_cost = (prompt_tokens / 1_000_000) * input_price
        output_cost = (completion_tokens / 1_000_000) * output_price
        total_cost = input_cost + output_cost

        return {
            "model": self.model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": usage.get("total_tokens", 0),
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
        }


def get_llm_client(
    config_dir: Path | None = None, use_stub: bool = False, model: str | None = None
) -> LLMClient:
    """
    Factory function to get an LLM client instance.

    Args:
        config_dir: Directory containing config files. If None, uses project config/.
        use_stub: If True, use stub mode (no API calls).
        model: Optional model name to override default/evaluation model.

    Returns:
        LLMClient instance.
    """
    return LLMClient(config_dir=config_dir, use_stub=use_stub, model=model)
