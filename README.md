# TiendaDB

* El proyecto TiendaDB implementa una web app y REST API básica para el manejo de órdenes y productos en una tienda (basada en la tienda "Los Compadres" en la Universidad de Sonora).
* El proyecto utiliza un servidor Flask para proveer una web app y una REST API para acceder y modificar los contenidos de una base de datos de Microsoft SQL Server.
* Desarrollado como la séptima actividad y proyecto final de la materia **Desarrollo de Sistemas IV** impartida por el profesor Meza Ibarra Iván Dostoyewski en el semestre 2026-1.

## Instrucciones de Uso

1. Ejecutar el archivo **`docs/db_script.sql`** en el servidor de Microsoft SQL Server por utilizar.
2. Especificar las variables de entorno en el archivo **`.env`** para la conexión a la base de datos.
3. Instalar las dependencias en **`requirements.txt`**
4. Ejecutar el archivo **`run.py`**
> El programa se ejecuta en la ruta defecto de Flask (`localhost:5000`) en modo debug.

## Estructura del Proyecto

```text
TiendaDB
├── app: Lógica y estructura de la aplicación
│   ├── api: Lógica de la REST API
│   ├── static: Archivos estáticos 
│   ├── templates: Plantillas HTML usadas por Flask
│   ├── web: Lógica para la web app
│   ├── db.py: Acceso a la base de datos por la web app
│   ├── db_api.py: Acceso a la base de datos por la REST API
│   └── helpers.py: Funciones de asistencia
├── docs: Documentación del proyecto y definición de la base de datos
├── .env: Credenciales de acceso a la base de datos
├── requirements.txt: Librerías de Python requeridas
└── run.py: Archivo de arranque del programa
```

## Blueprints

* **`/`** - Aplicación web
* **`/api/`** - API REST

## Capturas de Pantalla

### Vista de Cliente
![Vista de cliente - Vista de órdenes activas](/docs/assets/Screenshot3.png?raw=true "Vista de órdenes activas")
![Vista de cliente - Historial de órdenes](/docs/assets/Screenshot4.png?raw=true "Historial de órdenes")

### Vista de Administrador
![Vista de administrador - Creación de nuevo producto](/docs/assets/Screenshot1.png?raw=true "Creación de nuevo producto")
![Vista de administrador - Vista de productos](/docs/assets/Screenshot2.png?raw=true "Vista de productos")

## Demostración de Uso
[![Actividad 07 - Proyecto Final](https://markdown-videos-api.jorgenkh.no/url?url=https%3A%2F%2Fyoutu.be%2FD25i03dgOXc)](https://youtu.be/D25i03dgOXc)
