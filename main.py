"""
main.py - Punto de entrada de PWA Simulator
"""
import sys
import ctypes

# Si es invocado como runner de ventana PWA (tanto en script como en exe compilado)
if len(sys.argv) >= 3 and sys.argv[1] == "--pwa-runner":
    from pwa_runner import run_from_config_file
    run_from_config_file(sys.argv[2])
    sys.exit(0)

# Inicializar AppUserModelID en Windows para icono agrupado en barra de tareas
if sys.platform == "win32":
    try:
        from config import APP_ID
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass

from gui import PWASimulatorApp

def main():
    app = PWASimulatorApp()
    app.mainloop()

if __name__ == "__main__":
    main()
