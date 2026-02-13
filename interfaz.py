# NOMBRE DEL ARCHIVO: interfaz_app.py
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk 
import pandas as pd
import threading
import os
import sys 
import time

# --- IMPORTAMOS TU BACKEND ---
import mainCode 

class WoodToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Marketing WhatsApp")
        self.root.geometry("1350x850") 
        
        # Variables de estado
        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.ruta_imagen_seleccionada = None
        
        # --- 1. CABECERA ---
        frame_top = tk.Frame(root, pady=10, padx=10, bg="#e0e0e0")
        frame_top.pack(fill="x")
        
        self.cargar_logo(frame_top)

        btn_cargar = tk.Button(frame_top, text="🔄 Cargar Base de Datos Interna", command=self.cargar_datos, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"))
        btn_cargar.pack(side=tk.LEFT, padx=10)
        
        self.lbl_status_db = tk.Label(frame_top, text="Estado: Esperando datos...", fg="gray", bg="#e0e0e0", font=("Segoe UI", 10))
        self.lbl_status_db.pack(side=tk.LEFT, padx=10)

        # --- 2. ÁREA DE FILTROS ---
        frame_filtros = tk.LabelFrame(root, text="Filtros de Audiencia", padx=10, pady=10, font=("Segoe UI", 10, "bold"))
        frame_filtros.pack(fill="x", padx=20, pady=5)
        
        # Filtro Nombre
        tk.Label(frame_filtros, text="Nombre:").grid(row=0, column=0, padx=5)
        self.entry_nombre = tk.Entry(frame_filtros)
        self.entry_nombre.grid(row=0, column=1, padx=5)
        self.entry_nombre.bind("<KeyRelease>", self.aplicar_filtros) 
        
        # Filtro Zona
        tk.Label(frame_filtros, text="Zona:").grid(row=0, column=2, padx=5)
        self.combo_zona = ttk.Combobox(frame_filtros, state="readonly", width=10)
        self.combo_zona.grid(row=0, column=3, padx=5)
        self.combo_zona.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        # Filtro Producto
        tk.Label(frame_filtros, text="Producto Comprado (>0):").grid(row=0, column=4, padx=5)
        self.combo_herramientas = ttk.Combobox(frame_filtros, state="readonly")
        self.combo_herramientas.grid(row=0, column=5, padx=5)
        self.combo_herramientas.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        btn_limpiar = tk.Button(frame_filtros, text="Limpiar Filtros", command=self.limpiar_filtros)
        btn_limpiar.grid(row=0, column=6, padx=15)

        self.lbl_conteo = tk.Label(frame_filtros, text="Registros: 0", font=("Segoe UI", 9, "bold"), fg="#2196F3")
        self.lbl_conteo.grid(row=0, column=7, padx=20)

        # --- 3. CONFIGURACIÓN DE CAMPAÑA ---
        frame_campana = tk.LabelFrame(root, text="Configuración del Mensaje", padx=10, pady=10, bg="#f5f5f5", font=("Segoe UI", 10, "bold"))
        frame_campana.pack(fill="x", padx=20, pady=10)

        tk.Label(frame_campana, text="Tipo de Mensaje:", bg="#f5f5f5").grid(row=0, column=0, sticky="w")
        self.tipo_mensaje_var = tk.StringVar(value="Promociones")
        opciones_mensaje = ["Promociones", "Rescate (Te extrañamos)", "Gira Vendedor", "Personalizado"]
        self.combo_tipo_mensaje = ttk.Combobox(frame_campana, values=opciones_mensaje, state="readonly", textvariable=self.tipo_mensaje_var, width=25)
        self.combo_tipo_mensaje.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.combo_tipo_mensaje.bind("<<ComboboxSelected>>", self.actualizar_inputs_dinamicos)

        tk.Label(frame_campana, text="Vendedor (Link WhatsApp):", bg="#f5f5f5").grid(row=0, column=1, sticky="w", padx=20)
        self.opciones_vendedores_keys = list(mainCode.DB_VENDEDORES.keys())
        self.combo_vendedor = ttk.Combobox(frame_campana, values=self.opciones_vendedores_keys, state="readonly", width=15)
        self.combo_vendedor.grid(row=1, column=1, padx=20, pady=5, sticky="w")
        if self.opciones_vendedores_keys: self.combo_vendedor.current(0)

        self.frame_dinamico = tk.Frame(frame_campana, bg="#f5f5f5", bd=1, relief="solid")
        self.frame_dinamico.grid(row=0, column=2, rowspan=2, padx=30, sticky="nesw")

        self.lbl_dinamico_titulo = tk.Label(self.frame_dinamico, text="", bg="#f5f5f5", font=("Arial", 8, "bold"))
        self.entry_dinamico_texto = tk.Entry(self.frame_dinamico, width=40)
        self.btn_subir_imagen = tk.Button(self.frame_dinamico, text="📂 Adjuntar Imagen (.jpg/.png)", command=self.seleccionar_imagen, bg="#FF9800", fg="white")
        self.lbl_nombre_imagen = tk.Label(self.frame_dinamico, text="Sin imagen", bg="#f5f5f5", fg="red", font=("Arial", 8))

        self.actualizar_inputs_dinamicos() 

        # --- 4. TABLA DE DATOS ---
        frame_tabla = tk.Frame(root)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Agregamos columna ZONA
        cols = ("Cliente", "Telefono", "Zona", "Prod. Favorito", "Prod. Secundario")
        self.tree = ttk.Treeview(frame_tabla, columns=cols, show="headings")
        
        self.tree.heading("Cliente", text="Cliente"); self.tree.column("Cliente", width=200)
        self.tree.heading("Telefono", text="Teléfono"); self.tree.column("Telefono", width=120)
        self.tree.heading("Zona", text="Zona"); self.tree.column("Zona", width=80)
        self.tree.heading("Prod. Favorito", text="Prod. Favorito"); self.tree.column("Prod. Favorito", width=200)
        self.tree.heading("Prod. Secundario", text="Prod. Secundario"); self.tree.column("Prod. Secundario", width=200)
        
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # --- 5. PIE DE PÁGINA ---
        frame_accion = tk.Frame(root, pady=15, bg="#333333")
        frame_accion.pack(fill="x", side="bottom")
        
        self.lbl_progreso = tk.Label(frame_accion, text="Sistema listo.", fg="white", bg="#333333", font=("Segoe UI", 11))
        self.lbl_progreso.pack(pady=(5, 0))

        btn_enviar = tk.Button(frame_accion, text="🚀 ENVIAR MENSAJES AHORA", command=self.iniciar_envio, bg="#2196F3", fg="white", font=("Segoe UI", 12, "bold"), padx=30, pady=10)
        btn_enviar.pack(pady=10)

    # =========================================================================
    # LÓGICA
    # =========================================================================

    def cargar_logo(self, parent):
        ruta = "logo.png" 
        if os.path.exists(ruta):
            try:
                img = Image.open(ruta)
                img = img.resize((150, 50)) 
                self.logo_img = ImageTk.PhotoImage(img)
                tk.Label(parent, image=self.logo_img, bg="#e0e0e0").pack(side=tk.RIGHT, padx=10)
            except: pass

    def actualizar_inputs_dinamicos(self, event=None):
        tipo = self.tipo_mensaje_var.get()
        self.lbl_dinamico_titulo.pack_forget()
        self.entry_dinamico_texto.pack_forget()
        self.btn_subir_imagen.pack_forget()
        self.lbl_nombre_imagen.pack_forget()

        if tipo == "Gira Vendedor":
            self.lbl_dinamico_titulo.config(text="Nombre del Vendedor que viaja:")
            self.lbl_dinamico_titulo.pack(anchor="w", padx=5, pady=2)
            self.entry_dinamico_texto.pack(anchor="w", padx=5, pady=2)
        elif tipo == "Personalizado":
            self.lbl_dinamico_titulo.config(text="Escribe el mensaje (Caption):")
            self.lbl_dinamico_titulo.pack(anchor="w", padx=5, pady=2)
            self.entry_dinamico_texto.pack(anchor="w", padx=5, pady=2)
            self.btn_subir_imagen.pack(anchor="w", padx=5, pady=5)
            self.lbl_nombre_imagen.pack(anchor="w", padx=5)

    def seleccionar_imagen(self):
        ruta = filedialog.askopenfilename(title="Seleccionar Imagen", filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        if ruta:
            ext = os.path.splitext(ruta)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png']:
                messagebox.showerror("Error", "Solo JPG o PNG.")
                self.ruta_imagen_seleccionada = None
                self.lbl_nombre_imagen.config(text="Formato inválido", fg="red")
            else:
                self.ruta_imagen_seleccionada = ruta
                self.lbl_nombre_imagen.config(text=os.path.basename(ruta), fg="green")

    def cargar_datos(self):
        self.lbl_status_db.config(text="Leyendo diccionario interno...", fg="blue")
        threading.Thread(target=self._hilo_carga).start()

    def _hilo_carga(self):
        df = mainCode.conectar_sheets() 
        if df.empty:
            self.root.after(0, lambda: self.lbl_status_db.config(text="Error: Diccionario vacío", fg="red"))
            return
        
        self.df_original = df
        
        # Aseguramos columna ZONA
        if 'Zona' not in self.df_original.columns:
            self.df_original['Zona'] = "N/A"
        else:
            # Convertimos a string para el filtro
            self.df_original['Zona'] = self.df_original['Zona'].astype(str)

        self.df_filtrado = df.copy()

        # Llenar combo de PRODUCTOS
        cols_prod = mainCode.identificar_cols_productos(df)
        self.combo_herramientas['values'] = ["Todos"] + cols_prod
        self.combo_herramientas.current(0)
        
        # Llenar combo de ZONAS (Valores únicos ordenados)
        zonas_unicas = sorted(self.df_original['Zona'].unique().tolist())
        self.combo_zona['values'] = ["Todas"] + zonas_unicas
        self.combo_zona.current(0)
        
        self.root.after(0, self.actualizar_tabla)
        self.root.after(0, lambda: self.lbl_status_db.config(text=f"Base cargada: {len(df)} registros", fg="green"))

    def actualizar_tabla(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        cols_prod = mainCode.identificar_cols_productos(self.df_original)
        
        for index, row in self.df_filtrado.iterrows():
            nombre = row.get('Cliente', '')
            tel = row.get('Numero de Telefono', '')
            zona = row.get('Zona', '')
            
            p1, p2 = mainCode.obtener_top_personalizados(row, cols_prod)
            self.tree.insert("", "end", values=(nombre, tel, zona, p1, p2))
            
        self.lbl_conteo.config(text=f"Registros filtrados: {len(self.df_filtrado)}")

    def aplicar_filtros(self, event=None):
        if self.df_original.empty: return
        
        nom = self.entry_nombre.get().lower()
        zona_sel = self.combo_zona.get()
        prod = self.combo_herramientas.get()
        
        df = self.df_original.copy()
        
        # 1. Filtro Nombre
        if nom: 
            df = df[df['Cliente'].str.lower().str.contains(nom, na=False)]
        
        # 2. Filtro Zona
        if zona_sel != "Todas":
            df = df[df['Zona'] == zona_sel]
        
        # 3. Filtro Producto (ROBUSTO)
        if prod != "Todos":
            # Convertimos a numérico, los errores (texto) se vuelven NaN y luego 0
            df[prod] = pd.to_numeric(df[prod], errors='coerce').fillna(0)
            # Filtramos solo los mayores a 0
            df = df[df[prod] > 0]
            
        self.df_filtrado = df
        self.actualizar_tabla()

    def limpiar_filtros(self):
        self.entry_nombre.delete(0, tk.END)
        self.combo_zona.current(0)
        self.combo_herramientas.current(0)
        self.aplicar_filtros()

    def iniciar_envio(self):
        if self.df_filtrado.empty:
            messagebox.showwarning("Vacío", "No hay clientes en la lista para enviar.")
            return

        tipo = self.tipo_mensaje_var.get()
        vendedor_key = self.combo_vendedor.get()
        
        numeros = mainCode.DB_VENDEDORES.get(vendedor_key, [])
        if not numeros: 
            messagebox.showerror("Error", "Vendedor no válido")
            return
            
        tel_vendedor = numeros[0]
        if len(numeros) > 1:
            seleccion = simpledialog.askinteger("Selección Múltiple", 
                f"El código {vendedor_key} tiene varias líneas:\n1. {numeros[0]}\n2. {numeros[1]}\n\nElige 1 o 2:", 
                minvalue=1, maxvalue=2)
            if not seleccion: return
            tel_vendedor = numeros[seleccion-1]

        params = {'tel_vendedor': tel_vendedor}
        
        if tipo == "Gira Vendedor":
            nombre_vendedor = self.entry_dinamico_texto.get().strip()
            if not nombre_vendedor:
                messagebox.showerror("Faltan datos", "Escribe el nombre del vendedor.")
                return
            params['nombre_vendedor'] = nombre_vendedor

        elif tipo == "Personalizado":
            texto = self.entry_dinamico_texto.get().strip()
            if not texto: 
                messagebox.showerror("Faltan datos", "Escribe el texto del mensaje.")
                return
            if not self.ruta_imagen_seleccionada:
                messagebox.showerror("Error Imagen", "Debes seleccionar una imagen válida.")
                return
            params['texto'] = texto
            params['ruta_imagen'] = self.ruta_imagen_seleccionada

        if not messagebox.askyesno("CONFIRMAR ENVÍO MASIVO", f"Vas a enviar '{tipo}' a {len(self.df_filtrado)} contactos.\n\n¿Estás seguro?"):
            return

        threading.Thread(target=self._proceso_envio_backend, args=(tipo, params)).start()

    def _proceso_envio_backend(self, tipo, params):
        self.lbl_progreso.config(text="Iniciando motor de envíos...", fg="orange")
        
        media_id = None
        if tipo == "Personalizado":
            self.lbl_progreso.config(text="Subiendo imagen a Meta...", fg="blue")
            media_id = mainCode.subir_imagen_whatsapp(params['ruta_imagen'])
            if not media_id:
                self.root.after(0, lambda: messagebox.showerror("Error API", "No se pudo subir la imagen."))
                self.lbl_progreso.config(text="Error subida imagen.", fg="red")
                return

        top_global_p1, top_global_p2, top_global_p3 = "A", "B", "C"
        if tipo == "Promociones":
            top_global_p1, top_global_p2, top_global_p3 = mainCode.obtener_top_3_globales(self.df_original)

        cols_prod = mainCode.identificar_cols_productos(self.df_original)
        total = len(self.df_filtrado)
        ok_count = 0
        err_count = 0

        for i, row in self.df_filtrado.iterrows():
            self.root.after(0, lambda idx=i: self.lbl_progreso.config(text=f"Enviando {idx+1}/{total}...", fg="blue"))
            
            nombre = row.get('Cliente', 'Cliente')
            tel_raw = row.get('Numero de Telefono', '')
            if not tel_raw: continue

            tel_fmt = mainCode.formatear_telefono(tel_raw)

            prods_str = ""
            if tipo == "Promociones": prods_str = f"{top_global_p1}, {top_global_p2}, {top_global_p3}"
            elif tipo in ["Rescate (Te extrañamos)", "Gira Vendedor"]:
                p1, p2 = mainCode.obtener_top_personalizados(row, cols_prod)
                prods_str = f"{p1} y {p2}"
            else: prods_str = "la promo enviada"
            
            link_footer = mainCode.generar_texto_footer(params['tel_vendedor'], prods_str)

            exito = False
            msg = ""

            if tipo == "Promociones":
                exito, msg = mainCode.enviar_promocion(tel_fmt, top_global_p1, top_global_p2, top_global_p3, link_footer)
            elif tipo == "Rescate (Te extrañamos)":
                p1, _ = mainCode.obtener_top_personalizados(row, cols_prod)
                exito, msg = mainCode.enviar_rescate(tel_fmt, nombre, p1, link_footer)
            elif tipo == "Gira Vendedor":
                p1, p2 = mainCode.obtener_top_personalizados(row, cols_prod)
                exito, msg = mainCode.enviar_gira(tel_fmt, params['nombre_vendedor'], p1, p2, link_footer)
            elif tipo == "Personalizado":
                exito, msg = mainCode.enviar_personalizado(tel_fmt, params['texto'], media_id, link_footer)

            if exito: ok_count += 1
            else: 
                err_count += 1
                print(f"Error {nombre}: {msg}")
            
            time.sleep(1) 

        self.root.after(0, lambda: self.lbl_progreso.config(text=f"Finalizado: {ok_count} OK, {err_count} Errores", fg="green"))
        self.root.after(0, lambda: messagebox.showinfo("Reporte", f"Campaña terminada.\nEnviados: {ok_count}\nFallidos: {err_count}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = WoodToolsApp(root)
    root.mainloop()