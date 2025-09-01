# Automatización Ticketmaster-Podio

Script de automatización con Selenium para extraer datos de eventos desde Ticketmaster y registrarlos en Podio.

## Características

- ✅ Login automático en Ticketmaster y Podio
- ✅ Búsqueda de eventos por recinto
- ✅ Extracción de datos (entradas vendidas, validadas, etc.)
- ✅ Descarga de PDF del evento
- ✅ Registro automático en formulario de Podio
- ✅ Sistema de logging completo
- ✅ Manejo de errores robusto
- ✅ Interacción por consola para selectores desconocidos

## Requisitos

- Python 3.8+
- Google Chrome instalado
- ChromeDriver (se instala automáticamente con webdriver-manager)

## Instalación

1. Clonar o descargar este repositorio
2. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

3. Configurar credenciales:
   - Copiar `.env.example` a `.env`
   - Editar `.env` con tus credenciales reales:
   ```
   TICKETMASTER_USER=tu_usuario
   TICKETMASTER_PASS=tu_contraseña
   PODIO_USER=tu_usuario
   PODIO_PASS=tu_contraseña
   ```

## Uso

Ejecutar el script:
```bash
python ticketmaster_podio_automation.py
```

El script te pedirá:
1. **Nombre o código del recinto**: Ingresa el identificador exacto del evento
2. **Selectores CSS**: El script preguntará por los selectores de cada elemento según sea necesario

### Flujo del Script

1. **Login en Ticketmaster**
   - Solicita URL de login
   - Pide selectores para campos de usuario/contraseña
   - Realiza login automático

2. **Búsqueda de Evento**
   - Busca el evento por el recinto proporcionado
   - Soporta búsqueda por campo, lista o URL directa

3. **Extracción de Datos**
   - Extrae entradas vendidas totales
   - Extrae entradas validadas/entrada real
   - Permite extraer campos adicionales
   - Guarda datos en JSON y CSV

4. **Descarga de PDF**
   - Descarga el PDF del evento
   - Renombra con formato: `recinto_fecha.pdf`

5. **Login en Podio**
   - Similar al login de Ticketmaster

6. **Registro en Podio**
   - Busca el evento en Podio
   - Rellena formulario con datos extraídos
   - Sube el PDF descargado
   - Envía el formulario

## Estructura de Archivos

```
proyecto/
├── ticketmaster_podio_automation.py  # Script principal
├── .env                              # Credenciales (no incluir en git)
├── .env.example                      # Ejemplo de credenciales
├── requirements.txt                  # Dependencias
├── README.md                         # Esta documentación
├── logs/                            # Logs de ejecución
│   └── automation_YYYYMMDD_HHMMSS.log
├── data/                            # Datos extraídos
│   ├── recinto_YYYYMMDD_HHMMSS.json
│   └── recinto_YYYYMMDD_HHMMSS.csv
└── downloads/                       # PDFs descargados
    └── recinto_YYYYMMDD_HHMMSS.pdf
```

## Características Técnicas

### Logging
- Logs detallados en consola y archivo
- Formato: `fecha - nivel - función - mensaje`
- Un archivo de log por ejecución

### Manejo de Errores
- Try-catch en todas las operaciones críticas
- Continúa el flujo cuando es posible
- Mensajes claros de error

### Modularidad
- Funciones separadas para cada operación
- Fácil mantenimiento y extensión
- Código comentado

### Interactividad
- Solicita información cuando no conoce selectores
- Permite diferentes métodos de búsqueda
- Confirmación visual (navegador no headless)

## Personalización

### Agregar Nuevos Campos
En la función `extraer_datos()`, el script pregunta si hay más campos que extraer. Simplemente:
1. Indica el nombre del campo
2. Proporciona el selector CSS
3. El dato se guardará automáticamente

### Timeouts
Puedes ajustar los tiempos de espera modificando:
- `timeout` en `wait_and_find_element()` (default: 10 segundos)
- `sleep()` después de acciones importantes

### Selectores Comunes
Ejemplos de selectores CSS que podrías necesitar:
- ID: `#elementId`
- Clase: `.className`
- Atributo: `[name="fieldName"]`
- Combinado: `div.container input[type="text"]`

## Solución de Problemas

### El script no encuentra un elemento
- Verifica que el selector CSS sea correcto
- Aumenta el timeout si la página carga lento
- Asegúrate de estar en la página correcta

### Error de descarga de PDF
- Verifica permisos en la carpeta `downloads/`
- Algunos sitios requieren tiempo extra para generar PDFs

### Login falla
- Verifica credenciales en `.env`
- Algunos sitios tienen captcha o 2FA

## Notas de Seguridad

- **NUNCA** compartir el archivo `.env` con credenciales reales
- Usar este script solo en sitios donde tengas autorización
- Las credenciales se cargan de forma segura desde variables de entorno

## Soporte

Si encuentras problemas:
1. Revisa los logs en `logs/`
2. Verifica que los selectores CSS sean correctos
3. Asegúrate de tener las últimas versiones de las dependencias