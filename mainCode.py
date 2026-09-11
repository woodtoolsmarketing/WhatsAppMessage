import pandas as pd
import requests
import os
import sys
import urllib.parse
import sqlite3
import re
import time
import mimetypes
import subprocess
from datetime import datetime, timedelta
import gspread
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request 

# ==========================================
# CONFIGURACIÓN DE LA API DE WHATSAPP Y SHEETS
# ==========================================
# El token se puede pasar por variable de entorno WT_CLOUD_API_TOKEN para no
# dejarlo en el código (recomendado). Si no está, usa el valor de abajo.
# IMPORTANTE: este token estuvo expuesto en el repo; conviene rotarlo en Meta.
CLOUD_API_TOKEN = os.environ.get("WT_CLOUD_API_TOKEN", "EAAUkLctR4q0BQ8mcvr7YtqEacloCMCDHq1AY8VE0gc0ZBIIZBboTSCSEIEOQQKbNtfD7i0HwqiJvnd9FZCdH27rlBVsOXer1Qmlx3N5GAMhO6FmRNmYwOuxCKcJAgqo9Xy8IwtiQcZCFcuJ2fIMQnO7mPvBjEYrAgCDs7eMyn1lZAT7aDaJ8SKG5I1cp7yAZDZD")
PHONE_NUMBER_ID = os.environ.get("WT_PHONE_NUMBER_ID", "1041050652417644")
VERSION = "v21.0"
BASE_URL = f"https://graph.facebook.com/{VERSION}/{PHONE_NUMBER_ID}"
URL_SERVIDOR_RENDER = "https://woodtools-webhook.onrender.com"

# Versión de esta app y repo público desde donde se descargan las actualizaciones
VERSION_APP = "12.8"
GITHUB_REPO = "woodtoolsmarketing/WhatsAppMessage"

NOMBRE_HOJA = "Base de datos wt"
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# ==========================================
# LÓGICA DE CONTROL DEL BOT INTELIGENTE Y RUTAS
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
ARCHIVO_LOG = obtener_ruta_persistente("errores_log.txt")

# NUEVA FUNCIÓN ANTI-CONGELAMIENTO
def log_error(mensaje):
    """Guarda los errores en un archivo en vez de usar print() que congela los .exe"""
    try:
        with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{hora_arg().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}\n")
    except:
        pass

def obtener_estado_bot_nube():
    try:
        res = requests.get(f"{URL_SERVIDOR_RENDER}/estado_bot", timeout=10)
        if res.status_code == 200:
            return res.json()
        return None
    except:
        return None

def cambiar_estado_bot_nube(nuevo_estado):
    try:
        res = requests.post(f"{URL_SERVIDOR_RENDER}/estado_bot",
                            json={"configuracion": nuevo_estado}, timeout=10)
        return res.status_code == 200
    except:
        return False

def consultar_servidor(ruta, timeout=30):
    """GET genérico al servidor Render para ver qué responde. Devuelve un dict:
    {ok: bool, status: int, texto: str, json: obj|None}. Nunca lanza excepción."""
    ruta = "/" + str(ruta).lstrip("/")
    try:
        res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}{ruta}",
                           timeout=timeout, headers={"User-Agent": "GestorWT"})
        try:
            js = res.json()
        except Exception:
            js = None
        return {"ok": res.status_code == 200, "status": res.status_code, "texto": res.text, "json": js}
    except Exception as e:
        return {"ok": False, "status": 0, "texto": f"Error de conexión: {e}", "json": None}

# ==========================================
# AUTO-ACTUALIZACIÓN (desde GitHub Releases)
# ==========================================
def _partes_version(v):
    """Convierte 'v12.1' o '12.1.0' en una lista de enteros [12, 1, 0]."""
    return [int(x) for x in re.findall(r'\d+', v or "")]

def _es_mas_nueva(remota, local):
    """True si 'remota' es una versión posterior a 'local' (compara número a número)."""
    r, l = _partes_version(remota), _partes_version(local)
    n = max(len(r), len(l))
    r += [0] * (n - len(r))
    l += [0] * (n - len(l))
    return r > l

