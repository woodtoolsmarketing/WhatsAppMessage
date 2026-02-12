import pandas as pd
import gspread
import requests
import time
import os
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURACIÓN ---
CLOUD_API_TOKEN = "TU_TOKEN_AQUI"
PHONE_NUMBER_ID = "TU_ID_TELEFONO_AQUI"
VERSION = "v17.0"
BASE_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}"
JSON_CREDS = 'service_account.json' 
NOMBRE_HOJA = "Base de datos wt"

# Nombres de las plantillas en Meta
PLANTILLA_PROMOS = "oferta_top_3"
PLANTILLA_RESCATE = "reactivacion_cliente"
PLANTILLA_GIRA = "aviso_visita_vendedor"

# Códigos de colores para la consola
COLOR_ROJO = "\033[91m"
COLOR_RESET = "\033[0m"
COLOR_VERDE = "\033[92m"

# --- FUNCIONES DE CONEXIÓN Y DATOS ---

def conectar_sheets():
    """Conecta a Google Sheets y devuelve un DataFrame limpio."""
    try:
        gc = gspread.service_account(filename=JSON_CREDS)
        sh = gc.open(NOMBRE_HOJA)
        datos_brutos = sh.sheet1.get_all_values()
        if len(datos_brutos) < 2: return pd.DataFrame()
        headers = datos_brutos[1] 
        data = datos_brutos[2:]
        return pd.DataFrame(data, columns=headers)
    except Exception as e:
        print(f"{COLOR_ROJO}Error conectando a Sheets: {e}{COLOR_RESET}")
        return pd.DataFrame() 

def formatear_telefono(numero):
    num_str = str(numero).strip().replace(" ", "").replace("-", "")
    if not num_str.startswith("54"):
        return f"549{num_str}"
    return num_str

def identificar_cols_productos(df):
    cols_cliente = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'CUIT', 'Ubicación']
    return [col for col in df.columns if col not in cols_cliente and col != '']

# --- LÓGICA DE CÁLCULO DE PRODUCTOS ---

def obtener_top_3_globales(df):
    cols = identificar_cols_productos(df)
    df_calc = df.copy()
    for col in cols:
        df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)
    ventas = df_calc[cols].sum().sort_values(ascending=False)
    top = ventas.index.tolist()
    return (top[0] if len(top)>0 else "A", top[1] if len(top)>1 else "B", top[2] if len(top)>2 else "C")

def obtener_top_personalizados(row, cols_productos):
    """Devuelve una lista ordenada de productos comprados por el cliente."""
    try:
        datos = row[cols_productos]
        datos = pd.to_numeric(datos, errors='coerce').fillna(0)
        ranking = datos.sort_values(ascending=False)
        # Filtramos solo los que tienen ventas > 0
        comprados = ranking[ranking > 0].index.tolist()
        
        # Rellenos por defecto si no compró nada
        p1 = comprados[0] if len(comprados) > 0 else "nuestros productos"
        p2 = comprados[1] if len(comprados) > 1 else "nuestras ofertas"
        return p1, p2
    except:
        return "nuestros productos", "ofertas"

# --- FUNCIONES DE ENVÍO (API WHATSAPP) ---

def _enviar_request(data):
    """Función interna para hacer el POST."""
    headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.post(f"{BASE_URL}/messages", headers=headers, json=data)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def subir_imagen_whatsapp(ruta_archivo):
    """Sube la imagen a WhatsApp y obtiene el ID para enviarla."""
    url = f"{BASE_URL}/media"
    headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}"}
    
    # Validación de formato estricta
    ext = os.path.splitext(ruta_archivo)[1].lower()
    if ext not in ['.jpg', '.jpeg', '.png']:
        print(f"\n{COLOR_ROJO}¡ALERTA! Introduce un formato válido (.jpg, .jpeg, .png){COLOR_RESET}")
        return None

    try:
        files = {
            'file': (os.path.basename(ruta_archivo), open(ruta_archivo, 'rb'), f'image/{ext.replace(".","")}')
        }
        data = {'messaging_product': 'whatsapp'}
        response = requests.post(url, headers=headers, files=files, data=data)
        
        if response.status_code == 200:
            return response.json()['id']
        else:
            print(f"{COLOR_ROJO}Error subiendo imagen: {response.text}{COLOR_RESET}")
            return None
    except FileNotFoundError:
        print(f"{COLOR_ROJO}No se encontró el archivo: {ruta_archivo}{COLOR_RESET}")
        return None

