#!/usr/bin/env python3
"""
Script de automatización para Ticketmaster y Podio
Automatiza el flujo de extracción de datos de eventos y actualización en Podio
"""

import os
import json
import csv
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

class TicketmasterPodioAutomation:
    def __init__(self):
        """Inicializar la clase con configuración básica"""
        self.driver = None
        self.wait = None
        self.setup_logging()
        self.setup_selenium()
        
        # Credenciales desde .env
        self.ticketmaster_user = os.getenv('TICKETMASTER_USER')
        self.ticketmaster_pass = os.getenv('TICKETMASTER_PASS')
        self.podio_user = os.getenv('PODIO_USER')
        self.podio_pass = os.getenv('PODIO_PASS')
        
        # Directorio de descargas
        self.download_dir = os.path.join(os.getcwd(), 'downloads')
        os.makedirs(self.download_dir, exist_ok=True)
        
    def setup_logging(self):
        """Configurar el sistema de logging"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"automation_{timestamp}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("Iniciando script de automatización")
        
    def setup_selenium(self):
        """Configurar el navegador Chrome"""
        try:
            chrome_options = Options()
            # No headless para que puedas ver la navegación
            # chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Configurar directorio de descargas
            prefs = {
                "download.default_directory": self.download_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            chrome_options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 10)
            
            self.logger.info("Navegador Chrome configurado correctamente")
            
        except Exception as e:
            self.logger.error(f"Error configurando Selenium: {e}")
            raise
            
    def login_ticketmaster(self) -> bool:
        """
        Realizar login en Ticketmaster
        Returns: True si el login es exitoso, False en caso contrario
        """
        try:
            self.logger.info("Iniciando login en Ticketmaster")
            
            # Verificar credenciales
            if not self.ticketmaster_user or not self.ticketmaster_pass:
                self.logger.error("Credenciales de Ticketmaster no encontradas en .env")
                return False
                
            # Navegar a Ticketmaster
            ticketmaster_url = input("Ingresa la URL de login de Ticketmaster: ").strip()
            if not ticketmaster_url:
                ticketmaster_url = "https://www.ticketmaster.com/signin"
                
            self.driver.get(ticketmaster_url)
            self.logger.info(f"Navegando a: {ticketmaster_url}")
            
            # Esperar y encontrar campos de login
            print("Por favor, indica los selectores de los campos de login:")
            email_selector = input("Selector del campo email/usuario: ").strip()
            if not email_selector:
                email_selector = "input[name='email']"
                
            password_selector = input("Selector del campo contraseña: ").strip()
            if not password_selector:
                password_selector = "input[name='password']"
                
            login_button_selector = input("Selector del botón de login: ").strip()
            if not login_button_selector:
                login_button_selector = "button[type='submit']"
            
            # Rellenar formulario
            email_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, email_selector)))
            email_field.clear()
            email_field.send_keys(self.ticketmaster_user)
            
            password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)
            password_field.clear()
            password_field.send_keys(self.ticketmaster_pass)
            
            # Hacer clic en login
            login_button = self.driver.find_element(By.CSS_SELECTOR, login_button_selector)
            login_button.click()
            
            # Esperar a que se complete el login
            time.sleep(3)
            
            # Verificar si el login fue exitoso
            current_url = self.driver.current_url
            if "signin" not in current_url.lower() and "login" not in current_url.lower():
                self.logger.info("Login en Ticketmaster exitoso")
                return True
            else:
                self.logger.error("Login en Ticketmaster falló")
                return False
                
        except TimeoutException:
            self.logger.error("Timeout esperando elementos de login en Ticketmaster")
            return False
        except Exception as e:
            self.logger.error(f"Error durante login en Ticketmaster: {e}")
            return False
            
    def buscar_evento(self, recinto: str) -> bool:
        """
        Buscar evento por recinto en Ticketmaster
        Args: recinto - nombre o código del recinto
        Returns: True si encuentra el evento, False en caso contrario
        """
        try:
            self.logger.info(f"Buscando evento para recinto: {recinto}")
            
            # Navegar al dashboard o página de búsqueda
            dashboard_url = input("Ingresa la URL del dashboard/búsqueda de eventos: ").strip()
            if dashboard_url:
                self.driver.get(dashboard_url)
                
            # Buscar campo de búsqueda
            search_selector = input("Selector del campo de búsqueda de eventos: ").strip()
            if not search_selector:
                search_selector = "input[type='search'], input[placeholder*='search'], input[name*='search']"
                
            search_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, search_selector)))
            search_field.clear()
            search_field.send_keys(recinto)
            
            # Buscar botón de búsqueda
            search_button_selector = input("Selector del botón de búsqueda (Enter si es automático): ").strip()
            if search_button_selector:
                search_button = self.driver.find_element(By.CSS_SELECTOR, search_button_selector)
                search_button.click()
            else:
                search_field.send_keys("\n")  # Presionar Enter
                
            time.sleep(3)
            
            # Verificar si se encontraron resultados
            results_selector = input("Selector de los resultados de búsqueda: ").strip()
            if results_selector:
                try:
                    results = self.driver.find_elements(By.CSS_SELECTOR, results_selector)
                    if results:
                        self.logger.info(f"Se encontraron {len(results)} resultados")
                        # Hacer clic en el primer resultado
                        results[0].click()
                        time.sleep(2)
                        return True
                    else:
                        self.logger.warning(f"No se encontraron eventos para el recinto: {recinto}")
                        return False
                except NoSuchElementException:
                    self.logger.warning(f"No se encontraron eventos para el recinto: {recinto}")
                    return False
            else:
                self.logger.info("Continuando sin verificar resultados específicos")
                return True
                
        except Exception as e:
            self.logger.error(f"Error buscando evento: {e}")
            return False
            
    def extraer_datos(self) -> Dict:
        """
        Extraer datos del evento desde el dashboard de Ticketmaster
        Returns: Diccionario con los datos extraídos
        """
        try:
            self.logger.info("Extrayendo datos del evento")
            
            datos = {
                'entradas_vendidas': 0,
                'entradas_validadas': 0,
                'fecha_extraccion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Solicitar selectores para los datos
            print("Por favor, proporciona los selectores para extraer los datos:")
            
            vendidas_selector = input("Selector para entradas vendidas totales: ").strip()
            if vendidas_selector:
                try:
                    vendidas_element = self.driver.find_element(By.CSS_SELECTOR, vendidas_selector)
                    vendidas_text = vendidas_element.text.strip()
                    # Extraer números del texto
                    import re
                    numeros = re.findall(r'\d+', vendidas_text.replace(',', ''))
                    if numeros:
                        datos['entradas_vendidas'] = int(numeros[0])
                        self.logger.info(f"Entradas vendidas: {datos['entradas_vendidas']}")
                except Exception as e:
                    self.logger.warning(f"No se pudo extraer entradas vendidas: {e}")
                    
            validadas_selector = input("Selector para entradas validadas/entrada real: ").strip()
            if validadas_selector:
                try:
                    validadas_element = self.driver.find_element(By.CSS_SELECTOR, validadas_selector)
                    validadas_text = validadas_element.text.strip()
                    # Extraer números del texto
                    import re
                    numeros = re.findall(r'\d+', validadas_text.replace(',', ''))
                    if numeros:
                        datos['entradas_validadas'] = int(numeros[0])
                        self.logger.info(f"Entradas validadas: {datos['entradas_validadas']}")
                except Exception as e:
                    self.logger.warning(f"No se pudo extraer entradas validadas: {e}")
                    
            return datos
            
        except Exception as e:
            self.logger.error(f"Error extrayendo datos: {e}")
            return {}
            
    def descargar_pdf(self, recinto: str) -> Optional[str]:
        """
        Descargar el PDF del evento
        Args: recinto - nombre del recinto para el nombre del archivo
        Returns: ruta del archivo descargado o None si falla
        """
        try:
            self.logger.info("Iniciando descarga de PDF")
            
            # Solicitar selector del botón/enlace de descarga
            download_selector = input("Selector del botón/enlace para descargar PDF: ").strip()
            if not download_selector:
                self.logger.warning("No se proporcionó selector de descarga")
                return None
                
            download_element = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, download_selector)))
            download_element.click()
            
            self.logger.info("Descarga iniciada, esperando archivo...")
            
            # Esperar a que se descargue el archivo
            time.sleep(5)
            
            # Buscar el archivo más reciente en el directorio de descargas
            downloads = [f for f in os.listdir(self.download_dir) if f.endswith('.pdf')]
            if downloads:
                # Ordenar por fecha de modificación
                downloads.sort(key=lambda x: os.path.getmtime(os.path.join(self.download_dir, x)), reverse=True)
                latest_pdf = downloads[0]
                
                # Renombrar con formato claro
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                new_name = f"{recinto}_{timestamp}.pdf"
                old_path = os.path.join(self.download_dir, latest_pdf)
                new_path = os.path.join(self.download_dir, new_name)
                
                os.rename(old_path, new_path)
                self.logger.info(f"PDF descargado y renombrado: {new_name}")
                return new_path
            else:
                self.logger.error("No se encontró archivo PDF descargado")
                return None
                
        except TimeoutException:
            self.logger.error("Timeout esperando botón de descarga")
            return None
        except Exception as e:
            self.logger.error(f"Error descargando PDF: {e}")
            return None
            
    def login_podio(self) -> bool:
        """
        Realizar login en Podio
        Returns: True si el login es exitoso, False en caso contrario
        """
        try:
            self.logger.info("Iniciando login en Podio")
            
            # Verificar credenciales
            if not self.podio_user or not self.podio_pass:
                self.logger.error("Credenciales de Podio no encontradas en .env")
                return False
                
            # Navegar a Podio
            podio_url = input("Ingresa la URL de login de Podio: ").strip()
            if not podio_url:
                podio_url = "https://podio.com/login"
                
            self.driver.get(podio_url)
            self.logger.info(f"Navegando a: {podio_url}")
            
            # Solicitar selectores
            print("Por favor, indica los selectores de los campos de login en Podio:")
            email_selector = input("Selector del campo email: ").strip()
            if not email_selector:
                email_selector = "input[name='user[mail]'], input[type='email']"
                
            password_selector = input("Selector del campo contraseña: ").strip()
            if not password_selector:
                password_selector = "input[name='user[password]'], input[type='password']"
                
            login_button_selector = input("Selector del botón de login: ").strip()
            if not login_button_selector:
                login_button_selector = "input[type='submit'], button[type='submit']"
            
            # Rellenar formulario
            email_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, email_selector)))
            email_field.clear()
            email_field.send_keys(self.podio_user)
            
            password_field = self.driver.find_element(By.CSS_SELECTOR, password_selector)
            password_field.clear()
            password_field.send_keys(self.podio_pass)
            
            # Hacer clic en login
            login_button = self.driver.find_element(By.CSS_SELECTOR, login_button_selector)
            login_button.click()
            
            time.sleep(3)
            
            # Verificar login exitoso
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                self.logger.info("Login en Podio exitoso")
                return True
            else:
                self.logger.error("Login en Podio falló")
                return False
                
        except Exception as e:
            self.logger.error(f"Error durante login en Podio: {e}")
            return False
            
    def buscar_evento_podio(self, recinto: str) -> bool:
        """
        Buscar el evento en Podio usando el recinto
        Args: recinto - nombre o código del recinto
        Returns: True si encuentra el evento, False en caso contrario
        """
        try:
            self.logger.info(f"Buscando evento en Podio para recinto: {recinto}")
            
            # Navegar al workspace/app correspondiente
            workspace_url = input("Ingresa la URL del workspace/app en Podio: ").strip()
            if workspace_url:
                self.driver.get(workspace_url)
                
            # Buscar el evento
            search_selector = input("Selector del campo de búsqueda en Podio: ").strip()
            if search_selector:
                search_field = self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, search_selector)))
                search_field.clear()
                search_field.send_keys(recinto)
                search_field.send_keys("\n")
                
                time.sleep(3)
                
            # Hacer clic en el resultado
            result_selector = input("Selector del resultado del evento (Enter para continuar): ").strip()
            if result_selector:
                result = self.driver.find_element(By.CSS_SELECTOR, result_selector)
                result.click()
                time.sleep(2)
                
            return True
            
        except Exception as e:
            self.logger.error(f"Error buscando evento en Podio: {e}")
            return False
            
    def rellenar_formulario(self, datos: Dict) -> bool:
        """
        Rellenar el formulario en Podio con los datos extraídos
        Args: datos - diccionario con los datos a rellenar
        Returns: True si se rellena exitosamente, False en caso contrario
        """
        try:
            self.logger.info("Rellenando formulario en Podio")
            
            # Navegar al formulario si es necesario
            form_url = input("URL del formulario (Enter si ya estás ahí): ").strip()
            if form_url:
                self.driver.get(form_url)
                
            print("Proporciona los selectores de los campos del formulario:")
            
            # Campo entradas vendidas
            vendidas_selector = input("Selector campo entradas vendidas: ").strip()
            if vendidas_selector and 'entradas_vendidas' in datos:
                try:
                    vendidas_field = self.driver.find_element(By.CSS_SELECTOR, vendidas_selector)
                    vendidas_field.clear()
                    vendidas_field.send_keys(str(datos['entradas_vendidas']))
                    self.logger.info(f"Campo entradas vendidas rellenado: {datos['entradas_vendidas']}")
                except Exception as e:
                    self.logger.warning(f"Error rellenando entradas vendidas: {e}")
                    
            # Campo entradas validadas
            validadas_selector = input("Selector campo entradas validadas: ").strip()
            if validadas_selector and 'entradas_validadas' in datos:
                try:
                    validadas_field = self.driver.find_element(By.CSS_SELECTOR, validadas_selector)
                    validadas_field.clear()
                    validadas_field.send_keys(str(datos['entradas_validadas']))
                    self.logger.info(f"Campo entradas validadas rellenado: {datos['entradas_validadas']}")
                except Exception as e:
                    self.logger.warning(f"Error rellenando entradas validadas: {e}")
                    
            # Otros campos adicionales
            while True:
                otro_campo = input("¿Hay otro campo que rellenar? (selector o Enter para continuar): ").strip()
                if not otro_campo:
                    break
                    
                valor_campo = input(f"Valor para el campo {otro_campo}: ").strip()
                try:
                    field = self.driver.find_element(By.CSS_SELECTOR, otro_campo)
                    field.clear()
                    field.send_keys(valor_campo)
                    self.logger.info(f"Campo adicional rellenado: {otro_campo} = {valor_campo}")
                except Exception as e:
                    self.logger.warning(f"Error rellenando campo adicional {otro_campo}: {e}")
                    
            return True
            
        except Exception as e:
            self.logger.error(f"Error rellenando formulario: {e}")
            return False
            
    def subir_pdf(self, pdf_path: str) -> bool:
        """
        Subir el PDF descargado al formulario de Podio
        Args: pdf_path - ruta del archivo PDF
        Returns: True si se sube exitosamente, False en caso contrario
        """
        try:
            self.logger.info(f"Subiendo PDF: {pdf_path}")
            
            if not os.path.exists(pdf_path):
                self.logger.error(f"Archivo PDF no encontrado: {pdf_path}")
                return False
                
            # Selector del campo de subida de archivos
            upload_selector = input("Selector del campo de subida de archivos: ").strip()
            if not upload_selector:
                upload_selector = "input[type='file']"
                
            upload_field = self.driver.find_element(By.CSS_SELECTOR, upload_selector)
            upload_field.send_keys(pdf_path)
            
            # Esperar a que se suba el archivo
            time.sleep(5)
            
            self.logger.info("PDF subido exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error subiendo PDF: {e}")
            return False
            
    def enviar_formulario(self) -> bool:
        """
        Enviar el formulario completado
        Returns: True si se envía exitosamente, False en caso contrario
        """
        try:
            self.logger.info("Enviando formulario")
            
            submit_selector = input("Selector del botón de envío: ").strip()
            if not submit_selector:
                submit_selector = "button[type='submit'], input[type='submit']"
                
            submit_button = self.driver.find_element(By.CSS_SELECTOR, submit_selector)
            submit_button.click()
            
            time.sleep(3)
            
            self.logger.info("Formulario enviado exitosamente")
            return True
            
        except Exception as e:
            self.logger.error(f"Error enviando formulario: {e}")
            return False
            
    def guardar_datos_json(self, datos: Dict, recinto: str):
        """Guardar datos extraídos en archivo JSON"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"datos_{recinto}_{timestamp}.json"
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(datos, f, indent=2, ensure_ascii=False)
                
            self.logger.info(f"Datos guardados en JSON: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error guardando datos JSON: {e}")
            
    def guardar_datos_csv(self, datos: Dict, recinto: str):
        """Guardar datos extraídos en archivo CSV"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"datos_{recinto}_{timestamp}.csv"
            
            df = pd.DataFrame([datos])
            df.to_csv(filename, index=False, encoding='utf-8')
            
            self.logger.info(f"Datos guardados en CSV: {filename}")
            
        except Exception as e:
            self.logger.error(f"Error guardando datos CSV: {e}")
            
    def cerrar_navegador(self):
        """Cerrar el navegador"""
        if self.driver:
            self.driver.quit()
            self.logger.info("Navegador cerrado")
            
    def ejecutar_flujo_completo(self):
        """Ejecutar el flujo completo de automatización"""
        try:
            # Solicitar recinto al usuario
            recinto = input("Ingresa el nombre o código exacto del recinto: ").strip()
            if not recinto:
                self.logger.error("Recinto no proporcionado")
                return
                
            self.logger.info(f"Iniciando flujo completo para recinto: {recinto}")
            
            # 1. Login en Ticketmaster
            if not self.login_ticketmaster():
                self.logger.error("Falló el login en Ticketmaster. Abortando.")
                return
                
            # 2. Buscar evento
            if not self.buscar_evento(recinto):
                self.logger.warning("No se encontró el evento, pero continuando...")
                
            # 3. Extraer datos
            datos = self.extraer_datos()
            if datos:
                # Guardar datos en JSON y CSV
                self.guardar_datos_json(datos, recinto)
                self.guardar_datos_csv(datos, recinto)
                
            # 4. Descargar PDF
            pdf_path = self.descargar_pdf(recinto)
            
            # 5. Login en Podio
            if not self.login_podio():
                self.logger.error("Falló el login en Podio. Abortando.")
                return
                
            # 6. Buscar evento en Podio
            if not self.buscar_evento_podio(recinto):
                self.logger.warning("No se encontró el evento en Podio, pero continuando...")
                
            # 7. Rellenar formulario
            if datos and self.rellenar_formulario(datos):
                # 8. Subir PDF si se descargó
                if pdf_path and self.subir_pdf(pdf_path):
                    # 9. Enviar formulario
                    self.enviar_formulario()
                    
            self.logger.info("Flujo completo ejecutado")
            
        except KeyboardInterrupt:
            self.logger.info("Proceso interrumpido por el usuario")
        except Exception as e:
            self.logger.error(f"Error en flujo completo: {e}")
        finally:
            input("Presiona Enter para cerrar el navegador...")
            self.cerrar_navegador()

def main():
    """Función principal"""
    print("=== AUTOMATIZACIÓN TICKETMASTER - PODIO ===")
    print("Asegúrate de tener configurado el archivo .env con las credenciales")
    print("TICKETMASTER_USER, TICKETMASTER_PASS, PODIO_USER, PODIO_PASS")
    print()
    
    automation = TicketmasterPodioAutomation()
    automation.ejecutar_flujo_completo()

if __name__ == "__main__":
    main()