import pandas as pd
import gspread
import requests
import time
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
# ¡IMPORTANTE! Este token es temporal. Por seguridad, no lo subas a GitHub público.
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
        # Obtiene todos los valores
        datos_brutos = sh.sheet1.get_all_values()
        
        # Según tu lógica: Fila 1 (índice 1) son headers, Fila 2 en adelante son datos
        if len(datos_brutos) < 2:
            return pd.DataFrame()

        headers = datos_brutos[1] 
        data = datos_brutos[2:]
        
        df = pd.DataFrame(data, columns=headers)
        return df
    except Exception as e:
        print(f"Error al conectar con Sheets: {e}")
        return pd.DataFrame() 

def obtener_top_3_globales(df):
    """Calcula los 3 productos más vendidos globalmente."""
    # Columnas que NO son productos (Datos del cliente)
    cols_cliente = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'CUIT', 'Ubicación']
    
    # Detectar columnas de productos dinámicamente
    cols_productos = [col for col in df.columns if col not in cols_cliente and col != '']
    
    df_calc = df.copy()
    
    # Convertir a números para poder sumar (tratando vacíos como 0)
    for col in cols_productos:
        df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)

    # Sumar ventas y ordenar
    ventas_totales = df_calc[cols_productos].sum().sort_values(ascending=False)
    top_productos = ventas_totales.index.tolist()
    
    # Asegurar que existan al menos 3, si no rellenar
    p1 = top_productos[0] if len(top_productos) > 0 else "Producto A"
    p2 = top_productos[1] if len(top_productos) > 1 else "Producto B"
    p3 = top_productos[2] if len(top_productos) > 2 else "Producto C"
    
    return p1, p2, p3

def formatear_telefono(numero):
    """Formatea el número para WhatsApp (quita espacios, agrega 549 si falta)."""
    num_str = str(numero).strip().replace(" ", "").replace("-", "")
    if not num_str.startswith("54"):
        return f"549{num_str}"
    return num_str

def enviar_mensaje_cloud_api(telefono, prod1, descuento, prod2, prod3):
    """Envía el mensaje usando la plantilla 'oferta_top_3'."""
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

# --- FUNCIÓN PRINCIPAL PARA LLAMAR DESDE INTERFAZ ---
def ejecutar_envio_masivo(descuento_texto="15% OFF"):
    """
    Función que orquesta todo el proceso:
    1. Conecta a la base de datos.
    2. Calcula los productos top.
    3. Itera por los clientes y envía mensajes.
    """
    print("Iniciando proceso...")
    df = conectar_sheets()
    
    if df.empty:
        return "Error: No se pudo cargar la base de datos o está vacía."

    # Obtener los productos estrella
    p1, p2, p3 = obtener_top_3_globales(df)
    print(f"Top Productos calculados: {p1}, {p2}, {p3}")

    contador_exitos = 0
    contador_errores = 0

    # Iterar sobre cada cliente
    for index, row in df.iterrows():
        try:
            nombre = row.get('Cliente', 'Cliente')
            telefono_raw = row.get('Numero de Telefono', '')
            
            if not telefono_raw:
                continue # Saltar si no hay teléfono

            telefono_fmt = formatear_telefono(telefono_raw)
            
            # Enviar mensaje
            exito, mensaje = enviar_mensaje_cloud_api(telefono_fmt, p1, descuento_texto, p2, p3)
            
            if exito:
                print(f"✅ Enviado a {nombre} ({telefono_fmt})")
                contador_exitos += 1
            else:
                print(f"❌ Error con {nombre}: {mensaje}")
                contador_errores += 1
            
            # Pausa para respetar límites de la API (evita bloqueo)
            time.sleep(1) 

        except Exception as e:
            print(f"Error procesando fila {index}: {e}")
            contador_errores += 1

    resultado_final = f"Proceso finalizado.\nEnviados: {contador_exitos}\nFallidos: {contador_errores}"
    return resultado_final

# Bloque para probarlo directamente ejecutando este archivo
if __name__ == "__main__":
    print(ejecutar_envio_masivo())