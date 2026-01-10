from fastapi import FastAPI, HTTPException, status, Form, Response
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from twilio.twiml.messaging_response import MessagingResponse
import os

DATABASE_URL = os.environ.get('DATABASE_URL')

app = FastAPI()

class Product(BaseModel):
    nombre_producto: Optional[str] = None
    precio : Optional[float] = None
    fecha_vencimiento : Optional[str] = None
    marca : Optional[str] = None
    stock : Optional[int] = None

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
            consulta_limpia = " ".join(partes[1:]).strip()
            if not consulta_limpia:
                respuesta = "❌ ¿Qué buscás? Ej: !producto quilmes lata"
            else:
                palabras = consulta_limpia.replace(",", " ").split()
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
                    respuesta = (
                        "📦 *Detalles del Producto*\n"
                        f"🔹*Nombre:* {producto['nombre_producto']}\n"
                        f"🏷️ *Marca:* {producto['marca']}\n"
                        f"💰 *Precio:* ${producto['precio']}\n"
                        f"🛒 *Stock:* {producto['stock']} unidades"
                    )
                else:
                    respuesta = f"❌ No encontré nada que tenga: *{consulta_limpia}*"

        elif comando == "!productoc":
            codigo_barra = " ".join(partes[1:]).strip()
            
            if len(codigo_barra) < 1:
                respuesta = "⚠️ Por favor, ingresá un código de barras."
            else:
                query_producto = """
                SELECT nombre_producto, stock, precio, fecha_vencimiento, marca
                FROM producto WHERE codigo = %s LIMIT 1
                """
                cursor.execute(query_producto, (codigo_barra,))
                producto = cursor.fetchone()

                if producto:
                    respuesta = (
                        "📦 *Detalles del Producto*\n"
                        f"🔹*Nombre:* {producto['nombre_producto']}\n"
                        f"🏷️ *Marca:* {producto['marca']}\n"
                        f"💰 *Precio:* ${producto['precio']}\n"
                        f"🛒 *Stock:* {producto['stock']} unidades"
                    )
                else:
                    respuesta = "❌ Producto no encontrado"

        elif comando == "!nuevo":
            texto_datos = mensaje.replace("!nuevo", "").strip()
            lista_datos = [p.strip() for p in texto_datos.split(",") if p.strip()]

            if len(lista_datos) < 6:
                respuesta = "❌ Formato incorrecto. Usá: !nuevo nombre,precio,fecha,stock,marca,codigo"
            else:
                nombre_p = lista_datos[0]
                precio = float(lista_datos[1])
                fecha_v = lista_datos[2]
                stock = int(lista_datos[3])
                marca = lista_datos[4]
                cod = lista_datos[5]

                query = """
                INSERT INTO producto (nombre_producto, precio, fecha_vencimiento, stock, marca, codigo)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (nombre_p, precio, fecha_v, stock, marca, cod))
                conn.commit() 
                respuesta = f"✅ Producto '{nombre_p}' creado con éxito."

        elif comando == "!actualizar":
            datos = mensaje.replace("!actualizar", "").strip()
            lista_datos = [p.strip() for p in datos.split(",") if p.strip()]

            if len(lista_datos) != 4:
                respuesta = "⚠️ Error: Usá !actualizar nombre,marca,columna,valor"
            else:
                nombre_busq, marca_busq, atributo, valor = lista_datos
                
                cursor.execute(
                    "SELECT id FROM producto WHERE nombre_producto ILIKE %s AND marca ILIKE %s LIMIT 1",
                    (f"%{nombre_busq}%", f"%{marca_busq}%")
                )
                resultado = cursor.fetchone()

                if not resultado:
                    respuesta = "❌ No encontré el producto para actualizar."
                else:
                    id_prod = resultado["id"]
                    # NOTA: Asegurate de que 'atributo' sea un nombre de columna válido
                    query_upd = f"UPDATE producto SET {atributo} = %s WHERE id = %s"
                    cursor.execute(query_upd, (valor, id_prod))
                    conn.commit()
                    respuesta = f"✅ Producto '{nombre_busq}' actualizado: {atributo} = {valor}."

        elif comando == "!":
            respuesta = (
                "🤖 *Comandos Disponibles:*\n"
                "• !producto [nombre],[marca]\n"
                "• !productoc [codigo]\n"
                "• !nuevo [nom,pre,fec,stk,mar,cod]\n"
                "• !actualizar [nom,mar,campo,valor]"
            )
        else:
            respuesta = "❓ Comando no reconocido. Escribí *!* para ayuda."

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        print(f"❌ Error en BD: {e}")
        respuesta = "⚠️ Error interno. Intentá de nuevo."
    
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    resp_twilio.message(respuesta)
    return Response(content=str(resp_twilio), media_type="application/xml")

