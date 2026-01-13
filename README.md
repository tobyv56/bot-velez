# 🛒bot-velez

bot de whatsapp de gestion de productos de supermercados para simplificar la gestion de productos, control de precios y seguimientos de 
vencimiento a tiempo real

## 🚀 Tecnologías Utilizadas

-lenguaje = python                      -hosting =  twilio
-framework web = fastapi
-bdd = postgreSQL (neon) 

## 🛠️ Comandos Disponibles

### tiene varios comando para interactuar con el bot como:

!nuevo nombre_producto,marca,precio,stock,fecha_vencimiento,codigo_barra (crea un nuevo producto con sus atributos correspondientes)
!actualizar nombre_producto, marca, atributo a cambiar, nuevo_valor (actualiza el producto al atributo el que quiera el usuario)
!producto nombre_producto, marca (consulta el producto correspondiente devolviendole nombre_producto,marca,precio,stock,fecha_vencimiento)
!productoc codigo_barra (es casi lo mismo que !producto pero se busca mediante el codigo de barra del producto "ideal para los empleados del supermercado para facilitar el trabajo")

## 🏗️ Arquitectura del Sistema

### twilio esta conectado a un servidor en fastapi alojado en la nube haciendo peticiones y consultas a una bdd relacional

(actualmente sigue en desarrollo para diferentes funcionalidades como que te devuelva el bot los productos por vencer o un nuevo comando como !productob tipo_producto que me devuelve el producto mas barato)

