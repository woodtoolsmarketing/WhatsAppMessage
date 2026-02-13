import pandas as pd
import gspread
import requests
import time
import os
import urllib.parse
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

# Colores consola
COLOR_ROJO = "\033[91m"
COLOR_RESET = "\033[0m"
COLOR_VERDE = "\033[92m"
COLOR_AMARILLO = "\033[93m"
COLOR_AZUL = "\033[94m"

# --- DICCIONARIO DE VENDEDORES (EXPANDIDO) ---
# Incluye tanto los grupos ("1/302") como los individuales ("1", "302")
DB_VENDEDORES = {
    # Caso Vendedor 0 (Tiene 2 líneas distintas)
    "0":     ["5491145394279", "5491165630406"],

    # Caso 1 y 302 (Líneas distintas)
    "1":     ["5491157528428"],
    "302":   ["5491134609057"],
    "1/302": ["5491157528428", "5491134609057"], # Grupo para menú

    # Caso 02
    "02":    ["5491145640940"],

    # Caso 15 y 40 (Comparten la MISMA línea)
    "15":    ["5491157528427"],
    "40":    ["5491157528427"],
    "15/40": ["5491157528427"],

    # Caso 04 y 44 (Comparten la MISMA línea)
    "04":    ["5491156321012"],
    "44":    ["5491156321012"],
    "04/44": ["5491156321012"],

    # Resto
    "09":    ["5491153455274"],
    "05":    ["5491164591316"],
    "16":    ["5491145640831"],
    "03":    ["5491168457778"]
}

# Lista visual para mantener el menú limpio (solo mostramos los grupos)
OPCIONES_VISUALES = ["0", "1/302", "02", "15/40", "04/44", "09", "05", "16", "03"]

# --- FUNCIONES DE CONEXIÓN Y DATOS ---

def conectar_sheets():
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

# --- LÓGICA DE SELECCIÓN DE VENDEDOR ---

def seleccionar_numero_vendedor():
    print(f"\n{COLOR_AMARILLO}--- SELECCIÓN DE VENDEDOR ---{COLOR_RESET}")
    print("Opciones disponibles (puedes escribir el grupo o el número individual):")
    
    # Mostrar menú limpio (solo las opciones principales)
    for i, k in enumerate(OPCIONES_VISUALES):
        print(f"{COLOR_AZUL}{k}{COLOR_RESET}", end=" | ")
    print("\n")
    
    while True:
        seleccion = input("Escriba el código del vendedor: ").strip()
        
        if seleccion in DB_VENDEDORES:
            numeros = DB_VENDEDORES[seleccion]
            
            # --- LÓGICA DE DESEMPATE ---
            
            # 1. Si eligieron el GRUPO "1/302" -> Hay que preguntar
            if seleccion == "1/302":
                print(f"Seleccionaste el grupo 1/302:")
                print(f"1. Vendedor 1 ({numeros[0]})")
                print(f"2. Vendedor 302 ({numeros[1]})")
                sub = input("¿Para cuál es? (1 o 2): ")
                return numeros[1] if sub == "2" else numeros[0]

            # 2. Si eligieron el VENDEDOR "0" (siempre son 2 líneas distintas) -> Hay que preguntar
            elif seleccion == "0":
                print(f"El vendedor 0 tiene dos líneas:")
                print(f"1. {numeros[0]}")
                print(f"2. {numeros[1]}")
                sub = input("¿Cuál usar? (1 o 2): ")
                return numeros[1] if sub == "2" else numeros[0]
            
            # 3. Resto de casos (Individuales como "1", "302" o Grupos con mismo número como "15/40")
            # Devuelven el primer (y único o principal) número directamente
            else:
                return numeros[0]
        else:
            print(f"{COLOR_ROJO}Código no encontrado. Intente nuevamente.{COLOR_RESET}")

def generar_texto_footer(telefono_vendedor, productos_ofrecidos):
    mensaje_cliente = f"Hola, me interesan las promociones sobre: {productos_ofrecidos}"
    mensaje_encoded = urllib.parse.quote(mensaje_cliente)
    link = f"https://wa.me/{telefono_vendedor}?text={mensaje_encoded}"
    return f"Si te interesa saber más sobre estas promociones entra al {link}"

# --- LÓGICA DE PRODUCTOS ---

def obtener_top_3_globales(df):
    cols = identificar_cols_productos(df)
    df_calc = df.copy()
    for col in cols:
        df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)
    ventas = df_calc[cols].sum().sort_values(ascending=False)
    top = ventas.index.tolist()
    return (top[0] if len(top)>0 else "A", top[1] if len(top)>1 else "B", top[2] if len(top)>2 else "C")

def obtener_top_personalizados(row, cols_productos):
    try:
        datos = row[cols_productos]
        datos = pd.to_numeric(datos, errors='coerce').fillna(0)
        ranking = datos.sort_values(ascending=False)
        comprados = ranking[ranking > 0].index.tolist()
        p1 = comprados[0] if len(comprados) > 0 else "nuestros productos"
        p2 = comprados[1] if len(comprados) > 1 else "nuestras ofertas"
        return p1, p2
    except:
        return "nuestros productos", "ofertas"

# --- FUNCIONES DE ENVÍO ---

def _enviar_request(data):
    headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.post(f"{BASE_URL}/messages", headers=headers, json=data)
        return response.status_code == 200, response.text
    except Exception as e:
        return False, str(e)

