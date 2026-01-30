import pandas as pd
import gspread
import requests
import time
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
CLOUD_API_TOKEN = "EAANcqeZCuZAM4BQrv8ZBjulKeQ95wVhlmlugMrm5Gkvb5jCZCThZAx0EblclgOuZAGX9ndyKqK8ZAkZAFUauzw5IywZCk8knumuW7yBDXvDrdCDWo12yCAyBjw3yXeyase7gqGR4j4UnZBeZAPlGGxzzGYMF8KKrdE7WZA9ZCXF4PlYpNPxxqRt58dlZApGi1ZCHmqx3vZBu1mZBEpyMLtJrpxfTMxH9YHBbaiSGR4ozCLrFRD3xGrOGmJZC1fshQdQl75llh25VNOU4F1ZBnKVZCRJ1f8spLAdw"
PHONE_NUMBER_ID = "1007885345737939"
VERSION = "v17.0"
URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"

# Archivos
JSON_CREDS = 'service_account.json' 
NOMBRE_HOJA = "Base de datos wt"

def conectar_sheets():
    """Conecta a Google Sheets y devuelve un DataFrame limpio."""
    try:
        # Autenticación (usando gspread moderno si es posible, o oauth2client como tenías)
        gc = gspread.service_account(filename=JSON_CREDS)
        sh = gc.open(NOMBRE_HOJA)
        
        # Leer todos los valores brutos
        datos_brutos = sh.sheet1.get_all_values()
        
        # Asumimos que la fila 2 (índice 1) tiene los encabezados reales (Cliente, Sierras, etc.)
        # Y los datos empiezan en la fila 3
        headers = datos_brutos[1]
        data = datos_brutos[2:]
        
        df = pd.DataFrame(data, columns=headers)
        return df
    except Exception as e:
        print(f"Error crítico conectando a Sheets: {e}")
        return pd.DataFrame()

def procesar_tendencias(df):
    """
    Toma todos los datos y genera una tabla dinámica para identificar tendencias.
    """
    # 1. Definir qué columnas son información del cliente y cuáles son productos
    # Ajusta esta lista si tienes más columnas de datos personales
    cols_cliente = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'DNI']
    
    # Detectamos dinámicamente las columnas de productos (todo lo que NO está en cols_cliente)
    cols_productos = [col for col in df.columns if col not in cols_cliente and col != '']
    
    print(f"Detectados productos: {cols_productos}")

    # 2. Limpieza de datos: Convertir columnas de productos a números
    for col in cols_productos:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 3. Generar Tabla Dinámica (Melt)
    # Transformamos de: Cliente | Sierras | Mechas
    # A formato:        Cliente | Producto | Cantidad
    df_long = df.melt(
        id_vars=['Cliente', 'Numero de Telefono'], 
        value_vars=cols_productos, 
        var_name='Producto', 
        value_name='Cantidad'
    )

    # 4. Usar Query para limpiar ceros (si no compró, no es tendencia)
    df_activos = df_long.query("Cantidad > 0")

    # 5. Encontrar la tendencia máxima por cliente
    # Ordenamos por Cliente y Cantidad descendente
    df_ordenado = df_activos.sort_values(['Cliente', 'Cantidad'], ascending=[True, False])
    
    # Tomamos el primer registro de cada cliente (que será su compra mayor)
    tendencias = df_ordenado.groupby('Cliente').first().reset_index()
    
    return tendencias

def formatear_telefono(numero):
    num_str = str(numero).strip()
    # Lógica simple para Argentina, ajusta según tu país
    if not num_str.startswith("54"):
        return f"549{num_str}"
    return num_str

def enviar_mensaje_cloud_api(telefono, nombre, producto_tendencia):
    headers = {
        "Authorization": f"Bearer {CLOUD_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": "oferta_personalizada",
            "language": {"code": "es"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(nombre)},
                    {"type": "text", "text": str(producto_tendencia)}
                ]
            }]
        }
    }
    
    try:
        response = requests.post(URL, headers=headers, json=data)
        if response.status_code == 200:
            return True, "Mensaje enviado exitosamente"
        else:
            return False, f"Error API: {response.text}"
    except Exception as e:
        return False, str(e)

# --- EJECUCIÓN PRINCIPAL ---
if __name__ == "__main__":
    print("--- Iniciando Análisis de Tendencias ---")
    
    # 1. Cargar Datos
    df_completo = conectar_sheets()
    
    if not df_completo.empty:
        # 2. Procesar Datos con Lógica de Tabla Dinámica
        tabla_tendencias = procesar_tendencias(df_completo)
        
        print("\n--- Tendencias Detectadas ---")
        print(tabla_tendencias[['Cliente', 'Producto', 'Cantidad']])
        print("-----------------------------\n")
        
        # 3. Enviar Mensajes basados en la tendencia
        for i, fila in tabla_tendencias.iterrows():
            cliente = fila['Cliente']
            producto = fila['Producto']
            cantidad = fila['Cantidad']
            telefono_raw = fila['Numero de Telefono']
            
            if not telefono_raw:
                print(f"Saltando a {cliente}: Sin teléfono.")
                continue
                
            telefono = formatear_telefono(telefono_raw)
            
            print(f"Preparando envío a {cliente} (Top compra: {producto} con {cantidad} unidades)...")
            
            # Descomenta para activar el envío real
            # exito, msg = enviar_mensaje_cloud_api(telefono, cliente, producto)
            # print(f"Estado: {msg}")
            
            time.sleep(1) # Respetar límites de velocidad de la API
            
    else:
        print("No se pudieron obtener datos del Sheet.")