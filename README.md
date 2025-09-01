## Automatización Ticketmaster → Podio (Selenium)

Script en Python que automatiza:
- Login en Ticketmaster, búsqueda de evento por recinto, extracción de métricas y descarga de PDF.
- Login en Podio, localización del formulario del evento, completado de campos y subida del PDF.

El navegador se abre en modo visible (no headless). El script pregunta por consola los selectores o URLs que falten.

### Requisitos

- Python 3.9+
- Drivers del navegador en el PATH (por ejemplo, `chromedriver` o `geckodriver`). Si no los tienes, el script te pedirá la ruta al ejecutable del driver.

### Instalación

```bash
pip install -r requirements.txt
```

O bien (requerido por el enunciado):

```bash
pip install selenium python-dotenv pandas
```

### Configuración

1) Copia `.env.example` a `.env` y completa las credenciales:

```
TICKETMASTER_USER=tu_usuario
TICKETMASTER_PASS=tu_password
PODIO_USER=tu_usuario
PODIO_PASS=tu_password
```

2) (Opcional) Prepara una carpeta de descargas si quieres una ruta concreta. El script creará `downloads/` y `logs/` si no existen.

### Uso

```bash
python main.py
```

El script te pedirá por consola:
- Recinto/código exacto del evento a buscar en Ticketmaster
- Selectores/URLs que falten para Ticketmaster y Podio
- Selectores para descarga del PDF y para los campos del formulario de Podio

### Salidas

- Archivos JSON y CSV con las métricas extraídas en `data/`
- PDF renombrado como `recinto_fecha.pdf` en `downloads/`
- Log por ejecución en `logs/run_YYYYmmdd_HHMMSS.log`

### Notas

- Si el evento no se encuentra, se informa por consola y en el log y se continúa con Podio.
- Si la descarga del PDF falla, verás un error claro en consola y log.
- El script está modularizado con funciones: `login_ticketmaster`, `buscar_evento`, `extraer_datos`, `descargar_pdf`, `login_podio`, `rellenar_formulario`, `subir_pdf`.
📡 Flipper Zero Projects by 404mm

¡Bienvenido a mi repositorio de proyectos, scripts y aprendizajes con Flipper Zero! 🐬

🚀 Sobre este repositorio

Este espacio es donde iré subiendo mis scripts personalizados y todo lo que vaya aprendiendo mientras exploro y experimento con Flipper Zero, un dispositivo versátil para hacking, experimentación y automatización.

📂 Contenido

- Scripts personalizados: Herramientas, automatizaciones y exploits para Flipper Zero.

- Guías y tutoriales: Mis apuntes y procesos al aprender cosas nuevas.

- Proyectos: Creaciones completas usando Flipper Zero, incluyendo compilaciones de apps y otros experimentos.

- Recursos útiles: Enlaces, documentación y trucos que me han servido en el camino.

🛠 Herramientas y configuraciones

- Flipper Zero como dispositivo principal.
- Kali Linux en mi portátil para desarrollo, testing y compilación.
- VS Code para editar scripts y código.
- Python, Bash, y C para la mayoría de mis scripts.