def subir_imagen_whatsapp(ruta_archivo):
    url = f"{BASE_URL}/media"
    headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}"}
    ext = os.path.splitext(ruta_archivo)[1].lower()
    
    if ext not in ['.jpg', '.jpeg', '.png']:
        print(f"\n{COLOR_ROJO}¡ALERTA! Introduce un formato válido (.jpg, .jpeg, .png){COLOR_RESET}")
        return None

    try:
        files = {'file': (os.path.basename(ruta_archivo), open(ruta_archivo, 'rb'), f'image/{ext.replace(".","")}')}
        data = {'messaging_product': 'whatsapp'}
        response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code == 200: return response.json()['id']
        else:
            print(f"{COLOR_ROJO}Error subiendo imagen: {response.text}{COLOR_RESET}")
            return None
    except FileNotFoundError:
        print(f"{COLOR_ROJO}No se encontró el archivo.{COLOR_RESET}")
        return None

# --- TIPOS DE MENSAJES ---

def enviar_promocion(tel, p1, p2, p3, footer_link):
    data = {
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {
            "name": PLANTILLA_PROMOS, "language": {"code": "es"},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": str(p1)}, 
                {"type": "text", "text": "Descuentos"}, 
                {"type": "text", "text": str(p2)}, 
                {"type": "text", "text": str(p3)},
                {"type": "text", "text": str(footer_link)}
            ]}]
        }
    }
    return _enviar_request(data)

def enviar_rescate(tel, nombre, prod_fav, footer_link):
    data = {
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {
            "name": PLANTILLA_RESCATE, "language": {"code": "es"},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": str(nombre)}, 
                {"type": "text", "text": str(prod_fav)},
                {"type": "text", "text": str(footer_link)}
            ]}]
        }
    }
    return _enviar_request(data)

def enviar_gira(tel, vendedor, p1, p2, footer_link):
    data = {
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {
            "name": PLANTILLA_GIRA, "language": {"code": "es"},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": str(vendedor)}, 
                {"type": "text", "text": str(p1)}, 
                {"type": "text", "text": str(p2)},
                {"type": "text", "text": str(footer_link)}
            ]}]
        }
    }
    return _enviar_request(data)

def enviar_personalizado(tel, texto, media_id, footer_link):
    texto_completo = f"{texto}\n\n{footer_link}"
    data = {
        "messaging_product": "whatsapp", "to": tel, "type": "image",
        "image": {"id": media_id, "caption": texto_completo}
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
    if opcion not in ['1', '2', '3', '4']: return

    # 1. Seleccionar Vendedor (Obligatorio)
    num_vendedor_seleccionado = seleccionar_numero_vendedor()
    print(f"{COLOR_VERDE}✅ Número configurado para el link: {num_vendedor_seleccionado}{COLOR_RESET}")

    df = conectar_sheets()
    if df.empty: return
    cols_productos = identificar_cols_productos(df)
    
    # Datos específicos según opción
    top_p1, top_p2, top_p3 = "", "", ""
    nombre_vendedor_gira = ""
    texto_personalizado = ""
    media_id_personalizado = ""

    if opcion == '1':
        top_p1, top_p2, top_p3 = obtener_top_3_globales(df)
        print(f"Top Global calculado: {top_p1}, {top_p2}, {top_p3}")
    
    elif opcion == '3':
        nombre_vendedor_gira = input("Ingrese el nombre del vendedor que viaja: ")

    elif opcion == '4':
        texto_personalizado = input("Texto del mensaje: ")
        while True:
            ruta = input("Ruta imagen (.jpg/.png): ").strip().replace('"', '')
            media_id_personalizado = subir_imagen_whatsapp(ruta)
            if media_id_personalizado: break
            if input("¿Reintentar? (s/n): ").lower() != 's': return

    print(f"\nIniciando envío a {len(df)} clientes...\n")
    
    cont_ok = 0
    for index, row in df.iterrows():
        nombre = row.get('Cliente', 'Cliente')
        tel = formatear_telefono(row.get('Numero de Telefono', ''))
        
        if not tel: continue

        # Generar Link Dinámico
        productos_ofertados = ""
        if opcion == '1':
            productos_ofertados = f"{top_p1}, {top_p2}, {top_p3}"
        elif opcion == '2' or opcion == '3':
            p1_pers, p2_pers = obtener_top_personalizados(row, cols_productos)
            productos_ofertados = f"{p1_pers} y {p2_pers}"
        elif opcion == '4':
            productos_ofertados = "la promoción enviada"

        footer_dinamico = generar_texto_footer(num_vendedor_seleccionado, productos_ofertados)

        # Enviar Mensaje
        exito = False
        msg = ""

        if opcion == '1':
            exito, msg = enviar_promocion(tel, top_p1, top_p2, top_p3, footer_dinamico)
        elif opcion == '2':
            p1, _ = obtener_top_personalizados(row, cols_productos)
            exito, msg = enviar_rescate(tel, nombre, p1, footer_dinamico)
        elif opcion == '3':
            p1, p2 = obtener_top_personalizados(row, cols_productos)
            exito, msg = enviar_gira(tel, nombre_vendedor_gira, p1, p2, footer_dinamico)
        elif opcion == '4':
            exito, msg = enviar_personalizado(tel, texto_personalizado, media_id_personalizado, footer_dinamico)

        if exito:
            print(f"{COLOR_VERDE}✅ Enviado a {nombre}{COLOR_RESET}")
            cont_ok += 1
        else:
            print(f"{COLOR_ROJO}❌ Error {nombre}: {msg}{COLOR_RESET}")
        
        time.sleep(1)

    print(f"\nProceso finalizado. Total enviados: {cont_ok}")

if __name__ == "__main__":
    ejecutar_sistema()