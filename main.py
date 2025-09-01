import os
import re
import sys
import json
import time
import glob
import shutil
import getpass
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd
from dotenv import load_dotenv

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.common.exceptions import TimeoutException, NoSuchElementException


# ------------------------------ Utilidades generales ------------------------------

def ensure_directories() -> Dict[str, Path]:
    base = Path.cwd()
    logs_dir = base / "logs"
    downloads_dir = base / "downloads"
    data_dir = base / "data"
    logs_dir.mkdir(exist_ok=True)
    downloads_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)
    return {"logs": logs_dir, "downloads": downloads_dir, "data": data_dir}


def setup_logging(logs_dir: Path) -> logging.Logger:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = logs_dir / f"run_{run_id}.log"
    logger = logging.getLogger("tm_podio_automation")
    logger.setLevel(logging.INFO)

    # Stream handler (console)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh_fmt = logging.Formatter("[%(asctime)s] %(levelname)s: %(message)s")
    sh.setFormatter(sh_fmt)
    logger.addHandler(sh)

    # File handler
    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(sh_fmt)
    logger.addHandler(fh)

    logger.info(f"Log de ejecución: {log_path}")
    return logger


def get_env_or_prompt(key: str, prompt: str, secret: bool = False) -> str:
    val = os.getenv(key)
    if val:
        return val
    if secret:
        return getpass.getpass(prompt + ": ")
    return input(prompt + ": ")


def prompt_selector(hint: str) -> str:
    return input(f"Introduce el selector CSS para {hint}: ")


def parse_int_from_text(text: str) -> Optional[int]:
    if text is None:
        return None
    # Extrae el primer número entero del texto
    match = re.search(r"(\d[\d\.,]*)", text)
    if not match:
        return None
    number_str = match.group(1).replace(".", "").replace(",", "")
    try:
        return int(number_str)
    except ValueError:
        return None


def wait_for_download(download_dir: Path, logger: logging.Logger, timeout_sec: int = 120) -> Optional[Path]:
    logger.info("Esperando a que termine la descarga del PDF...")
    end_time = time.time() + timeout_sec
    already = set(download_dir.glob("*"))
    while time.time() < end_time:
        time.sleep(1)
        # Evita archivos temporales .crdownload / .part
        pdfs = [p for p in download_dir.glob("*.pdf") if p not in already]
        partials = list(download_dir.glob("*.crdownload")) + list(download_dir.glob("*.part"))
        if pdfs and not partials:
            logger.info(f"Descarga detectada: {pdfs[0].name}")
            return pdfs[0]
    return None


