import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk 
import pandas as pd
import threading
import os
import sys 
import time
import ctypes  
import urllib.parse
import requests  
import json
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
        self.root.title("Gestor de Marketing WhatsApp v11.0 - CRM")
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
        
        try:
            myappid = 'woodtools.gestormarketing.11.0' 
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
        
        btn_derivados = tk.Button(frame_top, text="💬 Chats Abandonados", command=self.abrir_chats_derivados, bg="#9C27B0", fg="white", font=("Segoe UI", 10, "bold"))
        btn_derivados.pack(side=tk.LEFT, padx=10)
        
        self.lbl_status_db = tk.Label(frame_top, text="Esperando datos...", fg="white", bg=COLOR_ROJO_WT, font=("Segoe UI", 9, "bold"))
        self.lbl_status_db.pack(side=tk.LEFT, padx=10)

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
        frame_campana.pack(fill="x", padx=20, pady=2)

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
        
        self.lbl_preview_text = tk.Label(self.frame_preview, text="", bg="#e8ecef", width=55, height=7, justify="left", anchor="nw", wraplength=400, font=("Arial", 10, "italic"), relief="sunken", bd=1, padx=5, pady=5, fg="#333")
        self.lbl_preview_text.pack(padx=5, pady=2, fill="both", expand=True)

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

        frame_tabla = tk.Frame(root, bg=COLOR_ROJO_WT)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=2)
        self.tree = ttk.Treeview(frame_tabla, columns=("Cli", "Tel", "Vend", "Zona", "Est"), show="headings")
        self.tree.heading("Cli", text="Cliente"); self.tree.column("Cli", width=200)
        self.tree.heading("Tel", text="Se enviará a:"); self.tree.column("Tel", width=250)
        self.tree.heading("Vend", text="Vendedor"); self.tree.column("Vend", width=100)
        self.tree.heading("Zona", text="Zona"); self.tree.column("Zona", width=120)
        self.tree.heading("Est", text="Estado"); self.tree.column("Est", width=120)
        self.tree.tag_configure('valido', background='white'); self.tree.tag_configure('invalido', background='#FFCCCC', foreground='red')
        self.tree.bind("<<TreeviewSelect>>", self.al_seleccionar_cliente)
        
        scroll = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set); scroll.pack(side="right", fill="y"); self.tree.pack(fill="both", expand=True)

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
    # PANTALLA DE CHATS ABANDONADOS
    # ==========================================
    def abrir_chats_derivados(self):
        vent = tk.Toplevel(self.root)
        vent.title("Chats Abandonados / Requieren Atención")
        vent.geometry("900x600")
        vent.configure(bg=COLOR_PANELES)

        frame_izq = tk.Frame(vent, width=300, bg=COLOR_PANELES)
        frame_izq.pack(side="left", fill="y", padx=10, pady=10)

        frame_der = tk.Frame(vent, bg=COLOR_PANELES)
        frame_der.pack(side="right", fill="both", expand=True, padx=10, pady=10)

        tk.Label(frame_izq, text="Lista de Clientes", bg=COLOR_PANELES, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        lista_chats = tk.Listbox(frame_izq, font=("Arial", 11))
        lista_chats.pack(fill="both", expand=True, pady=5)

        tk.Label(frame_der, text="Historial del Chat", bg=COLOR_PANELES, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        txt_chat = tk.Text(frame_der, font=("Arial", 11), wrap="word", state="disabled")
        txt_chat.pack(fill="both", expand=True, pady=(0, 10))

        btn_resuelto = tk.Button(frame_der, text="✅ Marcar como Resuelto (Contactado)", bg="#4CAF50", fg="white", font=("bold", 11))
        btn_resuelto.pack(fill="x")

        try:
            res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/derivados", timeout=30)
            if res.status_code == 200:
                datos_chats = res.json()
            else:
                datos_chats = []
                messagebox.showerror("Error", f"El servidor respondió con código de error {res.status_code}.\nRevisá los logs en Render.", parent=vent)
        except requests.exceptions.Timeout:
            datos_chats = []
            messagebox.showerror("Aviso", "El servidor de Render tardó mucho en responder porque estaba 'durmiendo'.\nPor favor, cerrá esta ventana e intentalo de nuevo en 30 segundos.", parent=vent)
        except Exception as e:
            datos_chats = []
            messagebox.showerror("Error de Conexión", f"No se pudo conectar con el servidor.\nDetalle técnico: {str(e)}", parent=vent)

        if not datos_chats:
            lista_chats.insert(tk.END, "✅ No hay chats abandonados.")
            btn_resuelto.config(state="disabled")

        for d in datos_chats:
            nombre_vendedor = d['vendedor']
            for nombre, numeros in mainCode.DB_VENDEDORES.items():
                if d['vendedor'] in numeros: nombre_vendedor = nombre; break
            lista_chats.insert(tk.END, f"+{d['telefono']} ({nombre_vendedor})")

        def mostrar_chat(evt):
            sel = lista_chats.curselection()
            if not sel or not datos_chats: return
            idx = sel[0]
            chat_data = datos_chats[idx]
            
            txt_chat.config(state="normal")
            txt_chat.delete("1.0", tk.END)
            
            txt_chat.insert(tk.END, f"📱 Cliente: +{chat_data['telefono']}\n")
            txt_chat.insert(tk.END, f"📅 Fecha de derivación: {chat_data['fecha']}\n")
            txt_chat.insert(tk.END, "-"*50 + "\n\n")
            
            for msg in chat_data['historial']:
                role = "🤖 BOT" if msg['role'] == 'model' else "👤 CLIENTE"
                text = msg['parts'][0]
                if "Eres el asistente virtual" in text: continue
                txt_chat.insert(tk.END, f"{role}:\n{text}\n\n")
                
            txt_chat.config(state="disabled")

        lista_chats.bind("<<ListboxSelect>>", mostrar_chat)

        def marcar_resuelto():
            sel = lista_chats.curselection()
            if not sel or not datos_chats: return
            idx = sel[0]
            tel = datos_chats[idx]['telefono']
            try:
                requests.delete(f"{URL_SERVIDOR_RENDER.rstrip('/')}/derivados/{tel}")
                lista_chats.delete(idx)
                datos_chats.pop(idx)
                txt_chat.config(state="normal")
                txt_chat.delete("1.0", tk.END)
                txt_chat.config(state="disabled")
                messagebox.showinfo("Éxito", "El chat fue marcado como resuelto y eliminado de la lista.", parent=vent)
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo borrar el chat de la base de datos.\nDetalle: {str(e)}", parent=vent)

        btn_resuelto.config(command=marcar_resuelto)


    def verificar_observados(self):
        if self.df_filtrado.empty:
            msg = "✅ No hay datos cargados."
        else:
            df_descartados = self.df_filtrado[self.df_filtrado['Es_Valido'] == False]
            if df_descartados.empty:
                msg = "✅ No hay números descartados en la lista actual filtrada."
            else:
                msg = f"--- {len(df_descartados)} DESCARTADOS (En este filtro) ---\n\n"
                for _, row in df_descartados.iterrows():
                    tels = row.get('Telefonos_Raw', [])
                    msg += f"• {row['Cliente']} -> {' | '.join(tels) if tels else 'Sin números'}\n"
        
        vent = tk.Toplevel(self.root)
        vent.title("Descartados (Filtrados)"); vent.geometry("500x400")
        t = tk.Text(vent, wrap="word", padx=10, pady=10); t.pack(fill="both", expand=True)
        t.insert("1.0", msg); t.config(state="disabled")

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
            prod_promo = self.entry_dinamico_texto.get().strip() or "sierras circulares para seccionadora y escuadradora"
            preview = f"[📷 IMAGEN]\nHola {nombre_ej} 👋 Te contactamos para contarte que tenemos promociones en {prod_promo}. ¡Contactanos acá 👉 [Link de WhatsApp] por más información!"
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
                    "cliente": row['Telefonos_Validos'][0], 
                    "vendedor_tel": tel_v,
                    "tipo_campana": tipo,
                    "subtipo": params.get('subtipo_novedad', ''),
                    "tanda_id": id_tanda_actual
                }, timeout=15)
            except Exception as e: 
                pass

            for t in row['Telefonos_Validos']:
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
                    res, tipo_error = mainCode.enviar_personalizado(t, caption_final, media_id)

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
                
            # INYECCIÓN DE LA FILA ORGÁNICA (Se fija arriba de todo)
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