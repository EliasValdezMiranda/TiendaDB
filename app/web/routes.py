# =============================================================================
# routes.py - Definición de rutas para el Blueprint de la aplicación web
#
# Este módulo maneja todas las rutas HTTP de la interfaz web, incluyendo:
#   - Autenticación de usuarios (login, logout, registro)
#   - Gestión de productos (ver, agregar, editar, eliminar)
#   - Gestión de órdenes (ver, agregar, editar, confirmar, completar, eliminar)
#   - Historial de órdenes del usuario
#
# Las rutas están protegidas con el decorador @login_required, a excepción
# de /login, /logout y /register, que son públicas.
#
# Roles de usuario reconocidos por el sistema:
#   1 -> Cliente regular
#   2 -> Administrador
# =============================================================================

from . import web_bp

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session

from app.helpers import apology, login_required, verificar_float
from app.db import (
    agregar_usuario, verificar_password, obtener_rol_usuario, obtener_username,
    agregar_producto, obtener_productos, actualizar_producto, eliminar_producto,
    obtener_ordenes, agregar_orden, eliminar_orden, actualizar_orden,
    confirmar_orden, crear_pago, actualizar_pago, obtener_historial
)


@web_bp.after_request
def after_request(response):
    """Deshabilita el caché del navegador en todas las respuestas del Blueprint."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# =============================================================================
# AUTENTICACIÓN
# =============================================================================

@web_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    Maneja el inicio de sesión del usuario.

    GET  -> Muestra el formulario de login.
    POST -> Valida las credenciales contra la base de datos.

    Códigos de retorno de verificar_password():
        0  -> Fallo de conexión con la base de datos (503)
        -1  -> Credenciales inválidas (nombre de usuario o contraseña incorrectos) (400)
        >0  -> ID del usuario autenticado correctamente

    Al autenticarse, se almacenan en sesión el ID y el rol del usuario.
    """
    # Limpiar cualquier sesión previa antes de intentar el login
    session.clear()

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # Validar que se hayan enviado ambos campos obligatorios
        if not request.form.get("username"):
            # 400: el cliente no envió los datos requeridos (Bad Request)
            return apology("Introduce un nombre de usuario / Correo electrónico", 400)
        elif not request.form.get("password"):
            return apology("Introduce una contraseña", 400)

        id_usuario = verificar_password(username, password)

        # Manejar los códigos de error de la capa de datos
        if id_usuario == 0:
            return apology("Conexión fallida con la base de datos", 503)
        elif id_usuario == -1:
            return apology("Credenciales inválidas", 400)

        # Almacenar identidad y rol en la sesión del usuario
        session["user_id"] = id_usuario
        session["user_role"] = obtener_rol_usuario(id_usuario)

        return redirect("/")

    else:
        return render_template("login.html")


@web_bp.route("/logout")
def logout():
    """
    Cierra la sesión del usuario activo.

    Limpia todos los datos de sesión y redirige al formulario de login.
    """
    session.clear()
    return redirect("/")


