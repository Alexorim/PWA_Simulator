# DEVELOPMENT RULES — PWA Simulator

> Estas reglas son obligatorias salvo que el propietario del proyecto autorice explícitamente una excepción.

## 1. Regla Fundamental
ANTES DE MODIFICAR EL CÓDIGO:
1. Analizar la tarea.
2. Identificar archivos afectados.
3. Revisar componentes relacionados.
4. Revisar dependencias.
5. Revisar docs/PROJECT_CONTEXT.md.
6. Identificar posibles efectos secundarios.
7. Proponer el enfoque cuando la modificación sea importante.

## 2. Reglas de Modificación
- **Regla 1 — No reconstruir innecesariamente**: Modificaciones quirúrgicas y localizadas. No reescribir módulos enteros si la tarea concierne a una función o evento puntual.
- **Regla 2 — Reutilización**: Verificar componentes y utilidades existentes (`config.py`, `history.py`, `favicon_extractor.py`) antes de duplicar lógica.
- **Regla 3 — No romper funcionalidades existentes**: Preservar contratos, atajos de teclado (`F11`, `Ctrl+`, `Ctrl-`), persistencia de perfiles y compatibilidad con accesos directos.
- **Regla 4 — No cambiar tecnologías sin autorización**: Mantener estrictamente el stack de Python 3.12, CustomTkinter, `pywebview` (Edge WebView2) y Pillow.
- **Regla 5 — Dependencias mínimas**: Priorizar paquetes ya instalados y runtime nativo de Windows (WebView2, VBScript WScript) para evitar inflar el ejecutable portable.
- **Regla 6 — Estabilidad de Rutas y Archivos**: Mantener rutas locales relativas a `BASE_DIR` (`history.json`, `browser_profile/`, `URLS/`, `assets/`).
- **Regla 7 — Integridad de Datos y Perfiles**: Operaciones no destructivas en `history.json` y manipulación no invasiva (copia temporal) de la base de datos de cookies de Chromium.
- **Regla 8 — Seguridad Estricta**: Cero credenciales o contraseñas en código o registros. Delegar la autenticación de terceros exclusivamente en el contenedor de Chromium.
- **Regla 9 — Gestión de Procesos y Concurrencia**: Detener instancias previas bloqueantes antes de tareas de compilación y asegurar que los hilos secundarios usen `daemon=True`.
- **Regla 10 — Consistencia UI/UX**: Respetar la paleta de colores Deep Navy (`#0C0E14`), estética de botones macOS circulares (12px, estáticos) y estilos CSS inyectados.

## 3. Reglas de Calidad
- Tipado estricto en funciones de persistencia y configuración.
- Manejo defensivo de excepciones (`try/except`) al interactuar con el sistema de ventanas del SO, APIs de archivos y sockets de red.
- Compatibilidad comprobada tanto en ejecución directa con Python (`python main.py`) como en versión empaquetada (`PWASimulator.exe`).
- Separación limpia de responsabilidades entre el lanzador gráfico (`gui.py`) y el motor de ejecución web (`pwa_runner.py`).

## 4. Reglas para Agentes de IA
1. Comprender la solicitud.
2. Inspeccionar únicamente lo necesario (evitar escaneos masivos de directorios completos o archivos binarios).
3. Consultar `PROJECT_CONTEXT.md` y `DEVELOPMENT_RULES.md`.
4. Delimitar la edición quirúrgica a las líneas exactas.
5. Implementar el cambio sin reescrituras innecesarias.
6. Verificar compilación y no regresión mediante pruebas en consola o comprobación de handles.
7. Actualizar la sección 'Última actualización' de `PROJECT_CONTEXT.md` si hubo cambios de arquitectura, modelo o diseño de ventana.