def obtener_actualizacion_disponible():
    """Consulta el último release publicado en GitHub. Si hay una versión MÁS NUEVA
    que la instalada, devuelve {'version', 'url', 'notas'}; si no hay o falla, None."""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        res = requests.get(url, timeout=10, headers={"Accept": "application/vnd.github+json"})
        if res.status_code != 200:
            return None
        data = res.json()
        tag = data.get("tag_name", "")
        if not _es_mas_nueva(tag, VERSION_APP):
            return None
        # Busca el primer archivo .exe adjunto al release (el instalador)
        url_exe = None
        for asset in data.get("assets", []):
            if str(asset.get("name", "")).lower().endswith(".exe"):
                url_exe = asset.get("browser_download_url")
                break
        if not url_exe:
            return None
        return {"version": tag.lstrip("vV"), "url": url_exe, "notas": data.get("body", "") or ""}
    except Exception as e:
        log_error(f"Error consultando actualizaciones: {e}")
        return None

def descargar_instalador(url, callback_progreso=None):
    """Descarga el setup.exe a la carpeta temporal del sistema. Devuelve la ruta local
    o None si falla. callback_progreso(bajado, total) reporta el avance en bytes."""
    import tempfile
    try:
        destino = os.path.join(tempfile.gettempdir(), "WoodTools_Actualizacion_Setup.exe")
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            bajado = 0
            with open(destino, "wb") as f:
                for chunk in r.iter_content(chunk_size=262144):
                    if not chunk:
                        continue
                    f.write(chunk)
                    bajado += len(chunk)
                    if callback_progreso:
                        callback_progreso(bajado, total)
        return destino
    except Exception as e:
        log_error(f"Error descargando la actualización: {e}")
        return None

# ==========================================
# BASE DE DATOS LOCAL
# ==========================================
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
    except Exception as e: log_error(f"Error iniciando DB: {e}")

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
    except Exception as e: log_error(f"Error guardando en DB: {e}")

def actualizar_estado_tanda(tanda_id, estado_final):
    try:
        conn = sqlite3.connect(ARCHIVO_DB)
        cursor = conn.cursor()
        cursor.execute('UPDATE historial SET estado_tanda = ? WHERE tanda_id = ?', (estado_final, tanda_id))
        conn.commit(); conn.close()
    except Exception as e: log_error(f"Error actualizando tanda: {e}")

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
        log_error(f"Error armando el reporte detallado: {e}")
        return pd.DataFrame()

# ==========================================
# PLANTILLAS Y VENDEDORES
# ==========================================
PLANTILLA_PROMOS = "oferta_top_3"
PLANTILLA_RESCATE = "reactivacion_cliente"
PLANTILLA_GIRA = "aviso_visita_vendedor"
PLANTILLA_RECOTIZACION = "recotizacion_prospecto" 
PLANTILLA_NOVEDADES = "aviso_novedades_wt"
PLANTILLA_PERSONALIZADO = "personalizado_2"

# Plantillas equivalentes con ENCABEZADO DE VIDEO. Hay que crearlas en Meta y que las
# apruebe; el nombre debe coincidir EXACTO con el de la plantilla aprobada. Se pueden
# sobreescribir por variable de entorno por si les ponés otro nombre al crearlas.
PLANTILLA_PROMOS_VIDEO = os.environ.get("WT_PLANTILLA_PROMOS_VIDEO", "oferta_top_3_video")
PLANTILLA_RESCATE_VIDEO = os.environ.get("WT_PLANTILLA_RESCATE_VIDEO", "reactivacion_cliente_video")
PLANTILLA_NOVEDADES_VIDEO = os.environ.get("WT_PLANTILLA_NOVEDADES_VIDEO", "aviso_novedades_wt_video")
PLANTILLA_PERSONALIZADO_VIDEO = os.environ.get("WT_PLANTILLA_PERSONALIZADO_VIDEO", "personalizado_2_video")

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

