# NOMBRE DEL ARCHIVO: mainCode.py
import pandas as pd
import requests
import os
import urllib.parse

# --- CONFIGURACIÓN ---
CLOUD_API_TOKEN = "TU_TOKEN_AQUI"
PHONE_NUMBER_ID = "TU_ID_TELEFONO_AQUI"
VERSION = "v17.0"
BASE_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}"

# Nombres de las plantillas
PLANTILLA_PROMOS = "oferta_top_3"
PLANTILLA_RESCATE = "reactivacion_cliente"
PLANTILLA_GIRA = "aviso_visita_vendedor"

# --- BASE DE DATOS INTERNA (Diccionario) ---
# He introducido algunos números erróneos a propósito para probar la función (ej: numero corto, sin 54)
BASE_DE_DATOS = [
    {'Cliente': 'Valentin ', 'Número de cliente': 155334, 'Numero de Telefono': 1145394279, 'Zona': 4, 'Vendedor': 0, 'CUIT': '32-42557894-5', 'Sierras': 45, 'Cuchillas ': 12, 'Mechas': 34, 'Fresas': 10, 'Cabezales': 0},
    {'Cliente': 'Emmanuel (Error)', 'Número de cliente': 125588, 'Numero de Telefono': 11575, 'Zona': 12, 'Vendedor': 0, 'CUIT': '22-38665475-6', 'Sierras': 12, 'Cuchillas ': 46, 'Mechas': 58, 'Fresas': 8, 'Cabezales': 5},
    {'Cliente': 'Santiago ', 'Número de cliente': 235544, 'Numero de Telefono': 1134609057, 'Zona': 12, 'Vendedor': 1, 'CUIT': '43-42660379-9', 'Sierras': 34, 'Cuchillas ': 7, 'Mechas': 12, 'Fresas': 15, 'Cabezales': 2},
    {'Cliente': 'Ariel (Error)', 'Número de cliente': 105544, 'Numero de Telefono': "NumInvalido", 'Zona': 4, 'Vendedor': 302, 'CUIT': '33-32445668-6', 'Sierras': 43, 'Cuchillas ': 32, 'Mechas': 40, 'Fresas': 5, 'Cabezales': 4},
    {'Cliente': 'Carlos', 'Número de cliente': 94564, 'Numero de Telefono': 1165630406, 'Zona': 2, 'Vendedor': 44, 'CUIT': '19-18235648-6', 'Sierras': 56, 'Cuchillas ': 45, 'Mechas': 18, 'Fresas': 9, 'Cabezales': 0}
]

DB_VENDEDORES = {
    "0": ["5491145394279", "5491165630406"], "1": ["5491157528428"], "302": ["5491134609057"],
    "1/302": ["5491157528428", "5491134609057"], "02": ["5491145640940"], "15": ["5491157528427"],
    "40": ["5491157528427"], "15/40": ["5491157528427"], "04": ["5491156321012"], "44": ["5491156321012"],
    "04/44": ["5491156321012"], "09": ["5491153455274"], "05": ["5491164591316"], "16": ["5491145640831"],
    "03": ["5491168457778"]
}

# --- LISTAS EN MEMORIA PARA GESTIÓN DE ERRORES ---
# Aquí guardaremos temporalmente los que no pasan la validación
LISTA_OBSERVADOS = []

# --- FUNCIONES DE VALIDACIÓN Y PROCESAMIENTO ---

def formatear_telefono(numero):
    """Limpia el número y agrega 549 si es necesario."""
    num_str = str(numero).strip().replace(" ", "").replace("-", "").replace(".", "")
    if num_str.endswith("0") and "." in str(numero): num_str = num_str[:-2] # Fix floats
    
    if not num_str.isdigit(): return "" # Si tiene letras, devolver vacío
    
    if not num_str.startswith("54"):
        return f"549{num_str}"
    return num_str

def validar_formato_numero(numero_raw):
    """
    Verifica si un número es apto para envío (Lógica de negocio).
    Retorna: (Booleano, NumeroFormateado)
    """
    numero_fmt = formatear_telefono(numero_raw)
    
    # 1. Verificar que no esté vacío
    if not numero_fmt:
        return False, ""
    
    # 2. Verificar largo (Argentina suele ser 13 caracteres: 549 + 10 digitos)
    # Aceptamos entre 12 y 14 por seguridad.
    if len(numero_fmt) < 12 or len(numero_fmt) > 14:
        return False, numero_fmt
    
    return True, numero_fmt

def conectar_y_procesar():
    """
    Lee la base de datos, valida los números y devuelve un DataFrame 
    marcando cuáles son válidos y cuáles no.
    """
    global LISTA_OBSERVADOS
    LISTA_OBSERVADOS = [] # Reiniciar lista
    
    data_procesada = []
    
    for registro in BASE_DE_DATOS:
        raw_tel = registro.get('Numero de Telefono', '')
        es_valido, tel_fmt = validar_formato_numero(raw_tel)
        
        # Agregamos flags al registro para el frontend
        registro_copia = registro.copy()
        registro_copia['Es_Valido'] = es_valido
        registro_copia['Tel_Formateado'] = tel_fmt
        
        # Normalizar columnas
        registro_copia = {k.strip(): v for k, v in registro_copia.items()}
        
        data_procesada.append(registro_copia)
        
        if not es_valido:
            LISTA_OBSERVADOS.append(registro_copia)

    df = pd.DataFrame(data_procesada)
    return df

