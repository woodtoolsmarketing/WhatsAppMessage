import pandas as pd
import requests
import os
import sys
import urllib.parse

# ==========================================
# CONFIGURACIÓN DE LA API DE WHATSAPP
# ==========================================
CLOUD_API_TOKEN = "TU_TOKEN_AQUI"
PHONE_NUMBER_ID = "TU_ID_TELEFONO_AQUI"
VERSION = "v17.0"
BASE_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}"

# ==========================================
# LÓGICA DE RUTAS (SOPORTE PARA .EXE)
# ==========================================
def obtener_ruta_recurso(ruta_relativa):
    """
    Detecta si el script se está ejecutando desde Python o desde
    un archivo .exe compilado y devuelve la ruta correcta.
    """
    if getattr(sys, 'frozen', False):
        ruta_base = os.path.dirname(sys.executable)
    else:
        ruta_base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(ruta_base, ruta_relativa)

ARCHIVO_EXCEL = obtener_ruta_recurso("Base de datos wt.xlsx")

# Nombres de las plantillas aprobadas en Meta
PLANTILLA_PROMOS = "oferta_top_3"
PLANTILLA_RESCATE = "reactivacion_cliente"
PLANTILLA_GIRA = "aviso_visita_vendedor"

# ==========================================
# BASE DE DATOS DE VENDEDORES (ACTUALIZADA)
# ==========================================
DB_VENDEDORES = {
    "Valentín": ["5491145394279"],
    "Carlos": ["5491165630406"],
    "Emmanuel": ["5491157528428"]
}

LISTA_OBSERVADOS = []

def obtener_telefono_vendedor(codigo_excel, indice_preferencia=0):
    """
    Traduce el código numérico del Excel al número real del vendedor para el MODO AUTOMÁTICO.
    """
    codigo = str(codigo_excel).strip()
    
    if codigo == "0":
        return "5491145394279" if indice_preferencia == 0 else "5491165630406"
    elif codigo in ["1", "302", "1/302"]:
        return "5491157528428"
    else:
        return "5491145394279"

# ==========================================
# GENERADOR DINÁMICO DE LINKS CON AUTOCOMPLETADO
# ==========================================
def generar_link_whatsapp(tel, tipo_mensaje, datos_extra):
    """
    Genera un enlace de WhatsApp Web (wa.me) con un mensaje pre-escrito
    que incluye corchetes [ ] para que el cliente lo complete antes de enviarlo.
    """
    if tipo_mensaje == "Promociones":
        texto = "Hola, vi las promociones por WhatsApp y busco el [CÓDIGO] de [TIPO DE PRODUCTO] para mi máquina."
        
    elif tipo_mensaje == "Rescate (Te extrañamos)":
        texto = "Hola, me llegó el mensaje. Necesito reponer stock de [TIPO DE HERRAMIENTA] para mi taller."
        
    elif tipo_mensaje == "Gira Vendedor":
        vendedor = datos_extra.get('vendedor_nombre', 'el vendedor')
        texto = f"Hola, vi que {vendedor} va a estar por mi zona. Necesito encargar [CANTIDAD] de [TIPO DE PRODUCTO] para su visita."
        
    elif tipo_mensaje == "Novedades":
        herramienta = datos_extra.get('herramienta', 'herramientas')
        subtipo = datos_extra.get('subtipo', '')
        if subtipo == "Ingresos":
            texto = f"Hola, vi los nuevos ingresos de {herramienta}. Me interesa el modelo [CÓDIGO O MEDIDA] para cortar [MATERIAL]."
        else:
            texto = f"Hola, qué bueno que entró stock de {herramienta}. Necesito [CANTIDAD] unidades del código [CÓDIGO]."
            
    elif tipo_mensaje == "Personalizado":
        texto = "Hola, vi el mensaje de WhatsApp y quiero consultar por [PRODUCTO / SERVICIO]."
        
    else:
        texto = "Hola, me contacto para realizar una consulta."
        
    # Transforma los espacios y caracteres especiales a formato URL (%20, etc.)
    msg_codificado = urllib.parse.quote(texto)
    return f"https://wa.me/{tel}?text={msg_codificado}"