# ==========================================
# LÓGICA DE DETECCIÓN DE TELÉFONOS (MOVIDA ARRIBA PARA FILTROS)
# ==========================================
def formatear_telefono(numero_raw):
    num_str = str(numero_raw).replace(" ", "").replace("-", "")
    num_str = ''.join(filter(str.isdigit, num_str))
    
    if not num_str: return ""
    if num_str.startswith("549") and len(num_str) == 13: return num_str
    if num_str.startswith("54") and not num_str.startswith("549") and len(num_str) == 12: return "549" + num_str[2:]
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
    # 549 + código de área + número. Los códigos de área argentinos empiezan con 1, 2 o 3
    # (11, 2xx, 3xx): así se rechazan números imposibles como "5499..." que antes pasaban la
    # validación y Meta devolvía como "no entregable".
    if re.match(r'^549[123]\d{9}$', numero_fmt): return True, numero_fmt
    return False, numero_fmt

# ==========================================
# COSTO DE CAMPAÑA + CRUCE CON HISTORIAL REAL DE META
# ==========================================
# Meta cobra una "conversación de marketing" por destinatario (ventana de 24 h). Este es el
# valor aproximado por chat en USD; se ajusta acá si Meta cambia la tarifa de Argentina.
COSTO_POR_CHAT_USD = 0.06

def calcular_costo_campana(cantidad_chats):
    """Costo estimado en USD de enviar a `cantidad_chats` destinatarios (1 conversación c/u)."""
    try:
        return round(max(0, int(cantidad_chats)) * COSTO_POR_CHAT_USD, 2)
    except Exception:
        return 0.0

def clave_10_digitos(numero):
    """Últimos 10 dígitos de un número: la clave para cruzarlo con el historial del servidor."""
    d = ''.join(filter(str.isdigit, str(numero)))
    return d[-10:] if len(d) >= 10 else d

def obtener_estado_numeros_nube(timeout=30):
    """Cruza contra el HISTORIAL REAL de Meta guardado en el servidor (endpoint /numeros_estado).
    Devuelve (entregados, fallidos):
      - entregados: set con los últimos 10 dígitos de los números que YA se entregaron/leyeron.
      - fallidos: dict {ultimos_10: {'codigo':..., 'titulo':...}} de los que Meta NO pudo entregar.
    Si el servidor no responde, devuelve (set(), {}) sin romper la app."""
    try:
        res = requests.get(f"{URL_SERVIDOR_RENDER.rstrip('/')}/numeros_estado", timeout=timeout)
        if res.status_code == 200:
            data = res.json() or {}
            return set(data.get("entregados", []) or []), (data.get("fallidos", {}) or {})
    except Exception as e:
        log_error(f"No se pudo consultar /numeros_estado: {e}")
    return set(), {}

