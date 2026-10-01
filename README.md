# TiendaDB

* El proyecto TiendaDB implementa una web app y REST API básica para el manejo de órdenes y productos en una tienda (basada en la tienda "Los Compadres" en la Universidad de Sonora).

## Instrucciones de uso

1. Ejecutar el archivo **`docs/db_script.sql`** en el servidor de Microsoft SQL Server por utilizar.
2. Especificar las variables de entorno en el archivo **`.env`** para la conexión a la base de datos.
3. Instalar las dependencias en **`requirements.txt`**
4. Ejecutar el archivo **`run.py`**
> El programa se ejecuta en la ruta defecto de Flask (`localhost:5000`) en modo debug.

## Estructura del proyecto

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

## Demostración de uso

[![Actividad 07 - Proyecto Final](https://markdown-videos-api.jorgenkh.no/url?url=https%3A%2F%2Fyoutu.be%2FD25i03dgOXc)](https://youtu.be/D25i03dgOXc)
