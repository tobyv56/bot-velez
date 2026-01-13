from fastapi import FastAPI, Form, Response
import psycopg2
from psycopg2.extras import RealDictCursor
from twilio.twiml.messaging_response import MessagingResponse
import os
import unicodedata

DATABASE_URL = os.environ.get('DATABASE_URL')

app = FastAPI()

def limpiar_texto(texto):
    if not texto: return ""
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto if unicodedata.category(c) != 'Mn')

@app.get("/")
async def inicio():
    return {"estado": "online", "mensaje": "Bot funcionando"}

@app.post("/webhook")
async def responder_whatsapp(Body: str = Form(...)):
    mensaje = Body.strip()
    partes = mensaje.split()
    if not partes: return Response(content=str(MessagingResponse()), media_type="application/xml")
    
    comando = partes[0].lower()
    resp_twilio = MessagingResponse()
    respuesta = ""

    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        if comando == "!producto":
            consulta = " ".join(partes[1:]).strip()
            datos = [p.strip() for p in consulta.split(",") if p.strip()]
            if len(datos) < 2:
                respuesta = "⚠️ Usá: !producto nombre, marca"
            else:
                n, m = limpiar_texto(datos[0]), limpiar_texto(datos[1])
                query = "SELECT * FROM producto WHERE nombre_producto ILIKE %s AND marca ILIKE %s LIMIT 1"
                cursor.execute(query, (f"%{n}%", f"%{m}%"))
                p = cursor.fetchone()
                if p:
                    respuesta = f"📦 *{p['nombre_producto'].title()}*\n💰 Precio: ${p['precio']}\n🛒 Stock: {p['stock']}\n🏷️ Marca: {p['marca'].upper()}"
                else:
                    respuesta = "❌ No encontrado."

        elif comando == "!productoc":
            cod = " ".join(partes[1:]).strip()
            cursor.execute("SELECT * FROM producto WHERE codigo_barra = %s LIMIT 1", (cod,))
            p = cursor.fetchone()
            if p:
                respuesta = f"📦 *{p['nombre_producto'].title()}*\n💰 Precio: ${p['precio']}\n🛒 Stock: {p['stock']}\n📅 Vence: {p['fecha_vencimiento']}"
            else:
                respuesta = "❌ Código no encontrado."

        elif comando == "!nuevo":
            datos = [p.strip() for p in mensaje.replace("!nuevo", "").split(",") if p.strip()]
            if len(datos) < 6:
                respuesta = "❌ Error. Usá: nombre, precio, fecha, marca, stock, código"
            else:
                n_p = limpiar_texto(datos[0])
                pre = float(datos[1])
                ven = datos[2]
                mar = limpiar_texto(datos[3])
                stk = int(datos[4])
                cod = datos[5]
                
                query = """INSERT INTO producto (nombre_producto, precio, fecha_vencimiento, stock, marca, codigo_barra) 
                           VALUES (%s, %s, %s, %s, %s, %s)"""
                cursor.execute(query, (n_p, pre, ven, stk, mar, cod))
                conn.commit()
                respuesta = f"✅ Guardado: {n_p.title()}"

        elif comando == "!actualizar":
            datos = [p.strip() for p in mensaje.replace("!actualizar", "").split(",") if p.strip()]
            if len(datos) != 4:
                respuesta = "⚠️ Usá: nombre, marca, campo, valor"
            else:
                n, m, campo, val = datos
                cursor.execute("SELECT id FROM producto WHERE nombre_producto ILIKE %s AND marca ILIKE %s LIMIT 1", (f"%{n}%", f"%{m}%"))
                res = cursor.fetchone()
                if res:
                    # Ojo: campo debe ser un nombre de columna real como 'precio' o 'stock'
                    cursor.execute(f"UPDATE producto SET {campo} = %s WHERE id = %s", (val, res['id']))
                    conn.commit()
                    respuesta = f"✅ {campo} actualizado."
                else:
                    respuesta = "❌ No encontrado."

        elif comando == "!":
            respuesta = respuesta = (
                "🤖 *Asistente de Stock*\n\n"
                "🔍 *!producto* nombre, marca\n"
                "🔢 *!productoc* código\n"
                "➕ *!nuevo* nombre, precio, fecha, marca, stock, código\n"
                "🔄 *!actualizar* nombre, marca, campo, valor"
            )
        
        else:
            respuesta = "❓ Comando no válido. Escribí *!* para ayuda."

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        respuesta = f"❌ Error: {str(e)}"
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    resp_twilio.message(respuesta)
    return Response(content=str(resp_twilio), media_type="application/xml")


