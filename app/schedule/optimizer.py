from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from bisect import bisect_right
from typing import Iterable, List, Literal, Tuple


Metric = Literal["duration", "max_elev"]


@dataclass(frozen=True)
class PassItem:
    """
    This is an in-memory pass object used by the scheduling algorithm.

    Important:
    - start/end should already be CLIPPED to the query window [start,end]
      so weights reflect only the window part.
    """
    id: int
    satellite_id: int
    ground_station_id: int
    start_ts: datetime
    end_ts: datetime
    duration_s: int
    max_elev_deg: float


def weight(p: PassItem, metric: Metric) -> float:
    if metric == "duration":
        return float(p.duration_s)
    if metric == "max_elev":
        return float(p.max_elev_deg)
    raise ValueError(f"Unknown metric: {metric}")


def best_non_overlapping_weighted(
    passes: Iterable[PassItem],
    metric: Metric,
) -> Tuple[List[PassItem], float]:
    """
    Weighted interval scheduling (DP, O(n log n)):
    Returns:
      - best non-overlapping subset maximizing sum(weight)
      - best_score

    Overlap rule:
      Two passes do NOT overlap if prev.end_ts <= next.start_ts
    """
    items = sorted(list(passes), key=lambda x: (x.end_ts, x.start_ts))
    n = len(items)
    if n == 0:
        return ([], 0.0)

    ends = [it.end_ts for it in items]

    # p_idx[i] = index of last interval that ends <= items[i].start_ts
    p_idx = [-1] * n
    for i in range(n):
        j = bisect_right(ends, items[i].start_ts) - 1
        p_idx[i] = j

    # dp[i] = best score using intervals up to i (0..i)
    dp = [0.0] * n
    take = [False] * n

    for i in range(n):
        w = weight(items[i], metric)
        incl = w + (dp[p_idx[i]] if p_idx[i] >= 0 else 0.0)
        excl = dp[i - 1] if i > 0 else 0.0

        if incl > excl:
            dp[i] = incl
            take[i] = True
        else:
            dp[i] = excl
            take[i] = False

    # reconstruct solution
    chosen: List[PassItem] = []
    i = n - 1
    while i >= 0:
        if take[i]:
            chosen.append(items[i])
            i = p_idx[i]
        else:
            i -= 1

    chosen.reverse()
    return (chosen, dp[n - 1])


def top_k_passes(
    passes: Iterable[PassItem],
    metric: Metric,
    k: int,
) -> List[PassItem]:
    """
    Simple “Top K” list by metric (no non-overlap constraint).
    """
    if k <= 0:
        return []
    items = list(passes)
    items.sort(key=lambda p: weight(p, metric), reverse=True)
    return items[:k]
