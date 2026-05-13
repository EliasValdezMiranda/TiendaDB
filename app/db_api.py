# =============================================================================
# db_api.py — Capa de acceso a datos para la REST API
#
# Este módulo es el equivalente de db.py, pero diseñado específicamente para
# servir a la REST API (api_bp). Sus diferencias clave respecto a db.py son:
#
#   1. Las consultas SQL están centralizadas en cuatro diccionarios en lugar
#      de estar embebidas dentro de cada función, lo que facilita su localización
#      y mantenimiento.
#
#   2. Las operaciones CRUD genéricas (GET, POST, PUT, DELETE) están
#      abstraídas en dos funciones reutilizables: obtener_entradas() y
#      actualizar_entradas(), que reciben una clave del diccionario SQL
#      correspondiente en lugar de construir la consulta internamente.
#
#   3. Todas las funciones Devuelven diccionarios con la clave "exito" (booleano)
#      en lugar de valores escalares (True/False/None/int), lo que facilita
#      el manejo de errores en la capa de rutas de la API.
#
# Estados de orden:
#   1 → En carrito (Recién creada)
#   2 → Confirmada (En proceso)
#   3 → Completada (también se marca como Activo = 0)
# =============================================================================

import pyodbc
import os
from dotenv import load_dotenv
import decimal


# =============================================================================
# DICCIONARIOS DE CONSULTAS SQL
#
# Las consultas están organizadas en cuatro diccionarios según el tipo de
# operación. Las funciones obtener_entradas() y actualizar_entradas() acceden
# a ellos mediante una clave string (el nombre del recurso).
#
# Ventaja: cambiar una consulta SQL solo requiere editar este bloque, sin
# necesidad de buscarla dentro de una función.
# =============================================================================

# Consultas de lectura (SELECT). Usadas por obtener_entradas().
# Las consultas con ? en el WHERE esperan un parámetro (el ID del recurso).
# Las consultas sin ? Devuelven todos los registros de la entidad.
SQL_GET_DICT = {
    # Todos los usuarios con su rol resuelto mediante JOIN
    "obtener_usuarios": """
            SELECT 
                IdUsuario,
                Rol,
                Nombre,
                Username,
                Email,
                Activo,
                FechaHoraCreacion
            FROM Usuarios
            INNER JOIN RolUsuario
            ON Usuarios.IdRolUsuario = RolUsuario.IdRolusuario;
        """,
    # Un usuario específico por ID, con su rol resuelto mediante JOIN
    "obtener_usuario": """
            SELECT 
                IdUsuario,
                Rol,
                Nombre,
                Username,
                Email,
                Activo,
                FechaHoraCreacion
            FROM Usuarios
            INNER JOIN RolUsuario
            ON Usuarios.IdRolUsuario = RolUsuario.IdRolusuario
            WHERE IdUsuario = ?;
        """,
    # Todos los productos, incluyendo inactivos
    "obtener_productos": """
            SELECT
                IdProducto,
                NombreProducto,
                Precio,
                Disponible,
                Activo,
                FechaHoraCreacion
            FROM Producto;
        """,
    # Un producto específico por ID
    "obtener_producto": """
            SELECT
                IdProducto,
                NombreProducto,
                Precio,
                Disponible,
                Activo,
                FechaHoraCreacion
            FROM Producto
            WHERE IdProducto = ?;
        """,
    # Todas las órdenes del sistema, sin filtro de estado ni de actividad.
    "obtener_ordenes": """
            SELECT IdOrden,
                Estado,
                Usuarios.Nombre,
                Producto.NombreProducto,
                Cantidad,
                FechaHoraRecoleccion,
                Orden.Activo,
                Orden.FechaHoraCreacion
            FROM Orden
            INNER JOIN EstadoOrden
            ON Orden.IdEstado = EstadoOrden.IdEstado
            INNER JOIN Usuarios
            ON Orden.IdUsuario = Usuarios.IdUsuario
            INNER JOIN Producto
            ON Orden.IdProducto = Producto.IdProducto;
        """,
    # Una orden específica por ID
    "obtener_orden": """
            SELECT IdOrden,
                Estado,
                Usuarios.Nombre,
                Producto.NombreProducto,
                Cantidad,
                FechaHoraRecoleccion,
                Orden.Activo,
                Orden.FechaHoraCreacion
            FROM Orden
            INNER JOIN EstadoOrden
            ON Orden.IdEstado = EstadoOrden.IdEstado
            INNER JOIN Usuarios
            ON Orden.IdUsuario = Usuarios.IdUsuario
            INNER JOIN Producto
            ON Orden.IdProducto = Producto.IdProducto
            WHERE Orden.IdOrden = ?;
        """,
    # Todos los pagos con el nombre del método de pago resuelto mediante JOIN
    "obtener_pagos": """
            SELECT IdPago,
                IdOrden,
                Metodo AS MetodoDePago,
                CantidadAPagar,
                CantidadPagada,
                CantidadRegresada,
                FechaHoraCreacion
            FROM Pago
            INNER JOIN MetodoPago
            ON Pago.IdMetodoPago = MetodoPago.IdMetodoPago
    """,
    # Un pago específico por ID
    "obtener_pago": """
            SELECT IdPago,
                IdOrden,
                Metodo AS MetodoDePago,
                CantidadAPagar,
                CantidadPagada,
                CantidadRegresada,
                FechaHoraCreacion
            FROM Pago
            INNER JOIN MetodoPago
            ON Pago.IdMetodoPago = MetodoPago.IdMetodoPago
            WHERE IdPago = ?
    """
}

