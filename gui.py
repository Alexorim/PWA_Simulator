"""
gui.py - Interfaz gráfica moderna para PWA Simulator en CustomTkinter
"""
import os
import sys
import threading
from urllib.parse import urlparse
from typing import Optional

import customtkinter as ctk
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
        self.minsize(720, 520)
        self.resizable(True, True)

        # Configurar icono de ventana
        icon_path = os.path.join(os.path.dirname(__file__), "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self._create_widgets()

    def _create_widgets(self):
        # Contenedor principal con scroll o centrado
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(expand=True, fill="both", padx=30, pady=20)

        # Espaciador superior
        self.top_spacer = ctk.CTkFrame(self.main_container, fg_color="transparent", height=10)
        self.top_spacer.pack(side="top", fill="x")

        # 1. Logo y Título
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", pady=(10, 15))

        logo_path = os.path.join(os.path.dirname(__file__), "assets", "logo.png")
        if os.path.exists(logo_path):
            try:
                pil_logo = Image.open(logo_path)
                logo_img = ctk.CTkImage(light_image=pil_logo, dark_image=pil_logo, size=(110, 110))
                self.logo_label = ctk.CTkLabel(self.header_frame, image=logo_img, text="")
            except Exception:
                self.logo_label = ctk.CTkLabel(self.header_frame, text="⚡", font=("Segoe UI", 64))
        else:
            self.logo_label = ctk.CTkLabel(self.header_frame, text="⚡", font=("Segoe UI", 64))

        self.logo_label.pack(anchor="center")

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text="PWA SIMULATOR",
            font=("Segoe UI", 26, "bold"),
            text_color=TEXT_COLOR
        )
        self.title_label.pack(anchor="center", pady=(8, 2))

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="Visualiza cualquier sitio web como Progressive Web App independiente",
            font=("Segoe UI", 13),
            text_color=TEXT_SECONDARY
        )
        self.subtitle_label.pack(anchor="center")

        # 2. Entrada de URL
        self.input_card = ctk.CTkFrame(self.main_container, fg_color=BG_SECONDARY, corner_radius=16, border_width=1, border_color=BG_TERTIARY)
        self.input_card.pack(side="top", fill="x", padx=40, pady=15)

        self.input_inner = ctk.CTkFrame(self.input_card, fg_color="transparent")
        self.input_inner.pack(fill="x", padx=16, pady=14)

        self.url_icon = ctk.CTkLabel(self.input_inner, text="🌐", font=("Segoe UI", 16))
        self.url_icon.pack(side="left", padx=(0, 10))

        self.url_entry = ctk.CTkEntry(
            self.input_inner,
            placeholder_text="https://ejemplo.com o ingresa un dominio...",
            height=44,
            corner_radius=10,
            font=("Segoe UI", 14),
            border_width=0,
            fg_color="#121212",
            text_color=TEXT_COLOR
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.url_entry.bind("<Return>", self._on_submit)
        self.url_entry.focus_set()

        self.submit_btn = ctk.CTkButton(
            self.input_inner,
            text="Abrir PWA",
            font=("Segoe UI", 13, "bold"),
            width=110,
            height=44,
            corner_radius=10,
            fg_color=ACCENT_COLOR,
            hover_color=ACCENT_HOVER,
            command=self._on_submit
        )
        self.submit_btn.pack(side="right")

        # 3. Estado y barra de carga
        self.status_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=30)
        self.status_frame.pack(side="top", fill="x", pady=(2, 10))

        self.progress_bar = ctk.CTkProgressBar(self.status_frame, mode="indeterminate", width=260, height=4)
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self.status_frame, text="", font=("Segoe UI", 12))
        self.status_label.pack(anchor="center")

        # 4. Sección de Historial
        self.history_header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.history_header_frame.pack(side="top", fill="x", padx=45, pady=(5, 5))

        self.history_title = ctk.CTkLabel(
            self.history_header_frame,
            text="SITIOS RECIENTES",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_SECONDARY
        )
        self.history_title.pack(side="left")

        self.clear_btn = ctk.CTkButton(
            self.history_header_frame,
            text="Limpiar",
            font=("Segoe UI", 11),
            width=60,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            hover_color=BG_TERTIARY,
            text_color=TEXT_SECONDARY,
            command=self._on_clear_history
        )
        self.clear_btn.pack(side="right")

        # Scrollable frame para lista de historial
        self.history_scroll = ctk.CTkScrollableFrame(
            self.main_container,
            fg_color=BG_SECONDARY,
            corner_radius=12,
            height=140,
            border_width=1,
            border_color=BG_TERTIARY
        )
        self.history_scroll.pack(side="top", fill="both", expand=True, padx=40, pady=(0, 10))

        self._refresh_history()

        # 5. Footer con versión
        self.footer_label = ctk.CTkLabel(
            self.main_container,
            text=f"{APP_NAME} • Simulación nativa PWA con Edge WebView2",
            font=("Segoe UI", 10),
            text_color="#4B5563"
        )
        self.footer_label.pack(side="bottom", pady=4)

    def _on_submit(self, event=None):
        url = self.url_entry.get().strip()
        if not url:
            self._show_error("Por favor ingresa una URL.")
            return

        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url

        self._load_url(url)

    def _load_url(self, url: str):
        self.status_label.configure(text="Detectando PWA y metadatos del sitio...", text_color=TEXT_SECONDARY)
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

            # Buscar mejor icono
            icon_path = get_best_icon(pwa_result.icons)
            if not icon_path:
                domain = urlparse(url).netloc
                icon_path = favicon_fallback(domain)

            title = manifest.get('name') or manifest.get('short_name') or pwa_result.site_title or url
            add_entry(url, title, icon_path)

            self.after(0, lambda: self._launch_webview(target_url, manifest, icon_path, is_real_pwa))
        except Exception as e:
            # Fallback de emergencia: si algo falla en el scraper, abrir de todas formas
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
            self.status_label.configure(text="PWA nativa detectada ✓ — Iniciando...", text_color=SUCCESS_COLOR)
        else:
            self.status_label.configure(text="Modo PWA simulado — Iniciando...", text_color=WARNING_COLOR)

        # Ocultar la ventana principal mientras la PWA esté en ejecución
        self.withdraw()
        open_as_pwa(url, manifest, icon_path, on_close=self._on_webview_close)

    def _on_webview_close(self):
        # Al cerrarse la ventana de la PWA, restaurar de forma segura en el hilo de Tkinter
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
            if len(display_title) > 50:
                display_title = display_title[:47] + "..."

            # Botón para abrir el sitio
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

            # Botón para eliminar del historial
            del_btn = ctk.CTkButton(
                item_frame,
                text="✕",
                width=28,
                height=28,
                font=("Segoe UI", 11),
                fg_color="transparent",
                hover_color="#EF4444",
                text_color=TEXT_SECONDARY,
                command=lambda u=entry.url: self._remove_from_history(u)
            )
            del_btn.pack(side="right", padx=(4, 0))

    def _remove_from_history(self, url: str):
        remove_entry(url)
        self._refresh_history()

    def _on_clear_history(self):
        clear_history()
        self._refresh_history()
