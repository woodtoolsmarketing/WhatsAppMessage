import pandas as pd
import gspread
import requests
import time
# Asegúrate de tener el archivo service_account.json con las CREDENCIALES (no con datos de clientes)
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
# Token de acceso temporal o permanente (verificar caducidad si es temporal)
CLOUD_API_TOKEN = "EAANcqeZCuZAM4BQrv8ZBjulKeQ95wVhlmlugMrm5Gkvb5jCZCThZAx0EblclgOuZAGX9ndyKqK8ZAkZAFUauzw5IywZCk8knumuW7yBDXvDrdCDWo12yCAyBjw3yXeyase7gqGR4j4UnZBeZAPlGGxzzGYMF8KKrdE7WZA9ZCXF4PlYpNPxxqRt58dlZApGi1ZCHmqx3vZBu1mZBEpyMLtJrpxfTMxH9YHBbaiSGR4ozCLrFRD3xGrOGmJZC1fshQdQl75llh25VNOU4F1ZBnKVZCRJ1f8spLAdw"
PHONE_NUMBER_ID = "1007885345737939"
VERSION = "v17.0"
URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"

# Archivos
# IMPORTANTE: Este archivo debe contener las credenciales de Google Cloud (Project ID, Private Key...), NO la lista de clientes.
JSON_CREDS = 'service_account.json' 
NOMBRE_HOJA = "Base de datos wt"

def solicitar_descuento():
    """
    Solicita al usuario el porcentaje de descuento por consola.
    Valida que la entrada sea estrictamente numérica.
    """
    while True:
        entrada = input("Ingrese el porcentaje de descuento a ofrecer (solo números, ej: 15): ")
        try:
            # Reemplazamos % por vacío por si el usuario lo pone por costumbre
            entrada_limpia = entrada.replace('%', '').strip()
            descuento = float(entrada_limpia)
            
            # Devolvemos un entero si no tiene decimales (ej: 15.0 -> 15)
            if descuento.is_integer():
                return int(descuento)
            return descuento
        except ValueError:
            print("Error: Solo se permiten números. Intente nuevamente.")

def conectar_sheets():
    """Conecta a Google Sheets y devuelve un DataFrame limpio."""
    try:
        gc = gspread.service_account(filename=JSON_CREDS)
        sh = gc.open(NOMBRE_HOJA)
        
        # Leer todos los valores brutos
        datos_brutos = sh.sheet1.get_all_values()
        
        # Asumimos que la fila 2 (índice 1) tiene los encabezados
        headers = datos_brutos[1]
        data = datos_brutos[2:]
        
        df = pd.DataFrame(data, columns=headers)
        return df
    except Exception as e:
        print(f"Error crítico conectando a Sheets: {e}")
        return pd.DataFrame()

def obtener_top_3_globales(df):
    """
    Analiza toda la base de datos para encontrar los 3 productos más vendidos
    sumando las cantidades de todos los clientes.
    """
    # 1. Definir columnas que NO son productos
    cols_cliente = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'DNI']
    
    # 2. Identificar columnas de productos (las que no están en cols_cliente)
    cols_productos = [col for col in df.columns if col not in cols_cliente and col != '']
    
    # 3. Limpieza: Convertir a números, reemplazar vacíos con 0
    for col in cols_productos:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # 4. Sumar ventas totales por columna (producto)
    ventas_totales = df[cols_productos].sum().sort_values(ascending=False)
    
    # 5. Extraer el podio (Top 3)
    top_productos = ventas_totales.index.tolist()
    
    # Manejo de casos donde haya menos de 3 productos
    p1 = top_productos[0] if len(top_productos) > 0 else "Producto A"
    p2 = top_productos[1] if len(top_productos) > 1 else "Producto B"
    p3 = top_productos[2] if len(top_productos) > 2 else "Producto C"
    
    return p1, p2, p3

def formatear_telefono(numero):
    """Ajusta el formato del teléfono para WhatsApp (ej: Argentina 549...)."""
    num_str = str(numero).strip()
    # Si no empieza con 54, asumimos que falta el código de país (ajustar según necesidad)
    if not num_str.startswith("54"):
        return f"549{num_str}"
    return num_str

def enviar_mensaje_cloud_api(telefono, prod1, descuento, prod2, prod3):
    """
    Envía el mensaje usando la plantilla específica de 4 variables.
    Variables: {{1}}=Prod1, {{2}}=Descuento, {{3}}=Prod2, {{4}}=Prod3
    """
    headers = {
        "Authorization": f"Bearer {CLOUD_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "template",
        "template": {
            "name": "oferta_top_3", # <--- ASEGÚRATE DE QUE ESTE NOMBRE COINCIDA CON TU TEMPLATE EN META
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
    
    # 1. Paso previo: Pedir el descuento al usuario
    porcentaje_descuento = solicitar_descuento()
    print(f"-> Descuento configurado: {porcentaje_descuento}%")
    
    # 2. Cargar Datos
    print("-> Conectando con Google Sheets...")
    df_completo = conectar_sheets()
    
    if not df_completo.empty:
        # 3. Calcular Top 3 Global
        top1, top2, top3 = obtener_top_3_globales(df_completo)
        print(f"\n--- Top 3 Global Detectado ---")
        print(f"1. {top1}")
        print(f"2. {top2}")
        print(f"3. {top3}")
        print("------------------------------\n")
        
        # 4. Enviar Mensajes a la lista de clientes
        print(f"Iniciando envío a {len(df_completo)} clientes...")
        
        for i, fila in df_completo.iterrows():
            cliente = fila['Cliente']
            telefono_raw = fila['Numero de Telefono']
            
            if not telefono_raw:
                print(f"Saltando a {cliente}: Sin teléfono registrado.")
                continue
                
            telefono = formatear_telefono(telefono_raw)
            
            print(f"Enviando oferta a {cliente} ({telefono})...")
            
            # Envío real
            exito, msg = enviar_mensaje_cloud_api(telefono, top1, porcentaje_descuento, top2, top3)
            
            if exito:
                print("   [OK] Enviado.")
            else:
                print(f"   [ERROR] {msg}")
            
            # Pausa para evitar bloqueo por spam/rate limits
            time.sleep(1) 
            
        print("\n--- Proceso finalizado ---")
            
    else:
        print("No se pudieron obtener datos del Sheet. Revisa tu archivo 'service_account.json'.")