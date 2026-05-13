# =============================================================================
# helpers.py — Funciones auxiliares compartidas por la web app y la REST API
#
# Este módulo agrupa tres categorías de utilidades:
#
#   1. Helpers de Flask (apology, login_required):
#      Usados exclusivamente por la interfaz web (web_bp).
#
#   2. Helpers de validación de tipos primitivos (verificar_float,
#      verificar_datetime2_7):
#      Funciones de bajo nivel reutilizadas dentro de los validadores.
#
#   3. Validadores de cuerpo JSON (validacion_json, validar_usuario,
#      validar_producto, validar_orden, validar_pago):
#      Usados exclusivamente por la API REST (api_bp). Validan estructura,
#      tipos y rangos de los datos recibidos antes de pasarlos a db_api.py.
#
# NOTA — Patrón de retorno de validadores: Todas las funciones
# validar_*() siguen el mismo contrato:
#   - Éxito:  devuelve (solicitud, None) o (solicitud, None, dato_extra)
#   - Error:  devuelve (None, (jsonify(...), código)) o (None, ..., None)
# =============================================================================

import datetime
from datetime import datetime
from flask import redirect, render_template, request, session, jsonify
from functools import wraps
from re import match
from app.db_api import obtener_cantidad_a_pagar


# =============================================================================
# HELPERS DE FLASK — Interfaz web
# =============================================================================

def apology(message, code=400):
    """
    Renderiza una página de error (apology.html) con un mensaje y código HTTP.

    El mensaje se escapa para ser compatible con la URL de generación de
    memes de memegen (https://github.com/jacebrowning/memegen#special-characters),
    que es el servicio utilizado por la plantilla apology.html para mostrar
    el mensaje visualmente.

    Argumentos:
        message → Texto del error a mostrar al usuario.
        code    → Código de estado HTTP de la respuesta (por defecto 400).

    Devuelve una tupla (respuesta_renderizada, código_http) lista para ser
    devuelta directamente desde una ruta de Flask.
    """
    def escape(s):
        """
        Escapa caracteres especiales del mensaje para compatibilidad con
        la sintaxis de URLs de memegen.
        """
        for old, new in [
            ("-", "--"),
            (" ", "-"),
            ("_", "__"),
            ("?", "~q"),
            ("%", "~p"),
            ("#", "~h"),
            ("/", "~s"),
            ('"', "''"),
        ]:
            s = s.replace(old, new)
        return s

    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorador que protege rutas de Flask requiriendo sesión activa.

    Si session["user_id"] no está definido (el usuario no ha iniciado sesión),
    redirige a /login antes de ejecutar la función decorada.

    Uso:
        @web_bp.route("/ruta-protegida")
        @login_required
        def ruta_protegida():
            ...

    Referencia: https://flask.palletsprojects.com/en/latest/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


# =============================================================================
# HELPERS DE VALIDACIÓN DE TIPOS PRIMITIVOS
# =============================================================================

def verificar_float(numero):
    """
    Intenta convertir un valor a float y lo devuelve si tiene éxito.

    Se usa en las rutas web (routes.py de web_bp) para validar campos de
    precio provenientes de formularios HTML, donde todos los valores llegan
    como strings.

    Devuelve el float si la conversión es exitosa, o None si falla
    (ej. el string no representa un número válido).

    """
    try:
        resultado = float(numero)
        return resultado
    except:
        return None

def verificar_datetime2_7(dt_string):
    """
    Valida que un string tenga el formato DATETIME2(7) de SQL Server y
    represente una fecha/hora futura respecto al momento actual.

    El formato esperado es: YYYY-MM-DD HH:MM:SS.fffffff
    (7 dígitos fraccionarios de segundo, que es la precisión máxima de
    SQL Server DATETIME2(7)).

    La validación se realiza en tres pasos:
        1. Verificar el formato con una expresión regular estricta.
        2. Parsear el string a un objeto datetime (detecta fechas
            lógicamente inválidas como el 31 de abril).
        3. Comparar con datetime.now() para asegurar que la fecha sea
            igual o posterior al momento actual.

    Devuelve True si el string es válido y la fecha es futura, False en
    cualquier otro caso.

    NOTA: Python's strptime solo soporta 6 dígitos de fracción de segundo (%f),
    por lo que se elimina el último carácter del string (el 7° dígito) antes
    de parsearlo. Esto es correcto para validación de formato, pero implica
    una pérdida de precisión del último dígito al comparar.

    """
    # Paso 1: Validar el formato mediante expresión regular
    pattern = r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{7}$"

    if not match(pattern, dt_string):
        return False

    try:
        # Paso 2: Parsear el string eliminando el 7° dígito fraccionario,
        # ya que strptime solo soporta hasta 6 dígitos con %f
        dt_obj = datetime.strptime(dt_string[:-1], "%Y-%m-%d %H:%M:%S.%f")

        # Paso 3: Verificar que la fecha sea presente o futura
        return dt_obj >= datetime.now()

    except ValueError:
        # Se lanza si la fecha es lógicamente inválida (ej. 31 de abril, mes 13)
        return False