def export_data(data_dir: Path, recinto: str, event_date: str, sold: Optional[int], validated: Optional[int], logger: logging.Logger) -> Tuple[Path, Path]:
    safe_recinto = re.sub(r"[^A-Za-z0-9_-]+", "_", recinto.strip())
    safe_date = re.sub(r"[^A-Za-z0-9_-]+", "_", event_date.strip()) if event_date else datetime.now().strftime("%Y%m%d")
    base_name = f"{safe_recinto}_{safe_date}"
    json_path = data_dir / f"{base_name}.json"
    csv_path = data_dir / f"{base_name}.csv"

    payload = {
        "recinto": recinto,
        "fecha_evento": event_date,
        "entradas_vendidas": sold,
        "entradas_validadas": validated,
        "timestamp_extraccion": datetime.now().isoformat(),
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info(f"JSON guardado en {json_path}")

    df = pd.DataFrame([payload])
    df.to_csv(csv_path, index=False)
    logger.info(f"CSV guardado en {csv_path}")
    return json_path, csv_path


def rename_pdf(downloaded_pdf: Path, downloads_dir: Path, recinto: str, event_date: str, logger: logging.Logger) -> Path:
    safe_recinto = re.sub(r"[^A-Za-z0-9_-]+", "_", recinto.strip())
    safe_date = re.sub(r"[^A-Za-z0-9_-]+", "_", event_date.strip()) if event_date else datetime.now().strftime("%Y%m%d")
    target = downloads_dir / f"{safe_recinto}_{safe_date}.pdf"
    try:
        shutil.move(str(downloaded_pdf), str(target))
        logger.info(f"PDF renombrado a {target}")
        return target
    except Exception as exc:
        logger.error(f"No se pudo renombrar el PDF: {exc}")
        return downloaded_pdf


# ------------------------------ WebDriver ------------------------------

def init_driver(download_dir: Path, logger: logging.Logger) -> webdriver.Remote:
    browser = input("¿Qué navegador quieres usar? [chrome/firefox] (por defecto chrome): ") or "chrome"
    browser = browser.strip().lower()

    if browser == "firefox":
        ff_options = FirefoxOptions()
        ff_options.headless = False
        profile = webdriver.FirefoxProfile()
        profile.set_preference("browser.download.folderList", 2)
        profile.set_preference("browser.download.dir", str(download_dir))
        profile.set_preference("browser.helperApps.neverAsk.saveToDisk", "application/pdf,application/octet-stream")
        # Intenta inicializar con driver en PATH
        try:
            logger.info("Iniciando Firefox...")
            return webdriver.Firefox(service=FirefoxService(), options=ff_options, firefox_profile=profile)
        except Exception as exc:
            logger.warning(f"No se pudo iniciar Firefox con geckodriver del PATH: {exc}")
            driver_path = input("Ruta absoluta a geckodriver (o Enter para cancelar): ")
            if not driver_path:
                raise RuntimeError("No se pudo iniciar Firefox: falta geckodriver.")
            return webdriver.Firefox(service=FirefoxService(executable_path=driver_path), options=ff_options, firefox_profile=profile)

    # Por defecto: Chrome
    chrome_options = ChromeOptions()
    chrome_options.add_experimental_option("prefs", {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "plugins.always_open_pdf_externally": True,
    })
    chrome_options.add_argument("--start-maximized")
    # Intenta con chromedriver del PATH
    try:
        logger.info("Iniciando Chrome...")
        return webdriver.Chrome(service=ChromeService(), options=chrome_options)
    except Exception as exc:
        logger.warning(f"No se pudo iniciar Chrome con chromedriver del PATH: {exc}")
        driver_path = input("Ruta absoluta a chromedriver (o Enter para cancelar): ")
        if not driver_path:
            raise RuntimeError("No se pudo iniciar Chrome: falta chromedriver.")
        return webdriver.Chrome(service=ChromeService(executable_path=driver_path), options=chrome_options)


# ------------------------------ Ticketmaster ------------------------------

def login_ticketmaster(driver: webdriver.Remote, logger: logging.Logger) -> None:
    load_dotenv()
    user = get_env_or_prompt("TICKETMASTER_USER", "Usuario de Ticketmaster")
    password = get_env_or_prompt("TICKETMASTER_PASS", "Contraseña de Ticketmaster", secret=True)
    login_url = input("URL de login de Ticketmaster (incluye https://): ")

    driver.get(login_url)
    logger.info("Abriendo página de login de Ticketmaster...")

    # Selectores solicitados al usuario si no se conocen
    user_sel = prompt_selector("(Ticketmaster) campo de usuario")
    pass_sel = prompt_selector("(Ticketmaster) campo de contraseña")
    submit_sel = prompt_selector("(Ticketmaster) botón de login")

    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, user_sel)))
    driver.find_element(By.CSS_SELECTOR, user_sel).clear()
    driver.find_element(By.CSS_SELECTOR, user_sel).send_keys(user)

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, pass_sel)))
    driver.find_element(By.CSS_SELECTOR, pass_sel).clear()
    driver.find_element(By.CSS_SELECTOR, pass_sel).send_keys(password)

    driver.find_element(By.CSS_SELECTOR, submit_sel).click()
    logger.info("Login en Ticketmaster enviado. Si hay 2FA, complétalo manualmente.")

    # Espera opcional a que se complete el login
    time.sleep(5)


def buscar_evento(driver: webdriver.Remote, recinto: str, logger: logging.Logger) -> bool:
    logger.info(f"Buscando evento por recinto/código: {recinto}")
    search_url = input("URL de búsqueda/listado de eventos en Ticketmaster: ")
    driver.get(search_url)

    search_input_sel = prompt_selector("(Ticketmaster) campo de búsqueda por recinto")
    result_link_sel = prompt_selector("(Ticketmaster) enlace del evento en resultados")

    wait = WebDriverWait(driver, 30)
    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, search_input_sel)))
        box = driver.find_element(By.CSS_SELECTOR, search_input_sel)
        box.clear()
        box.send_keys(recinto)
        box.submit()
        time.sleep(3)

        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, result_link_sel)))
        driver.find_element(By.CSS_SELECTOR, result_link_sel).click()
        logger.info("Evento abierto. Accediendo al panel/detalle...")
        return True
    except TimeoutException:
        logger.warning("No se encontró el evento en Ticketmaster.")
        print("[AVISO] No se encontró el evento en Ticketmaster.")
        return False


