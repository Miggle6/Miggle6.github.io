window.recessionResult10={
  "as_of": "2025-06-01",
  "title": "10-input (Manual, normalized)",
  "probability_pct": 30.7,
  "z": -0.8125,
  "features": {
    "YieldSpread": -0.04,
    "SahmGap": 0.167,
    "rPCE_6mAnn": -0.148,
    "BuildingPermits_YoY": -2.727,
    "IndustrialProd_YoY": 0.953,
    "CreditSpread_pp": 1.85,
    "Claims_YoY": 5.189,
    "NewOrders_YoY": 2.44,
    "ConsExpect_YoY": -23.03,
    "RealM2_YoY": 1.802
  },
  "contributions": {
    "YieldSpread": 0.12672,
    "SahmGap": 0.30060000000000003,
    "rPCE_6mAnn": 0.148,
    "BuildingPermits_YoY": 0.32724,
    "IndustrialProd_YoY": -0.9148799999999999,
    "CreditSpread": 1.11,
    "InitialClaims_YoY": 0.72646,
    "NewOrders_YoY": -0.3416,
    "ConsExpect_YoY": 0.9212000000000001,
    "RealM2_YoY": -0.21624,
    "Intercept": -3.0
  },
  "notes": {
    "ISM_New_Orders": "Using NEWORDER (capex new orders ex-aircraft) as proxy; replace with ISM feed if available.",
    "Normalization": {
      "Permits_YoY": "/10",
      "Claims_YoY": "/10",
      "NewOrders_YoY": "/10",
      "ConsExpect_YoY": "/20",
      "RealM2_YoY": "/10"
    }
  }
};