# Consultas de inserción (INSERT). Usadas por actualizar_entradas() con operacion='POST'.
# Todas van acompañadas de SET NOCOUNT ON y SELECT SCOPE_IDENTITY() en actualizar_entradas()
# para obtener el ID del registro recién creado.
# NOTA: No existe entrada para "usuarios" porque la creación de usuarios se maneja
# mediante un procedimiento almacenado en agregar_usuario(), no con un INSERT directo.
SQL_INSERT_DICT = {
    "producto": """
            INSERT INTO Producto (NombreProducto, Precio, Disponible)
            VALUES (?, ?, ?);
    """,
    "orden": """
            INSERT INTO Orden (IdUsuario, IdProducto, Cantidad, FechaHoraRecoleccion)
            VALUES (?, ?, ?, ?);
    """,
    "pago": """
            INSERT INTO Pago (IdOrden, IdMetodoPago, CantidadAPagar, CantidadPagada, CantidadRegresada)
            VALUES (?, ?, ?, ?, ?);
    """
}

# Consultas de actualización (UPDATE). Usadas por actualizar_entradas() con operacion='PUT'.
# El último parámetro (?) en cada consulta corresponde siempre al ID del registro a actualizar.
SQL_UPDATE_DICT = {
    # Actualiza nombre, username y email. No permite cambiar contraseña ni rol desde la API.
    "usuarios": """
            UPDATE Usuarios
            SET
                Nombre = ?,
                Username = ?,
                Email = ?
            WHERE IdUsuario = ?
        """,
    "producto": """
            UPDATE Producto
            SET 
                NombreProducto = ?, 
                Precio = ?, 
                Disponible = ?
            WHERE IdProducto = ?;
    """,
    # Permite actualizar todos los campos de la orden, incluyendo usuario y producto.
    "orden": """
            UPDATE Orden
            SET
                IdUsuario = ?,
                IdProducto = ?,
                Cantidad = ?,
                FechaHoraRecoleccion = ?
            WHERE IdOrden = ?;
    """,
    # Permite actualizar todos los campos financieros del pago.
    # NOTA: CantidadRegresada se calcula y envía desde el archivo helpers.py (funcion validar_pago)
    "pago": """
            UPDATE Pago
            SET
                IdOrden = ?,
                IdMetodoPago = ?,
                CantidadAPagar = ?,
                CantidadPagada = ?, 
                CantidadRegresada = ?
            WHERE IdPago = ?;
    """
}

