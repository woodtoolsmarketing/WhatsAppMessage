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