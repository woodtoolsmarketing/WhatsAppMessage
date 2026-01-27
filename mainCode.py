import pandas as pd
import gspread
import requests
import time
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN DE WHATSAPP CLOUD API ---
# Estos datos los obtienes en el panel de Meta Developers
CLOUD_API_TOKEN = "TU_TOKEN_AQUI"
PHONE_NUMBER_ID = "TU_PHONE_ID_AQUI"
VERSION = "v17.0"
URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}/messages"

# Configuración de Google Sheets
NOMBRE_HOJA = "Base de datos wt"
JSON_CREDS = 'sheets.json'

def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(JSON_CREDS, scope)
    client = gspread.authorize(creds)
    return pd.DataFrame(client.open(NOMBRE_HOJA).sheet1.get_all_records())

def enviar_mensaje_cloud_api(telefono, nombre, producto):
    headers = {
        "Authorization": f"Bearer {CLOUD_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Estructura JSON exigida por la Cloud API
    data = {
        "messaging_product": "whatsapp",
        "to": str(telefono),
        "type": "template",
        "template": {
            "name": "oferta_personalizada", # Nombre de tu plantilla aprobada
            "language": {"code": "es"},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": nombre},
                    {"type": "text", "text": producto}
                ]
            }]
        }
    }
    
    try:
        response = requests.post(URL, headers=headers, json=data)
        if response.status_code == 200:
            return True, "Enviado"
        else:
            return False, response.text
    except Exception as e:
        return False, str(e)

# --- FLUJO PRINCIPAL ---
if __name__ == "__main__":
    print("Iniciando Bot de Ventas (Cloud API)...")
    
    # 1. Leer datos
    df = conectar_sheets()
    
    # 2. Calcular Tendencias (Qué compra más cada cliente)
    # Agrupa por cliente y elige la categoría más frecuente
    tendencias = df.groupby(['Cliente', 'Telefono'])['Categoria'].agg(
        lambda x: x.value_counts().index[0]
    ).reset_index()
    
    # 3. Enviar
    for i, fila in tendencias.iterrows():
        print(f"Procesando a {fila['Cliente']}...", end=" ")
        exito, msg = enviar_mensaje_cloud_api(fila['Telefono'], fila['Cliente'], fila['Categoria'])
        print(f"Resultado: {msg}")
        time.sleep(1) # Respetar límites de la API