# Consultas de eliminación (DELETE). Usadas por actualizar_entradas() con operacion='DELETE'.
SQL_DELETE_DICT = {
    "usuarios": """
            DELETE FROM Usuarios
            WHERE IdUsuario = ?
    """,
    "producto": """
            DELETE FROM Producto
            WHERE IdProducto = ?;
    """,
    "orden": """
            DELETE FROM Orden
            WHERE IdOrden = ?;
    """,
    "pago": """
            DELETE FROM Pago
            WHERE IdPago = ?
    """
}


# =============================================================================
# CONEXIÓN
# =============================================================================

def get_sql_connection():
    """
    Crea y Devuelve una conexión activa a la base de datos SQL Server.

    Idéntica a la función homónima en db.py. Lee las credenciales desde
    variables de entorno definidas en el archivo .env:
        DB_SERVER, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD

    Devuelve la conexión si tiene éxito, o None si falla.

    """
    load_dotenv()

    # Leer credenciales desde el entorno
    server = os.getenv('DB_SERVER')
    port = os.getenv('DB_PORT')
    database = os.getenv('DB_NAME')
    username = os.getenv('DB_USER')
    password = os.getenv('DB_PASSWORD')

    # Construir el string de conexión para pyodbc
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server},{port};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"  # Útil para entornos de desarrollo local sin SSL
    )

    try:
        conn = pyodbc.connect(conn_str)
        print("Successfully connected to the database!")
        return conn
    except Exception as e:
        print(f"Error while connecting: {e}")
        return None


# =============================================================================
# OPERACIONES GENÉRICAS CRUD
# =============================================================================

def obtener_entradas(sql_clave, params=None):
    """
    Función genérica de lectura. Ejecuta la consulta SELECT asociada a
    sql_clave en SQL_GET_DICT y Devuelve los resultados como lista de diccionarios.

    Argumentos:
        sql_clave → Clave del diccionario SQL_GET_DICT (ej. "obtener_usuarios").
        params    → Parámetros opcionales para la consulta (ej. el ID del recurso).
                    Si es None, se ejecuta la consulta sin parámetros (Devuelve todos
                    los registros). Si se proporciona, se filtra por ese valor.

    Devuelve una lista de diccionarios si la consulta es exitosa (puede ser
    una lista vacía si no hay registros).

    Devuelve un diccionario {"exito": False, "error": "..."} si la conexión
    falla o si ocurre una excepción.

    """
    connection = get_sql_connection()
    if not connection:
        return {"exito": False, "error": "Conexión a la base de datos fallida"}

    cursor = connection.cursor()

    # Obtener la consulta SQL del diccionario centralizado
    sql = SQL_GET_DICT[sql_clave]

    try:
        if params == None:
            # Consulta sin filtro: Devuelve todos los registros de la entidad
            cursor.execute(sql)
        else:
            # Consulta con parámetro: filtra por el valor proporcionado (generalmente un ID)
            cursor.execute(sql, params)

        # Convertir los objetos pyodbc.Row a diccionarios para serialización JSON
        columns = [column[0] for column in cursor.description]
        entradas = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return entradas

    except Exception as e:
        return {"exito": False, "error": "Error al obtener entradas"}
    finally:
        connection.close()


