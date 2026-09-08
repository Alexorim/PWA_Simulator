# PWA Simulator

Simulador de Progressive Web Apps para escritorio. Permite abrir cualquier sitio web como si fuera una aplicación PWA nativa.

## Características

- **Detección automática de PWA**: Si el sitio tiene un manifest PWA real, lo usa automáticamente
- **Simulación inteligente**: Para sitios sin PWA, genera una experiencia PWA simulada
- **Vista standalone**: Muestra el sitio sin barra de URL ni controles de navegador
- **Extracción de íconos**: Detecta y usa favicons/íconos del sitio automáticamente
- **Historial**: Guarda las últimas URLs visitadas para acceso rápido
- **Tema oscuro**: Interfaz moderna con fondo negro

## Requisitos

- Python 3.9+
- Windows 10/11 (con WebView2 runtime, incluido por defecto en Windows 11)

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
python main.py
```

O usar el acceso directo / `iniciar.bat`.

## Compilar a .exe

```bash
compilar_exe.bat
```

## Tecnologías

- **CustomTkinter** - Interfaz gráfica moderna
- **pywebview** - Motor de renderizado web (Edge WebView2)
- **BeautifulSoup** - Parsing de HTML para detección de manifest
- **Pillow** - Procesamiento de íconos
- **requests** - Peticiones HTTP

## Estructura

```
PWASimulator/
├── main.py                # Punto de entrada
├── gui.py                 # Interfaz de inicio
├── pwa_detector.py        # Detección de manifest PWA
├── pwa_simulator.py       # Simulación de PWA
├── webview_manager.py     # Gestión de ventana WebView
├── favicon_extractor.py   # Extracción de íconos
├── config.py              # Configuración
├── history.py             # Historial de URLs
└── assets/
    └── logo.png           # Logo de la app
```
