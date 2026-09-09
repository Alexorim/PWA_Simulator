"""
main.py - Punto de entrada de PWA Simulator
"""
import sys
import ctypes

# 1. Si es invocado como runner de ventana PWA (tanto en script como en exe compilado)
if len(sys.argv) >= 3 and sys.argv[1] == "--pwa-runner":
    from pwa_runner import run_from_config_file
    run_from_config_file(sys.argv[2])
    sys.exit(0)

# 2. Inicializar AppUserModelID en Windows para icono agrupado en barra de tareas
if sys.platform == "win32":
    try:
        from config import APP_ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

# 3. Exportar variables compatibles con Vercel Serverless Function (evita errores en Vercel CLI)
def handler(environ_or_request=None, start_response=None, *args, **kwargs):
    if callable(start_response):
        status = '302 Found'
        response_headers = [('Location', '/index.html')]
        start_response(status, response_headers)
        return [b'Redirecting to web UI...']
    return {
        'statusCode': 302,
        'headers': {'Location': '/index.html'},
        'body': 'Redirecting to web UI...'
    }

app = handler
application = handler

def main():
    from gui import PWASimulatorApp
    gui_app = PWASimulatorApp()
    gui_app.mainloop()

if __name__ == "__main__":
    main()
