# =============================================================================
# routes.py — Definición de rutas para el Blueprint de la REST API
#
# Este módulo contiene los endpoints REST de la aplicación, organizados por
# recurso. Cada recurso cuenta con rutas para operaciones CRUD.
#
# Recursos disponibles:
#   /usuarios              -> Gestión de cuentas de usuario
#   /productos             -> Catálogo de productos
#   /ordenes               -> Órdenes de compra
#   /ordenes/confirmar     -> Confirmación de una orden (requiere pago previo)
#   /ordenes/completar     -> Finalización/entrega de una orden
#   /pagos                 -> Registro y consulta de pagos
#
# Convenciones generales:
#   - Las funciones obtener_entradas() y actualizar_entradas() son capas
#     genéricas de acceso a datos que reciben el nombre del procedimiento/
#     operación y sus parámetros.
#   - Las funciones validar_*() validan el cuerpo JSON de la solicitud y
#     devuelven (solicitud, error) o (solicitud, error, dato_extra).
#   - Cuando un recurso no existe, se devuelve 404.
#   - Cuando se crea un recurso exitosamente via POST, se devuelve 201.
# =============================================================================

from . import api_bp

from flask import Flask, request, jsonify

from app.helpers import verificar_float, validar_usuario, validar_producto, validar_orden, validar_pago
from app.db_api import obtener_entradas, actualizar_entradas, agregar_usuario, verificar_pago_existente, confirmar_orden, finalizar_orden


# =============================================================================
# USUARIOS
# =============================================================================

@api_bp.route("usuarios", methods=["GET", "POST"])
def usuarios():
    """
    Endpoint de recursos para la entidad 'Usuarios'.

    GET  -> Devuelve la lista de todos los usuarios registrados en el sistema.
    POST -> Crea un nuevo usuario con los datos proporcionados en el cuerpo JSON.
            Campos requeridos: nombre, username, email, password.

    NOTA: agregar_usuario() se utiliza para configurar la contrasea con hashing aquí, a diferencia de otros
    recursos que usan la funcin genérica actualizar_entradas().

    """
    # Campos obligatorios para la creación de un usuario
    claves_requeridas = ["nombre", "username", "email", "password"]

    if request.method == 'GET':
        usuarios = obtener_entradas("obtener_usuarios")
        print(usuarios)
        return jsonify(usuarios)

    elif request.method == 'POST':
        solicitud, error = validar_usuario(claves_requeridas)
        if error:
            return error
        # 201: se creó un nuevo recurso exitosamente
        return jsonify(agregar_usuario(
            solicitud["nombre"],
            solicitud["username"],
            solicitud["email"],
            solicitud["password"]
        )), 201


@api_bp.route("usuarios/<int:id_usuario>", methods=["GET", "PUT", "DELETE"])
def usuarios_id(id_usuario):
    """
    Endpoint de recurso individual para la entidad 'usuarios'.

    GET    -> Devuelve los datos del usuario con el ID especificado.
    PUT    -> Actualiza nombre, username e email del usuario.
                Campos requeridos: nombre, username, email.
    DELETE -> Elimina el usuario con el ID especificado.

    En todos los métodos se verifica primero que el usuario exista;
    si no, se devuelve 404.

    """
    # Campos obligatorios para la actualización de un usuario
    claves_requeridas = ["nombre", "username", "email"]

    # Verificar que el usuario exista antes de proceder con cualquier operación
    usuario = obtener_entradas("obtener_usuario", (id_usuario))
    if len(usuario) == 0:
        # 404: el recurso solicitado no existe en el sistema
        return jsonify({"error": f"El usuario buscado no existe"}), 404

    if request.method == 'GET':
        return jsonify(usuario), 200

    elif request.method == 'PUT':
        solicitud, error = validar_usuario(claves_requeridas)
        if error:
            return error
        return jsonify(actualizar_entradas(
            request.method,
            "usuarios",
            (solicitud["nombre"], solicitud["username"], solicitud["email"], id_usuario)
        )), 200

    elif request.method == 'DELETE':
        return jsonify(actualizar_entradas(request.method, "usuarios", (id_usuario,))), 200


