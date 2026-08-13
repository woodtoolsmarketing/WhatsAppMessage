import pandas as pd
import requests
import os
import sys
import urllib.parse
import sqlite3
import re
import time
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

# Versión de esta app y repo público desde donde se descargan las actualizaciones
VERSION_APP = "12.3"
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

def _enviar_request(data):
    """VERSIÓN ANTI-CONGELAMIENTO: Registra errores sin colapsar la app."""
    try:
        headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}", "Content-Type": "application/json"}
        res = requests.post(f"{BASE_URL}/messages", headers=headers, json=data, timeout=10)
        
        time.sleep(1) # Pausa obligatoria para no ahogar la API
        
        if res.status_code == 200: 
            return True, "OK"
        elif 400 <= res.status_code < 500: 
            log_error(f"META RECHAZÓ EL MENSAJE (Error 4xx): {res.text}") 
            return False, "ERROR DEL CLIENTE"
        else: 
            log_error(f"ERROR DEL SERVIDOR META (Error 5xx): {res.text}")
            return False, "ERROR DEL SERVIDOR" 
    except requests.exceptions.Timeout:
        log_error("Timeout: Meta tardó demasiado en responder.")
        return False, "TIMEOUT"
    except Exception as e: 
        log_error(f"Falla de red crítica: {str(e)}")
        return False, "ERROR DE RED O SERVIDOR"
    
def subir_imagen_whatsapp(ruta):
    try:
        headers = {"Authorization": f"Bearer {CLOUD_API_TOKEN}"}
        files = {'file': (os.path.basename(ruta), open(ruta, 'rb'), 'image/jpeg')}
        data = {'messaging_product': 'whatsapp'}
        res = requests.post(f"{BASE_URL}/media", headers=headers, files=files, data=data, timeout=20)
        if res.status_code == 200: return res.json()['id']
        log_error(f"Error subiendo imagen a Meta: {res.text}")
        return None
    except Exception as e:
        log_error(f"Excepción subiendo imagen: {e}")
        return None

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

def enviar_personalizado(tel, caption_final, link_completo, media_id): 
    dynamic_url = extraer_sufijo_dinamico(link_completo)
    return _enviar_request({
        "messaging_product": "whatsapp", "to": tel, "type": "template", "template": {
            "name": PLANTILLA_PERSONALIZADO, "language": {"code": "es"}, "components": [
                {"type": "header", "parameters": [{"type": "image", "image": {"id": media_id}}]},
                {"type": "body", "parameters": [{"type": "text", "text": str(caption_final)[:1000]}]},
                {"type": "button", "sub_type": "url", "index": "0", "parameters": [{"type": "text", "text": dynamic_url}]}
            ]
        }
    })

def enviar_solo_imagen(tel, media_id):
    return _enviar_request({"messaging_product": "whatsapp", "to": tel, "type": "image", "image": {"id": media_id}})