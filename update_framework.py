import json
import logging

from pathlib import Path

from gen_risk import load_prompt, client, read_stock_list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def merge_risk_factors(merged_risks, prior_framework):
    """Merge two sets of risk factors using DeepSeek."""
    merge_prompt = load_prompt("merge_prompt_v2.yaml")

    try:
        prompt = merge_prompt.format(input=merged_risks,
                                     previous_framework=prior_framework)
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system",
                 "content": "You are a financial analyst expert in merging and generalizing risk factors."},
                {"role": "user", "content": prompt}  # Note: The prompt might be quite lengthy.
            ],
            stream=False
        )
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error merging risk factors: {str(e)}")
        return None


def save_framework(framework_content, year):
    """Save the merged framework to a file for specific year."""
    framework_dir = Path(__file__).parent / "llm_output" / "risk_frameworks"
    framework_dir.mkdir(parents=True, exist_ok=True)

    framework_path = framework_dir / f"risk_framework_{year}.json"
    try:
        # Remove markdown code block markers if present
        cleaned_content = framework_content[7:-3] if framework_content.startswith('```') else framework_content
        framework_path.write_text(cleaned_content, encoding='utf-8')
        logger.info(f"Risk framework for {year} saved successfully")

    except Exception as e:
        logger.error(f"Error saving risk framework for {year}: {str(e)}")


def merge_company_risk_factors(year, companies):
    """Merge risk factors with resume capability."""
    merged_risks = []

    framework_path = Path("llm_output") / "risk_frameworks" / f"risk_framework_{year}.json"
    if framework_path.exists():
        logger.info(f"Framework for {year} already exists. Skipping merge.")
        return

    # Concatenate risk_analysis of companies this year
    for company in companies:
        json_path = Path("llm_output") / "inferred_risks" / company / year / "inferred_risks.json"
        try:
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    company_risks = json.load(f)
                    merged_risks.append(company_risks)
                    logger.info(f"Added {company} to merge list")
            else:
                logger.warning(f"Risk analysis file not found for {company} in {year}")

        except Exception as e:
            logger.error(f"Error processing {company}: {str(e)}")
            continue

    # Load previous framework
    prior_year = str(int(year) - 1)
    prior_framework_path = Path("llm_output") / "risk_frameworks" / f"risk_framework_{prior_year}.json"
    with open(prior_framework_path, 'r', encoding='utf-8') as f:
        prior_framework = json.load(f)

    framework = merge_risk_factors(merged_risks, prior_framework)
    save_framework(framework, year)

    return framework


if __name__ == "__main__":
    excel_path = "stock_list.xlsx"
    companies = read_stock_list(excel_path)
    framework_year = "2023"

    merge_company_risk_factors(framework_year, companies)
