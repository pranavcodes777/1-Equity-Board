import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(page_title="Pranav Equity Dashboard", layout="wide")
st.title("Pranav Equity Dashboard")

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------
@st.cache_data
def load_data():
    df = pd.read_parquet("Database/SENSEX30_2000_PRESENT.parquet")
    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)
    df = df.sort_values(["Equity", "Date"])
    df["Daily_Return"] = df.groupby("Equity")["Close"].pct_change()
    return df

df = load_data()

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
st.sidebar.header("Controls")

equities = sorted(df["Equity"].unique())

selected_equities = st.sidebar.multiselect(
    "Select Equities",
    equities,
    default=equities[:4]
)

min_date = df["Date"].min()
max_date = df["Date"].max()

date_range = st.sidebar.slider(
    "Select Date Range",
    min_value=min_date.to_pydatetime(),
    max_value=max_date.to_pydatetime(),
    value=(min_date.to_pydatetime(), max_date.to_pydatetime())
)

start_date, end_date = date_range

filtered_df = df[
    (df["Equity"].isin(selected_equities)) &
    (df["Date"] >= pd.to_datetime(start_date)) &
    (df["Date"] <= pd.to_datetime(end_date))
]

# ---------------------------------------------------
# TABS
# ---------------------------------------------------
(
    tab_indexed, tab_dist, tab_corr,
    tab_returns, tab_ma,
    tab_vol, tab_beta, tab_sharpe
) = st.tabs([
    "Indexed Performance",
    "Return Distribution",
    "Correlation Heatmap",
    "Returns Snapshot",
    "Moving Averages",
    "Rolling Volatility",
    "Beta vs NIFTY",
    "Sharpe & Sortino",
])

# ===================================================
# TAB 1 — INDEXED PERFORMANCE
# ===================================================
with tab_indexed:
    st.subheader("Indexed Performance Comparison")

    perf_df = filtered_df.copy()
    perf_df["Indexed"] = (
        perf_df.groupby("Equity")["Close"]
        .transform(lambda x: x / x.iloc[0] * 100)
    )

    fig = px.line(
        perf_df, x="Date", y="Indexed", color="Equity",
        title="Indexed Performance (Base = 100)"
    )
    fig.update_layout(height=600)
    st.plotly_chart(fig, use_container_width=True)

# ===================================================
# TAB 2 — RETURN DISTRIBUTION
# ===================================================
with tab_dist:
    st.subheader("Distribution of Daily Returns")

    bins = st.slider("Histogram Bins", 10, 100, 40)

    hist_fig = px.histogram(
        filtered_df, x="Daily_Return", color="Equity",
        nbins=bins, opacity=0.5, barmode="overlay",
        title="Histogram of Daily Returns"
    )
    hist_fig.update_layout(height=600)
    st.plotly_chart(hist_fig, use_container_width=True)

# ===================================================
# TAB 3 — CORRELATION HEATMAP
# ===================================================
with tab_corr:
    st.subheader("Correlation Heatmap")

    pivot_df = filtered_df.pivot_table(
        index="Date", columns="Equity", values="Daily_Return"
    )
    corr_matrix = pivot_df.corr()

    heatmap = px.imshow(
        corr_matrix, text_auto=True, aspect="auto",
        title="Correlation Matrix"
    )
    heatmap.update_layout(height=700)
    st.plotly_chart(heatmap, use_container_width=True)