# =============================================================================
# PRODUCTOS
# =============================================================================

@api_bp.route("productos", methods=["GET", "POST"])
def productos():
    """
    Endpoint de recursos para la entidad 'Producto'.

    GET  -> Devuelve la lista de todos los productos del catálogo.
    POST -> Crea un nuevo producto.
            Campos requeridos: nombre_producto, precio, disponible.
    """
    # Campos obligatorios para la creación de un producto
    claves_requeridas = ["nombre_producto", "precio", "disponible"]

    if request.method == 'GET':
        productos = obtener_entradas("obtener_productos")
        print(productos)
        return jsonify(productos)

    elif request.method == 'POST':
        solicitud, error = validar_producto(claves_requeridas)
        if error:
            return error
        # 201: se creó un nuevo recurso exitosamente
        return jsonify(actualizar_entradas(
            request.method,
            "producto",
            (solicitud["nombre_producto"], solicitud["precio"], solicitud["disponible"])
        )), 201


@api_bp.route("productos/<int:id_producto>", methods=["GET", "PUT", "DELETE"])
def productos_id(id_producto):
    """
    Endpoint de recurso individual para la entidad 'Productos'.

    GET    -> Devuelve los datos del producto con el ID especificado.
    PUT    -> Actualiza los datos del producto.
                Campos requeridos: nombre_producto, precio, disponible.
    DELETE -> Elimina el producto con el ID especificado.

    En todos los métodos se verifica primero que el producto exista;
    si no, se devuelve 404.

    """
    # Campos obligatorios para la actualización de un producto
    claves_requeridas = ["nombre_producto", "precio", "disponible"]

    # Verificar que el producto exista antes de proceder con cualquier operación
    producto = obtener_entradas("obtener_producto", (id_producto))
    if len(producto) == 0:
        # 404: el recurso solicitado no existe en el sistema
        return jsonify({"error": f"El producto buscado no existe"}), 404

    if request.method == 'GET':
        return jsonify(producto), 200

    elif request.method == 'PUT':
        solicitud, error = validar_producto(claves_requeridas)
        if error:
            return error
        return jsonify(actualizar_entradas(
            request.method,
            "producto",
            (solicitud["nombre_producto"], solicitud["precio"], solicitud["disponible"], id_producto)
        )), 200

    elif request.method == 'DELETE':
        # NOTA: (id_producto) no es una tupla. Ver comentario de la función.
        return jsonify(actualizar_entradas(request.method, "producto", (id_producto,))), 200


# =============================================================================
# ÓRDENES
# =============================================================================

@api_bp.route("ordenes", methods=["GET", "POST"])
def ordenes():
    """
    Endpoint de recursos para la entidad 'Orden'.

    GET  -> Devuelve la lista de todas las órdenes del sistema.
    POST -> Crea una nueva orden.
            Campos requeridos: id_usuario, id_producto, cantidad, fecha_hora_recoleccion.
    """
    # Campos obligatorios para la creación de una orden
    claves_requeridas = ["id_usuario", "id_producto", "cantidad", "fecha_hora_recoleccion"]

    if request.method == 'GET':
        ordenes = obtener_entradas("obtener_ordenes")
        print(ordenes)
        return jsonify(ordenes)

    elif request.method == 'POST':
        solicitud, error = validar_orden(claves_requeridas)
        if error:
            return error
        # 201: se creó un nuevo recurso exitosamente
        return jsonify(actualizar_entradas(
            request.method,
            "orden",
            (solicitud["id_usuario"], solicitud["id_producto"], solicitud["cantidad"], solicitud["fecha_hora_recoleccion"])
        )), 201


