import pandas as pd
import requests
import os
import sys
import urllib.parse
import sqlite3
import re
from datetime import datetime, timedelta
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request 

# ==========================================
# CONFIGURACIÓN DE LA API DE WHATSAPP Y SHEETS
# ==========================================
CLOUD_API_TOKEN = "EAAUkLctR4q0BQ8mcvr7YtqEacloCMCDHq1AY8VE0gc0ZBIIZBboTSCSEIEOQQKbNtfD7i0HwqiJvnd9FZCdH27rlBVsOXer1Qmlx3N5GAMhO6FmRNmYwOuxCKcJAgqo9Xy8IwtiQcZCFcuJ2fIMQnO7mPvBjEYrAgCDs7eMyn1lZAT7aDaJ8SKG5I1cp7yAZDZD"
PHONE_NUMBER_ID = "1041050652417644"
VERSION = "v17.0"
BASE_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}"
URL_SERVIDOR_RENDER = "https://woodtools-webhook.onrender.com"

NOMBRE_HOJA = "Base de datos wt"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# ==========================================
# LÓGICA DE CONTROL DEL BOT INTELIGENTE
# ==========================================
def obtener_estado_bot_nube():
    """Consulta al servidor de Render el estado actual del bot"""
    try:
        res = requests.get(f"{URL_SERVIDOR_RENDER}/estado_bot", timeout=10)
        if res.status_code == 200:
            return res.json()
        return None
    except:
        return None

def cambiar_estado_bot_nube(nuevo_estado):
    """Envía la orden al servidor para cambiar el modo ('AUTO', 'ON', 'OFF')"""
    try:
        res = requests.post(f"{URL_SERVIDOR_RENDER}/estado_bot", 
                            json={"configuracion": nuevo_estado}, timeout=10)
        return res.status_code == 200
    except:
        return False

# ==========================================
# LÓGICA DE RUTAS Y BASE DE DATOS LOCAL
# ==========================================
def hora_arg():
    """Devuelve la hora actual en Argentina (UTC-3)"""
    return datetime.utcnow() - timedelta(hours=3)

def obtener_ruta_recurso(ruta_relativa):
    if getattr(sys, 'frozen', False):
        ruta_base = sys._MEIPASS
    else:
        ruta_base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(ruta_base, ruta_relativa)

def obtener_ruta_persistente(nombre_archivo):
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), nombre_archivo)
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_archivo)

ARCHIVO_DB = obtener_ruta_persistente("historial_campanas.db") 
ARCHIVO_TOKEN = obtener_ruta_persistente("token.json")

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
        try: cursor.execute('ALTER TABLE historial ADD COLUMN total_base INTEGER DEFAULT 0')
        except sqlite3.OperationalError: pass
        conn.commit(); conn.close()
    except Exception as e: print(f"Error iniciando DB: {e}")

def registrar_envio_db(tanda_id, cliente, telefono, vendedor, tipo, herramienta, estado_individual, total_base=0):
    try:
        conn = sqlite3.connect(ARCHIVO_DB)
        cursor = conn.cursor()
        fecha = hora_arg().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute('''
            INSERT INTO historial (tanda_id, fecha_hora, cliente, telefono, vendedor_asignado, tipo_campana, herramienta, estado_envio, estado_tanda, total_base)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (tanda_id, fecha, cliente, telefono, vendedor, tipo, herramienta, estado_individual, "PROCESANDO", total_base))
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
                   MAX(estado_tanda) as estado_tanda, substr(fecha_hora, 1, 7) as mes,
                   MAX(total_base) as total_base
            FROM historial WHERE tanda_id IS NOT NULL
            GROUP BY tanda_id ORDER BY fecha_inicio DESC
        ''', conn)
        conn.close()
        return df.to_dict('records')
    except Exception as e: return []

def obtener_datos_reporte_por_tandas(lista_tandas):
    if not lista_tandas: return pd.DataFrame()
    try:
        conn = sqlite3.connect(ARCHIVO_DB)
        placeholders = ','.join('?' * len(lista_tandas))
        query = f"SELECT * FROM historial WHERE tanda_id IN ({placeholders}) ORDER BY fecha_hora ASC"
        df = pd.read_sql_query(query, conn, params=lista_tandas)
        conn.close()
        return df
    except Exception as e:
        print(f"Error armando el reporte detallado: {e}")
        return pd.DataFrame()

