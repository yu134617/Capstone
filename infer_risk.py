import json
import time
import logging

from pathlib import Path

from gen_risk import load_prompt, client, read_stock_list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def read_risk_framework(year):
    framework_path = Path("llm_output") / "risk_frameworks" / f"risk_framework_{year}.json"

    if not framework_path.exists():
        logger.error(f"Risk framework for {year} not found. Please generate it first.")
        return None

    with open(framework_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def infer_company_risks(company, risk_framework, risk_item):
    """Infer risks for a specific company using the framework and identify new risks."""
    inference_prompt = load_prompt("inference_prompt.yaml")
    prompt = inference_prompt.format(
        company=company,
        description=risk_item,
        framework=json.dumps(risk_framework, indent=2)
    )

    try:
        response = client.chat.completions.create(
            model="deepseek-reasoner",
            messages=[
                {"role": "system", "content": """You are a risk analysis expert who specializes in inferring 
                                              company-specific risks and identifying new risk patterns. 
                                              Always return valid JSON without any additional text or formatting."""},
                {"role": "user", "content": prompt}
            ],
            stream=False
        )

        # Clean and validate the response
        content = response.choices[0].message.content.strip()
        if content.startswith('```json'):
            content = content[7:]
        if content.endswith('```'):
            content = content[:-3]
        content = content.strip()

        # Validate JSON before returning
        json.loads(content)  # Raise JSONDecodeError if invalid
        return content

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response for {company}: {str(e)}")
        logger.error(f"Raw response: {content}")
        return None
    except Exception as e:
        logger.error(f"Error in risk inference for {company}. Error type: {type(e).__name__}, Message: {str(e)}")
        return None


def save_inferred_risks(company, year, inferred_risks):
    inferFactor_dir = Path("llm_output") / "inferred_risks" / company / year
    inferFactor_dir.mkdir(parents=True, exist_ok=True)

    with open(inferFactor_dir / "inferred_risks.json", 'w', encoding='utf-8') as f:
        # Remove the markdown code block markers if present
        cleaned_risks = inferred_risks.strip('`').replace('json\n', '')
        f.write(cleaned_risks)
    logger.info(f"Successfully saved inferred risks for {company}")


def infer_risk(framework_year, analysis_year, companies):
    """Infer risks with resume capability."""
    logger.info(f"Processing analysis year: {analysis_year}")

    # Get already inferred companies for this year
    inferred = set()
    inferBase_path = Path("llm_output/inferred_risks")
    if inferBase_path.exists():
        for company_dir in inferBase_path.iterdir():
            if (company_dir / analysis_year / "inferred_risks.json").exists():
                inferred.add(company_dir.name)
    if inferred:
        logger.info(f"Resuming inference for {analysis_year}. Already processed: {len(inferred)} companies")

    # Infer risk for remaining companies this year
    remaining = [c for c in companies if c not in inferred]
    risk_framework = read_risk_framework(framework_year)
    for company in remaining:
        risk_item_path = Path("sec-edgar-filings") / company / analysis_year / "risk_item.html"
        try:
            if not risk_item_path.exists():
                logger.warning(f"Risk analysis not found for {company} in {analysis_year}")
                continue
            with open(risk_item_path, 'r', encoding='utf-8') as f:
                risk_item = f.read()

            response = infer_company_risks(company, risk_framework, risk_item)  # Infer risks

            # Parse response
            try:
                company_risks = json.loads(response)
                save_inferred_risks(company, analysis_year, json.dumps(company_risks, indent=2))

            except json.JSONDecodeError as e:
                logger.error(f"Error parsing response for {company} in {analysis_year}: {str(e)}")
                continue

        except Exception as e:
            logger.error(f"Error processing {company} in {analysis_year}: {str(e)}")
            continue
        time.sleep(1)  # Rate limiting


if __name__ == "__main__":
    excel_path = "stock_list.xlsx"
    companies = read_stock_list(excel_path)
    framework_year = "2021"
    analysis_year = "2023"

    infer_risk(framework_year, analysis_year, companies)
