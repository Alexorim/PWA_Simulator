import os
import tempfile

APP_NAME = "PWA Simulator"
APP_VERSION = "1.0.0"
APP_ID = "alejandro.herramientas.pwasimulator.v1"

# Window dimensions
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 600
WEBVIEW_WIDTH = 1024
WEBVIEW_HEIGHT = 768

# Colors
BG_COLOR = "#0D0D0D"
BG_SECONDARY = "#1A1A1A"
BG_TERTIARY = "#2A2A2A"
ACCENT_COLOR = "#3B82F6"
ACCENT_HOVER = "#2563EB"
TEXT_COLOR = "#FFFFFF"
TEXT_SECONDARY = "#9CA3AF"
ERROR_COLOR = "#EF4444"
SUCCESS_COLOR = "#22C55E"
WARNING_COLOR = "#F59E0B"

# Network
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 10

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICON_CACHE_DIR = os.path.join(tempfile.gettempdir(), "pwa_simulator", "icons")
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
MAX_HISTORY = 10

# Ensure cache directory exists
os.makedirs(ICON_CACHE_DIR, exist_ok=True)
