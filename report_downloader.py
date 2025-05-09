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
API_KEY = 'fc25bec1ad4dba775cd8d0934e3ab93f03241671d4b1b57e6004856f6841d8a5'  # SEC API KEY
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

    max_retries = 10
    retries = 0
    while retries < max_retries:
        try:
            item_1_a_html = extractorApi.get_section(url, '1A', 'html')
            return item_1_a_html

        except ConnectionError as e:
            retries += 1
            print(f"Connection error: {e}. Retrying ({retries}/{max_retries})...")
            time.sleep(1)
    # If maximum retry attempts are reached, raise an exception
    raise ConnectionError(f"Failed to retrieve data after {max_retries} attempts.")


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
        base_dir = f"sec-edgar-filings/{ticker}/{year[:4]}"
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
