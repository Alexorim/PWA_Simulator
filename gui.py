"""
gui.py - Interfaz gráfica moderna para PWA Simulator en CustomTkinter
Incluye fondo de Red Neuronal animada en Tkinter Canvas, animación en el Logo,
botón de instalación rápida (Acceso directo PWA en Windows) en cada elemento del historial,
y visor embebido con menú flotante de controles y herramientas de desarrollo.
"""
import os
import sys
import math
import random
import threading
from urllib.parse import urlparse
from typing import Optional

import customtkinter as ctk
import tkinter as tk
from PIL import Image

from config import (
    APP_NAME, APP_VERSION, WINDOW_WIDTH, WINDOW_HEIGHT,
    BG_COLOR, BG_SECONDARY, BG_TERTIARY, BORDER_COLOR, ACCENT_COLOR, ACCENT_HOVER,
    TEXT_COLOR, TEXT_SECONDARY, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR
)
from history import get_history, add_entry, remove_entry, clear_history
from pwa_detector import detect_pwa
from pwa_simulator import simulate_pwa, merge_manifest
from webview_manager import open_as_pwa, open_google_login, open_google_logout
from favicon_extractor import get_best_icon, favicon_fallback
from google_auth import is_google_logged_in, clear_browser_profile
from quick_access import save_quick_access, sync_existing_history, create_desktop_shortcut

ctk.set_appearance_mode('Dark')
ctk.set_default_color_theme('blue')

class PWASimulatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} v{APP_VERSION}")

        # Centrar ventana en pantalla
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = max(0, (screen_width - WINDOW_WIDTH) // 2)
        y = max(0, (screen_height - WINDOW_HEIGHT) // 2)
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+{x}+{y}")

        self.configure(fg_color=BG_COLOR)
        self.minsize(780, 580)
        self.resizable(True, True)

        # Variables de ventana y zoom
        self.zoom_level = 1.0
        self._is_maximized = False

        # Configurar icono de ventana
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Traer la ventana al frente con foco en la barra de tareas
        self.lift()
        self.attributes('-topmost', True)
        self.after_idle(lambda: self.attributes('-topmost', False))
        self.focus_force()

        # Configurar ventana frameless en Windows (sin marco nativo)
        self.after(30, self._setup_frameless_window)

        # Variables para animación de red neuronal y vista de historial
        self.nodes = []
        self.anim_running = True
        self.logo_angle = 0
        self.logo_pulse = 0
        self.history_view_mode = "list"
        self._icon_cache = {}
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._win_start_x = 0
        self._win_start_y = 0

        self._create_top_bar()
        self._setup_background_canvas()
        self._create_widgets()
        self._init_neural_network()
        self._start_animations()
        self._refresh_google_status()
        threading.Thread(target=sync_existing_history, daemon=True).start()

        # Atajos de teclado para Zoom y Ventana
        self.bind("<Control-plus>", self._zoom_in)
        self.bind("<Control-equal>", self._zoom_in)
        self.bind("<Control-minus>", self._zoom_out)
        self.bind("<Control-0>", self._zoom_reset)
        self.bind("<F11>", lambda e: self._toggle_maximize())

        # Optimización de CPU: Pausar animaciones en minimizado o segundo plano
        self.bind("<Unmap>", self._on_window_unmap)
        self.bind("<Map>", self._on_window_map)

    def _setup_frameless_window(self):
        """Elimina la barra de título nativa de Windows (frameless) manteniendo la barra de tareas."""
        try:
            import ctypes
            self.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            if hwnd == 0:
                hwnd = self.winfo_id()
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style & ~WS_CAPTION)
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER)
        except Exception:
            pass

    def _create_top_bar(self):
        """Barra de título superior moderna frameless con botones de macOS a la izquierda."""
        self.top_bar = ctk.CTkFrame(self, height=36, fg_color="#080A0F", corner_radius=0)
        self.top_bar.pack(side="top", fill="x")
        self.top_bar.pack_propagate(False)

        # 1. Tres punticos estilo macOS en el extremo izquierdo
        self.macos_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent", height=36)
        self.macos_frame.pack(side="left", padx=(14, 10), pady=0)

        # Botón Rojo (Cerrar)
        self.btn_mac_close = ctk.CTkButton(
            self.macos_frame,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#ff5f56",
            hover_color="#e0443e",
            font=("Segoe UI", 8, "bold"),
            text_color="#450A0A",
            command=self.destroy
        )
        self.btn_mac_close.pack(side="left", padx=(0, 8))

        # Botón Amarillo (Minimizar)
        self.btn_mac_min = ctk.CTkButton(
            self.macos_frame,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#ffbd2e",
            hover_color="#dea123",
            font=("Segoe UI", 9, "bold"),
            text_color="#451A03",
            command=self._minimize_window
        )
        self.btn_mac_min.pack(side="left", padx=(0, 8))

        # Botón Verde (Maximizar / Pantalla completa)
        self.btn_mac_max = ctk.CTkButton(
            self.macos_frame,
            text="",
            width=12,
            height=12,
            corner_radius=6,
            fg_color="#27c93f",
            hover_color="#1aab29",
            font=("Segoe UI", 8, "bold"),
            text_color="#052E16",
            command=self._toggle_maximize
        )
        self.btn_mac_max.pack(side="left")

        # 2. Menús a la izquierda (después de los punticos)
        self.top_left = ctk.CTkFrame(self.top_bar, fg_color="transparent", height=36)
        self.top_left.pack(side="left", padx=(4, 8), pady=0)

        # Botón PWASimulator con versión visible
        self.btn_app_version = ctk.CTkButton(
            self.top_left,
            text=f"⚡ PWASimulator v{APP_VERSION}",
            font=("Segoe UI", 11, "bold"),
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#181D2A",
            text_color="#E2E8F0",
            command=self._show_about_menu
        )
        self.btn_app_version.pack(side="left", padx=(0, 2))

        # Menú Ajustes
        self.btn_settings = ctk.CTkButton(
            self.top_left,
            text="Ajustes",
            font=("Segoe UI", 11),
            width=65,
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#181D2A",
            text_color="#94A3B8",
            command=self._show_settings_menu
        )
        self.btn_settings.pack(side="left", padx=(0, 2))

        # Menú Ventana
        self.btn_window = ctk.CTkButton(
            self.top_left,
            text="Ventana",
            font=("Segoe UI", 11),
            width=65,
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#181D2A",
            text_color="#94A3B8",
            command=self._show_window_menu
        )
        self.btn_window.pack(side="left", padx=(0, 2))

        # Menú Vista
        self.btn_view = ctk.CTkButton(
            self.top_left,
            text="Vista",
            font=("Segoe UI", 11),
            width=55,
            height=26,
            corner_radius=6,
            fg_color="transparent",
            hover_color="#181D2A",
            text_color="#94A3B8",
            command=self._show_view_menu
        )
        self.btn_view.pack(side="left")

        # 3. Región central arrastrable (Drag Region)
        self.drag_area = ctk.CTkFrame(self.top_bar, fg_color="transparent", height=36)
        self.drag_area.pack(side="left", fill="both", expand=True)
        self.drag_area.pack_propagate(False)

        # 4. Extremo derecho: Badge de estado limpio
        self.top_right = ctk.CTkFrame(self.top_bar, fg_color="transparent", height=36)
        self.top_right.pack(side="right", padx=12, pady=0)
        self.badge_status = ctk.CTkLabel(
            self.top_right,
            text="🟢 PWA Engine",
            font=("Segoe UI", 10),
            text_color="#38BDF8"
        )
        self.badge_status.pack(side="right")

        # Vincular arrastre en toda la barra superior para mover la ventana sin esfuerzo
        for w in (self.top_bar, self.drag_area, self.top_right, self.badge_status):
            self._bind_drag_widget(w)

    def _bind_drag_widget(self, widget):
        """Asigna los eventos de arrastre tanto al widget contenedor como a su canvas interno si existe."""
        widget.bind("<Button-1>", self._start_move)
        widget.bind("<B1-Motion>", self._on_move)
        widget.bind("<Double-Button-1>", self._toggle_maximize)
        if hasattr(widget, "_canvas") and widget._canvas:
            widget._canvas.bind("<Button-1>", self._start_move)
            widget._canvas.bind("<B1-Motion>", self._on_move)
            widget._canvas.bind("<Double-Button-1>", self._toggle_maximize)

    def _setup_background_canvas(self):
        """Crea el canvas de fondo para la red neuronal interactiva."""
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.canvas.place(x=0, y=34, relwidth=1, relheight=1)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, event):
        self.canvas_width = event.width
        self.canvas_height = event.height

    def _create_widgets(self):
        # Contenedor principal superpuesto sobre el canvas
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(expand=True, fill="both", padx=28, pady=(4, 6))

        # 1. Logo animado y Título (bien arriba, protagonista y ultra nítido)
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", pady=(2, 4))

        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            try:
                self.pil_logo = Image.open(logo_path).convert("RGBA")
                # Redimensionar con algoritmo LANCZOS para máxima nitidez y definición
                crisp_logo = self.pil_logo.resize((96, 96), Image.Resampling.LANCZOS)
                self.logo_img = ctk.CTkImage(light_image=crisp_logo, dark_image=crisp_logo, size=(96, 96))
                self.logo_label = ctk.CTkLabel(self.header_frame, image=self.logo_img, text="")
            except Exception:
                self.pil_logo = None
                self.logo_label = ctk.CTkLabel(self.header_frame, text="⚡", font=("Segoe UI", 48))
        else:
            self.pil_logo = None
            self.logo_label = ctk.CTkLabel(self.header_frame, text="⚡", font=("Segoe UI", 48))

        self.logo_label.pack(anchor="center")

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="PWA SIMULATOR",
            font=("Segoe UI", 24, "bold"),
            text_color=TEXT_COLOR
        )
        self.title_label.pack(anchor="center", pady=(3, 1))

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Simula, instala y ejecuta cualquier sitio web en modo Progressive Web App",
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY
        )
        self.subtitle_label.pack(anchor="center", pady=(0, 4))

        # 2. Entrada de URL estilo Glassmorphism unificado
        self.input_card = ctk.CTkFrame(
            self.main_container,
            fg_color=BG_SECONDARY,
            corner_radius=18,
            border_width=1,
            border_color=BORDER_COLOR
        )
        self.input_card.pack(side="top", fill="x", padx=20, pady=(2, 6))

        self.input_inner = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.input_inner.pack(fill="x", padx=10, pady=6)

        self.url_icon = ctk.CTkLabel(self.input_inner, text="🌐", font=("Segoe UI", 15), text_color=TEXT_SECONDARY)
        self.url_icon.pack(side="left", padx=(4, 8))

        self.url_entry = ctk.CTkEntry(
            self.input_inner,
            placeholder_text="https://ejemplo.com o ingresa una dirección...",
            placeholder_text_color="#64748B",
            height=40,
            corner_radius=10,
            font=("Segoe UI", 13),
            border_width=0,
            fg_color="#090C14",
            text_color=TEXT_COLOR
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", self._on_submit)
        self.url_entry.focus_set()

        self.submit_btn = ctk.CTkButton(
            self.input_inner,
            text="Abrir PWA",
            font=("Segoe UI", 13, "bold"),
            width=120,
            height=40,
            corner_radius=14,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            command=self._on_submit
        )
        self.submit_btn.pack(side="right")

        # 2.5 Banner de Cuenta Google
        self.google_card = ctk.CTkFrame(
            self.main_container,
            fg_color="#10131E",
            corner_radius=12,
            border_width=1,
            border_color="#1E2336"
        )
        self.google_card.pack(side="top", fill="x", padx=20, pady=(0, 5))

        self.google_inner = ctk.CTkFrame(self.google_card, fg_color="transparent")
        self.google_inner.pack(fill="x", padx=12, pady=5)

        self.google_status_icon = ctk.CTkLabel(self.google_inner, text="🔒", font=("Segoe UI", 12), text_color="#94A3B8")
        self.google_status_icon.pack(side="left", padx=(2, 6))

        self.google_status_label = ctk.CTkLabel(
            self.google_inner,
            text="Google: No conectado (Inicia sesión para sincronizar todas las PWAs)",
            font=("Segoe UI", 11),
            text_color=TEXT_SECONDARY
        )
        self.google_status_label.pack(side="left")

        self.google_actions_frame = ctk.CTkFrame(self.google_inner, fg_color="transparent")
        self.google_actions_frame.pack(side="right")

        self.google_logout_btn = ctk.CTkButton(
            self.google_actions_frame,
            text="Cerrar sesión",
            font=("Segoe UI", 11),
            width=80,
            height=28,
            corner_radius=7,
            fg_color="transparent",
            hover_color="#2A1717",
            text_color="#EF4444",
            command=self._on_google_logout
        )

        self.google_login_btn = ctk.CTkButton(
            self.google_actions_frame,
            text="G  Iniciar sesión con Google",
            font=("Segoe UI", 11, "bold"),
            width=175,
            height=28,
            corner_radius=7,
            fg_color="#171C29",
            border_width=1,
            border_color="#262E42",
            hover_color="#222838",
            text_color="#E2E8F0",
            command=self._on_google_login
        )
        self.google_login_btn.pack(side="right", padx=(4, 0))

        # 3. Estado y barra de carga
        self.status_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=20)
        self.status_frame.pack(side="top", fill="x", pady=(0, 2))

        self.progress_bar = ctk.CTkProgressBar(self.status_frame, mode="indeterminate", width=220, height=3, progress_color=ACCENT_COLOR)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self.status_frame, text="", font=("Segoe UI", 11))
        self.status_label.pack(anchor="center")

        # 4. Sección de Historial (Más espacio y protagonismo)
        self.history_header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.history_header_frame.pack(side="top", fill="x", padx=25, pady=(2, 3))

        self.history_title = ctk.CTkLabel(
            self.history_header_frame,
            text="SITIOS RECIENTES",
            font=("Segoe UI", 10, "bold"),
            text_color="#8E9BB0"
        )
        self.history_title.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            self.history_header_frame,
            text="Limpiar todo",
            font=("Segoe UI", 11),
            width=75,
            height=24,
            corner_radius=7,
            fg_color="transparent",
            hover_color="#1A2030",
            text_color="#64748B",
            command=self._on_clear_history
        )
        self.clear_btn.pack(side="right")

        self.view_toggle_btn = ctk.CTkButton(
            self.history_header_frame,
            text="📱 Iconos",
            font=("Segoe UI", 11),
            width=78,
            height=24,
            corner_radius=7,
            fg_color="#181D2A",
            hover_color=ACCENT_COLOR,
            text_color="#E2E8F0",
            command=self._toggle_history_view
        )
        self.view_toggle_btn.pack(side="right", padx=(0, 6))

        # Scrollable frame para historial estilo tarjeta Glassmorphic ampliada
        self.history_scroll = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color=BG_SECONDARY,
            corner_radius=16,
            height=310,
            border_width=1,
            border_color=BORDER_COLOR
        )
        self.history_scroll.pack(side="top", fill="both", expand=True, padx=20, pady=(0, 4))

        self._refresh_history()

        # 5. Footer con créditos y estado
        self.footer_label = ctk.CTkLabel(
            self.main_container,
            text=f"{APP_NAME} v{APP_VERSION} • Simulación nativa PWA (Edge Chromium) • F12 para DevTools",
            font=("Segoe UI", 10),
            text_color="#4B5563"
        )
        self.footer_label.pack(side="bottom", pady=2)

    def _init_neural_network(self):
        """Inicializa los nodos de la red neuronal animada con estética cósmica/azul-violeta."""
        self.canvas_width = WINDOW_WIDTH
        self.canvas_height = WINDOW_HEIGHT
        self.node_count = 36
        self.nodes = []

        colors = ["#38BDF8", "#3B82F6", "#818CF8", "#A855F7", "#60A5FA"]

        for _ in range(self.node_count):
            self.nodes.append({
                "x": random.uniform(0, self.canvas_width),
                "y": random.uniform(0, self.canvas_height),
                "vx": random.uniform(-0.25, 0.25),
                "vy": random.uniform(-0.25, 0.25),
                "radius": random.uniform(1.5, 2.8),
                "pulse": random.uniform(0, math.pi * 2),
                "speed": random.uniform(0.02, 0.05),
                "color": random.choice(colors)
            })

    def _start_animations(self):
        """Ciclo de renderizado de la animación de red neuronal y logo."""
        if not self.anim_running:
            return

        try:
            self.canvas.delete("all")
            w = max(self.canvas.winfo_width(), 100)
            h = max(self.canvas.winfo_height(), 100)

            # Actualizar y dibujar nodos
            max_dist = 120
            for i, n in enumerate(self.nodes):
                n["x"] += n["vx"]
                n["y"] += n["vy"]
                n["pulse"] += n["speed"]

                if n["x"] < 0 or n["x"] > w:
                    n["vx"] *= -1
                if n["y"] < 0 or n["y"] > h:
                    n["vy"] *= -1

                # Conexiones sinápticas sutiles
                for j in range(i + 1, len(self.nodes)):
                    n2 = self.nodes[j]
                    dx = n["x"] - n2["x"]
                    dy = n["y"] - n2["y"]
                    dist = math.sqrt(dx * dx + dy * dy)

                    if dist < max_dist:
                        self.canvas.create_line(
                            n["x"], n["y"], n2["x"], n2["y"],
                            fill="#161B2E", width=1
                        )

                # Dibujar nodo con brillo suave
                r = n["radius"] + math.sin(n["pulse"]) * 0.5
                self.canvas.create_oval(
                    n["x"] - r, n["y"] - r, n["x"] + r, n["y"] + r,
                    fill=n.get("color", "#3B82F6"), outline="", width=0
                )

            # Animación ligera en el logo
            self.logo_pulse += 0.05
            if not self.pil_logo:
                glow_chars = ["⚡", "✨", "⚡", "⚡"]
                char_idx = int(self.logo_pulse * 1.5) % len(glow_chars)
                self.logo_label.configure(text=glow_chars[char_idx])
        except Exception:
            pass

        # Continuar loop a ~30 FPS
        self.after(33, self._start_animations)

    def _on_submit(self, event=None):
        url = self.url_entry.get().strip()
        if not url:
            self._show_error("Por favor ingresa una URL.")
            return

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        self._load_url(url)

    def _load_url(self, url: str):
        self.status_label.configure(text="Detectando PWA y preparando simulación...", text_color=TEXT_SECONDARY)
        self.progress_bar.pack(anchor="center", pady=(0, 6))
        self.progress_bar.start()

        self.url_entry.configure(state="disabled")
        self.submit_btn.configure(state="disabled")

        thread = threading.Thread(target=self._detect_and_open, args=(url,), daemon=True)
        thread.start()

    def _detect_and_open(self, url: str):
        try:
            pwa_result = detect_pwa(url)

            if pwa_result.has_pwa:
                manifest = merge_manifest(pwa_result.manifest, pwa_result)
                target_url = pwa_result.start_url if pwa_result.start_url else url
                is_real_pwa = True
            else:
                manifest = simulate_pwa(url, pwa_result)
                target_url = url
                is_real_pwa = False

            icon_path = get_best_icon(pwa_result.icons)
            if not icon_path:
                domain = urlparse(url).netloc
                icon_path = favicon_fallback(domain)

            title = manifest.get('name') or manifest.get('short_name') or pwa_result.site_title or url
            add_entry(url, title, icon_path)
            save_quick_access(url, title, icon_path)

            self.after(0, lambda: self._launch_webview(target_url, manifest, icon_path, is_real_pwa))
        except Exception as e:
            try:
                domain = urlparse(url).netloc or url
                fallback_manifest = {
                    "name": domain,
                    "short_name": domain[:12],
                    "start_url": url,
                    "display": "standalone",
                    "background_color": "#0D0D0D"
                }
                add_entry(url, domain, None)
                save_quick_access(url, domain, None)
                self.after(0, lambda: self._launch_webview(url, fallback_manifest, None, False))
            except Exception:
                self.after(0, lambda: self._show_error(f"Error al analizar el sitio: {str(e)}"))

    def _launch_webview(self, url: str, manifest: dict, icon_path: Optional[str], is_real_pwa: bool):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()

        if is_real_pwa:
            self.status_label.configure(text="PWA nativa detectada ✓ — Abriendo...", text_color=SUCCESS_COLOR)
        else:
            self.status_label.configure(text="Modo PWA simulado — Abriendo...", text_color=WARNING_COLOR)

        self.anim_running = False
        self.withdraw()
        open_as_pwa(url, manifest, icon_path, on_close=self._on_webview_close)

    def _on_webview_close(self):
        self.after(0, self._restore_main_window)
        self.after(400, self._refresh_google_status)

    def _restore_main_window(self):
        self.deiconify()
        if not self.anim_running:
            self.anim_running = True
            self._start_animations()
        self.url_entry.configure(state="normal")
        self.submit_btn.configure(state="normal")
        self.status_label.configure(text="")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self._refresh_history()

    def _on_window_unmap(self, event):
        """Pausa animaciones al minimizar la ventana para consumo cero de CPU."""
        if event.widget == self:
            self.anim_running = False

    def _on_window_map(self, event):
        """Reanuda animaciones cuando la ventana vuelve a estar visible."""
        if event.widget == self and not self.anim_running:
            self.anim_running = True
            self._start_animations()

    def _refresh_google_status(self):
        """Consulta el estado de la sesión de Google en segundo plano."""
        threading.Thread(target=self._check_google_session_worker, daemon=True).start()

    def _check_google_session_worker(self):
        logged_in = is_google_logged_in()
        self.after(0, lambda: self._apply_google_status(logged_in))

    def _apply_google_status(self, logged_in: Optional[bool]):
        if logged_in is True:
            self.google_status_icon.configure(text="✅")
            self.google_status_label.configure(
                text="Google: Sesión iniciada y compartida con todas las simulaciones",
                text_color=SUCCESS_COLOR
            )
            self.google_login_btn.configure(
                text="Gestionar cuenta",
                fg_color=BG_TERTIARY,
                hover_color="#38383A"
            )
            self.google_logout_btn.pack(side="right", padx=(0, 6))
        elif logged_in is False:
            self.google_status_icon.configure(text="🔒")
            self.google_status_label.configure(
                text="Google: No conectado (Inicia sesión para sincronizar todas las PWAs)",
                text_color=TEXT_SECONDARY
            )
            self.google_login_btn.configure(
                text="Iniciar sesión con Google",
                fg_color="#4285F4",
                hover_color="#3367D6"
            )
            self.google_logout_btn.pack_forget()
        else:
            # Estado bloqueado temporalmente por WebView2 en ejecución
            self.google_status_icon.configure(text="🔄")
            self.google_status_label.configure(
                text="Google: Perfil en uso por una ventana activa",
                text_color=TEXT_SECONDARY
            )

    def _on_google_login(self):
        self.google_status_label.configure(
            text="Abriendo ventana de inicio de sesión de Google...",
            text_color=ACCENT_COLOR
        )
        self.google_login_btn.configure(state="disabled")
        open_google_login(on_close=self._on_google_login_closed)

    def _on_google_login_closed(self):
        self.after(0, lambda: self.google_login_btn.configure(state="normal"))
        self.after(300, self._refresh_google_status)

    def _on_google_logout(self):
        self.google_status_label.configure(text="Abriendo ventana para cerrar sesión en Google...", text_color=WARNING_COLOR)
        open_google_logout(on_close=lambda: self.after(300, self._refresh_google_status))

    def _on_clear_profile(self):
        ok, msg = clear_browser_profile()
        if ok:
            self.status_label.configure(text=f"✓ {msg}", text_color=SUCCESS_COLOR)
        else:
            self._show_error(msg)
        self.after(300, self._refresh_google_status)

    def _show_error(self, message: str):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.configure(text=message, text_color=ERROR_COLOR)
        self.url_entry.configure(state="normal")
        self.submit_btn.configure(state="normal")

    def _toggle_history_view(self):
        """Alterna entre la vista de lista y la vista de iconos estilo app móvil."""
        if self.history_view_mode == "list":
            self.history_view_mode = "icons"
            self.view_toggle_btn.configure(text="📑 Lista", fg_color=ACCENT_COLOR)
        else:
            self.history_view_mode = "list"
            self.view_toggle_btn.configure(text="📱 Iconos", fg_color=BG_TERTIARY)
        self._refresh_history()

    def _get_entry_icon(self, entry, size=(42, 42)) -> Optional[ctk.CTkImage]:
        """Obtiene o carga en caché el icono de la aplicación escalado al tamaño especificado."""
        candidates = []
        if entry.favicon_path and os.path.exists(entry.favicon_path):
            candidates.append(entry.favicon_path)

        from quick_access import _slugify
        from config import URLS_DIR
        domain = urlparse(entry.url).netloc or entry.url
        slug = _slugify(domain)
        urls_ico = os.path.join(URLS_DIR, f"{slug}.ico")
        if os.path.exists(urls_ico):
            candidates.append(urls_ico)

        cache_key = (candidates[0] if candidates else "none", size)
        if cache_key in self._icon_cache:
            return self._icon_cache[cache_key]

        for path in candidates:
            try:
                pil_img = Image.open(path).convert("RGBA")
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=size)
                self._icon_cache[cache_key] = ctk_img
                return ctk_img
            except Exception:
                continue

        fb_key = ("default", size)
        if fb_key not in self._icon_cache:
            fb = Image.new("RGBA", size, color=(30, 36, 52, 255))
            self._icon_cache[fb_key] = ctk.CTkImage(light_image=fb, dark_image=fb, size=size)
        return self._icon_cache[fb_key]

    def _refresh_history(self):
        for widget in self.history_scroll.winfo_children():
            widget.destroy()

        history = get_history()
        if not history:
            no_history = ctk.CTkLabel(
                self.history_scroll,
                text="No hay sitios recientes. Ingresa una URL para comenzar.",
                font=("Segoe UI", 12),
                text_color=TEXT_SECONDARY
            )
            no_history.pack(pady=20)
            self.clear_btn.configure(state="disabled")
            self.view_toggle_btn.configure(state="disabled")
            return

        self.clear_btn.configure(state="normal")
        self.view_toggle_btn.configure(state="normal")

        # Vista de iconos estilo aplicación móvil
        if self.history_view_mode == "icons":
            grid_frame = ctk.CTkFrame(self.history_scroll, fg_color="transparent")
            grid_frame.pack(fill="both", expand=True, padx=2, pady=4)

            cols = 6
            for col_idx in range(cols):
                grid_frame.grid_columnconfigure(col_idx, weight=1)

            for idx, entry in enumerate(history):
                r = idx // cols
                c = idx % cols

                icon_img = self._get_entry_icon(entry, size=(42, 42))
                display_name = entry.title if entry.title else urlparse(entry.url).netloc
                # Truncar hasta donde alcance el nombre como en un icono de celular
                if len(display_name) > 13:
                    display_name = display_name[:11] + "…"

                app_card = ctk.CTkButton(
                    grid_frame,
                    text=display_name,
                    image=icon_img,
                    compound="top",
                    font=("Segoe UI", 10),
                    width=96,
                    height=88,
                    corner_radius=16,
                    fg_color="#151926",
                    hover_color=ACCENT_COLOR,
                    text_color=TEXT_COLOR,
                    command=lambda u=entry.url: self._load_url(u)
                )
                app_card.grid(row=r, column=c, padx=5, pady=6, sticky="n")
            return

        # Vista de lista estándar con favicon real iluminado
        for entry in history:
            item_frame = ctk.CTkFrame(self.history_scroll, fg_color="transparent", height=42)
            item_frame.pack(fill="x", pady=2, padx=4)

            display_title = entry.title if entry.title else entry.url
            if len(display_title) > 42:
                display_title = display_title[:39] + "..."

            row_icon = self._get_entry_icon(entry, size=(24, 24))

            # Botón principal con favicon real e iluminado
            btn = ctk.CTkButton(
                item_frame,
                text=f"  {display_title}",
                image=row_icon,
                compound="left",
                anchor="w",
                font=("Segoe UI", 12),
                fg_color="transparent",
                hover_color="#181D2A",
                text_color="#E2E8F0",
                command=lambda u=entry.url: self._load_url(u)
            )
            btn.pack(side="left", fill="x", expand=True)

            # Botón para instalar PWA (Acceso directo en Windows)
            install_btn = ctk.CTkButton(
                item_frame,
                text="📥 Instalar",
                width=82,
                height=26,
                corner_radius=8,
                font=("Segoe UI", 11, "bold"),
                fg_color="#172235",
                border_width=1,
                border_color="#1F304B",
                hover_color="#0284C7",
                text_color="#38BDF8",
                command=lambda u=entry.url, t=entry.title: self._install_pwa_shortcut(u, t)
            )
            install_btn.pack(side="right", padx=(4, 2))

            # Botón para eliminar del historial
            del_btn = ctk.CTkButton(
                item_frame,
                text="✕",
                width=24,
                height=24,
                corner_radius=6,
                font=("Segoe UI", 11),
                fg_color="transparent",
                hover_color="#DC2626",
                text_color="#64748B",
                command=lambda u=entry.url: self._remove_from_history(u)
            )
            del_btn.pack(side="right", padx=(2, 0))

    # Control de ventana y arrastre fluido y seguro (sin cierres inesperados)
    def _start_move(self, event):
        """Registra el punto inicial del arrastre en coordenadas absolutas de pantalla."""
        try:
            if self.state() == 'zoomed' or self._is_maximized:
                self.state('normal')
                self._is_maximized = False
                self.update_idletasks()
                # Recentrar suavemente respecto al cursor al desmaximizar
                win_w = self.winfo_width()
                new_x = max(0, event.x_root - (win_w // 2))
                new_y = max(0, event.y_root - 18)
                self.geometry(f"+{new_x}+{new_y}")
                self.update_idletasks()

            self._drag_start_x = event.x_root
            self._drag_start_y = event.y_root
            self._win_start_x = self.winfo_x()
            self._win_start_y = self.winfo_y()
        except Exception:
            pass

    def _on_move(self, event):
        """Mueve la ventana de manera continua y estable calculando el desplazamiento del cursor."""
        try:
            delta_x = event.x_root - self._drag_start_x
            delta_y = event.y_root - self._drag_start_y
            new_x = self._win_start_x + delta_x
            new_y = self._win_start_y + delta_y
            self.geometry(f"+{new_x}+{new_y}")
        except Exception:
            pass

    def _toggle_maximize(self, event=None):
        """Alterna entre maximizado y tamaño normal de ventana."""
        try:
            if self.state() == 'zoomed' or self._is_maximized:
                self.state('normal')
                self._is_maximized = False
            else:
                self.state('zoomed')
                self._is_maximized = True
        except Exception:
            pass

    def _minimize_window(self):
        """Minimiza limpiamente a la barra de tareas."""
        self.iconify()

    # Menús superiores tipo SaaS
    def _show_about_menu(self):
        m = tk.Menu(self, tearoff=0, bg="#10131E", fg="#E2E8F0", activebackground="#0284C7", activeforeground="#FFFFFF", font=("Segoe UI", 10), bd=1, relief="flat")
        m.add_command(label=f"PWA Simulator v{APP_VERSION} (Versión Actual)", state="disabled")
        m.add_separator()
        m.add_command(label="Entorno: Microsoft Edge WebView2", state="disabled")
        m.add_command(label="Modo Gaming & Bajo Consumo: Activo", state="disabled")
        x = self.btn_app_version.winfo_rootx()
        y = self.btn_app_version.winfo_rooty() + self.btn_app_version.winfo_height() + 2
        m.post(x, y)

    def _show_settings_menu(self):
        m = tk.Menu(self, tearoff=0, bg="#10131E", fg="#E2E8F0", activebackground="#0284C7", activeforeground="#FFFFFF", font=("Segoe UI", 10), bd=1, relief="flat")
        m.add_command(label="Iniciar / Gestionar Cuenta Google", command=self._on_google_login)
        m.add_command(label="Cerrar Sesión Google", command=self._on_google_logout)
        m.add_command(label="Limpiar Historial de Sitios", command=self._on_clear_history)
        m.add_command(label="Restablecer Perfil / Borrar Cookies y Sesiones", command=self._on_clear_profile)
        from config import URLS_DIR
        m.add_command(label="Abrir Carpeta URLS (Accesos Rápidos)", command=lambda: os.startfile(URLS_DIR) if hasattr(os, "startfile") else None)
        x = self.btn_settings.winfo_rootx()
        y = self.btn_settings.winfo_rooty() + self.btn_settings.winfo_height() + 2
        m.post(x, y)

    def _show_window_menu(self):
        m = tk.Menu(self, tearoff=0, bg="#10131E", fg="#E2E8F0", activebackground="#0284C7", activeforeground="#FFFFFF", font=("Segoe UI", 10), bd=1, relief="flat")
        m.add_command(label="Maximizar / Restaurar      F11", command=self._toggle_maximize)
        m.add_command(label="Minimizar                    Ctrl+M", command=self._minimize_window)
        m.add_separator()
        m.add_command(label="Cerrar                       Alt+F4", command=self.destroy)
        x = self.btn_window.winfo_rootx()
        y = self.btn_window.winfo_rooty() + self.btn_window.winfo_height() + 2
        m.post(x, y)

    def _show_view_menu(self):
        m = tk.Menu(self, tearoff=0, bg="#10131E", fg="#E2E8F0", activebackground="#0284C7", activeforeground="#FFFFFF", font=("Segoe UI", 10), bd=1, relief="flat")
        m.add_command(label=f"Zoom In  (+10%)             Ctrl +  [{int(self.zoom_level*100)}%]", command=self._zoom_in)
        m.add_command(label="Zoom Out (-10%)             Ctrl -", command=self._zoom_out)
        m.add_command(label="Reset Zoom (100%)           Ctrl 0", command=self._zoom_reset)
        m.add_separator()
        m.add_command(label=f"Cambiar a {'Iconos' if self.history_view_mode == 'list' else 'Lista'}", command=self._toggle_history_view)
        x = self.btn_view.winfo_rootx()
        y = self.btn_view.winfo_rooty() + self.btn_view.winfo_height() + 2
        m.post(x, y)

    def _zoom_in(self, event=None):
        self.zoom_level = min(1.8, round(self.zoom_level + 0.1, 2))
        ctk.set_widget_scaling(self.zoom_level)

    def _zoom_out(self, event=None):
        self.zoom_level = max(0.7, round(self.zoom_level - 0.1, 2))
        ctk.set_widget_scaling(self.zoom_level)

    def _zoom_reset(self, event=None):
        self.zoom_level = 1.0
        ctk.set_widget_scaling(1.0)

    def _install_pwa_shortcut(self, url: str, title: str):
        """Crea un acceso directo .lnk en el escritorio de Windows para lanzar la página como PWA independiente."""
        ok, link_name, err = create_desktop_shortcut(url, title)
        if ok:
            self.status_label.configure(
                text=f"✓ Acceso PWA '{link_name}' creado en tu Escritorio",
                text_color=SUCCESS_COLOR
            )
        else:
            self._show_error(f"Error al generar acceso: {err}")

    def _remove_from_history(self, url: str):
        remove_entry(url)
        self._refresh_history()

    def _on_clear_history(self):
        clear_history()
        self._refresh_history()
