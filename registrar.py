import os
import requests

# Script manual para registrar el número en la Cloud API (verificación en dos pasos).
# Los datos sensibles se leen de variables de entorno para NO dejarlos en el código:
#   WT_CLOUD_API_TOKEN  -> token de acceso de Meta
#   WT_PHONE_NUMBER_ID  -> ID del número (por defecto el de siempre)
#   WT_REGISTER_PIN     -> PIN de 6 dígitos que vos elegís (anotalo)
TOKEN = os.environ.get("WT_CLOUD_API_TOKEN", "")
PHONE_ID = os.environ.get("WT_PHONE_NUMBER_ID", "1041050652417644")
PIN_SEGURIDAD = os.environ.get("WT_REGISTER_PIN", "")

if not TOKEN or not PIN_SEGURIDAD:
    print("Faltan variables de entorno. Definí WT_CLOUD_API_TOKEN y WT_REGISTER_PIN antes de correr este script.")
    raise SystemExit(1)

url = f"https://graph.facebook.com/v21.0/{PHONE_ID}/register"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}
data = {
    "messaging_product": "whatsapp",
    "pin": PIN_SEGURIDAD
}

print("Enviando orden de registro a Meta...")
response = requests.post(url, headers=headers, json=data, timeout=30)
print("Respuesta de Meta:", response.json())
