import schedule
import time
import psycopg2 
from psycopg2.extras import RealDictCursor
from twilio.rest import Client
import os

TWILIO_SID = os.environ.get('TWILIO_SID')
TWILIO_TOKEN = os.environ.get('TWILIO_TOKEN')

client = Client(TWILIO_SID, TWILIO_TOKEN)


conn = psycopg2.connect(
        host="localhost",
        database="bot velez",
        user="postgres",
        password="4512",
        cursor_factory=RealDictCursor
)

cursor = conn.cursor()

def revision_vencimiento():
    
    query_fecha_venc = """SELECT nombre_producto,fecha_vencimiento FROM producto
                     WHERE 
                     fecha_vencimiento BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '62 days'
                     AND 
                     fecha_vencimiento >= CURRENT_DATE"""
    cursor.execute(query_fecha_venc)
    query_fecha = cursor.fetchall()

    productos_por_vencer = []

    for producto in query_fecha:
        print(f"   -> Procesando: {producto['nombre_producto']}")
        nombre_producto = producto['nombre_producto']
        fecha_producto = producto['fecha_vencimiento']

        texto = f"el producto {nombre_producto} vence el {fecha_producto}"

        productos_por_vencer.append(texto)

    cursor.close()
    conn.close()

    if len(productos_por_vencer) > 0:
        print(f"3. Intentando enviar {len(productos_por_vencer)} productos a Twilio...")
        respuesta = "reporte diario de los productos por vencer"
        cuerpo = "\n".join(productos_por_vencer) 
        respuesta_final = respuesta + cuerpo

        try:
            message = client.messages.create(
                from_='whatsapp:+14155238886',  
                body= respuesta_final,
                to='whatsapp:+5491158878312'   
            )
        except Exception as e:
            print(f"❌ Error al enviar WhatsApp: {e}")
            
schedule.every().day.at("10:00").do(revision_vencimiento)

while True:
    schedule.run_pending()
    time.sleep(1)