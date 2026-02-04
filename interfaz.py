import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import pandas as pd
import threading
import mainCode 

class WoodToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WoodTools Marketing Manager")
        self.root.geometry("1200x650") # Agrandamos un poco la ventana para que entren las columnas
        
        # Variables de datos
        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        
        # --- MARCO SUPERIOR ---
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
        tk.Label(frame_filtros, text="Nombre:").grid(row=0, column=0, padx=5)
        self.entry_nombre = tk.Entry(frame_filtros)
        self.entry_nombre.grid(row=0, column=1, padx=5)
        self.entry_nombre.bind("<KeyRelease>", self.aplicar_filtros) 
        
        # Filtro Ubicación
        tk.Label(frame_filtros, text="Ubicación:").grid(row=0, column=2, padx=5)
        self.entry_ubicacion = tk.Entry(frame_filtros)
        self.entry_ubicacion.grid(row=0, column=3, padx=5)
        self.entry_ubicacion.bind("<KeyRelease>", self.aplicar_filtros)

        # Filtro Herramienta
        tk.Label(frame_filtros, text="Compró:").grid(row=0, column=4, padx=5)
        self.combo_herramientas = ttk.Combobox(frame_filtros, state="readonly")
        self.combo_herramientas.grid(row=0, column=5, padx=5)
        self.combo_herramientas.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        btn_limpiar = tk.Button(frame_filtros, text="Limpiar", command=self.limpiar_filtros)
        btn_limpiar.grid(row=0, column=6, padx=15)

        # --- TABLA DE DATOS (NUEVAS COLUMNAS) ---
        frame_tabla = tk.Frame(root)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Definimos las columnas solicitadas
        cols = ("Cliente", "N° Cliente", "DNI", "Telefono", "Ubicación", "Más Comprado", "Otros Productos")
        self.tree = ttk.Treeview(frame_tabla, columns=cols, show="headings")
        
        # Configuración de encabezados y anchos
        self.tree.heading("Cliente", text="Cliente")
        self.tree.column("Cliente", width=120)
        
        self.tree.heading("N° Cliente", text="N° Cliente")
        self.tree.column("N° Cliente", width=70)

        self.tree.heading("DNI", text="DNI")
        self.tree.column("DNI", width=80)

        self.tree.heading("Telefono", text="Teléfono")
        self.tree.column("Telefono", width=100)

        self.tree.heading("Ubicación", text="Ubicación")
        self.tree.column("Ubicación", width=100)

        self.tree.heading("Más Comprado", text="⭐ Más Comprado")
        self.tree.column("Más Comprado", width=120)

        self.tree.heading("Otros Productos", text="📦 Otros Productos")
        self.tree.column("Otros Productos", width=250)
            
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # --- PANEL DE ACCIÓN ---
        frame_accion = tk.Frame(root, pady=20, bg="#f0f0f0")
        frame_accion.pack(fill="x", side="bottom")
        
        btn_enviar = tk.Button(frame_accion, text="🚀 CONFIGURAR DESCUENTO Y ENVIAR", command=self.confirmar_envio, bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
        btn_enviar.pack(padx=20, pady=10)

    def cargar_datos(self):
        self.lbl_status.config(text="Cargando desde Google Sheets...", fg="blue")
        self.root.update_idletasks()
        threading.Thread(target=self._cargar_datos_thread).start()

    def _cargar_datos_thread(self):
        try:
            df = mainCode.conectar_sheets()
            if df.empty:
                self.actualizar_status("Error: No se obtuvieron datos.", "red")
                return

            self.df_original = df
            if 'Ubicación' not in self.df_original.columns:
                self.df_original['Ubicación'] = "No especificado"

            self.df_filtrado = df.copy()
            
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
        
        # Columnas que NO son productos (para excluirlas del cálculo de compras)
        cols_no_prod = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'DNI', 'Ubicación']

        for index, row in self.df_filtrado.iterrows():
            # --- Lógica para encontrar qué compró cada uno ---
            try:
                # Extraemos solo las columnas de productos para esta fila
                cols_productos = [c for c in row.index if c not in cols_no_prod]
                datos_productos = row[cols_productos]
                
                # Convertimos a números para poder ordenar
                datos_productos = pd.to_numeric(datos_productos, errors='coerce').fillna(0)
                
                # Filtramos solo lo que compró (mayor a 0) y ordenamos de mayor a menor
                compras = datos_productos[datos_productos > 0].sort_values(ascending=False)
                
                if not compras.empty:
                    mas_comprado = compras.index[0] # El primero es el mayor
                    otros = compras.index[1:].tolist() # El resto de la lista
                    otros_str = ", ".join(otros) if others else "-"
                else:
                    mas_comprado = "-"
                    otros_str = "-"
            except Exception:
                mas_comprado = "Error Calc"
                otros_str = "-"

            # Insertamos la fila en la tabla visual
            self.tree.insert("", "end", values=(
                row.get('Cliente', ''), 
                row.get('Número de cliente', ''), 
                row.get('DNI', ''), 
                row.get('Numero de Telefono', ''), 
                row.get('Ubicación', ''), 
                mas_comprado, 
                otros_str
            ))

    def aplicar_filtros(self, event=None):
        if self.df_original.empty: return
        nombre = self.entry_nombre.get().lower()
        ubicacion = self.entry_ubicacion.get().lower()
        herramienta = self.combo_herramientas.get()

        df = self.df_original.copy()
        if nombre:
            df = df[df['Cliente'].str.lower().str.contains(nombre, na=False)]
        if ubicacion:
            df = df[df['Ubicación'].str.lower().str.contains(ubicacion, na=False)]
        if herramienta != "Todos" and herramienta in df.columns:
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

        descuento = simpledialog.askinteger("Configurar Oferta", "Ingrese el porcentaje de descuento a aplicar (%):", minvalue=1, maxvalue=100)
        
        if descuento is None: return 

        confirm = messagebox.askyesno("Confirmar Envío", f"Se enviará mensaje a {len(self.df_filtrado)} clientes con un {descuento}% de descuento.\n¿Está seguro?")
        if confirm:
            self.enviar_mensajes(descuento)

    def enviar_mensajes(self, descuento):
        self.lbl_status.config(text="Calculando Top Global...", fg="orange")
        self.root.update()
        
        top1, top2, top3 = mainCode.obtener_top_3_globales(self.df_original)
        
        contador_exito = 0
        total = len(self.df_filtrado)

        for i, fila in self.df_filtrado.iterrows():
            cliente = fila['Cliente']
            telefono_raw = fila['Numero de Telefono']
            
            if not telefono_raw: continue

            telefono = mainCode.formatear_telefono(telefono_raw)
            self.lbl_status.config(text=f"Enviando a {cliente} ({i+1}/{total})...")
            self.root.update()
            
            exito, msg = mainCode.enviar_mensaje_cloud_api(telefono, top1, descuento, top2, top3)
            
            if exito: contador_exito += 1
            self.root.after(1000) 

        messagebox.showinfo("Proceso Terminado", f"Se enviaron {contador_exito} de {total} mensajes correctamente.")
        self.lbl_status.config(text="Envío finalizado.", fg="green")

if __name__ == "__main__":
    root = tk.Tk()
    app = WoodToolsApp(root)
    root.mainloop()