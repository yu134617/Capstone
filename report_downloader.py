import os
import time

import pandas as pd
from edgar import Company
from edgar import set_identity
from sec_downloader import Downloader
from sec_downloader.types import CompanyAndAccessionNumber
from sec_api import ExtractorApi


set_identity("email@example.com")
dl = Downloader("MyCompanyName", "email@example.com")
API_KEY = '4a55aa1e96941ed7292019011b2b53f43b8766be167fcdb785ab748b32293eb1'  # SEC API KEY
extractorApi = ExtractorApi(API_KEY)


def get_risk_item(ticker, year):
    company = Company(ticker)
    filings = company.get_filings(filing_date=year, form="10-K")
    # Get the first filing for that year
    filing = filings[0]
    cik = str(filing.cik)
    accession_no = filing.accession_number

    metadatas = dl.get_filing_metadatas(CompanyAndAccessionNumber(ticker_or_cik=cik, accession_number=accession_no))
    url = metadatas[0].primary_doc_url
    item_1_a_html = extractorApi.get_section(url, '1A', 'html')

    return item_1_a_html


def save_risk_item(risk_item, ticker, year):
    base_dir = f"sec-edgar-filings/{ticker}/{year[:4]}"
    os.makedirs(base_dir, exist_ok=True)

    filename = f"{base_dir}/risk_item.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(risk_item)


def process_stock_list(excel_path, year):
    df = pd.read_excel(excel_path)
    # Assuming the column containing tickers is named 'Ticker'
    tickers = df['Ticker'].tolist()

    for ticker in tickers:
        base_dir = f"sec-edgar-filings/{year[:4]}/{ticker}"
        filename = f"{base_dir}/risk_item.html"

        # Check if the file already exists
        if os.path.exists(filename):
            print(f"File already exists for {ticker} in year {year[:4]}, skipping...")
            continue

        print(f"Processing {ticker} for year {year}...")
        risk_item = get_risk_item(ticker, year)
        save_risk_item(risk_item, ticker, year)
        print(f"Completed processing {ticker}")
        time.sleep(1)


if __name__ == "__main__":
    os.makedirs("sec-edgar-filings", exist_ok=True)
    excel_path = "stock_list.xlsx"
    years = ["2019-01-01:2019-12-31",
             "2020-01-01:2020-12-31",
             "2021-01-01:2021-12-31",
             "2022-01-01:2022-12-31",
             "2023-01-01:2023-12-31"]
    for year in years:
        process_stock_list(excel_path, year)
