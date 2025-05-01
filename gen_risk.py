import time
import logging

import yaml
import pandas as pd
from pathlib import Path
from openai import OpenAI


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DeepSeek_API_KEY = "sk-eda818fcb729437db63df02ddfe494a1"
client = OpenAI(
    api_key=DeepSeek_API_KEY,
    base_url="https://api.deepseek.com")
max_retries = 3
retry_delay = 5  # seconds


def read_stock_list(excel_path):
    df = pd.read_excel(excel_path)
    # Assuming the column containing tickers is named 'Ticker'
    return df['Ticker'].tolist()


def load_prompt(filename):
    prompt_dir = Path(__file__).parent / "prompt"
    prompt_path = prompt_dir / filename

    with open(prompt_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        return data["template"]


def analyze_risk_factors(company_name, filing_content):
    """Analyze risk factors using DeepSeek with retry logic."""
    base_prompt = load_prompt("base_prompt.yaml")
    for attempt in range(max_retries):
        try:
            prompt = base_prompt.format(company=company_name)
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {"role": "system",
                     "content": "You are a financial analyst expert in analyzing risk factors from SEC filings."},
                    {"role": "user", "content": prompt + "\n\n" + filing_content}
                ],
                stream=False
            )
            return response.choices[0].message.content

        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Retry {attempt + 1} for {company_name}: {str(e)}")
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"Error analyzing risk factors for {company_name}: {str(e)}")
                return None


def save_analysis(company_name, year, analysis):
    """Save the analysis to the llm_output directory."""
    riskFactor_dir = Path(__file__).parent / "llm_output" / "risk_factors" / company_name / year
    riskFactor_dir.mkdir(parents=True, exist_ok=True)

    riskFactor_file = riskFactor_dir / "risk_analysis.json"
    try:
        with open(riskFactor_file, 'w', encoding='utf-8') as f:
            f.write(analysis[7:-3])  # ```json somewords ```
        logger.info(f"Analysis saved for {company_name} ({year})")

    except Exception as e:
        logger.error(f"Error saving analysis for {company_name}: {str(e)}")


def process_companies(companies, year):
    """Process individual companies with resume capability."""
    # Get already processed companies
    processed = set()
    riskBase_dir = Path("llm_output/risk_factors")
    if riskBase_dir.exists():
        for company_dir in riskBase_dir.iterdir():
            if (company_dir / year / "risk_analysis.json").exists():
                processed.add(company_dir.name)

    if processed:
        logger.info(f"Resuming processing. Already processed: {len(processed)} companies")

    # Process remaining companies
    remaining = [c for c in companies if c not in processed]
    for company in remaining:
        filing_dir = Path(__file__).parent / "sec-edgar-filings"
        filing_path = filing_dir / company / year / "risk_item.html"
        with open(filing_path, 'r', encoding='utf-8') as file:
            filing_content = file.read()

        analysis = analyze_risk_factors(company, filing_content)
        save_analysis(company, year, analysis)
        logger.info(f"Successfully processed {company}")
        time.sleep(1)  # Rate limiting


if __name__ == "__main__":
    excel_file_path = "stock_list.xlsx"
    companies = read_stock_list(excel_file_path)
    base_year = "2019"

    process_companies(companies, base_year)
