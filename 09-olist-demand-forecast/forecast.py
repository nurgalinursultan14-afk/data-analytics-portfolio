"""Forecast daily Olist orders two weeks ahead and backtest four methods.

Usage:
    python ../06-olist-ecommerce-sql/build_db.py   # once: builds ../06-olist-ecommerce-sql/output/olist.db
    python forecast.py                             # -> output/*.csv, output/*.png
"""
import sqlite3
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.holtwinters import ExponentialSmoothing

warnings.filterwarnings("ignore")
HERE = Path(__file__).parent
DB = HERE.parent / "06-olist-ecommerce-sql" / "output" / "olist.db"
OUT = HERE / "output"

# The series: completed orders per day. Before Feb 2017 the marketplace is still ramping up
# (single-digit days), and after Aug 19, 2018 the dataset's collection cutoff makes counts
# collapse (252 -> 11 in ten days), so both ends are trimmed. Whole weeks: Mon Feb 6, 2017 to Sun Aug 19, 2018.
START, END = "2017-02-06", "2018-08-19"
HORIZON = 14          # forecast two weeks ahead
FOLDS = 20            # rolling origins every 14 days, the last ending at END (covers Black Friday 2017)

# Days that move demand and are known in advance.
EVENTS = {
    "black_friday": ["2017-11-24"],
    "black_friday_weekend": ["2017-11-25", "2017-11-26", "2017-11-27", "2017-11-28"],
    "christmas_lull": [str(d.date()) for d in pd.date_range("2017-12-22", "2018-01-01")],
}


def load_series():
    con = sqlite3.connect(DB)
    s = pd.read_sql("SELECT date(purchased_at) AS d, COUNT(*) AS n FROM sales GROUP BY 1",
                    con, parse_dates=["d"]).set_index("d").n
    return s.asfreq("D", fill_value=0)[START:END]


def design(index):
    """Regression features: trend, day of week, event flags (all known ahead of time)."""
    X = pd.DataFrame(index=index)
    X["trend"] = (index - pd.Timestamp(START)).days / 365
    for dow in range(1, 7):
        X[f"dow_{dow}"] = (index.dayofweek == dow).astype(float)
    for name, days in EVENTS.items():
        X[name] = index.isin(pd.to_datetime(days)).astype(float)
    return sm.add_constant(X, has_constant="add")


def seasonal_naive(train, h):
    """Same weekday last week."""
    last_week = train[-7:].values
    return np.resize(last_week, h)


def weekday_average(train, h):
    """Mean of the same weekday over the last 4 weeks."""
    w = train[-28:]
    by_dow = w.groupby(w.index.dayofweek).mean()
    idx = pd.date_range(train.index[-1] + pd.Timedelta(days=1), periods=h)
    return by_dow.reindex(idx.dayofweek).values


def holt_winters(train, h):
    """Damped additive trend + weekly seasonality on log orders, fit on the last 26 weeks."""
    y = np.log1p(train[-182:])
    fit = ExponentialSmoothing(y, trend="add", damped_trend=True, seasonal="add",
                               seasonal_periods=7, initialization_method="estimated").fit()
    return np.expm1(fit.forecast(h).values)


def regression(train, h):
    """OLS on log orders: trend, weekday, events. Fit on the last 26 weeks so the level is recent."""
    y = np.log1p(train[-182:])
    idx = pd.date_range(train.index[-1] + pd.Timedelta(days=1), periods=h)
    model = sm.OLS(y, design(y.index)).fit()
    return np.expm1(model.predict(design(idx)).values)


def ensemble(train, h):
    """Plain average of seasonal naive, Holt-Winters and regression."""
    return (seasonal_naive(train, h) + holt_winters(train, h) + regression(train, h)) / 3


METHODS = {
    "Seasonal naive (same weekday last week)": seasonal_naive,
    "Weekday average (last 4 weeks)": weekday_average,
    "Holt-Winters (damped trend, weekly season)": holt_winters,
    "Regression (trend + weekday + events)": regression,
    "Ensemble (average of naive, Holt-Winters, regression)": ensemble,
}


def backtest(s):
    rows, preds = [], []
    end = pd.Timestamp(END)
    origins = [end - pd.Timedelta(days=HORIZON * k) for k in range(FOLDS, 0, -1)]
    for origin in origins:
        train = s[:origin]
        test = s[origin + pd.Timedelta(days=1): origin + pd.Timedelta(days=HORIZON)]
        for name, fn in METHODS.items():
            f = fn(train, HORIZON)
            err = f - test.values
            rows.append({
                "origin": origin.date(), "method": name,
                "mae": np.abs(err).mean(),
                "mape": (np.abs(err) / test.values).mean() * 100,
                "two_week_total_error_pct": (f.sum() - test.sum()) / test.sum() * 100,
            })
            preds.append(pd.DataFrame({"date": test.index, "method": name, "actual": test.values, "forecast": f.round(1)}))
    return pd.DataFrame(rows), pd.concat(preds)


