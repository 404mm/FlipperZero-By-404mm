#!/usr/bin/env python3
"""
Script de automatización Ticketmaster-Podio
Automatiza el flujo de extracción de datos de eventos desde Ticketmaster
y su posterior registro en Podio.
"""

import os
import sys
import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from time import sleep
from typing import Dict, Optional, Tuple

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
import pandas as pd


# Configuración de logging
def setup_logging() -> logging.Logger:
    """Configura el sistema de logging con archivo y consola."""
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"automation_{timestamp}.log"
    
    # Configurar formato de logs
    log_format = '%(asctime)s - %(levelname)s - %(funcName)s - %(message)s'
    
    # Configurar handlers
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(log_format))
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
    
    # Configurar logger
    logger = logging.getLogger('TicketmasterPodioBot')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# Inicializar logger global
logger = setup_logging()


def load_credentials() -> Dict[str, str]:
    """Carga las credenciales desde el archivo .env"""
    load_dotenv()
    
    required_vars = [
        'TICKETMASTER_USER', 'TICKETMASTER_PASS',
        'PODIO_USER', 'PODIO_PASS'
    ]
    
    credentials = {}
    missing_vars = []
    
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            missing_vars.append(var)
        else:
            credentials[var] = value
    
    if missing_vars:
        logger.error(f"Faltan las siguientes variables en .env: {', '.join(missing_vars)}")
        sys.exit(1)
    
    logger.info("Credenciales cargadas correctamente")
    return credentials


def init_driver() -> webdriver.Chrome:
    """Inicializa el driver de Chrome con las opciones necesarias."""
    options = webdriver.ChromeOptions()
    
    # Configurar directorio de descargas
    download_dir = Path.cwd() / "downloads"
    download_dir.mkdir(exist_ok=True)
    
    prefs = {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True
    }
    options.add_experimental_option("prefs", prefs)
    
    # Opciones adicionales
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    logger.info("Inicializando navegador Chrome...")
    driver = webdriver.Chrome(options=options)
    driver.maximize_window()
    
    return driver


def wait_and_find_element(driver: webdriver.Chrome, by: By, value: str, 
                         timeout: int = 10, clickable: bool = False) -> Optional:
    """Espera y encuentra un elemento en la página."""
    try:
        wait = WebDriverWait(driver, timeout)
        if clickable:
            element = wait.until(EC.element_to_be_clickable((by, value)))
        else:
            element = wait.until(EC.presence_of_element_located((by, value)))
        return element
    except TimeoutException:
        logger.warning(f"No se encontró el elemento: {value}")
        return None


def login_ticketmaster(driver: webdriver.Chrome, credentials: Dict[str, str]) -> bool:
    """
    Realiza el login en Ticketmaster.
    
    Args:
        driver: Instancia del navegador
        credentials: Diccionario con las credenciales
        
    Returns:
        bool: True si el login fue exitoso, False en caso contrario
    """
    logger.info("Iniciando login en Ticketmaster...")
    
    try:
        # Navegar a la página de login
        login_url = input("Por favor, ingresa la URL de login de Ticketmaster: ").strip()
        driver.get(login_url)
        sleep(2)
        
        # Solicitar selectores si no los conocemos
        username_selector = input("Ingresa el selector CSS/ID para el campo de usuario (ej: #username): ").strip()
        password_selector = input("Ingresa el selector CSS/ID para el campo de contraseña: ").strip()
        login_button_selector = input("Ingresa el selector CSS/ID para el botón de login: ").strip()
        
        # Encontrar y llenar campos
        username_field = wait_and_find_element(driver, By.CSS_SELECTOR, username_selector)
        if not username_field:
            logger.error("No se encontró el campo de usuario")
            return False
            
        username_field.clear()
        username_field.send_keys(credentials['TICKETMASTER_USER'])
        logger.debug("Usuario ingresado")
        
        password_field = wait_and_find_element(driver, By.CSS_SELECTOR, password_selector)
        if not password_field:
            logger.error("No se encontró el campo de contraseña")
            return False
            
        password_field.clear()
        password_field.send_keys(credentials['TICKETMASTER_PASS'])
        logger.debug("Contraseña ingresada")
        
        # Click en login
        login_button = wait_and_find_element(driver, By.CSS_SELECTOR, login_button_selector, clickable=True)
        if not login_button:
            logger.error("No se encontró el botón de login")
            return False
            
        login_button.click()
        logger.info("Formulario de login enviado")
        
        # Esperar a que cargue la página después del login
        sleep(5)
        
        # Verificar login exitoso
        dashboard_indicator = input("Ingresa un selector que indique login exitoso (ej: elemento del dashboard): ").strip()
        if wait_and_find_element(driver, By.CSS_SELECTOR, dashboard_indicator, timeout=15):
            logger.info("Login en Ticketmaster exitoso")
            return True
        else:
            logger.error("No se pudo verificar el login exitoso")
            return False
            
    except Exception as e:
        logger.error(f"Error durante el login en Ticketmaster: {str(e)}")
        return False