@api_bp.route("ordenes/<int:id_orden>", methods=["GET", "PUT", "DELETE"])
def ordenes_id(id_orden):
    """
    Endpoint de recurso individual para la entidad 'Orden'.

    GET    → Devuelve los datos de la orden con el ID especificado.
    PUT    → Actualiza los datos de la orden.
                Campos requeridos: id_usuario, id_producto, cantidad, fecha_hora_recoleccion.
    DELETE → Elimina la orden con el ID especificado.

    En todos los métodos se verifica primero que la orden exista;
    si no, se devuelve 404.

    """
    # Campos obligatorios para la actualización de una orden
    claves_requeridas = ["id_usuario", "id_producto", "cantidad", "fecha_hora_recoleccion"]

    # Verificar que la orden exista antes de proceder con cualquier operación
    orden = obtener_entradas("obtener_orden", (id_orden))
    if len(orden) == 0:
        # 404: el recurso solicitado no existe en el sistema
        return jsonify({"error": f"La orden buscada no existe"}), 404

    if request.method == 'GET':
        return jsonify(orden), 200

    elif request.method == 'PUT':
        solicitud, error = validar_orden(claves_requeridas)
        if error:
            return error
        return jsonify(actualizar_entradas(
            request.method,
            "orden",
            (solicitud["id_usuario"], solicitud["id_producto"], solicitud["cantidad"], solicitud["fecha_hora_recoleccion"], id_orden)
        )), 200

    elif request.method == 'DELETE':
        # NOTA: (id_orden) no es una tupla. Ver comentario de la función.
        return jsonify(actualizar_entradas(request.method, "orden", (id_orden,))), 200


@api_bp.route("ordenes/confirmar/<int:id_orden>", methods=["PUT"])
def confirmar_orden_id(id_orden):
    """
    Confirma una orden pendiente, verificando que ya exista un pago registrado.

    El flujo de validación es el siguiente:
        1. Verificar que la orden exista (404 si no).
        2. Verificar que exista un pago asociado mediante verificar_pago_existente().
        Si no existe, se retorna 400 con el mensaje de error del resultado.
        3. Ejecutar la confirmación de la orden mediante confirmar_orden().
        Si falla, se retorna 400 con el mensaje de error del resultado.
        4. Si todo es exitoso, se retorna 200 con la confirmación.

    Tanto verificar_pago_existente() como confirmar_orden() retornan diccionarios
    con al menos la clave "exito" (booleano) para indicar el resultado.

    """
    # Verificar que la orden exista antes de proceder
    orden = obtener_entradas("obtener_orden", (id_orden))
    if len(orden) == 0:
        # 404: el recurso solicitado no existe en el sistema
        return jsonify({"error": f"La orden buscada no existe"}), 404

    # Paso 1: Verificar que la orden tenga un pago registrado antes de confirmar
    resultado = verificar_pago_existente(id_orden)
    if not resultado["exito"]:
        return jsonify(resultado), 400

    # Paso 2: Ejecutar la confirmación de la orden en la base de datos
    confirmacion = confirmar_orden(id_orden)
    if not confirmacion["exito"]:
        return jsonify(confirmacion), 400
    else:
        return jsonify(confirmacion), 200


@api_bp.route("ordenes/completar/<int:id_orden>", methods=["PUT"])
def completar_orden_id(id_orden):
    """
    Marca una orden confirmada como completada/entregada.

    El flujo es:
    1. Verificar que la orden exista (404 si no).
    2. Ejecutar la finalización mediante finalizar_orden().
        Si falla, retorna 400 con el mensaje de error.
        Si tiene éxito, retorna 200.

    """
    # Verificar que la orden exista antes de proceder
    orden = obtener_entradas("obtener_orden", (id_orden))
    if len(orden) == 0:
        # 404: el recurso solicitado no existe en el sistema
        return jsonify({"error": f"La orden buscada no existe"}), 404

    # Ejecutar la finalización de la orden en la base de datos
    resultado = finalizar_orden(id_orden)
    if not resultado["exito"]:
        return jsonify(resultado), 400
    else:
        return jsonify(resultado), 200