# ==========================================
# EXTRACCIÓN Y LECTURA DE EXCEL
# ==========================================
def extraer_telefonos(row1, row2):
    phones = []
    
    def check_and_add(val):
        if pd.notna(val):
            val_str = str(val).strip()
            if sum(c.isdigit() for c in val_str) >= 6: 
                phones.append(val_str)
    
    for col in [5, 6, 7, 8, 9]:
        if col < len(row1): check_and_add(row1[col])
        
    if row2 is not None:
        for col in [2, 5, 6, 7, 8, 9]:
            if col < len(row2): check_and_add(row2[col])
            
    seen = set()
    return [x for x in phones if not (x in seen or seen.add(x))]

def leer_desde_excel():
    print(f"--- LEYENDO BASE DE DATOS ---")
    if not os.path.exists(ARCHIVO_EXCEL): 
        print(f"No se encontró el archivo: {ARCHIVO_EXCEL}")
        return []

    try:
        if ARCHIVO_EXCEL.endswith('.csv'):
            df = pd.read_csv(ARCHIVO_EXCEL, header=None, dtype=str)
        else:
            df = pd.read_excel(ARCHIVO_EXCEL, header=None, dtype=str)
        
        start_index = 0
        for idx, row in df.iterrows():
            val = str(row[0])
            if val.isdigit() and len(val) > 5:
                start_index = idx
                break
        
        data_rows = df.iloc[start_index:].reset_index(drop=True)
        registros = []
        i = 0
        
        while i < len(data_rows):
            row = data_rows.iloc[i]
            code = str(row[0])
            
            if pd.notna(code) and code.strip().isdigit() and len(code.strip()) > 3:
                cliente_dict = {
                    'Número de cliente': code.strip(),
                    'Cliente': str(row[1]).strip() if pd.notna(row[1]) else "Cliente Sin Nombre",
                    'Zona': '0', 
                    'Vendedor': '0' 
                }
                
                row2 = None
                
                if i + 1 < len(data_rows):
                    r2 = data_rows.iloc[i+1]
                    if pd.isna(r2[0]) or not str(r2[0]).strip().isdigit():
                        row2 = r2
                        if pd.notna(r2[1]): 
                            cliente_dict['Vendedor'] = str(r2[1]).strip()
                        
                        if i + 2 < len(data_rows):
                            r3 = data_rows.iloc[i+2]
                            if (pd.isna(r3[0]) or not str(r3[0]).strip()) and pd.notna(r3[2]) and str(r3[2]).strip().isdigit():
                                cliente_dict['Zona'] = str(r3[2]).strip()
                                i += 1 
                        i += 1 
                
                cliente_dict['Telefonos_Raw'] = extraer_telefonos(row, row2)
                registros.append(cliente_dict)
                
            i += 1
            
        print(f"Total clientes encontrados: {len(registros)}")
        return registros
        
    except Exception as e: 
        print(f"Error procesando el Excel: {e}")
        return []

# ==========================================
# VALIDACIÓN DE NÚMEROS (ESTRICTA)
# ==========================================
def formatear_telefono(numero):
    num_str = str(numero).strip().replace(" ", "").replace("-", "").replace(".", "")
    num_str = ''.join(filter(str.isdigit, num_str))
    
    if not num_str: return "" 
    if num_str.startswith("0"): num_str = num_str[1:] 
    if not num_str.startswith("54"): return f"549{num_str}"
        
    return num_str

def validar_formato_numero(numero_raw):
    numero_fmt = formatear_telefono(numero_raw)
    
    if not numero_fmt: return False, ""
    if len(numero_fmt) <= 11: return False, numero_fmt 
    if len(numero_fmt) > 15: return False, numero_fmt
        
    return True, numero_fmt