# =============================================================================
# VALIDADORES DE CUERPO JSON — REST API
# =============================================================================

def validacion_json(claves_requeridas):
    """
    Función base de validación JSON, compartida por todos los validadores
    específicos (validar_usuario, validar_producto, validar_orden, validar_pago).

    Realiza dos verificaciones:
        1. Que el cuerpo de la solicitud sea un JSON válido y no esté vacío.
            (request.get_json(silent=True) devuelve None si el body no es JSON
            o si el Content-Type no es application/json.)
        2. Que el JSON contenga todas las claves requeridas para el recurso.

    Devuelve (solicitud, None) si la validación es exitosa.
    Devuelve (None, (jsonify(error), 400)) si falla.
    """
    # silent=True evita que Flask lance una excepción si el body no es JSON válido
    solicitud = request.get_json(silent=True)

    if not solicitud:
        return None, (jsonify({"error": "JSON de entrada no introducido"}), 400)

    # Identificar qué campos obligatorios faltan en el JSON recibido
    campos_sin_completar = [clave for clave in claves_requeridas if clave not in solicitud]
    if campos_sin_completar:
        return None, (jsonify({"error": f"Faltan los siguientes campos: {', '.join(campos_sin_completar)}"}), 400)

    return solicitud, None


def validar_usuario(claves_requeridas):
    """
    Valida los campos de un usuario recibidos en el cuerpo JSON de la solicitud.

    Primero delega la validación estructural a validacion_json() y luego
    aplica validaciones de tipo y longitud máxima sobre cada campo:

        nombre   → string, no vacío, máximo 100 caracteres
        username → string, no vacío, máximo 20 caracteres
        email    → string, no vacío, máximo 50 caracteres

    Devuelve (solicitud, None) si todos los campos son válidos.
    Devuelve (None, (jsonify(error), 400)) ante el primer error encontrado.
    """
    solicitud, error = validacion_json(claves_requeridas)
    if error:
        return None, error

    nombre = solicitud["nombre"]
    username = solicitud["username"]
    email = solicitud["email"]

    # Validaciones de 'nombre'
    if type(nombre) is not str:
        return None, (jsonify({"error": f"El campo 'Nombre' no es una cadena"}), 400)
    if nombre == '':
        return None, (jsonify({"error": f"El campo 'Nombre' cuenta con un string vacío"}), 400)
    if len(nombre) > 100:
        return None, (jsonify({"error": f"El campo 'Nombre' excede su longitud permitida (100 caracteres)"}), 400)

    # Validaciones de 'username'
    if type(username) is not str:
        return None, (jsonify({"error": f"El campo 'Username' no es una cadena"}), 400)
    if username == '':
        return None, (jsonify({"error": f"El campo 'Username' cuenta con un string vacío"}), 400)
    if len(username) > 20:
        return None, (jsonify({"error": f"El campo 'Username' excede su longitud permitida (20 caracteres)"}), 400)

    # Validaciones de 'email'
    if type(email) is not str:
        return None, (jsonify({"error": f"El campo 'Email' no es una cadena"}), 400)
    if email == '':
        return None, (jsonify({"error": f"El campo 'Email' cuenta con un string vacío"}), 400)
    if len(email) > 50:
        return None, (jsonify({"error": f"El campo 'Email' excede su longitud permitida (50 caracteres)"}), 400)

    return solicitud, None


