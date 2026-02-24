import pandas as pd
import requests
import os
import sys
import urllib.parse
import sqlite3
from datetime import datetime

# ==========================================
# CONFIGURACIÓN DE LA API DE WHATSAPP
# ==========================================
CLOUD_API_TOKEN = "TU_TOKEN_AQUI"
PHONE_NUMBER_ID = "TU_ID_TELEFONO_AQUI"
VERSION = "v17.0"
BASE_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}"

# ==========================================
# LÓGICA DE RUTAS Y BASE DE DATOS LOCAL
# ==========================================
def obtener_ruta_recurso(ruta_relativa):
    if getattr(sys, 'frozen', False):
        ruta_base = os.path.dirname(sys.executable)
        return os.path.join(ruta_base, ruta_relativa)
    else:
        ruta_base = os.path.dirname(os.path.abspath(__file__))
        ruta_directa = os.path.join(ruta_base, ruta_relativa)
        ruta_dist = os.path.join(ruta_base, "dist", ruta_relativa)
        if not os.path.exists(ruta_directa) and os.path.exists(ruta_dist):
            return ruta_dist
        return ruta_directa

ARCHIVO_DB = obtener_ruta_recurso("historial_campanas.db") 

def inicializar_db():
    try:
        conn = sqlite3.connect(ARCHIVO_DB)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanda_id TEXT,
                fecha_hora TEXT,
                cliente TEXT,
                telefono TEXT,
                vendedor_asignado TEXT,
                tipo_campana TEXT,
                herramienta TEXT,
                estado_envio TEXT,
                estado_tanda TEXT
            )
        ''')
        try: cursor.execute('ALTER TABLE historial ADD COLUMN tanda_id TEXT')
        except sqlite3.OperationalError: pass
        try: cursor.execute('ALTER TABLE historial ADD COLUMN estado_tanda TEXT')
        except sqlite3.OperationalError: pass
        conn.commit(); conn.close()
    except Exception as e: print(f"Error iniciando DB: {e}")

def registrar_envio_db(tanda_id, cliente, telefono, vendedor, tipo, herramienta, estado_individual):
    try:
        conn = sqlite3.connect(ARCHIVO_DB)
        cursor = conn.cursor()
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO historial (tanda_id, fecha_hora, cliente, telefono, vendedor_asignado, tipo_campana, herramienta, estado_envio, estado_tanda)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tanda_id, fecha, cliente, telefono, vendedor, tipo, herramienta, estado_individual, "PROCESANDO"))
        conn.commit(); conn.close()
    except Exception as e: print(f"Error guardando en DB: {e}")

def actualizar_estado_tanda(tanda_id, estado_final):
    try:
        conn = sqlite3.connect(ARCHIVO_DB)
        cursor = conn.cursor()
        cursor.execute('UPDATE historial SET estado_tanda = ? WHERE tanda_id = ?', (estado_final, tanda_id))
        conn.commit(); conn.close()
    except Exception as e: print(f"Error actualizando tanda: {e}")

def obtener_tandas_campanas():
    try:
        conn = sqlite3.connect(ARCHIVO_DB)
        df = pd.read_sql_query('''
            SELECT tanda_id, tipo_campana, vendedor_asignado, 
                   MIN(fecha_hora) as fecha_inicio, COUNT(id) as total_msgs,
                   MAX(estado_tanda) as estado_tanda, substr(fecha_hora, 1, 7) as mes
            FROM historial WHERE tanda_id IS NOT NULL
            GROUP BY tanda_id ORDER BY fecha_inicio DESC
        ''', conn)
        conn.close()
        return df.to_dict('records')
    except Exception as e: return []

def obtener_datos_reporte_por_tandas(tandas_seleccionadas):
    try:
        if not tandas_seleccionadas: return pd.DataFrame()
        conn = sqlite3.connect(ARCHIVO_DB)
        placeholders = ','.join(['?'] * len(tandas_seleccionadas))
        query = f"SELECT * FROM historial WHERE tanda_id IN ({placeholders}) ORDER BY id ASC"
        df = pd.read_sql_query(query, conn, params=tandas_seleccionadas)
        conn.close()
        return df
    except Exception as e: return pd.DataFrame()

# Nombres de las plantillas en Meta
PLANTILLA_PROMOS = "oferta_top_3"
PLANTILLA_RESCATE = "reactivacion_cliente"
PLANTILLA_GIRA = "aviso_visita_vendedor"
PLANTILLA_RECOTIZACION = "recotizacion_prospecto" 

# ==========================================
# BASE DE DATOS DE VENDEDORES
# ==========================================
DB_VENDEDORES = {"Valentín": ["5491145394279"], "Carlos": ["5491165630406"], "Emmanuel": ["5491157528428"]}
LISTA_OBSERVADOS = []

def obtener_telefono_vendedor(codigo_excel, indice_preferencia=0):
    codigo = str(codigo_excel).strip()
    if codigo == "0": return "5491145394279" if indice_preferencia == 0 else "5491165630406"
    elif codigo in ["1", "302", "1/302"]: return "5491157528428"
    else: return "5491145394279"

# ==========================================
# GENERADOR DE LINKS AUTOCOMPLETABLES
# ==========================================
def generar_link_whatsapp(tel, tipo_mensaje, datos_extra):
    if tipo_mensaje == "Promociones": texto = "Hola, vi las promociones por WhatsApp y busco el [CÓDIGO] de [TIPO DE PRODUCTO] para mi máquina."
    elif tipo_mensaje == "Rescate (Te extrañamos)": texto = "Hola, me llegó el mensaje. Necesito reponer stock de [TIPO DE HERRAMIENTA] para mi taller."
    elif tipo_mensaje == "Gira Vendedor": texto = f"Hola, vi que {datos_extra.get('vendedor_nombre', 'el vendedor')} va a estar por mi zona. Necesito encargar [CANTIDAD] de [TIPO DE PRODUCTO] para su visita."
    elif tipo_mensaje == "Novedades":
        if datos_extra.get('subtipo', '') == "Ingresos": texto = f"Hola, vi los nuevos ingresos de {datos_extra.get('herramienta', 'herramientas')}. Me interesa el modelo [CÓDIGO O MEDIDA] para cortar [MATERIAL]."
        else: texto = f"Hola, qué bueno que entró stock de {datos_extra.get('herramienta', 'herramientas')}. Necesito [CANTIDAD] unidades del código [CÓDIGO]."
    elif tipo_mensaje == "Recotización": texto = f"Hola Emmanuel, soy {datos_extra.get('cliente_nombre', '')}. Me gustaría recibir una recotización por {datos_extra.get('herramienta', 'un producto')}."
    elif tipo_mensaje == "Personalizado": texto = "Hola, vi el mensaje de WhatsApp y quiero consultar por [PRODUCTO / SERVICIO]."
    else: texto = "Hola, me contacto para realizar una consulta."
        
    msg_codificado = urllib.parse.quote(texto)
    return f"https://wa.me/{tel}?text={msg_codificado}"

# ==========================================
# LECTURA DE EXCEL Y VALIDACIÓN
# ==========================================
def extraer_telefonos(row1, row2):
    phones = []
    def check_and_add(val):
        if pd.notna(val):
            val_str = str(val).strip()
            if sum(c.isdigit() for c in val_str) >= 6: phones.append(val_str)
    for col in [5, 6, 7, 8, 9]:
        if col < len(row1): check_and_add(row1[col])
    if row2 is not None:
        for col in [2, 5, 6, 7, 8, 9]:
            if col < len(row2): check_and_add(row2[col])
    seen = set()
    return [x for x in phones if not (x in seen or seen.add(x))]

def leer_desde_excel(ruta_archivo, tipo_base):
    if not os.path.exists(ruta_archivo): return []
    try:
        if ruta_archivo.endswith('.csv'): df = pd.read_csv(ruta_archivo, header=None if tipo_base == "clientes" else 0, dtype=str)
        else: df = pd.read_excel(ruta_archivo, header=None if tipo_base == "clientes" else 0, dtype=str)
        
        registros = []
        if tipo_base == "prospectos":
            for _, row in df.iterrows():
                cliente_dict = {'Cliente': str(row.get('Nombres', 'Sin Nombre')).strip(), 'Telefonos_Raw': [str(row.get('Número', ''))], 'Vendedor': str(row.get('Vendedor', '5001')).strip(), 'Fav_Temp': str(row.get('Producto por el que consultó', '')).strip(), 'Zona': str(row.get('Producto por el que consultó', '')).strip()}
                registros.append(cliente_dict)
            return registros

        start_index = 0
        for idx, row in df.iterrows():
            if str(row[0]).isdigit() and len(str(row[0])) > 5:
                start_index = idx; break
        
        data_rows = df.iloc[start_index:].reset_index(drop=True)
        i = 0
        while i < len(data_rows):
            row = data_rows.iloc[i]
            code = str(row[0])
            if pd.notna(code) and code.strip().isdigit() and len(code.strip()) > 3:
                cliente_dict = {'Número de cliente': code.strip(), 'Cliente': str(row[1]).strip() if pd.notna(row[1]) else "Cliente Sin Nombre", 'Zona': '0', 'Vendedor': '0'}
                row2 = None
                if i + 1 < len(data_rows):
                    r2 = data_rows.iloc[i+1]
                    if pd.isna(r2[0]) or not str(r2[0]).strip().isdigit():
                        row2 = r2
                        if pd.notna(r2[1]): cliente_dict['Vendedor'] = str(r2[1]).strip()
                        if i + 2 < len(data_rows):
                            r3 = data_rows.iloc[i+2]
                            if (pd.isna(r3[0]) or not str(r3[0]).strip()) and pd.notna(r3[2]) and str(r3[2]).strip().isdigit():
                                cliente_dict['Zona'] = str(r3[2]).strip()
                                i += 1 
                        i += 1 
                cliente_dict['Telefonos_Raw'] = extraer_telefonos(row, row2)
                registros.append(cliente_dict)
            i += 1
        return registros
    except Exception as e: return []

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

def conectar_y_procesar(nombre_archivo, tipo_base):
    global LISTA_OBSERVADOS
    LISTA_OBSERVADOS = [] 
    ruta_final = obtener_ruta_recurso(nombre_archivo)
    datos = leer_desde_excel(ruta_final, tipo_base)
    data_procesada = []
    
    for registro in datos:
        raw_list = registro.get('Telefonos_Raw', [])
        validos, invalidos = [], []
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
    if not LISTA_OBSERVADOS: return "✅ Base limpia."
    txt = f"--- {len(LISTA_OBSERVADOS)} DESCARTADOS ---\n"
    for item in LISTA_OBSERVADOS:
        tels = item.get('Telefonos_Raw', [])
        tels_str = " | ".join(tels) if tels else "Sin números"
        txt += f"• {item['Cliente']} -> {tels_str}\n"
    return txt

def identificar_cols_productos(df): return ['Sierras', 'Cuchillas', 'Mechas', 'Fresas', 'Cabezales']

# ==========================================
# ENVÍOS API META Y CLASIFICACIÓN DE ERRORES
# ==========================================
def _enviar_request(data):
    try:
        headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}", "Content-Type": "application/json"}
        res = requests.post(f"{BASE_URL}/messages", headers=headers, json=data)
        if res.status_code == 200: return True, "OK"
        elif 400 <= res.status_code < 500: return False, "ERROR DEL CLIENTE"
        else: return False, "ERROR DEL SERVIDOR" 
    except Exception as e: return False, "ERROR DEL SERVIDOR"
    
def subir_imagen_whatsapp(ruta):
    try:
        headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}"}
        files = {'file': (os.path.basename(ruta), open(ruta, 'rb'), 'image/jpeg')}
        data = {'messaging_product': 'whatsapp'}
        res = requests.post(f"{BASE_URL}/media", headers=headers, files=files, data=data)
        if res.status_code == 200: return res.json()['id']
        return None
    except: return None

def enviar_promocion(tel, p1, p2, p3, link): 
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "template", "template": {"name": PLANTILLA_PROMOS, "language": {"code": "es"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": str(p1)}, {"type": "text", "text": str(p2)}, {"type": "text", "text": str(p3)}, {"type": "text", "text": str(link)}]}]}})

def enviar_rescate(tel, nom, prod, link): 
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "template", "template": {"name": PLANTILLA_RESCATE, "language": {"code": "es"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": str(nom)}, {"type": "text", "text": str(prod)}, {"type": "text", "text": str(link)}]}]}})

def enviar_gira(tel, vend, p1, p2, link): 
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "template", "template": {"name": PLANTILLA_GIRA, "language": {"code": "es"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": str(vend)}, {"type": "text", "text": str(p1)}, {"type": "text", "text": str(p2)}, {"type": "text", "text": str(link)}]}]}})

def enviar_recotizacion(tel, link): 
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "template", "template": {"name": PLANTILLA_RECOTIZACION, "language": {"code": "es"}, "components": [{"type": "body", "parameters": [{"type": "text", "text": str(link)}]}]}})

def enviar_personalizado(tel, caption_final, media_id): 
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "image", "image": {"id": media_id, "caption": str(caption_final)}})

def enviar_novedades(tel, tipo_novedad, herramienta, link_wa):
    txt = f"Hola, tenemos nuevas incorporaciones de {herramienta}. Si querés más información entrá a este link: {link_wa}" if tipo_novedad == "Ingresos" else f"Hola, te informamos que pudimos obtener nuevamente stock de {herramienta}. Para conocer cuáles son los modelos entrá a este link: {link_wa}"
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "text", "text": {"body": txt}})

def enviar_solo_imagen(tel, media_id):
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "image", "image": {"id": media_id}})