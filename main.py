from gen_risk import read_stock_list, process_companies
from build_framework import merge_company_risk_factors as build_merge
from infer_risk import infer_risk
from update_framework import merge_company_risk_factors as update_merge


def main():
    start_year = "2019"  # Start year
    end_year = "2023"    # End year

    excel_file_path = "stock_list.xlsx"
    companies = read_stock_list(excel_file_path)

    process_companies(companies, start_year)  # Initial gen_risk
    build_merge(start_year, companies)        # Initial build_framework

    for year in range(int(start_year), int(end_year)):
        year_str = str(year)
        next_year_str = str(year + 1)
        infer_risk(year_str, next_year_str, companies)  # Infer risk for each company
        update_merge(next_year_str, companies)          # Update risk framework


if __name__ == "__main__":
    main()
