# Broker Portfolio Analyzer

A Streamlit app that turns a broker positions Excel export into an interactive portfolio analysis dashboard.

## What it does

- Upload `.xls`, `.xlsx`, or `.csv` broker positions files
- Parse Wells Fargo Advisors-style positions exports
- Avoid double-counting summary rows and tax-lot rows
- Build an interactive heat map
- Show allocation, P&L, daily change, income, concentration, and tax-lot tables
- Export cleaned CSVs and TradingView-style CSVs

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy safely

Do **not** commit your broker positions file to GitHub. This app intentionally starts with no default portfolio data. Upload your file only inside the app UI.

Suggested `.gitignore`:

```gitignore
*.xls
*.xlsx
*.csv
portfolio_analysis_outputs.zip
__pycache__/
.streamlit/secrets.toml
```

## Current parser

The parser is optimized for Wells Fargo Advisors position exports with sections such as Stocks, ETFs, Mutual Funds, Cash, Fixed Income, and Total Portfolio.
