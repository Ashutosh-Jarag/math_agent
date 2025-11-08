
# Math input/output guardrails.


def input_guardrail(question: str) -> bool:
    """
    Check if the given math problem is valid.
    Args:
        question (str): The math problem to check.
    Returns:
        bool: True if the problem is valid, False otherwise.
    """
    allowed_keywords = [
        "integrate", "differentiate", "derivative", "equation", "matrix",
        "limit", "solve", "find", "function", "value", "graph", "area", "volume"
    ]
    return any(word in question.lower() for word in allowed_keywords)


def output_guardrail(text: str) -> bool:
    """
    Check if the generated answer contains inappropriate content.
    Args:
        text (str): The generated answer to check.
    Returns:
        bool: True if the answer is appropriate, False otherwise.
    
    """
    banned_keywords = ["violence", "religion", "politics", "hack", "illegal", "suicide"]
    return not any(bad in text.lower() for bad in banned_keywords)
