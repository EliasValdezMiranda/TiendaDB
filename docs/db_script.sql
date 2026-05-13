-- USE master;
-- ALTER DATABASE TiendaDB SET SINGLE_USER WITH ROLLBACK IMMEDIATE;
-- DROP DATABASE TiendaDB;

CREATE DATABASE TiendaDB;
USE TiendaDB;
GO

DROP TABLE IF EXISTS RolUsuario;
GO

CREATE TABLE RolUsuario(
    IdRolUsuario INT PRIMARY KEY,
	Rol NVARCHAR(30) NOT NULL
);
GO

INSERT INTO RolUsuario (IdRolUsuario, Rol)
VALUES
    (1, 'Cliente'),
    (2, 'Administrador');
GO

DROP TABLE IF EXISTS Usuarios;
GO

CREATE TABLE Usuarios (
	IdUsuario INT IDENTITY(1,1) PRIMARY KEY,
    IdRolUsuario INT NOT NULL DEFAULT 1,
    Nombre NVARCHAR(100) NOT NULL,
    Username NVARCHAR(20) UNIQUE NOT NULL,
    Email NVARCHAR(50) UNIQUE NOT NULL,
    PasswordHash VARBINARY(64) NOT NULL,
    Sal UNIQUEIDENTIFIER NOT NULL,
    Activo BIT DEFAULT 1,
    FechaHoraCreacion DATETIME2(7) DEFAULT GETDATE()
    CONSTRAINT FK_Usuarios_RolUsuario
		FOREIGN KEY (IdRolUsuario) REFERENCES RolUsuario(IdRolUsuario)
);
GO

DROP TABLE IF EXISTS LogsUsuarios;
GO

CREATE TABLE LogsUsuarios (
	IdLogUsuario INT IDENTITY(1,1) PRIMARY KEY,
	IdUsuario INT NOT NULL,
	Comentario NVARCHAR(100) NOT NULL,
    FechaHoraCreacion DATETIME NOT NULL DEFAULT GETDATE(),
	CONSTRAINT FK_LogsUsuarios_Usuarios
		FOREIGN KEY (IdUsuario) REFERENCES Usuarios(IdUsuario)
);
GO

-- Trigger despues de insertar un usuario, agregar registro de operación ("Usuario agregado")
CREATE TRIGGER TR_Usuarios_FI
ON dbo.Usuarios
FOR INSERT
AS
BEGIN
    INSERT INTO LogsUsuarios (
        IdUsuario,
        Comentario
    )
    SELECT 
        IdUsuario, 
        'Usuario agregado'
    FROM INSERTED;
END
GO

