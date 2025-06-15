# PASOS PARA EJECUTAR EL BACKEND DE MANERA LOCAL:

**Necesario tener:**

- Python versión >= 3...
- Pip
- Postman (opcional pero recomendado para evaluar las rutas)
- Workbench

---

## PASO 1:

- Descargar el proyecto:
  - En .rar o zip.
  - O Clonación: `git clone https://github.com/Neith21/K-loque_Report.git`

---

## PASO 2:

- Posicionarse en el repositorio y crear un entorno virtual:
  1. Abrir terminal y `cd` hasta el repositorio.
  2. Ejecutar el comando: `python -m venv env` (se creará una carpeta env en el mismo nivel de la carpeta backend)
  3. Para activar el entorno virtual el comando es: `env\Scripts\activate` (debemos estar en el mismo nivel de la carpeta env)

---

## PASO 3:

- Ejecutar librerías comandos:
  1. `cd backend`
  2. `pip install -r requirements.txt`

---

## PASO 4:

Configuraciones generales del proyecto:

- Crear una base de datos en MySQL:
  - `CREATE DATABASE kloque_report_db;`
  - `USE kloque_report_db;`
- Crear un archivo `.env` dentro de backend al mismo nivel de `.env.example` y ponerle las credenciales (seguir el ejemplo de `.env.example`)

---

## PASO 5:

- Hacer migraciones comandos (estar en el mismo nivel de backend):
  1. `python manage.py migrate`
  2. `python manage.py makemigrations`
  3. `python manage.py migrate`
- Crear un super usuario:
  1. `python manage.py createsuperuser`
  2. Ponerle nombre de usuario, correo y contraseñas genéricos (`juan`, `j@j.com`, `123`)
  3. Dirá que la contraseña es débil pero dejenlo pasar (Y)

---

## PASO 6:

- Correr el servidor comando (estar en el mismo nivel de backend):
  - `python manage.py runserver 192.168.1.6:8000` (antes es necesario conocer nuestra ip)

---

## PASO 7:

A partir de aquí tenemos la libertad de hacer lo que sea, como primer paso recomiendo leer la documentación para saber cómo consumir la api:

- Entrar al navegador y poner la ruta (deberá cambiar a la ip de su computadora):
  - `http://10.15.2.117:8000/documentation`
  - `http://10.15.2.117:8000/redoc`

---

Para volver a usar el backend es necesario activar el entorno virtual y correr el servidor
