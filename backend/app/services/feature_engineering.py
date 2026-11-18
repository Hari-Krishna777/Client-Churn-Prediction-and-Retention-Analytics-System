import pandas as pd
from app.config import TENURE_BINS, TENURE_LABELS, SERVICE_COLUMNS


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply the exact feature engineering pipeline verified against Deepnote:
    1. TenureGroup: binned tenure into [-1, 6, 12, 24, 48, 72] with labels:
       "0-6 months", "7-12 months", "13-24 months", "25-48 months", "49-72 months".
    2. AvgMonthlySpend: TotalCharges / tenure when tenure > 0, else MonthlyCharges.
    3. ServiceCount: Count of services with value "Yes" among the 8 service features.
    """
    df = df.copy()

    # 1. TenureGroup
    df["TenureGroup"] = pd.cut(
        df["tenure"],
        bins=TENURE_BINS,
        labels=TENURE_LABELS
    )

    # 2. AvgMonthlySpend
    total_charges = pd.to_numeric(df["TotalCharges"], errors="coerce").fillna(0.0)
    tenure = pd.to_numeric(df["tenure"], errors="coerce").fillna(0)
    monthly_charges = pd.to_numeric(df["MonthlyCharges"], errors="coerce").fillna(0.0)

    avg_spend = total_charges / tenure.replace(0, float("nan"))
    df["AvgMonthlySpend"] = avg_spend.fillna(monthly_charges)

    # 3. ServiceCount
    df["ServiceCount"] = df[SERVICE_COLUMNS].eq("Yes").sum(axis=1)

    return df
