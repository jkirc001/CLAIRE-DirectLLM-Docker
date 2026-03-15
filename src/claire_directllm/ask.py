"""CLI interface for asking questions directly to the LLM."""

import os
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from claire_directllm.llm.client import get_llm_client
from claire_directllm.llm.prompts import build_direct_prompt

app = typer.Typer()
console = Console()


@app.command()
def ask(
    question: str = typer.Argument(..., help="The question to ask"),
    eval_mode: bool = typer.Option(
        False,
        "--eval",
        help="Enable evaluation mode (forces gpt-4o for LLM)",
    ),
    stub: bool = typer.Option(
        False,
        "--stub",
        help="Use stub LLM mode (no API calls, free testing)",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show debug information (token usage, cost estimates)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Override model to use (e.g., gpt-5.2, gpt-4o, o1-pro)",
    ),
) -> None:
    """
    Ask a question directly to the LLM (no retrieval, no context).
    """
    # Set evaluation mode if flag is provided
    if eval_mode:
        os.environ["CLAIRE_ENV"] = "evaluation"
    
    # Get config directory (go up from src/claire_directllm/ask.py to project root)
    config_dir = Path(__file__).parent.parent.parent / "config"
    
    # Initialize LLM client
    try:
        llm_client = get_llm_client(config_dir=config_dir, use_stub=stub, model=model)
    except Exception as e:
        console.print(f"[red]Error initializing LLM client: {e}[/red]")
        raise typer.Exit(1)
    
    # Build prompt
    prompt = build_direct_prompt(question)
    
    # Generate answer
    try:
        if debug:
            answer, usage = llm_client.generate(prompt, return_usage=True)
        else:
            answer = llm_client.generate(prompt, return_usage=False)
            usage = None
    except Exception as e:
        console.print(f"[red]Error generating answer: {e}[/red]")
        raise typer.Exit(1)
    
    # Display answer
    console.print("\n" + "=" * 80)
    console.print("[bold]ANSWER[/bold]")
    console.print("=" * 80)
    console.print(answer)
    console.print("=" * 80)
    
    # Display debug information if requested
    if debug:
        # Show system message
        console.print("\n" + "=" * 80)
        console.print("[bold]SYSTEM MESSAGE[/bold]")
        console.print("=" * 80)
        console.print(llm_client.system_message)
        console.print("=" * 80)
        
        # Show prompt
        console.print("\n" + "=" * 80)
        console.print("[bold]PROMPT[/bold]")
        console.print("=" * 80)
        console.print(prompt)
        console.print("=" * 80)
        
        # Show cost information if usage is available
        if usage:
            cost_info = llm_client.calculate_cost(usage)
            console.print("\n" + "=" * 80)
            console.print("[bold]COST INFORMATION[/bold]")
            console.print("=" * 80)
            console.print(f"Model: {cost_info['model']}")
            console.print(f"Prompt tokens: {cost_info['prompt_tokens']}")
            console.print(f"Completion tokens: {cost_info['completion_tokens']}")
            console.print(f"Total tokens: {cost_info['total_tokens']}")
            console.print("\nEstimated cost:")
            console.print(f"  Input:  ${cost_info['input_cost']:.6f}")
            console.print(f"  Output: ${cost_info['output_cost']:.6f}")
            console.print(f"  Total:  ${cost_info['total_cost']:.6f}")
            console.print("=" * 80)
        
        if stub:
            console.print("\n[yellow]Note: Running in stub mode - no actual API calls were made.[/yellow]")


if __name__ == "__main__":
    app()

