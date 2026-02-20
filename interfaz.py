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

import mainCode 

# ==========================================
# LÓGICA PARA RUTAS INTERNAS (IMÁGENES)
# ==========================================
def obtener_ruta_interna(ruta_relativa):
    try:
        ruta_base = sys._MEIPASS
    except Exception:
        ruta_base = os.path.abspath(".")
    return os.path.join(ruta_base, ruta_relativa)

class WoodToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Marketing WhatsApp v5.0 - Links Autocompletables")
        self.root.geometry("1400x900") 
        
        # ==========================================
        # CONFIGURACIÓN DE ÍCONOS (.ICO) Y BARRA DE TAREAS
        # ==========================================
        try:
            myappid = 'woodtools.gestormarketing.5.0' 
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass 
            
        ruta_ico = obtener_ruta_interna(r"Imagenes\logo.ico")
        if not os.path.exists(ruta_ico):
            ruta_ico = obtener_ruta_interna("logo.ico")
            
        if os.path.exists(ruta_ico):
            try:
                self.root.iconbitmap(ruta_ico)
            except Exception as e:
                print(f"Error cargando icono .ico: {e}")

        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.ruta_imagen_seleccionada = None
        
        # ==========================================
        # 1. CABECERA (LOGO .PNG ARRIBA A LA DERECHA)
        # ==========================================
        frame_top = tk.Frame(root, pady=10, padx=10, bg="#e0e0e0")
        frame_top.pack(fill="x")
        
        self.cargar_logo(frame_top)

        btn_cargar = tk.Button(frame_top, text="🔄 Cargar Base de Datos", command=self.cargar_datos, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"))
        btn_cargar.pack(side=tk.LEFT, padx=10)
        
        btn_verificar = tk.Button(frame_top, text="🔍 Ver Clientes Descartados", command=self.verificar_observados, bg="#FF9800", fg="white", font=("Segoe UI", 10, "bold"))
        btn_verificar.pack(side=tk.LEFT, padx=10)
        
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
        
        tk.Label(frame_filtros, text="Zona:").grid(row=0, column=2)
        self.combo_zona = ttk.Combobox(frame_filtros, state="readonly", width=10)
        self.combo_zona.grid(row=0, column=3)
        self.combo_zona.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        tk.Label(frame_filtros, text="Favorito:").grid(row=0, column=4)
        self.combo_herramientas = ttk.Combobox(frame_filtros, state="readonly")
        self.combo_herramientas.grid(row=0, column=5)
        self.combo_herramientas.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        btn_limpiar = tk.Button(frame_filtros, text="Limpiar", command=self.limpiar_filtros)
        btn_limpiar.grid(row=0, column=6, padx=15)
        
        self.lbl_conteo = tk.Label(frame_filtros, text="Regs: 0", font=("Segoe UI", 9, "bold"), fg="#2196F3")
        self.lbl_conteo.grid(row=0, column=7, padx=20)

        # ==========================================
        # 3. CONFIGURACIÓN DEL MENSAJE
        # ==========================================
        frame_campana = tk.LabelFrame(root, text="Configuración de Envío", padx=10, pady=10, bg="#f5f5f5")
        frame_campana.pack(fill="x", padx=20, pady=10)

        tk.Label(frame_campana, text="Tipo Mensaje:", bg="#f5f5f5").grid(row=0, column=0, sticky="w")
        self.tipo_mensaje_var = tk.StringVar(value="Promociones")
        
        opciones_plantillas = ["Promociones", "Rescate (Te extrañamos)", "Gira Vendedor", "Personalizado", "Novedades"]
        self.combo_tipo_mensaje = ttk.Combobox(frame_campana, values=opciones_plantillas, state="readonly", textvariable=self.tipo_mensaje_var, width=25)
        self.combo_tipo_mensaje.grid(row=1, column=0, padx=5, pady=5)
        self.combo_tipo_mensaje.bind("<<ComboboxSelected>>", self.actualizar_inputs_dinamicos)

        tk.Label(frame_campana, text="Enviar como (Link Vendedor):", bg="#f5f5f5").grid(row=0, column=1, sticky="w", padx=20)
        
        opciones_vendedores = ["AUTOMÁTICO (Según Excel)"] + list(mainCode.DB_VENDEDORES.keys())
        self.combo_vendedor = ttk.Combobox(frame_campana, values=opciones_vendedores, state="readonly", width=30)
        self.combo_vendedor.grid(row=1, column=1, padx=20, pady=5)
        self.combo_vendedor.current(0)

        # --- RECUADRO DINÁMICO (COSTADO) ---
        self.frame_dinamico = tk.Frame(frame_campana, bg="#f5f5f5")
        self.frame_dinamico.grid(row=0, column=2, rowspan=2, padx=30, sticky="nesw")
        
        self.lbl_dinamico_titulo = tk.Label(self.frame_dinamico, text="", bg="#f5f5f5", font=("Arial", 8, "bold"))
        self.entry_dinamico_texto = tk.Entry(self.frame_dinamico, width=40)
        
        # --- NUEVO: CUADRO GRANDE PARA EL MENSAJE PERSONALIZADO ---
        self.text_dinamico_multilinea = tk.Text(self.frame_dinamico, width=55, height=5, font=("Arial", 10), relief="solid", bd=1)
        
        self.btn_subir_imagen = tk.Button(self.frame_dinamico, text="📂 Adjuntar Imagen", command=self.seleccionar_imagen)
        self.lbl_nombre_imagen = tk.Label(self.frame_dinamico, text="Sin imagen", bg="#f5f5f5", fg="red")

        self.lbl_novedad_subtipo = tk.Label(self.frame_dinamico, text="Tipo de Novedad:", bg="#f5f5f5", font=("Arial", 8, "bold"))
        self.combo_novedad_subtipo = ttk.Combobox(self.frame_dinamico, values=["Ingresos", "Reposición de stock"], state="readonly", width=30)
        self.lbl_novedad_herramienta = tk.Label(self.frame_dinamico, text="Herramienta a promocionar:", bg="#f5f5f5", font=("Arial", 8, "bold"))
        self.combo_novedad_herramienta = ttk.Combobox(self.frame_dinamico, state="readonly", width=30)

        self.actualizar_inputs_dinamicos() 

        # ==========================================
        # 4. BOTÓN DE ENVÍO
        # ==========================================
        frame_accion = tk.Frame(root, pady=15, bg="#333333")
        frame_accion.pack(fill="x", side="bottom")
        
        self.lbl_progreso = tk.Label(frame_accion, text="Sistema listo.", fg="white", bg="#333333")
        self.lbl_progreso.pack(pady=5)
        
        btn_enviar = tk.Button(frame_accion, text="🚀 ENVIAR A TODOS LOS NÚMEROS VÁLIDOS", command=self.iniciar_envio, bg="#2196F3", fg="white", font=("Segoe UI", 12, "bold"))
        btn_enviar.pack(pady=10)

        # ==========================================
        # 5. PANEL DE DETALLES
        # ==========================================
        self.frame_telefonos = tk.LabelFrame(root, text="🔍 Alternativas Encontradas (Clic en la tabla arriba para ver)", padx=10, pady=10, bg="#f5f5f5", font=("Segoe UI", 9, "bold"))
        self.frame_telefonos.pack(fill="x", padx=20, pady=5, side="bottom")
        self._limpiar_panel_telefonos()

        # ==========================================
        # 6. TABLA DE RESULTADOS
        # ==========================================
        frame_tabla = tk.Frame(root)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=5)
        
        self.tree = ttk.Treeview(frame_tabla, columns=("Cli", "Tel", "Vend", "Zona", "Est"), show="headings")
        self.tree.heading("Cli", text="Cliente")
        self.tree.column("Cli", width=200)
        self.tree.heading("Tel", text="Se enviará a:")
        self.tree.column("Tel", width=250)
        self.tree.heading("Vend", text="Vendedor (Excel)")
        self.tree.column("Vend", width=100)
        self.tree.heading("Zona", text="Zona")
        self.tree.column("Zona", width=80)
        self.tree.heading("Est", text="Estado")
        self.tree.column("Est", width=120)
        
        self.tree.tag_configure('valido', background='white')
        self.tree.tag_configure('invalido', background='#FFCCCC', foreground='red')
        
        self.tree.bind("<<TreeviewSelect>>", self.al_seleccionar_cliente)

        scroll = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scroll.set)
        scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

    # ==========================================
    # LÓGICA DE INTERFAZ Y EVENTOS
    # ==========================================
    def cargar_logo(self, parent):
        ruta_1 = obtener_ruta_interna(r"Imagenes\logo.png")
        ruta_2 = obtener_ruta_interna("logo.png")
        ruta_final = ruta_1 if os.path.exists(ruta_1) else ruta_2
        
        if os.path.exists(ruta_final):
            try:
                img_abierta = Image.open(ruta_final)
                ancho_original, alto_original = img_abierta.size
                alto_deseado = 65 
                ancho_proporcional = int((alto_deseado / alto_original) * ancho_original)
                img_redimensionada = img_abierta.resize((ancho_proporcional, alto_deseado), Image.Resampling.LANCZOS)
                
                self.logo_img = ImageTk.PhotoImage(img_redimensionada)
                tk.Label(parent, image=self.logo_img, bg="#e0e0e0").pack(side=tk.RIGHT, padx=15)
            except Exception as e:
                print(f"Error cargando el logo: {e}")

    def verificar_observados(self):
        msg = mainCode.revisar_numeros_problematicos()
        vent = tk.Toplevel(self.root)
        vent.title("Reporte de Clientes Descartados")
        vent.geometry("500x400")
        
        try:
            ruta_ico = obtener_ruta_interna(r"Imagenes\logo.ico")
            if not os.path.exists(ruta_ico): ruta_ico = obtener_ruta_interna("logo.ico")
            if os.path.exists(ruta_ico): vent.iconbitmap(ruta_ico)
        except: pass

        t = tk.Text(vent, wrap="word", padx=10, pady=10)
        t.pack(fill="both", expand=True)
        t.insert("1.0", msg)
        t.config(state="disabled")

    def actualizar_inputs_dinamicos(self, event=None):
        tipo = self.tipo_mensaje_var.get()
        for widget in self.frame_dinamico.winfo_children(): 
            widget.pack_forget()
        
        if tipo == "Gira Vendedor":
            self.lbl_dinamico_titulo.config(text="Nombre del Vendedor que viaja:")
            self.lbl_dinamico_titulo.pack(anchor="w")
            self.entry_dinamico_texto.pack(anchor="w", pady=5)
            
        elif tipo == "Personalizado":
            self.lbl_dinamico_titulo.config(text="Escribe el mensaje (Caption):")
            self.lbl_dinamico_titulo.pack(anchor="w")
            self.text_dinamico_multilinea.pack(anchor="w", pady=5)
            self.btn_subir_imagen.pack(anchor="w", pady=5)
            self.lbl_nombre_imagen.pack(anchor="w")
            
        elif tipo == "Novedades":
            self.lbl_novedad_subtipo.pack(anchor="w", pady=(0, 2))
            if self.combo_novedad_subtipo.get() == "":
                self.combo_novedad_subtipo.current(0)
            self.combo_novedad_subtipo.pack(anchor="w", pady=(0, 10))
            
            self.lbl_novedad_herramienta.pack(anchor="w", pady=(0, 2))
            herramientas_disponibles = mainCode.identificar_cols_productos(pd.DataFrame())
            self.combo_novedad_herramienta['values'] = herramientas_disponibles
            if self.combo_novedad_herramienta.get() == "":
                self.combo_novedad_herramienta.current(0)
            self.combo_novedad_herramienta.pack(anchor="w")

    def seleccionar_imagen(self):
        ruta = filedialog.askopenfilename(filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        if ruta: 
            self.ruta_imagen_seleccionada = ruta
            self.lbl_nombre_imagen.config(text="Imagen Seleccionada OK", fg="green")

    def _limpiar_panel_telefonos(self):
        for widget in self.frame_telefonos.winfo_children(): 
            widget.destroy()
        tk.Label(self.frame_telefonos, text="Haz clic en un cliente de la tabla para ver sus números descartados (rojo) y válidos (verde).", bg="#f5f5f5", fg="gray").pack(pady=10)

    def al_seleccionar_cliente(self, event):
        seleccion = self.tree.selection()
        if not seleccion: return
        
        idx = int(seleccion[0])
        row = self.df_filtrado.loc[idx]
        
        for widget in self.frame_telefonos.winfo_children(): widget.destroy()
            
        tels_raw = row.get('Telefonos_Raw', [])
        if not isinstance(tels_raw, list) or len(tels_raw) == 0:
            tk.Label(self.frame_telefonos, text="No se encontró ningún número en las columnas de este cliente.", fg="red", bg="#f5f5f5").pack(side="left")
            return
            
        for t in tels_raw:
            es_valido, t_fmt = mainCode.validar_formato_numero(t)
            if es_valido:
                bg_color, fg_color, border_color = "#E8F5E9", "#2E7D32", "green"
                txt_status = f"✅ Enviar a: {t_fmt}"
            else:
                bg_color, fg_color, border_color = "#FFEBEE", "#C62828", "red"
                txt_status = "❌ Descartado"
                
            frame_tel = tk.Frame(self.frame_telefonos, bg=bg_color, highlightbackground=border_color, highlightthickness=2, padx=10, pady=5)
            frame_tel.pack(side="left", padx=10, fill="y")
            tk.Label(frame_tel, text=t, font=("Segoe UI", 10, "bold"), bg=bg_color, fg=fg_color).pack()
            tk.Label(frame_tel, text=txt_status, font=("Segoe UI", 8), bg=bg_color, fg=fg_color).pack()

    # ==========================================
    # CARGA Y FILTRADO DE DATOS
    # ==========================================
    def cargar_datos(self):
        self.lbl_status_db.config(text="Cargando base de datos...", fg="blue")
        threading.Thread(target=self._hilo_carga).start()

    def _hilo_carga(self):
        df = mainCode.conectar_y_procesar()
        if df.empty: 
            self.root.after(0, lambda: self.lbl_status_db.config(text="Error", fg="red"))
            self.root.after(0, lambda: messagebox.showerror("Error", "Base vacía o 'Base de datos wt.xlsx' no encontrada en la carpeta."))
            return
        
        for col in ['Zona', 'Vendedor']: 
            if col not in df.columns: df[col] = "0"
            df[col] = df[col].astype(str)

        cols_prod = mainCode.identificar_cols_productos(df)
        
        # ASIGNACIÓN TEMPORAL DE FAVORITOS
        df['Fav_Temp'] = "Sierras" 
        df['Sec_Temp'] = "Cuchillas"
        
        self.df_original = df
        self.df_filtrado = df.copy()
        
        self.combo_zona['values'] = ["Todas"] + sorted(df['Zona'].unique().tolist())
        self.combo_zona.current(0)
        self.combo_herramientas['values'] = ["Todos"] + cols_prod
        self.combo_herramientas.current(0)
        
        self.root.after(0, self._limpiar_panel_telefonos)
        self.root.after(0, self.actualizar_tabla)
        self.root.after(0, lambda: self.lbl_status_db.config(text=f"Cargado: {len(df)} clientes listos", fg="green"))

    def actualizar_tabla(self):
        for item in self.tree.get_children(): self.tree.delete(item)
            
        for idx, row in self.df_filtrado.iterrows():
            tag = "valido" if row['Es_Valido'] else "invalido"
            if row['Es_Valido']:
                count = len(row['Telefonos_Validos'])
                estado_texto = f"OK ({count} nros)"
            else:
                estado_texto = "DESCARTADO"
            
            valores = (row['Cliente'], row.get('Tel_Formateado', '-'), row.get('Vendedor', '-'), row['Zona'], estado_texto)
            self.tree.insert("", "end", iid=idx, values=valores, tags=(tag,))
            
        self.lbl_conteo.config(text=f"Registros Visibles: {len(self.df_filtrado)}")

    def aplicar_filtros(self, event=None):
        if self.df_original.empty: return
        df = self.df_original.copy()
        nombre_filtro = self.entry_nombre.get().lower()
        if nombre_filtro: df = df[df['Cliente'].str.lower().str.contains(nombre_filtro, na=False)]
        zona_filtro = self.combo_zona.get()
        if zona_filtro != "Todas": df = df[df['Zona'] == zona_filtro]
        self.df_filtrado = df
        self.actualizar_tabla()
        self._limpiar_panel_telefonos()

    def limpiar_filtros(self):
        self.entry_nombre.delete(0, tk.END)
        self.combo_zona.current(0)
        self.combo_herramientas.current(0)
        self.aplicar_filtros()

    # ==========================================
    # LÓGICA DE ENVÍO MASIVO
    # ==========================================
    def iniciar_envio(self):
        df_ok = self.df_filtrado[self.df_filtrado['Es_Valido'] == True]
        if df_ok.empty: return messagebox.showwarning("Atención", "No hay clientes válidos con números correctos para enviar.")

        seleccion_ui = self.combo_vendedor.get()
        params = {}
        
        if "AUTOMÁTICO" in seleccion_ui:
            params['modo_vendedor'] = "AUTO"
            rta = messagebox.askyesno("Vendedores Compartidos", "En el Excel el código '0' tiene 2 vendedores.\n\n¿Deseas usar a Valentín (Primer número)?\n(Si presionas Sí = Valentín, si presionas No = Carlos)")
            params['preferencia_index'] = 0 if rta else 1
        else:
            params['modo_vendedor'] = "MANUAL"
            numeros = mainCode.DB_VENDEDORES.get(seleccion_ui, [])
            params['tel_fijo'] = numeros[0] if numeros else "5491145394279"

        tipo = self.tipo_mensaje_var.get()
        
        if tipo == "Novedades":
            herramienta_elegida = self.combo_novedad_herramienta.get()
            params['subtipo_novedad'] = self.combo_novedad_subtipo.get()
            params['herramienta_novedad'] = herramienta_elegida
            df_ok = df_ok[df_ok['Fav_Temp'] == herramienta_elegida]
            if df_ok.empty: return messagebox.showwarning("Filtro Inteligente", f"No se encontraron clientes válidos cuyo producto favorito sea '{herramienta_elegida}'.")
        
        elif tipo == "Gira Vendedor": 
            texto = self.entry_dinamico_texto.get().strip()
            if not texto: return messagebox.showerror("Error", "El nombre del vendedor no puede estar vacío.")
            params['texto_extra'] = texto
            
        elif tipo == "Personalizado":
            if not self.ruta_imagen_seleccionada: 
                return messagebox.showerror("Error", "Debes adjuntar una imagen para enviar un mensaje Personalizado.")
            texto = self.text_dinamico_multilinea.get("1.0", tk.END).strip()
            if not texto: return messagebox.showerror("Error", "El campo de mensaje no puede estar vacío.")
            params['texto_extra'] = texto
            params['ruta_imagen'] = self.ruta_imagen_seleccionada

        msg_confirmacion = f"¡ATENCIÓN!\n\nSe procesarán {len(df_ok)} clientes válidos.\n\nRegla activa: Si un cliente tiene 2 teléfonos correctos, el mensaje le llegará a AMBOS números automáticamente.\n\n¿Estás seguro de iniciar?"
        if not messagebox.askyesno("Confirmar Envío Masivo", msg_confirmacion): return
        
        threading.Thread(target=self._proceso_envio, args=(tipo, params, df_ok)).start()

    def _proceso_envio(self, tipo, params, df):
        media_id = None
        if tipo == "Personalizado": 
            self.lbl_progreso.config(text="Subiendo imagen a Meta...", fg="blue")
            media_id = mainCode.subir_imagen_whatsapp(params['ruta_imagen'])
            if not media_id:
                self.root.after(0, lambda: messagebox.showerror("Error API", "Falló la subida de la imagen a WhatsApp Meta. Abortando."))
                return
        
        total_clientes = len(df)
        clientes_procesados = 0
        mensajes_ok = 0
        mensajes_err = 0

        for _, row in df.iterrows():
            clientes_procesados += 1
            self.root.after(0, lambda x=clientes_procesados: self.lbl_progreso.config(text=f"Procesando Cliente {x}/{total_clientes}...", fg="blue"))
            
            # 1. Determinar de quién es el Link
            if params['modo_vendedor'] == "AUTO":
                codigo_vendedor_celda = row.get('Vendedor', '0')
                tel_vendedor = mainCode.obtener_telefono_vendedor(codigo_vendedor_celda, params['preferencia_index'])
            else:
                tel_vendedor = params['tel_fijo']
            
            # 2. Generar el enlace inteligente con espacios [ ] para que el cliente llene
            datos_extra = {
                'vendedor_nombre': params.get('texto_extra', 'el vendedor'),
                'herramienta': params.get('herramienta_novedad', 'herramientas'),
                'subtipo': params.get('subtipo_novedad', '')
            }
            link_inteligente = mainCode.generar_link_whatsapp(tel_vendedor, tipo, datos_extra)
            
            # 3. Enviar
            validos_del_cliente = row['Telefonos_Validos']
            if isinstance(validos_del_cliente, list):
                for tel_destino in validos_del_cliente:
                    exito = False
                    
                    if tipo == "Novedades":
                        exito, _ = mainCode.enviar_novedades(tel_destino, params['subtipo_novedad'], params['herramienta_novedad'], link_inteligente)
                    else:
                        # Para las demás plantillas, adjuntamos "Contacto directo:" junto al link
                        texto_footer = f"Contacto directo: {link_inteligente}"
                        
                        if tipo == "Promociones": 
                            exito, _ = mainCode.enviar_promocion(tel_destino, "Promociones exclusivas", "Herramientas", "Ofertas", texto_footer)
                        elif tipo == "Rescate (Te extrañamos)": 
                            exito, _ = mainCode.enviar_rescate(tel_destino, row['Cliente'], row.get('Fav_Temp','-'), texto_footer)
                        elif tipo == "Gira Vendedor": 
                            exito, _ = mainCode.enviar_gira(tel_destino, params.get('texto_extra','Vendedor'), row.get('Fav_Temp','-'), "Ofertas", texto_footer)
                        elif tipo == "Personalizado": 
                            exito, _ = mainCode.enviar_personalizado(tel_destino, params.get('texto_extra',''), media_id, texto_footer)

                    if exito: mensajes_ok += 1
                    else: mensajes_err += 1
                    time.sleep(1) 

        self.root.after(0, lambda: self.lbl_progreso.config(text="Proceso Finalizado", fg="green"))
        self.root.after(0, lambda: messagebox.showinfo("Reporte Final", f"Campaña Finalizada.\n\n📱 Mensajes entregados a la API: {mensajes_ok}\n❌ Errores de API: {mensajes_err}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = WoodToolsApp(root)
    root.mainloop()