def actualizar_entradas(operacion, sql_clave, params=None):
    """
    Función genérica de escritura. Ejecuta operaciones INSERT, UPDATE o DELETE
    sobre la base de datos según el método HTTP recibido como argumento.

    Argumentos:
        operacion → Método HTTP como string: 'POST' (insertar), 'PUT' (actualizar)
                    o 'DELETE' (eliminar). Determina qué diccionario SQL se utiliza.
        sql_clave → Clave del diccionario SQL correspondiente (ej. "producto", "orden").
        params    → Tupla de parámetros para la consulta SQL.

    Para operaciones POST (INSERT):
        Antepone SET NOCOUNT ON para suprimir el mensaje de filas afectadas y
        añade SELECT SCOPE_IDENTITY() para recuperar el ID del registro creado.
        Devuelve {"exito": True, "id_nueva_entrada": <id>}.

    Para operaciones PUT y DELETE:
        Devuelve {"exito": True, "columnas_afectadas": <rowcount>}.

    En caso de error:
        Devuelve {"exito": False, "error": <mensaje>}.

    """
    connection = get_sql_connection()
    if not connection:
        return {"exito": False, "error": "Conexión a la base de datos fallida"}

    cursor = connection.cursor()

    # Seleccionar la consulta SQL del diccionario correspondiente según la operación
    if operacion == 'POST':
        # SET NOCOUNT ON suprime el mensaje de filas afectadas para que
        # pyodbc pueda leer el resultado de SCOPE_IDENTITY() directamente
        sql = f"SET NOCOUNT ON; {SQL_INSERT_DICT[sql_clave]}; SELECT SCOPE_IDENTITY();"
    elif operacion == 'PUT':
        sql = SQL_UPDATE_DICT[sql_clave]
    elif operacion == 'DELETE':
        sql = SQL_DELETE_DICT[sql_clave]

    try:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        if "INSERT" in sql.upper():
            # Recuperar el ID autoincremental generado por el INSERT
            last_id_row = cursor.fetchone()
            last_id = last_id_row[0] if last_id_row else None

        # Capturar el número de filas afectadas (válido para PUT y DELETE)
        rows_affected = cursor.rowcount

        connection.commit()

        if operacion == 'POST':
            return {
                "exito": True,
                "id_nueva_entrada": last_id
            }
        else:
            # Para PUT y DELETE: Devuelve cuántas filas fueron afectadas
            return {
                "exito": True,
                "columnas_afectadas": rows_affected
            }

    except Exception as e:
        connection.rollback()
        print(f"Database error: {e}")
        return {"exito": False, "error": str(e)}
    finally:
        connection.close()


# =============================================================================
# USUARIOS
# =============================================================================

def agregar_usuario(nombre, username, email, password):
    """
    Registra un nuevo usuario llamando al procedimiento almacenado
    [dbo].[stpAgregarUsuario], de forma idéntica a db.py.

    El rol se asigna automáticamente como 1 (cliente regular).

    A diferencia de su equivalente en db.py, esta versión:
        - Devuelve un diccionario {"exito": True/False, ...} en lugar de una tupla.
        - Interpreta explícitamente id_usuario == 0 como fallo del SP (ej. usuario
        duplicado), devolviendo el mensaje de error del SP en ese caso.
        - No expone el ID del usuario creado en la respuesta exitosa.

    Devuelve {"exito": True, "Mensaje": "..."} si el usuario fue creado.
    Devuelve {"exito": False, "Mensaje": <msg_sp>} si el SP reportó un error (id == 0).
    Devuelve {"exito": False, "error": <excepción>} si ocurre una excepción.
    """
    connection = get_sql_connection()
    if not connection:
        return {"exito": False, "error": "Conexión a la base de datos fallida"}

    cursor = connection.cursor()

    # Bloque T-SQL para capturar los parámetros OUTPUT del SP mediante un SELECT final
    sql = """
        DECLARE @out_id INT;
        DECLARE @out_msg NVARCHAR(500);

        EXEC [dbo].[stpAgregarUsuario] 
            @Nombre = ?, 
            @IdRolUsuario = ?, 
            @Username = ?, 
            @Email = ?, 
            @Password = ?, 
            @IDUsuario = @out_id OUTPUT, 
            @Mensaje = @out_msg OUTPUT;

        SELECT @out_id AS IDUsuario, @out_msg AS Mensaje;
    """

    # El rol 1 (cliente) se asigna por defecto a todos los usuarios registrados desde la API
    params = (nombre, 1, username, email, password)

    try:
        cursor.execute(sql, params)
        result = cursor.fetchone()

        id_usuario = result[0]
        mensaje = result[1]

        # El SP Devuelve id_usuario == 0 para indicar un error de validación
        # (ej. username o email ya registrados). En ese caso no se hace commit.
        if id_usuario == 0:
            return {"exito": False, "Mensaje": mensaje}

        # El INSERT dentro del SP requiere commit explícito para persistir los datos
        connection.commit()

        print(f"Server Response: {mensaje}")
        print(f"New User ID: {id_usuario}")

        return {"exito": True, "Mensaje": f"Usuario con ID #{id_usuario} creado"}

    except Exception as e:
        print(f"An error occurred: {e}")
        connection.rollback()
        return {"exito": False, "error": e}
    finally:
        connection.close()


