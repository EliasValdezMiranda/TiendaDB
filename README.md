# TiendaDB

[![Actividad 07 - Proyecto Final](https://markdown-videos-api.jorgenkh.no/url?url=https%3A%2F%2Fyoutu.be%2FD25i03dgOXc)](https://youtu.be/D25i03dgOXc)

El proyecto TiendaDB implementa una web app y REST API básica para el manejo de órdenes y productos en una tienda (basada en la tienda "Los Compadres" en la Universidad de Sonora).

**Estructura del proyecto**
* app: Almacena los archivos con la lógica y estructura de la aplicación
    * api: Almacena los archivos de lógica para la REST API
    * static: Almacena los archivos estáticos del proyecto (aquellos que no se modifican)
    * templates: Almacena las plantillas HTML del proyecto, modificadas por Flask para la correcta presentación de la web app
    * web: Almacena los archivos de lógica para la web app
    * db.py: Almacena las funciones de acceso a la base de datos por parte de la web app
    * db_api.py: Almacena las funciones de acceso a la base de datos por parte de la REST API
    * helpers.py: Almacena funciones de asistencia para el manejo de la información en la web app y REST API
* docs: Almacena la documentación del proyecto, incluyendo el archivo de definición de la base de datos
* .env: Almacena las credenciales de acceso a la base de datos
* run.py: Archivo de arranque del programa. Inicia la web app y la API REST

**Instrucciones de uso**
1.- Ejecutar el archivo db_script.sql en el servidor de Microsoft SQL Server por utilizar.
2.- Especificar las variables de entorno en el archivo ".env" para la conexión a la base de datos.
3.- Instalar las dependencias en requirements.txt
4.- Ejecutar el archivo run.py
* El programa se ejecuta en la ruta de Flask por defecto (localhost:5000) en modo debug.

**Blueprints**
/ - Aplicación web
/api/ - API REST
