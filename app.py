import io

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from portfolio_parser import parse_broker_upload, tradingview_csv

st.set_page_config(page_title="Broker Portfolio Analyzer", page_icon="📊", layout="wide")

st.title("Broker Portfolio Analyzer")
st.caption("Upload your broker positions export, then get a heat map, allocation breakdown, P&L tables, lot cleanup, and download-ready analysis files. No default portfolio file is bundled in this app.")

with st.sidebar:
    st.header("Upload")
    uploaded = st.file_uploader("Broker positions file", type=["xls", "xlsx", "csv"])
    st.write("Currently optimized for Wells Fargo Advisors position exports.")
    color_by = st.radio("Heat map color by", ["Today's Change %", "Unrealized P&L %", "Portfolio Weight"], horizontal=False)
    min_tile = st.slider("Hide tiny tiles below market value", 0, 5000, 0, 250)

if uploaded is None:
    st.info("Upload your latest broker positions Excel file to generate the dashboard.")
    st.markdown(
        """
        **Workflow this app is built for:**
        1. Download positions from your broker as `.xls` or `.xlsx`.
        2. Upload the file here.
        3. Review the heat map, allocation, winners/losers, income, and concentration.
        4. Export cleaned CSVs for deeper analysis.
        """
    )
    st.stop()

try:
    result = parse_broker_upload(uploaded)
except Exception as e:
    st.error(f"Could not parse this file: {e}")
    st.stop()

summary = result.summary.copy()
lots = result.lots.copy()
allocation = result.allocation.copy()

# Top metrics.
broker_total = result.broker_total if result.broker_total else allocation["Market Value"].sum()
ugl_total = summary["Unrealized P&L $"].fillna(0).sum()
today_total = summary["Today's Change $"].fillna(0).sum()
equity_count = summary.loc[summary["Asset Type"].eq("Stocks"), "Symbol"].nunique()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Total portfolio value", f"${broker_total:,.0f}")
c2.metric("Unrealized P&L", f"${ugl_total:,.0f}")
c3.metric("Today's change", f"${today_total:,.0f}", f"{today_total / broker_total:.2%}" if broker_total else None)
c4.metric("Equity positions", f"{equity_count} stocks")
c5.metric("Priced date", result.priced_date or "Not found")

st.divider()

# Asset allocation bar / pie.
left, right = st.columns([1.25, 2])
with left:
    st.subheader("Asset allocation")
    fig_alloc = px.pie(allocation, names="Asset Class", values="Market Value", hole=0.45)
    fig_alloc.update_traces(textposition="inside", textinfo="percent+label")
    fig_alloc.update_layout(margin=dict(l=0, r=0, t=20, b=20), height=360)
    st.plotly_chart(fig_alloc, use_container_width=True)

with right:
    st.subheader("Portfolio heat map")
    hm = summary[summary["Market Value"].fillna(0) >= min_tile].copy()
    if hm.empty:
        st.warning("No holdings passed the market value filter.")
    else:
        fig = px.treemap(
            hm,
            path=["Asset Type", "Symbol"],
            values="Market Value",
            color=color_by,
            color_continuous_scale="RdYlGn",
            color_continuous_midpoint=0 if color_by != "Portfolio Weight" else hm[color_by].median(),
            hover_data={
                "Description": True,
                "Market Value": ":$,.2f",
                "Portfolio Weight": ":.2%",
                "Unrealized P&L $": ":$,.2f",
                "Unrealized P&L %": ":.2%",
                "Today's Change $": ":$,.2f",
                "Today's Change %": ":.2%",
            },
        )
        fig.update_traces(texttemplate="<b>%{label}</b><br>%{value:$,.0f}")
        fig.update_layout(margin=dict(l=0, r=0, t=20, b=20), height=500)
        st.plotly_chart(fig, use_container_width=True)

# Tabs.
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Holdings", "Winners / Losers", "Income", "Tax lots", "Exports"])