@web_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    Maneja el registro de nuevos usuarios.

    GET  -> Muestra el formulario de registro.
    POST -> Valida los datos del formulario y crea el usuario en la base de datos.

    Códigos de retorno de agregar_usuario() (almacenados en resultados[0]):
        None       -> Fallo de conexión con la base de datos
        -2 a 0     -> Error de validación o duplicado; el mensaje de error
                    está en resultados[1]
        > 0        -> ID del nuevo usuario creado exitosamente

    Al registrarse exitosamente, se inicia sesión automáticamente con el
    nuevo usuario.

    """
    if request.method == "GET":
        return render_template("register.html")

    elif request.method == "POST":
        nombre = request.form.get("nombre")
        username = request.form.get("username")
        email = request.form.get("email")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Validaciones de presencia de campos obligatorios
        if not nombre:
            return apology("Nombre no introducido", 400)
        elif not username:
            return apology("Nombre de usuario no introducido", 400)
        elif not email:
            return apology("Correo electrónico no introducido", 400)
        elif not password:
            return apology("Contraseña no introducida", 400)
        elif not confirmation:
            return apology("Confirmación de contraseña no introducida", 400)

        # Verificar que la contraseña y su confirmación coincidan
        if password != confirmation:
            return apology("Las contraseñas no coinciden", 400)

        resultados = agregar_usuario(nombre, username, email, password)

        # Manejar los distintos resultados de la operación de registro
        if resultados is None:
            # Fallo de conexión con la base de datos
            return apology("Conexión fallida con la base de datos", 503)
        elif resultados[0] in range(-2, 1):
            # Error de validación o conflicto (ej. usuario duplicado)
            # El mensaje descriptivo viene en resultados[1]
            return apology(resultados[1], 400)
        else:
            # Registro exitoso: iniciar sesión automáticamente con el nuevo usuario
            session["user_id"] = resultados[0]
            session["user_role"] = obtener_rol_usuario(resultados[0])
            return redirect("/")


# =============================================================================
# RUTA PRINCIPAL
# =============================================================================

@web_bp.route("/")
@login_required
def index():
    """
    Página principal de la aplicación.

    Muestra las órdenes activas según el rol del usuario:
        - Rol 1 (cliente): solo sus propias órdenes.
        - Rol 2 (admin): todas las órdenes del sistema.

    La variable 'admin' controla qué acciones se muestran en la plantilla.
    """
    if session["user_role"] == 1:
        # Cliente: obtener únicamente las órdenes asociadas a su ID
        ordenes = obtener_ordenes(session["user_id"])
        admin = False
    elif session["user_role"] == 2:
        # Administrador: obtener todas las órdenes del sistema
        ordenes = obtener_ordenes()
        admin = True
    else:
        # Estado inesperado del servidor: el rol almacenado en sesión no es válido
        # Este error no es provocado por el cliente, por eso se usa 500
        return apology("Error: Rol de usuario no identificado", 500)

    return render_template(
        "index.html",
        name=obtener_username(session["user_id"]),
        ordenes=ordenes,
        admin=admin
    )


# =============================================================================
# RUTAS DE PRODUCTOS
# =============================================================================

@web_bp.route("/producto/ver", methods=["GET"])
@login_required
def view_product():
    """
    Muestra el catálogo completo de productos registrados en el sistema.
    Solo los administradores pueden acceder a esta función.
    """
    if session["user_role"] != 2:
        return apology("Error: Acceso prohibido", 403)
    productos = obtener_productos()
    return render_template('view_product.html', productos=productos)


@web_bp.route("/producto/agregar", methods=["GET", "POST"])
@login_required
def add_product():
    """
    Maneja el alta de un nuevo producto.

    GET  -> Muestra el formulario de creación.
    POST -> Valida los datos del formulario y registra el producto en la base
            de datos. Si la operación es exitosa, redirige a /producto/ver.

    """
    if session["user_role"] != 2:
        return apology("Error: Acceso prohibido", 403)
    
    if request.method == "GET":
        return render_template("add_product.html")

    elif request.method == "POST":
        nombre = request.form.get("nombre")
        precio = verificar_float(request.form.get("precio"))

        # bool() sobre el resultado de get() puede devolver True incluso para
        # strings vacíos si el campo existe en el formulario
        disponible = bool(request.form.get("disponible"))

        # Validaciones de entrada
        if not nombre:
            return apology("Error: Nombre no introducido", 400)
        elif not precio:
            return apology("Error: Precio inválido", 400)
        elif precio <= 0:
            return apology("Error: Precio menor a 0", 400)
        elif not disponible:
            return apology("Error: Disponibilidad no seleccionada", 400)

        resultado = agregar_producto(nombre, precio, disponible)
        print(f"Id de producto creado: {resultado}")

        # resultado <= 0 indica fallo en la operación de base de datos
        if resultado <= 0:
            return apology("Error, revisar", 503)
        else:
            return redirect("/producto/ver")


@web_bp.route("/producto/editar/<int:id_producto>", methods=["POST"])
@login_required
def edit_product(id_producto):
    """
    Actualiza los datos de un producto existente.

    Recibe por formulario: nombre, precio y disponibilidad.
    El campo 'disponible' se interpreta como booleano: '1' = True, cualquier
    otro valor = False.

    Redirige a /producto/ver si la operación es exitosa.
    """
    if session["user_role"] != 2:
        return apology("Error: Acceso prohibido", 403)
    
    nombre = request.form.get("nombre")
    precio = verificar_float(request.form.get("precio"))

    # El campo 'disponible' viene por el valor del Radio '0' o '1' desde el formulario
    disponible = True if request.form.get("disponible") == '1' else False

    # Validaciones de entrada
    if not nombre:
        return apology("Error: Nombre no introducido", 400)
    elif not precio:
        return apology("Error: Precio inválido", 400)
    elif precio <= 0:
        return apology("Error: Precio menor a 0", 400)

    resultado = actualizar_producto(nombre, precio, disponible, id_producto)
    print(f"Id de producto actualizado: {resultado}")

    # resultado <= 0 indica fallo en la operación de base de datos
    if resultado <= 0:
        return apology("Error, revisar", 503)
    else:
        return redirect("/producto/ver")


@web_bp.route("/producto/eliminar/<int:id_producto>", methods=["POST"])
@login_required
def delete_product(id_producto):
    """
    Elimina un producto del sistema por su ID.

    Redirige a /producto/ver si la operación es exitosa.
    """
    if session["user_role"] != 2:
        return apology("Error: Acceso prohibido", 403)

    resultado = eliminar_producto(id_producto)
    print(f"Id de producto eliminado: {resultado}")

    # resultado <= 0 indica fallo en la operación de base de datos
    if resultado <= 0:
        return apology("Error, revisar", 503)
    else:
        return redirect("/producto/ver")


# =============================================================================
# RUTAS DE ÓRDENES
# =============================================================================

@web_bp.route("/orden/agregar", methods=["GET", "POST"])
@login_required
def add_order():
    """
    Maneja la creación de una nueva orden por parte del usuario.

    GET  -> Obtiene el catálogo de productos disponibles y muestra el formulario.
    POST -> Valida los datos y registra la orden en la base de datos.

    La fecha y hora de recolección se reciben como campos separados del
    formulario ('fecha_recoleccion' y 'hora_recoleccion') y se combinan
    en formato 'YYYY-MM-DD HH:MM:00', compatible con el tipo DATETIME2 de
    SQL Server.

    """
    if request.method == "GET":
        # Obtener todos los productos disponibles para mostrar en el formulario
        productos = obtener_productos()
        return render_template("add_order.html", productos=productos)

    else:
        # Verificación defensiva de sesión activa
        if "user_id" not in session:
            return redirect("/login")

        id_usuario = session["user_id"]
        id_producto = request.form.get("id_producto")

        # Validar que se haya seleccionado un producto
        if id_producto == '':
            return apology("Error: Producto no especificado", 400)

        cantidad = request.form.get("cantidad")
        if not cantidad:
            return apology("Error: Cantidad inválida", 400)

        # Extraer la fecha y hora de recolección como campos separados
        fecha = request.form.get("fecha_recoleccion")
        hora = request.form.get("hora_recoleccion")

        # Combinar en formato ISO compatible con DATETIME2 de SQL Server
        fecha_hora_recoleccion = f"{fecha} {hora}:00"

        success = agregar_orden(id_usuario, id_producto, cantidad, fecha_hora_recoleccion)

        if success:
            return redirect("/")
        else:
            return "Hubo un error al procesar tu orden.", 500


@web_bp.route("/orden/editar/<int:id_orden>", methods=["POST"])
@login_required
def edit_order(id_orden):
    """
    Actualiza la cantidad de productos de una orden existente.

    """
    # Conversión directa sin manejo de excepciones; puede fallar si el valor no es numérico
    cantidad = int(request.form.get("cantidad"))
    if not cantidad:
        return apology("Error: Cantidad no introducida", 400)

    resultado = actualizar_orden(id_orden, cantidad)
    print(f"Id de la orden actualizada: {resultado}")

    # resultado <= 0 indica fallo en la operación de base de datos
    if resultado <= 0:
        return apology("Error, revisar", 503)
    else:
        return redirect("/")


@web_bp.route("/orden/confirmar/<int:id_orden>", methods=["POST"])
@login_required
def confirm_order(id_orden):
    """
    Confirma una orden y registra su pago inicial.

    Métodos de pago reconocidos por el sistema:
        1 -> Efectivo (pago al recoger)
        2 -> Transferencia (pago al recoger)
        3 -> Tarjeta / pago inmediato (se considera pagado en su totalidad al confirmar)

    Para los métodos 1 y 2, el pago queda pendiente de completarse (completa=False).
    Para el método 3, el monto total se registra como pagado de inmediato (completa=True).

    El estado 2 en confirmar_orden() representa "Confirmada / En proceso".
    """
    metodo_pago = int(request.form.get("metodo_pago"))
    precio_total = float(request.form.get("precio_total"))

    # Método de pago 3 (tarjeta) = pago inmediato y completo
    if metodo_pago != 3:
        # Métodos 1 y 2: Se confirma la orden y crea el pago sin monto pagado aún
        confirmar_orden(id_orden, 2)       # Estado 2: confirmada
        crear_pago(id_orden, metodo_pago, precio_total)
        return render_template("confirmed_order.html", completa=False)
    else:
        # Método 3: El total se registra inmediatamente como pagado
        confirmar_orden(id_orden, 2)       # Estado 2: confirmada
        crear_pago(id_orden, metodo_pago, precio_total, precio_total)
        return render_template("confirmed_order.html", completa=True)


@web_bp.route("/orden/completar/<int:id_orden>", methods=["POST"])
@login_required
def complete_order(id_orden):
    """
    Marca una orden como completada y registra el pago final.

    Métodos de pago en esta ruta:
        '1' -> Efectivo: se valida que la cantidad entregada sea >= al total.
        '2' -> Transferencia: se registra el total como pagado automáticamente.

    El estado 3 en confirmar_orden() representa "Completada / Entregada".

    """
    if session["user_role"] != 2:
        return apology("Error: Acceso prohibido", 403)

    id_pago = request.form.get("id_pago")
    metodo_pago = request.form.get("metodo_pago")
    cantidad_a_pagar = float(request.form.get("precio_total"))

    # Validación específica para pago en efectivo: el cliente debe pagar al menos el total
    if metodo_pago == '1':
        cantidad_pagada = float(request.form.get("cantidad_pagada"))
        print(f"Cantidad a pagar: {cantidad_a_pagar}")
        print(f"Cantidad pagada: {cantidad_pagada}")
        if cantidad_pagada < cantidad_a_pagar:
            return apology("Error: La cantidad pagada no puede ser menor que la cantidad por pagar", 400)

    # Actualizar el estado de la orden a "Completada" (estado 3)
    resultados = confirmar_orden(id_orden, 3)
    if resultados <= 0:
        return apology("Error 1, revisar", 503)

    # Registrar el pago según el método
    if metodo_pago == '1':
        # Efectivo: guardar la cantidad real entregada por el cliente
        resultados = actualizar_pago(id_pago, cantidad_a_pagar, cantidad_pagada)
    elif metodo_pago == '2':
        # Transferencia: se asume que el monto pagado es igual al total
        resultados = actualizar_pago(id_pago, cantidad_a_pagar, cantidad_a_pagar)

    if resultados <= 0:
        return apology("Error 2, revisar", 503)

    return redirect("/")


@web_bp.route("/orden/eliminar/<int:id_orden>", methods=["POST"])
@login_required
def delete_order(id_orden):
    """
    Elimina una orden del sistema por su ID.

    Redirige a la página principal si la operación es exitosa.
    """
    resultado = eliminar_orden(id_orden)
    print(f"Id de orden eliminada: {resultado}")

    # resultado <= 0 indica fallo en la operación de base de datos
    if resultado <= 0:
        return apology("Error, revisar", 503)
    else:
        return redirect("/")


# =============================================================================
# HISTORIAL
# =============================================================================

@web_bp.route("/historial")
@login_required
def view_history():
    """
    Muestra el historial de órdenes completadas del usuario autenticado.

    Solo accesible para usuarios con rol 1 (cliente). Los administradores
    (rol 2) no tienen una vista de historial definida actualmente y reciben
    un error 500.

    """
    if session["user_role"] != 1:
        # Estado inesperado del servidor: el rol no corresponde a ningún caso manejado
        # Solo los clientes pueden acceder a su historial de órdenes
        return apology("Error: Rol de usuario no identificado", 500)

    ordenes = obtener_historial(session["user_id"])
    return render_template(
        "history.html",
        name=obtener_username(session["user_id"]),
        ordenes=ordenes
    )

