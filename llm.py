"""LLM-клиент Groq, обёрнутый наблюдаемостью.

Логика вызова та же, что в прошлых проектах, но вокруг неё — измерение:
секундомер + подсчёт стоимости + запись в журнал (obslog). Успех И ошибка
записываются одинаково — иначе метрика надёжности была бы неправдой.
"""

import os
import time
import requests
from dotenv import load_dotenv

import obslog
import pricing

load_dotenv()

GROQ_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = os.getenv("LLM_MODEL", "qwen/qwen3.8-27b").strip()


def available() -> bool:
    return bool(GROQ_KEY)


def chat(messages, label="chat", model=None, max_tokens=600, temperature=0.2):
    """Зовёт модель и логирует вызов. Возвращает (content, usage)."""
    model = model or MODEL
    if not GROQ_KEY:
        raise RuntimeError("нет GROQ_API_KEY в .env")

    payload = {"model": model, "messages": messages,
               "max_tokens": max_tokens, "temperature": temperature}
    if "gpt-oss" in model:
        payload["reasoning_effort"] = "low"

    t0 = time.perf_counter()          # секундомер: старт
    ptok = ctok = 0
    try:
        r = requests.post(GROQ_URL, timeout=60,
                          headers={"Authorization": f"Bearer {GROQ_KEY}",
                                   "Content-Type": "application/json"},
                          json=payload)
        r.raise_for_status()
        data = r.json()
        usage = data.get("usage", {})
        ptok = usage.get("prompt_tokens", 0)
        ctok = usage.get("completion_tokens", 0)
        content = (data["choices"][0]["message"].get("content", "") or "").strip()
        latency_ms = (time.perf_counter() - t0) * 1000   # секундомер: стоп
        obslog.record(model, label, latency_ms, ptok, ctok,
                      pricing.cost_usd(model, ptok, ctok), ok=True)
        return content, usage
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        obslog.record(model, label, latency_ms, ptok, ctok,
                      pricing.cost_usd(model, ptok, ctok), ok=False, error=str(e)[:200])
        raise