def buscar_evento(driver: webdriver.Chrome, recinto: str) -> bool:
    """
    Busca un evento por nombre o código de recinto.
    
    Args:
        driver: Instancia del navegador
        recinto: Nombre o código del recinto a buscar
        
    Returns:
        bool: True si se encontró el evento, False en caso contrario
    """
    logger.info(f"Buscando evento para el recinto: {recinto}")
    
    try:
        # Solicitar información sobre cómo buscar
        search_url = input("Ingresa la URL de búsqueda de eventos (o 'skip' si ya estás en la página correcta): ").strip()
        if search_url.lower() != 'skip':
            driver.get(search_url)
            sleep(2)
        
        search_method = input("¿Cómo se busca el evento? (1: Campo de búsqueda, 2: Lista/tabla, 3: URL directa): ").strip()
        
        if search_method == "1":
            # Búsqueda por campo
            search_selector = input("Ingresa el selector del campo de búsqueda: ").strip()
            search_field = wait_and_find_element(driver, By.CSS_SELECTOR, search_selector)
            if not search_field:
                logger.error("No se encontró el campo de búsqueda")
                return False
                
            search_field.clear()
            search_field.send_keys(recinto)
            
            # Buscar botón o presionar Enter
            search_button_selector = input("Ingresa el selector del botón de búsqueda (o 'enter' para presionar Enter): ").strip()
            if search_button_selector.lower() != 'enter':
                search_button = wait_and_find_element(driver, By.CSS_SELECTOR, search_button_selector, clickable=True)
                if search_button:
                    search_button.click()
            else:
                search_field.send_keys(Keys.RETURN)
                
        elif search_method == "2":
            # Búsqueda en lista/tabla
            event_selector = input("Ingresa el selector CSS para identificar el evento en la lista: ").strip()
            event_element = wait_and_find_element(driver, By.CSS_SELECTOR, event_selector)
            if not event_element:
                logger.error(f"No se encontró el evento para el recinto: {recinto}")
                return False
            event_element.click()
            
        elif search_method == "3":
            # URL directa
            event_url = input(f"Ingresa la URL directa del evento para {recinto}: ").strip()
            driver.get(event_url)
            
        sleep(3)
        
        # Verificar que estamos en la página del evento
        event_indicator = input("Ingresa un selector que confirme que estamos en la página del evento: ").strip()
        if wait_and_find_element(driver, By.CSS_SELECTOR, event_indicator):
            logger.info(f"Evento encontrado para el recinto: {recinto}")
            return True
        else:
            logger.error(f"No se pudo confirmar el acceso al evento para: {recinto}")
            return False
            
    except Exception as e:
        logger.error(f"Error al buscar evento: {str(e)}")
        return False


def extraer_datos(driver: webdriver.Chrome) -> Optional[Dict[str, any]]:
    """
    Extrae los datos del evento (entradas vendidas, validadas, etc.).
    
    Args:
        driver: Instancia del navegador
        
    Returns:
        Dict con los datos extraídos o None si hay error
    """
    logger.info("Extrayendo datos del evento...")
    
    datos = {
        'fecha_extraccion': datetime.now().isoformat(),
        'entradas_vendidas': None,
        'entradas_validadas': None,
        'otros_datos': {}
    }
    
    try:
        # Solicitar selectores para los datos
        print("\nVamos a extraer los datos del evento.")
        print("Para cada dato, proporciona el selector CSS correspondiente.")
        
        # Entradas vendidas
        vendidas_selector = input("Selector para 'Entradas vendidas totales': ").strip()
        vendidas_element = wait_and_find_element(driver, By.CSS_SELECTOR, vendidas_selector)
        if vendidas_element:
            datos['entradas_vendidas'] = vendidas_element.text.strip()
            logger.info(f"Entradas vendidas: {datos['entradas_vendidas']}")
        else:
            logger.warning("No se pudo obtener el dato de entradas vendidas")
        
        # Entradas validadas
        validadas_selector = input("Selector para 'Entradas validadas/entrada real': ").strip()
        validadas_element = wait_and_find_element(driver, By.CSS_SELECTOR, validadas_selector)
        if validadas_element:
            datos['entradas_validadas'] = validadas_element.text.strip()
            logger.info(f"Entradas validadas: {datos['entradas_validadas']}")
        else:
            logger.warning("No se pudo obtener el dato de entradas validadas")
        
        # Otros datos opcionales
        while True:
            otro_dato = input("¿Hay algún otro dato que extraer? (nombre del dato o 'no'): ").strip()
            if otro_dato.lower() == 'no':
                break
            
            dato_selector = input(f"Selector para '{otro_dato}': ").strip()
            dato_element = wait_and_find_element(driver, By.CSS_SELECTOR, dato_selector)
            if dato_element:
                datos['otros_datos'][otro_dato] = dato_element.text.strip()
                logger.info(f"{otro_dato}: {datos['otros_datos'][otro_dato]}")
        
        return datos
        
    except Exception as e:
        logger.error(f"Error al extraer datos: {str(e)}")
        return None


