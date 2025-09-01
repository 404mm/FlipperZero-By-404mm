"""
Ticketmaster & Podio Automation Script
=====================================
Prerequisites:
    pip install selenium python-dotenv pandas

Environment Variables (.env file in the same directory):
    TICKETMASTER_USER=your_email
    TICKETMASTER_PASS=your_password
    PODIO_USER=your_podio_user
    PODIO_PASS=your_podio_password

Overview:
    1. Ask the user for a venue name/code.
    2. Log into Ticketmaster and search for the event matching that venue.
    3. Extract relevant statistics and download the event PDF.
    4. Log into Podio, locate the corresponding event item and fill out its form with the extracted data, then upload the PDF.

NOTE:
    - **Selectors & dynamic URLs vary between accounts.** When the script cannot find an element, it will ASK you via input() for the correct CSS/XPath selector and will remember it for the session.
    - A new log file is generated on every run under logs/YYYY-MM-DD_HH-MM-SS.log.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

SESSION_SELECTORS: Dict[str, str] = {}


def _ask_selector(question: str) -> str:
    """Prompt the user for a selector and cache it for the session."""
    if question in SESSION_SELECTORS:
        return SESSION_SELECTORS[question]
    selector = input(f"[INPUT REQUIRED] {question} → ")
    SESSION_SELECTORS[question] = selector
    return selector


def setup_logging() -> logging.Logger:
    """Create timestamped log file and return logger instance."""
    logs_dir = Path(__file__).with_suffix("").parent / "logs"
    logs_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = logs_dir / f"automation_{ts}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    logging.info("Log initiated: %s", log_file)
    return logging.getLogger(__name__)


def init_driver(download_dir: Path) -> webdriver.Chrome:
    """Initialize Chrome driver with desired preferences (non-headless)."""
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": str(download_dir.resolve()),
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    })
    # The following line keeps the browser visible.
    # To run headless, uncomment the next line.
    # chrome_options.add_argument("--headless=new")

    service = ChromeService()
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    return driver

# ---------------------------------------------------------------------------
# Ticketmaster actions
# ---------------------------------------------------------------------------

def login_ticketmaster(driver: webdriver.Chrome, user: str, password: str):
    """Login to Ticketmaster using provided credentials."""
    logging.info("Logging into Ticketmaster ...")
    driver.get("https://ticketmaster.com.mx")  # Adjust URL if needed

    # Ask for login button selector if not found
    try:
        login_btn_selector = _ask_selector("CSS selector for the Ticketmaster login button")
        driver.find_element(By.CSS_SELECTOR, login_btn_selector).click()
    except NoSuchElementException:
        logging.error("Login button not found – update selector.")
        sys.exit(1)

    # Wait for login form
    user_selector = _ask_selector("CSS selector for Ticketmaster user/email input")
    pass_selector = _ask_selector("CSS selector for Ticketmaster password input")
    submit_selector = _ask_selector("CSS selector for Ticketmaster submit/login button")

    WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, user_selector)))

    driver.find_element(By.CSS_SELECTOR, user_selector).send_keys(user)
    driver.find_element(By.CSS_SELECTOR, pass_selector).send_keys(password)
    driver.find_element(By.CSS_SELECTOR, submit_selector).click()

    logging.info("Ticketmaster login submitted.")


def buscar_evento(driver: webdriver.Chrome, recinto: str) -> bool:
    """Search for an event by venue code/name. Returns True if found."""
    logging.info("Searching event for venue: %s", recinto)

    search_selector = _ask_selector("CSS selector for Ticketmaster search input")
    WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, search_selector)))
    search_box = driver.find_element(By.CSS_SELECTOR, search_selector)
    search_box.clear()
    search_box.send_keys(recinto + "\n")  # Press Enter

    # TODO: refine logic to identify correct event row/card from results
    event_link_selector = _ask_selector("CSS selector for event link in search results")

    try:
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, event_link_selector))).click()
        logging.info("Event page opened.")
        return True
    except TimeoutException:
        logging.warning("Event not found for venue %s", recinto)
        return False


def extraer_datos(driver: webdriver.Chrome) -> Dict[str, int]:
    """Extract selling and validation statistics from the event dashboard."""
    logging.info("Extracting event statistics ...")

    sold_selector = _ask_selector("CSS selector for total tickets sold")
    validated_selector = _ask_selector("CSS selector for validated tickets")

    try:
        sold = driver.find_element(By.CSS_SELECTOR, sold_selector).text
        validated = driver.find_element(By.CSS_SELECTOR, validated_selector).text
        data = {
            "tickets_sold": int(sold.replace(",", "").strip()),
            "tickets_validated": int(validated.replace(",", "").strip()),
        }
        logging.info("Data extracted: %s", data)
        return data
    except Exception as exc:
        logging.error("Failed to extract data: %s", exc)
        raise


def descargar_pdf(driver: webdriver.Chrome, recinto: str, download_dir: Path) -> Path:
    """Download event PDF and return its saved path."""
    logging.info("Initiating PDF download …")

    pdf_btn_selector = _ask_selector("CSS selector for PDF download button")
    try:
        driver.find_element(By.CSS_SELECTOR, pdf_btn_selector).click()
    except NoSuchElementException:
        logging.error("PDF download button not found.")
        raise

    # Wait for file to appear in download directory
    logging.info("Waiting for PDF to download …")
    WebDriverWait(driver, 60).until(lambda d: any(f.suffix == ".pdf" for f in download_dir.glob("*.pdf")))

    pdf_path = max(download_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime)
    new_name = f"{recinto}_{datetime.now().strftime('%Y-%m-%d')}.pdf"
    new_path = download_dir / new_name
    pdf_path.rename(new_path)
    logging.info("PDF downloaded: %s", new_path)
    return new_path

# ---------------------------------------------------------------------------
# Podio actions
# ---------------------------------------------------------------------------

def login_podio(driver: webdriver.Chrome, user: str, password: str):
    logging.info("Logging into Podio …")
    driver.get("https://podio.com/login")

    user_selector = _ask_selector("CSS selector for Podio user/email input")
    pass_selector = _ask_selector("CSS selector for Podio password input")
    submit_selector = _ask_selector("CSS selector for Podio login button")

    WebDriverWait(driver, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, user_selector)))

    driver.find_element(By.CSS_SELECTOR, user_selector).send_keys(user)
    driver.find_element(By.CSS_SELECTOR, pass_selector).send_keys(password)
    driver.find_element(By.CSS_SELECTOR, submit_selector).click()

    logging.info("Podio login submitted.")


def rellenar_formulario(driver: webdriver.Chrome, data: Dict[str, int]):
    """Fill Podio form fields with extracted data."""
    logging.info("Filling Podio form …")

    sold_field_selector = _ask_selector("CSS selector for Podio 'tickets sold' field")
    validated_field_selector = _ask_selector("CSS selector for Podio 'tickets validated' field")

    driver.find_element(By.CSS_SELECTOR, sold_field_selector).send_keys(str(data["tickets_sold"]))
    driver.find_element(By.CSS_SELECTOR, validated_field_selector).send_keys(str(data["tickets_validated"]))


def subir_pdf(driver: webdriver.Chrome, pdf_path: Path):
    """Upload PDF to Podio form and submit."""
    logging.info("Uploading PDF to Podio …")

    upload_input_selector = _ask_selector("CSS selector for Podio file upload input[type='file']")
    submit_btn_selector = _ask_selector("CSS selector for Podio form submit button")

    file_input = driver.find_element(By.CSS_SELECTOR, upload_input_selector)
    file_input.send_keys(str(pdf_path.resolve()))

    # Wait briefly for upload to finish (could be improved by checking upload indicator)
    WebDriverWait(driver, 30).until(lambda d: "uploaded" in file_input.get_attribute("class"))

    driver.find_element(By.CSS_SELECTOR, submit_btn_selector).click()
    logging.info("Podio form submitted.")

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def save_data(recinto: str, data: Dict[str, int]):
    """Save statistics to both JSON and CSV files."""
    out_dir = Path.cwd() / "outputs"
    out_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    json_path = out_dir / f"{recinto}_{ts}.json"
    csv_path = out_dir / f"{recinto}_{ts}.csv"

    with json_path.open("w", encoding="utf-8") as jf:
        json.dump(data, jf, indent=2, ensure_ascii=False)
    pd.DataFrame([data]).to_csv(csv_path, index=False)

    logging.info("Data saved as %s and %s", json_path, csv_path)

# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def main():
    load_dotenv()
    logger = setup_logging()

    recinto = input("Ingrese nombre/código exacto del recinto: ").strip()
    if not recinto:
        logger.error("Recinto no proporcionado. Abortando.")
        return

    ticket_user = os.getenv("TICKETMASTER_USER")
    ticket_pass = os.getenv("TICKETMASTER_PASS")
    podio_user = os.getenv("PODIO_USER")
    podio_pass = os.getenv("PODIO_PASS")

    if not all([ticket_user, ticket_pass, podio_user, podio_pass]):
        logger.error("Credenciales faltantes en .env. Abortando.")
        return

    download_dir = Path.cwd() / "downloads"
    download_dir.mkdir(exist_ok=True)

    driver = init_driver(download_dir)

    try:
        login_ticketmaster(driver, ticket_user, ticket_pass)
        found = buscar_evento(driver, recinto)
        if not found:
            logger.warning("No se encontró el evento. Finalizando script.")
            return

        stats = extraer_datos(driver)
        pdf_path = descargar_pdf(driver, recinto, download_dir)
        save_data(recinto, stats)

        login_podio(driver, podio_user, podio_pass)
        # TODO: navigate to relevant Podio item before filling form – may require additional selectors
        rellenar_formulario(driver, stats)
        subir_pdf(driver, pdf_path)

        logger.info("Proceso completado exitosamente.")
    except Exception as exc:
        logger.exception("Se produjo un error: %s", exc)
    finally:
        input("Presione ENTER para cerrar el navegador…")
        driver.quit()


if __name__ == "__main__":
    main()