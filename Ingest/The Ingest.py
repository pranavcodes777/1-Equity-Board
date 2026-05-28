import os
import sys

import pandas as pd
import yfinance as yf

# =========================================================
# SENSEX 30 STOCKS + NIFTY + SENSEX
# =========================================================

stocks = {
    "Reliance": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFC Bank": "HDFCBANK.NS",
    "Infosys": "INFY.NS",
    "ICICI Bank": "ICICIBANK.NS",
    "Hindustan Unilever": "HINDUNILVR.NS",
    "ITC": "ITC.NS",
    "State Bank of India": "SBIN.NS",
    "Bharti Airtel": "BHARTIARTL.NS",
    "Kotak Mahindra Bank": "KOTAKBANK.NS",
    "Larsen & Toubro": "LT.NS",
    "Axis Bank": "AXISBANK.NS",
    "Asian Paints": "ASIANPAINT.NS",
    "Maruti Suzuki": "MARUTI.NS",
    "Sun Pharma": "SUNPHARMA.NS",
    "Titan": "TITAN.NS",
    "UltraTech Cement": "ULTRACEMCO.NS",
    "Nestle India": "NESTLEIND.NS",
    "Bajaj Finance": "BAJFINANCE.NS",
    "Mahindra & Mahindra": "M&M.NS",
    "Power Grid": "POWERGRID.NS",
    "NTPC": "NTPC.NS",
    "Tata Steel": "TATASTEEL.NS",
    "Wipro": "WIPRO.NS",
    "Tech Mahindra": "TECHM.NS",
    "IndusInd Bank": "INDUSINDBK.NS",
    "HCL Technologies": "HCLTECH.NS",
    "Bajaj Finserv": "BAJAJFINSV.NS",
    "JSW Steel": "JSWSTEEL.NS",
    "Tata Motors": "TATAMOTORS.NS",

    # Indices
    "NIFTY 50": "^NSEI",
    "SENSEX": "^BSESN"
}

DEFAULT_START  = "2000-01-01"
SUMMARY_PATH   = r"E:\Quarks&Quants\Quants\0.1. Equity Board\Automation\last_run.txt"

# =========================================================
# PATHS
# =========================================================

parquet_path = r"E:\Quarks&Quants\Quants\0.1. Equity Board\Database\SENSEX30_2000_PRESENT.parquet"
csv_path     = r"E:\Quarks&Quants\Quants\0.1. Equity Board\Database\SENSEX30_2000_PRESENT.csv"

# =========================================================
# LOAD EXISTING DATA (UPSERT BASE)
# =========================================================

if os.path.exists(parquet_path):
    print("Existing database found — loading for upsert...\n")
    existing_df = pd.read_parquet(parquet_path)
    existing_df["Date"] = pd.to_datetime(existing_df["Date"], dayfirst=True)

    # Most recent date per equity
    latest_dates = (
        existing_df.groupby("Equity")["Date"]
        .max()
        .to_dict()
    )
    print("Latest dates in existing database:")
    for equity, date in latest_dates.items():
        print(f"  {equity}: {date.strftime('%d-%b-%Y')}")
    print()
else:
    print("No existing database found — full download from scratch.\n")
    existing_df = pd.DataFrame()
    latest_dates = {}

rows_before = len(existing_df)

# =========================================================
# DOWNLOAD NEW / INCREMENTAL DATA
# =========================================================

new_data        = []
equity_new_rows = {}   # equity_name -> new row count