def guardar_datos(datos: Dict[str, any], recinto: str) -> Tuple[str, str]:
    """
    Guarda los datos extraídos en formatos JSON y CSV.
    
    Args:
        datos: Diccionario con los datos extraídos
        recinto: Nombre del recinto
        
    Returns:
        Tupla con las rutas de los archivos guardados (json, csv)
    """
    logger.info("Guardando datos extraídos...")
    
    # Crear directorio de datos
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base_filename = f"{recinto.replace(' ', '_')}_{timestamp}"
    
    # Guardar JSON
    json_path = data_dir / f"{base_filename}.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    logger.info(f"Datos guardados en JSON: {json_path}")
    
    # Preparar datos para CSV
    csv_data = {
        'recinto': recinto,
        'fecha_extraccion': datos['fecha_extraccion'],
        'entradas_vendidas': datos['entradas_vendidas'],
        'entradas_validadas': datos['entradas_validadas']
    }
    csv_data.update(datos['otros_datos'])
    
    # Guardar CSV
    csv_path = data_dir / f"{base_filename}.csv"
    df = pd.DataFrame([csv_data])
    df.to_csv(csv_path, index=False, encoding='utf-8')
    logger.info(f"Datos guardados en CSV: {csv_path}")
    
    return str(json_path), str(csv_path)


def descargar_pdf(driver: webdriver.Chrome, recinto: str) -> Optional[str]:
    """
    Descarga el PDF del evento.
    
    Args:
        driver: Instancia del navegador
        recinto: Nombre del recinto
        
    Returns:
        Ruta del PDF descargado o None si hay error
    """
    logger.info("Preparando descarga de PDF...")
    
    try:
        # Solicitar información sobre cómo descargar el PDF
        pdf_method = input("¿Cómo se descarga el PDF? (1: Botón directo, 2: Generar primero, 3: Link): ").strip()
        
        if pdf_method == "1":
            # Botón de descarga directo
            download_selector = input("Ingresa el selector del botón de descarga del PDF: ").strip()
            download_button = wait_and_find_element(driver, By.CSS_SELECTOR, download_selector, clickable=True)
            if not download_button:
                logger.error("No se encontró el botón de descarga")
                return None
            download_button.click()
            
        elif pdf_method == "2":
            # Generar PDF primero
            generate_selector = input("Ingresa el selector del botón para generar el PDF: ").strip()
            generate_button = wait_and_find_element(driver, By.CSS_SELECTOR, generate_selector, clickable=True)
            if not generate_button:
                logger.error("No se encontró el botón de generación")
                return None
            generate_button.click()
            
            logger.info("Esperando generación del PDF...")
            sleep(5)  # Esperar a que se genere
            
            # Ahora descargar
            download_selector = input("Ingresa el selector del botón/link de descarga del PDF generado: ").strip()
            download_element = wait_and_find_element(driver, By.CSS_SELECTOR, download_selector, clickable=True)
            if not download_element:
                logger.error("No se encontró el elemento de descarga")
                return None
            download_element.click()
            
        elif pdf_method == "3":
            # Link directo
            pdf_link_selector = input("Ingresa el selector del link del PDF: ").strip()
            pdf_link = wait_and_find_element(driver, By.CSS_SELECTOR, pdf_link_selector)
            if not pdf_link:
                logger.error("No se encontró el link del PDF")
                return None
            pdf_url = pdf_link.get_attribute('href')
            driver.get(pdf_url)
        
        # Esperar a que se complete la descarga
        logger.info("Esperando descarga del PDF...")
        sleep(10)  # Ajustar según sea necesario
        
        # Renombrar el archivo descargado
        download_dir = Path("downloads")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_filename = f"{recinto.replace(' ', '_')}_{timestamp}.pdf"
        
        # Buscar el archivo más reciente en downloads
        pdf_files = list(download_dir.glob("*.pdf"))
        if pdf_files:
            latest_pdf = max(pdf_files, key=lambda p: p.stat().st_mtime)
            new_path = download_dir / new_filename
            latest_pdf.rename(new_path)
            logger.info(f"PDF descargado y renombrado: {new_path}")
            return str(new_path)
        else:
            logger.error("No se encontró ningún PDF descargado")
            return None
            
    except Exception as e:
        logger.error(f"Error al descargar PDF: {str(e)}")
        return None