# =============================================================================
# PAGOS Y ÓRDENES — OPERACIONES ESPECIALIZADAS
# =============================================================================

def obtener_cantidad_a_pagar(IdOrden):
    """
    Calcula y Devuelve el precio total de una orden (Cantidad * Precio del producto).

    Se utiliza en la capa de helpers (validar_pago) para obtener el monto
    que debe pagarse antes de registrar o actualizar un pago.

    Maneja la conversión de Decimal a float, ya que SQL Server puede devolver
    valores monetarios como decimal.Decimal, que no es serializable a JSON.

    Devuelve {"exito": True, "data": <float>} si la orden existe.
    Devuelve {"exito": False, "error": "..."} si la orden no existe, la conexión
    falla, u ocurre una excepción.
    """
    connection = get_sql_connection()
    if not connection:
        return {"exito": False, "error": "Conexión fallida"}

    cursor = connection.cursor()

    # Calcular el precio total multiplicando cantidad por precio unitario del producto
    sql = """
            SELECT (Cantidad * Precio) AS PrecioTotal
            FROM Orden
            INNER JOIN Producto ON Orden.IdProducto = Producto.IdProducto
            WHERE IdOrden = ?
    """

    params = (IdOrden,)

    try:
        cursor.execute(sql, params)
        result = cursor.fetchone()

        if result is None:
            return {"exito": False, "error": f"No se encontró la orden {IdOrden}"}

        valor = result[0]

        # SQL Server devuelve valores calculados con Precio como decimal.Decimal.
        # Se convierte a float para compatibilidad con JSON y operaciones aritméticas.
        if isinstance(valor, decimal.Decimal):
            valor = float(valor)

        return {"exito": True, "data": valor}

    except Exception as e:
        return {"exito": False, "error": str(e)}
    finally:
        connection.close()


def verificar_pago_existente(IdOrden):
    """
    Verifica si existe al menos un registro de pago asociado a una orden.

    Se usa en confirmar_orden_id (routes.py de la API) como precondición:
    no se puede confirmar una orden si no tiene un pago registrado.

    Utiliza SELECT TOP 1 1 para minimizar la lectura: solo comprueba
    existencia sin traer datos adicionales del registro.

    Devuelve {"exito": True, "Mensaje": "Pago encontrado"} si existe el pago.
    Devuelve {"exito": False, "error": "..."} si no existe, la conexión falla,
    u ocurre una excepción.
    """
    connection = get_sql_connection()
    if not connection:
        return {"exito": False, "error": "Conexión a la base de datos fallida"}

    cursor = connection.cursor()

    # SELECT TOP 1 1: Devuelve una fila con el valor 1 si existe al menos un pago,
    # o ninguna fila si no existe. Es más eficiente que COUNT(*) para verificar existencia.
    sql = """
            SELECT TOP 1 1
            FROM Pago
            WHERE IdOrden = ?
    """
    params = (IdOrden,)

    try:
        cursor.execute(sql, params)
        result = cursor.fetchone()

        # Si result no es None, se encontró al menos un pago para esta orden
        if result:
            return {"exito": True, "Mensaje": "Pago encontrado"}
        else:
            return {"exito": False, "error": f"No existe un registro de pago para la orden #{IdOrden}"}

    except Exception as e:
        print(f"Error al verificar pago: {e}")
        return {"exito": False, "error": str(e)}
    finally:
        connection.close()


