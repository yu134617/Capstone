# 对2019的risk factors引入自动验证机制，逻辑校验
import json
import logging
from pathlib import Path

from gen_risk import *

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_leaf(content):
    process_leaf_prompt = """如果leaf factor太多"""
    prompt = process_leaf_prompt.format(company=company_name)

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system",
             "content": "You are a financial analyst expert in analyzing risk factors from SEC filings."},
            {"role": "user",
             "content": prompt + "\n\n" + content}
        ],
        stream=False
    )
    return response.choices[0].message.content


def process_root(content):
    logging.info("Processing with LLM: %s")
    return content

def check_and_process_files(company_name, year):
    riskFactor_dir = Path(__file__).parent / "llm_output" / "risk_factors" / company_name / year

    for file_path in riskFactor_dir.glob('*.json'):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = json.load(file)

            root_factors = len(content)
            leaf_factors = 0
            for value in content.values():
                if isinstance(value, list):
                    leaf_factors += len(value)
                else:
                    leaf_factors += 1

            # 1. 检查leaf factor数量
            if leaf_factors > 50:
                logging.info(
                    f"File {company_name} has more than 50 leaf factors. Processing with LLM.")
                content = process_leaf(content)

            # 2. 检查root factor数量
            if root_factors > 10:
                logging.info(f"File {company_name} has more than 10 root factors. Processing with LLM.")
                content = process_root(content)

            # 将处理后的内容写回文件
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(content, file, ensure_ascii=False, indent=4)

        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON in file {company_name}: {e}")
        except Exception as e:
            logger.error(f"An error occurred while processing file {company_name}: {e}")


if __name__ == "__main__":
    company_name = "ORCL"  # META, CSCO, WFC
    year = "2019"

    check_and_process_files(company_name, year)