# ==========================================
# LISTA NEGRA: FILTRO SÚPER AGRESIVO (Sufijos)
# ==========================================
NUMEROS_DESCARTADOS_STR = "3764456633-3764420402-3815773623-1553435836-5491142596405-5493434260308-5491166334158-5493782413709-5491147493121-5491154251121-5492364450824-5491142813861-5491142963860-5491153872222-5491157655862-1154050797-1126446881-5491142520944-5491142591920-5491144994231-5493414850586-5493414027107-5493464493941-15687979-910394903-5493704342539-5493704827455-02254484189-5491158079933-5491121943744-1553024913-15629744-5493471423090-5493758401827-5493758457227-5491142082790-5493456420485-5491136564978-5491147412488-154035917-1552262796-15494747-5493456420587-5493456425121-5493456407212-5491144992948-5491146935000-5491142620738-5492284585872-5493564424444-5491132524577-5491142701611-5491132524568-3541520902-5493514727689-5493515115009-5492984428507-5492984291750-5493515122708-5493514701559-5491160189996-5491142083212-1558783465-3855385790-5491144045153-5491145812526-5491145842070-5493756481198-5493764642470-5491146535716-5491160928067-5493772635537-5493447470682-5491148137853-5491136440291-5491142544007-5491142549017-5491155062683-81213301730-5491143510462-5491144440644-37524941610-15694529-299418756-5492994426721-5492994583044-5492215682014-5492284443347-5491160800008-5493764426849-5493414623087-261424667-5491140537938-5491142676040-5493415501731-5493417787265-5491147304400-5492914888008-5491147466782-5493454903125-5491136278164-5493751423105-5491161972833-155635302-5492614521113-5492615154076-5493424608997-5493424308844-5492944428600-3454272913-155283942-1164393869-15555463-15690838-1553978911-5492364635567-5492494316964-5499249443885-5492944610381-5492944499227-5493434840824-5493436207265-5493436227540-1131137846-5491146536397-25124402244-5492914550352-5492914120493-5492915225300-3751303003-5491141800506-5491145260205-5491145399399-5491134811771-5491130976000-5491134005566-5491145640940-5491158431455-5491134609120-5491145640831-5491156321012-5491157528428-5491164591316-5491168457778-5491157528427-5491165630406-5491145394279-5493816706400-5491153452371-5491121827274-5491165667851-5491134334827-5491131761431-5491133336664-5491164318838-5491164395047-5491134665339-5491157626801-5491131165563-549114008550-5492954676654-5492235358961-5492234227603-5492234227695-5493795170186-5491159538732-5491135484075-5491127674082-5491133375369-5491130713856-5491150605633-5491140764666-5491154711348"

DESCARTADOS_RAW = set(NUMEROS_DESCARTADOS_STR.split("-"))
DESCARTADOS_SUFIJOS = set()

# Pre-computamos todas las terminaciones posibles de la lista negra
# Esto garantiza que si Excel tiene "549..." y la lista negra no (o viceversa), siempre haya match.
for num in DESCARTADOS_RAW:
    n_limpio = ''.join(filter(str.isdigit, num))
    if not n_limpio: continue
    DESCARTADOS_SUFIJOS.add(n_limpio)
    if len(n_limpio) >= 10: DESCARTADOS_SUFIJOS.add(n_limpio[-10:])
    if len(n_limpio) >= 9:  DESCARTADOS_SUFIJOS.add(n_limpio[-9:])
    if len(n_limpio) >= 8:  DESCARTADOS_SUFIJOS.add(n_limpio[-8:])

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
            
            # --- NUEVO FILTRO DE DESCARTES (MULTI-COINCIDENCIA AGRESIVA) ---
            es_revendedor = False
            
            for tel_raw in tels_raw:
                tel_limpio = ''.join(filter(str.isdigit, tel_raw))
                if not tel_limpio: continue
                
                # Pasamos el número del Excel por la función que arregla los +549 y los 15
                tel_fmt = formatear_telefono(tel_limpio)
                
                # Desglosamos el número en todas sus versiones posibles (completo, últimos 10, últimos 9, últimos 8)
                sufijos_a_revisar = [tel_limpio, tel_fmt]
                if len(tel_limpio) >= 10: sufijos_a_revisar.append(tel_limpio[-10:])
                if len(tel_limpio) >= 9:  sufijos_a_revisar.append(tel_limpio[-9:])
                if len(tel_limpio) >= 8:  sufijos_a_revisar.append(tel_limpio[-8:])
                
                if len(tel_fmt) >= 10: sufijos_a_revisar.append(tel_fmt[-10:])
                if len(tel_fmt) >= 9:  sufijos_a_revisar.append(tel_fmt[-9:])
                if len(tel_fmt) >= 8:  sufijos_a_revisar.append(tel_fmt[-8:])
                
                # Si CUALQUIERA de las versiones de este número coincide con la lista negra, queda descartado
                if any(suf in DESCARTADOS_SUFIJOS for suf in sufijos_a_revisar if suf):
                    es_revendedor = True
                    break
            # ----------------------------------------------------------------
            
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
            
        if registro.get('Es_Revendedor', False):
            invalidos.extend(validos)
            validos = []
            registro['Es_Valido'] = False
            registro['Tel_Formateado'] = "Descartado (Lista Negra)"
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

