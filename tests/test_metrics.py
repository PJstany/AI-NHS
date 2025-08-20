import pandas as pd
from src.metrics import kpi_flags, equity_summary

def test_p90_p95_and_gaps():
    df = pd.DataFrame({
        "subgroup": ["A"]*100 + ["B"]*100,
        "wait_days": list(range(100)) + list(range(100)),
        "pclass": ["routine"]*200,
        "attended": [True]*200
    })
    df = kpi_flags(df, 0, 3, 14)
    overall, gaps = equity_summary(df)
    assert {"P90", "P95"} <= set(overall.columns)

