import os
import csv
import time
import logging
from datetime import datetime, timedelta
import pandas as pd
from .fetcher import fetch_filters, fetch_subcategories, is_holiday, fetch_performance

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def find_latest_business_day(start_date_str: str) -> str:
    """
    Checks if start_date_str is a holiday, and loops backward day-by-day until a business day is found.
    """
    current_date = datetime.strptime(start_date_str, "%d-%b-%Y")
    max_lookback = 10
    
    for i in range(max_lookback):
        date_str = current_date.strftime("%d-%b-%Y")
        logger.info(f"Checking holiday status for: {date_str}...")
        holiday = is_holiday(date_str)
        
        if not holiday:
            logger.info(f"Selected business day: {date_str}")
            return date_str
            
        logger.info(f"{date_str} is a reporting holiday. Checking previous day...")
        current_date -= timedelta(days=1)
        
    raise RuntimeError(f"Could not find any non-holiday date within the last {max_lookback} days starting from {start_date_str}.")

def run_download(output_path: str = None):
    if not output_path:
        # Default save path
        workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        output_path = os.path.join(workspace_dir, "data", "performance_data.csv")
        downloads_dir = os.path.join(workspace_dir, "downloads")
    else:
        downloads_dir = os.path.dirname(output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    os.makedirs(downloads_dir, exist_ok=True)

    logger.info("Fetching filters from AMFI...")
    filters = fetch_filters()
    if not filters:
        raise ValueError("Could not fetch filters from AMFI.")

    maturity_types = filters.get("maturityTypeList", [])
    categories = filters.get("investmentTypeList", [])
    initial_report_date = filters.get("reportDate")

    logger.info(f"Initial report date from filters: {initial_report_date}")
    
    # Verify and adjust for holidays
    report_date = find_latest_business_day(initial_report_date)
    logger.info(f"Fetching scheme performance metrics for date: {report_date}")

    all_records = []
    
    # Loop over all combinations of Maturity Type -> Category -> Subcategory
    for mat_type in maturity_types:
        mat_id = mat_type["id"]
        mat_name = mat_type["name"]
        
        for cat in categories:
            cat_id = cat["id"]
            cat_name = cat["name"]
            
            logger.info(f"Fetching subcategories for Category: {cat_name} (ID: {cat_id})...")
            subcategories = fetch_subcategories(cat_id)
            if not subcategories:
                logger.warning(f"No subcategories found for Category: {cat_name}")
                continue
                
            for sub_cat in subcategories:
                sub_id = sub_cat["id"]
                sub_name = sub_cat["name"]
                
                logger.info(f"Fetching performance for: {mat_name} - {cat_name} - {sub_name}...")
                
                try:
                    schemes_data = fetch_performance(
                        maturity_type=mat_id,
                        category=cat_id,
                        sub_category=sub_id,
                        report_date=report_date
                    )
                    
                    if schemes_data:
                        count = len(schemes_data)
                        logger.info(f"Successfully fetched {count} schemes.")
                        
                        # Add metadata and append to master records
                        for scheme in schemes_data:
                            scheme["Maturity_Type"] = mat_name
                            scheme["Category"] = cat_name
                            scheme["Subcategory"] = sub_name
                            scheme["Report_Date"] = report_date
                            all_records.append(scheme)
                    else:
                        logger.info("No schemes found for this combination.")
                        
                except Exception as e:
                    logger.error(f"Error fetching performance for {mat_name} - {cat_name} - {sub_name}: {e}")
                
                # Polite delay between calls
                time.sleep(0.1)

    if not all_records:
        logger.warning("No performance records fetched.")
        return

    # Convert to DataFrame to flatten and structure columns
    df = pd.DataFrame(all_records)
    
    # Reorder columns to place metadata at the beginning
    meta_cols = ["Maturity_Type", "Category", "Subcategory", "Report_Date"]
    other_cols = [col for col in df.columns if col not in meta_cols]
    df = df[meta_cols + other_cols]

    # Save to master output file
    df.to_csv(output_path, index=False)
    logger.info(f"Saved consolidated performance dataset to: {output_path} ({len(df)} records)")

    # Also save a date-specific backup in the downloads directory
    backup_filename = f"performance_data_{report_date}.csv"
    backup_path = os.path.join(downloads_dir, backup_filename)
    df.to_csv(backup_path, index=False)
    logger.info(f"Saved backup dataset to: {backup_path}")

if __name__ == "__main__":
    run_download()