-- Trigger despues de actualizar un usuario, agregar registro de operación ("Información de usuario actualizada")
CREATE TRIGGER TR_Usuarios_AU
ON dbo.Usuarios
AFTER UPDATE
AS
BEGIN
	IF EXISTS (SELECT 1 FROM DELETED WHERE Activo = 0)
    BEGIN
        RAISERROR ('Operación cancelada: No se pueden modificar usuarios inactivos.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    IF (TRIGGER_NESTLEVEL() > 1) RETURN;

    SET NOCOUNT ON;

    INSERT INTO LogsUsuarios (
        IdUsuario, 
        Comentario
    )
    SELECT 
        IdUsuario, 
        'Usuario actualizado'
    FROM INSERTED
END
GO

-- Trigger despues de eliminar un usuario, agregar registro de operación ("Usuario eliminado")
CREATE TRIGGER TR_Usuarios_IoD
ON dbo.Usuarios
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE U
    SET U.Activo = 0
    FROM dbo.Usuarios U
    INNER JOIN DELETED D ON U.IdUsuario = D.IdUsuario;

    INSERT INTO LogsUsuarios (
        IdUsuario,
        Comentario
    )
    SELECT 
        IdUsuario, 
        'Usuario eliminado'
    FROM INSERTED;
END
GO

-- =============================================
-- Author:		Elías Valdez Miranda
-- Create date: 08-Abril-2025
-- Description:	Procedimiento utilizado para la
-- creación de un usuario. Utiliza el algoritmo
-- de encriptación SHA2_512 para mantener la
-- seguridad de la información en la base de datos.
-- =============================================
CREATE PROCEDURE [dbo].[stpAgregarUsuario]
    @Nombre nvarchar(100),
    @IdRolUsuario int,
    @Username nvarchar(50),
    @Email nvarchar(50),
    @Password nvarchar(100),
    @IDUsuario int OUTPUT,
    @Mensaje nvarchar(500) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        -- 1. Check if Username already exists
        IF EXISTS (SELECT 1 FROM Usuarios WHERE Username = @Username)
        BEGIN
            SET @IDUsuario = 0
            SET @Mensaje = 'Error: El nombre de usuario ya está en uso.'
            RETURN;
        END

        -- 2. Check if Email already exists
        IF EXISTS (SELECT 1 FROM Usuarios WHERE Email = @Email)
        BEGIN
            SET @IDUsuario = -1
            SET @Mensaje = 'Error: El correo electrónico ya está registrado.'
            RETURN;
        END

        -- 3. Logic for Hashing
        DECLARE @Sal UNIQUEIDENTIFIER = NEWID()
        DECLARE @HashedPassword VARBINARY(64)

        -- Hashing using SHA2_512
        SET @HashedPassword = HASHBYTES('SHA2_512', @Password + CAST(@Sal AS NVARCHAR(36)))

        -- 4. Insertion
        INSERT INTO Usuarios (Nombre, IdRolUsuario, Username, Email, PasswordHash, Sal)
        VALUES (@Nombre, @IdRolUsuario, @Username, @Email, @HashedPassword, @Sal)

        SET @IDUsuario = SCOPE_IDENTITY()
        SET @Mensaje = 'Usuario creado exitosamente'
        
    END TRY
    BEGIN CATCH
        SET @IDUsuario = -2
        SET @Mensaje = ERROR_MESSAGE()
    END CATCH
END
GO

-- =============================================
-- Author:		Elías Valdez Miranda
-- Create date: 08-Abril-2025
-- Description:	Función que verifica la contraseña
-- otorgada con el hash generado de acuerdo a la 
-- sal almacenada en el perfil de usuario.
-- Devuelve la ID del usuario si la contraseña es válida,
-- de lo contrario, devuelve -1.
-- =============================================
CREATE FUNCTION [dbo].[ufnVerificarPassword]
(
    @UsernameOrEmail NVARCHAR(255),
    @Password NVARCHAR(100)
)
RETURNS INT
AS
BEGIN
    DECLARE @IDUsuario INT
    DECLARE @HashAlmacenado VARBINARY(64)
    DECLARE @Sal UNIQUEIDENTIFIER
    
    SELECT @HashAlmacenado = PasswordHash, 
            @Sal = Sal,
            @IDUsuario = IDUsuario
    FROM Usuarios
    WHERE Username = @UsernameOrEmail OR Email = @UsernameOrEmail
    
    -- Verificar si se encontró el usuario y la contraseña es correcta
    IF @HashAlmacenado IS NOT NULL
        AND @HashAlmacenado = HASHBYTES('SHA2_512', @Password + CAST(@Sal AS NVARCHAR(36)))
    BEGIN
        -- La contraseña es correcta, retornar el IDUsuario
        RETURN @IDUsuario
    END
    
    -- Si no, retornar -1
    RETURN -1
END
GO


-- VERIFICADO HASTA AQUÍ


DROP TABLE IF EXISTS Producto;
GO

CREATE TABLE Producto (
    IdProducto INT IDENTITY(1,1) PRIMARY KEY,
    NombreProducto VARCHAR(100) NOT NULL,
    Precio DECIMAL NOT NULL,
    Disponible BIT DEFAULT 1,
    Activo BIT DEFAULT 1,
    FechaHoraCreacion DATETIME NOT NULL DEFAULT GETDATE()
);
GO

DROP TABLE IF EXISTS LogsProducto;
GO

CREATE TABLE LogsProducto (
	IdLogProducto INT IDENTITY(1,1) PRIMARY KEY,
	IdProducto INT NOT NULL,
	Comentario NVARCHAR(100) NOT NULL,
    FechaRegistro DATETIME NOT NULL DEFAULT GETDATE(),
	CONSTRAINT FK_LogsProducto_Producto
		FOREIGN KEY (IdProducto) REFERENCES Producto(IdProducto)
);
GO

-- Trigger despues de insertar un producto, agregar registro de operación ("Producto agregado")
CREATE TRIGGER TR_Producto_FI
ON dbo.Producto
FOR INSERT
AS
BEGIN
    INSERT INTO LogsProducto (
        IdProducto,
        Comentario
    )
    SELECT 
        IdProducto, 
        'Producto agregado'
    FROM INSERTED;
END
GO

-- Trigger despues de actualizar un usuario, agregar registro de operación ("Información de usuario actualizada")
CREATE TRIGGER TR_Producto_AU
ON dbo.Producto
AFTER UPDATE
AS
BEGIN
	IF EXISTS (SELECT 1 FROM DELETED WHERE Activo = 0)
    BEGIN
        RAISERROR ('Operación cancelada: No se pueden modificar productos inactivos.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    IF (TRIGGER_NESTLEVEL() > 1) RETURN;

    SET NOCOUNT ON;

    INSERT INTO LogsProducto (
        IdProducto, 
        Comentario
    )
    SELECT 
        IdProducto, 
        'Producto actualizado'
    FROM INSERTED
END
GO

-- Trigger despues de eliminar una orden de producto, agregar registro de operación ("Orden de producto eliminada")
CREATE TRIGGER TR_Producto_IoD
ON dbo.Producto
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE P
    SET P.Activo = 0
    FROM dbo.Producto P
    INNER JOIN DELETED D ON P.IdProducto = D.IdProducto;

    INSERT INTO LogsProducto (
        IdProducto,
        Comentario
    )
    SELECT 
        IdProducto,
        'Producto eliminado'
    FROM INSERTED;
END
GO

DROP TABLE IF EXISTS EstadoOrden;
GO

CREATE TABLE EstadoOrden(
    IdEstado INT PRIMARY KEY,
	Estado NVARCHAR(30) NOT NULL
);
GO

INSERT INTO EstadoOrden (IdEstado, Estado)
VALUES
    (1, 'En carrito'),
    (2, 'Confirmada'),
    (3, 'Completada'),
    (4, 'Cancelada');
GO

DROP TABLE IF EXISTS Orden;
GO

CREATE TABLE Orden (
	IdOrden INT IDENTITY(1,1) PRIMARY KEY,
    IdEstado INT NOT NULL DEFAULT 1,
    IdUsuario INT NOT NULL,
    IdProducto INT NOT NULL,
    Cantidad INT NOT NULL DEFAULT 1,
    FechaHoraRecoleccion DATETIME2(7),
    Activo BIT DEFAULT 1,
    FechaHoraCreacion DATETIME2(7) DEFAULT GETDATE(),
    CONSTRAINT FK_Orden_Usuarios
		FOREIGN KEY (IdUsuario) REFERENCES Usuarios(IdUsuario),
    CONSTRAINT FK_Orden_EstadoOrden
		FOREIGN KEY (IdEstado) REFERENCES EstadoOrden(IdEstado)
);
GO

DROP TABLE IF EXISTS LogsOrden;
GO

CREATE TABLE LogsOrden (
	IdLogOrden INT IDENTITY(1,1) PRIMARY KEY,
	IdOrden INT NOT NULL,
	Comentario NVARCHAR(100) NOT NULL,
    FechaRegistro DATETIME NOT NULL DEFAULT GETDATE(),
	CONSTRAINT FK_LogsOrden_Orden
		FOREIGN KEY (IdOrden) REFERENCES Orden(IdOrden)
);
GO

-- Trigger despues de insertar una orden, agregar registro de operación ("Orden creada")
CREATE TRIGGER TR_Orden_FI
ON dbo.Orden
FOR INSERT
AS
BEGIN
    INSERT INTO LogsOrden (
        IdOrden,
        Comentario
    )
    SELECT 
        IdOrden, 
        'Orden agregada'
    FROM INSERTED;
END
GO

-- Trigger despues de actualizar una orden, agregar registro de operación ("Orden actualizada")
CREATE TRIGGER TR_Orden_AU
ON dbo.Orden
AFTER UPDATE
AS
BEGIN
	IF EXISTS (SELECT 1 FROM DELETED WHERE Activo = 0)
    BEGIN
        RAISERROR ('Operación cancelada: No se pueden modificar ordenes inactivas.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    IF (TRIGGER_NESTLEVEL() > 1) RETURN;

    SET NOCOUNT ON;

    INSERT INTO LogsOrden (
        IdOrden, 
        Comentario
    )
    SELECT 
        IdOrden, 
        'Orden actualizada'
    FROM INSERTED
END
GO

-- Trigger despues de eliminar un usuario, agregar registro de operación ("Usuario eliminado")
CREATE TRIGGER TR_Orden_IoD
ON dbo.Orden
INSTEAD OF DELETE
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE O
    SET O.Activo = 0,
        O.IdEstado = 4
    FROM dbo.Orden O
    INNER JOIN DELETED D ON O.IdOrden = D.IdOrden

    INSERT INTO LogsOrden (
        IdOrden,
        Comentario
    )
    SELECT 
        IdOrden, 
        'Orden eliminada'
    FROM INSERTED;
END
GO

-- =============================================
-- Author:		Elías Valdez Miranda
-- Create date: 14-Abril-2025
-- Description:	Procedimiento almacenado que
-- actualiza el estado de una orden proporcionada. 
-- =============================================
CREATE PROCEDURE [dbo].[uspActualizarEstadoOrden]
    @IdOrden INT,
    @IdEstado INT
AS
BEGIN
    -- Use SET NOCOUNT ON to prevent extra result sets from interfering with SELECT statements
    SET NOCOUNT ON;

    DECLARE @Comentario NVARCHAR(100);

    -- 1. Initial Update
    UPDATE dbo.Orden
    SET IdEstado = @IdEstado
    WHERE IdOrden = @IdOrden;

    -- 2. Logic for specific states
    IF @IdEstado = 2
    BEGIN
        SET @Comentario = 'Orden en progreso';
    END
    ELSE IF @IdEstado = 3
    BEGIN
        SET @Comentario = 'Orden completada';
        UPDATE dbo.Orden
        SET Activo = 0
        WHERE IdOrden = @IdOrden;
    END
    ELSE IF @IdEstado = 4
    BEGIN
        SET @Comentario = 'Orden cancelada';
        UPDATE dbo.Orden
        SET Activo = 0
        WHERE IdOrden = @IdOrden;
    END
    ELSE
    BEGIN
        -- Use THROW or RAISERROR for better error handling in procedures
        PRINT 'Estado no válido';
        RETURN -1; 
    END

    -- 3. Insert into Logs
    INSERT INTO LogsOrden (IdOrden, Comentario)
    VALUES (@IdOrden, @Comentario);

    RETURN 0; -- Success
END
GO

DROP TABLE IF EXISTS MetodoPago

CREATE TABLE MetodoPago (
    IdMetodoPago INT PRIMARY KEY,
    Metodo VARCHAR(30) NOT NULL
)

INSERT INTO MetodoPago (IdMetodoPago, Metodo)
VALUES
    (1, 'Efectivo'),
    (2, 'Tarjeta'),
    (3, 'En línea');
GO

DROP TABLE IF EXISTS Pago;
GO

CREATE TABLE Pago (
    IdPago INT IDENTITY(1,1) PRIMARY KEY,
    IdOrden INT NOT NULL,
    IdMetodoPago INT NOT NULL,
    CantidadAPagar DECIMAL,
    CantidadPagada DECIMAL,
    CantidadRegresada DECIMAL,
    FechaHoraCreacion DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_Pago_Orden
		FOREIGN KEY (IdOrden) REFERENCES Orden(IdOrden),
    CONSTRAINT FK_Pago_Metodo
		FOREIGN KEY (IdMetodoPago) REFERENCES MetodoPago(IdMetodoPago),
);
GO

EXEC stpAgregarUsuario
    @Nombre = 'Administrador',
    @IdRolUsuario = 2,
    @Username = 'admin',
    @Email = 'admin@gmail.com',
    @Password = 'admin',
    @IDUsuario = NULL,
    @Mensaje = NULL;

EXEC stpAgregarUsuario
    @Nombre = 'Cliente',
    @IdRolUsuario = 1,
    @Username = 'user',
    @Email = 'user@gmail.com',
    @Password = 'user',
    @IDUsuario = NULL,
    @Mensaje = NULL;