def confirmar_orden(IdOrden):
    """
    Cambia el estado de una orden a 2 (Confirmada), siempre que la orden
    esté activa (Activo = 1).

    La condición AND Activo = 1 en el WHERE sirve como salvaguarda para
    evitar reactivar órdenes que ya fueron completadas y desactivadas.

    Devuelve {"exito": True, "Mensaje": "..."} si la orden fue actualizada
    (rowcount > 0).
    Devuelve {"exito": False, "error": "Orden no actualizada"} si el WHERE
    no coincidió con ninguna fila (orden no existe, ya está inactiva, o
    ya tenía estado 2).
    Devuelve {"exito": False, "error": <excepción>} si ocurre un error.

    """
    connection = get_sql_connection()
    if not connection:
        return {"exito": False, "error": "Conexión a la base de datos fallida"}

    cursor = connection.cursor()

    # Solo se actualiza si la orden existe y está activa (Activo = 1)
    sql = """
            UPDATE Orden
            SET IdEstado = 2
            WHERE IdOrden = ?
            AND Activo = 1;
    """
    params = (IdOrden,)

    try:
        cursor.execute(sql, params)
        if cursor.rowcount > 0:
            # Confirmar la transacción solo si se modificó al menos una fila
            connection.commit()
            return {"exito": True, "Mensaje": f"Orden #{IdOrden} confirmada"}
        # rowcount == 0: la orden no existe, ya está inactiva, o ya tenía estado 2
        return {"exito": False, "error": "Orden no actualizada"}

    except Exception as e:
        print(f"Ocurrió un error al actualizar la orden: {e}")
        connection.rollback()
        return {"exito": False, "error": str(e)}
    finally:
        connection.close()


def finalizar_orden(IdOrden):
    """
    Marca una orden como completada (IdEstado = 3) y la desactiva (Activo = 0),
    efectuando un borrado lógico.

    A diferencia de confirmar_orden(), esta función realiza una validación
    previa del estado actual antes de ejecutar el UPDATE, en dos pasos:

        1. Verificar que la orden exista y leer su IdEstado actual.
        2. Validar que IdEstado sea 2 (Confirmada). Si no lo es, Devuelve error
        con el estado actual para facilitar el diagnóstico.
        3. Ejecutar el UPDATE a IdEstado = 3 y Activo = 0.

    Las órdenes finalizadas (Activo = 0) no aparecen en obtener_ordenes()
    de db.py, pero sí en obtener_historial() y en las consultas de db_api.py
    que no filtran por Activo.

    Devuelve {"exito": True, "mensaje": "..."} si la orden fue finalizada.
    Devuelve {"exito": False, "error": "..."} en cualquier caso de fallo.

    """
    connection = get_sql_connection()
    if not connection:
        return {"exito": False, "error": "Conexión a la base de datos fallida"}

    cursor = connection.cursor()

    try:
        # Paso 1: Verificar que la orden exista y obtener su estado actual
        sql_check = "SELECT IdEstado FROM Orden WHERE IdOrden = ?"
        cursor.execute(sql_check, (IdOrden,))
        result = cursor.fetchone()

        if not result:
            return {"exito": False, "error": f"La orden #{IdOrden} no existe"}

        id_estado_actual = result[0]

        # Paso 2: Validar que la orden esté en estado 2 (Confirmada) antes de finalizar.
        # No se puede completar una orden que aún no ha sido confirmada.
        if id_estado_actual != 2:
            return {
                "exito": False,
                "error": f"La orden #{IdOrden} no se puede finalizar porque su estado es {id_estado_actual} (se requiere estado 2)"
            }

        # Paso 3: Marcar como completada (estado 3) y desactivar (borrado lógico)
        sql_update = """
            UPDATE Orden
            SET IdEstado = 3,
                Activo = 0
            WHERE IdOrden = ?
        """
        cursor.execute(sql_update, (IdOrden,))

        connection.commit()
        return {"exito": True, "mensaje": f"Orden #{IdOrden} finalizada y desactivada correctamente"}

    except Exception as e:
        connection.rollback()
        print(f"Error al finalizar orden: {e}")
        return {"exito": False, "error": str(e)}
    finally:
        connection.close()
