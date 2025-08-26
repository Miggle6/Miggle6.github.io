# recPred10.py - Ten-input recession model with data taken from the St. Louis Federal
#                Reserve.
# 22-Aug-25  M. Watler          Created with yield spread, unemployment, and consumer
#                               spending.
# 23-Aug-25  M. Watler          Writes coefficients to a JavaScript file
# 23-Aug-25  M. Watler          Fourth input: Building Permits YoY (PERMIT)
# 24-Aug-25  M. Watler          Fifth input: Industrial Production YoY (INDPRO)
# 25-Aug-25  M. Watler          Added five more inputs, all leading indicators:
#                               Credit Spreads (Corporate vs. Treasuries), Initial Jobless
#                               Claims, ISM New Orders Index, Consumer Expectations Index,
#                               Money Supply Growth (Real M2).
#                               Notes:
#                               - ISM New Orders (NAPMNOI) is no longer available via
#                                 FRED's API. We use NEWORDER as a forward-demand proxy.
#                               - If you license ISM, replace NEWORDER block with your 
#                                 feed and keep the same sign/normalization.
#
# recPred10.py - Ten-input recession model (adds 5 leading indicators to your 5)
# 25-Aug-25  ChatGPT (per M. Watler request)
#
# Adds:
#   Credit Spreads (BAA10Y), Initial Jobless Claims (IC4WSA -> monthly avg, YoY),
#   "ISM New Orders" proxy using NEWORDER (Nondefense Capital Goods ex-Aircraft), YoY,
#   Consumer Expectations proxy (UMCSENT), YoY,
#   Money Supply Growth (M2REAL), YoY.
#
# Notes:
# - ISM New Orders (NAPMNOI) is not available via FRED's API. We use NEWORDER as a forward-demand proxy.
#   If you license ISM, replace the proxy block and keep the sign/normalization.
#
import os, json, requests, pandas as pd, numpy as np
from dataclasses import dataclass
from math import exp
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report

API_KEY = os.getenv("FRED_API_KEY", "2ed1a331382b6bfc93e0d12dc6b19ff0")
BASE = "https://api.stlouisfed.org/fred/series/observations"

def fred_series(series_id, start="1960-01-01", frequency=None, aggregation_method=None):
    params = {
        "series_id": series_id,
        "api_key": API_KEY,
        "file_type": "json",
        "observation_start": start,
    }
    if frequency:
        params["frequency"] = frequency
    if aggregation_method:
        params["aggregation_method"] = aggregation_method
    r = requests.get(BASE, params=params, timeout=30)
    r.raise_for_status()
    js = r.json()["observations"]
    df = pd.DataFrame(js)[["date", "value"]]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().set_index("date").sort_index()
    # HARDEN: ensure unique index at fetch time
    df = df.loc[~df.index.duplicated(keep="last")]
    df.columns = [series_id]
    return df

def ensure_unique_month_index(name, s: pd.DataFrame) -> pd.DataFrame:
    """Coerce to month-start and ensure unique index (keep last)."""
    s.index = s.index.to_period("M").to_timestamp(how="start")
    s = s.loc[~s.index.duplicated(keep="last")]
    s.attrs["name"] = name
    return s

# -----------------------------
# Manual coefficients (10 inputs) — re-scaled
# -----------------------------
@dataclass
class ManualCoeffs10:
    b0: float = -3.00
    # Original 5 (same scale as your previous script)
    w_spread: float = 3.168     # Yield curve (more negative => higher risk via -spread)
    w_sahm: float   = 1.80
    w_pce: float    = 1.00
    w_perm: float   = 1.20     # (-permits_yoy)/10
    w_ip: float     = 0.96     # (-indprod_yoy)

    # New 5 (re-weighted & normalized to prevent domination)
    w_credit: float = 0.60     # Credit spread in pp (raw)
    w_claims: float = 1.40     # Initial claims YoY% / 10
    w_neword: float = 1.40     # New orders YoY% / 10, enters as negative
    w_consx: float  = 0.80     # Sentiment YoY% / 20, enters as negative
    w_m2: float     = 1.20     # Real M2 YoY% / 10, enters as negative

def logistic(z: float) -> float:
    return 1.0 / (1.0 + exp(-z))