# ==========================================
# PLANTILLAS Y VENDEDORES
# ==========================================
PLANTILLA_PROMOS = "oferta_top_3"
PLANTILLA_RESCATE = "reactivacion_cliente"
PLANTILLA_GIRA = "aviso_visita_vendedor"
PLANTILLA_RECOTIZACION = "recotizacion_prospecto" 
PLANTILLA_NOVEDADES = "aviso_novedades_wt"
PLANTILLA_PERSONALIZADO = "contacto_personalizado_wt"

DB_VENDEDORES = {
    "Valentín": ["5491145394279"], 
    "Carlos": ["5491165630406"], 
    "Emmanuel": ["5491157528428"],
    "Ariel": ["5491134811771"],
    "Roberto": ["5491164591316"],
    "Nicolas": ["5491157528427"],
    "Ezequiel": ["5491153455274"],
    "Alan": ["5491156321012"],
    "Luis": ["5491168457778"]
}

REVENDEDORES_CODIGOS = {
    "4652": "Abalos Esteban",
    "2253": "Acinar",
    "14285": "Acosta Hernan Dario Herrajes tafildel valle",
    "7195": "Afilacion Soriano",
    "4373": "Afipar",
    "1889": "Aldo Rodruguez /Idecort",
    "1789": "Alonso Matias",
    "11858": "ALENKA GRACIELA",
    "10344": "Arbelaiz",
    "11699": "ANTONIJEVIC IVAN DANIEL",
    "9239": "Barnes problemático pagar",
    "12394": "Battaller Estebam",
    "11785": "Bevacqua Manuel",
    "12430": "BertoLazzi Alejandra",
    "905": "Bidinost",
    "9931": "BIMETAL",
    "9288": "Blanco Maq. (Staffolani Roman)",
    "11611": "COOP.DE TRAB EL CARANDA LIM F.",
    "1558": "Jose Blas Pinamar",
    "879": "Ciganoto",
    "11775": "Braga Alicia ex lucich (6412)",
    "214": "setefratti",
    "10679": "BREDICE MAURO DANIEL",
    "12515": "Bhoor AIA",
    "10428": "Bruni Marcos",
    "7933": "Bulonera Torcuato",
    "94": "Cabello Susana (Af del sur Damian)",
    "2514": "Capovilla Ernesto",
    "906": "Catavorello",
    "1538": "Chiappa Sierras",
    "11268": "DELBRE",
    "3640": "TECNO L.D.",
    "6626": "Dartamani Carlos",
    "14639": "DUERO AFILADO( Cordoba)",
    "2633": "Ellemberger` Edgar",
    "6421": "Fisicaro Mauricio",
    "2123": "Forti Oscar (Bruni)",
    "9541": "Fraile Julio",
    "228": "FREMECH Ariel Gomez",
    "14181": "Fernadez Jorge Luis El Rey de la melamina",
    "2691": "Grodnienski Max (Abraham Maq.)",
    "1092": "IMAD S.R.L.",
    "9645": "Javier Haedo",
    "5789": "Keil Gerardo vendedor 32",
    "7986": "Kranjac Hnos (afilador)",
    "4446": "Kurtz Adolfo",
    "8907": "La casa de las Herramientas",
    "14791": "LEPRI MARIANO",
    "3044": "lagomarcino",
    "1369": "Mancardi(afilador)",
    "841": "Maq Caseros",
    "5809": "Maq Picotto Mario",
    "12043": "MACHENA SRL DI CESARE",
    "8966": "Martiren Ruben(glorioso 10622)",
    "138": "Met Picotto (edgardo)",
    "6494": "Monica- Todo Filo",
    "1214": "MULTIPLACAS SA",
    "5677": "Moscuzza Daniel",
    "2569": "Mutilva",
    "691": "NEA GESTION S.R.L.",
    "7851": "Palavecino",
    "820": "Paoletti",
    "2591": "Piccini Martin (Afilados Postai)",
    "8467": "Riquelme Luis (bariloche)",
    "7317": "Romero Guadalberto/Garcia H",
    "15904": "EDMUNDO Y ANDRES LACONI",
    "136": "Rupper Hugo",
    "8848": "S.P.M",
    "9251": "Santana",
    "12100": "Sergio martinez",
    "10966": "SERVIMAD Ciccioli",
    "5005": "Sierras Andinas(afilador y revendedor)",
    "1676": "Sierras del Parana",
    "13328": "Silva Nicolas Martin",
    "5207": "Talleres Ciudadela",
    "3138": "Taurus",
    "4257": "TODO AFILADO VIZOSO",
    "9360": "Torres Graciela",
    "12631": "VADI PLAC",
    "3023": "Vila",
    "4682": "Waintrub",
    "3730": "Wegiers Angel (Multiplacas)",
    "7216": "Zaninovic",
    "9766": "Zapico Sebastian",
    "9220": "Zubizarreta Luis Alberto(afilador)",
    "14481": "MAGARO SA (FERRETERIA)"
}

