import schedule
import time
import psycopg2 
from psycopg2.extras import RealDictCursor
from twilio.rest import Client
import os
import requests


TWILIO_SID = os.environ.get('TWILIO_SID')
TWILIO_TOKEN = os.environ.get('TWILIO_TOKEN')
DATABASE_URL = os.environ.get('DATABASE_URL')
RENDER_URL = "https://bot-velez.onrender.com" 

client = Client(TWILIO_SID, TWILIO_TOKEN)

def revision_vencimiento():
    print("⏰ Iniciando revisión de vencimientos...")
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        query_fecha_venc = """
            SELECT nombre_producto, fecha_vencimiento 
            FROM producto
            WHERE fecha_vencimiento BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '62 days'
            AND fecha_vencimiento >= CURRENT_DATE
        """
        cursor.execute(query_fecha_venc)
        query_fecha = cursor.fetchall()

        productos_por_vencer = []
        for producto in query_fecha:
            texto = f"• {producto['nombre_producto']} vence el {producto['fecha_vencimiento']}"
            productos_por_vencer.append(texto)

        
        cursor.close()
        conn.close()

        if productos_por_vencer:
            print(f"📦 Se encontraron {len(productos_por_vencer)} productos. Enviando WhatsApp...")
            respuesta_final = "📢 *Reporte de Vencimientos:*\n\n" + "\n".join(productos_por_vencer)

            client.messages.create(
                from_='whatsapp:+14155238886',  
                body=respuesta_final,
                to='whatsapp:+5491158878312'   
            )
        else:
            print("✅ No hay productos por vencer hoy.")

    except Exception as e:
        print(f"❌ Error en revision_vencimiento: {e}")

def mantener_vivo():
    try:
        r = requests.get(RENDER_URL)
        print(f"📡 Keep-alive exitoso (Status: {r.status_code})")
    except Exception as e:
        print(f"❌ Falló el keep-alive: {e}")

schedule.every().day.at("10:00").do(revision_vencimiento)

schedule.every(10).minutes.do(mantener_vivo)

print("🚀 Script de alertas y keep-alive iniciado...")

mantener_vivo()

while True:
    schedule.run_pending()
    time.sleep(60) 