def login_podio(driver: webdriver.Chrome, credentials: Dict[str, str]) -> bool:
    """
    Realiza el login en Podio.
    
    Args:
        driver: Instancia del navegador
        credentials: Diccionario con las credenciales
        
    Returns:
        bool: True si el login fue exitoso, False en caso contrario
    """
    logger.info("Iniciando login en Podio...")
    
    try:
        # Navegar a Podio
        podio_url = input("Por favor, ingresa la URL de login de Podio: ").strip()
        driver.get(podio_url)
        sleep(2)
        
        # Solicitar selectores
        username_selector = input("Ingresa el selector para el campo de usuario en Podio: ").strip()
        password_selector = input("Ingresa el selector para el campo de contraseña en Podio: ").strip()
        login_button_selector = input("Ingresa el selector para el botón de login en Podio: ").strip()
        
        # Login
        username_field = wait_and_find_element(driver, By.CSS_SELECTOR, username_selector)
        if not username_field:
            logger.error("No se encontró el campo de usuario en Podio")
            return False
            
        username_field.clear()
        username_field.send_keys(credentials['PODIO_USER'])
        
        password_field = wait_and_find_element(driver, By.CSS_SELECTOR, password_selector)
        if not password_field:
            logger.error("No se encontró el campo de contraseña en Podio")
            return False
            
        password_field.clear()
        password_field.send_keys(credentials['PODIO_PASS'])
        
        login_button = wait_and_find_element(driver, By.CSS_SELECTOR, login_button_selector, clickable=True)
        if not login_button:
            logger.error("No se encontró el botón de login en Podio")
            return False
            
        login_button.click()
        logger.info("Formulario de login enviado")
        
        sleep(5)
        
        # Verificar login
        dashboard_indicator = input("Ingresa un selector que indique login exitoso en Podio: ").strip()
        if wait_and_find_element(driver, By.CSS_SELECTOR, dashboard_indicator, timeout=15):
            logger.info("Login en Podio exitoso")
            return True
        else:
            logger.error("No se pudo verificar el login exitoso en Podio")
            return False
            
    except Exception as e:
        logger.error(f"Error durante el login en Podio: {str(e)}")
        return False


def buscar_evento_podio(driver: webdriver.Chrome, recinto: str) -> bool:
    """
    Busca el evento en Podio.
    
    Args:
        driver: Instancia del navegador
        recinto: Nombre o código del recinto
        
    Returns:
        bool: True si se encontró, False en caso contrario
    """
    logger.info(f"Buscando evento en Podio para: {recinto}")
    
    try:
        # Navegar a la sección de eventos si es necesario
        events_url = input("Ingresa la URL de la sección de eventos en Podio (o 'skip' si ya estás ahí): ").strip()
        if events_url.lower() != 'skip':
            driver.get(events_url)
            sleep(2)
        
        # Buscar el evento
        search_method = input("¿Cómo buscar el evento en Podio? (1: Campo búsqueda, 2: Lista, 3: URL directa): ").strip()
        
        if search_method == "1":
            search_selector = input("Selector del campo de búsqueda en Podio: ").strip()
            search_field = wait_and_find_element(driver, By.CSS_SELECTOR, search_selector)
            if not search_field:
                logger.error("No se encontró el campo de búsqueda")
                return False
                
            search_field.clear()
            search_field.send_keys(recinto)
            
            submit_selector = input("Selector del botón buscar (o 'enter'): ").strip()
            if submit_selector.lower() != 'enter':
                submit_button = wait_and_find_element(driver, By.CSS_SELECTOR, submit_selector, clickable=True)
                if submit_button:
                    submit_button.click()
            else:
                search_field.send_keys(Keys.RETURN)
                
            sleep(3)
            
            # Seleccionar el evento de los resultados
            event_selector = input("Selector para identificar el evento en los resultados: ").strip()
            event_element = wait_and_find_element(driver, By.CSS_SELECTOR, event_selector, clickable=True)
            if not event_element:
                logger.error("No se encontró el evento en los resultados")
                return False
            event_element.click()
            
        elif search_method == "2":
            event_selector = input("Selector para el evento en la lista: ").strip()
            event_element = wait_and_find_element(driver, By.CSS_SELECTOR, event_selector, clickable=True)
            if not event_element:
                logger.error("No se encontró el evento en la lista")
                return False
            event_element.click()
            
        elif search_method == "3":
            event_url = input(f"URL directa del evento en Podio para {recinto}: ").strip()
            driver.get(event_url)
        
        sleep(3)
        logger.info("Evento encontrado en Podio")
        return True
        
    except Exception as e:
        logger.error(f"Error al buscar evento en Podio: {str(e)}")
        return False


