import os
import tempfile

APP_NAME = "PWA Simulator"
APP_VERSION = "1.0.0"
APP_ID = "alejandro.herramientas.pwasimulator.v1"

# Window dimensions
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 700
WEBVIEW_WIDTH = 1024
WEBVIEW_HEIGHT = 768

# Colors (Modern Deep Navy / Glassmorphic)
BG_COLOR = "#0C0E14"
BG_SECONDARY = "#121520"
BG_TERTIARY = "#181D2A"
BORDER_COLOR = "#222738"
ACCENT_COLOR = "#0284C7"
ACCENT_HOVER = "#0369A1"
TEXT_COLOR = "#F8FAFC"
TEXT_SECONDARY = "#94A3B8"
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
PROFILE_DIR = os.path.join(BASE_DIR, "browser_profile")
URLS_DIR = os.path.join(BASE_DIR, "URLS")
MAX_HISTORY = 10

# Ensure directories exist
os.makedirs(ICON_CACHE_DIR, exist_ok=True)
os.makedirs(PROFILE_DIR, exist_ok=True)
os.makedirs(URLS_DIR, exist_ok=True)