for equity_name, ticker in stocks.items():

    # Determine start date for this equity
    if equity_name in latest_dates:
        # Start one day after latest to avoid re-downloading known data
        # (small overlap is fine — dedup handles it)
        start = latest_dates[equity_name].strftime("%Y-%m-%d")
        print(f"Updating  {equity_name} from {start}...")
    else:
        start = DEFAULT_START
        print(f"New equity {equity_name} — full download from {start}...")

    try:

        data = yf.download(
            ticker,
            start=start,
            end="2030-01-01",
            interval="1d",
            auto_adjust=False,
            progress=False
        )

        if data.empty:
            print(f"  No new data for {equity_name}")
            continue

        # Flatten MultiIndex columns
        data.columns = data.columns.get_level_values(0)

        # Reset index
        data.reset_index(inplace=True)

        # Keep required columns
        data = data[["Date", "Open", "High", "Low", "Close", "Volume"]]

        # Add Equity column
        data.insert(0, "Equity", equity_name)

        # Format Date
        data["Date"] = pd.to_datetime(data["Date"]).dt.strftime("%d-%b-%Y")

        # Round OHLC
        data[["Open", "High", "Low", "Close"]] = data[
            ["Open", "High", "Low", "Close"]
        ].round(2)

        # Volume as integer
        data["Volume"] = data["Volume"].astype("int64")

        new_data.append(data)
        print(f"  Done: {len(data)} new rows")
        equity_new_rows[equity_name] = len(data)

    except Exception as e:
        print(f"  ERROR — {equity_name}: {e}")

# =========================================================
# UPSERT — COMBINE EXISTING + NEW
# =========================================================

if new_data:
    new_df = pd.concat(new_data, ignore_index=True)

    if not existing_df.empty:
        # Reformat existing dates back to string to match new_df
        existing_df["Date"] = pd.to_datetime(
            existing_df["Date"]
        ).dt.strftime("%d-%b-%Y")

        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        combined_df = new_df

    # Deduplicate on (Equity, Date) — keep last (newest fetch wins)
    combined_df = combined_df.drop_duplicates(
        subset=["Equity", "Date"],
        keep="last"
    )

    # Sort
    combined_df["_sort_date"] = pd.to_datetime(combined_df["Date"], dayfirst=True)
    combined_df = combined_df.sort_values(["Equity", "_sort_date"])
    combined_df = combined_df.drop(columns=["_sort_date"])
    combined_df.reset_index(drop=True, inplace=True)

    final_df = combined_df

else:
    print("\nNo new data downloaded. Database is already up to date.")
    final_df = existing_df
    if not final_df.empty:
        final_df["Date"] = pd.to_datetime(
            final_df["Date"]
        ).dt.strftime("%d-%b-%Y")

# =========================================================
# SAVE
# =========================================================

final_df.to_parquet(parquet_path, index=False, engine="pyarrow")
final_df.to_csv(csv_path, index=False)

# =========================================================
# SUMMARY
# =========================================================

from datetime import datetime

rows_after     = len(final_df)
new_rows_added = rows_after - rows_before
date_col       = pd.to_datetime(final_df["Date"], dayfirst=True)
run_time       = datetime.now().strftime("%d-%b-%Y %H:%M:%S")

summary_lines = [
    "============================================================",
    f"  RUN TIME       : {run_time}",
    f"  INGEST STATUS  : SUCCESS",
    f"  NEW ROWS ADDED : {new_rows_added:,}",
    f"  TOTAL ROWS     : {rows_after:,}",
    f"  EQUITIES       : {final_df['Equity'].nunique()}",
    f"  DATE RANGE     : {date_col.min().strftime('%d-%b-%Y')} -> {date_col.max().strftime('%d-%b-%Y')}",
    "------------------------------------------------------------",
]

if equity_new_rows:
    summary_lines.append("  NEW ROWS PER EQUITY:")
    for eq, cnt in sorted(equity_new_rows.items()):
        summary_lines.append(f"    {eq:<25} {cnt:>6} rows")
else:
    summary_lines.append("  No new rows fetched — already up to date.")

summary_lines.append("============================================================")

summary_text = "\n".join(summary_lines)

print("\n" + summary_text)

# Write last_run.txt (bat file appends git push result below this)
with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
    f.write(summary_text + "\n")
    f.write("  GIT PUSH       : PENDING\n")
    f.write("============================================================\n")

if sys.stdin.isatty():
    input("\nPress Enter to exit...")
