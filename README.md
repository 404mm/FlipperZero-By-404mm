# Automatización Ticketmaster - Podio

Script de automatización en Python con Selenium que automatiza el flujo de extracción de datos de eventos desde Ticketmaster y actualización de formularios en Podio.

## 🚀 Características

- **Login automatizado** en Ticketmaster y Podio
- **Búsqueda de eventos** por recinto/código
- **Extracción de datos** (entradas vendidas, validadas)
- **Descarga automática** de PDFs
- **Rellenado de formularios** en Podio
- **Subida de archivos** PDF
- **Logging completo** de todas las operaciones
- **Gestión de errores** robusta
- **Navegador visible** para seguimiento del proceso

## 📋 Requisitos

### Software necesario:
- Python 3.8+
- Google Chrome
- ChromeDriver

### Dependencias Python:
```bash
pip install -r requirements.txt
```

## ⚙️ Configuración

1. **Clonar/descargar** los archivos del proyecto

2. **Instalar dependencias:**
   ```bash
   pip install selenium python-dotenv pandas
   ```

3. **Configurar credenciales:**
   - Copia `.env.example` a `.env`
   - Completa con tus credenciales reales:
   ```
   TICKETMASTER_USER=tu_email@ejemplo.com
   TICKETMASTER_PASS=tu_contraseña
   PODIO_USER=tu_email@ejemplo.com  
   PODIO_PASS=tu_contraseña
   ```

4. **ChromeDriver:**
   - Asegúrate de tener Chrome instalado
   - Descarga ChromeDriver desde https://chromedriver.chromium.org/
   - Colócalo en tu PATH o en la carpeta del proyecto

## 🎯 Uso

### Ejecución básica:
```bash
python ticketmaster_automation.py
```

### Flujo de ejecución:

1. **Inicio:** El script te pedirá el nombre/código del recinto
2. **Ticketmaster:** Login automático y búsqueda del evento
3. **Extracción:** Obtiene datos de entradas vendidas/validadas
4. **Descarga:** Descarga el PDF del evento
5. **Podio:** Login y búsqueda del evento correspondiente
6. **Formulario:** Rellena campos con los datos extraídos
7. **Subida:** Sube el PDF descargado
8. **Envío:** Envía el formulario completado

### Interacción durante la ejecución:

El script te preguntará por selectores CSS cuando sea necesario:
- Campos de login
- Botones de búsqueda
- Campos de datos
- Botones de descarga
- Campos de formulario

## 📁 Estructura de archivos

```
proyecto/
├── ticketmaster_automation.py  # Script principal
├── requirements.txt            # Dependencias
├── .env.example               # Plantilla de configuración
├── .env                       # Credenciales (crear manualmente)
├── downloads/                 # PDFs descargados
├── datos_*.json              # Datos extraídos (JSON)
├── datos_*.csv               # Datos extraídos (CSV)
└── automation_*.log          # Logs de ejecución
```

## 📊 Datos extraídos

El script extrae y guarda:
- **Entradas vendidas totales**
- **Entradas validadas/entrada real**
- **Fecha y hora de extracción**
- **PDF del evento**

Los datos se guardan en formatos JSON y CSV con timestamp.

## 🔧 Personalización

### Modificar selectores:
Si los selectores cambian, puedes:
1. Ejecutar el script y proporcionar nuevos selectores cuando se soliciten
2. Modificar los valores por defecto en el código

### Añadir campos:
Para extraer datos adicionales, modifica la función `extraer_datos()` y añade los selectores correspondientes.

### Cambiar configuración:
- Directorio de descargas: modifica `self.download_dir`
- Timeouts: ajusta `WebDriverWait(self.driver, 10)`
- Opciones de Chrome: modifica `chrome_options`

## 🐛 Solución de problemas

### Errores comunes:

1. **ChromeDriver no encontrado:**
   - Descarga ChromeDriver compatible con tu versión de Chrome
   - Asegúrate de que esté en el PATH

2. **Credenciales incorrectas:**
   - Verifica el archivo `.env`
   - Comprueba que las credenciales sean válidas

3. **Selectores no encontrados:**
   - Las páginas web pueden cambiar
   - Proporciona nuevos selectores cuando se soliciten
   - Usa las herramientas de desarrollador de Chrome

4. **Timeout en elementos:**
   - Aumenta el tiempo de espera en `WebDriverWait`
   - Verifica que la página esté cargando correctamente

### Logs:
Revisa los archivos `automation_*.log` para información detallada sobre errores.

## ⚠️ Consideraciones importantes

- **Términos de servicio:** Asegúrate de cumplir con los TOS de ambas plataformas
- **Rate limiting:** El script incluye delays para evitar sobrecargar los servidores
- **Credenciales:** Nunca compartas tu archivo `.env`
- **Actualizaciones:** Las páginas web pueden cambiar, requiriendo ajustes en selectores

## 📝 Logging

Cada ejecución genera un log detallado con:
- Timestamp de cada operación
- Errores y warnings
- Datos extraídos
- Estado de cada paso del proceso

Los logs se guardan en archivos con formato: `automation_YYYYMMDD_HHMMSS.log`

## 🤝 Soporte

Si encuentras problemas:
1. Revisa los logs de error
2. Verifica que Chrome y ChromeDriver estén actualizados
3. Comprueba que los selectores CSS sigan siendo válidos
4. Asegúrate de que las credenciales sean correctas

---

**Nota:** Este script está diseñado para ser interactivo y adaptable. Te preguntará por los selectores específicos de tu entorno, por lo que no necesitas conocimientos técnicos avanzados para usarlo.