"""Стоимость вызова LLM в долларах.

Модели берут деньги за токены (≈ ¾ слова). Отдельно за вход (prompt — то, что
мы послали) и за выход (completion — то, что модель сгенерила). Цена указана за
1 000 000 токенов. Ставки ниже — ориентировочные (Groq), их легко поменять.
"""

# (input $/1M, output $/1M)
PRICES = {
    "qwen/qwen3.8-27b":     (0.20, 0.60),
    "openai/gpt-oss-20b":   (0.10, 0.50),
    "openai/gpt-oss-120b":  (0.15, 0.75),
    "llama-3.3-70b":        (0.59, 0.79),
}
DEFAULT = (0.20, 0.60)  # если модель не в таблице


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Считает стоимость одного вызова: (вход·ставка_вх + выход·ставка_вых) / 1e6."""
    pin, pout = PRICES.get(model, DEFAULT)
    return (prompt_tokens * pin + completion_tokens * pout) / 1_000_000
