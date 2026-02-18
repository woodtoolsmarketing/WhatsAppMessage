import pandas as pd
import requests
import os
import sys
import urllib.parse

# --- CONFIGURACIÓN ---
CLOUD_API_TOKEN = "TU_TOKEN_AQUI"
PHONE_NUMBER_ID = "TU_ID_TELEFONO_AQUI"
VERSION = "v17.0"
BASE_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}"

# --- LÓGICA DE RUTA (Para que funcione en el .EXE y en VSCode) ---
def obtener_ruta_recurso(ruta_relativa):
    """
    Busca archivos basándose en la ubicación del ejecutable o del script.
    """
    if getattr(sys, 'frozen', False):
        # Si es un .EXE (creado con PyInstaller)
        ruta_base = os.path.dirname(sys.executable)
    else:
        # Si estamos ejecutando el .py en VSCode
        ruta_base = os.path.dirname(os.path.abspath(__file__))
    
    return os.path.join(ruta_base, ruta_relativa)

# --- CORRECCIÓN REALIZADA AQUÍ (PASO 1) ---
# Ahora busca exactamente el archivo que tienes en tu carpeta
ARCHIVO_EXCEL = obtener_ruta_recurso("Base de datos wt.xlsx")

# Nombres de las plantillas
PLANTILLA_PROMOS = "oferta_top_3"
PLANTILLA_RESCATE = "reactivacion_cliente"
PLANTILLA_GIRA = "aviso_visita_vendedor"

# Diccionario de vendedores
DB_VENDEDORES = {
    "0": ["5491145394279", "5491165630406"], "1": ["5491157528428"], "302": ["5491134609057"],
    "1/302": ["5491157528428", "5491134609057"], "02": ["5491145640940"], "15": ["5491157528427"],
    "40": ["5491157528427"], "15/40": ["5491157528427"], "04": ["5491156321012"], "44": ["5491156321012"],
    "04/44": ["5491156321012"], "09": ["5491153455274"], "05": ["5491164591316"], "16": ["5491145640831"],
    "03": ["5491168457778"]
}

LISTA_OBSERVADOS = []

# --- LECTURA DE EXCEL ---
def leer_desde_excel():
    print(f"--- LEYENDO BASE DE DATOS ---")
    print(f"Buscando archivo en: {ARCHIVO_EXCEL}")
    
    if not os.path.exists(ARCHIVO_EXCEL):
        print("❌ ERROR: El archivo no existe. Asegúrate de copiar 'Base de datos wt.xlsx' junto al .exe")
        return []

    try:
        # Leemos sin encabezados para procesar la estructura cruda
        if ARCHIVO_EXCEL.endswith('.csv'):
            df = pd.read_csv(ARCHIVO_EXCEL, header=None, dtype=str)
        else:
            df = pd.read_excel(ARCHIVO_EXCEL, header=None, dtype=str)
        
        # Buscamos dónde empieza el primer código numérico
        start_index = 0
        for idx, row in df.iterrows():
            val = str(row[0])
            if val.isdigit() and len(val) > 5: # Código de cliente detectado
                start_index = idx
                break
        
        data_rows = df.iloc[start_index:].reset_index(drop=True)
        registros = []
        i = 0
        
        while i < len(data_rows):
            row = data_rows.iloc[i]
            code = str(row[0])
            
            if pd.notna(code) and code.strip().isdigit() and len(code.strip()) > 3:
                # Fila 1: Datos principales
                cliente_dict = {
                    'Número de cliente': code.strip(),
                    'Cliente': str(row[1]).strip() if pd.notna(row[1]) else "Cliente Sin Nombre",
                    'Numero de Telefono': str(row[5]).strip() if pd.notna(row[5]) else "",
                    'CUIT': str(row[8]).strip() if pd.notna(row[8]) else "",
                    'Zona': '0', 'Vendedor': '0'
                }
                
                # Fila 2 (i+1): Datos adicionales
                if i + 1 < len(data_rows):
                    row2 = data_rows.iloc[i+1]
                    if pd.isna(row2[0]) or not str(row2[0]).strip().isdigit():
                        # Fila 3 (i+2): Zona
                        if i + 2 < len(data_rows):
                            row3 = data_rows.iloc[i+2]
                            if (pd.isna(row3[0]) or not str(row3[0]).strip()) and \
                               pd.notna(row3[2]) and str(row3[2]).strip().isdigit():
                                cliente_dict['Zona'] = str(row3[2]).strip()
                                i += 1 
                        i += 1 
                
                registros.append(cliente_dict)
            i += 1
            
        print(f"✅ {len(registros)} clientes importados correctamente.")
        return registros

    except Exception as e:
        print(f"❌ Error procesando Excel: {e}")
        return []