def rellenar_formulario(driver: webdriver.Chrome, datos: Dict[str, any]) -> bool:
    """
    Rellena el formulario en Podio con los datos extraídos.
    
    Args:
        driver: Instancia del navegador
        datos: Diccionario con los datos a rellenar
        
    Returns:
        bool: True si se completó correctamente
    """
    logger.info("Rellenando formulario en Podio...")
    
    try:
        # Acceder al formulario
        form_selector = input("Selector para acceder al formulario (botón editar/nuevo): ").strip()
        form_button = wait_and_find_element(driver, By.CSS_SELECTOR, form_selector, clickable=True)
        if form_button:
            form_button.click()
            sleep(2)
        
        # Mapear campos del formulario
        print("\nVamos a mapear los campos del formulario con los datos extraídos.")
        
        # Entradas vendidas
        if datos.get('entradas_vendidas'):
            field_selector = input("Selector para el campo 'Entradas vendidas': ").strip()
            field = wait_and_find_element(driver, By.CSS_SELECTOR, field_selector)
            if field:
                field.clear()
                field.send_keys(str(datos['entradas_vendidas']))
                logger.info("Campo 'Entradas vendidas' completado")
        
        # Entradas validadas
        if datos.get('entradas_validadas'):
            field_selector = input("Selector para el campo 'Entradas validadas': ").strip()
            field = wait_and_find_element(driver, By.CSS_SELECTOR, field_selector)
            if field:
                field.clear()
                field.send_keys(str(datos['entradas_validadas']))
                logger.info("Campo 'Entradas validadas' completado")
        
        # Otros campos
        for campo, valor in datos.get('otros_datos', {}).items():
            use_field = input(f"¿Existe un campo para '{campo}' en el formulario? (si/no): ").strip()
            if use_field.lower() == 'si':
                field_selector = input(f"Selector para el campo '{campo}': ").strip()
                field = wait_and_find_element(driver, By.CSS_SELECTOR, field_selector)
                if field:
                    field.clear()
                    field.send_keys(str(valor))
                    logger.info(f"Campo '{campo}' completado")
        
        return True
        
    except Exception as e:
        logger.error(f"Error al rellenar formulario: {str(e)}")
        return False


def subir_pdf(driver: webdriver.Chrome, pdf_path: str) -> bool:
    """
    Sube el PDF al formulario de Podio.
    
    Args:
        driver: Instancia del navegador
        pdf_path: Ruta del archivo PDF
        
    Returns:
        bool: True si se subió correctamente
    """
    logger.info(f"Subiendo PDF: {pdf_path}")
    
    try:
        # Buscar el campo de archivo
        file_input_selector = input("Selector para el campo de subida de archivos (input[type='file']): ").strip()
        
        # Primero intentar con input directo
        file_inputs = driver.find_elements(By.CSS_SELECTOR, file_input_selector)
        if file_inputs:
            file_input = file_inputs[0]
            # Hacer visible el input si está oculto
            driver.execute_script("arguments[0].style.display = 'block';", file_input)
            file_input.send_keys(os.path.abspath(pdf_path))
            logger.info("PDF enviado al input de archivo")
            sleep(3)  # Esperar a que se procese
            return True
        
        # Si no funciona, intentar con botón que abre selector
        upload_button_selector = input("Si no funcionó, ingresa el selector del botón de subir archivo: ").strip()
        upload_button = wait_and_find_element(driver, By.CSS_SELECTOR, upload_button_selector, clickable=True)
        if upload_button:
            logger.warning("Necesitarás seleccionar manualmente el archivo en el diálogo que se abrirá")
            logger.warning(f"Archivo a seleccionar: {os.path.abspath(pdf_path)}")
            upload_button.click()
            input("Presiona Enter después de seleccionar el archivo...")
            return True
            
        logger.error("No se pudo encontrar el campo de subida de archivos")
        return False
        
    except Exception as e:
        logger.error(f"Error al subir PDF: {str(e)}")
        return False