def manual_logit_and_contrib(feat, c: ManualCoeffs10):
    """
    Monotonic mappings (higher z => more risk):
      YieldSpread_pp:         use (-YieldSpread)
      SahmGap_pp:             use (+SahmGap)
      rPCE_6mAnn_pct:         use (-rPCE)
      BuildingPermits_YoY%:   use (-permits_yoy)/10
      IndustrialProd_YoY%:    use (-indpro_yoy)

      CreditSpread_pp:        use (+credit_spread)
      Claims_YoY%:            use (+claims_yoy)/10
      NewOrders_YoY%:         use (-neworders_yoy)/10
      ConsExpect_YoY%:        use (-cons_yoy)/20
      RealM2_YoY%:            use (-m2_yoy)/10
    """
    contrib = {
        "YieldSpread":         c.w_spread * (-feat["YieldSpread"]),
        "SahmGap":             c.w_sahm   * (feat["SahmGap"]),
        "rPCE_6mAnn":          c.w_pce    * (-feat["rPCE_6mAnn"]),
        "BuildingPermits_YoY": c.w_perm   * (-feat["BuildingPermits_YoY"]) / 10.0,
        "IndustrialProd_YoY":  c.w_ip     * (-feat["IndustrialProd_YoY"]),
        "CreditSpread":        c.w_credit * (feat["CreditSpread_pp"]),                # pp (raw)
        "InitialClaims_YoY":   c.w_claims * (feat["Claims_YoY"]) / 10.0,              # % -> /10
        "NewOrders_YoY":       c.w_neword * (-feat["NewOrders_YoY"]) / 10.0,          # % -> /10
        "ConsExpect_YoY":      c.w_consx  * (-feat["ConsExpect_YoY"]) / 20.0,         # % -> /20
        "RealM2_YoY":          c.w_m2     * (-feat["RealM2_YoY"]) / 10.0,             # % -> /10
        "Intercept":           c.b0,
    }
    z = sum(contrib.values())
    p = logistic(z)
    return z, p, contrib