with tab1:
    st.subheader("Cleaned holdings summary")
    display_cols = [
        "Symbol", "Description", "Asset Type", "Shares", "Last Price", "Market Value", "Portfolio Weight",
        "Total Cost", "Avg Cost", "Unrealized P&L $", "Unrealized P&L %", "Today's Change $", "Today's Change %", "Lot Count"
    ]
    st.dataframe(
        summary[display_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Market Value": st.column_config.NumberColumn(format="$%.2f"),
            "Portfolio Weight": st.column_config.NumberColumn(format="%.2f%%"),
            "Total Cost": st.column_config.NumberColumn(format="$%.2f"),
            "Avg Cost": st.column_config.NumberColumn(format="$%.2f"),
            "Unrealized P&L $": st.column_config.NumberColumn(format="$%.2f"),
            "Unrealized P&L %": st.column_config.NumberColumn(format="%.2f%%"),
            "Today's Change $": st.column_config.NumberColumn(format="$%.2f"),
            "Today's Change %": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Biggest unrealized winners")
        st.dataframe(summary.sort_values("Unrealized P&L $", ascending=False).head(10)[["Symbol", "Market Value", "Unrealized P&L $", "Unrealized P&L %", "Portfolio Weight"]], use_container_width=True, hide_index=True)
    with c2:
        st.subheader("Biggest unrealized losers")
        st.dataframe(summary.sort_values("Unrealized P&L $", ascending=True).head(10)[["Symbol", "Market Value", "Unrealized P&L $", "Unrealized P&L %", "Portfolio Weight"]], use_container_width=True, hide_index=True)

    st.subheader("Concentration check")
    top5_weight = summary.head(5)["Portfolio Weight"].sum()
    top10_weight = summary.head(10)["Portfolio Weight"].sum()
    c3, c4 = st.columns(2)
    c3.metric("Top 5 holdings weight", f"{top5_weight:.2%}")
    c4.metric("Top 10 holdings weight", f"{top10_weight:.2%}")

with tab3:
    st.subheader("Estimated annual income")
    income_df = summary[summary["Est. Annual Income"].fillna(0) > 0].sort_values("Est. Annual Income", ascending=False)
    st.metric("Estimated annual income from securities", f"${income_df['Est. Annual Income'].sum():,.0f}")
    fig_income = px.bar(income_df.head(20), x="Symbol", y="Est. Annual Income", hover_data=["Description", "Market Value", "Yield on MV"])
    fig_income.update_layout(height=400, margin=dict(l=0, r=0, t=20, b=20))
    st.plotly_chart(fig_income, use_container_width=True)
    st.dataframe(income_df[["Symbol", "Description", "Asset Type", "Market Value", "Est. Annual Income", "Yield on MV"]], use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Tax-lot / source-row cleanup")
    st.write("The parser avoids double-counting broker summary rows and keeps usable lot rows for trade-date and basis analysis.")
    if lots.empty:
        st.warning("No lot rows found.")
    else:
        st.dataframe(lots, use_container_width=True, hide_index=True)

with tab5:
    st.subheader("Download cleaned files")
    summary_csv = summary.to_csv(index=False).encode("utf-8")
    lots_csv = lots.to_csv(index=False).encode("utf-8")
    alloc_csv = allocation.to_csv(index=False).encode("utf-8")
    tv_consolidated = tradingview_csv(summary, "consolidated").to_csv(index=False).encode("utf-8")
    tv_lot = tradingview_csv(lots, "lot").to_csv(index=False).encode("utf-8") if not lots.empty else b""

    d1, d2, d3 = st.columns(3)
    d1.download_button("Download holdings summary CSV", summary_csv, "portfolio_summary_cleaned.csv", "text/csv")
    d2.download_button("Download tax lots CSV", lots_csv, "portfolio_lot_level_cleaned.csv", "text/csv")
    d3.download_button("Download allocation CSV", alloc_csv, "portfolio_allocation.csv", "text/csv")

    d4, d5 = st.columns(2)
    d4.download_button("Download TradingView-style consolidated CSV", tv_consolidated, "tradingview_portfolio_import_consolidated.csv", "text/csv")
    if tv_lot:
        d5.download_button("Download TradingView-style lot CSV", tv_lot, "tradingview_portfolio_import_lot_level.csv", "text/csv")

    # One-click zip of all outputs.
    zip_buffer = io.BytesIO()
    import zipfile
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("portfolio_summary_cleaned.csv", summary_csv)
        z.writestr("portfolio_lot_level_cleaned.csv", lots_csv)
        z.writestr("portfolio_allocation.csv", alloc_csv)
        z.writestr("tradingview_portfolio_import_consolidated.csv", tv_consolidated)
        if tv_lot:
            z.writestr("tradingview_portfolio_import_lot_level.csv", tv_lot)
    st.download_button("Download all outputs as ZIP", zip_buffer.getvalue(), "portfolio_analysis_outputs.zip", "application/zip")