def validar_producto(claves_requeridas):
    """
    Valida los campos de un producto recibidos en el cuerpo JSON de la solicitud.

    Primero delega la validación estructural a validacion_json() y luego
    aplica validaciones de tipo y rango sobre cada campo:

        nombre_producto → string, no vacío, máximo 100 caracteres
        precio          → int o float, mayor a 0
        disponible      → booleano estricto (True/False)

    NOTA: El tipo de 'precio' acepta tanto int como float, a diferencia de
    'cantidad' en validar_orden() que solo acepta int.

    NOTA: 'disponible' se valida como booleano estricto con type(...) is bool,
    lo que rechaza correctamente strings como "true" o enteros como 1.

    Devuelve (solicitud, None) si todos los campos son válidos.
    Devuelve (None, (jsonify(error), 400)) ante el primer error encontrado.
    """
    solicitud, error = validacion_json(claves_requeridas)
    if error:
        return None, error

    nombre_producto = solicitud["nombre_producto"]
    precio = solicitud["precio"]
    disponible = solicitud["disponible"]

    # Validaciones de 'nombre_producto'
    if type(nombre_producto) is not str:
        return None, (jsonify({"error": f"El campo 'Nombre_Producto' no es una cadena"}), 400)
    if nombre_producto == '':
        return None, (jsonify({"error": f"El campo 'Nombre_Producto' cuenta con un string vacío"}), 400)
    if len(nombre_producto) > 100:
        return None, (jsonify({"error": f"El campo 'Nombre_Producto' excede su longitud permitida (100 caracteres)"}), 400)

    # Validaciones de 'precio': debe ser numérico y positivo
    if type(precio) not in (int, float):
        return None, (jsonify({"error": f"El campo 'Precio' no es un número válido"}), 400)
    if precio <= 0:
        return None, (jsonify({"error": f"El campo 'Precio' no puede tener un valor menor o igual a 0"}), 400)

    # Validaciones de 'disponible': debe ser un booleano estricto
    if type(disponible) is not bool:
        return None, (jsonify({"error": f"El campo 'Disponible' no es un valor booleano"}), 400)

    return solicitud, None


def validar_orden(claves_requeridas):
    """
    Valida los campos de una orden recibidos en el cuerpo JSON de la solicitud.

    Primero delega la validación estructural a validacion_json() y luego
    aplica validaciones de tipo y rango sobre cada campo:

        id_usuario            → int, mayor a 0
        id_producto           → int, mayor a 0
        cantidad              → int, mayor a 0
        fecha_hora_recoleccion → string con formato DATETIME2(7) y fecha futura

    La validación de fecha_hora_recoleccion delega en verificar_datetime2_7(),
    que verifica formato, parseo e integridad temporal (fecha futura).

    Devuelve (solicitud, None) si todos los campos son válidos.
    Devuelve (None, (jsonify(error), 400)) ante el primer error encontrado.
    """
    solicitud, error = validacion_json(claves_requeridas)
    if error:
        return None, error

    id_usuario = solicitud["id_usuario"]
    id_producto = solicitud["id_producto"]
    cantidad = solicitud["cantidad"]
    fecha_hora_recoleccion = solicitud["fecha_hora_recoleccion"]

    # Validaciones de 'id_usuario': entero positivo
    if type(id_usuario) is not int:
        return None, (jsonify({"error": f"El campo 'IdUsuario' no es un número válido"}), 400)
    if id_usuario <= 0:
        return None, (jsonify({"error": f"El campo 'IdUsuario' no puede tener un valor menor o igual a 0"}), 400)

    # Validaciones de 'id_producto': entero positivo
    if type(id_producto) is not int:
        return None, (jsonify({"error": f"El campo 'IdProducto' no es un número válido"}), 400)
    if id_producto <= 0:
        return None, (jsonify({"error": f"El campo 'IdProducto' no puede tener un valor menor o igual a 0"}), 400)

    # Validaciones de 'cantidad': entero positivo
    if type(cantidad) is not int:
        return None, (jsonify({"error": f"El campo 'Cantidad' no es un número válido"}), 400)
    if cantidad <= 0:
        return None, (jsonify({"error": f"El campo 'Cantidad' no puede tener un valor menor o igual a 0"}), 400)

    # Validaciones de 'fecha_hora_recoleccion':
    # debe ser string con formato DATETIME2(7) y representar una fecha futura
    if type(fecha_hora_recoleccion) is not str:
        return None, (jsonify({"error": f"El campo 'fecha_hora_recoleccion' debe ser una cadena con formato YYYY-MM-DD HH:MM:SS.fffffff"}), 400)
    if not verificar_datetime2_7(fecha_hora_recoleccion):
        return None, (jsonify({"error": f"El campo 'fecha_hora_recoleccion' debe seguir el formato YYYY-MM-DD HH:MM:SS.fffffff y tener una hora superior a la actual"}), 400)

    return solicitud, None


