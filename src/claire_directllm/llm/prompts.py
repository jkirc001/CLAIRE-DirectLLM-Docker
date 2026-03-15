"""Prompt building functions for direct LLM question answering."""


def build_direct_prompt(query: str) -> str:
    """
    Build a prompt for direct LLM answering (no context).
    
    Args:
        query: User question
        
    Returns:
        Formatted prompt string
    """
    prompt = f"""Question:
{query}

Answer questions based on general knowledge when no database results are available."""
    
    return prompt

