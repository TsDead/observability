"""Агрегация журнала в метрики для дашборда.

Ключевая идея — перцентили, а не среднее. Среднее прячет редкие тормоза;
p95 (95% запросов быстрее него) показывает «хвост», который чувствуют юзеры.
"""

import obslog


def _pct(values, p):
    """p-й перцентиль списка (p от 0 до 100), без внешних библиотек."""
    if not values:
        return 0
    s = sorted(values)
    k = (len(s) - 1) * p / 100
    lo = int(k)
    hi = min(lo + 1, len(s) - 1)
    return round(s[lo] + (s[hi] - s[lo]) * (k - lo))   # линейная интерполяция


def summary():
    rows = obslog.rows(5000)
    n = len(rows)
    if n == 0:
        return {"calls": 0, "empty": True}

    lat = [r["latency_ms"] for r in rows]
    ok = [r for r in rows if r["ok"]]
    errors = n - len(ok)

    # разбивка по метке вызова (chat / agent_step / demo …)
    by_label = {}
    for r in rows:
        b = by_label.setdefault(r["label"], {"calls": 0, "cost": 0.0})
        b["calls"] += 1
        b["cost"] += r["cost_usd"]

    # токены по дням — для мини-графика
    by_day = {}
    for r in rows:
        day = r["ts"][:10]
        by_day[day] = by_day.get(day, 0) + r["prompt_tokens"] + r["completion_tokens"]
    days = sorted(by_day)[-7:]                       # последние 7 дней

    top = sorted(rows, key=lambda r: r["cost_usd"], reverse=True)[:5]

    return {
        "empty": False,
        "calls": n,
        "cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
        "tokens": sum(r["prompt_tokens"] + r["completion_tokens"] for r in rows),
        "error_rate": round(errors / n, 4),
        "errors": errors,
        "p50_ms": _pct(lat, 50),
        "p95_ms": _pct(lat, 95),
        "by_label": [{"label": k, **v, "cost": round(v["cost"], 6)}
                     for k, v in sorted(by_label.items(), key=lambda x: -x[1]["calls"])],
        "by_day": [{"day": d, "tokens": by_day[d]} for d in days],
        "top": [{"label": r["label"], "model": r["model"], "cost": round(r["cost_usd"], 6),
                 "latency_ms": r["latency_ms"]} for r in top],
        "recent": [{"ts": r["ts"][11:19], "label": r["label"], "latency_ms": r["latency_ms"],
                    "tokens": r["prompt_tokens"] + r["completion_tokens"],
                    "cost": r["cost_usd"], "ok": r["ok"]} for r in rows[:20]],
    }
