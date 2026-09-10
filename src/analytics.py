"""Latency, cost, and model-selection analytics.

Selection analysis is Pareto-based rather than rank-only (docs/DECISIONS.md
D-012): a model is on the frontier when no other model is at least as good on
every objective and strictly better on one.
"""

from __future__ import annotations


def _present(values: list) -> list:
    return [value for value in values if value is not None]


def percentile(values: list[float], fraction: float) -> float | None:
    """Linear-interpolation percentile. Returns None for an empty input."""
    data = sorted(_present(values))
    if not data:
        return None
    if len(data) == 1:
        return round(float(data[0]), 2)
    position = (len(data) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(data) - 1)
    weight = position - lower
    return round(data[lower] * (1 - weight) + data[upper] * weight, 2)


def latency_stats(values: list[float]) -> dict:
    data = _present(values)
    return {
        "samples": len(data),
        "avg_latency_ms": round(sum(data) / len(data), 2) if data else None,
        "p50_latency_ms": percentile(data, 0.50),
        "p95_latency_ms": percentile(data, 0.95),
        "max_latency_ms": round(max(data), 2) if data else None,
    }


def cost_per_100_tasks(total_cost, completed_tasks: int):
    """Scale an observed total cost to 100 tasks."""
    if total_cost is None or not completed_tasks:
        return None
    return round(total_cost / completed_tasks * 100, 8)


def quality_per_cny(overall_score, cost_cny):
    """Overall score delivered per CNY of candidate inference cost."""
    if overall_score is None or cost_cny is None or cost_cny <= 0:
        return None
    return round(overall_score / cost_cny, 4)


def dominates(left: dict, right: dict, objectives: list[tuple[str, str]]) -> bool:
    """True when `left` Pareto-dominates `right`.

    `objectives` is a list of (field, direction) where direction is "max" or
    "min". Dominance requires left to be at least as good on every objective and
    strictly better on at least one.
    """
    strictly_better = False
    for field, direction in objectives:
        left_value, right_value = left.get(field), right.get(field)
        if left_value is None or right_value is None:
            return False
        if direction == "max":
            if left_value < right_value:
                return False
            if left_value > right_value:
                strictly_better = True
        else:
            if left_value > right_value:
                return False
            if left_value < right_value:
                strictly_better = True
    return strictly_better


def pareto_frontier(rows: list[dict], objectives: list[tuple[str, str]]) -> dict:
    """Compute the Pareto frontier and name the dominating model for the rest.

    Rows missing any objective value are reported as `not_evaluated` rather than
    being silently dropped or treated as failing.
    """
    evaluated = [
        row
        for row in rows
        if all(row.get(field) is not None for field, _ in objectives)
    ]
    not_evaluated = [row["model_key"] for row in rows if row not in evaluated]

    frontier: list[str] = []
    dominated: dict[str, str] = {}

    for row in evaluated:
        dominators = [
            other
            for other in evaluated
            if other is not row and dominates(other, row, objectives)
        ]
        if dominators:
            best = sorted(
                dominators,
                key=lambda item: (
                    -(item.get(objectives[0][0]) or 0)
                    if objectives[0][1] == "max"
                    else (item.get(objectives[0][0]) or 0)
                ),
            )[0]
            dominated[row["model_key"]] = best["model_key"]
        else:
            frontier.append(row["model_key"])

    return {
        "objectives": [{"field": field, "direction": direction} for field, direction in objectives],
        "frontier": frontier,
        "dominated": dominated,
        "not_evaluated": not_evaluated,
    }


def aggregate_cost_metrics(records: list[dict], candidate_cost_key: str = "normalized_cost_cny") -> dict:
    """Sum a cost field across records, reporting None when nothing is priced."""
    values = [record.get(candidate_cost_key) for record in records]
    present = _present(values)
    return {
        "total": round(sum(present), 8) if present else None,
        "priced_records": len(present),
        "unpriced_records": len(values) - len(present),
    }
