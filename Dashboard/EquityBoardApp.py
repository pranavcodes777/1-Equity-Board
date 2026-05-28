import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="Pranav Equity Dashboard",
    layout="wide"
)

st.title("Pranav Equity Dashboard")

# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------
@st.cache_data
def load_data():
    file_path = "Database/SENSEX30_2000_PRESENT.parquet"

    df = pd.read_parquet(file_path)

    df["Date"] = pd.to_datetime(df["Date"], dayfirst=True)

    df = df.sort_values(["Equity", "Date"])

    df["Daily_Return"] = (
        df.groupby("Equity")["Close"]
        .pct_change()
    )

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
    value=(
        min_date.to_pydatetime(),
        max_date.to_pydatetime()
    )
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
tab1, tab2, tab3 = st.tabs([
    "Indexed Performance",
    "Return Distribution",
    "Correlation Heatmap"
])

# ===================================================
# TAB 1 — INDEXED PERFORMANCE
# ===================================================
with tab1:

    st.subheader("Indexed Performance Comparison")

    perf_df = filtered_df.copy()

    perf_df["Indexed"] = (
        perf_df.groupby("Equity")["Close"]
        .transform(lambda x: x / x.iloc[0] * 100)
    )

    fig = px.line(
        perf_df,
        x="Date",
        y="Indexed",
        color="Equity",
        title="Indexed Performance (Base = 100)"
    )

    fig.update_layout(height=600)

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# ===================================================
# TAB 2 — RETURN DISTRIBUTION
# ===================================================
with tab2:

    st.subheader("Distribution of Daily Returns")

    bins = st.slider(
        "Histogram Bins",
        10,
        100,
        40
    )

    hist_fig = px.histogram(
        filtered_df,
        x="Daily_Return",
        color="Equity",
        nbins=bins,
        opacity=0.5,
        barmode="overlay",
        title="Histogram of Daily Returns"
    )

    hist_fig.update_layout(height=600)

    st.plotly_chart(
        hist_fig,
        use_container_width=True
    )

# ===================================================
# TAB 3 — CORRELATION HEATMAP
# ===================================================
with tab3:

    st.subheader("Correlation Heatmap")

    pivot_df = filtered_df.pivot_table(
        index="Date",
        columns="Equity",
        values="Daily_Return"
    )

    corr_matrix = pivot_df.corr()

    heatmap = px.imshow(
        corr_matrix,
        text_auto=True,
        aspect="auto",
        title="Correlation Matrix"
    )

    heatmap.update_layout(height=700)

    st.plotly_chart(
        heatmap,
        use_container_width=True
    )