# Antes TODO error 4xx era "ERROR DEL CLIENTE": no se podía saber si el número no existía,
# si Meta nos frenó por el tope diario, si la plantilla estaba pausada, etc.
LIMITE_24H = "LÍMITE 24H DE META"

def _clasificar_error_meta(res):
    """Convierte la respuesta 4xx de Meta en un estado legible que incluye el código de error."""
    try:
        err = (res.json() or {}).get("error", {}) or {}
    except Exception:
        err = {}
    code = err.get("code")
    msg = str(err.get("message") or err.get("error_user_msg") or "")[:80]
    if code == 131056: return f"{LIMITE_24H} (131056)"                       # tope de conversaciones/24h
    if code in (130429, 131048): return f"RATE LIMIT ({code})"               # demasiados msgs por segundo
    if code == 131026: return "NO ENTREGABLE: número no está en WhatsApp (131026)"
    if code == 131047: return "FUERA DE VENTANA 24H (131047)"
    if code == 131049: return "BLOQUEADO POR META: tope de marketing al usuario (131049)"
    if code in (131009, 100): return f"NÚMERO/PARÁMETRO INVÁLIDO ({code}) {msg}"
    if code in (132000, 132001, 132012, 132015, 132016): return f"PLANTILLA: {msg} ({code})"
    if code in (131031, 131042): return f"CUENTA/PAGO: {msg} ({code})"
    return f"ERROR DEL CLIENTE ({code}) {msg}" if code else "ERROR DEL CLIENTE"

def debe_frenar_campana(tipo_error):
    """True si seguir enviando es inútil: Meta frenó la cuenta por el tope diario."""
    return isinstance(tipo_error, str) and tipo_error.startswith(LIMITE_24H)

def es_error_de_servidor(tipo_error):
    """Errores de red/servidor/rate-limit (transitorios) vs. rechazos del cliente (definitivos)."""
    t = str(tipo_error or "")
    return t in ("ERROR DEL SERVIDOR", "TIMEOUT", "ERROR DE RED O SERVIDOR", "ERROR DESCONOCIDO") or t.startswith("RATE LIMIT")

def _enviar_request(data, reintentos=2):
    """VERSIÓN ANTI-CONGELAMIENTO: registra errores sin colapsar la app.
    Reintenta ante rate-limit (429) y errores de servidor (5xx) con espera creciente."""
    headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}", "Content-Type": "application/json"}
    for intento in range(reintentos + 1):
        try:
            res = requests.post(f"{BASE_URL}/messages", headers=headers, json=data, timeout=15)

            time.sleep(1)  # Pausa obligatoria para no ahogar la API

            if res.status_code == 200:
                return True, "OK"

            if res.status_code == 429:
                log_error(f"RATE LIMIT (429) de Meta, intento {intento + 1}: {res.text}")
                if intento < reintentos:
                    time.sleep(5 * (intento + 1))
                    continue
                return False, "RATE LIMIT"

            if 500 <= res.status_code < 600:
                log_error(f"ERROR DEL SERVIDOR META (5xx), intento {intento + 1}: {res.text}")
                if intento < reintentos:
                    time.sleep(3 * (intento + 1))
                    continue
                return False, "ERROR DEL SERVIDOR"

            if 400 <= res.status_code < 500:
                log_error(f"META RECHAZÓ EL MENSAJE (Error {res.status_code}): {res.text}")
                estado = _clasificar_error_meta(res)
                # Rate limit de throughput (130429/131048): sí vale la pena reintentar.
                if estado.startswith("RATE LIMIT") and intento < reintentos:
                    time.sleep(5 * (intento + 1))
                    continue
                return False, estado

            log_error(f"Respuesta inesperada de Meta ({res.status_code}): {res.text}")
            return False, f"ERROR {res.status_code}"

        except requests.exceptions.Timeout:
            log_error(f"Timeout: Meta tardó demasiado en responder (intento {intento + 1}).")
            if intento < reintentos:
                continue
            return False, "TIMEOUT"
        except Exception as e:
            log_error(f"Falla de red crítica: {str(e)}")
            if intento < reintentos:
                time.sleep(2)
                continue
            return False, "ERROR DE RED O SERVIDOR"
    return False, "ERROR DESCONOCIDO"
    