REVENDEDORES_NOMBRES = [
    "BIRBA LEANDRO JORGE",
    "Dutra Alexis Uruguay",
    "Garcia Joaquin",
    "IFRAN",
    "Mastro Mauro hermanos",
    "Oscar de casa nova",
    "Sergio Pastre",
    "PAIVA ESTEBAN",
    "VIDELA RAUL ALEJANDRO"
]

LISTA_OBSERVADOS = []

def obtener_telefono_vendedor(codigo_excel, indice_preferencia=0):
    codigo = str(codigo_excel).strip()
    if codigo == "0": return "5491145394279" if indice_preferencia == 0 else "5491165630406"
    elif codigo in ["1", "302", "1/302"]: return "5491157528428"
    else: return "5491145394279"

def generar_link_whatsapp(tel, tipo_mensaje, datos_extra):
    if tipo_mensaje == "Promociones": 
        producto = datos_extra.get('herramienta', 'sierras circulares')
        texto = f"Hola, me llegó el mensaje con la promoción de {producto} y quiero más información."
    elif tipo_mensaje == "Rescate (Te extrañamos)": 
        texto = "Hola, me llegó el mensaje de WhatsApp. Me gustaría ver el catálogo actualizado para reponer stock en mi taller."
    elif tipo_mensaje == "Gira Vendedor": 
        texto = f"Hola, vi que {datos_extra.get('vendedor_nombre', 'el vendedor')} va a estar por mi zona. Me gustaría coordinar una visita para hacer un pedido."
    elif tipo_mensaje == "Novedades": 
        texto = "Hola, vi el mensaje sobre los nuevos ingresos de stock y me gustaría conocer los modelos disponibles."
    elif tipo_mensaje == "Recotización": 
        texto = f"Hola, soy {datos_extra.get('cliente_nombre', 'un cliente')}. Me gustaría recibir una recotización actualizada, por favor."
    elif tipo_mensaje == "Personalizado": 
        texto = "Hola, vi el mensaje de WhatsApp y me gustaría hacer una consulta."
    else: 
        texto = "Hola, me contacto para realizar una consulta."
        
    msg_codificado = urllib.parse.quote(texto)
    return f"https://api.whatsapp.com/send?phone={tel}&text={msg_codificado}"

