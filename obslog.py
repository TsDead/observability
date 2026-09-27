"""Журнал вызовов LLM — ядро наблюдаемости.

Хранилище — SQLite: это встроенная в Python база-в-одном-файле (obs.db),
без сервера и без ключей. Каждый вызов модели = одна строка в таблице calls.
Потом metrics.py читает эти строки и считает агрегаты (стоимость, p95 latency…).
"""

import sqlite3
import datetime
from pathlib import Path

DB = Path(__file__).parent / "obs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS calls (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  ts                TEXT    NOT NULL,   -- когда (ISO-время UTC)
  model             TEXT    NOT NULL,   -- какая модель
  label             TEXT    NOT NULL,   -- метка вызова: chat / agent_step / demo …
  latency_ms        INTEGER NOT NULL,   -- сколько заняло, миллисекунды
  prompt_tokens     INTEGER NOT NULL,   -- токенов на входе
  completion_tokens INTEGER NOT NULL,   -- токенов на выходе
  cost_usd          REAL    NOT NULL,   -- стоимость в долларах
  ok                INTEGER NOT NULL,   -- 1 = успех, 0 = ошибка
  error             TEXT                -- текст ошибки, если была
);
"""


def _conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row      # чтобы читать строки как словари
    c.execute(SCHEMA)                # создаём таблицу, если её ещё нет
    return c


def record(model, label, latency_ms, prompt_tokens=0, completion_tokens=0,
           cost_usd=0.0, ok=True, error=None):
    """Записать один вызов в журнал. Это и есть «инструментирование»."""
    with _conn() as c:
        c.execute(
            "INSERT INTO calls (ts,model,label,latency_ms,prompt_tokens,"
            "completion_tokens,cost_usd,ok,error) VALUES (?,?,?,?,?,?,?,?,?)",
            (datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
             model, label, int(latency_ms), int(prompt_tokens),
             int(completion_tokens), float(cost_usd), 1 if ok else 0, error),
        )


def rows(limit=1000):
    """Последние вызовы (для метрик и таблицы на дашборде)."""
    with _conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM calls ORDER BY id DESC LIMIT ?", (limit,))]


def clear():
    with _conn() as c:
        c.execute("DELETE FROM calls")
