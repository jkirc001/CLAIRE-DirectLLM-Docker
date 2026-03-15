"""Compare answers from multiple models for a given question."""

import json
import os
import re
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from claire_directllm.llm.client import get_llm_client
from claire_directllm.llm.prompts import build_direct_prompt

app = typer.Typer()
console = Console()


def extract_cvss_score(answer: str) -> str | None:
    """Extract CVSS score from answer text if present."""
    patterns = [
        r'cvss.*?score.*?(\d+\.\d+)',
        r'score.*?(\d+\.\d+).*?(?:high|critical|base)',
        r'(\d+\.\d+).*?\(.*?(?:high|critical)',
        r'cvss.*?(\d+\.\d+).*?\(',
        r'base score.*?(\d+\.\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, answer, re.IGNORECASE)
        if match:
            score = match.group(1)
            # Verify it's a reasonable CVSS score (0.0 to 10.0)
            try:
                score_float = float(score)
                if 0.0 <= score_float <= 10.0:
                    return score
            except ValueError:
                pass
    return None


@app.command()
def compare(
    question: str = typer.Argument(..., help="The question to ask"),
    models: str = typer.Option(
        None,
        "--models",
        "-m",
        help="Comma-separated list of models to test (e.g., 'gpt-4o,gpt-5.2,gpt-4.1'). If not provided, tests all allowed models.",
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Show detailed information for each model",
    ),
    output: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Save results to a file (JSON format). If not specified, results are only displayed.",
    ),
) -> None:
    """
    Compare answers from multiple models for the same question.
    """
    # Get config directory
    config_dir = Path(__file__).parent.parent.parent / "config"

    # Get list of models to test
    if models:
        model_list = [m.strip() for m in models.split(",")]
    else:
        # Load config to get all allowed models
        import yaml
        models_config = yaml.safe_load(open(config_dir / "models.yaml"))
        model_list = models_config["allowed_models"]

    console.print(f"\n[bold]Testing {len(model_list)} model(s) with question:[/bold]")
    console.print(Panel(question, border_style="blue"))
    console.print()

    results = []
    prompt = build_direct_prompt(question)

    # Test each model
    for model_name in model_list:
        console.print(f"[yellow]Testing {model_name}...[/yellow]")
        try:
            llm_client = get_llm_client(config_dir=config_dir, use_stub=False, model=model_name)

            if debug:
                answer, usage = llm_client.generate(prompt, return_usage=True)
                cost_info = llm_client.calculate_cost(usage)
                cvss_score = extract_cvss_score(answer)
                results.append(
                    {
                        "model": model_name,
                        "answer": answer,
                        "tokens": usage.get("total_tokens", 0),
                        "cost": cost_info.get("total_cost", 0),
                        "cvss_score": cvss_score,
                        "error": None,
                    }
                )
            else:
                answer = llm_client.generate(prompt, return_usage=False)
                cvss_score = extract_cvss_score(answer)
                results.append(
                    {
                        "model": model_name,
                        "answer": answer,
                        "tokens": None,
                        "cost": None,
                        "cvss_score": cvss_score,
                        "error": None,
                    }
                )
            console.print(f"[green]✓ {model_name} completed[/green]\n")
        except Exception as e:
            console.print(f"[red]✗ {model_name} failed: {e}[/red]\n")
            results.append(
                {
                    "model": model_name,
                    "answer": None,
                    "tokens": None,
                    "cost": None,
                    "error": str(e),
                }
            )

    # Display comparison table
    console.print("\n" + "=" * 80)
    console.print("[bold]COMPARISON RESULTS[/bold]")
    console.print("=" * 80 + "\n")

    # Create summary table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Model", style="cyan", width=15)
    table.add_column("CVSS Score", width=12)
    table.add_column("Status", width=10)
    if debug:
        table.add_column("Tokens", justify="right", width=10)
        table.add_column("Cost", justify="right", width=12)

    for result in results:
        if result["error"]:
            status = f"[red]Error[/red]"
            row = [result["model"], "-", status]
        else:
            status = "[green]Success[/green]"
            cvss_score = result.get("cvss_score")
            cvss_display = f"[green]{cvss_score}[/green]" if cvss_score else "[dim]N/A[/dim]"
            row = [result["model"], cvss_display, status]
            if debug:
                row.append(str(result["tokens"]))
                row.append(f"${result['cost']:.6f}")
        table.add_row(*row)

    console.print(table)
    console.print()

    # Display detailed answers
    for result in results:
        if result["error"]:
            console.print(f"\n[bold red]{result['model']} - ERROR[/bold red]")
            console.print(Panel(result["error"], border_style="red"))
        else:
            console.print(f"\n[bold cyan]{result['model']}[/bold cyan]")
            if debug and result["tokens"]:
                console.print(f"[dim]Tokens: {result['tokens']} | Cost: ${result['cost']:.6f}[/dim]")
            console.print(Panel(result["answer"], border_style="green"))

    # Save results to file if requested
    if output:
        output_path = Path(output)
        output_data = {
            "question": question,
            "timestamp": datetime.now().isoformat(),
            "models_tested": model_list,
            "results": results,
        }
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
        console.print(f"\n[green]Results saved to: {output_path}[/green]")


if __name__ == "__main__":
    app()