# ==========================================
# LECTOR DESDE GOOGLE SHEETS Y RENOVACIÓN DE TOKEN
# ==========================================
def obtener_credenciales():
    creds = None
    if os.path.exists(ARCHIVO_TOKEN):
        creds = Credentials.from_authorized_user_file(ARCHIVO_TOKEN, SCOPES)
        
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try: creds.refresh(Request())
            except Exception: creds = None
                
        if not creds or not creds.valid:
            ruta_creds = obtener_ruta_recurso("credenciales.json")
            if not os.path.exists(ruta_creds): return None
            flow = InstalledAppFlow.from_client_secrets_file(ruta_creds, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(ARCHIVO_TOKEN, 'w') as token:
            token.write(creds.to_json())
            
    return creds

def aplicar_correcciones_texto(texto):
    t = str(texto).strip()
    t = re.sub(r'(?i)0a', '0-A', t)
    t = re.sub(r'(?i)0b', '0-B', t)
    return t

def obtener_pestanas_disponibles():
    try:
        creds = obtener_credenciales()
        if not creds: return ["Base de datos wt"]
        gc = gspread.authorize(creds)
        sh = gc.open(NOMBRE_HOJA)
        return [ws.title for ws in sh.worksheets()]
    except Exception: return ["Hoja 1"]

def leer_desde_google_sheets(nombre_pestana=""):
    try:
        creds = obtener_credenciales()
        if not creds: return []
        gc = gspread.authorize(creds)
        sh = gc.open(NOMBRE_HOJA)
        
        if nombre_pestana and nombre_pestana.lower() not in ["clientes", "prospectos"]:
            try: ws = sh.worksheet(nombre_pestana)
            except gspread.exceptions.WorksheetNotFound: ws = sh.sheet1
        else: ws = sh.sheet1 
        
        datos_brutos = ws.get_all_values()
        if len(datos_brutos) < 2: return []
            
        headers_brutos = datos_brutos[0] 
        headers = [h.strip() if h.strip() != "" else f"Col_Vacia_{i}" for i, h in enumerate(headers_brutos)]
        
        es_formato_complejo = 'Primer número' in headers
        data = datos_brutos[1:] if len(datos_brutos) > 1 else []
        
        df = pd.DataFrame(data, columns=headers)
        df = df.fillna("")
        registros = []
        
        for _, row in df.iterrows():
            tels_raw = []
            if es_formato_complejo:
                for col in ['Primer número', 'Segundo número', 'Tercer número', 'Cuarto número', 'Quinto número']:
                    if col in row and str(row[col]).strip():
                        val_str_limpio = str(row[col]).strip().replace(" ", "").replace("-", "")
                        val_num = ''.join(filter(str.isdigit, val_str_limpio))
                        if not val_num.startswith("000") and val_num: tels_raw.append(val_str_limpio)
                cliente_nom = str(row.get('Nombre', 'Cliente Sin Nombre')).strip() or "Cliente Sin Nombre"
            else:
                col_tel = 'Numero de Telefono' if 'Numero de Telefono' in row else ('Número' if 'Número' in row else ('Teléfono' if 'Teléfono' in row else None))
                if col_tel and col_tel in row:
                    num_raw_limpio = str(row[col_tel]).strip().replace(" ", "").replace("-", "")
                    num_only = ''.join(filter(str.isdigit, num_raw_limpio))
                    if not num_only.startswith("000") and num_only: tels_raw.append(num_raw_limpio)
                cliente_nom = str(row.get('Cliente', row.get('Nombres', row.get('Nombre', 'Sin Nombre')))).strip() or "Sin Nombre"
            
            cod_cliente = aplicar_correcciones_texto(row.get('Código de cliente', row.get('Número de cliente', ''))).strip()
            
            # --- FILTRO DE REVENDEDORES ---
            es_revendedor = False
            nombre_lower = cliente_nom.lower()
            
            # 1. Filtro por Código de Cliente
            if cod_cliente and cod_cliente in REVENDEDORES_CODIGOS:
                es_revendedor = True
                
            # 2. Filtro infalible por etiqueta explícita en el nombre
            elif "(reventa)" in nombre_lower or "reventa" in nombre_lower or "revendedor" in nombre_lower:
                es_revendedor = True
                
            else:
                # 3. Buscar en la lista aislada de nombres
                for rev_nombre in REVENDEDORES_NOMBRES:
                    if rev_nombre.lower() in nombre_lower:
                        es_revendedor = True
                        break
                        
                # 4. Buscar cruzado en los valores del diccionario
                if not es_revendedor:
                    for cod, nombre_dict in REVENDEDORES_CODIGOS.items():
                        palabra_clave_dict = nombre_dict.split(" ")[0].lower()
                        if len(palabra_clave_dict) > 3 and palabra_clave_dict in nombre_lower:
                            es_revendedor = True
                            break
            # ------------------------------
            
            if cliente_nom != "Sin Nombre" and cliente_nom != "Cliente Sin Nombre":
                registros.append({
                    'Código de cliente': cod_cliente,
                    'Cliente': cliente_nom,
                    'Zona': aplicar_correcciones_texto(row.get('Zona del cliente', row.get('Zona', '0'))) or '0',
                    'Vendedor': str(row.get('Vendedor', '0')).strip() or '0',
                    'Telefonos_Raw': tels_raw,
                    'Fav_Temp': str(row.get('Producto por el que consultó', '')).strip(),
                    'Es_Revendedor': es_revendedor
                })
        return registros
    except Exception: return []

# ==========================================
# LÓGICA DE DETECCIÓN DE TELÉFONOS
# ==========================================
def formatear_telefono(numero_raw):
    num_str = str(numero_raw).replace(" ", "").replace("-", "")
    num_str = ''.join(filter(str.isdigit, num_str))
    
    if not num_str: return ""
    if num_str.startswith("549") and len(num_str) == 13: return num_str
    if num_str.startswith("54") and len(num_str) == 12: return "549" + num_str[2:]
    if num_str.startswith("549"): num_str = num_str[3:]
    elif num_str.startswith("54"): num_str = num_str[2:]
    if num_str.startswith("0"): num_str = num_str[1:]
    
    match_15 = re.match(r'^([1-3]\d{1,3})15(\d{6,8})$', num_str)
    if match_15:
        area = match_15.group(1); resto = match_15.group(2)
        if len(area) + len(resto) == 10: return f"549{area}{resto}"
        
    if num_str.startswith("15") and len(num_str) == 10: return f"54911{num_str[2:]}"
    if len(num_str) == 8 and num_str[0] in "234567": return f"54911{num_str}"
    if len(num_str) == 10: return f"549{num_str}"
    
    return num_str

def validar_formato_numero(numero_raw):
    numero_fmt = formatear_telefono(numero_raw)
    if not numero_fmt: return False, ""
    if re.match(r'^549\d{10}$', numero_fmt): return True, numero_fmt
    return False, numero_fmt

def conectar_y_procesar(nombre_pestana=""):
    global LISTA_OBSERVADOS
    LISTA_OBSERVADOS = [] 
    datos = leer_desde_google_sheets(nombre_pestana)
    data_procesada = []
    
    for registro in datos:
        raw_list = registro.get('Telefonos_Raw', [])
        validos, invalidos = [], []
        
        for raw_tel in raw_list:
            es_valido, tel_fmt = validar_formato_numero(raw_tel)
            if es_valido:
                if tel_fmt not in validos:
                    validos.append(tel_fmt)
            else:
                if raw_tel not in invalidos:
                    invalidos.append(raw_tel)
            
        # Si es revendedor, forzamos que todos sus números vayan a la lista de inválidos
        # Esto hace que visualmente figure en la tabla pero se marque como DESCARTADO
        if registro.get('Es_Revendedor', False):
            invalidos.extend(validos)
            validos = []
            registro['Es_Valido'] = False
            registro['Tel_Formateado'] = "Descartado (Revendedor)"
        else:
            registro['Es_Valido'] = len(validos) > 0 
            if validos: registro['Tel_Formateado'] = " | ".join(validos)
            elif invalidos: registro['Tel_Formateado'] = invalidos[0]
            else: registro['Tel_Formateado'] = "Sin número"

        registro['Telefonos_Validos'] = validos
        registro['Telefonos_Invalidos'] = invalidos
        
        data_procesada.append(registro)
        if not registro['Es_Valido']: LISTA_OBSERVADOS.append(registro)
        
    return pd.DataFrame(data_procesada)

def revisar_numeros_problematicos():
    global LISTA_OBSERVADOS
    if not LISTA_OBSERVADOS: return "✅ Base limpia."
    txt = f"--- {len(LISTA_OBSERVADOS)} DESCARTADOS ---\n"
    for item in LISTA_OBSERVADOS:
        tels = item.get('Telefonos_Raw', [])
        txt += f"• {item['Cliente']} -> {' | '.join(tels) if tels else 'Sin números'}\n"
    return txt

def identificar_cols_productos(df): return ['Sierras', 'Cuchillas', 'Mechas', 'Fresas', 'Cabezales']

def _enviar_request(data):
    try:
        headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}", "Content-Type": "application/json"}
        res = requests.post(f"{BASE_URL}/messages", headers=headers, json=data)
        if res.status_code == 200: return True, "OK"
        elif 400 <= res.status_code < 500: 
            print("ERROR META:", res.json()) 
            return False, "ERROR DEL CLIENTE"
        else: return False, "ERROR DEL SERVIDOR" 
    except Exception: return False, "ERROR DEL SERVIDOR"
    
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
# MAGIA DE BOTONES: EXTRACTOR DE ENLACE DINÁMICO
# ==========================================
def extraer_sufijo_dinamico(link_completo):
    base = "https://woodtools-webhook.onrender.com/wa/"
    if str(link_completo).startswith(base):
        return link_completo[len(base):]
    return link_completo