# Tipos de archivo aceptados y su MIME. Antes se subía TODO como 'image/jpeg',
# lo que hacía que Meta rechazara PNG y videos.
MIME_POR_EXTENSION = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp",
    ".mp4": "video/mp4", ".3gp": "video/3gpp", ".3gpp": "video/3gpp",
}

def _detectar_mime(ruta):
    ext = os.path.splitext(str(ruta))[1].lower()
    if ext in MIME_POR_EXTENSION:
        return MIME_POR_EXTENSION[ext]
    adivinado, _ = mimetypes.guess_type(str(ruta))
    return adivinado or "application/octet-stream"

def es_video(ruta):
    """True si la ruta apunta a un archivo de video (por extensión)."""
    return _detectar_mime(ruta).startswith("video/")

def subir_media_whatsapp(ruta):
    """Sube una imagen O un video a Meta y devuelve el media_id (o None).
    Detecta el MIME por la extensión y cierra el archivo correctamente."""
    try:
        mime = _detectar_mime(ruta)
        headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}"}
        data = {'messaging_product': 'whatsapp'}
        # timeout amplio: los videos pesan más que una foto
        with open(ruta, 'rb') as fh:
            files = {'file': (os.path.basename(ruta), fh, mime)}
            res = requests.post(f"{BASE_URL}/media", headers=headers, files=files, data=data, timeout=120)
        if res.status_code == 200:
            return res.json().get('id')
        log_error(f"Error subiendo media a Meta ({mime}): {res.text}")
        return None
    except Exception as e:
        log_error(f"Excepción subiendo media: {e}")
        return None

def subir_imagen_whatsapp(ruta):
    # Compatibilidad: delega en subir_media_whatsapp (soporta imagen y video).
    return subir_media_whatsapp(ruta)

# ==========================================
# COMPRESIÓN DE VIDEO (para respetar el límite de 16 MB de la Cloud API)
# ==========================================
# En Windows, evita que se abra una ventana de consola al llamar a ffmpeg desde el .exe.
_SIN_VENTANA = 0x08000000 if os.name == "nt" else 0

def _ruta_ffmpeg():
    """Ruta al ffmpeg empaquetado (imageio-ffmpeg, que trae libx264). None si no está."""
    # 1) En el .exe (PyInstaller): buscar el binario en la carpeta empaquetada.
    try:
        if getattr(sys, 'frozen', False):
            import glob
            base = os.path.join(sys._MEIPASS, 'imageio_ffmpeg', 'binaries')
            cands = glob.glob(os.path.join(base, 'ffmpeg-*'))
            if cands:
                return cands[0]
    except Exception:
        pass
    # 2) En desarrollo (o si el paso 1 no lo encontró): via el paquete.
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:
        log_error(f"ffmpeg no disponible para comprimir video: {e}")
        return None

def _duracion_video(ffmpeg, ruta):
    """Duración en segundos, parseando la salida de 'ffmpeg -i'."""
    try:
        p = subprocess.run([ffmpeg, "-i", ruta], capture_output=True, text=True,
                           creationflags=_SIN_VENTANA)
        salida = (p.stderr or "") + (p.stdout or "")
        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", salida)
        if not m:
            return None
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    except Exception:
        return None