def extraer_datos(driver: webdriver.Remote, logger: logging.Logger) -> Tuple[Optional[int], Optional[int], str]:
    logger.info("Extrayendo datos del panel del evento...")
    sold_sel = prompt_selector("(Ticketmaster) métrica 'entradas vendidas totales'")
    validated_sel = prompt_selector("(Ticketmaster) métrica 'entradas validadas/entrada real'")
    date_sel = input("Selector CSS de la fecha del evento (o deja vacío para introducirla manualmente): ")

    wait = WebDriverWait(driver, 30)
    sold = validated = None
    event_date = ""

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, sold_sel)))
        sold_text = driver.find_element(By.CSS_SELECTOR, sold_sel).text
        sold = parse_int_from_text(sold_text)
    except Exception as exc:
        logger.warning(f"No se pudo extraer 'entradas vendidas': {exc}")

    try:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, validated_sel)))
        validated_text = driver.find_element(By.CSS_SELECTOR, validated_sel).text
        validated = parse_int_from_text(validated_text)
    except Exception as exc:
        logger.warning(f"No se pudo extraer 'entradas validadas': {exc}")

    if date_sel:
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, date_sel)))
            event_date = driver.find_element(By.CSS_SELECTOR, date_sel).text.strip()
        except Exception:
            logger.warning("No se pudo extraer la fecha del evento por selector; se solicitará manualmente.")

    if not event_date:
        event_date = input("Introduce la fecha del evento (ej: 2025-09-10 o 10-09-2025): ")

    logger.info(f"Datos: vendidas={sold}, validadas={validated}, fecha={event_date}")
    return sold, validated, event_date


def descargar_pdf(driver: webdriver.Remote, downloads_dir: Path, recinto: str, event_date: str, logger: logging.Logger) -> Optional[Path]:
    logger.info("Descargando PDF del evento...")
    pdf_button_sel = prompt_selector("(Ticketmaster) botón/enlace para descargar PDF del evento")

    wait = WebDriverWait(driver, 30)
    try:
        wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, pdf_button_sel)))
        driver.find_element(By.CSS_SELECTOR, pdf_button_sel).click()
    except Exception as exc:
        logger.error(f"Fallo al iniciar descarga de PDF: {exc}")
        print("[ERROR] No se pudo iniciar la descarga del PDF. Revisa el selector y vuelve a intentar.")
        return None

    downloaded = wait_for_download(downloads_dir, logger, timeout_sec=180)
    if not downloaded:
        logger.error("No se detectó la descarga del PDF a tiempo.")
        print("[ERROR] La descarga del PDF no se completó a tiempo.")
        return None

    renamed = rename_pdf(downloaded, downloads_dir, recinto, event_date, logger)
    return renamed


# ------------------------------ Podio ------------------------------

def login_podio(driver: webdriver.Remote, logger: logging.Logger) -> None:
    load_dotenv()
    user = get_env_or_prompt("PODIO_USER", "Usuario de Podio")
    password = get_env_or_prompt("PODIO_PASS", "Contraseña de Podio", secret=True)
    login_url = input("URL de login de Podio (incluye https://): ")

    driver.get(login_url)
    logger.info("Abriendo página de login de Podio...")

    user_sel = prompt_selector("(Podio) campo de usuario")
    pass_sel = prompt_selector("(Podio) campo de contraseña")
    submit_sel = prompt_selector("(Podio) botón de login")

    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, user_sel)))
    driver.find_element(By.CSS_SELECTOR, user_sel).clear()
    driver.find_element(By.CSS_SELECTOR, user_sel).send_keys(user)

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, pass_sel)))
    driver.find_element(By.CSS_SELECTOR, pass_sel).clear()
    driver.find_element(By.CSS_SELECTOR, pass_sel).send_keys(password)

    driver.find_element(By.CSS_SELECTOR, submit_sel).click()
    logger.info("Login en Podio enviado. Si hay 2FA, complétalo manualmente.")
    time.sleep(5)