# =============================================================================
# PAGOS
# =============================================================================

@api_bp.route("pagos", methods=["GET", "POST"])
def pagos():
    """
    Endpoint de recursos para la entidad 'Pago'.

    GET  -> Retorna la lista de todos los pagos registrados.
    POST -> Registra un nuevo pago asociado a una orden.
            Campos requeridos: id_orden, id_metodo_pago, cantidad_pagada.

    La función validar_pago() retorna tres valores:
    (solicitud, error, cantidad_a_pagar)
    donde 'cantidad_a_pagar' es el monto total de la orden, que se obtiene
    internamente durante la validación (presumiblemente consultando la BD).

    La diferencia (solicitud["cantidad_pagada"] - cantidad_a_pagar) representa
    el cambio o vuelto a devolver al cliente en caso de pago en efectivo.

    """
    # Campos obligatorios para el registro de un pago
    claves_requeridas = ["id_orden", "id_metodo_pago", "cantidad_pagada"]

    if request.method == 'GET':
        pagos = obtener_entradas("obtener_pagos")
        print(pagos)
        return jsonify(pagos)

    elif request.method == 'POST':
        # validar_pago retorna un tercer valor: el monto total de la orden (cantidad_a_pagar)
        solicitud, error, cantidad_a_pagar = validar_pago(claves_requeridas)
        if error:
            return error
        # 201: se creó un nuevo recurso exitosamente
        # Los parámetros son: id_orden, id_metodo_pago, monto_total, cantidad_pagada, cambio
        return jsonify(actualizar_entradas(
            request.method,
            "pago",
            (
                solicitud["id_orden"],
                solicitud["id_metodo_pago"],
                cantidad_a_pagar,
                solicitud["cantidad_pagada"],
                solicitud["cantidad_pagada"] - cantidad_a_pagar  # CantidadARegresar
            )
        )), 201


@api_bp.route("pagos/<int:id_pago>", methods=["GET", "PUT", "DELETE"])
def pagos_id(id_pago):
    """
    Endpoint de recurso individual para la entidad 'Pago'.

    GET    -> Devuelve los datos del pago con el ID especificado.
    PUT    -> Actualiza los datos del pago.
                Campos requeridos: id_orden, id_metodo_pago, cantidad_pagada.
    DELETE -> Elimina el pago con el ID especificado.

    En todos los métodos se verifica primero que el pago exista;
    si no, se retorna 404.

    NOTA: (id_pago) no es una tupla. Ver comentario en usuarios_id.
    """
    # Campos obligatorios para la actualización de un pago
    claves_requeridas = ["id_orden", "id_metodo_pago", "cantidad_pagada"]

    # Verificar que el pago exista antes de proceder con cualquier operación
    pago = obtener_entradas("obtener_pago", (id_pago))
    if len(pago) == 0:
        # 404: el recurso solicitado no existe en el sistema
        return jsonify({"error": f"El pago buscado no existe"}), 404

    if request.method == 'GET':
        return jsonify(pago), 200

    elif request.method == 'PUT':
        # validar_pago retorna un tercer valor: el monto total de la orden
        solicitud, error, cantidad_a_pagar = validar_pago(claves_requeridas)
        if error:
            return error
        # Los parámetros son: id_orden, id_metodo_pago, monto_total, cantidad_pagada, cambio, id_pago
        return jsonify(actualizar_entradas(
            request.method,
            "pago",
            (
                solicitud["id_orden"],
                solicitud["id_metodo_pago"],
                cantidad_a_pagar,
                solicitud["cantidad_pagada"],
                solicitud["cantidad_pagada"] - cantidad_a_pagar,  # CantidadRegresada
                id_pago
            )
        )), 200

    elif request.method == 'DELETE':
        return jsonify(actualizar_entradas(request.method, "pago", (id_pago,))), 200