def comprimir_video(ruta, limite_mb=16):
    """Si el video supera limite_mb, lo recomprime (H.264 + AAC) para que quede por debajo
    y devuelve la ruta del archivo comprimido (en la carpeta temporal). Si ya está por debajo
    o no se puede comprimir, devuelve la ruta original."""
    try:
        tam_mb = os.path.getsize(ruta) / (1024 * 1024)
    except Exception:
        return ruta
    if tam_mb <= limite_mb:
        return ruta
    ffmpeg = _ruta_ffmpeg()
    if not ffmpeg:
        return ruta  # sin ffmpeg no hay nada que hacer; Meta lo rechazará con aviso claro
    try:
        import tempfile
        dur = _duracion_video(ffmpeg, ruta) or 60.0
        objetivo_mb = max(3, limite_mb - 2)  # margen de seguridad bajo el límite
        total_kbps = (objetivo_mb * 8 * 1024) / dur
        video_kbps = int(max(300, total_kbps - 128))  # 128 kbps para el audio
        salida = os.path.join(tempfile.gettempdir(), "wt_video_comprimido.mp4")
        cmd = [ffmpeg, "-y", "-i", ruta,
               "-c:v", "libx264", "-preset", "veryfast",
               "-b:v", f"{video_kbps}k",
               "-maxrate", f"{int(video_kbps * 1.3)}k",
               "-bufsize", f"{int(video_kbps * 2)}k",
               "-c:a", "aac", "-b:a", "128k",
               "-movflags", "+faststart", salida]
        subprocess.run(cmd, capture_output=True, creationflags=_SIN_VENTANA, timeout=600)
        if os.path.exists(salida) and os.path.getsize(salida) > 0:
            return salida
        return ruta
    except Exception as e:
        log_error(f"Error comprimiendo video: {e}")
        return ruta

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
def _componente_header_media(media_id, es_video=False):
    """Componente 'header' con imagen o video, segun corresponda."""
    tipo = "video" if es_video else "image"
    return {"type": "header", "parameters": [{"type": tipo, tipo: {"id": media_id}}]}

def enviar_promocion(tel, nombre, producto_promo, link, media_id, es_video=False):
    dynamic_url = extraer_sufijo_dinamico(link)
    nombre_plantilla = PLANTILLA_PROMOS_VIDEO if es_video else PLANTILLA_PROMOS
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": nombre_plantilla, "language": {"code": "es"}, "components": [
                _componente_header_media(media_id, es_video),
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

def enviar_rescate(tel, nom, prod, link, media_id, es_video=False):
    dynamic_url = extraer_sufijo_dinamico(link)
    nombre_plantilla = PLANTILLA_RESCATE_VIDEO if es_video else PLANTILLA_RESCATE
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": nombre_plantilla, "language": {"code": "es"}, "components": [
                _componente_header_media(media_id, es_video),
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

def enviar_novedades(tel, tipo_novedad, herramienta, link_wa, media_id, es_video=False):
    frase = "Acaban de ingresar nuevos modelos." if tipo_novedad == "Nuevo producto" else "Pudimos reponer el stock que esperabas."
    dynamic_url = extraer_sufijo_dinamico(link_wa)
    nombre_plantilla = PLANTILLA_NOVEDADES_VIDEO if es_video else PLANTILLA_NOVEDADES
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": nombre_plantilla, "language": {"code": "es"}, "components": [
                _componente_header_media(media_id, es_video),
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

def enviar_personalizado(tel, caption_final, link_completo, media_id, es_video=False):
    dynamic_url = extraer_sufijo_dinamico(link_completo)
    nombre_plantilla = PLANTILLA_PERSONALIZADO_VIDEO if es_video else PLANTILLA_PERSONALIZADO
    # Meta rechaza parámetros de plantilla con saltos de línea, tabs o >4 espacios:
    # colapsamos todos los espacios en blanco a uno solo.
    texto_limpio = re.sub(r'\s+', ' ', str(caption_final)).strip()[:1000]
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": nombre_plantilla, "language": {"code": "es"}, "components": [
                _componente_header_media(media_id, es_video),
                {"type": "body", "parameters": [{"type": "text", "text": texto_limpio}]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": dynamic_url}]}
            ]
        }
    })

def enviar_solo_imagen(tel, media_id):
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "image", "image": {"id": media_id}})