# ==========================================
# FUNCIONES DE ENVÍO DE PLANTILLAS
# ==========================================
def enviar_promocion(tel, nombre, producto_promo, link, media_id): 
    dynamic_url = extraer_sufijo_dinamico(link)
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": PLANTILLA_PROMOS, "language": {"code": "es"}, "components": [
                {"type": "header", "parameters": [{"type": "image", "image": {"id": media_id}}]},
                {"type": "body", "parameters": [
                    {"type": "text", "text": str(nombre)}, 
                    {"type": "text", "text": str(producto_promo)}
                ]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [
                    {"type": "text", "text": dynamic_url}
                ]}
            ]
        }
    })

def enviar_rescate(tel, nom, prod, link, media_id): 
    dynamic_url = extraer_sufijo_dinamico(link)
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": PLANTILLA_RESCATE, "language": {"code": "es"}, "components": [
                {"type": "header", "parameters": [{"type": "image", "image": {"id": media_id}}]},
                {"type": "body", "parameters": [
                    {"type": "text", "text": str(nom)}, 
                    {"type": "text", "text": str(prod)}
                ]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [
                    {"type": "text", "text": dynamic_url}
                ]}
            ]
        }
    })

def enviar_gira(tel, vend, link): 
    dynamic_url = extraer_sufijo_dinamico(link)
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": PLANTILLA_GIRA, "language": {"code": "es"}, "components": [
                {"type": "body", "parameters": [
                    {"type": "text", "text": str(vend)}
                ]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [
                    {"type": "text", "text": dynamic_url}
                ]}
            ]
        }
    })