# ===================================================
# TAB 4 — RETURNS SNAPSHOT
# ===================================================
with tab_returns:
    st.subheader("Returns Snapshot")
    st.caption("Trailing returns computed from each equity's most recent available date.")

    PERIODS = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "6M": 126, "1Y": 252}

    rows = []
    for equity in selected_equities:
        eq = df[df["Equity"] == equity].sort_values("Date")
        if eq.empty:
            continue

        latest       = eq["Close"].iloc[-1]
        latest_date  = eq["Date"].iloc[-1]

        row = {
            "Equity"      : equity,
            "Last Price"  : round(latest, 2),
            "As of"       : latest_date.strftime("%d-%b-%Y"),
        }

        for label, n in PERIODS.items():
            if len(eq) > n:
                row[label] = round((latest / eq["Close"].iloc[-(n + 1)] - 1) * 100, 2)
            else:
                row[label] = None

        ytd = eq[eq["Date"].dt.year == latest_date.year]
        row["YTD"] = round((latest / ytd["Close"].iloc[0] - 1) * 100, 2) if len(ytd) > 1 else None

        rows.append(row)

    if rows:
        snap = pd.DataFrame(rows).set_index("Equity")
        ret_cols = ["1D", "1W", "1M", "3M", "6M", "1Y", "YTD"]

        def _color_ret(v):
            if pd.isna(v):
                return ""
            return "color: #2ecc71; font-weight:bold" if v > 0 else "color: #e74c3c; font-weight:bold"

        styled_snap = (
            snap.style
            .map(_color_ret, subset=ret_cols)
            .format({c: "{:.2f}%" for c in ret_cols}, na_rep="—")
        )
        st.dataframe(styled_snap, use_container_width=True)
    else:
        st.info("Select equities from the sidebar.")

# ===================================================
# TAB 5 — MOVING AVERAGES
# ===================================================
with tab_ma:
    st.subheader("Moving Averages — SMA 20 / 50 / 200")

    if not selected_equities:
        st.info("Select at least one equity.")
    else:
        eq_sel = st.selectbox("Equity", selected_equities, key="ma_eq")

        ma_df = (
            df[df["Equity"] == eq_sel]
            .sort_values("Date")
            .query("Date >= @start_date and Date <= @end_date")
            .copy()
        )

        ma_df["SMA_20"]  = ma_df["Close"].rolling(20).mean()
        ma_df["SMA_50"]  = ma_df["Close"].rolling(50).mean()
        ma_df["SMA_200"] = ma_df["Close"].rolling(200).mean()

        fig_ma = go.Figure()
        fig_ma.add_trace(go.Scatter(
            x=ma_df["Date"], y=ma_df["Close"],
            name="Close", line=dict(color="#636EFA", width=1.5)
        ))
        fig_ma.add_trace(go.Scatter(
            x=ma_df["Date"], y=ma_df["SMA_20"],
            name="SMA 20", line=dict(color="#FFA15A", width=1.2, dash="dot")
        ))
        fig_ma.add_trace(go.Scatter(
            x=ma_df["Date"], y=ma_df["SMA_50"],
            name="SMA 50", line=dict(color="#00CC96", width=1.2, dash="dash")
        ))
        fig_ma.add_trace(go.Scatter(
            x=ma_df["Date"], y=ma_df["SMA_200"],
            name="SMA 200", line=dict(color="#EF553B", width=1.5)
        ))

        fig_ma.update_layout(
            title=f"{eq_sel} — Price & Moving Averages",
            height=600, xaxis_title="Date", yaxis_title="Price (INR)"
        )
        st.plotly_chart(fig_ma, use_container_width=True)

# ===================================================
# TAB 6 — ROLLING VOLATILITY
# ===================================================
with tab_vol:
    st.subheader("Rolling Annualised Volatility")

    VOL_WINDOWS = {"30-Day": 30, "90-Day": 90, "252-Day": 252}
    win_label = st.radio("Window", list(VOL_WINDOWS.keys()), horizontal=True, key="vol_win")
    window    = VOL_WINDOWS[win_label]

    fig_vol = go.Figure()

    for equity in selected_equities:
        eq = filtered_df[filtered_df["Equity"] == equity].sort_values("Date").copy()
        eq["Vol"] = eq["Daily_Return"].rolling(window).std() * np.sqrt(252) * 100
        eq = eq.dropna(subset=["Vol"])
        if eq.empty:
            continue
        fig_vol.add_trace(go.Scatter(x=eq["Date"], y=eq["Vol"], name=equity, mode="lines"))

    fig_vol.update_layout(
        title=f"{win_label} Rolling Annualised Volatility (%)",
        height=600, xaxis_title="Date", yaxis_title="Volatility (%)"
    )
    st.plotly_chart(fig_vol, use_container_width=True)

