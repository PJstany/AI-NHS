import pandas as pd
from src.aggregate import summarize

def test_warmup_filters_early_days(tmp_path):
    df = pd.DataFrame({
        "arrival_day":[0,1,2,14,15],
        "wait_days":[0,0,0,1,2],
        "attended":[True,True,True,True,True],
        "subgroup":["A","A","A","A","A"],
        "pclass":["routine"]*5,
        "pred_risk":[0.5]*5
    })
    th = {"same_day":0,"within_3d":3,"within_14d":14}
    out0 = summarize(df.copy(), th, warmup_days=0)["overall"]
    out14 = summarize(df.copy(), th, warmup_days=14)["overall"]
    assert out0["n"].iloc[0] == 5
    assert out14["n"].iloc[0] == 2