# --- VALIDACIÓN ---
def formatear_telefono(numero):
    num_str = str(numero).strip().replace(" ", "").replace("-", "").replace(".", "").replace("*", "").replace("/", "")
    if num_str.endswith("0") and "." in str(numero): num_str = num_str[:-2]
    num_str = ''.join(filter(str.isdigit, num_str))
    if not num_str: return "" 
    if num_str.startswith("0"): num_str = num_str[1:] 
    if not num_str.startswith("54"): return f"549{num_str}"
    return num_str

def validar_formato_numero(numero_raw):
    numero_fmt = formatear_telefono(numero_raw)
    if not numero_fmt: return False, ""
    if len(numero_fmt) < 10 or len(numero_fmt) > 15: return False, numero_fmt
    return True, numero_fmt

def conectar_y_procesar():
    global LISTA_OBSERVADOS
    LISTA_OBSERVADOS = [] 
    datos = leer_desde_excel()
    data_procesada = []
    
    for registro in datos:
        raw_tel = registro.get('Numero de Telefono', '')
        es_valido, tel_fmt = validar_formato_numero(raw_tel)
        registro['Es_Valido'] = es_valido
        registro['Tel_Formateado'] = tel_fmt
        data_procesada.append(registro)
        if not es_valido: LISTA_OBSERVADOS.append(registro)

    return pd.DataFrame(data_procesada)

def revisar_numeros_problematicos():
    global LISTA_OBSERVADOS
    if not LISTA_OBSERVADOS: return "✅ Base limpia."
    txt = f"--- {len(LISTA_OBSERVADOS)} NÚMEROS INVÁLIDOS ---\n"
    for item in LISTA_OBSERVADOS:
        txt += f"• {item['Cliente']}: {item['Numero de Telefono']}\n"
    return txt

# --- HELPERS ---
def identificar_cols_productos(df):
    return ['Sierras', 'Cuchillas', 'Mechas', 'Fresas', 'Cabezales']

def generar_texto_footer(tel, prods):
    msg = urllib.parse.quote(f"Hola, me interesan las promociones sobre: {prods}")
    return f"Más info: https://wa.me/{tel}?text={msg}"

def obtener_top_3_globales(df):
    return ("Ofertas", "Herramientas", "Promociones")

def obtener_top_personalizados(row, cols):
    return "Nuestros Productos", "Ofertas Especiales"

# --- API WHATSAPP ---
def _enviar_request(data):
    try:
        headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}", "Content-Type": "application/json"}
        res = requests.post(f"{BASE_URL}/messages", headers=headers, json=data)
        return res.status_code == 200, res.text
    except Exception as e: return False, str(e)

def subir_imagen_whatsapp(ruta):
    try:
        headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}"}
        files = {'file': (os.path.basename(ruta), open(ruta, 'rb'), 'image/jpeg')}
        data = {'messaging_product': 'whatsapp'}
        res = requests.post(f"{BASE_URL}/media", headers=headers, files=files, data=data)
        if res.status_code == 200: return res.json()['id']
        return None
    except: return None

# --- ENVÍOS ---
def enviar_promocion(tel, p1, p2, p3, link):
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {"name": PLANTILLA_PROMOS, "language": {"code": "es"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": str(p1)}, {"type": "text", "text": "Descuentos"}, {"type": "text", "text": str(p2)}, {"type": "text", "text": str(p3)}, {"type": "text", "text": str(link)}]}]}
    })

def enviar_rescate(tel, nom, prod, link):
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {"name": PLANTILLA_RESCATE, "language": {"code": "es"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": str(nom)}, {"type": "text", "text": str(prod)}, {"type": "text", "text": str(link)}]}]}
    })

def enviar_gira(tel, vend, p1, p2, link):
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {"name": PLANTILLA_GIRA, "language": {"code": "es"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": str(vend)}, {"type": "text", "text": str(p1)}, {"type": "text", "text": str(p2)}, {"type": "text", "text": str(link)}]}]}
    })

def enviar_personalizado(tel, txt, media, link):
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "image",
        "image": {"id": media, "caption": f"{txt}\n\n{link}"}
    })