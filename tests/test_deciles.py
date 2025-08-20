import pandas as pd
from src.metrics import risk_deciles

def test_risk_deciles_runs():
    df = pd.DataFrame({"subgroup":["A"]*100,"pred_risk":[i/100 for i in range(100)],"wait_days":list(range(100))})
    d = risk_deciles(df)
    assert d["risk_decile"].nunique() >= 5
