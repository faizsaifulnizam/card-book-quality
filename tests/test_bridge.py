"""Unit test for the midpoint bridge on made-up numbers — no data, no MAS files.

Run: python tests/test_bridge.py   (also runs under pytest)

R0=100, r0=5% → W0=5.0 · R1=120, r1=6% → W1=7.2 · ΔW=2.2
  midpoint: volume = ΔR × avg rate = 20 × 0.055 = 1.10
            rate   = Δr × avg R    = 0.01 × 110   = 1.10   (sums to ΔW exactly)
  base:     joint term = ΔR × Δr   = 20 × 0.01    = 0.20   (closure, surfaced not absorbed)
"""
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.analysis import bridge  # noqa: E402


def test_bridge_midpoint_closes_exactly():
    old, new = {"w": 5.0, "R": 100.0, "r": 0.05}, {"w": 7.2, "R": 120.0, "r": 0.06}
    b = bridge(old, new)
    assert math.isclose(b["dW"], 2.2, abs_tol=1e-12)
    assert math.isclose(b["volume"], 1.10, abs_tol=1e-12)
    assert math.isclose(b["rate"], 1.10, abs_tol=1e-12)
    assert abs(b["inter"]) < 1e-12                       # midpoint absorbs the joint term
    assert math.isclose(b["volume"] + b["rate"], b["dW"], abs_tol=1e-12)
    # base-weighted alternative: vol + rate + joint closes exactly; joint = ΔR × Δr
    assert math.isclose(b["volume_b"] + b["rate_b"] + b["inter_b"], b["dW"], abs_tol=1e-12)
    assert math.isclose(b["inter_b"], 0.20, abs_tol=1e-12)


def test_bridge_zero_residual_has_no_negative_sign():
    b = bridge({'w': 5.0, 'R': 100.0, 'r': 0.05}, {'w': 7.2, 'R': 120.0, 'r': 0.06})
    assert b['inter'] == 0.0
    assert math.copysign(1.0, b['inter']) == 1.0


def test_bridge_falling_and_opposing_contributions():
    cases = [
        # Falling balances, falling rates, unchanged, and both directions of opposition.
        (100, .05, 80, .05, -1, 0),
        (100, .05, 100, .03, 0, -2),
        (100, .05, 100, .05, 0, 0),
        (100, .05, 120, .04, .9, -1.1),
        (100, .05, 80, .06, -1.1, .9),
        (120, .06, 100, .05, -1.1, -1.1),
    ]
    for R0, r0, R1, r1, volume, rate in cases:
        b = bridge({'w': R0 * r0, 'R': R0, 'r': r0}, {'w': R1 * r1, 'R': R1, 'r': r1})
        assert math.isclose(b['volume'], volume, abs_tol=1e-12)
        assert math.isclose(b['rate'], rate, abs_tol=1e-12)
        assert math.isclose(b['volume'] + b['rate'], b['dW'], abs_tol=1e-12)
        assert math.isclose(b['volume_b'] + b['rate_b'] + b['inter_b'], b['dW'], abs_tol=1e-12)


def main():
    test_bridge_midpoint_closes_exactly()
    test_bridge_zero_residual_has_no_negative_sign()
    test_bridge_falling_and_opposing_contributions()
    print("test_bridge: PASS — midpoint splits exactly (1.10 + 1.10 = 2.20); base closure exact; joint = ΔR·Δr = 0.20")


if __name__ == "__main__":
    main()