def validar_pago(claves_requeridas):
    """
    Valida los campos de un pago recibidos en el cuerpo JSON de la solicitud.

    A diferencia de los otros validadores, esta función devuelve tres valores:
        (solicitud, error, cantidad_a_pagar)

    Esto se debe a que durante la validación se consulta la base de datos para
    obtener el precio total de la orden (cantidad_a_pagar), valor que la capa
    de rutas necesita para calcular el cambio/vuelto al registrar el pago.
    Si la validación falla, el tercer valor siempre es None.

    Validaciones aplicadas:

        id_orden       → int, mayor a 0
        id_metodo_pago → int, entre 1 y 3 (métodos válidos del sistema)
        cantidad_pagada → int o float, mayor a 0 y >= cantidad_a_pagar

    Entre la validación de id_metodo_pago y cantidad_pagada se realiza una
    consulta a la BD para obtener cantidad_a_pagar mediante
    obtener_cantidad_a_pagar(). Si la orden no existe o la consulta falla,
    se devuelve el error correspondiente.

    NOTA: La condición de rango de id_metodo_pago (> 0 y <= 3) asume que
    existen exactamente 3 métodos de pago en la tabla MetodoPago. Si se
    agregan nuevos métodos, esta validación deberá actualizarse manualmente.

    Devuelve (solicitud, None, cantidad_a_pagar) si todos los campos son válidos.
    Devuelve (None, (jsonify(error), 400), None) ante el primer error encontrado.
    """
    solicitud, error = validacion_json(claves_requeridas)
    if error:
        return None, error, None

    id_orden = solicitud["id_orden"]
    id_metodo_pago = solicitud["id_metodo_pago"]
    cantidad_pagada = solicitud["cantidad_pagada"]

    # Validaciones de 'id_orden': entero positivo
    if type(id_orden) is not int:
        return None, (jsonify({"error": f"El campo 'IdOrden' no es un número válido"}), 400), None
    if id_orden <= 0:
        return None, (jsonify({"error": f"El campo 'IdOrden' no puede tener un valor menor o igual a 0"}), 400), None

    # Validaciones de 'id_metodo_pago': entero entre 1 y 3 (inclusive)
    if type(id_metodo_pago) is not int:
        return None, (jsonify({"error": f"El campo 'IdMetodoPago' no es un número válido"}), 400), None
    if id_metodo_pago <= 0 or id_metodo_pago > 3:
        return None, (jsonify({"error": f"El campo 'IdMetodoPago' no puede tener un valor menor o igual a 0 o mayor que 3"}), 400), None

    # Consulta a la BD para obtener el monto total que debe pagarse por esta orden.
    # Este valor se utiliza tanto para validar cantidad_pagada como para calcularlo
    # en la capa de rutas al registrar el pago.
    cantidad_a_pagar = obtener_cantidad_a_pagar(id_orden)
    if not cantidad_a_pagar["exito"]:
        # La orden no existe o hubo un error de conexión; se devuelve el error de la BD
        return None, jsonify(cantidad_a_pagar), None
    cantidad_a_pagar = cantidad_a_pagar["data"]  # Extraer el valor numérico del dict

    # Validaciones de 'cantidad_pagada': numérico, positivo y >= monto total de la orden
    if type(cantidad_pagada) not in (int, float):
        return None, (jsonify({"error": f"El campo 'CantidadPagada' no es un número válido"}), 400), None
    if cantidad_pagada <= 0 or cantidad_pagada < cantidad_a_pagar:
        return None, (jsonify({"error": f"El campo 'CantidadPagada' no puede tener un valor menor o igual a 0 o menor a la cantidad a pagar (${cantidad_a_pagar})"}), 400), None

    # Devuelve la solicitud validada, sin error, y el monto total de la orden
    return solicitud, None, cantidad_a_pagar
