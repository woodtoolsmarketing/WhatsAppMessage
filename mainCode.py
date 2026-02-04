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
        return pd.DataFrame() # Retorna vacío si hay error

def obtener_top_3_globales(df):
    """Calcula los 3 productos más vendidos globalmente."""
    # Agregamos 'Ubicación' a la lista de columnas que NO son productos
    cols_cliente = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'DNI', 'Ubicación']
    cols_productos = [col for col in df.columns if col not in cols_cliente and col != '']
    
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
            return True, "Enviado OK"
        else:
            return False, f"Error API: {response.text}"
    except Exception as e:
        return False, str(e)