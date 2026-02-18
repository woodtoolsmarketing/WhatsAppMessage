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
        
        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        self.ruta_imagen_seleccionada = None
        
        # --- 1. CABECERA ---
        frame_top = tk.Frame(root, pady=10, padx=10, bg="#e0e0e0")
        frame_top.pack(fill="x")
        
        self.cargar_logo(frame_top)

        btn_cargar = tk.Button(frame_top, text="🔄 Cargar y Validar Base de Datos", command=self.cargar_datos, bg="#4CAF50", fg="white", font=("Segoe UI", 10, "bold"))
        btn_cargar.pack(side=tk.LEFT, padx=10)
        
        # BOTÓN NUEVO: Verificar Observados
        btn_verificar = tk.Button(frame_top, text="🔍 Verificar Observados", command=self.verificar_observados, bg="#FF9800", fg="white", font=("Segoe UI", 10, "bold"))
        btn_verificar.pack(side=tk.LEFT, padx=10)
        
        self.lbl_status_db = tk.Label(frame_top, text="Estado: Esperando datos...", fg="gray", bg="#e0e0e0", font=("Segoe UI", 10))
        self.lbl_status_db.pack(side=tk.LEFT, padx=10)

        # --- 2. ÁREA DE FILTROS ---
        frame_filtros = tk.LabelFrame(root, text="Filtros de Audiencia", padx=10, pady=10, font=("Segoe UI", 10, "bold"))
        frame_filtros.pack(fill="x", padx=20, pady=5)
        
        tk.Label(frame_filtros, text="Nombre:").grid(row=0, column=0, padx=5)
        self.entry_nombre = tk.Entry(frame_filtros)
        self.entry_nombre.grid(row=0, column=1, padx=5)
        self.entry_nombre.bind("<KeyRelease>", self.aplicar_filtros) 
        
        tk.Label(frame_filtros, text="Zona:").grid(row=0, column=2, padx=5)
        self.combo_zona = ttk.Combobox(frame_filtros, state="readonly", width=10)
        self.combo_zona.grid(row=0, column=3, padx=5)
        self.combo_zona.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        tk.Label(frame_filtros, text="Su Favorito es:").grid(row=0, column=4, padx=5)
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
        
        cols = ("Cliente", "Telefono", "Zona", "Prod. Favorito", "Estado")
        self.tree = ttk.Treeview(frame_tabla, columns=cols, show="headings")
        
        self.tree.heading("Cliente", text="Cliente"); self.tree.column("Cliente", width=200)
        self.tree.heading("Telefono", text="Teléfono"); self.tree.column("Telefono", width=120)
        self.tree.heading("Zona", text="Zona"); self.tree.column("Zona", width=80)
        self.tree.heading("Prod. Favorito", text="Prod. Favorito"); self.tree.column("Prod. Favorito", width=200)
        self.tree.heading("Estado", text="Estado"); self.tree.column("Estado", width=100)
        
        # Configurar colores para estados
        self.tree.tag_configure('valido', background='white')
        self.tree.tag_configure('invalido', background='#FFCCCC', foreground='red') # ROJO

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

    # --- FUNCIONES ---

    def cargar_logo(self, parent):
        if os.path.exists("logo.png"):
            try:
                img = Image.open("logo.png").resize((150, 50)) 
                self.logo_img = ImageTk.PhotoImage(img)
                tk.Label(parent, image=self.logo_img, bg="#e0e0e0").pack(side=tk.RIGHT, padx=10)
            except: pass

    def verificar_observados(self):
        """Muestra el reporte de números inválidos"""
        reporte = mainCode.revisar_numeros_problematicos()
        vent = tk.Toplevel(self.root)
        vent.title("Números Observados")
        vent.geometry("400x400")
        txt = tk.Text(vent, wrap="word", padx=10, pady=10)
        txt.pack(fill="both", expand=True)
        txt.insert("1.0", reporte)
        txt.config(state="disabled")

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
        ruta = filedialog.askopenfilename(filetypes=[("Imágenes", "*.jpg *.jpeg *.png")])
        if ruta:
            # Normalizamos la ruta
            self.ruta_imagen_seleccionada = os.path.normpath(ruta)
            self.lbl_nombre_imagen.config(text=os.path.basename(ruta), fg="green")

    def cargar_datos(self):
        self.lbl_status_db.config(text="Validando base de datos...", fg="blue")
        threading.Thread(target=self._hilo_carga).start()

    def _hilo_carga(self):
        # Usamos la función del backend que valida
        df = mainCode.conectar_y_procesar() 
        if df.empty:
            self.root.after(0, lambda: self.lbl_status_db.config(text="Error: Base vacía", fg="red"))
            return
        
        # 1. Normalizar Zona
        if 'Zona' not in df.columns: df['Zona'] = "N/A"
        else: df['Zona'] = df['Zona'].astype(str)

        # 2. Pre-calcular favoritos
        cols_prod = mainCode.identificar_cols_productos(df)
        favs, secs = [], []
        for index, row in df.iterrows():
            p1, p2 = mainCode.obtener_top_personalizados(row, cols_prod)
            favs.append(p1)
            secs.append(p2)
        
        df['Fav_Temp'] = favs
        df['Sec_Temp'] = secs
        
        self.df_original = df
        self.df_filtrado = df.copy()

        self.combo_herramientas['values'] = ["Todos"] + cols_prod
        self.combo_herramientas.current(0)
        
        zonas = sorted(self.df_original['Zona'].unique().tolist())
        self.combo_zona['values'] = ["Todas"] + zonas
        self.combo_zona.current(0)
        
        self.root.after(0, self.actualizar_tabla)
        self.root.after(0, lambda: self.lbl_status_db.config(text=f"Base cargada: {len(df)} regs", fg="green"))

    def actualizar_tabla(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        for index, row in self.df_filtrado.iterrows():
            nombre = row.get('Cliente', '')
            tel = row.get('Numero de Telefono', '')
            zona = row.get('Zona', '')
            p1 = row.get('Fav_Temp', '-')
            
            # Verificación de validez para colorear
            es_valido = row.get('Es_Valido', False)
            estado_txt = "OK" if es_valido else "INVÁLIDO"
            tag = "valido" if es_valido else "invalido"
            
            self.tree.insert("", "end", values=(nombre, tel, zona, p1, estado_txt), tags=(tag,))
            
        self.lbl_conteo.config(text=f"Registros: {len(self.df_filtrado)}")

    def aplicar_filtros(self, event=None):
        if self.df_original.empty: return
        nom = self.entry_nombre.get().lower()
        zona = self.combo_zona.get()
        prod = self.combo_herramientas.get()
        
        df = self.df_original.copy()
        if nom: df = df[df['Cliente'].str.lower().str.contains(nom, na=False)]
        if zona != "Todas": df = df[df['Zona'] == zona]
        if prod != "Todos": df = df[df['Fav_Temp'] == prod]
            
        self.df_filtrado = df
        self.actualizar_tabla()

    def limpiar_filtros(self):
        self.entry_nombre.delete(0, tk.END)
        self.combo_zona.current(0)
        self.combo_herramientas.current(0)
        self.aplicar_filtros()

    def iniciar_envio(self):
        # Filtramos solo válidos para envío
        df_a_enviar = self.df_filtrado[self.df_filtrado['Es_Valido'] == True]
        df_invalidos = self.df_filtrado[self.df_filtrado['Es_Valido'] == False]
        
        if df_a_enviar.empty:
            msg = "No hay usuarios válidos."
            if not df_invalidos.empty: msg += f"\n(Hay {len(df_invalidos)} inválidos)."
            return messagebox.showwarning("Atención", msg)

        tipo = self.tipo_mensaje_var.get()
        vendedor_key = self.combo_vendedor.get()
        
        numeros = mainCode.DB_VENDEDORES.get(vendedor_key, [])
        tel_vendedor = numeros[0]
        if len(numeros) > 1:
            sel = simpledialog.askinteger("Selección", f"1: {numeros[0]}\n2: {numeros[1]}", minvalue=1, maxvalue=2)
            if not sel: return
            tel_vendedor = numeros[sel-1]

        params = {'tel_vendedor': tel_vendedor}
        
        if tipo == "Gira Vendedor":
            if not self.entry_dinamico_texto.get().strip(): return messagebox.showerror("Error", "Falta vendedor")
            params['nombre_vendedor'] = self.entry_dinamico_texto.get().strip()
        elif tipo == "Personalizado":
            if not self.entry_dinamico_texto.get().strip(): return messagebox.showerror("Error", "Falta texto")
            if not self.ruta_imagen_seleccionada: return messagebox.showerror("Error", "Falta imagen")
            params['texto'] = self.entry_dinamico_texto.get().strip()
            params['ruta_imagen'] = self.ruta_imagen_seleccionada

        if not messagebox.askyesno("Confirmar", f"Se enviará a {len(df_a_enviar)} contactos válidos.\n({len(df_invalidos)} inválidos omitidos)."):
            return

        threading.Thread(target=self._proceso_envio, args=(tipo, params, df_a_enviar)).start()

    def _proceso_envio(self, tipo, params, df_valido):
        self.lbl_progreso.config(text="Iniciando...", fg="orange")
        
        media_id = None
        if tipo == "Personalizado":
            self.lbl_progreso.config(text="Subiendo imagen...", fg="blue")
            if not os.path.exists(params['ruta_imagen']): return messagebox.showerror("Error", "Imagen no existe")
            media_id = mainCode.subir_imagen_whatsapp(params['ruta_imagen'])
            if not media_id: return messagebox.showerror("Error", "Fallo subida API")

        top_p1, top_p2, top_p3 = mainCode.obtener_top_3_globales(self.df_original)
        
        total = len(df_valido)
        cnt_ok = 0
        cnt_err = 0
        
        for i, (idx, row) in enumerate(df_valido.iterrows()):
            self.root.after(0, lambda x=i: self.lbl_progreso.config(text=f"Enviando {x+1}/{total}...", fg="blue"))
            
            nombre = row['Cliente']
            tel_fmt = row['Tel_Formateado'] 
            p1 = row.get('Fav_Temp', 'Prod')
            p2 = row.get('Sec_Temp', 'Prod')
            
            prods = f"{top_p1}, {top_p2}, {top_p3}" if tipo == "Promociones" else f"{p1} y {p2}" if tipo != "Personalizado" else "promo"
            footer = mainCode.generar_texto_footer(params['tel_vendedor'], prods)
            
            exito = False
            
            if tipo == "Promociones":
                exito, _ = mainCode.enviar_promocion(tel_fmt, top_p1, top_p2, top_p3, footer)
            elif tipo == "Rescate (Te extrañamos)":
                exito, _ = mainCode.enviar_rescate(tel_fmt, nombre, p1, footer)
            elif tipo == "Gira Vendedor":
                exito, _ = mainCode.enviar_gira(tel_fmt, params['nombre_vendedor'], p1, p2, footer)
            elif tipo == "Personalizado":
                exito, _ = mainCode.enviar_personalizado(tel_fmt, params['texto'], media_id, footer)
            
            if exito: cnt_ok += 1
            else: cnt_err += 1
            
            time.sleep(1)

        self.root.after(0, lambda: self.lbl_progreso.config(text="Finalizado", fg="green"))
        self.root.after(0, lambda: messagebox.showinfo("Fin", f"Enviados: {cnt_ok}\nFallidos (API): {cnt_err}"))

if __name__ == "__main__":
    root = tk.Tk()
    app = WoodToolsApp(root)
    root.mainloop()