# ===================================================
# TAB 7 — BETA vs NIFTY
# ===================================================
with tab_beta:
    st.subheader("Rolling Beta vs NIFTY 50")

    nifty = (
        df[df["Equity"] == "NIFTY 50"]
        .sort_values("Date")[["Date", "Daily_Return"]]
        .rename(columns={"Daily_Return": "NIFTY_Ret"})
    )

    beta_win = st.slider("Rolling Window (days)", 60, 252, 120, step=10, key="beta_win")

    fig_beta = go.Figure()
    any_plotted = False

    for equity in selected_equities:
        if equity == "NIFTY 50":
            continue

        eq = (
            filtered_df[filtered_df["Equity"] == equity][["Date", "Daily_Return"]]
            .sort_values("Date")
            .merge(nifty, on="Date", how="inner")
        )

        if len(eq) < beta_win:
            st.warning(f"{equity}: insufficient data for {beta_win}-day beta window.")
            continue

        eq["Beta"] = (
            eq["Daily_Return"].rolling(beta_win).cov(eq["NIFTY_Ret"]) /
            eq["NIFTY_Ret"].rolling(beta_win).var()
        )

        fig_beta.add_trace(go.Scatter(x=eq["Date"], y=eq["Beta"], name=equity, mode="lines"))
        any_plotted = True

    if any_plotted:
        fig_beta.add_hline(y=1.0, line_dash="dash", line_color="gray", annotation_text="β = 1  ")
        fig_beta.update_layout(
            title=f"{beta_win}-Day Rolling Beta vs NIFTY 50",
            height=600, xaxis_title="Date", yaxis_title="Beta"
        )
        st.plotly_chart(fig_beta, use_container_width=True)
    else:
        st.info("No eligible equities selected (exclude NIFTY 50 itself).")

# ===================================================
# TAB 8 — SHARPE & SORTINO
# ===================================================
with tab_sharpe:
    st.subheader("Sharpe & Sortino Ratios")
    st.caption("Computed over the selected date range.")

    rf_pct  = st.number_input("Annual Risk-Free Rate (%)", value=6.5, step=0.1, key="rf")
    rf_daily = (rf_pct / 100) / 252

    rows_r = []
    for equity in selected_equities:
        eq = filtered_df[filtered_df["Equity"] == equity].dropna(subset=["Daily_Return"])
        if len(eq) < 30:
            continue

        r       = eq["Daily_Return"]
        excess  = r - rf_daily
        ann_ret = r.mean() * 252
        ann_vol = r.std() * np.sqrt(252)

        sharpe = (excess.mean() * 252) / ann_vol if ann_vol > 0 else None

        downside      = r[r < rf_daily]
        downside_vol  = downside.std() * np.sqrt(252) if len(downside) > 1 else None
        sortino = (excess.mean() * 252) / downside_vol if downside_vol and downside_vol > 0 else None

        rows_r.append({
            "Equity"            : equity,
            "Ann. Return (%)"   : round(ann_ret * 100, 2),
            "Ann. Volatility (%)": round(ann_vol * 100, 2),
            "Sharpe"            : round(sharpe, 2) if sharpe is not None else None,
            "Sortino"           : round(sortino, 2) if sortino is not None else None,
        })

    if rows_r:
        risk_df = (
            pd.DataFrame(rows_r)
            .set_index("Equity")
            .sort_values("Sharpe", ascending=False)
        )

        def _color_ratio(v):
            if pd.isna(v):
                return ""
            if v >= 1.5:
                return "color: #2ecc71; font-weight:bold"
            elif v >= 0.5:
                return "color: #f39c12; font-weight:bold"
            else:
                return "color: #e74c3c; font-weight:bold"

        styled_risk = risk_df.style.map(_color_ratio, subset=["Sharpe", "Sortino"])
        st.dataframe(styled_risk, use_container_width=True)
        st.caption("Green ≥ 1.5 · Orange 0.5–1.5 · Red < 0.5")
    else:
        st.info("Select equities from the sidebar.")
