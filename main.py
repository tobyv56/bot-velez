from fastapi import FastAPI, HTTPException, status, Form, Response
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from twilio.twiml.messaging_response import MessagingResponse
import os
import unicodedata

DATABASE_URL = os.environ.get('DATABASE_URL')

app = FastAPI()

@app.get("/")
async def inicio():
    return {"estado": "online", "mensaje": "Bot de Stock funcionando"}

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

def limpiar_texto(texto):
    if not texto:
        return ""
    texto = texto.lower()
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    return texto

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
                respuesta = "❌ ¿Qué buscás? Ej: !producto quilmes, lata"
            else:
                try:
                    conn.rollback() 
                    lista_datos = [p.strip() for p in consulta_limpia.split(",") if p.strip()]

                    if len(lista_datos) < 2:
                        respuesta = "⚠️ Formato: !producto nombre, marca"
                    else:
                        n_b = limpiar_texto(lista_datos[0])
                        m_b = limpiar_texto(lista_datos[1])
                
                        query = """
                            SELECT nombre_producto, stock, precio, fecha_vencimiento, marca 
                            FROM producto 
                            WHERE nombre_producto ILIKE %s AND marca ILIKE %s 
                            LIMIT 1
                        """
                        cursor.execute(query, (f"%{n_b}%", f"%{m_b}%"))
                        producto = cursor.fetchone()

                        if producto:
                            respuesta = (
                                "📦 *Detalles del Producto*\n"
                                f"🔹 *Nombre:* {producto['nombre_producto'].title()}\n"
                                f"🏷️ *Marca:* {producto['marca'].upper()}\n"
                                f"💰 *Precio:* ${producto['precio']}\n"
                                f"🛒 *Stock:* {producto['stock']} unidades"
                            )
                        else:
                            respuesta = f"❌ No encontré '{n_b}' de marca '{m_b}'."
                except Exception as e:
                    print(f"Error: {e}")
                    respuesta = "⚠️ Error al buscar."
                
        elif comando == "!productoc":
            cod_busqueda = " ".join(partes[1:]).strip()
            if not cod_busqueda:
                respuesta = "⚠️ Ingresá el código de barras."
            else:
                query_producto = "SELECT * FROM producto WHERE codigo_barra = %s LIMIT 1"
                cursor.execute(query_producto, (cod_busqueda,))
                producto = cursor.fetchone()
                if producto:
                    respuesta = (
                        "📦 *Detalles del Producto*\n"
                        f"🔹 *Nombre:* {producto['nombre_producto'].title()}\n"
                        f"🏷️ *Marca:* {producto['marca'].upper()}\n"
                        f"💰 *Precio:* ${producto['precio']}\n"
                        f"🛒 *Stock:* {producto['stock']} unidades\n"
                        f"📅 *Vencimiento:* {producto['fecha_vencimiento']}"
                    )
                else:
                    respuesta = "❌ Código no encontrado."

        elif comando == "!nuevo":
            texto_datos = mensaje.replace("!nuevo", "").strip()
            lista_datos = [p.strip() for p in texto_datos.split(",") if p.strip()]
            if len(lista_datos) < 6:
                respuesta = "❌ Formato: !nuevo nombre, precio, fecha, marca, stock, código"
            else:
                try:
                    conn.rollback()
                    n_p = limpiar_texto(lista_datos[0])
                    pre = float(lista_datos[1])
                    ven = lista_datos[2].strip()
                    mar = limpiar_texto(lista_datos[3])
                    stk = int(lista_datos[4])
                    cod = lista_datos[5].strip()

                    query_ins = """
                        INSERT INTO producto (nombre_producto, precio, fecha_vencimiento, stock, marca, codigo_barra)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """
                    cursor.execute(query_ins, (n_p, pre, ven, stk, mar, cod))
                    conn.commit()
                    respuesta = f"✅ Producto '{n_p.title()}' creado."
                except Exception as e:
                    conn.rollback()
                    respuesta = f"❌ Error al guardar: {str(e)}"

        elif comando == "!actualizar":
            datos = mensaje.replace("!actualizar", "").strip()
            lista_datos = [p.strip() for p in datos.split(",") if p.strip()]
            if len(lista_datos) != 4:
                respuesta = "⚠️ Usá: !actualizar nombre, marca, campo, valor"
            else:
                n_up, m_up, attr, val = lista_datos
                cursor.execute("SELECT id FROM producto WHERE nombre_producto ILIKE %s AND marca ILIKE %s LIMIT 1", (f"%{n_up}%", f"%{m_up}%"))
                res = cursor.fetchone()
                if res:
                    cursor.execute(f"UPDATE producto SET {attr} = %s WHERE id = %s", (val, res['id']))
                    conn.commit()
                    respuesta = f"✅ {attr} actualizado."
                else:
                    respuesta = "❌ No encontrado."

        elif comando == "!":
            respuesta = (
                "🤖 *Asistente de Stock*\n\n"
                "🔍 *!producto* nombre, marca\n"
                "🔢 *!productoc* código\n"
                "➕ *!nuevo* nombre, precio, fecha, marca, stock, código\n"
                "🔄 *!actualizar* nombre, marca, campo, valor"
            )
        else:
            respuesta = "❓ Escribí *!* para ver ayuda."

    except Exception as e:
        if 'conn' in locals(): conn.rollback()
        print(f"Error Crítico: {e}")
        respuesta = "⚠️ Error de conexión."
    finally:
        if 'cursor' in locals(): cursor.close()
        if 'conn' in locals(): conn.close()

    resp_twilio.message(respuesta)
    return Response(content=str(resp_twilio), media_type="application/xml")                    
                    cursor.execute(
                        insercion_producto,
                        (nombre_producto, precio, fecha_vencimiento, stock, marca, codigo_barra)
                    )
                    conn.commit()

                    respuesta = (
                        "✅ *Producto creado con éxito*\n"
                        f"🔹 Nombre: {nombre_producto.title()}\n"
                        f"🔹 Marca: {marca.upper()}\n"
                        f"🔹 Precio: ${precio}\n"
                        f"🔹 Stock: {stock} unid.\n"
                        f"🔹 Vencimiento: {fecha_vencimiento}\n"
                        f"🔹 Código: {codigo_barra}"
                    )

                except Exception as e:
                    conn.rollback()
                    respuesta = f"❌ Error BD: {str(e)}"

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

    



