def enviar_novedades(tel, tipo_novedad, herramienta, link_wa, media_id):
    frase = "Acaban de ingresar nuevos modelos." if tipo_novedad == "Nuevo producto" else "Pudimos reponer el stock que esperabas."
    dynamic_url = extraer_sufijo_dinamico(link_wa)
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": PLANTILLA_NOVEDADES, "language": {"code": "es"}, "components": [
                {"type": "header", "parameters": [{"type": "image", "image": {"id": media_id}}]},
                {"type": "body", "parameters": [
                    {"type": "text", "text": str(herramienta)},
                    {"type": "text", "text": str(frase)}
                ]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [
                    {"type": "text", "text": dynamic_url}
                ]}
            ]
        }
    })

def enviar_recotizacion(tel, link): 
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "template", "template": {"name": PLANTILLA_RECOTIZACION, "language": {"code": "es"}, "components": [
        {"type": "body", "parameters": [
            {"type": "text", "text": str(link)}
        ]}
    ]}})

def enviar_personalizado(tel, caption_final, media_id): 
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": PLANTILLA_PERSONALIZADO, "language": {"code": "es"}, "components": [
                {"type": "header", "parameters": [{"type": "image", "image": {"id": media_id}}]},
                {"type": "body", "parameters": [{"type": "text", "text": str(caption_final)[:1000]}]}
            ]
        }
    })

def enviar_solo_imagen(tel, media_id):
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "image", "image": {"id": media_id}})