def conectar_y_procesar():
    global LISTA_OBSERVADOS
    LISTA_OBSERVADOS = [] 
    datos = leer_desde_excel()
    data_procesada = []
    
    for registro in datos:
        raw_list = registro.get('Telefonos_Raw', [])
        validos = []
        invalidos = []
        
        for raw_tel in raw_list:
            es_valido, tel_fmt = validar_formato_numero(raw_tel)
            if es_valido: validos.append(tel_fmt)
            else: invalidos.append(raw_tel)
            
        registro['Telefonos_Validos'] = validos
        registro['Telefonos_Invalidos'] = invalidos
        registro['Es_Valido'] = len(validos) > 0 
        
        if validos: registro['Tel_Formateado'] = " | ".join(validos)
        elif invalidos: registro['Tel_Formateado'] = invalidos[0]
        else: registro['Tel_Formateado'] = "Sin número"
            
        data_procesada.append(registro)
        if not registro['Es_Valido']: LISTA_OBSERVADOS.append(registro)

    return pd.DataFrame(data_procesada)

def revisar_numeros_problematicos():
    global LISTA_OBSERVADOS
    if not LISTA_OBSERVADOS: return "✅ Base limpia. Todos tienen al menos 1 número válido."
        
    txt = f"--- {len(LISTA_OBSERVADOS)} CLIENTES SIN NINGÚN NÚMERO VÁLIDO ---\n"
    for item in LISTA_OBSERVADOS:
        tels = item.get('Telefonos_Raw', [])
        tels_str = " | ".join(tels) if tels else "Sin números en Excel"
        txt += f"• {item['Cliente']} -> {tels_str}\n"
    return txt

def identificar_cols_productos(df): 
    return ['Sierras', 'Cuchillas', 'Mechas', 'Fresas', 'Cabezales']

def obtener_top_3_globales(df): 
    return ("Ofertas", "Herramientas", "Promociones")

# ==========================================
# LLAMADAS A LA API DE WHATSAPP META
# ==========================================
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

# ==========================================
# FUNCIONES DE ENVÍO POR TIPO DE PLANTILLA
# ==========================================
def enviar_promocion(tel, p1, p2, p3, link): 
    payload = {
        "messaging_product": "whatsapp", "to": tel, "type": "template", 
        "template": {"name": PLANTILLA_PROMOS, "language": {"code": "es"}, 
            "components": [{"type": "body", "parameters": [
                        {"type": "text", "text": str(p1)}, 
                        {"type": "text", "text": "Descuentos"}, 
                        {"type": "text", "text": str(p2)}, 
                        {"type": "text", "text": str(p3)}, 
                        {"type": "text", "text": str(link)}
                    ]}]}}
    return _enviar_request(payload)

def enviar_rescate(tel, nom, prod, link): 
    payload = {
        "messaging_product": "whatsapp", "to": tel, "type": "template", 
        "template": {"name": PLANTILLA_RESCATE, "language": {"code": "es"}, 
            "components": [{"type": "body", "parameters": [
                        {"type": "text", "text": str(nom)}, 
                        {"type": "text", "text": str(prod)}, 
                        {"type": "text", "text": str(link)}
                    ]}]}}
    return _enviar_request(payload)

def enviar_gira(tel, vend, p1, p2, link): 
    payload = {
        "messaging_product": "whatsapp", "to": tel, "type": "template", 
        "template": {"name": PLANTILLA_GIRA, "language": {"code": "es"}, 
            "components": [{"type": "body", "parameters": [
                        {"type": "text", "text": str(vend)}, 
                        {"type": "text", "text": str(p1)}, 
                        {"type": "text", "text": str(p2)}, 
                        {"type": "text", "text": str(link)}
                    ]}]}}
    return _enviar_request(payload)

def enviar_personalizado(tel, txt, media_id, link): 
    payload = {
        "messaging_product": "whatsapp", "to": tel, "type": "image", 
        "image": {"id": media_id, "caption": f"{txt}\n\n{link}"}
    }
    return _enviar_request(payload)

def enviar_novedades(tel, tipo_novedad, herramienta, link_wa):
    if tipo_novedad == "Ingresos":
        txt = f"Hola, tenemos nuevas incorporaciones de {herramienta}. Sabemos que te interesa por lo que queremos que seas una de las primeras personas en saberlo. Si querés más información entrá a este link: {link_wa}"
    else:
        txt = f"Hola, te informamos que pudimos obtener nuevamente stock de {herramienta}. Para conocer cuáles son los modelos entrá a este link: {link_wa}"
        
    payload = {
        "messaging_product": "whatsapp", "to": tel, "type": "text", "text": {"body": txt}
    }
    return _enviar_request(payload)