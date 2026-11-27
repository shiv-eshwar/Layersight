"""Closed form, Wilson interval, and the illustrative funnel."""

import math
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

# Quantile of the standard normal used by a 95% Wilson interval.
Z_95 = 1.959963984540054


def closed_form(p_stop: Sequence[float]) -> float:
    """Probability an attack passes every layer, assuming independence."""

    survival = 1.0
    for probability in p_stop:
        survival *= 1.0 - probability
    return survival


def wilson_interval(passed: int, runs: int, *, z: float = Z_95) -> tuple[float, float]:
    """95% Wilson score interval for `passed` successes in `runs` trials."""

    if runs <= 0:
        raise ValueError("runs must be positive")
    if passed < 0 or passed > runs:
        raise ValueError("passed must be between 0 and runs")
    n = float(runs)
    proportion = passed / n
    z2 = z * z
    denom = 1.0 + z2 / n
    center = (proportion + z2 / (2.0 * n)) / denom
    margin = z * math.sqrt(proportion * (1.0 - proportion) / n + z2 / (4.0 * n * n)) / denom
    low = max(0.0, center - margin)
    high = min(1.0, center + margin)
    return (low, high)


def expected_remaining(runs: int, p_stop: Sequence[float]) -> list[float]:
    """Unrounded attacks still going after each layer, in layer order."""

    remaining = Decimal(runs)
    out: list[float] = []
    for probability in p_stop:
        remaining *= Decimal(1) - Decimal(str(probability))
        out.append(float(remaining))
    return out


def round_half_up(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def relative_reduction(before: float, after: float) -> float | None:
    """(P_before - P_after) / P_before. Undefined when the baseline is zero."""

    if before == 0:
        return None
    return (before - after) / before