def main():
    OUT.mkdir(exist_ok=True)
    s = load_series()
    print(f"{len(s)} days, {s.index[0].date()} to {s.index[-1].date()}, {s.sum():,} orders")

    folds, preds = backtest(s)
    summary = (folds.groupby("method")
               .agg(mae=("mae", "mean"), mape=("mape", "mean"),
                    abs_total_error_pct=("two_week_total_error_pct", lambda x: x.abs().mean()))
               .round(1).sort_values("mae"))
    folds.round(2).to_csv(OUT / "backtest_folds.csv", index=False)
    preds.to_csv(OUT / "backtest_predictions.csv", index=False)
    summary.to_csv(OUT / "backtest_summary.csv")
    print(summary.to_string())
    naive = summary.loc["Seasonal naive (same weekday last week)", "mae"]
    print(f"best vs seasonal naive: {(1 - summary.mae.iloc[0] / naive) * 100:.0f}% lower MAE")

    # Weekday profile (share of a week's orders) and the event lift, from the full regression
    y = np.log1p(s)
    full = sm.OLS(y, design(s.index)).fit()
    dow_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    effects = {dow_names[d]: (np.exp(full.params.get(f"dow_{d}", 0.0)) - 1) * 100 for d in range(7)}
    events = {k: (np.exp(full.params[k]) - 1) * 100 for k in EVENTS}
    pd.Series(effects, name="pct_vs_monday").round(1).to_csv(OUT / "weekday_effect.csv")
    pd.Series(events, name="pct_lift").round(0).to_csv(OUT / "event_effect.csv")
    print("weekday vs Monday %:", {k: round(v, 1) for k, v in effects.items()})
    print("event lift %:", {k: round(v) for k, v in events.items()})

    # Final forecast: the best method from the backtest, 14 days past END, with an
    # empirical 80% band from that method's backtest errors (ratio of actual to forecast).
    best = summary.index[0]
    bp = preds[preds.method == best]
    ratio = bp.actual / bp.forecast
    lo, hi = ratio.quantile([0.1, 0.9])
    f = METHODS[best](s, HORIZON)
    fidx = pd.date_range(s.index[-1] + pd.Timedelta(days=1), periods=HORIZON)
    fc = pd.DataFrame({"date": fidx.date, "forecast": f.round(0), "low_80": (f * lo).round(0), "high_80": (f * hi).round(0)})
    fc.to_csv(OUT / "forecast_next_14_days.csv", index=False)
    print(f"best: {best}; 80% band x{lo:.2f} to x{hi:.2f}")

    # Charts
    plt.rcParams.update({"axes.spines.top": False, "axes.spines.right": False, "font.size": 10})
    fig, ax = plt.subplots(figsize=(12, 4.2))
    ax.plot(s.index, s.values, color="#9aa5b1", lw=0.8, label="Orders per day")
    ax.plot(s.rolling(7, center=True).mean(), color="#2a6fdb", lw=2, label="7-day average")
    ax.annotate("Black Friday\n1,166 orders", xy=(pd.Timestamp("2017-11-24"), s["2017-11-24"]),
                xytext=(pd.Timestamp("2017-08-01"), 1000), arrowprops=dict(arrowstyle="->", color="#555"), fontsize=9)
    ax.set_title("Daily orders, Feb 2017 to Aug 2018", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper left")
    fig.tight_layout(); fig.savefig(OUT / "chart_daily_orders.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 3.6))
    colors = ["#2a6fdb" if m == best else "#9aa5b1" for m in summary.index]
    ax.barh(summary.index[::-1], summary.mae[::-1], color=colors[::-1])
    for i, v in enumerate(summary.mae[::-1]):
        ax.text(v + 0.5, i, f"{v:.1f}", va="center", fontsize=9)
    ax.set_xlabel("Mean absolute error, orders per day (20 two-week backtests)")
    ax.set_title("Which forecast method wins?", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(OUT / "chart_backtest.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 4))
    recent = s["2018-05-01":]
    ax.plot(recent.index, recent.values, color="#14171f", lw=1.2, label="Actual")
    last = bp[pd.to_datetime(bp.date) >= pd.Timestamp("2018-05-01")]
    first = True
    for _, g in last.groupby(np.arange(len(last)) // HORIZON):
        ax.plot(pd.to_datetime(g.date), g.forecast, color="#2a6fdb", lw=1.6, label="Backtest forecast" if first else None)
        first = False
    ax.fill_between(pd.to_datetime(fc.date), fc.low_80, fc.high_80, color="#2a6fdb", alpha=0.18, label="Next 14 days, 80% band")
    ax.plot(pd.to_datetime(fc.date), fc.forecast, color="#2a6fdb", lw=2, ls="--")
    ax.set_title("Ensemble forecast: backtests since May 2018 and the next two weeks", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)
    fig.tight_layout(); fig.savefig(OUT / "chart_forecast.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
