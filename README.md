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
- Crear un archivo .env dentro de backend y ponerle las credenciales (seguir el ejemplo de .env.example)

---

## PASO 5:

- Hacer migraciones comandos (estar en el mismo nivel de backend):
  1. `python manage.py migrate`
  2. `python manage.py makemigrations`
  3. `python manage.py migrate`
- Crear un super usuario:
  1. `python manage.py createsuperuser`
  2. Ponerle nombre de usuario, correo y contraseñas genéricos (juan, j@j.com, 123)
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




# PASOS PARA EJECUTAR EL FRONTEND DE MANERA LOCAL:
**Necesario tener:**

- Android Studio Versión => Android Studio Meerkat Feature Drop | 2024.3.2 Patch (Recomendado).
- Dispositivo android versión 10 o mayor.
- Vysor (Opcional).

---

## PASO OPCIONAL (EN CASO DE TENER UNA VERSIÓN ANTIGUA DE ANDROID STUDIO):
  - Abrir el proyecto.
  - Buscar el archivo libs.versions.toml en la carpeta "gradle/libs.versions.toml" y cambiar la versión agp = "8.10.1" a la del android studio del entorno local.

---

## PASO 1:

- Abrir el proyecto:
  - Abrir Android Studio.
  - Darle a la opción "Open".
  - Buscar el proyecto que está ubicado en la carpeta del repositorio \K-Loque_Report\frontend
  - Abrir y selccionar la opción de "Trust Project"

---

## PASO 2:

- Actualizar dependencias:
  - Dirijirse a la pestaña "File".
  - Dar clic en la opción "Sync Project with Gradle Files".

---

## PASO 3:

- Actualizar direcciones y politicas de seguridad de dominio:
  1 MainActivity.kt:
    - Dentro del proyecto, buscar el archivo MainActivity.kt, ubicado en la carpeta "com/puella_softworks/k_loque_reports/MainActivity.kt".
    - Dirigirse a la línea de código 64 y ubicar la ruta "**http://GenshinImpact/admin/**".
    - Cambiar "_GenshinImpact_" por la dirección local o de dominio, por ejemplo usando la ruta "_127.0.0.1:8000_", el resultado sería el siguiente "**http://127.0.0.1:8000/admin**".

  2 RetrofitClient.kt:
    - Dentro del proyecto, buscar el archivo RetrofitClient.kt, ubicado en la carpeta "com/puella_softworks/k_loque_reports/classes/RetrofitClient.kt".
    - Dirigirse a la línea de código 9 y ubicar la ruta "**http://GenshinImpact/**".
    - Cambiar "_GenshinImpact_" por la dirección local o de dominio, por ejemplo usando la ruta "_127.0.0.1:8000_", el resultado sería el siguiente "**http://127.0.0.1:8000/**".

  3 network_security_config.xml:
    - Dentro del proyecto, buscar el archivo network_security_config.xml, ubicado en la carpeta "xml/network_security_config.xml".
    - Ubicar la línea de código 5 e identificar el dominio: "**<domain includeSubdomains="true">GenshinImpact</domain>**"
    - Cambiar "_GenshinImpact_" por la dirección local o de dominio, por ejemplo usando la ruta "_127.0.0.1:8000_", el resultado sería el siguiente "**<domain includeSubdomains="true">127.0.0.1</domain>**".


---

## PASO 4:

- Ejecutar proyecto:
  - Conectar el celular con depuración USB o inalámbrica activa (Opcional).
  - Darle al botón de "Run App" o presionar la combinación de teclas **Shift + F10**.

---

## PASO OPCIONAL ():