def main():
    print("Downloading FRED series…")
    # Core (monthly)
    t10y3m = fred_series("T10Y3M", "1960-01-01", frequency="m", aggregation_method="avg")
    unrate = fred_series("UNRATE", "1960-01-01")
    pcec96 = fred_series("PCEC96", "1960-01-01")
    permit = fred_series("PERMIT", "1960-01-01")
    indpro = fred_series("INDPRO", "1960-01-01")
    usrec  = fred_series("USREC",  "1960-01-01")

    # New 5
    baa10y   = fred_series("BAA10Y",   "1960-01-01")                                        # credit spread (pp)
    ic4wsa_m = fred_series("IC4WSA",   "1967-01-01", frequency="m", aggregation_method="avg")  # monthly avg
    neworder = fred_series("NEWORDER", "1992-02-01")                                        # proxy for ISM
    umcsent  = fred_series("UMCSENT",  "1952-11-01")                                        # expectations proxy
    m2real   = fred_series("M2REAL",   "1959-01-01")                                        # real M2

    # Align to month-start and ensure unique index per series
    t10y3m   = ensure_unique_month_index("T10Y3M",   t10y3m)
    unrate   = ensure_unique_month_index("UNRATE",   unrate)
    pcec96   = ensure_unique_month_index("PCEC96",   pcec96)
    permit   = ensure_unique_month_index("PERMIT",   permit)
    indpro   = ensure_unique_month_index("INDPRO",   indpro)
    usrec    = ensure_unique_month_index("USREC",    usrec)
    baa10y   = ensure_unique_month_index("BAA10Y",   baa10y)
    ic4wsa_m = ensure_unique_month_index("IC4WSA",   ic4wsa_m)
    neworder = ensure_unique_month_index("NEWORDER", neworder)
    umcsent  = ensure_unique_month_index("UMCSENT",  umcsent)
    m2real   = ensure_unique_month_index("M2REAL",   m2real)

    # Defensive: verify each is unique
    series_list = [t10y3m, unrate, pcec96, permit, indpro, usrec,
                   baa10y, ic4wsa_m, neworder, umcsent, m2real]
    names = ["T10Y3M","UNRATE","PCEC96","PERMIT","INDPRO","USREC",
             "BAA10Y","IC4WSA","NEWORDER","UMCSENT","M2REAL"]
    dups = [n for n, s in zip(names, series_list) if s.index.has_duplicates]
    assert not dups, f"Duplicate index remains in: {dups}"

    # Duplicate-safe outer join across all series, then enforce monthly grid
    df = pd.concat(series_list, axis=1).sort_index()

    # Collapse any remaining duplicate monthly labels deterministically (just in case)
    if df.index.has_duplicates:
        df = df.groupby(level=0).last()

    # Regular monthly start-of-month index
    df = df.resample("MS").asfreq()

    # Keep rows where the core (original 5) exist
    df = df.dropna(subset=["T10Y3M", "UNRATE", "PCEC96", "PERMIT", "INDPRO", "USREC"])

    # --- Original Feature Engineering ---
    df["YieldSpread"] = df["T10Y3M"]
    un_ma3 = df["UNRATE"].rolling(3).mean()
    prior12_min = un_ma3.shift(1).rolling(12).min()
    df["SahmGap"] = (un_ma3 - prior12_min).clip(lower=0)
    df["rPCE_6mAnn"] = ((df["PCEC96"] / df["PCEC96"].shift(6))**2 - 1) * 100.0
    df["PERMIT_MA3"] = df["PERMIT"].rolling(3).mean()
    df["BuildingPermits_YoY"] = 100.0 * (df["PERMIT_MA3"] / df["PERMIT_MA3"].shift(12) - 1.0)
    df["INDPRO_MA3"] = df["INDPRO"].rolling(3).mean()
    df["IndustrialProd_YoY"] = 100.0 * (df["INDPRO_MA3"] / df["INDPRO_MA3"].shift(12) - 1.0)

    # --- New Features ---
    # 6) Credit Spreads (pp): BAA10Y is already in pp; smooth to 3mma
    df["CreditSpread_pp"] = df["BAA10Y"].rolling(3).mean()

    # 7) Initial Jobless Claims YoY%: monthly avg of IC4WSA -> 3mma -> YoY%
    df["IC4WSA_MA3"] = df["IC4WSA"].rolling(3).mean()
    df["Claims_YoY"] = 100.0 * (df["IC4WSA_MA3"] / df["IC4WSA_MA3"].shift(12) - 1.0)

    # 8) "ISM New Orders" proxy: NEWORDER YoY% (level is $; YoY handles scale); 3mma first
    df["NEWORDER_MA3"] = df["NEWORDER"].rolling(3).mean()
    df["NewOrders_YoY"] = 100.0 * (df["NEWORDER_MA3"] / df["NEWORDER_MA3"].shift(12) - 1.0)

    # 9) Consumer Expectations proxy: UMCSENT YoY% (lower => higher risk); 3mma first
    df["UMCSENT_MA3"] = df["UMCSENT"].rolling(3).mean()
    df["ConsExpect_YoY"] = 100.0 * (df["UMCSENT_MA3"] / df["UMCSENT_MA3"].shift(12) - 1.0)

    # 10) Real M2 YoY% (lower => higher risk); 3mma first
    df["M2REAL_MA3"] = df["M2REAL"].rolling(3).mean()
    df["RealM2_YoY"] = 100.0 * (df["M2REAL_MA3"] / df["M2REAL_MA3"].shift(12) - 1.0)

    # Label: any recession in next 12 months
    leads = [df["USREC"].shift(-k) for k in range(1, 13)]
    df["y12"] = (pd.concat(leads, axis=1).max(axis=1) >= 1).astype(int)

    # Modeling frame
    X_cols5  = ["YieldSpread","SahmGap","rPCE_6mAnn","BuildingPermits_YoY","IndustrialProd_YoY"]
    X_cols10 = X_cols5 + ["CreditSpread_pp","Claims_YoY","NewOrders_YoY","ConsExpect_YoY","RealM2_YoY"]
    df_model = df.dropna(subset=X_cols10 + ["y12"]).copy()

    # Chronological split (unchanged)
    split_date = "2015-01-01"
    train = df_model.loc[df_model.index < split_date]
    test  = df_model.loc[df_model.index >= split_date]
    X_tr, y_tr = train[X_cols10].values, train["y12"].values
    X_te, y_te = test[X_cols10].values,  test["y12"].values

    # Reference logistic (does not affect manual output)
    if len(np.unique(y_tr)) == 2 and len(X_tr) > 50:
        logit = LogisticRegression(solver="lbfgs", max_iter=1000, C=1e6)
        logit.fit(X_tr, y_tr)
        p_te = logit.predict_proba(X_te)[:, 1]
        auc = roc_auc_score(y_te, p_te)
        print("\nReference fitted model (10 inputs) — Test ROC-AUC:", round(auc, 3))
        print("\nClassification report (threshold=0.5):")
        print(classification_report(y_te, (p_te >= 0.5).astype(int), digits=3))
    else:
        print("\nReference fitted model skipped (insufficient class variety or samples).")

    # Determine aligned latest month (features availability)
    ref_month = df_model.index.max()
    latest = df_model.loc[ref_month]

    # Rounded display (3dp)
    disp = {k: float(np.round(latest[k], 3)) for k in X_cols10}

    # Manual probability (fixed weights, normalized)
    mc = ManualCoeffs10()
    z_manual, p_manual, contrib = manual_logit_and_contrib(disp, mc)

    # Console preview
    print(f"\nAligned latest month: {ref_month.date()}")
    print("Generated inputs (10):")
    for k in X_cols10:
        print(f"  {k:20s}: {disp[k]:+.3f}")
    print("\nManual model logit contributions (higher => more risk):")
    for k, v in contrib.items():
        print(f"  {k:20s} {v:+.3f}")
    print(f"\nManual model recession probability (next 12m): {p_manual*100:.1f}%")

    # ---- Write display-only result JS (manual) ----
    result = {
        "as_of": ref_month.strftime("%Y-%m-01"),
        "title": "10-input (Manual, normalized)",
        "probability_pct": round(p_manual * 100, 1),
        "z": round(z_manual, 4),
        "features": disp,
        "contributions": {k: float(v) for k, v in contrib.items()},
        "notes": {
            "ISM_New_Orders": "Using NEWORDER (capex new orders ex-aircraft) as proxy; replace with ISM feed if available.",
            "Normalization": {
                "Permits_YoY": "/10", "Claims_YoY": "/10", "NewOrders_YoY": "/10",
                "ConsExpect_YoY": "/20", "RealM2_YoY": "/10"
            }
        }
    }
    with open("result10.js", "w", encoding="utf-8") as f:
        f.write("window.recessionResult10=" + json.dumps(result, indent=2) + ";")
    print("\nWrote result10.js")

if __name__ == "__main__":
    main()