def rellenar_formulario(driver: webdriver.Remote, recinto: str, event_date: str, sold: Optional[int], validated: Optional[int], logger: logging.Logger) -> None:
    logger.info("Rellenando formulario en Podio...")
    form_url = input("URL del formulario del evento en Podio (o URL de creación de item): ")
    driver.get(form_url)

    # Selectores para campos, solicitados al usuario
    recinto_sel = prompt_selector("(Podio) campo 'recinto' o equivalente")
    fecha_sel = prompt_selector("(Podio) campo 'fecha' o equivalente")
    vendidas_sel = prompt_selector("(Podio) campo 'entradas vendidas' o equivalente")
    validadas_sel = prompt_selector("(Podio) campo 'entradas validadas' o equivalente")
    submit_sel = prompt_selector("(Podio) botón para enviar/guardar el formulario")

    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, recinto_sel)))
    driver.find_element(By.CSS_SELECTOR, recinto_sel).clear()
    driver.find_element(By.CSS_SELECTOR, recinto_sel).send_keys(recinto)

    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, fecha_sel)))
    driver.find_element(By.CSS_SELECTOR, fecha_sel).clear()
    driver.find_element(By.CSS_SELECTOR, fecha_sel).send_keys(event_date)

    if sold is not None:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, vendidas_sel)))
        driver.find_element(By.CSS_SELECTOR, vendidas_sel).clear()
        driver.find_element(By.CSS_SELECTOR, vendidas_sel).send_keys(str(sold))

    if validated is not None:
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, validadas_sel)))
        driver.find_element(By.CSS_SELECTOR, validadas_sel).clear()
        driver.find_element(By.CSS_SELECTOR, validadas_sel).send_keys(str(validated))

    # El envío se realizará después de subir el PDF
    driver._podio_submit_selector = submit_sel  # type: ignore[attr-defined]


def subir_pdf(driver: webdriver.Remote, pdf_path: Optional[Path], logger: logging.Logger) -> None:
    if not pdf_path:
        logger.warning("No hay PDF para subir a Podio.")
        return
    logger.info(f"Subiendo PDF a Podio: {pdf_path}")

    upload_sel = prompt_selector("(Podio) input[type=file] para subir el PDF")

    wait = WebDriverWait(driver, 30)
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, upload_sel)))
    upload_input = driver.find_element(By.CSS_SELECTOR, upload_sel)
    upload_input.send_keys(str(pdf_path.resolve()))

    # Espera breve a que termine la subida
    time.sleep(5)

    # Envía el formulario si guardamos el selector
    submit_sel = getattr(driver, "_podio_submit_selector", None)
    if submit_sel:
        try:
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, submit_sel)))
            driver.find_element(By.CSS_SELECTOR, submit_sel).click()
            logger.info("Formulario de Podio enviado.")
        except Exception as exc:
            logger.error(f"No se pudo enviar el formulario de Podio: {exc}")


# ------------------------------ Orquestación ------------------------------

def main() -> None:
    dirs = ensure_directories()
    logger = setup_logging(dirs["logs"])
    load_dotenv()

    print("=== Automatización Ticketmaster → Podio ===")
    recinto = input("Introduce el nombre o código exacto del recinto: ").strip()
    if not recinto:
        print("Debes indicar un recinto o código.")
        return

    # Abre el navegador visible
    try:
        driver = init_driver(dirs["downloads"], logger)
    except Exception as exc:
        logger.error(f"No se pudo inicializar el navegador: {exc}")
        print("[ERROR] No se pudo inicializar el navegador. Revisa el driver y vuelve a intentar.")
        return

    sold = validated = None
    event_date = ""
    pdf_file: Optional[Path] = None

    try:
        # Ticketmaster
        login_ticketmaster(driver, logger)
        encontrado = buscar_evento(driver, recinto, logger)
        if encontrado:
            sold, validated, event_date = extraer_datos(driver, logger)
            pdf_file = descargar_pdf(driver, dirs["downloads"], recinto, event_date, logger)
            export_data(dirs["data"], recinto, event_date, sold, validated, logger)
        else:
            logger.info("Continuando con Podio aunque no se encontró el evento en Ticketmaster.")

        # Podio
        login_podio(driver, logger)
        rellenar_formulario(driver, recinto, event_date, sold, validated, logger)
        subir_pdf(driver, pdf_file, logger)

        logger.info("Flujo completado.")
    finally:
        # Mantén el navegador abierto para revisión si el usuario quiere
        keep_open = input("¿Deseas mantener el navegador abierto? [s/N]: ").strip().lower()
        if keep_open != "s":
            try:
                driver.quit()
            except Exception:
                pass


if __name__ == "__main__":
    main()

