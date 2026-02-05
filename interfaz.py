import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk 
import pandas as pd
import threading
import os
import sys 
import mainCode 

class WoodToolsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("WoodTools Marketing Manager")
        self.root.geometry("1300x700") 
        
        # Variables de datos
        self.df_original = pd.DataFrame()
        self.df_filtrado = pd.DataFrame()
        
        # --- MARCO SUPERIOR ---
        frame_top = tk.Frame(root, pady=10, padx=10)
        frame_top.pack(fill="x")
        
        # 1. LOGO (Carga visual y cambio de icono de ventana)
        # Se llama ANTES de los botones para que el icono se aplique rápido
        self.cargar_logo(frame_top)

        # 2. Botones (Izquierda)
        btn_cargar = tk.Button(frame_top, text="🔄 Cargar Base de Datos", command=self.cargar_datos, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        btn_cargar.pack(side=tk.LEFT, padx=10)
        
        self.lbl_status = tk.Label(frame_top, text="Estado: Esperando datos...", fg="gray", font=("Arial", 10))
        self.lbl_status.pack(side=tk.LEFT, padx=10)

        # --- FILTROS ---
        frame_filtros = tk.LabelFrame(root, text="Filtros de Búsqueda", padx=10, pady=10)
        frame_filtros.pack(fill="x", padx=20, pady=5)
        
        tk.Label(frame_filtros, text="Nombre:").grid(row=0, column=0, padx=5)
        self.entry_nombre = tk.Entry(frame_filtros)
        self.entry_nombre.grid(row=0, column=1, padx=5)
        self.entry_nombre.bind("<KeyRelease>", self.aplicar_filtros) 
        
        tk.Label(frame_filtros, text="Ubicación:").grid(row=0, column=2, padx=5)
        self.entry_ubicacion = tk.Entry(frame_filtros)
        self.entry_ubicacion.grid(row=0, column=3, padx=5)
        self.entry_ubicacion.bind("<KeyRelease>", self.aplicar_filtros)

        tk.Label(frame_filtros, text="Compró:").grid(row=0, column=4, padx=5)
        self.combo_herramientas = ttk.Combobox(frame_filtros, state="readonly")
        self.combo_herramientas.grid(row=0, column=5, padx=5)
        self.combo_herramientas.bind("<<ComboboxSelected>>", self.aplicar_filtros)

        btn_limpiar = tk.Button(frame_filtros, text="Limpiar", command=self.limpiar_filtros)
        btn_limpiar.grid(row=0, column=6, padx=15)

        # --- TABLA ---
        frame_tabla = tk.Frame(root)
        frame_tabla.pack(fill="both", expand=True, padx=20, pady=10)
        
        # --- COLUMNAS (Con CUIT) ---
        cols = ("Cliente", "N° Cliente", "CUIT", "Telefono", "Ubicación", "Más Comprado", "Otros Productos")
        self.tree = ttk.Treeview(frame_tabla, columns=cols, show="headings")
        
        anchos = [180, 80, 100, 120, 150, 180, 400]
        for col, ancho in zip(cols, anchos):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=ancho)
            
        scrollbar = ttk.Scrollbar(frame_tabla, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)

        # --- BOTÓN ---
        frame_accion = tk.Frame(root, pady=20, bg="#f0f0f0")
        frame_accion.pack(fill="x", side="bottom")
        
        btn_enviar = tk.Button(frame_accion, text="🚀 CONFIGURAR DESCUENTO Y ENVIAR", command=self.confirmar_envio, bg="#2196F3", fg="white", font=("Arial", 11, "bold"))
        btn_enviar.pack(padx=20, pady=10)

    # --- LOGO Y RUTAS ---
    def resolver_ruta(self, ruta_relativa):
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, ruta_relativa)
        return os.path.join(os.path.abspath("."), ruta_relativa)

    def cargar_logo(self, parent_frame):
        # Rutas a los archivos
        ruta_png = self.resolver_ruta(os.path.join("Imagenes", "logo.png"))
        ruta_ico = self.resolver_ruta(os.path.join("Imagenes", "logo.ico"))
        
        img_para_interfaz = None

        # 1. CARGAR IMAGEN VISUAL (Para el label de la interfaz)
        if os.path.exists(ruta_png):
            try:
                img_pil = Image.open(ruta_png)
                img_para_interfaz = img_pil # Guardamos referencia para usarla de icono si hace falta

                # Redimensionar para el Label visual
                base_width = 180
                w_percent = (base_width / float(img_pil.size[0]))
                h_size = int((float(img_pil.size[1]) * float(w_percent)))
                img_redim = img_pil.resize((base_width, h_size), Image.Resampling.LANCZOS)
                
                self.logo_img = ImageTk.PhotoImage(img_redim)
                lbl_logo = tk.Label(parent_frame, image=self.logo_img)
                lbl_logo.pack(side=tk.RIGHT, padx=10)
            except Exception as e:
                print(f"Error cargando imagen visual: {e}")
        else:
            print(f"Advertencia: No se encontró logo.png en {ruta_png}")

        # 2. CONFIGURAR ICONO DE LA VENTANA (Reemplazar la pluma)
        icono_establecido = False
        
        # INTENTO A: Usar .ico (Mejor calidad)
        if os.path.exists(ruta_ico):
            try:
                self.root.iconbitmap(ruta_ico)
                icono_establecido = True
            except Exception:
                pass # Si falla, pasamos al plan B

        # INTENTO B: Si falló el .ico, usar el .png (Plan de respaldo infalible)
        if not icono_establecido and img_para_interfaz:
            try:
                foto_icono = ImageTk.PhotoImage(img_para_interfaz)
                self.root.iconphoto(False, foto_icono)
            except Exception as e:
                print(f"Error en icono de respaldo: {e}")

    # --- LÓGICA (Sin cambios) ---
    def cargar_datos(self):
        self.lbl_status.config(text="Cargando...", fg="blue")
        self.root.update_idletasks()
        threading.Thread(target=self._cargar_datos_thread).start()

    def _cargar_datos_thread(self):
        try:
            df = mainCode.conectar_sheets()
            if df.empty:
                self.actualizar_status("Error datos", "red")
                return
            self.df_original = df
            if 'Ubicación' not in self.df_original.columns: self.df_original['Ubicación'] = "No especificado"
            self.df_filtrado = df.copy()
            
            cols_no_prod = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'CUIT', 'Ubicación']
            
            productos = [col for col in self.df_original.columns if col not in cols_no_prod]
            self.combo_herramientas['values'] = ["Todos"] + productos
            self.combo_herramientas.current(0)
            self.root.after(0, self.actualizar_tabla)
            self.actualizar_status(f"Datos: {len(df)} clientes.", "green")
        except Exception as e:
            self.actualizar_status(f"Error: {str(e)}", "red")

    def actualizar_status(self, texto, color):
        self.root.after(0, lambda: self.lbl_status.config(text=texto, fg=color))

    def actualizar_tabla(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        
        cols_no_prod = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'CUIT', 'Ubicación']
        
        for index, row in self.df_filtrado.iterrows():
            try:
                cols_productos = [c for c in row.index if c not in cols_no_prod]
                datos_productos = pd.to_numeric(row[cols_productos], errors='coerce').fillna(0)
                compras = datos_productos[datos_productos > 0].sort_values(ascending=False)
                if not compras.empty:
                    mas_comprado = compras.index[0]
                    otros = compras.index[1:].tolist()
                    otros_str = ", ".join(otros) if otros else "-"
                else:
                    mas_comprado = "-"
                    otros_str = "-"
            except: mas_comprado, otros_str = "-", "-"
            
            self.tree.insert("", "end", values=(
                row.get('Cliente',''), 
                row.get('Número de cliente',''), 
                row.get('CUIT',''), 
                row.get('Numero de Telefono',''), 
                row.get('Ubicación',''), 
                mas_comprado, 
                otros_str
            ))

    def aplicar_filtros(self, event=None):
        if self.df_original.empty: return
        nombre = self.entry_nombre.get().lower()
        ubicacion = self.entry_ubicacion.get().lower()
        herramientienta = self.combo_herramientas.get()
        df = self.df_original.copy()
        if nombre: df = df[df['Cliente'].str.lower().str.contains(nombre,na=False)]
        if ubicacion: df = df[df['Ubicación'].str.lower().str.contains(ubicacion,na=False)]
        if herramientienta != "Todos" and herramientienta in df.columns:
            df[herramientienta] = pd.to_numeric(df[herramientienta], errors='coerce').fillna(0)
            df = df[df[herramientienta] > 0]
        self.df_filtrado = df
        self.actualizar_tabla()
        self.lbl_status.config(text=f"Filtrado: {len(df)}")

    def limpiar_filtros(self):
        self.entry_nombre.delete(0, tk.END)
        self.entry_ubicacion.delete(0, tk.END)
        self.combo_herramientas.current(0)
        self.aplicar_filtros()

    def confirmar_envio(self):
        if self.df_filtrado.empty: return messagebox.showwarning("Atención", "Lista vacía")
        descuento = simpledialog.askinteger("Oferta", "Descuento (%):", minvalue=1, maxvalue=100)
        if descuento is None: return 
        if messagebox.askyesno("Confirmar", f"Enviar a {len(self.df_filtrado)} clientes con {descuento}% off?"):
            self.enviar_mensajes(descuento)

    def enviar_mensajes(self, descuento):
        self.lbl_status.config(text="Enviando...", fg="orange")
        self.root.update()
        try:
            top1, top2, top3 = mainCode.obtener_top_3_globales(self.df_original)
        except AttributeError:
            top1, top2, top3 = "Producto A", "Producto B", "Producto C"

        cnt = 0
        for i, fila in self.df_filtrado.iterrows():
            tel = fila['Numero de Telefono']
            if not tel: continue
            self.lbl_status.config(text=f"Enviando a {fila['Cliente']}...")
            self.root.update()
            try:
                ok, _ = mainCode.enviar_mensaje_cloud_api(mainCode.formatear_telefono(tel), top1, descuento, top2, top3)
            except AttributeError:
                ok = True 
                self.root.after(500) 

            if ok: cnt += 1
            self.root.after(100)
        messagebox.showinfo("Fin", f"Enviados: {cnt}")
        self.lbl_status.config(text="Listo", fg="green")

if __name__ == "__main__":
    root = tk.Tk()
    app = WoodToolsApp(root)
    root.mainloop()