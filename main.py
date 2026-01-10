from fastapi import FastAPI, HTTPException,status,Form,Response
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional
from twilio.twiml.messaging_response import MessagingResponse
import os
from psycopg2 import pool

DATABASE_URL = os.environ.get('DATABASE_URL')

app = FastAPI()

class Product(BaseModel):
    nombre_producto: Optional[str] = None #solamente dice que el atributo es opcional para modificarlo
    precio : Optional[float] = None
    fecha_vencimiento : Optional[str] = None
    marca : Optional[str] = None
    stock : Optional[int] = None

conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

cursor = conn.cursor()

@app.post("/webhook")
async def responder_whatsapp(Body: str = Form(...)):
    
    mensaje = Body.strip()
    if not mensaje: return Response(content=str(MessagingResponse()), media_type="application/xml")
    
    partes = mensaje.split() #rompe la cadena
    comando = partes[0].lower()

    resp_twilio = MessagingResponse()
    respuesta = ""

    if comando == "!producto":
        
        consulta_limpia = " ".join(partes[1:]).strip()

        if not consulta_limpia:
            respuesta = "❌ ¿Qué buscás? Ej: !producto quilmes lata"
        else:
            try:
                conn.rollback() 
                
                palabras = consulta_limpia.replace(",", " ").split() # formateo la cadena
                
                query_base = "SELECT nombre_producto, stock, precio, fecha_vencimiento, marca FROM producto WHERE " # arma la query
                condiciones = []
                parametros = []

                for p in palabras:
                    condiciones.append("(nombre_producto ILIKE %s OR marca ILIKE %s)") #implemento la condicion del where
                    termino = f"%{p}%" #armo el termino del like 
                    parametros.extend([termino, termino]) #"Desarma" la segunda lista y mete sus elementos uno por uno.

                query_final = query_base + " AND ".join(condiciones) + " LIMIT 1" #arma toda la query entera

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
            
            except Exception as e:
                conn.rollback()
                print(f"Errorazo: {e}") #devuelve un error textual de la bdd
                respuesta = "⚠️ Hubo un fallo en la base de datos."
    
    elif comando == "!productoc":
        
        codigo_barra = " ".join(partes[1:]).strip()

        conn.rollback()
        
        if len(codigo) != 11 and not codigo.isdigit():
                respuesta = "codigo de barra incorrecto...."
        else:
                query_producto = """
                SELECT nombre_producto, stock, precio, fecha_vencimiento, marca
                FROM producto
                WHERE codigo = %s
                LIMIT 1
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
            respuesta = "❌ Formato incorrecto. Usá: !nuevo nombre,precio,fecha,stock,marca,codigo de barra"
        else:
            try:

                conn.rollback()

                nombre_producto = lista_datos[0].strip()
                precio = float(lista_datos[1].strip())
                fecha_vencimiento = lista_datos[2].strip()
                stock = int(lista_datos[3].strip())
                marca = lista_datos[4].strip()
                codigo_barra = lista_datos[5].strip()

                insercion_producto = """
                INSERT INTO producto
                (nombre_producto, precio, fecha_vencimiento, stock, marca,codigo)
                VALUES (%s, %s, %s, %s, %s,%s)
                """
                cursor.execute(
                    insercion_producto,
                    (nombre_producto, precio, fecha_vencimiento, stock, marca, codigo_barra)
                )
                conn.commit()

                respuesta = (
                    "✅ Producto creado\n"
                    f"Nombre: {nombre_producto}\n"
                    f"Precio: {precio}\n"
                    f"Vencimiento: {fecha_vencimiento}\n"
                    f"Stock: {stock}\n"
                    f"Marca: {marca}\n"
                    f"codigo_barra: {codigo_barra}\n"
                )

            except Exception as e:
                respuesta = f"❌ Error BD: {str(e)}"
    
    elif comando == "!actualizar":
        datos = mensaje.replace("!actualizar", "").strip()
        lista_datos = [p.strip() for p in datos.split(",") if p.strip()]

        if len(lista_datos) != 4:
            respuesta = "⚠️ Error: Faltan datos."
        else:
            nombre_largo, marca_larga, atributo, valor = lista_datos

            palabra_prod = nombre_largo.split()[0]

            palabras_marca = marca_larga.split()

            if len(palabras_marca) > 1 and palabras_marca[0].lower() in ["la", "el", "los", "las", "de"]:
                palabra_marca = palabras_marca[1] 
            else:
                palabra_marca = palabras_marca[0] 

            query = """
                SELECT id, nombre_producto, marca 
                FROM producto 
                WHERE nombre_producto ILIKE %s 
                AND marca ILIKE %s
                LIMIT 1
            """
    
            p_prod = f"%{palabra_prod}%"
            p_marc = f"%{palabra_marca}%"

            cursor.execute(query, (p_prod, p_marc))
            resultado = cursor.fetchone()

            if not resultado:
                respuesta = f"❌ No encontré coincidencia para '{palabra_prod}' de '{palabra_marca}'"
            else:
                id_producto = resultado["id"]

                query_update = f"UPDATE producto SET {atributo} = %s WHERE id = %s"
                cursor.execute(query_update, (valor, id_producto))
                conn.commit()
                
                respuesta = f"producto actualizado con exito!"
    elif comando == "!":
        respuesta = (f"comandos disponibles:\n"
                    f"!producto: nombre_producto marca\n" 
                    f"!productoc: codigo_barra\n"
                    f"!nuevo: nombre_producto,precio,fecha_vencimiento,marca,stock,codigo_barra\n"
                    f"!actualizar: nombre_producto,marca,atributo a modificar, por ej: nombre,stock,nuevo valor\n")

    else:
        respuesta = "❓ Comando no reconocido"

    resp_twilio.message(respuesta)

    return Response(
        content=str(resp_twilio),
        media_type="application/xml"
    )

    try:
    db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 20,
        os.environ.get('DATABASE_URL'),
        sslmode='require'
    )
    print("Pool de conexiones creado con éxito")
except Exception as e:
    print(f"Error creando el pool: {e}")

def ejecutar_query(query, params=None, es_consulta=True):
    conn = None
    try:
        # Esto asegura que CADA VEZ que alguien mande un mensaje, 
        # se intente una conexión nueva y fresca
            conn = psycopg2.connect(os.environ.get('DATABASE_URL'), sslmode='require')
            cur = conn.cursor(cursor_factory=RealDictCursor)
        
            cur.execute(query, params)
        
            if es_consulta:
                resultado = cur.fetchone()
            else:
                conn.commit() # Para INSERT o UPDATE
                resultado = True
            
            cur.close()
            return resultado
    except Exception as e:
            print(f"Error en la base de datos: {e}")
            return None
    finally:
            if conn:
                conn.close() # Cerramos siempre para evitar el error de "closed"

def get_connection():
    # Esto intentará conectar de nuevo si la conexión se perdió
    return psycopg2.connect(os.environ.get('DATABASE_URL'), sslmode='require')