def enviar_formulario(driver: webdriver.Chrome) -> bool:
    """
    Envía el formulario en Podio.
    
    Args:
        driver: Instancia del navegador
        
    Returns:
        bool: True si se envió correctamente
    """
    logger.info("Enviando formulario...")
    
    try:
        # Buscar botón de envío
        submit_selector = input("Selector del botón para enviar/guardar el formulario: ").strip()
        submit_button = wait_and_find_element(driver, By.CSS_SELECTOR, submit_selector, clickable=True)
        
        if not submit_button:
            logger.error("No se encontró el botón de envío")
            return False
        
        submit_button.click()
        logger.info("Formulario enviado")
        
        sleep(3)
        
        # Verificar envío exitoso
        success_indicator = input("Selector de elemento que confirme envío exitoso (mensaje, redirección): ").strip()
        if wait_and_find_element(driver, By.CSS_SELECTOR, success_indicator, timeout=10):
            logger.info("Formulario enviado exitosamente")
            return True
        else:
            logger.warning("No se pudo confirmar el envío exitoso")
            return True  # Asumimos que se envió si no hay error
            
    except Exception as e:
        logger.error(f"Error al enviar formulario: {str(e)}")
        return False


def main():
    """Función principal que orquesta todo el flujo."""
    logger.info("=== Iniciando automatización Ticketmaster-Podio ===")
    
    # Cargar credenciales
    credentials = load_credentials()
    
    # Solicitar recinto
    recinto = input("Ingresa el nombre o código exacto del recinto: ").strip()
    if not recinto:
        logger.error("El recinto no puede estar vacío")
        return
    
    logger.info(f"Procesando recinto: {recinto}")
    
    # Inicializar driver
    driver = init_driver()
    
    try:
        # === TICKETMASTER ===
        logger.info("=== FASE 1: TICKETMASTER ===")
        
        # Login
        if not login_ticketmaster(driver, credentials):
            logger.error("Fallo en login de Ticketmaster. Abortando.")
            return
        
        # Buscar evento
        if not buscar_evento(driver, recinto):
            logger.error(f"No se encontró el evento para el recinto: {recinto}")
            logger.info("Continuando con el proceso...")
            
        # Extraer datos
        datos = extraer_datos(driver)
        if not datos:
            logger.error("No se pudieron extraer datos. Abortando.")
            return
        
        # Guardar datos
        json_path, csv_path = guardar_datos(datos, recinto)
        
        # Descargar PDF
        pdf_path = descargar_pdf(driver, recinto)
        if not pdf_path:
            logger.error("No se pudo descargar el PDF")
            logger.info("Continuando sin PDF...")
        
        # === PODIO ===
        logger.info("=== FASE 2: PODIO ===")
        
        # Login en Podio
        if not login_podio(driver, credentials):
            logger.error("Fallo en login de Podio. Abortando.")
            return
        
        # Buscar evento en Podio
        if not buscar_evento_podio(driver, recinto):
            logger.error("No se encontró el evento en Podio")
            return
        
        # Rellenar formulario
        if not rellenar_formulario(driver, datos):
            logger.warning("Hubo problemas al rellenar el formulario")
        
        # Subir PDF si existe
        if pdf_path and os.path.exists(pdf_path):
            if not subir_pdf(driver, pdf_path):
                logger.warning("No se pudo subir el PDF")
        
        # Enviar formulario
        if enviar_formulario(driver):
            logger.info("=== PROCESO COMPLETADO EXITOSAMENTE ===")
        else:
            logger.error("Fallo al enviar el formulario")
        
    except Exception as e:
        logger.error(f"Error general en el proceso: {str(e)}")
        
    finally:
        # Esperar antes de cerrar para revisar
        input("\nPresiona Enter para cerrar el navegador...")
        driver.quit()
        logger.info("Navegador cerrado. Fin del proceso.")


if __name__ == "__main__":
    main()