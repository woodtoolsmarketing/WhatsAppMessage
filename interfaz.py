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
from datetime import datetime

import mainCode 

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
        
        self.cancelar_envio = False
        self.tipo_base_actual = "clientes" 
        
        mainCode.inicializar_db()
        
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
        
        # ==========================================
        # 1. CABECERA
        # ==========================================
        frame_top = tk.Frame(root, pady=10, padx=10, bg="#e0e0e0")
        frame_top.pack(fill="x")
        self.cargar_logo(frame_top)

        btn_cargar = tk.Button(frame_top, text="🔄 Cargar Base", command=self.abrir_selector_bases, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"))
        btn_cargar.pack(side=tk.LEFT, padx=10)
        
        btn_verificar = tk.Button(frame_top, text="🔍 Descartes", command=self.verificar_observados, bg="#FF9800", fg="white", font=("Segoe UI", 10, "bold"))
        btn_verificar.pack(side=tk.LEFT, padx=10)
        
        btn_reporte = tk.Button(frame_top, text="📊 Exportar Reporte Mensual / Anual", command=self.abrir_ventana_exportacion, bg="#2196F3", fg="white", font=("Segoe UI", 10, "bold"))
        btn_reporte.pack(side=tk.LEFT, padx=10)
        
        self.lbl_status_db = tk.Label(frame_top, text="Esperando datos...", fg="gray", bg="#e0e0e0")
        self.lbl_status_db.pack(side=tk.LEFT, padx=10)

        # ==========================================
        # 2. ÁREA DE FILTROS
        # ==========================================
        frame_filtros = tk.LabelFrame(root, text="Filtros", padx=10, pady=10)
        frame_filtros.pack(fill="x", padx=20, pady=5)
        
        tk.Label(frame_filtros, text="Nombre:").grid(row=0, column=0)
        self.entry_nombre = tk.Entry(frame_filtros)
        self.entry_nombre.grid(row=0, column=1, padx=5)
        self.entry_nombre.bind("<KeyRelease>", self.aplicar_filtros) 
        
        tk.Label(frame_filtros, text="Zona/Interés:").grid(row=0, column=2)
        self.combo_zona = ttk.Combobox(frame_filtros, state="readonly", width=10)
        self.combo_zona.grid(row=0, column=3)
        self.combo_zona.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        tk.Label(frame_filtros, text="Favorito:").grid(row=0, column=4)
        self.combo_herramientas = ttk.Combobox(frame_filtros, state="readonly")
        self.combo_herramientas.grid(row=0, column=5)
        self.combo_herramientas.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        tk.Button(frame_filtros, text="Limpiar", command=self.limpiar_filtros).grid(row=0, column=6, padx=15)
        self.lbl_conteo = tk.Label(frame_filtros, text="Regs: 0", font=("Segoe UI", 9, "bold"), fg="#2196F3")
        self.lbl_conteo.grid(row=0, column=7, padx=20)

        # ==========================================
        # 3. CONFIGURACIÓN DEL MENSAJE Y PREVIEW
        # ==========================================
        frame_campana = tk.LabelFrame(root, text="Configuración de Envío", padx=10, pady=10, bg="#f5f5f5")
        frame_campana.pack(fill="x", padx=20, pady=10)

        tk.Label(frame_campana, text="Tipo Mensaje:", bg="#f5f5f5").grid(row=0, column=0, sticky="w")
        self.tipo_mensaje_var = tk.StringVar(value="Promociones")
        self.combo_tipo_mensaje = ttk.Combobox(frame_campana, values=["Promociones", "Rescate (Te extrañamos)", "Gira Vendedor", "Personalizado", "Novedades", "Recotización"], state="readonly", textvariable=self.tipo_mensaje_var, width=25)
        self.combo_tipo_mensaje.grid(row=1, column=0, padx=5, pady=5, sticky="n")
        self.combo_tipo_mensaje.bind("<<ComboboxSelected>>", self.actualizar_inputs_dinamicos)

        tk.Label(frame_campana, text="Enviar como:", bg="#f5f5f5").grid(row=0, column=1, sticky="w", padx=20)
        opciones_vendedores = ["AUTOMÁTICO (Según Excel)"] + list(mainCode.DB_VENDEDORES.keys())
        self.combo_vendedor = ttk.Combobox(frame_campana, values=opciones_vendedores, state="readonly", width=30)
        self.combo_vendedor.grid(row=1, column=1, padx=20, pady=5, sticky="n")
        self.combo_vendedor.current(0)

        self.frame_dinamico = tk.Frame(frame_campana, bg="#f5f5f5")
        self.frame_dinamico.grid(row=0, column=2, rowspan=2, padx=10, sticky="nwe")
        
        self.lbl_dinamico_titulo = tk.Label(self.frame_dinamico, text="", bg="#f5f5f5", font=("Arial", 9, "bold"))
        self.entry_dinamico_texto = tk.Entry(self.frame_dinamico, width=35)
        self.text_dinamico_multilinea = tk.Text(self.frame_dinamico, width=45, height=6, font=("Arial", 10), relief="solid", bd=1)
        
        self.lbl_novedad_subtipo = tk.Label(self.frame_dinamico, text="Tipo:", bg="#f5f5f5", font=("Arial", 8, "bold"))
        self.combo_novedad_subtipo = ttk.Combobox(self.frame_dinamico, values=["Ingresos", "Reposición de stock"], state="readonly", width=25)
        self.lbl_novedad_herramienta = tk.Label(self.frame_dinamico, text="Herramienta:", bg="#f5f5f5", font=("Arial", 8, "bold"))
        self.combo_novedad_herramienta = ttk.Combobox(self.frame_dinamico, state="readonly", width=25)

        self.lbl_aviso_meta = tk.Label(self.frame_dinamico, text="🔒 Estructura fijada por plantilla de Meta.", fg="#d32f2f", bg="#f5f5f5", font=("Arial", 8, "bold"))
        self.lbl_tip_tags = tk.Label(self.frame_dinamico, text="💡 Tip: Usa [CLIENTE] y [LINK] para acomodarlos donde quieras.", fg="#1976d2", bg="#f5f5f5", font=("Arial", 8, "italic"))

        self.btn_subir_imagen = tk.Button(self.frame_dinamico, text="📂 Adjuntar Imagen", command=self.seleccionar_imagen)
        self.btn_quitar_imagen = tk.Button(self.frame_dinamico, text="❌ Quitar Imagen", command=self.quitar_imagen, fg="red")
        self.lbl_nombre_imagen = tk.Label(self.frame_dinamico, text="Sin imagen", bg="#f5f5f5", fg="red")

        self.frame_preview = tk.LabelFrame(frame_campana, text="Plantilla de Mensaje (Vista Previa)", bg="#f5f5f5", fg="#555", font=("Segoe UI", 9, "bold"))
        self.frame_preview.grid(row=0, column=3, rowspan=2, padx=30, sticky="nsew")
        
        self.lbl_preview_text = tk.Label(self.frame_preview, text="", bg="#e8ecef", width=55, height=7, justify="left", anchor="nw", wraplength=400, font=("Arial", 10, "italic"), relief="sunken", bd=1, padx=10, pady=10, fg="#333")
        self.lbl_preview_text.pack(padx=10, pady=5, fill="both", expand=True)

        self.entry_dinamico_texto.bind("<KeyRelease>", self.actualizar_preview)
        self.text_dinamico_multilinea.bind("<KeyRelease>", self.actualizar_preview)
        self.combo_novedad_subtipo.bind("<<ComboboxSelected>>", self.actualizar_preview)
        self.combo_novedad_herramienta.bind("<<ComboboxSelected>>", self.actualizar_preview)

        self.actualizar_inputs_dinamicos() 

        # ==========================================
        # 4. BOTONES DE ACCIÓN
        # ==========================================
        frame_accion = tk.Frame(root, pady=15, bg="#333333")
        frame_accion.pack(fill="x", side="bottom")
        
        self.lbl_progreso = tk.Label(frame_accion, text="Sistema listo.", fg="white", bg="#333333", font=("Segoe UI", 10))
        self.lbl_progreso.pack(pady=5)
        
        frame_botones_accion = tk.Frame(frame_accion, bg="#333333")
        frame_botones_accion.pack(pady=10)

        self.btn_enviar = tk.Button(frame_botones_accion, text="🚀 ENVIAR A TODOS", command=self.iniciar_envio, bg="#2196F3", fg="white", font=("Segoe UI", 12, "bold"), width=20)
        self.btn_enviar.grid(row=0, column=0, padx=15)

        self.btn_cancelar = tk.Button(frame_botones_accion, text="🛑 CANCELAR ENVÍO", command=self.comando_cancelar_envio, bg="#f44336", fg="white", font=("Segoe UI", 12, "bold"), width=20, state="disabled")
        self.btn_cancelar.grid(row=0, column=1, padx=15)

        # ==========================================
        # 5. TABLAS DE RESULTADOS
        # ==========================================
        self.frame_telefonos = tk.LabelFrame(root, text="🔍 Gestión de Teléfonos (Clic en tabla para ver)", padx=10, pady=10, bg="#f5f5f5", font=("Segoe UI", 9, "bold"))
        self.frame_telefonos.pack(fill="x", padx=20, pady=5, side="bottom")
        self._limpiar_panel_telefonos()

        frame_tabla = tk.Frame(root)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=5)
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

    # ==========================================
    # FUNCIONES DE INTERFAZ Y PREVIEW
    # ==========================================
    def cargar_logo(self, parent):
        ruta_1 = obtener_ruta_interna(r"Imagenes\logo.png")
        ruta_2 = obtener_ruta_interna("logo.png")
        ruta_final = ruta_1 if os.path.exists(ruta_1) else ruta_2
        if os.path.exists(ruta_final):
            try:
                img = Image.open(ruta_final)
                w, h = img.size; new_w = int((65/h)*w)
                self.logo_img = ImageTk.PhotoImage(img.resize((new_w, 65), Image.Resampling.LANCZOS))
                tk.Label(parent, image=self.logo_img, bg="#e0e0e0").pack(side=tk.RIGHT, padx=15)
            except: pass

    def verificar_observados(self):
        msg = mainCode.revisar_numeros_problematicos()
        vent = tk.Toplevel(self.root)
        vent.title("Descartados"); vent.geometry("500x400")
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
            desc = self.entry_dinamico_texto.get().strip()
            if not desc: desc = "[%]"
            preview = f"Hola, {nombre_ej}, al ver tu interés en nuestros productos te ofrecemos un {desc}% de descuento para tus próximas compras. Si te interesa hablanos al 👉 [Link de WhatsApp]"
        elif tipo == "Rescate (Te extrañamos)":
            preview = f"¡Hola {nombre_ej}! Vimos que hace tiempo no nos compras. Te invitamos a reponer tu stock de {herramienta_ej}.\n\nEntrá a este link para más información 👉 [Link de WhatsApp]"
        elif tipo == "Gira Vendedor":
            vend = self.entry_dinamico_texto.get().strip()
            if not vend: vend = "[Nombre Vendedor]"
            preview = f"¡Hola {nombre_ej}! Te avisamos que {vend} estará visitando clientes por tu zona.\n\nEntrá a este link para coordinar la visita 👉 [Link de WhatsApp]"
        elif tipo == "Novedades":
            her = self.combo_novedad_herramienta.get()
            if not her: her = "[Herramienta]"
            if self.combo_novedad_subtipo.get() == "Ingresos":
                preview = f"Hola, tenemos nuevas incorporaciones de {her}. Si querés más información entrá a este link: [Link de WhatsApp]"
            else:
                preview = f"Hola, te informamos que pudimos obtener nuevamente stock de {her}. Para conocer cuáles son los modelos entrá a este link: [Link de WhatsApp]"
        elif tipo == "Recotización":
            preview = f"¡Hola {nombre_ej}! Vimos que en un pasado estuviste interesado en nuestros productos pero no obtuvimos más respuestas de tu parte. Podemos ofrecerte una recotización para {herramienta_ej}.\n\nEntrá a este link para más información 👉 [Link a Emmanuel]"
        elif tipo == "Personalizado":
            txt = self.text_dinamico_multilinea.get("1.0", tk.END).strip()
            if not txt: txt = "Escribe tu mensaje libre aquí."
            preview = txt.replace("[CLIENTE]", nombre_ej).replace("[LINK]", "[Link Autocompletable de WhatsApp]")
            if "[LINK]" not in txt:
                preview += f"\n\n[Link agregado por defecto al final]"
            preview += "\n\n📎 [Tu Imagen Adjunta se enviará junto con este texto]"

        self.lbl_preview_text.config(text=preview)

    def actualizar_inputs_dinamicos(self, e=None):
        tipo = self.tipo_mensaje_var.get()
        for w in self.frame_dinamico.winfo_children(): w.pack_forget()
        
        if tipo in ["Promociones", "Rescate (Te extrañamos)", "Gira Vendedor", "Recotización"]:
            self.lbl_aviso_meta.pack(anchor="w", pady=(0,5))
            
        if tipo == "Promociones":
            self.lbl_dinamico_titulo.config(text="Porcentaje de Descuento (Ej: 15):"); self.lbl_dinamico_titulo.pack(anchor="w")
            self.entry_dinamico_texto.pack(anchor="w", pady=5)
        elif tipo == "Gira Vendedor":
            self.lbl_dinamico_titulo.config(text="Escribe el Nombre del Vendedor:"); self.lbl_dinamico_titulo.pack(anchor="w")
            self.entry_dinamico_texto.pack(anchor="w", pady=5)
        elif tipo == "Personalizado":
            self.lbl_dinamico_titulo.config(text="Mensaje Libre a tu medida:"); self.lbl_dinamico_titulo.pack(anchor="w")
            self.lbl_tip_tags.pack(anchor="w", pady=(0, 5)) 
            self.text_dinamico_multilinea.pack(anchor="w", pady=5)
        elif tipo == "Novedades":
            self.lbl_novedad_subtipo.pack(anchor="w"); self.combo_novedad_subtipo.pack(anchor="w", pady=(0,5))
            if not self.combo_novedad_subtipo.get(): self.combo_novedad_subtipo.current(0)
            self.lbl_novedad_herramienta.pack(anchor="w"); self.combo_novedad_herramienta.pack(anchor="w")
            self.combo_novedad_herramienta['values'] = mainCode.identificar_cols_productos(pd.DataFrame())
            if not self.combo_novedad_herramienta.get(): self.combo_novedad_herramienta.current(0)
        elif tipo == "Recotización":
            tk.Label(self.frame_dinamico, text="El link apuntará automáticamente a Emmanuel.", fg="blue", bg="#f5f5f5").pack(anchor="w", pady=5)

        ttk.Separator(self.frame_dinamico, orient='horizontal').pack(fill='x', pady=10)
        
        if tipo != "Recotización":
            self.btn_subir_imagen.config(text="📂 Adjuntar Imagen (OBLIGATORIO)" if tipo == "Personalizado" else "📂 Adjuntar Imagen (OPCIONAL)")
            self.btn_subir_imagen.pack(anchor="w", pady=(0,2))
            if self.ruta_imagen_seleccionada: self.btn_quitar_imagen.pack(anchor="w", pady=(0,2))
            self.lbl_nombre_imagen.pack(anchor="w")

        self.actualizar_preview()

    def seleccionar_imagen(self):
        ruta = filedialog.askopenfilename(filetypes=[("IMG", "*.jpg *.jpeg *.png")])
        if ruta: self.ruta_imagen_seleccionada = ruta; self.lbl_nombre_imagen.config(text="OK", fg="green"); self.btn_quitar_imagen.pack(anchor="w")

    def quitar_imagen(self):
        self.ruta_imagen_seleccionada = None; self.lbl_nombre_imagen.config(text="Sin imagen", fg="red"); self.btn_quitar_imagen.pack_forget()

    def _limpiar_panel_telefonos(self):
        for w in self.frame_telefonos.winfo_children(): w.destroy()
        tk.Label(self.frame_telefonos, text="Clic en tabla para ver las opciones de edición.", bg="#f5f5f5", fg="gray").pack(pady=10)

    # NUEVAS FUNCIONES DE EDICIÓN Y ALTERNANCIA
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
            
            # Pedir el número nuevo al usuario
            nuevo_num = simpledialog.askstring("Editar Número", f"Corrigiendo el número de {row['Cliente']}:\n\nReemplazar {num_antiguo} por:", initialvalue=num_antiguo)
            
            if not nuevo_num or nuevo_num.strip() == num_antiguo: return # Canceló o lo dejó igual
            nuevo_num = nuevo_num.strip()
            
            # Validamos el nuevo número con las reglas de Meta y Argentina
            es_nuevo_valido, nuevo_fmt = mainCode.validar_formato_numero(nuevo_num)
            
            # Sacamos el viejo de las listas
            if es_valido_actual and num_antiguo in row['Telefonos_Validos']:
                row['Telefonos_Validos'].remove(num_antiguo)
            elif not es_valido_actual and num_antiguo in row['Telefonos_Invalidos']:
                row['Telefonos_Invalidos'].remove(num_antiguo)
                
            if num_antiguo in row['Telefonos_Raw']:
                row['Telefonos_Raw'].remove(num_antiguo)
            row['Telefonos_Raw'].append(nuevo_num)
            
            # Metemos el nuevo en la lista correspondiente
            if es_nuevo_valido:
                if nuevo_fmt not in row['Telefonos_Validos']:
                    row['Telefonos_Validos'].append(nuevo_fmt)
            else:
                if nuevo_num not in row['Telefonos_Invalidos']:
                    row['Telefonos_Invalidos'].append(nuevo_num)
                    
            # Recalculamos el estado global de la fila
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
            
            # Mensaje de retroalimentación
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
        
        if not todos: tk.Label(self.frame_telefonos, text="Sin números", fg="red", bg="#f5f5f5").pack(side="left"); return
        
        for tel, es_val in todos:
            bg, fg = ("#E8F5E9", "#2E7D32") if es_val else ("#FFEBEE", "#C62828")
            f = tk.Frame(self.frame_telefonos, bg=bg, highlightthickness=2, padx=10, pady=5)
            f.pack(side="left", padx=10, fill="y")
            tk.Label(f, text=tel, font=("bold"), bg=bg, fg=fg).pack()
            
            # Contenedor para alinear los botones en horizontal
            f_btns = tk.Frame(f, bg=bg)
            f_btns.pack(pady=(5,0))
            
            # Botón Alternar
            lbl_accion = tk.Label(f_btns, text="✅ Quitar" if es_val else "❌ Forzar Uso", bg=bg, fg=fg, cursor="hand2", font=("Segoe UI", 9, "underline"))
            lbl_accion.pack(side="left", padx=5)
            lbl_accion.bind("<Button-1>", lambda e, t=tel, v=es_val: self.alternar_estado_numero(t, v))
            
            # Botón Editar
            lbl_editar = tk.Label(f_btns, text="✏️ Editar", bg=bg, fg="#1976D2", cursor="hand2", font=("Segoe UI", 9, "underline"))
            lbl_editar.pack(side="left", padx=5)
            lbl_editar.bind("<Button-1>", lambda e, t=tel, v=es_val: self.editar_numero(t, v))

    # ==========================================
    # SELECTOR DE BASES Y CARGA
    # ==========================================
    def abrir_selector_bases(self):
        vent_selector = tk.Toplevel(self.root)
        vent_selector.title("Selector de Bases de Datos")
        vent_selector.geometry("400x200")
        vent_selector.configure(bg="#f5f5f5")
        
        tk.Label(vent_selector, text="¿Qué base de datos deseas procesar?", font=("Segoe UI", 12, "bold"), bg="#f5f5f5").pack(pady=20)
        
        btn_clientes = tk.Button(vent_selector, text="📘 Base de Clientes (wt)", width=25, bg="#4CAF50", fg="white", font=("bold"), 
                                 command=lambda: self._iniciar_carga("Base de datos wt.xlsx", "clientes", vent_selector))
        btn_clientes.pack(pady=5)
        
        btn_prospectos = tk.Button(vent_selector, text="📙 Base de Prospectos (wt)", width=25, bg="#FF9800", fg="white", font=("bold"), 
                                   command=lambda: self._iniciar_carga("Base de prospectos wt.xlsx", "prospectos", vent_selector)) 
        btn_prospectos.pack(pady=5)

    def _iniciar_carga(self, archivo, tipo, ventana):
        ventana.destroy()
        self.tipo_base_actual = tipo
        threading.Thread(target=self._hilo_carga, args=(archivo, tipo)).start()
    
    def _hilo_carga(self, archivo, tipo):
        df = mainCode.conectar_y_procesar(archivo, tipo)
        if df.empty: 
            return self.root.after(0, lambda: messagebox.showerror("Error", f"Base vacía o no se encontró '{archivo}' en la carpeta raíz ni en 'dist'."))
            
        for c in ['Zona', 'Vendedor']: df[c] = df[c].fillna("0").astype(str)
        if tipo == "clientes":
            df['Fav_Temp'] = "Sierras"; df['Sec_Temp'] = "Cuchillas"
        
        self.df_original = df; self.df_filtrado = df.copy()
        
        self.root.after(0, self.actualizar_tabla)
        zonas_unicas = ["Todas"] + sorted(df['Zona'].unique().tolist())
        self.root.after(0, lambda: self.combo_zona.config(values=zonas_unicas))
        self.root.after(0, lambda: self.combo_zona.current(0))
        herramientas = ["Todos"] + mainCode.identificar_cols_productos(df)
        self.root.after(0, lambda: self.combo_herramientas.config(values=herramientas))
        self.root.after(0, lambda: self.combo_herramientas.current(0))
        self.root.after(0, lambda: self.lbl_status_db.config(text=f"Cargado: {len(df)} regs ({tipo.upper()})", fg="green"))

    def actualizar_tabla(self):
        if self.tipo_base_actual == "prospectos":
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

    # ==========================================
    # LÓGICA DE EXPORTACIÓN
    # ==========================================
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
            ttk.Checkbutton(scrollable_frame, text=f"[{t_fecha[:10]}] {t_tipo} - {nombre_vendedor} ({t_tot} msjs) {estado_formateado}", variable=var).pack(anchor="w", pady=2, padx=15)
        tk.Button(vent_exportar, text="📥 Generar Excel", bg="#4CAF50", fg="white", font=("bold", 11), command=lambda: self._ejecutar_exportacion_filtrada(vent_exportar)).pack(pady=20)

    def _ejecutar_exportacion_filtrada(self, ventana):
        tandas_elegidas = [t_id for t_id, var in self.check_vars.items() if var.get()]
        if not tandas_elegidas: return messagebox.showwarning("Atención", "Debes dejar seleccionada al menos una campaña para exportar.")
        df_historico = mainCode.obtener_datos_reporte_por_tandas(tandas_elegidas)
        if df_historico.empty: return messagebox.showerror("Error", "No se encontraron datos.")
        datos_para_excel = []
        for t_id in reversed(tandas_elegidas):
            df_tanda = df_historico[df_historico['tanda_id'] == t_id]
            if df_tanda.empty: continue
            primer_registro = df_tanda.iloc[0]; tipo_campana = primer_registro['tipo_campana'].upper(); num_vend = primer_registro['vendedor_asignado']; fecha_campana = primer_registro['fecha_hora'][:10]
            nombre_vend = "VARIOS"
            for nombre, numeros in mainCode.DB_VENDEDORES.items():
                if num_vend in numeros: nombre_vend = nombre.upper(); break
            datos_para_excel.append({"Fecha y Hora": f"CAMPAÑA DEL DÍA [{fecha_campana}] - {tipo_campana} DE {nombre_vend}", "Cliente": "-------------------------", "Teléfono": "-------------------------", "Vendedor Asignado": "-------------------------", "Tipo de Campaña": "-------------------------", "Herramienta": "-------------------------", "Estado de Envío": "-------------------------"})
            for _, row in df_tanda.iterrows():
                datos_para_excel.append({"Fecha y Hora": row['fecha_hora'], "Cliente": row['cliente'], "Teléfono": row['telefono'], "Vendedor Asignado": row['vendedor_asignado'], "Tipo de Campaña": row['tipo_campana'], "Herramienta": row.get('herramienta', ''), "Estado de Envío": row['estado_envio']})
        df_final = pd.DataFrame(datos_para_excel)
        try:
            ruta_base = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            carpeta_reportes = os.path.join(ruta_base, "Reportes")
            if not os.path.exists(carpeta_reportes): os.makedirs(carpeta_reportes)
            ruta_final = os.path.join(carpeta_reportes, f"Reporte_Campanas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            df_final.to_excel(ruta_final, index=False)
            os.startfile(carpeta_reportes) 
            messagebox.showinfo("Éxito", f"Reporte generado correctamente en la carpeta:\n\n{ruta_final}")
            ventana.destroy()
        except Exception as e: messagebox.showerror("Error", f"No se pudo guardar el archivo Excel: {e}")

    # ==========================================
    # LÓGICA DE CANCELACIÓN Y ENVÍO MASIVO
    # ==========================================
    def comando_cancelar_envio(self):
        self.cancelar_envio = True
        self.btn_cancelar.config(state="disabled", text="Cancelando...")
        self.lbl_progreso.config(text="Frenando el proceso... (Terminando cliente actual)", fg="red")

    def iniciar_envio(self):
        df_ok = self.df_filtrado[self.df_filtrado['Es_Valido'] == True]
        if df_ok.empty: return messagebox.showwarning("Error", "No hay destinatarios válidos en la lista actual.")
        
        sel = self.combo_vendedor.get()
        params = {}
        if "AUTOMÁTICO" in sel:
            params['modo_vendedor'] = "AUTO"
            rta = messagebox.askyesno("Vendedores", "Para los clientes asignados al código '0':\n¿Deseas enviar con el link de Valentín (Sí) o de Carlos (No)?")
            params['preferencia_index'] = 0 if rta else 1
        else:
            params['modo_vendedor'] = "MANUAL"
            nums = mainCode.DB_VENDEDORES.get(sel, [])
            params['tel_fijo'] = nums[0] if nums else "5491145394279"

        if self.ruta_imagen_seleccionada: params['ruta_imagen'] = self.ruta_imagen_seleccionada
        tipo = self.tipo_mensaje_var.get()
        
        if tipo == "Promociones":
            desc = self.entry_dinamico_texto.get().strip()
            if not desc: return messagebox.showerror("Error", "Debes ingresar un porcentaje de descuento (solo el número).")
            params['descuento'] = desc
        elif tipo == "Novedades":
            her = self.combo_novedad_herramienta.get()
            params['subtipo_novedad'] = self.combo_novedad_subtipo.get()
            params['herramienta_novedad'] = her
            df_ok = df_ok[df_ok['Fav_Temp'] == her]
            if df_ok.empty: return messagebox.showwarning("Filtro", f"Ningún cliente en pantalla tiene como interés '{her}'.")
        elif tipo == "Gira Vendedor":
            if not self.entry_dinamico_texto.get().strip(): return messagebox.showerror("Error", "Falta vendedor.")
            params['texto_extra'] = self.entry_dinamico_texto.get().strip()
        elif tipo == "Personalizado":
            if not self.ruta_imagen_seleccionada: return messagebox.showerror("Error", "Imagen obligatoria.")
            if not self.text_dinamico_multilinea.get("1.0", tk.END).strip(): return messagebox.showerror("Error", "Texto obligatorio.")
            params['texto_extra'] = self.text_dinamico_multilinea.get("1.0", tk.END).strip()

        if not messagebox.askyesno("Confirmar Envío", f"Revisá la Vista Previa a la derecha.\n\n¿Estás seguro que deseas disparar la campaña a {len(df_ok)} destinatarios?"): return
        
        self.cancelar_envio = False
        self.btn_enviar.config(state="disabled")
        self.btn_cancelar.config(state="normal", text="🛑 CANCELAR ENVÍO")
        
        threading.Thread(target=self._proceso_envio, args=(tipo, params, df_ok)).start()

    def _proceso_envio(self, tipo, params, df):
        media_id = None
        if params.get('ruta_imagen'):
            self.lbl_progreso.config(text="Subiendo imagen a Meta...", fg="blue")
            media_id = mainCode.subir_imagen_whatsapp(params['ruta_imagen'])
            if not media_id: 
                self.root.after(0, lambda: self.btn_enviar.config(state="normal"))
                self.root.after(0, lambda: self.btn_cancelar.config(state="disabled"))
                return messagebox.showerror("Error", "Fallo subida imagen a Meta.")

        id_tanda_actual = datetime.now().strftime("TANDA_%Y%m%d_%H%M%S")
        tot = len(df); ok = 0; err = 0; hubo_error_servidor = False; hubo_error_cliente = False
        
        for i, (_, row) in enumerate(df.iterrows()):
            if self.cancelar_envio: break
            self.root.after(0, lambda x=i: self.lbl_progreso.config(text=f"Cliente {x+1}/{tot}...", fg="blue"))
            
            if tipo == "Recotización":
                tel_v = mainCode.DB_VENDEDORES["Emmanuel"][0]
                d_extra = {'cliente_nombre': row['Cliente'], 'herramienta': row.get('Fav_Temp','un producto')}
            else:
                tel_v = mainCode.obtener_telefono_vendedor(row.get('Vendedor','0'), params.get('preferencia_index', 0)) if params['modo_vendedor'] == "AUTO" else params['tel_fijo']
                d_extra = {'vendedor_nombre': params.get('texto_extra',''), 'herramienta': params.get('herramienta_novedad',''), 'subtipo': params.get('subtipo_novedad','')}
            
            link = mainCode.generar_link_whatsapp(tel_v, tipo, d_extra)
            
            for t in row['Telefonos_Validos']:
                if self.cancelar_envio: break
                res = False; tipo_error = ""
                
                if media_id and tipo != "Personalizado": 
                    mainCode.enviar_solo_imagen(t, media_id)
                    time.sleep(0.5)
                
                if tipo == "Promociones": res, tipo_error = mainCode.enviar_promocion(t, row['Cliente'], params['descuento'], link)
                elif tipo == "Novedades": res, tipo_error = mainCode.enviar_novedades(t, params['subtipo_novedad'], params['herramienta_novedad'], link)
                elif tipo == "Rescate (Te extrañamos)": res, tipo_error = mainCode.enviar_rescate(t, row['Cliente'], row.get('Fav_Temp','-'), f"Contacto: {link}")
                elif tipo == "Gira Vendedor": res, tipo_error = mainCode.enviar_gira(t, params.get('texto_extra','Vendedor'), row.get('Fav_Temp','-'), "Ofertas", f"Contacto: {link}")
                elif tipo == "Recotización": res, tipo_error = mainCode.enviar_recotizacion(t, link)
                elif tipo == "Personalizado": 
                    txt_base = params.get('texto_extra','')
                    caption_final = txt_base.replace("[CLIENTE]", row['Cliente']).replace("[LINK]", link)
                    if "[LINK]" not in txt_base:
                        caption_final += f"\n\nContacto: {link}"
                    res, tipo_error = mainCode.enviar_personalizado(t, caption_final, media_id)

                if res: ok += 1; estado_individual = "ENVIADO CORRECTAMENTE"
                else: 
                    err += 1; estado_individual = tipo_error
                    if tipo_error == "ERROR DEL CLIENTE": hubo_error_cliente = True
                    else: hubo_error_servidor = True
                
                herramienta_usada = row.get('Fav_Temp', '-') if tipo == "Recotización" else params.get('herramienta_novedad', '-')
                mainCode.registrar_envio_db(id_tanda_actual, row['Cliente'], t, tel_v, tipo, herramienta_usada, estado_individual)
                time.sleep(1)

        if self.cancelar_envio: estado_final_tanda = "CAMPAÑA CANCELADA"
        elif hubo_error_servidor: estado_final_tanda = "ERROR DEL SERVIDOR"
        elif hubo_error_cliente: estado_final_tanda = "ERROR DEL CLIENTE"
        else: estado_final_tanda = "ENVIADO CON EXITO"
            
        mainCode.actualizar_estado_tanda(id_tanda_actual, estado_final_tanda)
        self.root.after(0, lambda: self.btn_enviar.config(state="normal"))
        self.root.after(0, lambda: self.btn_cancelar.config(state="disabled", text="🛑 CANCELAR ENVÍO"))
        
        if self.cancelar_envio:
            self.root.after(0, lambda: self.lbl_progreso.config(text="Envío Cancelado", fg="red"))
            self.root.after(0, lambda: messagebox.showwarning("Proceso Detenido", f"La campaña fue frenada.\n\nEnviados con éxito: {ok}\nErrores: {err}"))
        else:
            self.root.after(0, lambda: self.lbl_progreso.config(text="Campaña completada", fg="green"))
            self.root.after(0, lambda: messagebox.showinfo("Reporte Final", f"Campaña Finalizada.\n\nEnviados con éxito: {ok}\nErrores: {err}\n\nQuedó registrada en el historial como: {estado_final_tanda}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = WoodToolsApp(root)
    root.mainloop()