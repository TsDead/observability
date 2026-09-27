"""LLM Observability — дашборд стоимости, latency и надёжности.

Показывает метрики по журналу вызовов (obslog). Кнопка «демо-трафик» гоняет
пачку разных запросов, чтобы наполнить журнал; один вызов намеренно битый —
чтобы error-rate был честным, а не всегда нулевым.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

import llm
import obslog
import metrics

app = FastAPI(title="LLM Observability")
HTML = (Path(__file__).parent / "static" / "index.html").read_text(encoding="utf-8")

# набор разнотипных запросов для демо-трафика (метка → промпт, модель)
DEMO = [
    ("chat", "Назови столицу Японии одним словом.", None),
    ("chat", "Слоган для пекарни, ровно 5 слов.", None),
    ("agent_step", "Ты агент. Каким инструментом посчитать 18*47? Ответь одной фразой.", None),
    ("summarize", "Сожми в одно предложение: RAG подставляет модели куски документов, "
                  "чтобы она отвечала по данным, а не выдумывала.", "openai/gpt-oss-20b"),
    ("classify", "Тональность отзыва «всё отлично, рекомендую» — одно слово.", "openai/gpt-oss-20b"),
]


@app.get("/", response_class=HTMLResponse)
def index():
    return HTML


@app.get("/api/metrics")
def api_metrics():
    return metrics.summary()


@app.post("/api/demo")
def api_demo():
    if not llm.available():
        return {"error": "Не задан GROQ_API_KEY в .env."}
    done = 0
    for label, prompt, model in DEMO:
        try:
            llm.chat([{"role": "user", "content": prompt}], label=label, model=model, max_tokens=120)
            done += 1
        except Exception:
            pass  # ошибка уже записана в журнал внутри llm.chat
    # намеренно битый вызов — несуществующая модель → пишется как ok=0
    try:
        llm.chat([{"role": "user", "content": "ping"}], label="chat", model="no-such-model-xyz", max_tokens=10)
    except Exception:
        pass
    return {"generated": done + 1}


@app.post("/api/clear")
def api_clear():
    obslog.clear()
    return {"ok": True}
