import sqlite3
import pandas as pd
import os

# 1. Rutas de los archivos
# Asegurate de poner el nombre correcto de tu archivo exportado de Neon
ruta_exportacion_neon = "datos_neon.csv" 
ruta_db_local = "historial_campanas.db"

def migrar_datos():
    if not os.path.exists(ruta_exportacion_neon):
        print(f"Error: No se encontró el archivo '{ruta_exportacion_neon}'.")
        return
        
    print("Leyendo archivo de exportación...")
    # Si tu exportación es un Excel, cambiá read_csv por read_excel
    df_neon = pd.read_csv(ruta_exportacion_neon) 
    
    if not os.path.exists(ruta_db_local):
        print(f"Error: No se encontró la base de datos local '{ruta_db_local}'. Ejecutá tu aplicación al menos una vez para que se cree.")
        return

    print("Conectando a la base de datos local...")
    conn = sqlite3.connect(ruta_db_local)
    cursor = conn.cursor()
    
    registros_insertados = 0
    
    for index, row in df_neon.iterrows():
        # 2. Mapeo de columnas
        # Reemplazá el texto entre comillas con el nombre exacto de la columna en tu CSV de Neon.
        # El segundo valor es un dato por defecto por si la celda está vacía.
        tanda_id = str(row.get('tanda_id', f'TANDA_MIGRADA_{index}'))
        fecha_hora = str(row.get('fecha_hora', '2025-01-01 12:00:00'))
        cliente = str(row.get('cliente', 'Cliente Desconocido'))
        telefono = str(row.get('telefono', '0'))
        vendedor_asignado = str(row.get('vendedor_asignado', '0'))
        tipo_campana = str(row.get('tipo_campana', 'Migración Neon'))
        herramienta = str(row.get('herramienta', '-'))
        estado_envio = str(row.get('estado_envio', 'ENVIADO CORRECTAMENTE'))
        estado_tanda = str(row.get('estado_tanda', 'ENVIADO CON EXITO'))
        
        # Manejo de números para evitar errores
        try:
            total_base = int(row.get('total_base', 1))
        except ValueError:
            total_base = 1

        cursor.execute('''
            INSERT INTO historial (tanda_id, fecha_hora, cliente, telefono, vendedor_asignado, tipo_campana, herramienta, estado_envio, estado_tanda, total_base)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tanda_id, fecha_hora, cliente, telefono, vendedor_asignado, tipo_campana, herramienta, estado_envio, estado_tanda, total_base))
        
        registros_insertados += 1

    conn.commit()
    conn.close()
    print(f"Migración completada exitosamente. Se integraron {registros_insertados} registros a tu aplicación.")

if __name__ == "__main__":
    migrar_datos()