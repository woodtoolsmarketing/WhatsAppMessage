Este readme es para ir anotando todas las modificaciones por día que se le fueron haciendo al programa y cuestiones a mejorar 
27/1/2026: Instalación del entorno digital y del código primario. Averiguar por la API de Cloud y de Google para empezar a probar el programa


Codigos necesarios para iniciar e instalar el programa 
instalar python en el pc
instalar las extenciones de python en el vscode
introducir las siguientes credenciales
python -m venv venv
Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process -Force; .\venv\Scripts\Activate (en caso de emergencia)
pip install -r requirements.txt
git config --global user.name "woodtoolsmarketing"
git config --global user.email "woodtoolsmarketing@gmail.com"
pip install pyinstaller
pip install Pillow
pyinstaller --noconsole --onefile --icon=logo.ico --add-data "Imagenes/logo.png;Imagenes" interfaz.py
pip install pandas gspread requests oauth2client
pip install -r requirements.txt
source venv/Scripts/activate 
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
Para actualizar poner git pull
Para que se pueda ejecutar el programa de actualizaciones ir a:
Haz clic en el botón de Inicio de Windows (la ventanita abajo a la izquierda) y escribe directamente "Variables de entorno".
Te aparecerá una opción llamada "Editar las variables de entorno del sistema". Hazle clic.
Se abrirá una ventanita pequeña. Abajo del todo, haz clic en el botón que dice "Variables de entorno...".
En la ventana nueva, busca en la lista de abajo (la que dice Variables del sistema) una variable llamada Path.
Selecciónala y haz clic en el botón "Editar...".
Haz clic en "Nuevo" y pega exactamente esta ruta (que es donde se instala Git por defecto):
C:\Program Files\Git\cmd
Haz clic en Aceptar en las tres ventanas que abriste para cerrarlas y guardar los cambios.
PASO 2: Reiniciar (Súper importante)
Windows es un poco terco y no se entera de este cambio hasta que se reinician los programas.
Cierra por completo Visual Studio Code.
Cierra cualquier terminal o ventana negra que tengas abierta.
Vuelve a abrir Visual Studio Code.
PASO 3: La prueba de fuego
Antes de probar tu programa, confirmemos que Windows ya aprendió la palabra "git".
Abre una terminal nueva en Visual Studio Code (la que es Powershell o CMD normal, no Git Bash).
Escribe git --version y presiona Enter.
Si te responde con algo como git version 2.40..., ¡LISTO! Windows ya sabe usar Git.