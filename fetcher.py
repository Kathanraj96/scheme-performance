import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

AMFI_BASE_URL = "https://www.amfiindia.com/gateway/pollingsebi/api/amfi"

DEFAULT_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Origin": "https://www.amfiindia.com",
    "Referer": "https://www.amfiindia.com/polling/amfi/fund-performance",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
}

def make_post_request(endpoint: str, json_data=None, text_content=False, retries=3, backoff_factor=2):
    """
    Sends a POST request to AMFI API with retries and exponential backoff.
    """
    url = f"{AMFI_BASE_URL}/{endpoint}"
    headers = DEFAULT_HEADERS.copy()
    
    if text_content:
        headers["Content-Type"] = "text/plain"
        headers["Content-Length"] = "0"
        data = None
    else:
        headers["Content-Type"] = "application/json"
        data = json_data
        
    delay = 1.0
    for attempt in range(1, retries + 1):
        try:
            logger.debug(f"POST to {url} (Attempt {attempt}/{retries}) with data={json_data}")
            if text_content:
                # Content-Length 0 POST
                response = requests.post(url, headers=headers, timeout=15)
            else:
                response = requests.post(url, headers=headers, json=data, timeout=15)
                
            response.raise_for_status()
            res_json = response.json()
            
            # AMFI API standard response contains validationStatus
            if res_json.get("validationStatus") != "SUCCESS":
                raise ValueError(f"AMFI API error: {res_json.get('errorMsgs', [])}")
                
            return res_json.get("data")
            
        except (requests.RequestException, ValueError, KeyError) as e:
            logger.warning(f"Attempt {attempt} failed for {endpoint}: {e}")
            if attempt == retries:
                logger.error(f"All {retries} attempts failed for {endpoint}")
                raise e
            time.sleep(delay)
            delay *= backoff_factor

def fetch_filters():
    """
    Fetches available maturity types, investment categories, and mutual funds.
    """
    return make_post_request("fundperformancefilters", text_content=True)

def fetch_subcategories(category_id: int):
    """
    Fetches subcategories for a given investment category.
    """
    return make_post_request("getsubcategory", json_data={"category": category_id})

def is_holiday(report_date: str) -> bool:
    """
    Checks if a report_date (format DD-Mmm-YYYY) is an AMFI/SEBI reporting holiday.
    """
    return make_post_request("isHoliday", json_data={"reportDate": report_date})

def fetch_performance(maturity_type: int, category: int, sub_category: int, report_date: str):
    """
    Fetches performance metrics for a specific maturity/category/subcategory combination.
    """
    payload = {
        "maturityType": maturity_type,
        "category": category,
        "subCategory": sub_category,
        "mfid": 0,  # 0 fetches all mutual funds/AMCs
        "reportDate": report_date
    }
    return make_post_request("fundperformance", json_data=payload)