# --- TIPOS DE MENSAJES ---

def enviar_promocion(tel, p1, p2, p3):
    data = {
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {
            "name": PLANTILLA_PROMOS, "language": {"code": "es"},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": str(p1)}, {"type": "text", "text": "Descuentos"}, 
                {"type": "text", "text": str(p2)}, {"type": "text", "text": str(p3)}
            ]}]
        }
    }
    return _enviar_request(data)

def enviar_rescate(tel, nombre, prod_fav):
    data = {
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {
            "name": PLANTILLA_RESCATE, "language": {"code": "es"},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": str(nombre)}, {"type": "text", "text": str(prod_fav)}
            ]}]
        }
    }
    return _enviar_request(data)

def enviar_gira(tel, vendedor, p1, p2):
    data = {
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {
            "name": PLANTILLA_GIRA, "language": {"code": "es"},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": str(vendedor)}, {"type": "text", "text": str(p1)}, {"type": "text", "text": str(p2)}
            ]}]
        }
    }
    return _enviar_request(data)

def enviar_personalizado(tel, texto, media_id):
    data = {
        "messaging_product": "whatsapp",
        "to": tel,
        "type": "image",
        "image": {
            "id": media_id,
            "caption": texto
        }
    }
    return _enviar_request(data)

# --- MENÚ Y CONTROLADOR ---

def mostrar_menu():
    print("\n" + "="*40)
    print(" SISTEMA DE ENVÍO MASIVO WHATSAPP ")
    print("="*40)
    print("1. Promociones (Top Global)")
    print("2. Rescate (Cliente inactivo)")
    print("3. Gira (Vendedor en zona)")
    print("4. Personalizado (Texto + Imagen)")
    print("="*40)
    return input("Seleccione una opción (1-4): ")

def ejecutar_sistema():
    opcion = mostrar_menu()
    
    if opcion not in ['1', '2', '3', '4']:
        print("Opción inválida.")
        return

    # Preparación de datos comunes
    df = conectar_sheets()
    if df.empty: return
    cols_productos = identificar_cols_productos(df)
    
    # Preparación específica según opción
    params_extra = {}
    
    if opcion == '1': # Promociones
        p1, p2, p3 = obtener_top_3_globales(df)
        print(f"Promocionando Top Global: {p1}, {p2}, {p3}")
        params_extra = {'p1': p1, 'p2': p2, 'p3': p3}

    elif opcion == '3': # Gira
        vendedor = input("Ingrese el nombre del vendedor para la gira: ")
        params_extra = {'vendedor': vendedor}

    elif opcion == '4': # Personalizado
        texto = input("Escriba el mensaje para el pie de foto: ")
        while True:
            ruta = input("Ingrese la ruta de la imagen (ej: C:/fotos/promo.jpg): ").strip().replace('"', '')
            media_id = subir_imagen_whatsapp(ruta)
            if media_id:
                params_extra = {'texto': texto, 'media_id': media_id}
                break
            else:
                retry = input("¿Intentar de nuevo? (s/n): ")
                if retry.lower() != 's': return

    print(f"\nIniciando envío a {len(df)} clientes...\n")
    
    cont_ok = 0
    for index, row in df.iterrows():
        nombre = row.get('Cliente', 'Cliente')
        tel = formatear_telefono(row.get('Numero de Telefono', ''))
        
        if not tel: continue

        exito = False
        msg = ""

        # SELECCIÓN DE LÓGICA DE ENVÍO
        if opcion == '1':
            exito, msg = enviar_promocion(tel, **params_extra)
        
        elif opcion == '2':
            p1, _ = obtener_top_personalizados(row, cols_productos)
            exito, msg = enviar_rescate(tel, nombre, p1)
            
        elif opcion == '3':
            p1, p2 = obtener_top_personalizados(row, cols_productos)
            exito, msg = enviar_gira(tel, params_extra['vendedor'], p1, p2)
            
        elif opcion == '4':
            exito, msg = enviar_personalizado(tel, **params_extra)

        # Feedback visual
        if exito:
            print(f"{COLOR_VERDE}✅ Enviado a {nombre}{COLOR_RESET}")
            cont_ok += 1
        else:
            print(f"{COLOR_ROJO}❌ Error {nombre}: {msg}{COLOR_RESET}")
        
        time.sleep(1) # Pausa anti-spam

    print(f"\nProceso finalizado. Total enviados: {cont_ok}")

if __name__ == "__main__":
    ejecutar_sistema()