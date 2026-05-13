# =============================================================================
# db.py — Capa de acceso a datos para la interfaz web
#
# Este módulo contiene todas las funciones que interactúan directamente con la
# base de datos SQL Server a través de pyodbc. Cada función abre su propia
# conexión, ejecuta la operación y la cierra en el bloque finally.
#
# =============================================================================

import pyodbc
import os
from dotenv import load_dotenv


# =============================================================================
# CONEXIÓN
# =============================================================================

def get_sql_connection():
    """
    Crea y Devuelve una conexión activa a la base de datos SQL Server.

    Lee las credenciales de conexión desde variables de entorno definidas
    en el archivo .env:
        DB_SERVER   → Dirección del servidor
        DB_PORT     → Puerto (por defecto 1433 en SQL Server)
        DB_NAME     → Nombre de la base de datos
        DB_USER     → Usuario de la base de datos
        DB_PASSWORD → Contraseña

    Utiliza el driver "ODBC Driver 17 for SQL Server". Si el entorno tiene
    instalada la versión 18, es necesario actualizar el string de conexión.
    TrustServerCertificate=yes está habilitado para facilitar el desarrollo
    local sin certificados SSL válidos.

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
        "TrustServerCertificate=yes;"
    )

    try:
        conn = pyodbc.connect(conn_str)
        print("Conexión exitosa con la base de datos!")
        return conn
    except Exception as e:
        print(f"Error: {e}")
        return None


# =============================================================================
# USUARIOS
# =============================================================================

def obtener_usuarios():
    """
    Devuelve la lista completa de usuarios registrados en el sistema.

    Realiza un JOIN entre Usuarios y RolUsuario para incluir el nombre
    del rol (en lugar del ID) en el resultado.

    Devuelve una lista de diccionarios con las claves:
        IdUsuario, Rol, Nombre, Username, Email, Activo, FechaHoraCreacion

    Devuelve [] si la conexión falla o si ocurre un error en la consulta.
    """
    connection = get_sql_connection()
    if not connection:
        return []

    cursor = connection.cursor()

    sql = """
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
        """

    try:
        cursor.execute(sql)

        # Convertir los objetos pyodbc.Row a diccionarios para facilitar
        # su uso en las plantillas Jinja y en la capa de presentación
        columns = [column[0] for column in cursor.description]
        usuarios = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return usuarios

    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        connection.close()


def agregar_usuario(nombre, username, email, password):
    """
    Registra un nuevo usuario en el sistema llamando al procedimiento
    almacenado [dbo].[stpAgregarUsuario].

    El rol se asigna automáticamente como 1 (cliente regular), sin que
    el llamador pueda especificar otro valor.

    El procedimiento Devuelve dos parámetros de salida a través de un SELECT:
        IDUsuario -> ID del nuevo usuario creado (entero positivo), o un código
                    de error negativo si la operación falló (ej. usuario duplicado).
        Mensaje   -> Texto descriptivo del resultado de la operación.

    Devuelve una tupla (id_usuario, mensaje) si la operación es exitosa.
    Devuelve None implícitamente si la conexión falla o si ocurre una excepción.

    """
    connection = get_sql_connection()
    if not connection:
        return

    cursor = connection.cursor()

    # Bloque T-SQL necesario para capturar los parámetros OUTPUT del procedimiento.
    # Se declaran variables locales, se ejecuta el SP y se Devuelven los resultados
    # mediante un SELECT final que pyodbc puede leer con fetchone().
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

    # El rol 1 (cliente) se asigna por defecto a todos los usuarios registrados
    params = (nombre, 1, username, email, password)

    try:
        cursor.execute(sql, params)
        result = cursor.fetchone()

        id_usuario = result[0]
        mensaje = result[1]

        # El INSERT dentro del SP requiere commit explícito para persistir los datos
        connection.commit()

        print(f"Id del nuevo usuario: {id_usuario}")

        return id_usuario, mensaje

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        # Revertir cambios si ocurrió un error
        connection.rollback()
    finally:
        connection.close()


def verificar_password(username_or_email, password):
    """
    Verifica las credenciales de un usuario llamando a la función escalar
    [dbo].[ufnVerificarPassword].

    Acepta tanto el nombre de usuario como el correo electrónico como
    primer argumento (la función SQL maneja ambos casos internamente).

    Valores de retorno de la función SQL:
        >0  -> ID del usuario autenticado correctamente
        -1   -> Credenciales inválidas (usuario no encontrado o contraseña incorrecta)

    Valores de retorno de esta función Python:
        0   -> Fallo de conexión con la base de datos
        -1   -> Credenciales inválidas o error durante la ejecución

    """
    connection = get_sql_connection()
    if not connection:
        # Código de error que indica fallo de conexión
        return 0

    cursor = connection.cursor()

    # Las funciones escalares de SQL Server se llaman mediante SELECT
    sql = "SELECT [dbo].[ufnVerificarPassword](?, ?)"

    try:
        cursor.execute(sql, (username_or_email, password))

        # La función Devuelve un escalar; se lee como la primera columna de la primera fila
        result = cursor.fetchone()
        user_id = result[0] if result else -1

        if user_id != -1:
            print(f"Inicio de sesión exitoso! ID de Usuario: {user_id}")
        else:
            print("Inicio de sesión fallido: Credenciales inválidas.")

        return user_id

    except Exception as e:
        print(f"Ocurrió un error:: {e}")
        return -1
    finally:
        connection.close()


def obtener_username(IdUsuario):
    """
    Devuelve el nombre de usuario (Username) asociado a un ID de usuario.

    Se utiliza para mostrar el nombre del usuario autenticado
    en la interfaz.

    Devuelve el string con el Username si se encuentra, o None si ocurre un error.

    """
    connection = get_sql_connection()
    if not connection:
        return

    cursor = connection.cursor()

    sql = """
        SELECT Username FROM Usuarios WHERE IdUsuario = ?;
    """

    params = (IdUsuario,)

    try:
        cursor.execute(sql, params)
        result = cursor.fetchone()

        username = result[0]
        print(f"Nombre de usuario: {username}")

        return username

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        connection.rollback()
    finally:
        connection.close()


def obtener_rol_usuario(IdUsuario):
    """
    Devuelve el ID del rol asociado a un usuario (IDRolUsuario).

    El valor Devuelvedo se almacena en session["user_role"] al iniciar sesión
    y se utiliza en todas las rutas para diferenciar el comportamiento entre
    clientes (rol 1) y administradores (rol 2).

    Devuelve el entero con el ID del rol si se encuentra, o None implícitamente
    si ocurre un error.

    """
    connection = get_sql_connection()
    if not connection:
        return

    cursor = connection.cursor()

    sql = """
        SELECT IDRolUsuario FROM Usuarios WHERE IdUsuario = ?;
    """

    params = (IdUsuario,)

    try:
        cursor.execute(sql, params)
        result = cursor.fetchone()

        rol_usuario = result[0]
        print(f"Rol del usuario: {rol_usuario}")

        return rol_usuario

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        connection.rollback()
    finally:
        connection.close()


# =============================================================================
# ÓRDENES
# =============================================================================

def obtener_ordenes(id_usuario=None):
    """
    Devuelve las órdenes activas del sistema, con dos comportamientos según
    si se proporciona o no un ID de usuario.

    Sin argumento (admin):
        Devuelve TODAS las órdenes con estado 2 (Confirmadas), incluyendo
        información de pago (IdPago, IdMetodoPago, MetodoPago). Requiere
        JOIN con las tablas Pago y MetodoPago.

    Con id_usuario (cliente):
        Devuelve únicamente las órdenes activas del usuario especificado,
        sin importar el estado. No incluye información de pago.

    Devuelve una lista de diccionarios, o [] si hay un error de conexión o consulta.

    NOTA: La consulta de admin filtra por IdEstado = 2 (Confirmadas), por lo que las órdenes
    en estado 1 (En carrito) no son visibles para el administrador en esta vista.

    """
    connection = get_sql_connection()
    if not connection:
        return []

    cursor = connection.cursor()

    if id_usuario != None:
        # Consulta para cliente: órdenes activas propias, sin datos de pago
        sql = """
            SELECT
                IdOrden,
                NombreProducto,
                Usuarios.Nombre,
                Precio AS PrecioUnidad,
                Cantidad,
                (Cantidad * Precio) AS PrecioTotal,
                Orden.IdEstado,
                Estado,
                FechaHoraRecoleccion 
            FROM Orden
                INNER JOIN EstadoOrden
                ON Orden.IdEstado = EstadoOrden.IdEstado
                INNER JOIN Producto
                ON Orden.IdProducto = Producto.IdProducto
                INNER JOIN Usuarios
                ON Orden.IdUsuario = Usuarios.IdUsuario
            WHERE Orden.Activo = 1 AND Orden.IdUsuario = ?
            ORDER BY FechaHoraRecoleccion ASC;
        """
        params = (id_usuario,)
    else:
        # Consulta para admin: todas las órdenes confirmadas (estado 2),
        # incluyendo datos de pago para su gestión
        sql = """
            SELECT
                Orden.IdOrden,
                Usuarios.Nombre,
                NombreProducto,
                Precio AS PrecioUnidad,
                Cantidad,
                (Cantidad * Precio) AS PrecioTotal,
                Pago.IdPago,
                Pago.IdMetodoPago,
                MetodoPago.Metodo,
                Orden.IdEstado,
                Estado,
                FechaHoraRecoleccion 
            FROM Orden
                INNER JOIN EstadoOrden
                ON Orden.IdEstado = EstadoOrden.IdEstado
                INNER JOIN Producto
                ON Orden.IdProducto = Producto.IdProducto
                INNER JOIN Usuarios
                ON Orden.IdUsuario = Usuarios.IdUsuario
                INNER JOIN Pago
                ON Orden.IdOrden = Pago.IdOrden
                INNER JOIN MetodoPago
                ON Pago.IdMetodoPago = MetodoPago.IdMetodoPago
            WHERE Orden.Activo = 1 AND Orden.IdEstado = 2
            ORDER BY FechaHoraRecoleccion ASC;
        """

    try:
        if id_usuario != None:
            # La consulta de cliente requiere el parámetro id_usuario
            cursor.execute(sql, params)
        else:
            # La consulta de admin no lleva parámetros
            cursor.execute(sql)

        # Convertir los objetos pyodbc.Row a diccionarios para facilitar
        # su uso en las plantillas Jinja
        columns = [column[0] for column in cursor.description]
        ordenes = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return ordenes

    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        connection.close()


def agregar_orden(id_usuario, id_producto, cantidad, fecha_hora_recoleccion):
    """
    Inserta una nueva entrada en la entidad Orden.

    La orden se crea con los valores por defecto de la entidad para IdEstado
    (1 = En carrito) y Activo = 1, ya que no se especifican explícitamente
    en el INSERT.

    Devuelve True si la inserción fue exitosa, False de lo contrario.

    """
    connection = get_sql_connection()
    if not connection:
        return False

    cursor = connection.cursor()

    sql = """
        INSERT INTO Orden (IdUsuario, IdProducto, Cantidad, FechaHoraRecoleccion)
        VALUES (?, ?, ?, ?);
    """

    params = (id_usuario, id_producto, cantidad, fecha_hora_recoleccion)

    try:
        cursor.execute(sql, params)
        # El INSERT requiere commit explícito para persistir los datos
        connection.commit()
        return True

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        # Revertir el INSERT si ocurrió un error
        connection.rollback()
        return False
    finally:
        connection.close()


def actualizar_orden(id_orden, cantidad):
    """
    Actualiza la cantidad de productos de una orden existente.

    Devuelve True si la actualización afectó al menos una fila.
    Devuelve False si no se encontró la orden o si ocurrió un error.

    """
    connection = get_sql_connection()
    if not connection:
        return False

    cursor = connection.cursor()

    sql = """
        UPDATE Orden
        SET Cantidad = ?
        WHERE IdOrden = ?;
    """
    params = (cantidad, id_orden)

    try:
        cursor.execute(sql, params)
        if cursor.rowcount > 0:
            # Confirmar la transacción solo si se modificó al menos una fila
            connection.commit()
            return True
        return False

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        # Revertir cambios si ocurrió un error
        connection.rollback()
        return False
    finally:
        connection.close()


def confirmar_orden(id_orden, id_estado):
    """
    Actualiza el estado de una orden y, si corresponde, la desactiva.

    El comportamiento varía según el valor de id_estado:
        id_estado != 3 → Solo actualiza IdEstado (pasar a estado 2: Confirmada).
        id_estado == 3 → Actualiza IdEstado a 3 (Completada) Y establece Activo = 0,
                            lo que efectúa un borrado lógico de la orden.
                            Las órdenes con Activo = 0 no aparecen en obtener_ordenes().

    Devuelve True si la actualización afectó al menos una fila, False en caso contrario.

    """
    connection = get_sql_connection()
    if not connection:
        return False

    cursor = connection.cursor()

    if id_estado != 3:
        # Estados 1 y 2: solo actualizar el estado de la orden
        sql = """
                UPDATE Orden
                SET IdEstado = ?
                WHERE IdOrden = ?;
            """
    else:
        # Estado 3 (Completada): actualizar estado y desactivar la orden (borrado lógico)
        sql = """
                UPDATE Orden
                SET IdEstado = ?,
                    Activo = 0
                WHERE IdOrden = ?;
            """
    params = (id_estado, id_orden)

    try:
        cursor.execute(sql, params)
        if cursor.rowcount > 0:
            # Confirmar la transacción solo si se modificó al menos una fila
            connection.commit()
            return True
        return False

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        # Revertir cambios si ocurrió un error
        connection.rollback()
        return False
    finally:
        connection.close()


def eliminar_orden(id_orden):
    """
    Elimina físicamente una orden de la tabla Orden (borrado definitivo).

    A diferencia de confirmar_orden() con id_estado=3, esta función ejecuta
    un DELETE real en lugar de un borrado lógico (Activo = 0).

    Devuelve el id_orden si la eliminación fue exitosa (rowcount > 0).
    Devuelve False si ocurre una excepción.
    Devuelve None implícitamente si rowcount == 0 (orden no encontrada),
    ya que no hay un return explícito en ese caso.

    """
    connection = get_sql_connection()
    if not connection:
        return None

    cursor = connection.cursor()

    sql = """
        DELETE FROM Orden
        WHERE IdOrden = ?;
    """
    params = (id_orden,)

    try:
        cursor.execute(sql, params)
        if cursor.rowcount > 0:
            connection.commit()
            return id_orden
        # NOTA: si rowcount == 0, la función Devuelve None implícitamente
        # (ninguna orden fue eliminada porque no existía el ID)

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()


# =============================================================================
# PRODUCTOS
# =============================================================================

def obtener_productos():
    """
    Devuelve el catálogo de productos activos (Activo = 1).

    Los productos desactivados (Activo = 0) no se incluyen en el resultado.

    Devuelve una lista de diccionarios con las claves:
        IdProducto, NombreProducto, Precio, Disponible

    Devuelve [] si la conexión falla o si ocurre un error en la consulta.
    """
    connection = get_sql_connection()
    if not connection:
        return []

    cursor = connection.cursor()

    # Solo se Devuelven productos activos en el sistema
    sql = """
        SELECT IdProducto, NombreProducto, Precio, Disponible 
        FROM Producto 
        WHERE Activo = 1;
    """

    try:
        cursor.execute(sql)

        # Convertir los objetos pyodbc.Row a diccionarios para facilitar
        # su uso en las plantillas Jinja y en las respuestas JSON
        columns = [column[0] for column in cursor.description]
        productos = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return productos

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        return []
    finally:
        connection.close()


def agregar_producto(nombre, precio, disponible):
    """
    Inserta un nuevo producto en la tabla Producto y Devuelve su ID.

    Utiliza un batch T-SQL con SET NOCOUNT ON para suprimir el mensaje de
    filas afectadas del INSERT, seguido de SELECT SCOPE_IDENTITY() para
    obtener el ID autoincremental recién generado.

    Devuelve el ID entero del producto creado si la operación es exitosa.
    Devuelve False si no se pudo obtener el ID o si ocurre un error.

    """
    connection = get_sql_connection()
    if not connection:
        return None

    cursor = connection.cursor()

    # SET NOCOUNT ON suprime el mensaje de filas afectadas para que
    # pyodbc pueda leer directamente el resultado de SCOPE_IDENTITY()
    sql = """
        SET NOCOUNT ON
        INSERT INTO Producto (NombreProducto, Precio, Disponible)
        VALUES (?, ?, ?);
        SELECT SCOPE_IDENTITY();
    """
    params = (nombre, precio, disponible)

    try:
        cursor.execute(sql, params)

        # SCOPE_IDENTITY() Devuelve el ID como escalar en la primera fila
        row = cursor.fetchone()
        if row:
            id_producto = int(row[0])
            connection.commit()
            return id_producto

        return False

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()

def actualizar_producto(nombre, precio, disponible, id_producto):
    """
    Actualiza el nombre, precio y disponibilidad de un producto existente.

    Devuelve el id_producto si la actualización fue exitosa (rowcount > 0).
    Devuelve None si la conexión falla o si rowcount == 0 (producto no encontrado).
    Devuelve False si ocurre una excepción durante la ejecución.

    """
    connection = get_sql_connection()
    if not connection:
        return None

    cursor = connection.cursor()

    sql = """
        UPDATE Producto
        SET 
            NombreProducto = ?, 
            Precio = ?, 
            Disponible = ?
        WHERE IdProducto = ?;
    """
    params = (nombre, precio, disponible, id_producto)

    try:
        cursor.execute(sql, params)
        if cursor.rowcount > 0:
            connection.commit()
            return id_producto
        # NOTA: si rowcount == 0 la función Devuelve None implícitamente

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()


def eliminar_producto(id_producto):
    """
    Elimina físicamente un producto de la tabla Producto (borrado definitivo).

    Devuelve el id_producto si la eliminación fue exitosa (rowcount > 0).
    Devuelve None si la conexión falla o si rowcount == 0 (producto no encontrado).
    Devuelve False si ocurre una excepción.

    """
    connection = get_sql_connection()
    if not connection:
        return None

    cursor = connection.cursor()

    sql = """
        DELETE FROM Producto
        WHERE IdProducto = ?;
    """
    params = (id_producto,)

    try:
        cursor.execute(sql, params)
        if cursor.rowcount > 0:
            connection.commit()
            return id_producto
        # NOTA: si rowcount == 0 la función Devuelve None implícitamente

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()


# =============================================================================
# PAGOS
# =============================================================================

def crear_pago(id_orden, id_metodo_pago, cantidad_a_pagar, cantidad_pagada=None):
    """
    Registra un nuevo pago en la tabla Pago asociado a una orden.

    El comportamiento del INSERT varía según si se proporciona cantidad_pagada:

    Sin cantidad_pagada (métodos 1 y 2 — pago presencial):
        Solo inserta CantidadAPagar. CantidadPagada y CantidadRegresada
        quedan con sus valores por defecto (NULL).
        Se usa cuando el pago se completará más adelante con actualizar_pago().

    Con cantidad_pagada (método 3 — pago en línea inmediato):
        Inserta CantidadAPagar, CantidadPagada y CantidadRegresada.
        CantidadRegresada se calcula como (cantidad_pagada - cantidad_a_pagar),
        que, en el caso del método 3, siempre será 0, ya que ambos valores son iguales.

    Devuelve True si la inserción fue exitosa, False en caso contrario.
    """
    connection = get_sql_connection()
    if not connection:
        return False

    cursor = connection.cursor()

    if cantidad_pagada != None:
        # Pago en línea inmediato: se conoce el monto entregado y se calcula el cambio
        cantidad_regresada = cantidad_pagada - cantidad_a_pagar
        sql = """
            INSERT INTO Pago (IdOrden, IdMetodoPago, CantidadAPagar, CantidadPagada, CantidadRegresada)
            VALUES (?, ?, ?, ?, ?);
        """
        params = (id_orden, id_metodo_pago, cantidad_a_pagar, cantidad_pagada, cantidad_regresada)
    else:
        # Pago presencial: solo se registra el monto a pagar; se completará después
        sql = """
            INSERT INTO Pago (IdOrden, IdMetodoPago, CantidadAPagar)
            VALUES (?, ?, ?);
        """
        params = (id_orden, id_metodo_pago, cantidad_a_pagar)

    try:
        cursor.execute(sql, params)
        # El INSERT requiere commit explícito para persistir los datos
        connection.commit()
        return True

    except Exception as e:
        print(f"Ocurrió un error al procesar el pago: {e}")
        # Revertir el INSERT si ocurrió un error
        connection.rollback()
        return False
    finally:
        connection.close()


def actualizar_pago(id_pago, cantidad_a_pagar, cantidad_pagada):
    """
    Completa el registro de un pago diferido, actualizando CantidadPagada
    y CantidadRegresada para un pago existente.

    Se utiliza al completar una orden para registrar el monto real entregado
    por el cliente y el cambio devuelto.

    CantidadRegresada se calcula como (cantidad_pagada - cantidad_a_pagar).
    Para transferencias, ambos valores son iguales, resultando en 0.
    Para efectivo, puede haber un vuelto positivo si el cliente pagó de más.

    Devuelve True si la actualización fue exitosa (rowcount > 0).
    Devuelve None si la conexión falla o si rowcount == 0 (pago no encontrado).
    Devuelve False si ocurre una excepción.
    """
    connection = get_sql_connection()
    if not connection:
        return None

    cursor = connection.cursor()

    # Calcular el cambio/vuelto a registrar
    cantidad_regresada = cantidad_pagada - cantidad_a_pagar

    sql = """
        UPDATE Pago
        SET 
            CantidadPagada = ?, 
            CantidadRegresada = ?
        WHERE IdPago = ?;
    """
    params = (cantidad_pagada, cantidad_regresada, id_pago)

    try:
        cursor.execute(sql, params)
        if cursor.rowcount > 0:
            connection.commit()
            return True
        # NOTA: si rowcount == 0 la función Devuelve None implícitamente

    except Exception as e:
        print(f"Ocurrió un error: {e}")
        connection.rollback()
        return False
    finally:
        connection.close()


# =============================================================================
# HISTORIAL
# =============================================================================

def obtener_historial(id_usuario):
    """
    Devuelve el historial completo de órdenes de un usuario, sin filtro de
    estado ni de actividad (Activo).

    A diferencia de obtener_ordenes(), esta función:
        - No filtra por Activo = 1, por lo que incluye órdenes completadas
            (Activo = 0) que ya no aparecen en la vista principal.
        - No filtra por IdEstado, por lo que pueden aparecer órdenes en
            cualquier estado (pendiente, confirmada, completada).
        - Incluye FechaHoraCreacion para mostrar cuándo fue creada la orden.
        - No incluye información de pago.

    Los resultados se ordenan por FechaHoraCreacion descendente (más recientes
    primero).

    Devuelve una lista de diccionarios, o [] si hay un error.

    """
    connection = get_sql_connection()
    if not connection:
        return []

    cursor = connection.cursor()

    # Consulta sin filtros de Activo ni IdEstado: muestra todo el historial
    sql = """
            SELECT
                IdOrden,
                NombreProducto,
                Usuarios.Nombre,
                Precio AS PrecioUnidad,
                Cantidad,
                (Cantidad * Precio) AS PrecioTotal,
                Orden.IdEstado,
                Estado,
                FechaHoraRecoleccion,
                Orden.FechaHoraCreacion
            FROM Orden
                INNER JOIN EstadoOrden
                ON Orden.IdEstado = EstadoOrden.IdEstado
                INNER JOIN Producto
                ON Orden.IdProducto = Producto.IdProducto
                INNER JOIN Usuarios
                ON Orden.IdUsuario = Usuarios.IdUsuario
            WHERE Orden.IdUsuario = ?
            ORDER BY FechaHoraCreacion DESC;
        """
    params = (id_usuario,)

    try:
        cursor.execute(sql, params)

        # Convertir los objetos pyodbc.Row a diccionarios para facilitar
        # su uso en las plantillas Jinja
        columns = [column[0] for column in cursor.description]
        ordenes = [dict(zip(columns, row)) for row in cursor.fetchall()]

        return ordenes

    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        connection.close()
