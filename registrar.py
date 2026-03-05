import requests

# 1. PEGÁ ACÁ TU TOKEN LARGO DE SIEMPRE
TOKEN = "EAAUkLctR4q0BQ8mcvr7YtqEacloCMCDHq1AY8VE0gc0ZBIIZBboTSCSEIEOQQKbNtfD7i0HwqiJvnd9FZCdH27rlBVsOXer1Qmlx3N5GAMhO6FmRNmYwOuxCKcJAgqo9Xy8IwtiQcZCFcuJ2fIMQnO7mPvBjEYrAgCDs7eMyn1lZAT7aDaJ8SKG5I1cp7yAZDZD" 

# 2. ESTE ES TU ID CORRECTO
PHONE_ID = "1041050652417644"

# 3. INVENTÁ UN PIN DE 6 NÚMEROS (Anotalo por ahí por las dudas)
PIN_SEGURIDAD = "532026" 

url = f"https://graph.facebook.com/v17.0/{PHONE_ID}/register"
headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}
data = {
    "messaging_product": "whatsapp",
    "pin": PIN_SEGURIDAD
}

print("Enviando orden de registro a Meta...")
response = requests.post(url, headers=headers, json=data)
print("Respuesta de Meta:", response.json())