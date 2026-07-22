; ============================================================================
;  Instalador del Gestor de Marketing WhatsApp - WoodTools
;  Genera un setup.exe que instala la app (autónoma) sin necesidad de que la
;  persona descargue archivos, instale Python ni compile nada.
;
;  Cómo compilar este script:
;    - Con Inno Setup instalado, abrir este archivo y presionar Ctrl+F9, o
;    - Ejecutar:  ISCC.exe instalador.iss
;  El setup.exe queda en la carpeta .\Instalador\
; ============================================================================

#define MiNombre "Gestor de Marketing WhatsApp"
; La versión la pasa CONSTRUIR_INSTALADOR.bat con /DMiVersion=... (leída de VERSION_APP
; en mainCode.py). Si se compila el .iss a mano, se usa este valor por defecto.
#ifndef MiVersion
  #define MiVersion "12.2"
#endif
#define MiEmpresa "WoodTools SRL"
#define MiExe "Gestor de Mensajes Difusion.exe"

[Setup]
; AppId FIJO: no cambiarlo nunca. Permite que las versiones nuevas se instalen
; ENCIMA de la anterior (actualización) en vez de duplicar la app.
AppId={{8F2A6D14-4C9B-4E7A-9A1F-3B7E5C0D9A21}
AppName={#MiNombre}
AppVersion={#MiVersion}
AppPublisher={#MiEmpresa}
VersionInfoVersion={#MiVersion}
VersionInfoCompany={#MiEmpresa}
VersionInfoDescription=Instalador del {#MiNombre}

; Instalación POR USUARIO (sin pedir permisos de administrador) en una carpeta
; con permisos de escritura, para que la app pueda guardar su base de datos,
; el token de Google y los reportes al lado del ejecutable.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\WoodTools\Gestor de Marketing
DisableProgramGroupPage=yes
DisableDirPage=yes

; Ícono del asistente y del propio setup.exe
SetupIconFile=Imagenes\logo.ico

; Salida del instalador
OutputDir=Instalador
OutputBaseFilename=Instalador_GestorMarketing_WoodTools_v{#MiVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; Requiere Windows 10 o superior
MinVersion=10.0

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
; La app es un único .exe autónomo: adentro ya trae el logo y las credenciales.
; La base de datos, token.json y los reportes se crean solos en esta carpeta al usarla.
Source: "dist\{#MiExe}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Accesos directos en el Menú Inicio y en el Escritorio (con el ícono del .exe)
Name: "{autoprograms}\{#MiNombre}"; Filename: "{app}\{#MiExe}"
Name: "{autodesktop}\{#MiNombre}"; Filename: "{app}\{#MiExe}"

[Run]
; Opción de abrir la app apenas termina la instalación
Filename: "{app}\{#MiExe}"; Description: "Abrir el {#MiNombre} ahora"; Flags: nowait postinstall skipifsilent
