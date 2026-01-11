from fastapi import FastAPI, HTTPException, status, Form, Response
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from twilio.twiml.messaging_response import MessagingResponse
import os

DATABASE_URL = os.environ.get('DATABASE_URL')

app = FastAPI()

@app.get("/")
async def inicio():
    return {"estado": "online", "mensaje": "Bot de Stock funcionando"}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)


@app.post("/webhook")
async def responder_whatsapp(Body: str = Form(...)):
    mensaje = Body.strip()
    if not mensaje: 
        return Response(content=str(MessagingResponse()), media_type="application/xml")
    
    partes = mensaje.split()
    comando = partes[0].lower()
    resp_twilio = MessagingResponse()
    respuesta = ""

    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        cursor = conn.cursor()

        if comando == "!producto":
            consulta_limpia = " ".join(partes[1:]).replace(",", " ").strip()
            if not consulta_limpia:
                respuesta = "❌ ¿Qué buscás? Ej: !producto quilmes lata"
            else:
                palabras = [p for p in consulta_limpia.split() if len(p) > 1]
                query_base = "SELECT nombre_producto, stock, precio, fecha_vencimiento, marca FROM producto WHERE "
                condiciones = []
                parametros = []

                for p in palabras:
                    condiciones.append("(nombre_producto ILIKE %s OR marca ILIKE %s)")
                    termino = f"%{p}%"
                    parametros.extend([termino, termino])

                query_final = query_base + " AND ".join(condiciones) + " LIMIT 1"
                cursor.execute(query_final, parametros)
                producto = cursor.fetchone()

                if producto:
                    f_venc = producto['fecha_vencimiento']
                    f_formateada = f_venc.strftime('%d/%m/%Y') if f_venc else "Sin fecha"
                    respuesta = (
                        "📦 *Detalles del Producto*\n"
                        f"🔹 *Nombre:* {producto['nombre_producto']}\n"
                        f"🏷️ *Marca:* {producto['marca']}\n"
                        f"💰 *Precio:* ${producto['precio']}\n"
                        f"🛒 *Stock:* {producto['stock']} unidades\n"
                        f"📅 *Vencimiento:* {f_formateada}"
                    )
                else:
                    respuesta = f"❌ No encontré nada que coincida con: *{consulta_limpia}*"

        elif comando == "!productoc":
            codigo_barra = " ".join(partes[1:]).strip()
           
            if not codigo_barra:
                respuesta = "⚠️ Ingresá el código de barras después del comando."
            else:
                query_producto = "SELECT * FROM producto WHERE codigo_barra = %s LIMIT 1"
                cursor.execute(query_producto, (codigo_barra,))
                producto = cursor.fetchone()

                if producto:
                    f_venc = producto['fecha_vencimiento']
                    f_formateada = f_venc.strftime('%d/%m/%Y') if f_venc else "Sin fecha"
                    respuesta = (
                        "📦 *Detalles del Producto*\n"
                        f"🔹 *Nombre:* {producto['nombre_producto']}\n"
                        f"🏷️ *Marca:* {producto['marca']}\n"
                        f"💰 *Precio:* ${producto['precio']}\n"
                        f"🛒 *Stock:* {producto['stock']} unidades\n"
                        f"📅 *Vencimiento:* {f_formateada}"
                    )
                else:
                    respuesta = "❌ Código no encontrado en la base de datos."

        elif comando == "!nuevo":
            texto_datos = mensaje.replace("!nuevo", "").strip()
            lista_datos = [p.strip() for p in texto_datos.split(",") if p.strip()]

            if len(lista_datos) < 6:
                respuesta = "❌ Formato: !nuevo nombre, precio, fecha, stock, marca, codigo"
            else:
                try:
                    nombre_p = lista_datos[0]
                    precio = float(lista_datos[1].replace("$", ""))
                    fecha_v = lista_datos[2]
                    stock = int(lista_datos[3])
                    marca = lista_datos[4]
                    cod = lista_datos[5]

                    query = "INSERT INTO producto (nombre_producto, precio, fecha_vencimiento, stock, marca, codigo_barra) VALUES (%s, %s, %s, %s, %s, %s)"
                    cursor.execute(query, (nombre_p, precio, fecha_v, stock, marca, cod))
                    conn.commit()
                    respuesta = f"✅ *{nombre_p}* guardado correctamente."
                except ValueError:
                    respuesta = "❌ Error: El precio y el stock deben ser números."

        elif comando == "!actualizar":
            datos = mensaje.replace("!actualizar", "").strip()
            lista_datos = [p.strip() for p in datos.split(",") if p.strip()]
            if len(lista_datos) != 4:
                respuesta = "⚠️ Usá: !actualizar nombre, marca, campo, valor"
            else:
                nombre_b, marca_b, atributo, valor = lista_datos
                cursor.execute("SELECT id FROM producto WHERE nombre_producto ILIKE %s AND marca ILIKE %s LIMIT 1", (f"%{nombre_b}%", f"%{marca_b}%"))
                res = cursor.fetchone()
                if res:
                    cursor.execute(f"UPDATE producto SET {atributo} = %s WHERE id = %s", (valor, res['id']))
                    conn.commit()
                    respuesta = f"✅ {atributo} actualizado con éxito."
                else:
                    respuesta = "❌ No encontré el producto."

        elif comando == "!":
            respuesta = (
                "🤖 *Asistente de Stock*\n\n"
                "🔍 *!producto* [nombre]\n"
                "🔢 *!productoc* [código]\n"
                "➕ *!nuevo* [nombre, precio, fecha, stock, marca, código]\n"
                "🔄 *!actualizar* [nombre, marca, campo, valor]"
            )
        else:
            respuesta = "❓ Comando no reconocido. Escribí *!* para ver ayuda."

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        print(f"❌ Error Crítico: {e}")
        respuesta = "⚠️ Error de conexión. Reintentá en unos segundos."
    
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    resp_twilio.message(respuesta)
    return Response(content=str(resp_twilio), media_type="application/xml")












