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
        gc = gspread.service_account(filename=JSON_CREDS)
        sh = gc.open(NOMBRE_HOJA)
        
        datos_brutos = sh.sheet1.get_all_values()
        headers = datos_brutos[1]
        data = datos_brutos[2:]
        
        df = pd.DataFrame(data, columns=headers)
        return df
    except Exception as e:
        print(f"Error crítico conectando a Sheets: {e}")
        return pd.DataFrame()

def solicitar_cliente(df):
    """
    Pide al usuario un número de cliente, verifica si existe en el DataFrame.
    Si no existe, lanza un error que es capturado por el except.
    """
    while True:
        entrada = input("Ingrese el Número de Cliente al que desea enviar el mensaje: ")
        try:
            # Limpiamos la entrada de espacios
            cliente_id = entrada.strip()
            
            # Verificamos si existe en la columna 'Número de cliente'
            # Convertimos la columna a string para comparar texto con texto
            if cliente_id not in df['Número de cliente'].astype(str).values:
                # Esto fuerza a ir al bloque 'except'
                raise ValueError("Cliente no encontrado")
            
            print(f"Cliente {cliente_id} encontrado. Procediendo...")
            return cliente_id
            
        except ValueError:
            # Aquí entra si no está en la base de datos
            print("El número no está registrado, intente nuevamente")

def solicitar_descuento():
    """Solicita el descuento con validación de números y caracteres especiales."""
    while True:
        entrada = input("Ingrese el porcentaje de descuento a ofrecer (solo números, ej: 15): ")
        
        if '+' in entrada:
            print("Error: No se permiten caracteres especiales como '+'. Ingrese solo el número.")
            continue
            
        try:
            entrada_limpia = entrada.replace('%', '').strip()
            descuento = float(entrada_limpia)
            
            if descuento < 0:
                print("Error: El descuento no puede ser negativo.")
                continue

            if descuento.is_integer():
                return int(descuento)
            return descuento
            
        except ValueError:
            print("Error: Solo se permiten números. No ingrese letras ni caracteres especiales.")

def obtener_top_3_globales(df):
    """Calcula los 3 productos más vendidos globalmente."""
    cols_cliente = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'DNI']
    cols_productos = [col for col in df.columns if col not in cols_cliente and col != '']
    
    # Trabajamos sobre una copia para no afectar el df original
    df_calc = df.copy()
    for col in cols_productos:
        df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)

    ventas_totales = df_calc[cols_productos].sum().sort_values(ascending=False)
    top_productos = ventas_totales.index.tolist()
    
    p1 = top_productos[0] if len(top_productos) > 0 else "Producto A"
    p2 = top_productos[1] if len(top_productos) > 1 else "Producto B"
    p3 = top_productos[2] if len(top_productos) > 2 else "Producto C"
    
    return p1, p2, p3

def formatear_telefono(numero):
    num_str = str(numero).strip()
    if not num_str.startswith("54"):
        return f"549{num_str}"
    return num_str

def enviar_mensaje_cloud_api(telefono, prod1, descuento, prod2, prod3):
    headers = {
        "Authorization": f"Bearer {CLOUD_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": "oferta_top_3", 
            "language": {"code": "es"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": str(prod1)},
                    {"type": "text", "text": str(descuento)},
                    {"type": "text", "text": str(prod2)},
                    {"type": "text", "text": str(prod3)}
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
    print("--- Iniciando Sistema de Ofertas WoodTools ---")
    
    # 1. Cargar Datos PRIMERO (necesario para validar cliente)
    print("-> Conectando con Google Sheets...")
    df_completo = conectar_sheets()
    
    if not df_completo.empty:
        # 2. Solicitar Cliente Específico (Filtro de seguridad)
        cliente_id_elegido = solicitar_cliente(df_completo)
        
        # 3. Solicitar Descuento
        porcentaje_descuento = solicitar_descuento()
        print(f"-> Descuento configurado: {porcentaje_descuento}%")
        
        # 4. Calcular Top 3 Global (Usando toda la base, no solo el cliente elegido)
        top1, top2, top3 = obtener_top_3_globales(df_completo)
        print(f"\n--- Top 3 Global Detectado ---")
        print(f"1. {top1} | 2. {top2} | 3. {top3}")
        print("------------------------------\n")
        
        # 5. Filtrar DataFrame para enviar SOLO al cliente elegido
        # Convertimos a string para asegurar coincidencia
        df_filtrado = df_completo[df_completo['Número de cliente'].astype(str) == cliente_id_elegido]
        
        # 6. Enviar Mensaje
        for i, fila in df_filtrado.iterrows():
            cliente = fila['Cliente']
            telefono_raw = fila['Numero de Telefono']
            
            if not telefono_raw:
                print(f"Error: El cliente {cliente} no tiene teléfono registrado.")
                continue
                
            telefono = formatear_telefono(telefono_raw)
            print(f"Enviando oferta a {cliente} ({telefono})...")
            
            exito, msg = enviar_mensaje_cloud_api(telefono, top1, porcentaje_descuento, top2, top3)
            
            if exito:
                print("   [OK] Enviado.")
            else:
                print(f"   [ERROR] {msg}")
            
        print("\n--- Proceso finalizado ---")
            
    else:
        print("No se pudieron obtener datos del Sheet. Revisa tu archivo 'service_account.json'.")