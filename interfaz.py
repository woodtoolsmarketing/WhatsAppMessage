import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
import threading
import mainCode # Importamos tu archivo de lógica

class WoodToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WoodTools Marketing Manager")
        self.root.geometry("1000x600")
        
        # Variables de datos
        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        
        # --- MARCO SUPERIOR: CARGA DE DATOS ---
        frame_top = tk.Frame(root, pady=10)
        frame_top.pack(fill="x")
        
        btn_cargar = tk.Button(frame_top, text="🔄 Cargar Base de Datos", command=self.cargar_datos, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        btn_cargar.pack(side=tk.LEFT, padx=20)
        
        self.lbl_status = tk.Label(frame_top, text="Estado: Esperando datos...", fg="gray")
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        # --- MARCO DE FILTROS ---
        frame_filtros = tk.LabelFrame(root, text="Filtros de Búsqueda", padx=10, pady=10)
        frame_filtros.pack(fill="x", padx=20, pady=5)
        
        # Filtro Nombre
        tk.Label(frame_filtros, text="Nombre Cliente:").grid(row=0, column=0, padx=5)
        self.entry_nombre = tk.Entry(frame_filtros)
        self.entry_nombre.grid(row=0, column=1, padx=5)
        self.entry_nombre.bind("<KeyRelease>", self.aplicar_filtros) # Filtrar al escribir
        
        # Filtro Ubicación
        tk.Label(frame_filtros, text="Ubicación:").grid(row=0, column=2, padx=5)
        self.entry_ubicacion = tk.Entry(frame_filtros)
        self.entry_ubicacion.grid(row=0, column=3, padx=5)
        self.entry_ubicacion.bind("<KeyRelease>", self.aplicar_filtros)

        # Filtro Herramienta (Producto) - Muestra clientes que compraron X producto
        tk.Label(frame_filtros, text="Compró Herramienta:").grid(row=0, column=4, padx=5)
        self.combo_herramientas = ttk.Combobox(frame_filtros, state="readonly")
        self.combo_herramientas.grid(row=0, column=5, padx=5)
        self.combo_herramientas.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        btn_limpiar = tk.Button(frame_filtros, text="Limpiar Filtros", command=self.limpiar_filtros)
        btn_limpiar.grid(row=0, column=6, padx=15)

        # --- TABLA DE DATOS (Treeview) ---
        frame_tabla = tk.Frame(root)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Definir columnas
        cols = ("Cliente", "Telefono", "Ubicación", "Total Compras")
        self.tree = ttk.Treeview(frame_tabla, columns=cols, show="headings")
        
        # Configurar encabezados
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150)
            
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # --- PANEL DE ACCIÓN (ENVÍO) ---
        frame_accion = tk.Frame(root, pady=20, bg="#f0f0f0")
        frame_accion.pack(fill="x", side="bottom")
        
        tk.Label(frame_accion, text="Descuento a ofrecer (%):", bg="#f0f0f0").pack(side=tk.LEFT, padx=20)
        self.entry_descuento = tk.Entry(frame_accion, width=5)
        self.entry_descuento.pack(side=tk.LEFT)
        
        btn_enviar = tk.Button(frame_accion, text="🚀 ENVIAR MENSAJES A LISTA FILTRADA", command=self.confirmar_envio, bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
        btn_enviar.pack(side=tk.RIGHT, padx=20)

    def cargar_datos(self):
        self.lbl_status.config(text="Cargando desde Google Sheets...", fg="blue")
        self.root.update_idletasks()
        
        # Ejecutar en segundo plano para no congelar la ventana
        threading.Thread(target=self._cargar_datos_thread).start()

    def _cargar_datos_thread(self):
        try:
            df = mainCode.conectar_sheets()
            if df.empty:
                self.actualizar_status("Error: No se obtuvieron datos.", "red")
                return

            self.df_original = df
            
            # Asegurar que existe la columna Ubicación, si no, crearla vacía
            if 'Ubicación' not in self.df_original.columns:
                self.df_original['Ubicación'] = "No especificado"

            self.df_filtrado = df.copy()
            
            # Cargar herramientas en el combobox dinámicamente
            cols_cliente = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'DNI', 'Ubicación']
            productos = [col for col in self.df_original.columns if col not in cols_cliente]
            self.combo_herramientas['values'] = ["Todos"] + productos
            self.combo_herramientas.current(0)

            self.root.after(0, self.actualizar_tabla)
            self.actualizar_status(f"Datos cargados: {len(df)} clientes.", "green")
        except Exception as e:
            self.actualizar_status(f"Error crítico: {str(e)}", "red")

    def actualizar_status(self, texto, color):
        self.root.after(0, lambda: self.lbl_status.config(text=texto, fg=color))

    def actualizar_tabla(self):
        # Limpiar tabla actual
        for i in self.tree.get_children():
            self.tree.delete(i)
            
        # Insertar datos filtrados
        for index, row in self.df_filtrado.iterrows():
            # Calcular un total de compras simple para mostrar algo interesante
            # (Opcional)
            self.tree.insert("", "end", values=(row['Cliente'], row['Numero de Telefono'], row['Ubicación'], "Ver detalle"))

    def aplicar_filtros(self, event=None):
        if self.df_original.empty:
            return

        nombre = self.entry_nombre.get().lower()
        ubicacion = self.entry_ubicacion.get().lower()
        herramienta = self.combo_herramientas.get()

        df = self.df_original.copy()

        # Filtro Nombre
        if nombre:
            df = df[df['Cliente'].str.lower().str.contains(nombre, na=False)]
        
        # Filtro Ubicación
        if ubicacion:
            df = df[df['Ubicación'].str.lower().str.contains(ubicacion, na=False)]

        # Filtro Herramienta (Si seleccionó una específica, filtra clientes que compraron > 0)
        if herramienta != "Todos" and herramienta in df.columns:
            # Convertir a numérico para filtrar
            df[herramienta] = pd.to_numeric(df[herramienta], errors='coerce').fillna(0)
            df = df[df[herramienta] > 0]

        self.df_filtrado = df
        self.actualizar_tabla()
        self.lbl_status.config(text=f"Filtrado: {len(df)} clientes encontrados.")

    def limpiar_filtros(self):
        self.entry_nombre.delete(0, tk.END)
        self.entry_ubicacion.delete(0, tk.END)
        self.combo_herramientas.current(0)
        self.aplicar_filtros()

    def confirmar_envio(self):
        if self.df_filtrado.empty:
            messagebox.showwarning("Atención", "No hay clientes en la lista filtrada.")
            return

        descuento = self.entry_descuento.get()
        if not descuento.isdigit():
            messagebox.showerror("Error", "Ingrese un porcentaje de descuento válido (solo números).")
            return

        confirm = messagebox.askyesno("Confirmar Envío", f"Se enviará mensaje a {len(self.df_filtrado)} clientes.\n¿Está seguro?")
        if confirm:
            self.enviar_mensajes(descuento)

    def enviar_mensajes(self, descuento):
        self.lbl_status.config(text="Calculando Top Global...", fg="orange")
        self.root.update()
        
        # Calcular Top 3 (usando la base TOTAL, no la filtrada, para mantener la lógica global)
        top1, top2, top3 = mainCode.obtener_top_3_globales(self.df_original)
        
        contador_exito = 0
        total = len(self.df_filtrado)

        # Barra de progreso simple en consola o status
        for i, fila in self.df_filtrado.iterrows():
            cliente = fila['Cliente']
            telefono_raw = fila['Numero de Telefono']
            
            if not telefono_raw:
                continue

            telefono = mainCode.formatear_telefono(telefono_raw)
            self.lbl_status.config(text=f"Enviando a {cliente} ({i+1}/{total})...")
            self.root.update()
            
            exito, msg = mainCode.enviar_mensaje_cloud_api(telefono, top1, descuento, top2, top3)
            
            if exito:
                contador_exito += 1
            
            # Pausa pequeña para no saturar
            self.root.after(1000) 

        messagebox.showinfo("Proceso Terminado", f"Se enviaron {contador_exito} de {total} mensajes correctamente.")
        self.lbl_status.config(text="Envío finalizado.", fg="green")

if __name__ == "__main__":
    root = tk.Tk()
    app = WoodToolsApp(root)
    root.mainloop()