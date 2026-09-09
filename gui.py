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
    BG_COLOR, BG_SECONDARY, BG_TERTIARY, ACCENT_COLOR, ACCENT_HOVER,
    TEXT_COLOR, TEXT_SECONDARY, ERROR_COLOR, SUCCESS_COLOR, WARNING_COLOR
)
from history import get_history, add_entry, remove_entry, clear_history
from pwa_detector import detect_pwa
from pwa_simulator import simulate_pwa, merge_manifest
from webview_manager import open_as_pwa
from favicon_extractor import get_best_icon, favicon_fallback

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
        self.minsize(740, 560)
        self.resizable(True, True)

        # Configurar icono de ventana
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Variables para animación de red neuronal
        self.nodes = []
        self.anim_running = True
        self.logo_angle = 0
        self.logo_pulse = 0

        self._setup_background_canvas()
        self._create_widgets()
        self._init_neural_network()
        self._start_animations()

    def _setup_background_canvas(self):
        """Crea el canvas de fondo para la red neuronal interactiva."""
        self.canvas = tk.Canvas(self, bg=BG_COLOR, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, event):
        self.canvas_width = event.width
        self.canvas_height = event.height

    def _create_widgets(self):
        # Contenedor principal superpuesto sobre el canvas
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(expand=True, fill="both", padx=36, pady=20)

        # 1. Logo animado y Título
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", pady=(5, 12))

        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            try:
                self.pil_logo = Image.open(logo_path).convert("RGBA")
                self.logo_img = ctk.CTkImage(light_image=self.pil_logo, dark_image=self.pil_logo, size=(105, 105))
                self.logo_label = ctk.CTkLabel(self.header_frame, image=self.logo_img, text="")
            except Exception:
                self.pil_logo = None
                self.logo_label = ctk.CTkLabel(self.header_frame, text="⚡", font=("Segoe UI", 60))
        else:
            self.pil_logo = None
            self.logo_label = ctk.CTkLabel(self.header_frame, text="⚡", font=("Segoe UI", 60))

        self.logo_label.pack(anchor="center")

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="PWA SIMULATOR",
            font=("Segoe UI", 26, "bold"),
            text_color=TEXT_COLOR
        )
        self.title_label.pack(anchor="center", pady=(6, 2))

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Simula, instala y ejecuta cualquier sitio web en modo Progressive Web App",
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY
        )
        self.subtitle_label.pack(anchor="center")

        # 2. Entrada de URL
        self.input_card = ctk.CTkFrame(
            self.main_container,
            fg_color=BG_SECONDARY,
            corner_radius=14,
            border_width=1,
            border_color=BG_TERTIARY
        )
        self.input_card.pack(side="top", fill="x", padx=30, pady=12)

        self.input_inner = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.input_inner.pack(fill="x", padx=14, pady=12)

        self.url_icon = ctk.CTkLabel(self.input_inner, text="🌐", font=("Segoe UI", 15))
        self.url_icon.pack(side="left", padx=(0, 8))

        self.url_entry = ctk.CTkEntry(
            self.input_inner,
            placeholder_text="https://ejemplo.com o ingresa una dirección...",
            height=42,
            corner_radius=8,
            font=("Segoe UI", 13),
            border_width=0,
            fg_color="#111113",
            text_color=TEXT_COLOR
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.url_entry.bind("<Return>", self._on_submit)
        self.url_entry.focus_set()

        self.submit_btn = ctk.CTkButton(
            self.input_inner,
            text="Abrir PWA",
            font=("Segoe UI", 13, "bold"),
            width=110,
            height=42,
            corner_radius=8,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            command=self._on_submit
        )
        self.submit_btn.pack(side="right")

        # 3. Estado y barra de carga
        self.status_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=28)
        self.status_frame.pack(side="top", fill="x", pady=(2, 6))

        self.progress_bar = ctk.CTkProgressBar(self.status_frame, mode="indeterminate", width=240, height=3)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self.status_frame, text="", font=("Segoe UI", 12))
        self.status_label.pack(anchor="center")

        # 4. Sección de Historial
        self.history_header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.history_header_frame.pack(side="top", fill="x", padx=35, pady=(4, 4))

        self.history_title = ctk.CTkLabel(
            self.history_header_frame,
            text="SITIOS RECIENTES",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_SECONDARY
        )
        self.history_title.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            self.history_header_frame,
            text="Limpiar todo",
            font=("Segoe UI", 11),
            width=70,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            hover_color=BG_TERTIARY,
            text_color=TEXT_SECONDARY,
            command=self._on_clear_history
        )
        self.clear_btn.pack(side="right")

        # Scrollable frame para historial
        self.history_scroll = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color=BG_SECONDARY,
            corner_radius=12,
            height=150,
            border_width=1,
            border_color=BG_TERTIARY
        )
        self.history_scroll.pack(side="top", fill="both", expand=True, padx=30, pady=(0, 8))

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
        """Inicializa los nodos de la red neuronal animada."""
        self.canvas_width = WINDOW_WIDTH
        self.canvas_height = WINDOW_HEIGHT
        self.node_count = 38
        self.nodes = []

        for _ in range(self.node_count):
            self.nodes.append({
                "x": random.uniform(0, self.canvas_width),
                "y": random.uniform(0, self.canvas_height),
                "vx": random.uniform(-0.4, 0.4),
                "vy": random.uniform(-0.4, 0.4),
                "radius": random.uniform(1.5, 3.0),
                "pulse": random.uniform(0, math.pi * 2),
                "speed": random.uniform(0.03, 0.06)
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
            max_dist = 115
            for i, n in enumerate(self.nodes):
                n["x"] += n["vx"]
                n["y"] += n["vy"]
                n["pulse"] += n["speed"]

                if n["x"] < 0 or n["x"] > w:
                    n["vx"] *= -1
                if n["y"] < 0 or n["y"] > h:
                    n["vy"] *= -1

                # Conexiones sinápticas
                for j in range(i + 1, len(self.nodes)):
                    n2 = self.nodes[j]
                    dx = n["x"] - n2["x"]
                    dy = n["y"] - n2["y"]
                    dist = math.sqrt(dx * dx + dy * dy)

                    if dist < max_dist:
                        # Intensidad de azul según distancia
                        alpha = int((1 - dist / max_dist) * 45)
                        hex_alpha = f"#{alpha:02x}{alpha*2:02x}{min(255, alpha*5):02x}"
                        self.canvas.create_line(
                            n["x"], n["y"], n2["x"], n2["y"],
                            fill="#1E3A8A", width=1
                        )

                # Dibujar nodo
                r = n["radius"] + math.sin(n["pulse"]) * 0.7
                self.canvas.create_oval(
                    n["x"] - r, n["y"] - r, n["x"] + r, n["y"] + r,
                    fill="#3B82F6", outline="#60A5FA", width=1
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

        self.withdraw()
        open_as_pwa(url, manifest, icon_path, on_close=self._on_webview_close)

    def _on_webview_close(self):
        self.after(0, self._restore_main_window)

    def _restore_main_window(self):
        self.deiconify()
        self.url_entry.configure(state="normal")
        self.submit_btn.configure(state="normal")
        self.status_label.configure(text="")
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self._refresh_history()

    def _show_error(self, message: str):
        self.progress_bar.stop()
        self.progress_bar.pack_forget()
        self.status_label.configure(text=message, text_color=ERROR_COLOR)
        self.url_entry.configure(state="normal")
        self.submit_btn.configure(state="normal")

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
            return

        self.clear_btn.configure(state="normal")

        for entry in history:
            item_frame = ctk.CTkFrame(self.history_scroll, fg_color="transparent")
            item_frame.pack(fill="x", pady=2, padx=4)

            display_title = entry.title if entry.title else entry.url
            if len(display_title) > 42:
                display_title = display_title[:39] + "..."

            # Botón principal para abrir el sitio
            btn = ctk.CTkButton(
                item_frame,
                text=f"🌐  {display_title}",
                anchor="w",
                font=("Segoe UI", 12),
                fg_color="transparent",
                hover_color=BG_TERTIARY,
                text_color=TEXT_COLOR,
                command=lambda u=entry.url: self._load_url(u)
            )
            btn.pack(side="left", fill="x", expand=True)

            # Botón para instalar PWA (Acceso directo en Windows)
            install_btn = ctk.CTkButton(
                item_frame,
                text="📥 Instalar",
                width=75,
                height=26,
                font=("Segoe UI", 11, "bold"),
                fg_color="transparent",
                hover_color="#1E3A8A",
                text_color="#60A5FA",
                command=lambda u=entry.url, t=entry.title: self._install_pwa_shortcut(u, t)
            )
            install_btn.pack(side="right", padx=(4, 2))

            # Botón para eliminar del historial
            del_btn = ctk.CTkButton(
                item_frame,
                text="✕",
                width=26,
                height=26,
                font=("Segoe UI", 11),
                fg_color="transparent",
                hover_color="#EF4444",
                text_color=TEXT_SECONDARY,
                command=lambda u=entry.url: self._remove_from_history(u)
            )
            del_btn.pack(side="right", padx=(2, 0))

    def _install_pwa_shortcut(self, url: str, title: str):
        """Crea un acceso directo .lnk o script en el escritorio para lanzar la página como PWA independiente."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            clean_title = "".join(c for c in (title or urlparse(url).netloc) if c.isalnum() or c in (' ', '_', '-')).strip()
            if not clean_title:
                clean_title = "PWA"

            vbs_path = os.path.join(desktop, f"{clean_title}.vbs")
            python_exe = sys.executable
            main_py = os.path.abspath(os.path.join(os.path.dirname(__file__), "main.py"))

            # Crear VBS launcher silencioso en el escritorio que abre la URL directamente en PWA Simulator
            vbs_content = f'CreateObject("WScript.Shell").Run "\"{python_exe}\" \"{main_py}\" \"{url}\"", 0, False'
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_content)

            self.status_label.configure(
                text=f"✓ Acceso PWA '{clean_title}.vbs' creado en tu Escritorio",
                text_color=SUCCESS_COLOR
            )
        except Exception as e:
            self._show_error(f"Error al crear acceso directo: {e}")

    def _remove_from_history(self, url: str):
        remove_entry(url)
        self._refresh_history()

    def _on_clear_history(self):
        clear_history()
        self._refresh_history()
