from src.metrics import kpi_flags
import pandas as pd

def test_kpi_thresholds_align_to_days():
    df = pd.DataFrame({"wait_days":[0,1,3,10,20]})
    out = kpi_flags(df, same_day=0, within_3=3, within_14=14)
    assert out["breach_same_day"].iloc[0] == False  # 0 days is not > 0
    assert out["breach_3d"].iloc[2] == False        # 3 days is not > 3
    assert out["breach_14d"].iloc[4] == True        # 20 days is > 14