def revisar_numeros_problematicos():
    """
    Función llamada por el botón 'Verificar Números'.
    Analiza la lista de observados y genera un reporte.
    """
    global LISTA_OBSERVADOS
    
    if not LISTA_OBSERVADOS:
        return "No hay números observados para verificar."
    
    reporte = "--- REPORTE DE NÚMEROS OBSERVADOS ---\n"
    recuperados = 0
    
    for item in LISTA_OBSERVADOS:
        nombre = item.get('Cliente', 'Desc.')
        raw = item.get('Numero de Telefono', '')
        
        # Aquí podrías intentar una lógica de corrección automática más compleja
        # Por ahora, diagnosticamos por qué falló
        es_valido, fmt = validar_formato_numero(raw)
        
        estado = "❌ IRRECUPERABLE"
        razon = "Formato desconocido"
        
        if not str(raw).strip():
            razon = "Vacío"
        elif any(c.isalpha() for c in str(raw)):
            razon = "Contiene letras"
        elif len(fmt) < 12:
            razon = f"Muy corto ({len(fmt)} dígitos)"
            
        reporte += f"• {nombre}: {raw} -> {razon}\n"
    
    reporte += f"\nTotal observados: {len(LISTA_OBSERVADOS)}"
    return reporte

# --- HELPERS DE DATOS ---

def identificar_cols_productos(df):
    cols_cliente = ['Cliente', 'Número de cliente', 'Numero de Telefono', 'CUIT', 'Ubicación', 'Zona', 'Vendedor', 'Es_Valido', 'Tel_Formateado', 'Fav_Temp', 'Sec_Temp']
    return [col for col in df.columns if col not in cols_cliente and col != '']

def generar_texto_footer(telefono_vendedor, productos_ofrecidos):
    mensaje_cliente = f"Hola, me interesan las promociones sobre: {productos_ofrecidos}"
    mensaje_encoded = urllib.parse.quote(mensaje_cliente)
    return f"Si te interesa saber más sobre estas promociones entra al https://wa.me/{telefono_vendedor}?text={mensaje_encoded}"

# --- CÁLCULOS ---

def obtener_top_3_globales(df):
    # Solo calculamos sobre los válidos para no sesgar con datos basura
    df_validos = df[df['Es_Valido'] == True]
    if df_validos.empty: return ("A", "B", "C")
    
    cols = identificar_cols_productos(df_validos)
    df_calc = df_validos.copy()
    for col in cols:
        df_calc[col] = pd.to_numeric(df_calc[col], errors='coerce').fillna(0)
    ventas = df_calc[cols].sum().sort_values(ascending=False)
    top = ventas.index.tolist()
    return (str(top[0]) if len(top)>0 else "A", str(top[1]) if len(top)>1 else "B", str(top[2]) if len(top)>2 else "C")

def obtener_top_personalizados(row, cols_productos):
    try:
        datos = row[cols_productos]
        datos = pd.to_numeric(datos, errors='coerce').fillna(0)
        ranking = datos.sort_values(ascending=False)
        comprados = ranking[ranking > 0].index.tolist()
        p1 = str(comprados[0]) if len(comprados) > 0 else "nuestros productos"
        p2 = str(comprados[1]) if len(comprados) > 1 else "nuestras ofertas"
        return p1, p2
    except:
        return "nuestros productos", "ofertas"

# --- ENVÍO API ---

def _enviar_request(data):
    headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}", "Content-Type": "application/json"}
    try:
        response = requests.post(f"{BASE_URL}/messages", headers=headers, json=data)
        if response.status_code == 200:
            return True, "OK"
        else:
            return False, f"API Error: {response.text}"
    except Exception as e:
        return False, str(e)

def subir_imagen_whatsapp(ruta_archivo):
    url = f"{BASE_URL}/media"
    headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}"}
    try:
        files = {'file': (os.path.basename(ruta_archivo), open(ruta_archivo, 'rb'), 'image/jpeg')}
        data = {'messaging_product': 'whatsapp'}
        response = requests.post(url, headers=headers, files=files, data=data)
        if response.status_code == 200: return response.json()['id']
        return None
    except: return None

# --- TIPOS DE ENVÍO ---

def enviar_promocion(tel, p1, p2, p3, footer_link):
    data = {
        "messaging_product": "whatsapp", "to": tel, "type": "template",
        "template": {
            "name": PLANTILLA_PROMOS, "language": {"code": "es"},
            "components": [{"type": "body", "parameters": [
                {"type": "text", "text": str(p1)}, {"type": "text", "text": "Descuentos"}, 
                {"type": "text", "text": str(p2)}, {"type": "text", "text": str(p3)},
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
                {"type": "text", "text": str(nombre)}, {"type": "text", "text": str(prod_fav)},
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
                {"type": "text", "text": str(vendedor)}, {"type": "text", "text": str(p1)}, 
                {"type": "text", "text": str(p2)}, {"type": "text", "text": str(footer_link)}
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