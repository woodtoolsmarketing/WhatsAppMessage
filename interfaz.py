import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import pandas as pd
import threading
import subprocess
import os
import sys
import time
import ctypes
import urllib.parse
import requests
import json
import re
import io
from datetime import datetime, timedelta

import mainCode

URL_SERVIDOR_RENDER = "https://woodtools-webhook.onrender.com"
COLOR_ROJO_WT = "#a41e22"
COLOR_PANELES = "#f5f5f5"

def obtener_ruta_interna(ruta_relativa):
    try:
        ruta_base = sys._MEIPASS
    except Exception:
        ruta_base = os.path.abspath(".")
    return os.path.join(ruta_base, ruta_relativa)

class WoodToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Gestor de Marketing WhatsApp v{mainCode.VERSION_APP} - CRM")
        self.root.geometry("1500x900")
        self.root.state('zoomed')
        self.root.configure(bg=COLOR_ROJO_WT)
        self.cancelar_envio = False
        self.tipo_base_actual = "clientes"
        
        mainCode.inicializar_db()
        
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        menu_reportes = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Reportes", menu=menu_reportes)
        menu_reportes.add_command(label="Ver rendimiento de la campaña", command=self.abrir_rendimiento)

        menu_bot = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Bot", menu=menu_bot)
        menu_bot.add_command(label="Enseñar / Corregir al bot", command=self.abrir_correcciones_bot)
        menu_bot.add_command(label="Cortes de fresas (visión)", command=self.abrir_cortes_fresas)

        menu_servidor = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Servidor", menu=menu_servidor)
        menu_servidor.add_command(label="Ver qué dice el servidor", command=self.abrir_monitor_servidor)

        menu_ayuda = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Ayuda", menu=menu_ayuda)
        menu_ayuda.add_command(label="Buscar actualizaciones", command=lambda: self.verificar_actualizaciones(manual=True))
        menu_ayuda.add_command(label=f"Versión {mainCode.VERSION_APP}", state="disabled")

        try:
            myappid = 'woodtools.gestormarketing.12.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception: pass
            
        ruta_ico = obtener_ruta_interna(r"Imagenes\logo.ico")
        if not os.path.exists(ruta_ico): ruta_ico = obtener_ruta_interna("logo.ico")
            
        if os.path.exists(ruta_ico):
            try:
                self.root.iconbitmap(ruta_ico)
                icono_barra = ImageTk.PhotoImage(Image.open(ruta_ico))
                self.root.iconphoto(False, icono_barra)
            except Exception as e: print(f"Error cargando icono: {e}")

        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.ruta_imagen_seleccionada = None
        
        frame_top = tk.Frame(root, pady=5, padx=10, bg=COLOR_ROJO_WT)
        frame_top.pack(fill="x")
        self.cargar_logo_con_ovalo(frame_top)

        btn_cargar = tk.Button(frame_top, text="☁️ Descargar Base de la Nube", command=self.abrir_selector_bases, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"))
        btn_cargar.pack(side=tk.LEFT, padx=10)
        
        btn_verificar = tk.Button(frame_top, text="🔍 Descartes", command=self.verificar_observados, bg="#FF9800", fg="white", font=("Segoe UI", 10, "bold"))
        btn_verificar.pack(side=tk.LEFT, padx=10)
        
        btn_reporte = tk.Button(frame_top, text="📊 Exportar Reporte", command=self.abrir_ventana_exportacion, bg="#2196F3", fg="white", font=("Segoe UI", 10, "bold"))
        btn_reporte.pack(side=tk.LEFT, padx=10)
        
        btn_derivados = tk.Button(frame_top, text="💬 Chats Pendientes", command=self.abrir_chats_derivados, bg="#9C27B0", fg="white", font=("Segoe UI", 10, "bold"))
        btn_derivados.pack(side=tk.LEFT, padx=10)
        
        self.lbl_status_db = tk.Label(frame_top, text="Esperando datos...", fg="white", bg=COLOR_ROJO_WT, font=("Segoe UI", 9, "bold"))
        self.lbl_status_db.pack(side=tk.LEFT, padx=10)

        self.frame_bot_control = tk.Frame(frame_top, bg="white", padx=10, pady=2, highlightbackground="#ccc", highlightthickness=1)
        self.frame_bot_control.pack(side=tk.RIGHT, padx=20)
        
        self.lbl_bot_titulo = tk.Label(self.frame_bot_control, text="BOT INTELIGENTE", font=("Segoe UI", 8, "bold"), bg="white", fg="gray")
        self.lbl_bot_titulo.pack()
        
        self.lbl_bot_estado = tk.Label(self.frame_bot_control, text="CONECTANDO...", font=("Segoe UI", 10, "bold"), bg="white", fg="orange")
        self.lbl_bot_estado.pack()
        
        self.btn_toggle_bot = tk.Button(self.frame_bot_control, text="Cargando...", command=self.click_toggle_bot, font=("Segoe UI", 8), bg="#eee", relief="groove")
        self.btn_toggle_bot.pack(pady=2)
        
        self.config_bot_actual = "AUTO"

        frame_filtros = tk.LabelFrame(root, text="Filtros", padx=5, pady=2, bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold"))
        frame_filtros.pack(fill="x", padx=20, pady=2)
        
        tk.Label(frame_filtros, text="Nombre:", bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold")).grid(row=0, column=0)
        self.entry_nombre = tk.Entry(frame_filtros)
        self.entry_nombre.grid(row=0, column=1, padx=5)
        self.entry_nombre.bind("<KeyRelease>", self.aplicar_filtros)
        
        tk.Label(frame_filtros, text="Zona/Interés:", bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold")).grid(row=0, column=2)
        self.combo_zona = ttk.Combobox(frame_filtros, state="readonly", width=10)
        self.combo_zona.grid(row=0, column=3)
        self.combo_zona.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        tk.Label(frame_filtros, text="Favorito:", bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold")).grid(row=0, column=4)
        self.combo_herramientas = ttk.Combobox(frame_filtros, state="readonly")
        self.combo_herramientas.grid(row=0, column=5)
        self.combo_herramientas.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        tk.Button(frame_filtros, text="Limpiar", command=self.limpiar_filtros).grid(row=0, column=6, padx=15)
        self.lbl_conteo = tk.Label(frame_filtros, text="Regs: 0", font=("Segoe UI", 10, "bold"), fg="#2196F3", bg=COLOR_PANELES)
        self.lbl_conteo.grid(row=0, column=7, padx=20)

        frame_campana = tk.LabelFrame(root, text="Configuración de Envío", padx=5, pady=2, bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold"))
        # OJO: este bloque se empaqueta más abajo (después del Panel de Control y de Gestión
        # de Teléfonos) para que, al maximizar en pantallas chicas, esos paneles inferiores
        # tengan prioridad de espacio y el botón ENVIAR nunca quede fuera de pantalla.

        tk.Label(frame_campana, text="Tipo Mensaje:", bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w")
        self.tipo_mensaje_var = tk.StringVar(value="Promociones")
        self.combo_tipo_mensaje = ttk.Combobox(frame_campana, values=["Promociones", "Rescate (Te extrañamos)", "Gira Vendedor", "Personalizado", "Novedades", "Recotización"], state="readonly", textvariable=self.tipo_mensaje_var, width=25)
        self.combo_tipo_mensaje.grid(row=1, column=0, padx=5, pady=2, sticky="n")
        self.combo_tipo_mensaje.bind("<<ComboboxSelected>>", self.actualizar_inputs_dinamicos)

        tk.Label(frame_campana, text="Enviar como:", bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky="w", padx=10)
        
        opciones_vendedores_base = ["AUTOMÁTICO (Según Planilla)", "Emmanuel", "Carlos", "Valentín", "Ariel"]
        self.combo_vendedor = ttk.Combobox(frame_campana, values=opciones_vendedores_base, state="readonly", width=25)
        self.combo_vendedor.grid(row=1, column=1, padx=10, pady=2, sticky="n")
        self.combo_vendedor.current(0)
        self.combo_vendedor.bind("<<ComboboxSelected>>", self.actualizar_preview)

        self.frame_dinamico = tk.Frame(frame_campana, bg=COLOR_PANELES)
        self.frame_dinamico.grid(row=0, column=2, rowspan=2, padx=10, sticky="nwe")
        
        self.lbl_dinamico_titulo = tk.Label(self.frame_dinamico, text="", bg=COLOR_PANELES, fg="black", font=("Arial", 9, "bold"))
        
        self.entry_dinamico_texto = tk.Entry(self.frame_dinamico, width=30)
        self.text_dinamico_multilinea = tk.Text(self.frame_dinamico, width=40, height=3, font=("Arial", 10), relief="solid", bd=1)
        
        self.lbl_novedad_subtipo = tk.Label(self.frame_dinamico, text="Tipo:", bg=COLOR_PANELES, fg="black", font=("Arial", 8, "bold"))
        self.combo_novedad_subtipo = ttk.Combobox(self.frame_dinamico, values=["Ingreso de stock", "Nuevo producto"], state="readonly", width=20)
        self.lbl_novedad_herramienta = tk.Label(self.frame_dinamico, text="Herramienta:", bg=COLOR_PANELES, fg="black", font=("Arial", 8, "bold"))
        self.combo_novedad_herramienta = ttk.Combobox(self.frame_dinamico, state="readonly", width=20)

        self.lbl_aviso_meta = tk.Label(self.frame_dinamico, text="🔒 Plantilla Meta", fg="#d32f2f", bg=COLOR_PANELES, font=("Arial", 8, "bold"))
        self.lbl_tip_tags = tk.Label(self.frame_dinamico, text="💡 Usa [CLIENTE] y [LINK]", fg="#1976d2", bg=COLOR_PANELES, font=("Arial", 8, "italic"))

        self.btn_subir_imagen = tk.Button(self.frame_dinamico, text="📂 Adjuntar Imagen (Obligatoria)", command=self.seleccionar_imagen)
        self.btn_quitar_imagen = tk.Button(self.frame_dinamico, text="❌ Quitar Imagen", command=self.quitar_imagen, fg="red")
        self.lbl_nombre_imagen = tk.Label(self.frame_dinamico, text="Sin imagen", bg=COLOR_PANELES, fg="red")

        self.frame_preview = tk.LabelFrame(frame_campana, text="Vista Previa", bg=COLOR_PANELES, fg="#555", font=("Segoe UI", 9, "bold"))
        self.frame_preview.grid(row=0, column=3, rowspan=2, padx=10, sticky="nsew")
        
        self.lbl_preview_text = tk.Label(self.frame_preview, text="", bg="#e8ecef", width=55, height=6, justify="left", anchor="nw", wraplength=400, font=("Arial", 10, "italic"), relief="sunken", bd=1, padx=5, pady=5, fg="#333")
        self.lbl_preview_text.pack(padx=5, pady=2, fill="both", expand=True)

        # La columna de la Vista Previa se estira para ocupar todo el ancho libre a la derecha
        # (así no queda el hueco vacío al maximizar). Su texto ajusta el "wrap" al ancho real.
        frame_campana.columnconfigure(3, weight=1)
        self.frame_preview.bind("<Configure>", lambda e: self.lbl_preview_text.config(wraplength=max(300, e.width - 30)))

        self.entry_dinamico_texto.bind("<KeyRelease>", self.actualizar_preview)
        self.text_dinamico_multilinea.bind("<KeyRelease>", self.actualizar_preview)
        self.combo_novedad_subtipo.bind("<<ComboboxSelected>>", self.actualizar_preview)
        self.combo_novedad_herramienta.bind("<<ComboboxSelected>>", self.actualizar_preview)

        self.actualizar_inputs_dinamicos()

        frame_accion = tk.LabelFrame(root, text="Panel de Control", pady=5, padx=20, bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold"), relief="groove", bd=2)
        frame_accion.pack(fill="x", side="bottom", padx=20, pady=5)
        
        self.lbl_progreso = tk.Label(frame_accion, text="Sistema listo.", fg="black", bg=COLOR_PANELES, font=("Segoe UI", 10, "bold"))
        self.lbl_progreso.pack(pady=2)
        
        frame_botones_accion = tk.Frame(frame_accion, bg=COLOR_PANELES)
        frame_botones_accion.pack(pady=2)

        self.btn_enviar = tk.Button(frame_botones_accion, text="🚀 ENVIAR A TODOS", command=self.iniciar_envio, bg="#2196F3", fg="white", font=("Segoe UI", 12, "bold"), width=20)
        self.btn_enviar.grid(row=0, column=0, padx=15)

        self.btn_cancelar = tk.Button(frame_botones_accion, text="🛑 CANCELAR ENVÍO", command=self.comando_cancelar_envio, bg=COLOR_ROJO_WT, fg="white", font=("Segoe UI", 12, "bold"), width=20, state="disabled")
        self.btn_cancelar.grid(row=0, column=1, padx=15)

        self.frame_telefonos = tk.LabelFrame(root, text="🔍 Gestión de Teléfonos (Clic en la fila superior para ver)", padx=5, pady=5, bg=COLOR_PANELES, fg="black", font=("Segoe UI", 9, "bold"))
        self.frame_telefonos.pack(fill="x", padx=20, pady=2, side="bottom")
        self._limpiar_panel_telefonos()

        # Configuración de Envío: va arriba de la tabla (side="top"), pero se empaqueta AHORA,
        # después de los paneles inferiores, para que estos reserven su espacio primero.
        frame_campana.pack(fill="x", padx=20, pady=2)

        frame_tabla = tk.Frame(root, bg=COLOR_ROJO_WT)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=2)
        self.tree = ttk.Treeview(frame_tabla, columns=("Cli", "Tel", "Vend", "Zona", "Est"), show="headings")
        # Las columnas de texto (Cliente, Se enviará a, Zona) se estiran para llenar todo el
        # ancho de la ventana; Vendedor y Estado quedan fijas y angostas. Así no queda hueco a la derecha.
        self.tree.heading("Cli", text="Cliente"); self.tree.column("Cli", width=220, minwidth=160, stretch=True)
        self.tree.heading("Tel", text="Se enviará a:"); self.tree.column("Tel", width=300, minwidth=220, stretch=True)
        self.tree.heading("Vend", text="Vendedor"); self.tree.column("Vend", width=90, minwidth=70, anchor="center", stretch=False)
        self.tree.heading("Zona", text="Zona"); self.tree.column("Zona", width=260, minwidth=160, stretch=True)
        self.tree.heading("Est", text="Estado"); self.tree.column("Est", width=90, minwidth=70, anchor="center", stretch=False)
        self.tree.tag_configure('valido', background='white'); self.tree.tag_configure('invalido', background='#FFCCCC', foreground='red')
        self.tree.bind("<<TreeviewSelect>>", self.al_seleccionar_cliente)
        
        scroll = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set); scroll.pack(side="right", fill="y"); self.tree.pack(fill="both", expand=True)

        self.actualizar_estado_bot_loop()

        # Chequeo de actualizaciones al iniciar (solo en el .exe instalado, no en desarrollo)
        if getattr(sys, 'frozen', False):
            self.root.after(3000, lambda: threading.Thread(target=self._chequeo_inicial_actualizacion, daemon=True).start())

    def cargar_logo_con_ovalo(self, parent):
        ruta_1 = obtener_ruta_interna(r"Imagenes\logo.png")
        ruta_2 = obtener_ruta_interna("logo.png")
        ruta_final = ruta_1 if os.path.exists(ruta_1) else ruta_2
        if os.path.exists(ruta_final):
            try:
                img_pil = Image.open(ruta_final)
                h_deseado = 55
                w, h = img_pil.size
                new_w = int((h_deseado/h)*w)
                img_resized = img_pil.resize((new_w, h_deseado), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(img_resized)
                ovalo_w = new_w + 30
                ovalo_h = h_deseado + 10
                canvas = tk.Canvas(parent, width=ovalo_w, height=ovalo_h, bg=COLOR_ROJO_WT, highlightthickness=0)
                canvas.pack(side=tk.RIGHT, padx=15)
                canvas.create_oval(2, 2, ovalo_w-2, ovalo_h-2, fill=COLOR_PANELES, outline=COLOR_PANELES)
                canvas.create_image(ovalo_w/2, ovalo_h/2, image=self.logo_img)
            except Exception as e: print(f"Error cargando logo: {e}")

    # ==========================================
    # AUTO-ACTUALIZACIÓN
    # ==========================================
    def _chequeo_inicial_actualizacion(self):
        """Se ejecuta en segundo plano al abrir. Si hay versión nueva, la ofrece."""
        info = mainCode.obtener_actualizacion_disponible()
        if info:
            self.root.after(0, lambda: self._ofrecer_actualizacion(info))

    def verificar_actualizaciones(self, manual=False):
        """Busca actualizaciones. Si manual=True, avisa aunque ya esté al día."""
        def tarea():
            info = mainCode.obtener_actualizacion_disponible()
            if info:
                self.root.after(0, lambda: self._ofrecer_actualizacion(info))
            elif manual:
                self.root.after(0, lambda: messagebox.showinfo(
                    "Actualizaciones",
                    f"Ya tenés la última versión instalada (v{mainCode.VERSION_APP})."))
        threading.Thread(target=tarea, daemon=True).start()

    def _ofrecer_actualizacion(self, info):
        notas = (info.get("notas") or "").strip()
        if len(notas) > 300:
            notas = notas[:300] + "..."
        txt = f"Hay una versión nueva disponible: v{info['version']}\n(Tenés la v{mainCode.VERSION_APP})"
        if notas:
            txt += f"\n\nNovedades:\n{notas}"
        txt += "\n\n¿Querés descargarla e instalarla ahora?\nLa app se cerrará unos segundos y se volverá a abrir sola."
        if messagebox.askyesno("Actualización disponible", txt):
            self._descargar_e_instalar(info)

    def _descargar_e_instalar(self, info):
        vent = tk.Toplevel(self.root)
        vent.title("Descargando actualización")
        vent.geometry("430x130")
        vent.configure(bg="white")
        vent.transient(self.root)
        vent.resizable(False, False)
        tk.Label(vent, text=f"Descargando la versión v{info['version']}...", bg="white",
                 font=("Segoe UI", 10, "bold")).pack(pady=(18, 8))
        barra = ttk.Progressbar(vent, orient="horizontal", length=370, mode="determinate")
        barra.pack(pady=5)
        lbl = tk.Label(vent, text="0 %", bg="white", fg="#555")
        lbl.pack()

        def progreso(bajado, total):
            if total:
                pct = int(bajado * 100 / total)
                self.root.after(0, lambda: (barra.config(value=pct),
                    lbl.config(text=f"{pct} %   ({bajado // 1048576} / {total // 1048576} MB)")))

        def tarea():
            ruta = mainCode.descargar_instalador(info["url"], progreso)
            self.root.after(0, lambda: self._finalizar_actualizacion(vent, ruta))

        threading.Thread(target=tarea, daemon=True).start()

    def _finalizar_actualizacion(self, vent, ruta_setup):
        try: vent.destroy()
        except Exception: pass
        if not ruta_setup or not os.path.exists(ruta_setup):
            messagebox.showerror("Actualización",
                                 "No se pudo descargar la actualización. Probá de nuevo más tarde.")
            return
        try:
            ruta_app = sys.executable  # el .exe actual (misma ruta a la que reinstala el setup)
            # Espera ~3s a que la app cierre, instala en silencio y vuelve a abrir la app.
            cmd = (f'ping 127.0.0.1 -n 4 >nul & "{ruta_setup}" /VERYSILENT /SUPPRESSMSGBOXES '
                   f'/NORESTART & start "" "{ruta_app}"')
            subprocess.Popen(cmd, shell=True, creationflags=0x00000008)  # DETACHED_PROCESS
            self.root.destroy()
            os._exit(0)
        except Exception as e:
            mainCode.log_error(f"Error lanzando el instalador: {e}")
            messagebox.showerror("Actualización", f"No se pudo iniciar la instalación:\n{e}")

    # ==========================================
    # LÓGICA VISUAL DEL BOT
    # ==========================================
    def actualizar_estado_bot_loop(self):
        def tarea():
            data = mainCode.obtener_estado_bot_nube()
            if data:
                self.config_bot_actual = data['configuracion']
                modo = data['modo_actual']
                
                if modo == "INTELIGENTE":
                    self.root.after(0, lambda: self.lbl_bot_estado.config(text="● ENCENDIDO", fg="#2E7D32"))
                else:
                    self.root.after(0, lambda: self.lbl_bot_estado.config(text="○ APAGADO (Básico)", fg="#C62828"))
                
                if self.config_bot_actual == "AUTO":
                    self.root.after(0, lambda: self.btn_toggle_bot.config(text="Modo: Automático 🕒"))
                elif self.config_bot_actual == "ON":
                    self.root.after(0, lambda: self.btn_toggle_bot.config(text="Modo: Siempre ON 🟢"))
                else:
                    self.root.after(0, lambda: self.btn_toggle_bot.config(text="Modo: Siempre OFF 🔴"))
            else:
                self.root.after(0, lambda: self.lbl_bot_estado.config(text="ERROR CONEXIÓN", fg="gray"))
            
            self.root.after(30000, self.actualizar_estado_bot_loop)

        threading.Thread(target=tarea, daemon=True).start()

    def click_toggle_bot(self):
        proximos = {"AUTO": "ON", "ON": "OFF", "OFF": "AUTO"}
        nuevo = proximos.get(self.config_bot_actual, "AUTO")
        
        self.btn_toggle_bot.config(state="disabled", text="Cambiando...")
        
        def enviar():
            exito = mainCode.cambiar_estado_bot_nube(nuevo)
            if exito:
                self.config_bot_actual = nuevo
                data = mainCode.obtener_estado_bot_nube()
                if data:
                    self.root.after(0, lambda: self.btn_toggle_bot.config(state="normal"))
                    self.root.after(0, lambda d=data: self.actualizar_ui_manual(d))
            else:
                self.root.after(0, lambda: messagebox.showerror("Error", "No se pudo conectar con el servidor para cambiar el modo."))
                self.root.after(0, lambda: self.btn_toggle_bot.config(state="normal"))

        threading.Thread(target=enviar, daemon=True).start()

    def actualizar_ui_manual(self, data):
        self.config_bot_actual = data['configuracion']
        modo = data['modo_actual']
        if modo == "INTELIGENTE":
            self.lbl_bot_estado.config(text="● ENCENDIDO", fg="#2E7D32")
        else:
            self.lbl_bot_estado.config(text="○ APAGADO (Básico)", fg="#C62828")
        
        textos = {"AUTO": "Modo: Automático 🕒", "ON": "Modo: Siempre ON 🟢", "OFF": "Modo: Siempre OFF 🔴"}
        self.btn_toggle_bot.config(text=textos.get(self.config_bot_actual, "Error"))

    # ==========================================
    # PANTALLA DE CHATS PENDIENTES / ABANDONADOS
    # ==========================================
    def abrir_cortes_fresas(self):
        """Ventana para editar la guía de cortes de fresas (visión del bot). Usa los
        endpoints /fresas_cortes: el bot los aplica en la próxima foto, sin redeploy."""
        vent = tk.Toplevel(self.root)
        vent.title("Cortes de Fresas (guía de visión)")
        vent.geometry("900x820")
        vent.configure(bg="white")

        GRUPOS = ["canales", "moldura", "machimbre", "finger", "cepillado"]

        frame_form = tk.LabelFrame(vent, text="  Nuevo corte  ", bg="white",
                                   font=("Arial", 11, "bold"), fg=COLOR_ROJO_WT, padx=12, pady=10)
        frame_form.pack(fill="x", padx=12, pady=(12, 8))
        fila1 = tk.Frame(frame_form, bg="white")
        fila1.pack(fill="x", pady=(0, 6))
        tk.Label(fila1, text="Nombre de la fresa:", bg="white", font=("Arial", 10, "bold")).pack(side="left")
        entry_nombre = tk.Entry(fila1, font=("Arial", 11), relief="solid", bd=1, width=30)
        entry_nombre.pack(side="left", padx=(8, 12))
        tk.Label(fila1, text="Grupo:", bg="white", font=("Arial", 10, "bold")).pack(side="left")
        combo_grupo = ttk.Combobox(fila1, values=GRUPOS, state="readonly", width=13)
        combo_grupo.pack(side="left", padx=(6, 0))
        tk.Label(frame_form, text="¿Cómo se ve el corte? (para que el bot lo reconozca en la foto):", bg="white",
                 font=("Arial", 10, "bold")).pack(anchor="w")
        txt_desc = tk.Text(frame_form, font=("Arial", 11), height=3, wrap="word",
                           relief="solid", bd=1, highlightbackground="#ccc", highlightthickness=1)
        txt_desc.pack(fill="x", pady=(2, 8))
        tk.Label(frame_form, text="Palabras clave (sinónimos del cliente, separadas por coma):", bg="white",
                 font=("Arial", 10)).pack(anchor="w")
        entry_claves = tk.Entry(frame_form, font=("Arial", 11), relief="solid", bd=1)
        entry_claves.pack(fill="x", pady=(2, 8))
        btn_agregar = tk.Button(frame_form, text="➕ Agregar corte", bg="#4CAF50", fg="white",
                                font=("Arial", 11, "bold"), relief="flat", pady=8)
        btn_agregar.pack(fill="x")

        frame_lista = tk.LabelFrame(vent, text="  Cortes cargados  ", bg="white",
                                    font=("Arial", 11, "bold"), fg=COLOR_ROJO_WT, padx=12, pady=10)
        frame_lista.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        frame_bar = tk.Frame(frame_lista, bg="white")
        frame_bar.pack(fill="x", pady=(0, 6))
        btn_actualizar = tk.Button(frame_bar, text="🔄 Actualizar", bg="#2196F3", fg="white",
                                   font=("Arial", 9, "bold"), relief="flat", padx=10)
        btn_actualizar.pack(side="left")
        btn_probar = tk.Button(frame_bar, text="🔍 Probar con una foto", bg="#6a1b9a", fg="white",
                               font=("Arial", 9, "bold"), relief="flat", padx=10)
        btn_probar.pack(side="left", padx=(8, 0))
        btn_eliminar = tk.Button(frame_bar, text="🗑 Eliminar", bg="#e74c3c", fg="white",
                                 font=("Arial", 9, "bold"), relief="flat", padx=10, state="disabled")
        btn_eliminar.pack(side="right")

        detalle = tk.LabelFrame(frame_lista, text="  Ver / Editar el corte seleccionado  ",
                                bg="white", font=("Arial", 10, "bold"), fg=COLOR_ROJO_WT, padx=10, pady=8)
        detalle.pack(side="bottom", fill="x", pady=(8, 0))
        filad = tk.Frame(detalle, bg="white")
        filad.pack(fill="x", pady=(0, 4))
        tk.Label(filad, text="Grupo:", bg="white", font=("Arial", 9, "bold")).pack(side="left")
        combo_det = ttk.Combobox(filad, values=GRUPOS, state="readonly", width=12)
        combo_det.pack(side="left", padx=(6, 12))
        tk.Label(filad, text="Palabras clave:", bg="white", font=("Arial", 9, "bold")).pack(side="left")
        entry_claves_det = tk.Entry(filad, font=("Arial", 10), relief="solid", bd=1)
        entry_claves_det.pack(side="left", fill="x", expand=True, padx=(6, 12))
        btn_foto = tk.Button(filad, text="📷 Foto...", bg="#795548", fg="white",
                             font=("Arial", 9, "bold"), relief="flat", padx=10, state="disabled")
        btn_foto.pack(side="right", padx=(0, 6))
        btn_guardar_edit = tk.Button(filad, text="💾 Guardar", bg="#2196F3", fg="white",
                                     font=("Arial", 9, "bold"), relief="flat", padx=10, state="disabled")
        btn_guardar_edit.pack(side="right", padx=(0, 6))
        zona_det = tk.Frame(detalle, bg="white")
        zona_det.pack(fill="x")
        txt_det = tk.Text(zona_det, font=("Arial", 11), height=4, wrap="word", relief="solid", bd=1,
                          highlightbackground="#ccc", highlightthickness=1, state="disabled")
        txt_det.pack(side="left", fill="x", expand=True)
        lbl_foto = tk.Label(zona_det, bg="#f0f0f0", text="sin foto", fg="#999",
                            width=20, height=8, relief="solid", bd=1)
        lbl_foto.pack(side="right", padx=(10, 0))

        tree = ttk.Treeview(frame_lista, columns=("nombre", "grupo", "desc"), show="headings", height=9)
        tree.heading("nombre", text="Fresa")
        tree.heading("grupo", text="Grupo")
        tree.heading("desc", text="Descripción del corte")
        tree.column("nombre", width=190, anchor="w")
        tree.column("grupo", width=90, anchor="w")
        tree.column("desc", width=420, anchor="w")
        tree.pack(fill="both", expand=True)

        datos = {}

        def limpiar_det():
            txt_det.config(state="normal"); txt_det.delete("1.0", tk.END); txt_det.config(state="disabled")
            entry_claves_det.delete(0, tk.END)
            btn_guardar_edit.config(state="disabled")
            btn_foto.config(state="disabled")
            lbl_foto.config(image="", text="sin foto"); lbl_foto.image = None

        def cargar():
            for i in tree.get_children():
                tree.delete(i)
            datos.clear()
            try:
                res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/fresas_cortes", timeout=30)
                if res.status_code != 200:
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
                    return
                for c in res.json():
                    if not c.get("activo", True):
                        continue
                    datos[str(c["id"])] = c
                    nombre_disp = ("📷 " if c.get("tiene_imagen") else "") + (c.get("nombre", "") or "")
                    tree.insert("", tk.END, iid=str(c["id"]),
                                values=(nombre_disp, c.get("grupo", "") or "", c.get("descripcion_corte", "") or ""))
            except Exception as e:
                messagebox.showerror("Error de Conexión", f"No se pudo conectar con el servidor.\n{e}", parent=vent)
            btn_eliminar.config(state="disabled")
            limpiar_det()

        def agregar():
            nombre = entry_nombre.get().strip()
            desc = txt_desc.get("1.0", tk.END).strip()
            if len(nombre) < 2 or len(desc) < 5:
                messagebox.showwarning("Faltan datos", "Poné el nombre de la fresa y cómo se ve el corte.", parent=vent)
                return
            payload = {"nombre": nombre, "grupo": combo_grupo.get(),
                       "descripcion_corte": desc, "palabras_clave": entry_claves.get().strip()}
            try:
                res = requests.post(f"{URL_SERVIDOR_RENDER.rstrip('/')}/fresas_corte", json=payload, timeout=30)
                if res.status_code == 200:
                    entry_nombre.delete(0, tk.END); txt_desc.delete("1.0", tk.END)
                    entry_claves.delete(0, tk.END); combo_grupo.set("")
                    cargar()
                else:
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
            except Exception as e:
                messagebox.showerror("Error de Conexión", f"No se pudo guardar.\n{e}", parent=vent)

        def on_select(evt):
            sel = tree.selection()
            if not sel:
                btn_eliminar.config(state="disabled"); limpiar_det(); return
            btn_eliminar.config(state="normal")
            c = datos.get(sel[0], {})
            txt_det.config(state="normal"); txt_det.delete("1.0", tk.END)
            txt_det.insert("1.0", c.get("descripcion_corte", "") or "")
            combo_det.set(c.get("grupo", "") or "")
            entry_claves_det.delete(0, tk.END); entry_claves_det.insert(0, c.get("palabras_clave", "") or "")
            btn_guardar_edit.config(state="normal")
            btn_foto.config(state="normal")
            mostrar_foto(sel[0])

        def mostrar_foto(cid):
            try:
                res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/fresas_cortes/{cid}/imagen", timeout=30)
                if res.status_code == 200:
                    img = Image.open(io.BytesIO(res.content)); img.thumbnail((150, 120))
                    ph = ImageTk.PhotoImage(img)
                    lbl_foto.config(image=ph, text=""); lbl_foto.image = ph
                    return
            except Exception:
                pass
            lbl_foto.config(image="", text="sin foto"); lbl_foto.image = None

        def subir_foto_corte():
            sel = tree.selection()
            if not sel:
                return
            ruta = filedialog.askopenfilename(
                title="Foto de referencia del corte",
                filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp"), ("Todos", "*.*")], parent=vent)
            if not ruta:
                return
            try:
                with open(ruta, "rb") as fh:
                    res = requests.post(f"{URL_SERVIDOR_RENDER.rstrip('/')}/fresas_cortes/{sel[0]}/imagen",
                                        files={"foto": fh}, timeout=60)
                if res.status_code == 200:
                    cid = sel[0]
                    cargar()
                    try:
                        tree.selection_set(cid); tree.see(cid)
                    except Exception:
                        pass
                else:
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo subir la foto.\n{e}", parent=vent)

        def guardar_edit():
            sel = tree.selection()
            if not sel:
                return
            desc = txt_det.get("1.0", tk.END).strip()
            if len(desc) < 5:
                messagebox.showwarning("Vacío", "La descripción no puede quedar vacía.", parent=vent)
                return
            payload = {"descripcion_corte": desc, "grupo": combo_det.get(), "palabras_clave": entry_claves_det.get().strip()}
            try:
                res = requests.post(f"{URL_SERVIDOR_RENDER.rstrip('/')}/fresas_cortes/{sel[0]}/editar", json=payload, timeout=30)
                if res.status_code == 200:
                    messagebox.showinfo("Guardado", "Corte actualizado. El bot lo usa en la próxima foto.", parent=vent)
                    cargar()
                else:
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
            except Exception as e:
                messagebox.showerror("Error de Conexión", f"No se pudo guardar.\n{e}", parent=vent)

        def eliminar():
            sel = tree.selection()
            if not sel:
                return
            if not messagebox.askyesno("Eliminar", "¿Borrar este corte de la guía?", parent=vent):
                return
            try:
                requests.delete(f"{URL_SERVIDOR_RENDER.rstrip('/')}/fresas_cortes/{sel[0]}", timeout=30)
                cargar()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo borrar.\n{e}", parent=vent)

        def probar_foto():
            ruta = filedialog.askopenfilename(
                title="Elegí una foto del corte",
                filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.webp *.bmp"), ("Todos", "*.*")],
                parent=vent)
            if not ruta:
                return
            btn_probar.config(state="disabled", text="⏳ Analizando...")
            vent.update()
            try:
                with open(ruta, "rb") as fh:
                    res = requests.post(f"{URL_SERVIDOR_RENDER.rstrip('/')}/identificar_corte",
                                        files={"foto": fh}, timeout=90)
                if res.status_code == 200:
                    messagebox.showinfo("El bot identificó", res.json().get("resultado", "(sin respuesta)"), parent=vent)
                else:
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo analizar la foto.\n{e}", parent=vent)
            finally:
                btn_probar.config(state="normal", text="🔍 Probar con una foto")

        btn_agregar.config(command=agregar)
        btn_actualizar.config(command=cargar)
        btn_probar.config(command=probar_foto)
        btn_eliminar.config(command=eliminar)
        btn_guardar_edit.config(command=guardar_edit)
        btn_foto.config(command=subir_foto_corte)
        tree.bind("<<TreeviewSelect>>", on_select)

        cargar()

    def abrir_correcciones_bot(self):
        """Ventana para enseñarle/corregir al bot. Usa los endpoints /aprendizaje(s)
        del servidor: las correcciones se aplican en el próximo mensaje, sin redeploy."""
        vent = tk.Toplevel(self.root)
        vent.title("Enseñar / Corregir al Bot")
        vent.geometry("880x820")
        vent.configure(bg="white")

        AMBITOS = ["global", "Sierras", "Fresas", "Mechas", "Cuchillas", "Diamante", "Cabezales", "atencion"]

        # --- FORMULARIO (arriba) ---
        frame_form = tk.LabelFrame(vent, text="  Nueva corrección  ", bg="white",
                                   font=("Arial", 11, "bold"), fg=COLOR_ROJO_WT, padx=12, pady=10)
        frame_form.pack(fill="x", padx=12, pady=(12, 8))

        fila1 = tk.Frame(frame_form, bg="white")
        fila1.pack(fill="x", pady=(0, 6))
        tk.Label(fila1, text="¿Para qué familia?", bg="white", font=("Arial", 10, "bold")).pack(side="left")
        combo_ambito = ttk.Combobox(fila1, values=AMBITOS, state="readonly", width=18)
        combo_ambito.set("global")
        combo_ambito.pack(side="left", padx=(8, 0))
        tk.Label(fila1, text="(global = vale para todas)", bg="white", fg="#888", font=("Arial", 9)).pack(side="left", padx=8)

        tk.Label(frame_form, text="Situación (opcional, una nota para vos):", bg="white",
                 font=("Arial", 10)).pack(anchor="w")
        entry_situacion = tk.Entry(frame_form, font=("Arial", 11), relief="solid", bd=1)
        entry_situacion.pack(fill="x", pady=(2, 8))

        tk.Label(frame_form, text="Decile con tus palabras qué debe hacer (el bot lo resume y aprende solo):", bg="white",
                 font=("Arial", 10, "bold")).pack(anchor="w")
        txt_leccion = tk.Text(frame_form, font=("Arial", 11), height=4, wrap="word",
                              relief="solid", bd=1, highlightbackground="#ccc", highlightthickness=1)
        txt_leccion.pack(fill="x", pady=(2, 8))

        btn_guardar = tk.Button(frame_form, text="🤖 Que el bot lo aprenda", bg="#4CAF50", fg="white",
                                font=("Arial", 11, "bold"), relief="flat", pady=8)
        btn_guardar.pack(fill="x")

        # --- LISTA (abajo) ---
        frame_lista = tk.LabelFrame(vent, text="  Correcciones cargadas  ", bg="white",
                                    font=("Arial", 11, "bold"), fg=COLOR_ROJO_WT, padx=12, pady=10)
        frame_lista.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        frame_bar = tk.Frame(frame_lista, bg="white")
        frame_bar.pack(fill="x", pady=(0, 6))
        btn_actualizar = tk.Button(frame_bar, text="🔄 Actualizar", bg="#2196F3", fg="white",
                                   font=("Arial", 9, "bold"), relief="flat", padx=10)
        btn_actualizar.pack(side="left")
        tk.Label(frame_bar, text="🟡 = propuesta del bot (aprobala para que la use)", bg="white",
                 fg="#888", font=("Arial", 9)).pack(side="left", padx=10)
        btn_eliminar = tk.Button(frame_bar, text="🗑 Eliminar / Rechazar", bg="#e74c3c", fg="white",
                                 font=("Arial", 9, "bold"), relief="flat", padx=10, state="disabled")
        btn_eliminar.pack(side="right")
        btn_aprobar = tk.Button(frame_bar, text="✅ Aprobar", bg="#4CAF50", fg="white",
                                font=("Arial", 9, "bold"), relief="flat", padx=10, state="disabled")
        btn_aprobar.pack(side="right", padx=(0, 6))

        tree = ttk.Treeview(frame_lista, columns=("estado", "ambito", "leccion"), show="headings", height=10)
        tree.heading("estado", text="Estado")
        tree.heading("ambito", text="Familia")
        tree.heading("leccion", text="Corrección")
        tree.column("estado", width=90, anchor="w")
        tree.column("ambito", width=100, anchor="w")
        tree.column("leccion", width=510, anchor="w")
        tree.tag_configure("pendiente", background="#fff7e0")

        # --- Panel para VER COMPLETA y EDITAR la corrección seleccionada ---
        detalle = tk.LabelFrame(frame_lista, text="  Ver / Editar la corrección seleccionada  ",
                                bg="white", font=("Arial", 10, "bold"), fg=COLOR_ROJO_WT, padx=10, pady=8)
        detalle.pack(side="bottom", fill="x", pady=(8, 0))
        fila_det = tk.Frame(detalle, bg="white")
        fila_det.pack(fill="x", pady=(0, 4))
        tk.Label(fila_det, text="Familia:", bg="white", font=("Arial", 9, "bold")).pack(side="left")
        combo_det = ttk.Combobox(fila_det, values=AMBITOS, state="readonly", width=14)
        combo_det.pack(side="left", padx=(6, 0))
        btn_guardar_edit = tk.Button(fila_det, text="💾 Guardar cambios", bg="#2196F3", fg="white",
                                     font=("Arial", 9, "bold"), relief="flat", padx=10, state="disabled")
        btn_guardar_edit.pack(side="right")
        txt_detalle = tk.Text(detalle, font=("Arial", 11), height=4, wrap="word", relief="solid", bd=1,
                              highlightbackground="#ccc", highlightthickness=1, state="disabled")
        txt_detalle.pack(fill="x")

        tree.pack(fill="both", expand=True)

        estados = {}
        datos = {}

        def limpiar_detalle():
            txt_detalle.config(state="normal")
            txt_detalle.delete("1.0", tk.END)
            txt_detalle.config(state="disabled")
            btn_guardar_edit.config(state="disabled")

        def cargar_lista():
            for i in tree.get_children():
                tree.delete(i)
            estados.clear()
            datos.clear()
            try:
                res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/aprendizajes", timeout=30)
                if res.status_code != 200:
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
                    return
                for a in res.json():
                    if not a.get("activo", True):
                        continue
                    est = a.get("estado", "aprobado")
                    etiqueta = "🟡 pendiente" if est == "pendiente" else "✅ activa"
                    tags = ("pendiente",) if est == "pendiente" else ()
                    estados[str(a["id"])] = est
                    datos[str(a["id"])] = a
                    tree.insert("", tk.END, iid=str(a["id"]), tags=tags,
                                values=(etiqueta, a.get("ambito", ""), (a.get("leccion", "") or "")))
            except Exception as e:
                messagebox.showerror("Error de Conexión", f"No se pudo conectar con el servidor.\n{e}", parent=vent)
            btn_eliminar.config(state="disabled")
            btn_aprobar.config(state="disabled")
            limpiar_detalle()

        def guardar():
            leccion = txt_leccion.get("1.0", tk.END).strip()
            if len(leccion) < 5:
                messagebox.showwarning("Falta la corrección", "Escribí con tus palabras qué debe hacer el bot.", parent=vent)
                return
            nota = entry_situacion.get().strip()
            texto = (nota + ". " + leccion) if nota else leccion
            payload = {"ambito": combo_ambito.get() or "global", "texto": texto}
            btn_guardar.config(state="disabled", text="⏳ El bot está aprendiendo...")
            vent.update()
            try:
                res = requests.post(f"{URL_SERVIDOR_RENDER.rstrip('/')}/aprender", json=payload, timeout=45)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("status") == "ok":
                        txt_leccion.delete("1.0", tk.END)
                        entry_situacion.delete(0, tk.END)
                        messagebox.showinfo("Aprendido",
                            f"El bot lo entendió como:\n\n«{data.get('leccion','')}»\n\nLo aplica desde el próximo mensaje.",
                            parent=vent)
                        cargar_lista()
                    else:
                        messagebox.showwarning("No se guardó", data.get("motivo", "No se pudo sacar una regla útil de eso."), parent=vent)
                else:
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
            except Exception as e:
                messagebox.showerror("Error de Conexión", f"No se pudo conectar con el servidor.\n{e}", parent=vent)
            finally:
                btn_guardar.config(state="normal", text="🤖 Que el bot lo aprenda")

        def on_select(evt):
            sel = tree.selection()
            hay = bool(sel)
            btn_eliminar.config(state="normal" if hay else "disabled")
            btn_aprobar.config(state="normal" if (hay and estados.get(sel[0]) == "pendiente") else "disabled")
            if hay:
                a = datos.get(sel[0], {})
                txt_detalle.config(state="normal")
                txt_detalle.delete("1.0", tk.END)
                txt_detalle.insert("1.0", a.get("leccion", "") or "")
                combo_det.set(a.get("ambito", "global") or "global")
                btn_guardar_edit.config(state="normal")
            else:
                limpiar_detalle()

        def guardar_edit():
            sel = tree.selection()
            if not sel:
                return
            nuevo = txt_detalle.get("1.0", tk.END).strip()
            if len(nuevo) < 3:
                messagebox.showwarning("Texto vacío", "La corrección no puede quedar vacía.", parent=vent)
                return
            payload = {"leccion": nuevo, "ambito": combo_det.get() or ""}
            btn_guardar_edit.config(state="disabled", text="⏳ Guardando...")
            vent.update()
            try:
                res = requests.post(f"{URL_SERVIDOR_RENDER.rstrip('/')}/aprendizajes/{sel[0]}/editar", json=payload, timeout=30)
                if res.status_code == 200:
                    messagebox.showinfo("Guardado", "Corrección actualizada. El bot la usa así desde el próximo mensaje.", parent=vent)
                    cargar_lista()
                else:
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
            except Exception as e:
                messagebox.showerror("Error de Conexión", f"No se pudo guardar.\n{e}", parent=vent)
            finally:
                btn_guardar_edit.config(state="normal", text="💾 Guardar cambios")

        def aprobar():
            sel = tree.selection()
            if not sel:
                return
            try:
                requests.post(f"{URL_SERVIDOR_RENDER.rstrip('/')}/aprendizajes/{sel[0]}/aprobar", timeout=30)
                cargar_lista()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo aprobar.\n{e}", parent=vent)

        def eliminar():
            sel = tree.selection()
            if not sel:
                return
            if not messagebox.askyesno("Eliminar", "¿Borrar/rechazar esta corrección?", parent=vent):
                return
            try:
                requests.delete(f"{URL_SERVIDOR_RENDER.rstrip('/')}/aprendizajes/{sel[0]}", timeout=30)
                cargar_lista()
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo borrar.\n{e}", parent=vent)

        btn_guardar.config(command=guardar)
        btn_actualizar.config(command=cargar_lista)
        btn_eliminar.config(command=eliminar)
        btn_aprobar.config(command=aprobar)
        btn_guardar_edit.config(command=guardar_edit)
        tree.bind("<<TreeviewSelect>>", on_select)

        cargar_lista()

    # ==========================================
    # FOTOS DE LOS CHATS (las que manda el cliente)
    # ==========================================
    RE_MARCA_IMG = re.compile(r'\[Imagen analizada\s*#(\d+)\]', re.IGNORECASE)

    MAX_INTENTOS_FOTO = 3

    def _descargar_foto_chat(self, img_id, cuando_termine):
        """Baja la foto del servidor en segundo plano y la deja en el caché."""
        if not hasattr(self, "_fotos_chat"):
            self._fotos_chat = {}
        if not hasattr(self, "_intentos_foto"):
            self._intentos_foto = {}
        if not hasattr(self, "_esperan_foto"):
            self._esperan_foto = {}
        if img_id in self._fotos_chat:
            # Ya se está bajando: se anota este panel para avisarle también cuando llegue
            if self._fotos_chat[img_id] is None and cuando_termine not in self._esperan_foto.get(img_id, []):
                self._esperan_foto.setdefault(img_id, []).append(cuando_termine)
            return
        self._fotos_chat[img_id] = None  # marca "descargando" para no pedirla dos veces
        self._esperan_foto[img_id] = [cuando_termine]
        self._intentos_foto[img_id] = self._intentos_foto.get(img_id, 0) + 1

        def tarea():
            datos = False
            try:
                res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/chat_imagen/{img_id}", timeout=40)
                if res.status_code == 200 and res.content:
                    datos = res.content
                elif res.status_code == 404:
                    datos = "vencida"   # la foto ya se borró del servidor (pasaron 90 días)
            except Exception as e:
                mainCode.log_error(f"No se pudo bajar la foto {img_id}: {e}")

            if datos is False:
                # Error de red: se reintenta al reabrir el chat, pero con un tope para no
                # quedar pidiéndola en bucle si el servidor está caído.
                if self._intentos_foto.get(img_id, 0) >= self.MAX_INTENTOS_FOTO:
                    self._fotos_chat[img_id] = "error"
                else:
                    self._fotos_chat.pop(img_id, None)
            else:
                self._fotos_chat[img_id] = datos

            avisar = self._esperan_foto.pop(img_id, [])
            for cb in avisar:
                try:
                    self.root.after(0, cb)
                except Exception:
                    pass  # se cerró el programa mientras bajaba la foto

        threading.Thread(target=tarea, daemon=True).start()

    def _ver_foto_grande(self, datos, titulo="Foto del cliente"):
        """Abre la foto en una ventana aparte, a tamaño completo."""
        try:
            vent = tk.Toplevel(self.root)
            vent.title(titulo)
            vent.configure(bg="#222")
            img = Image.open(io.BytesIO(datos))
            ancho_max, alto_max = 1000, 700
            if img.width > ancho_max or img.height > alto_max:
                escala = min(ancho_max / img.width, alto_max / img.height)
                img = img.resize((int(img.width * escala), int(img.height * escala)), Image.Resampling.LANCZOS)
            foto = ImageTk.PhotoImage(img)
            lbl = tk.Label(vent, image=foto, bg="#222")
            lbl.image = foto  # referencia para que no la borre el recolector
            lbl.pack(padx=10, pady=10)
        except Exception as e:
            messagebox.showerror("Foto", f"No se pudo abrir la foto.\n{e}")

    def _pintar_historial(self, txt, historial, telefono="", fecha=""):
        """Escribe el chat en el widget mostrando las FOTOS que mandó el cliente
        (antes solo se veía el texto '[Imagen analizada]')."""
        if not hasattr(self, "_fotos_chat"):
            self._fotos_chat = {}
        if not hasattr(self, "_refs_fotos"):
            self._refs_fotos = {}

        # Token del chat que se está mostrando: si el usuario cambia de conversación
        # mientras baja una foto, el repintado tardío se descarta (antes pisaba el chat nuevo).
        token = (id(txt), telefono, id(historial))
        if not hasattr(self, "_token_chat"):
            self._token_chat = {}
        self._token_chat[id(txt)] = token

        def repintar():
            try:
                if not txt.winfo_exists():
                    return  # se cerró la ventana mientras bajaba la foto
            except Exception:
                return
            if self._token_chat.get(id(txt)) != token:
                return  # ya se está mirando otro chat
            self._pintar_historial(txt, historial, telefono, fecha)

        # Se destruyen las miniaturas del pintado anterior (si no, quedan colgadas en memoria)
        for w in list(txt.children.values()):
            try: w.destroy()
            except Exception: pass
        self._refs_fotos.pop(id(txt), None)
        refs = self._refs_fotos.setdefault(id(txt), [])
        del refs[:]

        pos_scroll = txt.yview()[0]  # para no perder el punto donde estaba leyendo
        txt.config(state="normal")
        txt.delete("1.0", tk.END)
        if telefono:
            txt.insert(tk.END, f"📱 Cliente: +{telefono}\n")
        if fecha:
            txt.insert(tk.END, f"📅 {fecha}\n")
        if telefono or fecha:
            txt.insert(tk.END, "-" * 50 + "\n\n")

        for msg in historial or []:
            texto = (msg.get('parts', [''])or[''])[0] or ''
            if "Eres el asistente virtual" in texto or "BASE_CONOCIMIENTO" in texto:
                continue
            rol = "🤖 BOT" if msg.get('role') == 'model' else "👤 CLIENTE"

            ids_fotos = [int(x) for x in self.RE_MARCA_IMG.findall(texto)]
            # se saca el marcador del texto; la foto se dibuja aparte
            limpio = self.RE_MARCA_IMG.sub('', texto)
            # Fotos viejas (antes de esta versión): no se guardaron, no hay nada para mostrar
            limpio = re.sub(r'\[Imagen analizada\]', '📷 (foto no guardada)', limpio, flags=re.IGNORECASE)
            limpio = re.sub(r'\[AGENDADO:\s*.*?\]', '', limpio, flags=re.IGNORECASE).strip()

            if not ids_fotos and not limpio:
                continue

            txt.insert(tk.END, f"{rol}:\n")
            for img_id in ids_fotos:
                datos = self._fotos_chat.get(img_id, "no-pedida")
                if datos == "no-pedida":
                    txt.insert(tk.END, "   ⏳ cargando foto...\n")
                    self._descargar_foto_chat(img_id, repintar)
                elif datos is None:
                    txt.insert(tk.END, "   ⏳ cargando foto...\n")
                elif datos == "vencida":
                    txt.insert(tk.END, "   📷 (foto vencida: pasaron más de 90 días)\n")
                elif datos == "error":
                    txt.insert(tk.END, "   📷 (no se pudo cargar la foto; reabrí la ventana para reintentar)\n")
                else:
                    try:
                        # La miniatura se guarda ya armada para no rehacerla en cada repintado
                        if not hasattr(self, "_mini_cache"):
                            self._mini_cache = {}
                        if img_id not in self._mini_cache:
                            img = Image.open(io.BytesIO(datos))
                            img.thumbnail((260, 260), Image.Resampling.LANCZOS)
                            self._mini_cache[img_id] = ImageTk.PhotoImage(img)
                        foto = self._mini_cache[img_id]
                        lbl = tk.Label(txt, image=foto, cursor="hand2", bd=1, relief="solid")
                        lbl.image = foto
                        lbl.bind("<Button-1>", lambda e, d=datos: self._ver_foto_grande(d))
                        txt.window_create(tk.END, window=lbl)
                        refs.append(foto)
                        txt.insert(tk.END, "\n   (clic en la foto para verla grande)\n")
                    except Exception:
                        txt.insert(tk.END, "   📷 (foto dañada)\n")
            if limpio:
                txt.insert(tk.END, f"{limpio}\n")
            txt.insert(tk.END, "\n")

        txt.config(state="disabled")
        if pos_scroll:
            try: txt.yview_moveto(pos_scroll)
            except Exception: pass

    # ==========================================
    # MONITOR DEL SERVIDOR (qué dice el servidor)
    # ==========================================
    def _text_con_scroll(self, parent, **kw):
        """Devuelve (contenedor, Text) con barra de desplazamiento vertical."""
        cont = tk.Frame(parent, bg="white")
        sb = ttk.Scrollbar(cont, orient="vertical")
        txt = tk.Text(cont, yscrollcommand=sb.set, **kw)
        sb.config(command=txt.yview)
        sb.pack(side="right", fill="y")
        txt.pack(side="left", fill="both", expand=True)
        return cont, txt

    def abrir_monitor_servidor(self):
        """Ventana con lo que dice el servidor: Monitor (estado en vivo),
        Conversaciones (/derivados) y JSON crudo de cada endpoint."""
        vent = tk.Toplevel(self.root)
        vent.title("Servidor — ¿Qué dice el servidor?")
        vent.geometry("1060x720")
        vent.configure(bg="white")

        nb = ttk.Notebook(vent)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        # ---------- PESTAÑA 1: MONITOR ----------
        tab_mon = tk.Frame(nb, bg="white"); nb.add(tab_mon, text="  📊 Monitor  ")
        top_mon = tk.Frame(tab_mon, bg="white"); top_mon.pack(fill="x", pady=(8, 4), padx=10)
        tk.Label(top_mon, text="Estado del servidor en vivo", bg="white",
                 font=("Segoe UI", 13, "bold")).pack(side="left")
        btn_ref_mon = tk.Button(top_mon, text="🔄 Actualizar", bg="#2196F3", fg="white",
                                font=("Segoe UI", 9, "bold"), relief="flat", padx=10)
        btn_ref_mon.pack(side="right")
        cont_mon, txt_mon = self._text_con_scroll(tab_mon, font=("Consolas", 11), wrap="word",
                                                  state="disabled", relief="flat",
                                                  highlightbackground="#ccc", highlightthickness=1, bg="#fbfbfb")
        cont_mon.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def cargar_monitor():
            btn_ref_mon.config(state="disabled", text="⏳ Consultando...")
            def tarea():
                online = mainCode.consultar_servidor("/", timeout=40)
                estado = mainCode.consultar_servidor("/estado_bot")
                metricas = mainCode.consultar_servidor("/metricas")
                derivados = mainCode.consultar_servidor("/derivados")
                aprend = mainCode.consultar_servidor("/aprendizajes")
                self.root.after(0, lambda: pintar_monitor(online, estado, metricas, derivados, aprend))
            threading.Thread(target=tarea, daemon=True).start()

        def pintar_monitor(online, estado, metricas, derivados, aprend):
            L = []
            L.append("🟢 SERVIDOR EN LÍNEA" if online["ok"] else f"🔴 SERVIDOR SIN CONEXIÓN (código {online['status']})")
            L.append("")
            if estado["ok"] and isinstance(estado["json"], dict):
                L.append(f"🤖 BOT:  {estado['json'].get('configuracion', '?')}   (modo: {estado['json'].get('modo_actual', '?')})")
            else:
                L.append("🤖 BOT:  no se pudo leer /estado_bot")
            L.append("")
            if metricas["ok"] and isinstance(metricas["json"], dict):
                m = metricas["json"]
                tot = {"entregados": 0, "leidos": 0, "respondidos": 0, "derivados": 0}
                for v in m.values():
                    for k in tot:
                        try: tot[k] += int(v.get(k, 0))
                        except Exception: pass
                L.append("📈 MÉTRICAS (todas las campañas):")
                L.append(f"     Entregados: {tot['entregados']}   Leídos: {tot['leidos']}   Respondidos: {tot['respondidos']}   Derivados: {tot['derivados']}")
                L.append(f"     Campañas registradas: {len(m)}")
                for camp, v in m.items():
                    L.append(f"       • {camp}: entregados {v.get('entregados', 0)}, leídos {v.get('leidos', 0)}, respondidos {v.get('respondidos', 0)}, derivados {v.get('derivados', 0)}")
            else:
                L.append("📈 MÉTRICAS: no se pudo leer /metricas")
            L.append("")
            n_der = len(derivados["json"]) if (derivados["ok"] and isinstance(derivados["json"], list)) else "?"
            L.append(f"💬 CHATS DERIVADOS (pendientes de atención): {n_der}")
            if aprend["ok"] and isinstance(aprend["json"], list):
                activos = sum(1 for a in aprend["json"] if a.get("activo"))
                L.append(f"🎓 APRENDIZAJES: {len(aprend['json'])} (activos: {activos})")
            else:
                L.append("🎓 APRENDIZAJES: no se pudo leer /aprendizajes")
            L.append("")
            L.append(f"Actualizado: {mainCode.hora_arg().strftime('%d/%m/%Y %H:%M:%S')} (hora Arg)")
            txt_mon.config(state="normal"); txt_mon.delete("1.0", tk.END)
            txt_mon.insert(tk.END, "\n".join(L)); txt_mon.config(state="disabled")
            btn_ref_mon.config(state="normal", text="🔄 Actualizar")

        btn_ref_mon.config(command=cargar_monitor)

        # ---------- PESTAÑA 2: CONVERSACIONES ----------
        tab_conv = tk.Frame(nb, bg="white"); nb.add(tab_conv, text="  💬 Conversaciones  ")
        izq = tk.Frame(tab_conv, width=340, bg="white"); izq.pack(side="left", fill="y", padx=10, pady=10); izq.pack_propagate(False)
        der = tk.Frame(tab_conv, bg="white"); der.pack(side="right", fill="both", expand=True, padx=10, pady=10)
        top_conv = tk.Frame(izq, bg="white"); top_conv.pack(fill="x")
        tk.Label(top_conv, text="Conversaciones derivadas", bg="white", font=("Segoe UI", 12, "bold")).pack(side="left")
        btn_ref_conv = tk.Button(top_conv, text="🔄", bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=6)
        btn_ref_conv.pack(side="right")
        frame_lc = tk.Frame(izq, bg="white"); frame_lc.pack(fill="both", expand=True, pady=(6, 0))
        sb_lc = ttk.Scrollbar(frame_lc, orient="vertical")
        lista_conv = tk.Listbox(frame_lc, font=("Segoe UI", 10), relief="solid", bd=1, highlightthickness=0, yscrollcommand=sb_lc.set)
        sb_lc.config(command=lista_conv.yview); sb_lc.pack(side="right", fill="y"); lista_conv.pack(side="left", fill="both", expand=True)
        tk.Label(der, text="Historial (lo que dijo el cliente y lo que respondió el bot)", bg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        cont_conv, txt_conv = self._text_con_scroll(der, font=("Segoe UI", 11), wrap="word", state="disabled",
                                                    relief="flat", highlightbackground="#ccc", highlightthickness=1)
        cont_conv.pack(fill="both", expand=True, pady=(6, 0))
        self._conv_datos = []

        def cargar_conv():
            btn_ref_conv.config(state="disabled")
            def tarea():
                r = mainCode.consultar_servidor("/derivados")
                self.root.after(0, lambda: pintar_conv(r))
            threading.Thread(target=tarea, daemon=True).start()

        def pintar_conv(r):
            lista_conv.delete(0, tk.END)
            txt_conv.config(state="normal"); txt_conv.delete("1.0", tk.END); txt_conv.config(state="disabled")
            self._conv_datos = r["json"] if (r["ok"] and isinstance(r["json"], list)) else []
            if not self._conv_datos:
                lista_conv.insert(tk.END, "(sin conversaciones o sin conexión)")
            for d in self._conv_datos:
                fecha = str(d.get("fecha", "")).split(".")[0]
                lista_conv.insert(tk.END, f"+{d.get('telefono', '?')}   {fecha}")
            btn_ref_conv.config(state="normal")

        def mostrar_conv(evt):
            sel = lista_conv.curselection()
            if not sel or not self._conv_datos or sel[0] >= len(self._conv_datos):
                return
            d = self._conv_datos[sel[0]]
            self._pintar_historial(txt_conv, d.get("historial", []),
                                   telefono=d.get("telefono", "?"), fecha=d.get("fecha", ""))

        lista_conv.bind("<<ListboxSelect>>", mostrar_conv)
        btn_ref_conv.config(command=cargar_conv)

        # ---------- PESTAÑA 3: JSON CRUDO ----------
        tab_raw = tk.Frame(nb, bg="white"); nb.add(tab_raw, text="  🧾 JSON crudo  ")
        top_raw = tk.Frame(tab_raw, bg="white"); top_raw.pack(fill="x", pady=(8, 4), padx=10)
        tk.Label(top_raw, text="Endpoint:", bg="white", font=("Segoe UI", 10, "bold")).pack(side="left")
        combo_ep = ttk.Combobox(top_raw, state="readonly", width=26,
                                values=["/", "/estado_bot", "/derivados", "/metricas", "/tracking_general", "/aprendizajes", "/fresas_cortes"])
        combo_ep.pack(side="left", padx=8); combo_ep.current(1)
        btn_raw = tk.Button(top_raw, text="Consultar", bg="#2196F3", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=12)
        btn_raw.pack(side="left")
        lbl_raw_status = tk.Label(top_raw, text="", bg="white", fg="#555", font=("Segoe UI", 9))
        lbl_raw_status.pack(side="left", padx=10)
        cont_raw, txt_raw = self._text_con_scroll(tab_raw, font=("Consolas", 10), wrap="word", state="disabled",
                                                  relief="flat", highlightbackground="#ccc", highlightthickness=1,
                                                  bg="#1e1e1e", fg="#d4d4d4", insertbackground="white")
        cont_raw.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        def consultar_raw():
            ep = combo_ep.get() or "/estado_bot"
            btn_raw.config(state="disabled"); lbl_raw_status.config(text="Consultando...")
            def tarea():
                r = mainCode.consultar_servidor(ep, timeout=40)
                self.root.after(0, lambda: pintar_raw(ep, r))
            threading.Thread(target=tarea, daemon=True).start()

        def pintar_raw(ep, r):
            if r["json"] is not None:
                try: cuerpo = json.dumps(r["json"], indent=2, ensure_ascii=False)
                except Exception: cuerpo = r["texto"]
            else:
                cuerpo = r["texto"]
            txt_raw.config(state="normal"); txt_raw.delete("1.0", tk.END)
            txt_raw.insert(tk.END, cuerpo); txt_raw.config(state="disabled")
            lbl_raw_status.config(text=f"GET {ep}  →  código {r['status']}")
            btn_raw.config(state="normal")

        btn_raw.config(command=consultar_raw)

        # Cargas iniciales
        cargar_monitor()
        cargar_conv()
        consultar_raw()

    def abrir_chats_derivados(self):
        vent = tk.Toplevel(self.root)
        vent.title("Chats Pendientes / Requieren Atención")
        vent.geometry("1000x700")
        vent.configure(bg="white")

        frame_izq = tk.Frame(vent, width=320, bg="white")
        frame_izq.pack(side="left", fill="y", padx=10, pady=10)
        frame_izq.pack_propagate(False)

        frame_der = tk.Frame(vent, bg="white")
        frame_der.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        # IZQUIERDA: Header y Pestañas
        tk.Label(frame_izq, text="Lista de Clientes", bg="white", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 5))
        
        frame_botones_tabs = tk.Frame(frame_izq, bg="white")
        frame_botones_tabs.pack(fill="x", pady=(0, 5))
        
        self.btn_tab_pendientes = tk.Button(frame_botones_tabs, text="Pendientes", bg="#ff4c4c", fg="black", font=("Arial", 9, "bold"), relief="solid", bd=2)
        self.btn_tab_pendientes.pack(side="left", expand=True, fill="x", padx=(0,2))
        
        self.btn_tab_agendados = tk.Button(frame_botones_tabs, text="Hablar más adelante", bg="#d373ff", fg="black", font=("Arial", 9, "bold"), relief="solid", bd=1)
        self.btn_tab_agendados.pack(side="left", expand=True, fill="x", padx=(2,0))

        lista_chats = tk.Listbox(frame_izq, font=("Arial", 11), relief="solid", bd=1, highlightthickness=0)
        lista_chats.pack(fill="both", expand=True)

        # DERECHA: Header, Actualizar y Chat
        frame_der_top = tk.Frame(frame_der, bg="white")
        frame_der_top.pack(fill="x", pady=(0, 5))
        
        tk.Label(frame_der_top, text="Historial del Chat", bg="white", font=("Arial", 12, "bold")).pack(side="left")
        
        btn_actualizar = tk.Button(frame_der_top, text="🔄 Actualizar", bg="#2196F3", fg="white", font=("Arial", 9, "bold"), relief="flat", padx=10)
        btn_actualizar.pack(side="right")

        txt_chat = tk.Text(frame_der, font=("Arial", 11), wrap="word", state="disabled", relief="flat", highlightbackground="#ccc", highlightthickness=1)
        txt_chat.pack(fill="both", expand=True, pady=(0, 10))

        btn_resuelto = tk.Button(frame_der, text="☑ Marcar como Resuelto (Contactado)", bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), state="disabled", relief="flat", pady=8)
        btn_resuelto.pack(fill="x")

        btn_aprender_chat = tk.Button(frame_der, text="🎓 Enseñarle al bot de este chat", bg="#6a1b9a", fg="white", font=("Arial", 10, "bold"), state="disabled", relief="flat", pady=6)
        btn_aprender_chat.pack(fill="x", pady=(6, 0))

        def aprender_de_chat_sel():
            sel = lista_chats.curselection()
            if not sel or not self.datos_chats_actuales:
                return
            idx = sel[0]
            if idx not in self.lista_indices_map:
                return
            tel = self.datos_chats_actuales[self.lista_indices_map[idx]]['telefono']
            nota = simpledialog.askstring("Enseñar al bot",
                "¿Qué tendría que haber hecho distinto el bot en este chat?\n(opcional, ayuda a que aprenda mejor)",
                parent=vent) or ""
            btn_aprender_chat.config(state="disabled", text="⏳ El bot está analizando el chat...")
            vent.update()
            try:
                res = requests.post(f"{URL_SERVIDOR_RENDER.rstrip('/')}/aprender_de_chat",
                                    json={"telefono": tel, "nota": nota}, timeout=60)
                data = res.json() if res.status_code == 200 else {}
                if data.get("status") == "pendiente":
                    messagebox.showinfo("Propuesta lista",
                        f"El bot propone aprender:\n\n«{data.get('leccion','')}»\n\nQuedó PENDIENTE en Bot → Enseñar / Corregir al bot. Aprobala para que la use.",
                        parent=vent)
                else:
                    messagebox.showwarning("Sin lección", data.get("motivo", "El bot no encontró algo útil/seguro para aprender de este chat."), parent=vent)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo analizar el chat.\n{e}", parent=vent)
            finally:
                btn_aprender_chat.config(state="normal", text="🎓 Enseñarle al bot de este chat")

        btn_aprender_chat.config(command=aprender_de_chat_sel)

        # --- Lógica de Pestañas y Listas ---
        self.datos_chats_actuales = []
        self.datos_abandonados = []
        self.datos_agendados = []
        self.vista_actual = "pendientes"
        self.lista_indices_map = {}

        def cambiar_vista(vista):
            self.vista_actual = vista
            if vista == "pendientes":
                self.btn_tab_pendientes.config(bd=2, relief="solid")
                self.btn_tab_agendados.config(bd=1, relief="ridge")
            else:
                self.btn_tab_pendientes.config(bd=1, relief="ridge")
                self.btn_tab_agendados.config(bd=2, relief="solid")
            actualizar_listbox()

        self.btn_tab_pendientes.config(command=lambda: cambiar_vista("pendientes"))
        self.btn_tab_agendados.config(command=lambda: cambiar_vista("agendados"))

        def actualizar_listbox():
            lista_chats.delete(0, tk.END)
            self.lista_indices_map.clear()
            txt_chat.config(state="normal")
            txt_chat.delete("1.0", tk.END)
            txt_chat.config(state="disabled")
            btn_resuelto.config(state="disabled")
            
            if self.vista_actual == "pendientes":
                lista_chats.insert(tk.END, "🕰️ ABANDONADOS:")
                lista_chats.itemconfig(0, {'fg': 'white', 'bg': '#FF9800'})
                idx_lb = 1
                for real_idx, d in self.datos_abandonados:
                    nombre_vendedor = d.get('vendedor', 'Sin asigna')
                    for nombre, numeros in mainCode.DB_VENDEDORES.items():
                        if d.get('vendedor') in numeros: nombre_vendedor = nombre; break
                    lista_chats.insert(tk.END, f"  +{d['telefono']} ({nombre_vendedor})")
                    self.lista_indices_map[idx_lb] = real_idx
                    idx_lb += 1
            else:
                lista_chats.insert(tk.END, "📅 CONTACTAR EL DÍA:")
                lista_chats.itemconfig(0, {'fg': 'white', 'bg': '#2196F3'})
                idx_lb = 1
                for real_idx, d, info in self.datos_agendados:
                    nombre_vendedor = d.get('vendedor', 'Sin asigna')
                    for nombre, numeros in mainCode.DB_VENDEDORES.items():
                        if d.get('vendedor') in numeros: nombre_vendedor = nombre; break
                    lista_chats.insert(tk.END, f"  📌 {info}")
                    self.lista_indices_map[idx_lb] = real_idx
                    idx_lb += 1
                    lista_chats.insert(tk.END, f"      +{d['telefono']} ({nombre_vendedor})")
                    self.lista_indices_map[idx_lb] = real_idx
                    idx_lb += 1

        def cargar_datos():
            btn_actualizar.config(state="disabled", text="⏳...")
            vent.update()

            try:
                res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/derivados", timeout=30)
                if res.status_code == 200:
                    datos_crudos = res.json()
                else:
                    datos_crudos = []
                    messagebox.showerror("Error", f"El servidor respondió con código {res.status_code}.", parent=vent)
            except Exception as e:
                datos_crudos = []
                messagebox.showerror("Error de Conexión", f"No se pudo conectar con el servidor.\n{e}", parent=vent)

            self.datos_chats_actuales = datos_crudos
            self.datos_abandonados = []
            self.datos_agendados = []
            
            for idx_data, d in enumerate(datos_crudos):
                hist_str = json.dumps(d.get('historial', []))
                agendado_match = re.search(r'\[AGENDADO:\s*(.*?)\]', hist_str, re.IGNORECASE)
                if agendado_match:
                    info_agendado = agendado_match.group(1)
                    self.datos_agendados.append((idx_data, d, info_agendado))
                else:
                    self.datos_abandonados.append((idx_data, d))
                    
            actualizar_listbox()
            btn_actualizar.config(state="normal", text="🔄 Actualizar")

        btn_actualizar.config(command=cargar_datos)

        def mostrar_chat(evt):
            sel = lista_chats.curselection()
            if not sel or not self.datos_chats_actuales: return
            idx = sel[0]
            if idx not in self.lista_indices_map: return
            
            real_idx = self.lista_indices_map[idx]
            chat_data = self.datos_chats_actuales[real_idx]
            
            # Pinta el chat mostrando las fotos que mandó el cliente (no el marcador de texto)
            self._pintar_historial(txt_chat, chat_data.get('historial', []),
                                   telefono=chat_data.get('telefono', ''),
                                   fecha=f"Fecha de derivación: {chat_data.get('fecha', '')}")
            btn_resuelto.config(state="normal")
            btn_aprender_chat.config(state="normal")

        lista_chats.bind("<<ListboxSelect>>", mostrar_chat)

        def marcar_resuelto():
            sel = lista_chats.curselection()
            if not sel: return
            idx = sel[0]
            if idx not in self.lista_indices_map: return
            
            real_idx = self.lista_indices_map[idx]
            tel = self.datos_chats_actuales[real_idx]['telefono']
            try:
                requests.delete(f"{URL_SERVIDOR_RENDER.rstrip('/')}/derivados/{tel}")
                cargar_datos() 
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo borrar el chat.\nDetalle: {str(e)}", parent=vent)

        btn_resuelto.config(command=marcar_resuelto)

        cargar_datos()

    def verificar_observados(self):
        if self.df_filtrado.empty:
            return messagebox.showinfo("Aviso", "✅ No hay datos cargados.")
            
        df_descartados = self.df_filtrado[self.df_filtrado['Es_Valido'] == False]
        if df_descartados.empty:
            return messagebox.showinfo("Aviso", "✅ No hay números descartados en la lista actual filtrada.")
            
        msg = f"--- {len(df_descartados)} DESCARTADOS (En este filtro) ---\n\n"
        for _, row in df_descartados.iterrows():
            tels = row.get('Telefonos_Raw', [])
            cod = row.get('Código de cliente', '')
            texto_cod = f"[{cod}] " if cod else ""
            es_rev = " [LISTA NEGRA]" if row.get('Es_Revendedor') else ""
            msg += f"• {texto_cod}{row['Cliente']}{es_rev} -> {' | '.join(tels) if tels else 'Sin números'}\n"
        
        vent = tk.Toplevel(self.root)
        vent.title("Descartados (Filtrados)")
        vent.geometry("550x450")
        vent.configure(bg=COLOR_PANELES)
        
        t = tk.Text(vent, wrap="word", padx=10, pady=10, font=("Arial", 10))
        t.pack(fill="both", expand=True, padx=10, pady=10)
        t.insert("1.0", msg)
        t.config(state="disabled")

        def exportar_descartes_excel():
            datos_export = []
            for _, row in df_descartados.iterrows():
                tels = row.get('Telefonos_Raw', [])
                datos_export.append({
                    "Código de cliente": row.get('Código de cliente', ''),
                    "Nombre": row['Cliente'] + (" [Lista Negra]" if row.get('Es_Revendedor') else ""),
                    "Número": " | ".join(tels) if tels else "Sin número"
                })
                
            df_export = pd.DataFrame(datos_export)
            ruta_guardar = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel", "*.xlsx")],
                title="Guardar Descartes en Excel",
                initialfile=f"Descartados_WoodTools_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )
            
            if ruta_guardar:
                try:
                    df_export.to_excel(ruta_guardar, index=False)
                    messagebox.showinfo("Éxito", f"Base de descartados exportada perfectamente.\n\nGuardada en:\n{ruta_guardar}", parent=vent)
                except Exception as e:
                    messagebox.showerror("Error", f"No se pudo guardar el archivo:\n{e}", parent=vent)

        btn_exportar = tk.Button(vent, text="📥 Exportar a Excel", command=exportar_descartes_excel, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"))
        btn_exportar.pack(pady=10)

    def actualizar_preview(self, event=None):
        tipo = self.tipo_mensaje_var.get()
        nombre_ej = "[Nombre del Cliente]"
        herramienta_ej = "[Herramienta de interés]"
        if not self.df_filtrado.empty:
            df_ok = self.df_filtrado[self.df_filtrado['Es_Valido'] == True]
            if not df_ok.empty:
                nombre_ej = df_ok.iloc[0]['Cliente']
                herramienta_ej = df_ok.iloc[0].get('Fav_Temp', herramienta_ej)

        if tipo == "Promociones":
            prod_promo = self.entry_dinamico_texto.get().strip() or "Sierras"
            preview = f"[📷 IMAGEN]\nHola {nombre_ej} 👋 Te contactamos para contarte que tenemos promociones en {prod_promo}.\n¡Contactanos acá 👇 por más información!\n\n🔘 [ Enviar mensaje ]"
        elif tipo == "Rescate (Te extrañamos)":
            preview = f"[📷 IMAGEN]\n¡Hola {nombre_ej}! Vimos que hace tiempo no nos compras. Te invitamos a reponer tu stock de {herramienta_ej} para tu taller. Entrá a este link para más información 👉 [Link de WhatsApp] ¡Saludos!"
        elif tipo == "Gira Vendedor":
            v_corto = self.combo_vendedor.get()
            nombres_completos = {
                "Alan": "Alan Calvi", "Ezequiel": "Ezequiel Calvi", 
                "Luis": "Luis Quevedo", "Nicolas": "Nicolas Saad", 
                "Roberto": "Roberto Golik", "Ariel": "Ariel Sosa"
            }
            vend = nombres_completos.get(v_corto, v_corto)
            if v_corto == "AUTOMÁTICO (Según Planilla)":
                vend = "[Vendedor]"
                
            preview = f"¡Hola! Te avisamos que el vendedor {vend} estará visitando clientes por tu zona. Entrá a este link para coordinar la visita 👉 [Link de WhatsApp] ¡Nos vemos!"
        elif tipo == "Novedades":
            her = self.combo_novedad_herramienta.get() or "[Herramienta]"
            frase = "Acaban de ingresar nuevos modelos." if self.combo_novedad_subtipo.get() == "Nuevo producto" else "Pudimos reponer el stock que esperabas."
            preview = f"[📷 IMAGEN]\n¡Hola! Tenemos novedades de {her} en nuestro catálogo. {frase} Entrá a este link para más info 👉 [Link de WhatsApp] ¡Saludos!"
        elif tipo == "Recotización":
            preview = f"¡Hola! 👋 Vimos tu interés anterior y te ofrecemos una recotización actualizada.\nHacé clic acá para verla: 👉 [Link a Emmanuel]\n¡Avisanos cualquier duda!"
        elif tipo == "Personalizado":
            txt = self.text_dinamico_multilinea.get("1.0", tk.END).strip() or "Escribe tu mensaje libre aquí."
            txt = txt.replace('[CLIENTE]', nombre_ej)
            preview = f"[📷 IMAGEN]\n¡Hola! Nos contactamos de WoodTools para acercarte esta información:\n¡¡{txt}. Si estas interesado entrá en este link!!"

        self.lbl_preview_text.config(text=preview)

    def actualizar_inputs_dinamicos(self, e=None):
        tipo = self.tipo_mensaje_var.get()
        
        if tipo in ["Promociones", "Rescate (Te extrañamos)", "Personalizado", "Novedades"]:
            opciones = ["AUTOMÁTICO (Según Planilla)", "Emmanuel", "Carlos", "Valentín", "Ariel"]
        elif tipo == "Recotización":
            opciones = ["Emmanuel"]
        elif tipo == "Gira Vendedor":
            opciones = ["Ariel", "Alan", "Nicolas", "Ezequiel", "Roberto", "Luis"]
        else:
            opciones = ["AUTOMÁTICO (Según Planilla)", "Emmanuel", "Carlos", "Valentín", "Ariel"]
            
        self.combo_vendedor['values'] = opciones
        if self.combo_vendedor.get() not in opciones:
            self.combo_vendedor.current(0)
            
        for w in self.frame_dinamico.winfo_children():
            w.pack_forget()
            if isinstance(w, tk.Label) and w not in [self.lbl_aviso_meta, self.lbl_tip_tags, self.lbl_nombre_imagen]:
                w.config(bg=COLOR_PANELES, fg="black")
        
        self.lbl_aviso_meta.pack(anchor="w", pady=(0,2))
            
        if tipo == "Promociones":
            self.lbl_dinamico_titulo.config(text="Producto a promocionar:"); self.lbl_dinamico_titulo.pack(anchor="w")
            self.entry_dinamico_texto.pack(anchor="w", pady=2)
        elif tipo == "Gira Vendedor":
            tk.Label(self.frame_dinamico, text="El vendedor se selecciona en 'Enviar como' (arriba).", bg=COLOR_PANELES, fg="blue").pack(anchor="w", pady=2)
        elif tipo == "Personalizado":
            self.lbl_dinamico_titulo.config(text="Mensaje Libre a tu medida:"); self.lbl_dinamico_titulo.pack(anchor="w")
            self.lbl_tip_tags.pack(anchor="w", pady=(0, 2)) 
            self.text_dinamico_multilinea.pack(anchor="w", pady=2)
        elif tipo == "Novedades":
            self.lbl_novedad_subtipo.pack(anchor="w"); self.combo_novedad_subtipo.pack(anchor="w", pady=(0,2))
            if not self.combo_novedad_subtipo.get(): self.combo_novedad_subtipo.current(0)
            self.lbl_novedad_herramienta.pack(anchor="w"); self.combo_novedad_herramienta.pack(anchor="w")
            self.combo_novedad_herramienta['values'] = ["Sierras", "Mechas", "Cuchillas", "Fresas"]
            if not self.combo_novedad_herramienta.get(): self.combo_novedad_herramienta.current(0)
        elif tipo == "Recotización":
            tk.Label(self.frame_dinamico, text="El link apuntará a Emmanuel y se envía desde su número.", fg="blue", bg=COLOR_PANELES, font=("Segoe UI", 9, "bold")).pack(anchor="w", pady=2)

        ttk.Separator(self.frame_dinamico, orient='horizontal').pack(fill='x', pady=5)
        
        tipos_con_imagen = ["Promociones", "Rescate (Te extrañamos)", "Novedades", "Personalizado"]
        
        if tipo in tipos_con_imagen:
            self.btn_subir_imagen.config(text="📂 Adjuntar Imagen (Obligatoria)")
            self.btn_subir_imagen.pack(anchor="w", pady=(0,2))
            if self.ruta_imagen_seleccionada: self.btn_quitar_imagen.pack(anchor="w", pady=(0,2))
            self.lbl_nombre_imagen.config(bg=COLOR_PANELES)
            self.lbl_nombre_imagen.pack(anchor="w")
        else:
            self.quitar_imagen() 

        self.actualizar_preview()

    def seleccionar_imagen(self):
        ruta = filedialog.askopenfilename(filetypes=[("IMG", "*.jpg *.jpeg *.png")])
        if ruta: self.ruta_imagen_seleccionada = ruta; self.lbl_nombre_imagen.config(text="OK", fg="green"); self.btn_quitar_imagen.pack(anchor="w")

    def quitar_imagen(self):
        self.ruta_imagen_seleccionada = None; self.lbl_nombre_imagen.config(text="Sin imagen", fg="red"); self.btn_quitar_imagen.pack_forget()

    def _limpiar_panel_telefonos(self):
        for w in self.frame_telefonos.winfo_children(): w.destroy()
        tk.Label(self.frame_telefonos, text="Clic en una fila de la tabla de arriba para ver los números.", bg=COLOR_PANELES, fg="gray", font=("Segoe UI", 9, "bold")).pack(pady=5)

    def alternar_estado_numero(self, num_formateado, es_valido_actual):
        try:
            sel = self.tree.selection()
            if not sel: return
            idx = int(sel[0])
            row = self.df_filtrado.loc[idx]
            
            if es_valido_actual:
                if num_formateado in row['Telefonos_Validos']:
                    row['Telefonos_Validos'].remove(num_formateado)
                    row['Telefonos_Invalidos'].append(num_formateado)
            else:
                if num_formateado in row['Telefonos_Invalidos']:
                    row['Telefonos_Invalidos'].remove(num_formateado)
                    row['Telefonos_Validos'].append(num_formateado)
                    
            row['Es_Valido'] = len(row['Telefonos_Validos']) > 0
            if row['Telefonos_Validos']: row['Tel_Formateado'] = " | ".join(row['Telefonos_Validos'])
            elif row['Telefonos_Invalidos']: row['Tel_Formateado'] = row['Telefonos_Invalidos'][0]
            else: row['Tel_Formateado'] = "Sin número"
            
            self.df_filtrado.loc[idx] = row
            self.df_original.loc[idx] = row
            
            self.actualizar_tabla()
            self.tree.selection_set(idx)
            self.al_seleccionar_cliente(None)
        except Exception as e: print("Error alternando:", e)

    def editar_numero(self, num_antiguo, es_valido_actual):
        try:
            sel = self.tree.selection()
            if not sel: return
            idx = int(sel[0])
            row = self.df_filtrado.loc[idx]
            
            nuevo_num = simpledialog.askstring("Editar Número", f"Corrigiendo el número de {row['Cliente']}:\n\nReemplazar {num_antiguo} por:", initialvalue=num_antiguo)
            
            if not nuevo_num or nuevo_num.strip() == num_antiguo: return
            nuevo_num = nuevo_num.strip()
            
            es_nuevo_valido, nuevo_fmt = mainCode.validar_formato_numero(nuevo_num)
            
            if es_valido_actual and num_antiguo in row['Telefonos_Validos']:
                row['Telefonos_Validos'].remove(num_antiguo)
            elif not es_valido_actual and num_antiguo in row['Telefonos_Invalidos']:
                row['Telefonos_Invalidos'].remove(num_antiguo)
                
            if num_antiguo in row['Telefonos_Raw']:
                row['Telefonos_Raw'].remove(num_antiguo)
            row['Telefonos_Raw'].append(nuevo_num)
            
            if es_nuevo_valido:
                if nuevo_fmt not in row['Telefonos_Validos']:
                    row['Telefonos_Validos'].append(nuevo_fmt)
            else:
                if nuevo_num not in row['Telefonos_Invalidos']:
                    row['Telefonos_Invalidos'].append(nuevo_num)
                    
            row['Es_Valido'] = len(row['Telefonos_Validos']) > 0
            if row['Telefonos_Validos']: 
                row['Tel_Formateado'] = " | ".join(row['Telefonos_Validos'])
            elif row['Telefonos_Invalidos']: 
                row['Tel_Formateado'] = row['Telefonos_Invalidos'][0]
            else: 
                row['Tel_Formateado'] = "Sin número"
                
            self.df_filtrado.loc[idx] = row
            self.df_original.loc[idx] = row
            
            self.actualizar_tabla()
            self.tree.selection_set(idx)
            self.al_seleccionar_cliente(None)
            
            if es_nuevo_valido:
                messagebox.showinfo("Número Aceptado", f"El número se corrigió y se validó como: {nuevo_fmt}\n\nQuedó listo para enviar.")
            else:
                messagebox.showwarning("Atención", "El número fue editado, pero sigue sin cumplir con el formato de 10 dígitos (quedó en rojo).")

        except Exception as e: print("Error editando:", e)

    def al_seleccionar_cliente(self, event):
        sel = self.tree.selection()
        if not sel: return
        row = self.df_filtrado.loc[int(sel[0])]
        for w in self.frame_telefonos.winfo_children(): w.destroy()
        
        tels_v = row.get('Telefonos_Validos', [])
        tels_i = row.get('Telefonos_Invalidos', [])
        todos = [(t, True) for t in tels_v] + [(t, False) for t in tels_i]
        
        if not todos: tk.Label(self.frame_telefonos, text="Sin números", fg="red", bg=COLOR_PANELES).pack(side="left"); return 
        
        for tel, es_val in todos:
            bg, fg = ("#E8F5E9", "#2E7D32") if es_val else ("#FFEBEE", "#C62828")
            f = tk.Frame(self.frame_telefonos, bg=bg, highlightthickness=2, padx=10, pady=2)
            f.pack(side="left", padx=10, fill="y")
            tk.Label(f, text=tel, font=("bold"), bg=bg, fg=fg).pack()
            
            f_btns = tk.Frame(f, bg=bg)
            f_btns.pack(pady=(2,0))
            
            lbl_accion = tk.Label(f_btns, text="✅ Quitar" if es_val else "❌ Forzar Uso", bg=bg, fg=fg, cursor="hand2", font=("Segoe UI", 9, "underline"))
            lbl_accion.pack(side="left", padx=5)
            lbl_accion.bind("<Button-1>", lambda e, t=tel, v=es_val: self.alternar_estado_numero(t, v))
            
            lbl_editar = tk.Label(f_btns, text="✏️ Editar", bg=bg, fg="#1976D2", cursor="hand2", font=("Segoe UI", 9, "underline"))
            lbl_editar.pack(side="left", padx=5)
            lbl_editar.bind("<Button-1>", lambda e, t=tel, v=es_val: self.editar_numero(t, v))

    def abrir_selector_bases(self):
        vent_selector = tk.Toplevel(self.root)
        vent_selector.title("Selector de Bases de Datos")
        vent_selector.geometry("480x350")
        vent_selector.configure(bg="#f5f5f5")
        
        lbl_cargando = tk.Label(vent_selector, text="🔍 Buscando pestañas en tu Google Sheets...", font=("Segoe UI", 11, "italic"), bg="#f5f5f5", fg="#555")
        lbl_cargando.pack(pady=40)

        def fetch_sheets():
            pestanas = mainCode.obtener_pestanas_disponibles()
            self.root.after(0, lambda: construir_botones(pestanas))

        def construir_botones(pestanas):
            lbl_cargando.destroy()
            tk.Label(vent_selector, text="¿Qué pestaña deseas importar?", font=("Segoe UI", 12, "bold"), bg="#f5f5f5").pack(pady=15)

            frame_canvas = tk.Frame(vent_selector, bg="#f5f5f5")
            frame_canvas.pack(fill="both", expand=True, padx=10, pady=5)

            canvas = tk.Canvas(frame_canvas, bg="#f5f5f5", highlightthickness=0)
            scrollbar = ttk.Scrollbar(frame_canvas, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#f5f5f5")

            scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            for p in pestanas:
                nombre_p_lower = p.lower()
                if "cliente" in nombre_p_lower:
                    color = "#4CAF50"; icono = "📘"
                elif "prospecto" in nombre_p_lower:
                    color = "#FF9800"; icono = "📙"
                elif "descarte" in nombre_p_lower or "observado" in nombre_p_lower:
                    color = COLOR_ROJO_WT; icono = "📕"
                else:
                    color = "#2196F3"; icono = "📄" 

                btn = tk.Button(scrollable_frame, text=f"{icono} Cargar: {p}", width=38, bg=color, fg="white", font=("Segoe UI", 10, "bold"), 
                                command=lambda nombre=p: self._iniciar_carga(nombre, vent_selector))
                btn.pack(pady=5, padx=20)

        threading.Thread(target=fetch_sheets, daemon=True).start()

    def _iniciar_carga(self, tipo, ventana):
        if ventana: ventana.destroy()
        self.tipo_base_actual = tipo
        self.lbl_status_db.config(text=f"Descargando pestaña '{tipo}'...", fg="white", bg=COLOR_ROJO_WT)
        threading.Thread(target=self._hilo_carga, args=(tipo,)).start()
    
    def _hilo_carga(self, tipo):
        df = mainCode.conectar_y_procesar(tipo)
        if df.empty: 
            return self.root.after(0, lambda: messagebox.showerror("Error", "Base vacía o no se pudo leer la planilla. Asegurate de que tenga el formato correcto."))
            
        for c in ['Zona', 'Vendedor']: df[c] = df[c].fillna("0").astype(str)
        if "prospecto" not in tipo.lower():
            df['Fav_Temp'] = "Sierras"; df['Sec_Temp'] = "Cuchillas"
        
        self.df_original = df; self.df_filtrado = df.copy()
        
        self.root.after(0, self.actualizar_tabla)
        zonas_unicas = ["Todas"] + sorted(df['Zona'].unique().tolist())
        self.root.after(0, lambda: self.combo_zona.config(values=zonas_unicas))
        self.root.after(0, lambda: self.combo_zona.current(0))
        herramientas = ["Todos"] + mainCode.identificar_cols_productos(df)
        self.root.after(0, lambda: self.combo_herramientas.config(values=herramientas))
        self.root.after(0, lambda: self.combo_herramientas.current(0))
        self.root.after(0, lambda: self.lbl_status_db.config(text=f"Cargado: {len(df)} registros de {tipo}", fg="white", bg=COLOR_ROJO_WT))

    def actualizar_tabla(self):
        if "prospecto" in self.tipo_base_actual.lower():
            self.tree.heading("Cli", text="Nombre del Prospecto")
            self.tree.heading("Zona", text="Herramienta de Interés")
        else:
            self.tree.heading("Cli", text="Cliente")
            self.tree.heading("Zona", text="Zona")

        for i in self.tree.get_children(): self.tree.delete(i)
        for idx, row in self.df_filtrado.iterrows():
            tag = "valido" if row['Es_Valido'] else "invalido"
            est = f"OK ({len(row['Telefonos_Validos'])})" if row['Es_Valido'] else "DESCARTADO"
            self.tree.insert("", "end", iid=idx, values=(row['Cliente'], row.get('Tel_Formateado','-'), row.get('Vendedor','-'), row['Zona'], est), tags=(tag,))
        self.lbl_conteo.config(text=f"Regs: {len(self.df_filtrado)}")

    def aplicar_filtros(self, e=None):
        if self.df_original.empty: return
        df = self.df_original.copy()
        if self.entry_nombre.get(): df = df[df['Cliente'].str.lower().str.contains(self.entry_nombre.get().lower(), na=False)]
        if self.combo_zona.get() != "Todas": df = df[df['Zona'] == self.combo_zona.get()]
        self.df_filtrado = df; self.actualizar_tabla(); self._limpiar_panel_telefonos()

    def limpiar_filtros(self): self.entry_nombre.delete(0, tk.END); self.combo_zona.current(0); self.aplicar_filtros()

    def abrir_ventana_exportacion(self):
        tandas_disponibles = mainCode.obtener_tandas_campanas()
        if not tandas_disponibles: return messagebox.showinfo("Información", "Todavía no hay ninguna campaña guardada en el historial.")
        vent_exportar = tk.Toplevel(self.root); vent_exportar.title("Exportar Reportes"); vent_exportar.geometry("600x600")
        tk.Label(vent_exportar, text="Selecciona qué campañas deseas incluir en tu reporte:", font=("Arial", 11, "bold")).pack(pady=15)
        frame_contenedor = tk.Frame(vent_exportar); frame_contenedor.pack(fill="both", expand=True, padx=20, pady=5)
        canvas = tk.Canvas(frame_contenedor); scrollbar = ttk.Scrollbar(frame_contenedor, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw"); canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True); scrollbar.pack(side="right", fill="y")
        
        meses_nombres = {"01": "Enero", "02": "Febrero", "03": "Marzo", "04": "Abril", "05": "Mayo", "06": "Junio", "07": "Julio", "08": "Agosto", "09": "Septiembre", "10": "Octubre", "11": "Noviembre", "12": "Diciembre"}
        self.check_vars = {}; ultimo_mes_visto = ""
        for tanda in tandas_disponibles:
            t_id = tanda['tanda_id']; t_fecha = tanda['fecha_inicio']; t_tipo = tanda['tipo_campana']; t_vend = tanda['vendedor_asignado']; t_tot = tanda['total_msgs']; t_estado_crudo = tanda['estado_tanda']; t_mes_anio = tanda['mes'] 
            if t_mes_anio != ultimo_mes_visto:
                if t_mes_anio:
                    anio, mes_num = t_mes_anio.split('-')
                    tk.Label(scrollable_frame, text=f"--- {meses_nombres.get(mes_num, mes_num).upper()} {anio} ---", font=("Arial", 10, "bold"), fg="#1976D2").pack(anchor="w", pady=(15, 5))
                ultimo_mes_visto = t_mes_anio
            nombre_vendedor = "Varios"
            for nombre, numeros in mainCode.DB_VENDEDORES.items():
                if t_vend in numeros: nombre_vendedor = nombre; break
            estado_formateado = f"({t_estado_crudo})" if t_estado_crudo else "(SIN ESTADO)"
            var = tk.BooleanVar(value=True); self.check_vars[t_id] = var
            ttk.Checkbutton(scrollable_frame, text=f"[{t_fecha[:10]}] {t_tipo} - {nombre_vendedor} ({t_tot} msjs)", variable=var).pack(anchor="w", pady=2, padx=15)
        tk.Button(vent_exportar, text="📥 Generar Excel", bg="#4CAF50", fg="white", font=("bold", 11), command=lambda: self._ejecutar_exportacion_filtrada(vent_exportar)).pack(pady=20)

    def _ejecutar_exportacion_filtrada(self, ventana):
        tandas_elegidas = [t_id for t_id, var in self.check_vars.items() if var.get()]
        if not tandas_elegidas: return messagebox.showwarning("Atención", "Debes dejar seleccionada al menos una campaña para exportar.")
        
        df_historico = mainCode.obtener_datos_reporte_por_tandas(tandas_elegidas)
        if df_historico.empty: return messagebox.showerror("Error", "No se encontraron datos.")
        
        try:
            res_tracking = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/tracking_general", timeout=30)
            tracking_data = res_tracking.json() if res_tracking.status_code == 200 else {}
        except:
            tracking_data = {}

        datos_para_excel = []
        for t_id in reversed(tandas_elegidas):
            df_tanda = df_historico[df_historico['tanda_id'] == t_id]
            if df_tanda.empty: continue
            
            primer_registro = df_tanda.iloc[0]
            tipo_campana = primer_registro['tipo_campana'].upper()
            num_vend = primer_registro['vendedor_asignado']
            fecha_campana = primer_registro['fecha_hora'][:10]
            
            nombre_vend = "VARIOS"
            for nombre, numeros in mainCode.DB_VENDEDORES.items():
                if num_vend in numeros: nombre_vend = nombre.upper(); break
                
            datos_para_excel.append({
                "Fecha y Hora": f"CAMPAÑA [{fecha_campana}]", 
                "Cliente": f"{tipo_campana} DE {nombre_vend}", 
                "Teléfono": "------------------", 
                "Vendedor Asignado": "------------------", 
                "Tipo de Campaña": "------------------", 
                "Herramienta": "------------------", 
                "Estado Final de Meta": "------------------"
            })
            
            for _, row in df_tanda.iterrows():
                tel_limpio = ''.join(filter(str.isdigit, str(row['telefono'])))
                tel_10 = tel_limpio[-10:] if len(tel_limpio) >= 10 else tel_limpio
                estado_local = row['estado_envio']
                estado_nube = tracking_data.get(t_id, {}).get(tel_10, None)

                if estado_nube == 'clicked_link': estado_final = "Derivado al Vendedor 🟢"
                elif estado_nube == 'responded': estado_final = "Respondido por el cliente 💬"
                elif estado_nube == 'read': estado_final = "Leído (Doble tilde azul) 🟦"
                elif estado_nube == 'delivered': estado_final = "Entregado (Doble tilde gris) ⬜"
                else: estado_final = estado_local 

                datos_para_excel.append({
                    "Fecha y Hora": row['fecha_hora'], 
                    "Cliente": row['cliente'], 
                    "Teléfono": row['telefono'], 
                    "Vendedor Asignado": row['vendedor_asignado'], 
                    "Tipo de Campaña": row['tipo_campana'], 
                    "Herramienta": row.get('herramienta', ''), 
                    "Estado Final de Meta": estado_final
                })
                
        df_final = pd.DataFrame(datos_para_excel)
        try:
            ruta_base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            carpeta_reportes = os.path.join(ruta_base, "Reportes campañas")
            if not os.path.exists(carpeta_reportes): os.makedirs(carpeta_reportes)
            ruta_final = os.path.join(carpeta_reportes, f"Reporte_Campanas_Detallado_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            
            writer = pd.ExcelWriter(ruta_final, engine='xlsxwriter')
            df_final.to_excel(writer, index=False, sheet_name='Log_Campañas')
            
            workbook  = writer.book
            worksheet = writer.sheets['Log_Campañas']
            
            worksheet.set_column('A:A', 30)
            worksheet.set_column('B:G', 25)
            
            ruta_logo = obtener_ruta_interna(r"Imagenes\logo.png")
            if not os.path.exists(ruta_logo): 
                ruta_logo = obtener_ruta_interna("logo.png")
                
            if os.path.exists(ruta_logo):
                max_row = len(df_final) + 1 
                fecha_hora_actual = mainCode.hora_arg().strftime("%Y-%m-%d %H:%M:%S")
                
                formato_texto = workbook.add_format({'bold': True, 'font_color': '#a41e22'})
                worksheet.write(max_row + 2, 0, f"Reporte generado el: {fecha_hora_actual}", formato_texto)
                worksheet.insert_image(max_row + 4, 0, ruta_logo, {'x_scale': 0.6, 'y_scale': 0.6})
            
            writer.close()
            
            os.startfile(carpeta_reportes) 
            messagebox.showinfo("Éxito", f"Reporte generado correctamente en la carpeta:\n\n{ruta_final}")
            ventana.destroy()
        except Exception as e: messagebox.showerror("Error", f"No se pudo guardar el archivo Excel: {e}")

    def comando_cancelar_envio(self):
        self.cancelar_envio = True
        self.btn_cancelar.config(state="disabled", text="Cancelando...")
        self.lbl_progreso.config(text="Frenando el proceso... (Terminando cliente actual)", fg="red")

    def iniciar_envio(self):
        df_ok = self.df_filtrado[self.df_filtrado['Es_Valido'] == True]
        if df_ok.empty: return messagebox.showwarning("Error", "No hay destinatarios válidos en la lista actual.")
        
        total_base = len(self.df_filtrado)
        
        tipo = self.tipo_mensaje_var.get()
        tipos_con_imagen = ["Promociones", "Rescate (Te extrañamos)", "Novedades", "Personalizado"]

        if tipo in tipos_con_imagen:
            if not self.ruta_imagen_seleccionada: 
                return messagebox.showerror("Error", "¡La imagen es OBLIGATORIA para esta plantilla de Meta! Por favor adjuntá una foto antes de enviar.")
        
        sel = self.combo_vendedor.get()
        params = {}
        if "AUTOMÁTICO" in sel:
            params['modo_vendedor'] = "AUTO"
            rta = messagebox.askyesno("Vendedores", "Para los clientes que tengan el código '0':\n¿Deseas enviar con el link de Valentín (Sí) o de Carlos (No)?")
            params['preferencia_index'] = 0 if rta else 1
        else:
            params['modo_vendedor'] = "MANUAL"
            nums = mainCode.DB_VENDEDORES.get(sel, [])
            params['tel_fijo'] = nums[0] if nums else "5491145394279"

        if self.ruta_imagen_seleccionada: params['ruta_imagen'] = self.ruta_imagen_seleccionada
        
        if tipo == "Promociones":
            if not self.entry_dinamico_texto.get().strip(): return messagebox.showerror("Error", "Falta ingresar el producto a promocionar.")
            params['herramienta'] = self.entry_dinamico_texto.get().strip()
        elif tipo == "Novedades":
            her = self.combo_novedad_herramienta.get()
            params['subtipo_novedad'] = self.combo_novedad_subtipo.get()
            params['herramienta_novedad'] = her
        elif tipo == "Gira Vendedor":
            v_corto = self.combo_vendedor.get()
            if not v_corto or "AUTOMÁTICO" in v_corto:
                return messagebox.showerror("Error", "Para Gira Vendedor, seleccione a alguien de la lista (Ariel, Alan, Nicolas, etc).")
            
            nombres_completos = {
                "Alan": "Alan Calvi", "Ezequiel": "Ezequiel Calvi", 
                "Luis": "Luis Quevedo", "Nicolas": "Nicolas Saad", 
                "Roberto": "Roberto Golik", "Ariel": "Ariel Sosa"
            }
            params['texto_extra'] = nombres_completos.get(v_corto, v_corto) 
            params['vendedor_gira_corto'] = v_corto 
            
        elif tipo == "Personalizado":
            if not self.text_dinamico_multilinea.get("1.0", tk.END).strip(): return messagebox.showerror("Error", "Texto obligatorio.")
            params['texto_extra'] = self.text_dinamico_multilinea.get("1.0", tk.END).strip()

        if not messagebox.askyesno("Confirmar Envío", f"Revisá la Vista Previa a la derecha.\n\n¿Estás seguro que deseas disparar la campaña a {len(df_ok)} destinatarios?"): return
        
        self.cancelar_envio = False
        self.btn_enviar.config(state="disabled")
        self.btn_cancelar.config(state="normal", text="🛑 CANCELAR ENVÍO")
        
        threading.Thread(target=self._proceso_envio, args=(tipo, params, df_ok, total_base)).start()

    def _proceso_envio(self, tipo, params, df, total_base):
        media_id = None
        if params.get('ruta_imagen'):
            self.lbl_progreso.config(text="Subiendo imagen a Meta...", fg="blue", bg=COLOR_PANELES) 
            media_id = mainCode.subir_imagen_whatsapp(params['ruta_imagen'])
            if not media_id: 
                self.root.after(0, lambda: self.btn_enviar.config(state="normal"))
                self.root.after(0, lambda: self.btn_cancelar.config(state="disabled"))
                return messagebox.showerror("Error", "Fallo subida imagen a Meta. La imagen no debe superar los 5MB o el formato es incorrecto.")

        id_tanda_actual = mainCode.hora_arg().strftime("TANDA_%Y%m%d_%H%M%S")
        tot = len(df); ok = 0; err = 0; hubo_error_servidor = False; hubo_error_cliente = False
        
        numeros_ya_enviados = set()
        
        for i, (_, row) in enumerate(df.iterrows()):
            if self.cancelar_envio: break
            self.root.after(0, lambda x=i: self.lbl_progreso.config(text=f"Cliente {x+1}/{tot}...", fg="blue", bg=COLOR_PANELES))
            
            if tipo == "Recotización":
                tel_v = mainCode.DB_VENDEDORES["Emmanuel"][0]
                d_extra = {'cliente_nombre': row['Cliente'], 'herramienta': row.get('Fav_Temp','un producto')}
                tel_para_link = tel_v
            else:
                tel_v = mainCode.obtener_telefono_vendedor(row.get('Vendedor','0'), params.get('preferencia_index', 0)) if params['modo_vendedor'] == "AUTO" else params['tel_fijo']
                d_extra = {'vendedor_nombre': params.get('texto_extra',''), 'herramienta': params.get('herramienta_novedad','') or params.get('herramienta',''), 'subtipo': params.get('subtipo_novedad','')}
                tel_para_link = tel_v
                
                if tipo == "Gira Vendedor":
                    nombre_gira_corto = params.get('vendedor_gira_corto', '')
                    tel_para_link = mainCode.DB_VENDEDORES.get(nombre_gira_corto, [tel_v])[0]
            
            url_render = f"{URL_SERVIDOR_RENDER}/asignar_vendedor"
            try: 
                requests.post(url_render, json={
                    "cliente": row['Telefonos_Validos'][0] if row['Telefonos_Validos'] else "", 
                    "vendedor_tel": tel_v,
                    "tipo_campana": tipo,
                    "subtipo": params.get('subtipo_novedad', ''),
                    "tanda_id": id_tanda_actual
                }, timeout=15)
            except Exception as e: 
                pass

            for t in row['Telefonos_Validos']:
                if t in numeros_ya_enviados:
                    continue
                numeros_ya_enviados.add(t)

                if self.cancelar_envio: break
                res = False; tipo_error = ""
                
                link_original = mainCode.generar_link_whatsapp(tel_para_link, tipo, d_extra)
                parsed_url = urllib.parse.urlparse(link_original)
                texto_param = urllib.parse.parse_qs(parsed_url.query).get('text', [''])[0]
                tel_limpio_10 = ''.join(filter(str.isdigit, str(t)))[-10:]
                link = f"{URL_SERVIDOR_RENDER}/wa/{id_tanda_actual}/{tel_limpio_10}/{tel_para_link}?text={urllib.parse.quote(texto_param)}"
                
                if tipo == "Promociones": res, tipo_error = mainCode.enviar_promocion(t, row['Cliente'], params.get('herramienta', 'sierras circulares'), link, media_id)
                elif tipo == "Novedades": res, tipo_error = mainCode.enviar_novedades(t, params['subtipo_novedad'], params['herramienta_novedad'], link, media_id)
                elif tipo == "Rescate (Te extrañamos)": res, tipo_error = mainCode.enviar_rescate(t, row['Cliente'], row.get('Fav_Temp','-'), link, media_id)
                elif tipo == "Gira Vendedor": res, tipo_error = mainCode.enviar_gira(t, params.get('texto_extra','Vendedor'), link)
                elif tipo == "Recotización": res, tipo_error = mainCode.enviar_recotizacion(t, link)
                elif tipo == "Personalizado": 
                    txt_base = params.get('texto_extra','')
                    caption_final = txt_base.replace("[CLIENTE]", row['Cliente'])
                    res, tipo_error = mainCode.enviar_personalizado(t, caption_final, link, media_id)

                if res: ok += 1; estado_individual = "ENVIADO CORRECTAMENTE"
                else: 
                    err += 1; estado_individual = tipo_error
                    if tipo_error == "ERROR DEL CLIENTE": hubo_error_cliente = True
                    else: hubo_error_servidor = True
                
                herramienta_usada = row.get('Fav_Temp', '-') if tipo == "Recotización" else params.get('herramienta_novedad', '-')
                mainCode.registrar_envio_db(id_tanda_actual, row['Cliente'], t, tel_v, tipo, herramienta_usada, estado_individual, total_base)
                time.sleep(1)

        if self.cancelar_envio: estado_final_tanda = "CAMPAÑA CANCELADA"
        elif hubo_error_servidor: estado_final_tanda = "ERROR DEL SERVIDOR"
        elif hubo_error_cliente: estado_final_tanda = "ERROR DEL CLIENTE"
        else: estado_final_tanda = "ENVIADO CON EXITO"
            
        mainCode.actualizar_estado_tanda(id_tanda_actual, estado_final_tanda)
        self.root.after(0, lambda: self.btn_enviar.config(state="normal"))
        self.root.after(0, lambda: self.btn_cancelar.config(state="disabled", text="🛑 CANCELAR ENVÍO"))
        
        if self.cancelar_envio:
            self.root.after(0, lambda: self.lbl_progreso.config(text="Envío Cancelado", fg="red", bg=COLOR_PANELES))
            self.root.after(0, lambda: messagebox.showwarning("Proceso Detenido", f"La campaña fue frenada.\n\nEnviados con éxito: {ok}\nErrores: {err}"))
        else:
            self.root.after(0, lambda: self.lbl_progreso.config(text="Campaña completada", fg="green", bg=COLOR_PANELES))
            self.root.after(0, lambda: messagebox.showinfo("Reporte Final", f"Campaña Finalizada.\n\nEnviados con éxito: {ok}\nErrores: {err}\n\nQuedó registrada en el historial como: {estado_final_tanda}"))

    def abrir_rendimiento(self):
        vent_rendimiento = tk.Toplevel(self.root)
        vent_rendimiento.title("Rendimiento de Campañas")
        vent_rendimiento.geometry("1100x600")
        vent_rendimiento.configure(bg=COLOR_PANELES)
        
        frame_header = tk.Frame(vent_rendimiento, bg=COLOR_PANELES)
        frame_header.pack(fill="x", pady=15, padx=20)
        
        tk.Label(frame_header, text="📊 Panel de Rendimiento Histórico", font=("Segoe UI", 16, "bold"), bg=COLOR_PANELES, fg=COLOR_ROJO_WT).pack(side="left")
        
        btn_recargar = tk.Button(frame_header, text="🔄 Recargar Nube", command=lambda: cargar_datos_rendimiento(), bg="#2196F3", fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2", padx=10)
        btn_recargar.pack(side="right")

        btn_exportar_dash = tk.Button(frame_header, text="📥 Exportar Resumen a Excel", command=lambda: self.exportar_dashboard_excel(tree_rendimiento), bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"), cursor="hand2", padx=10)
        btn_exportar_dash.pack(side="right", padx=10)

        frame_tabla = tk.Frame(vent_rendimiento)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)
        
        columnas = ("Estado", "Fecha", "Campaña", "Base (Total)", "Intentos (PC)", "Entregados (Nube)", "Leídos", "Rtas (Bot)", "Deriv. (Vend.)", "Tasa Deriv.")
        tree_rendimiento = ttk.Treeview(frame_tabla, columns=columnas, show="headings", height=15)
        
        anchos = [80, 90, 180, 90, 90, 110, 70, 80, 100, 90]
        for col, ancho in zip(columnas, anchos):
            tree_rendimiento.heading(col, text=col)
            tree_rendimiento.column(col, width=ancho, anchor="center")
            
        tree_rendimiento.tag_configure("organico", background="#E8F5E9", foreground="#2E7D32")
            
        scroll = ttk.Scrollbar(frame_tabla, orient="vertical", command=tree_rendimiento.yview)
        tree_rendimiento.configure(yscroll=scroll.set)
        scroll.pack(side="right", fill="y")
        tree_rendimiento.pack(fill="both", expand=True)
        
        lbl_nota = tk.Label(vent_rendimiento, text="* Nota: Los datos de Entregados, Leídos e Interacciones se obtienen en tiempo real desde el servidor de Render.", font=("Segoe UI", 8, "italic"), bg=COLOR_PANELES, fg="gray")
        lbl_nota.pack(pady=5)

        def cargar_datos_rendimiento():
            for item in tree_rendimiento.get_children():
                tree_rendimiento.delete(item)
                
            tandas = mainCode.obtener_tandas_campanas()
                
            datos_nube = {}
            try:
                res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/metricas", timeout=30)
                if res.status_code == 200:
                    datos_nube = res.json()
            except Exception as e:
                print(f"Error conectando al servidor en la nube: {e}")
                
            if "ORGANICO" in datos_nube:
                org = datos_nube["ORGANICO"]
                iniciados = org.get("respondidos", 0)
                derivados = org.get("derivados", 0)
                tasa_org = f"{(derivados / iniciados * 100):.1f}%" if iniciados > 0 else "0%"
                
                tree_rendimiento.insert("", "end", values=(
                    "🌱 ORGÁNICO", "-", "Chats Orgánicos", "-", "-", 
                    iniciados, "-", iniciados, derivados, tasa_org
                ), tags=("organico",))

            if not tandas and not "ORGANICO" in datos_nube:
                tree_rendimiento.insert("", "end", values=("---", "---", "Todavía no hay campañas registradas", "---", "---", "---", "---", "---", "---", "---"))
                return

            for t in tandas:
                estado_crudo = t.get('estado_tanda', 'ERROR')
                if "EXITO" in estado_crudo.upper() or "OK" in estado_crudo.upper(): icono_estado = "🟢 OK"
                elif "CANCELADA" in estado_crudo.upper() or "ABORTADA" in estado_crudo.upper(): icono_estado = "🔴 CANC."
                else: icono_estado = "🔴 ERR."
                    
                fecha = t.get('fecha_inicio', '')[:10]
                nombre = t.get('tipo_campana', 'Desconocida')
                intentos_locales = t.get('total_msgs', 0)
                total_base = t.get('total_base', 0) 
                t_id = t.get('tanda_id', '')
                
                metricas_campana = datos_nube.get(t_id, {})
                entregados_reales = metricas_campana.get("entregados", 0)
                leidos_reales = metricas_campana.get("leidos", 0)
                clics_reales = metricas_campana.get("respondidos", 0)
                derivados_reales = metricas_campana.get("derivados", 0)
                
                tasa_deriv = f"{(derivados_reales / entregados_reales * 100):.1f}%" if entregados_reales > 0 else "0%"
                
                tree_rendimiento.insert("", "end", values=(
                    icono_estado, fecha, nombre, total_base, intentos_locales, 
                    entregados_reales, leidos_reales, 
                    clics_reales, derivados_reales, tasa_deriv
                ))

        cargar_datos_rendimiento()

    def exportar_dashboard_excel(self, tree):
        items = tree.get_children()
        if not items:
            return messagebox.showinfo("Aviso", "No hay datos para exportar.")
            
        datos = []
        for item in items:
            valores = tree.item(item)['values']
            if valores[0] == "---": continue
            datos.append({
                "Estado": valores[0], "Fecha": valores[1], "Campaña": valores[2],
                "Base (Total)": valores[3], "Intentos (PC)": valores[4], "Entregados (Nube)": valores[5],
                "Leídos": valores[6], "Respuestas al Bot": valores[7], "Derivados al Vendedor": valores[8], "Tasa de Derivación": valores[9]
            })
            
        df = pd.DataFrame(datos)
        ruta_base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
        carpeta_reportes = os.path.join(ruta_base, "Reportes campañas")
        if not os.path.exists(carpeta_reportes): os.makedirs(carpeta_reportes)
        ruta_final = os.path.join(carpeta_reportes, f"Resumen_Global_{mainCode.hora_arg().strftime('%Y%m%d_%H%M%S')}.xlsx")
        df.to_excel(ruta_final, index=False)
        os.startfile(carpeta_reportes)
        messagebox.showinfo("Éxito", f"Resumen global exportado en:\n{ruta_final}")

if __name__ == "__main__":
    root = tk.Tk()
    app = WoodToolsApp(root)
    root.mainloop()