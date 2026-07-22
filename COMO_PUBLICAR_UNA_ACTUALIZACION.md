# Cómo sacar una versión nueva y que se actualice a todos solo

La app (desde la v12.1) revisa sola al abrir si hay una versión más nueva publicada en
**GitHub Releases** del repo `woodtoolsmarketing/WhatsAppMessage`. Si la hay, le ofrece a la
persona descargarla e instalarla; la app se cierra unos segundos y se vuelve a abrir sola.

Para publicar una versión nueva seguí estos 3 pasos:

## 1) Subir el número de versión (un solo lugar)
Editá `mainCode.py` la línea:
```
VERSION_APP = "12.1"
```
y poné el número nuevo, por ejemplo `"12.2"`.
Ese número lo toman solos tanto la app como el instalador.

## 2) Generar el instalador nuevo
Doble clic en **`CONSTRUIR_INSTALADOR.bat`**.
Cuando termina, el `setup.exe` queda en la carpeta **`Instalador\`** con el número nuevo
(ej. `Instalador_GestorMarketing_WoodTools_v12.2.exe`).

## 3) Publicar el release en GitHub (esto es lo que dispara la actualización)

### Opción A (fácil, recomendada): con un clic
Doble clic en **`PUBLICAR_VERSION.bat`**. Solito:
- Detecta la versión y el instalador que generaste.
- La **primera vez** te pide iniciar sesión en GitHub (se abre el navegador, una sola vez).
- Te pregunta las **novedades** (lo que verán los usuarios) y publica el release.

### Opción B (manual, por la web)
1. Entrá a: https://github.com/woodtoolsmarketing/WhatsAppMessage/releases
2. Clic en **"Draft a new release"**.
3. En **"Choose a tag"** escribí el mismo número con una `v` adelante (ej. `v12.2`) → **"Create new tag"**.
4. Título (ej. `Versión 12.2`). En la descripción escribí las **novedades** (eso les aparece a los usuarios en el cartel).
5. Arrastrá el archivo `Instalador\Instalador_GestorMarketing_WoodTools_vXX.exe` a la zona de **"Attach binaries"**.
6. Clic en **"Publish release"**.

¡Listo! La próxima vez que cada persona abra la app, le aparece el cartel para actualizar.

---

## Reglas importantes
- El tag del release (`v12.2`) tiene que ser **MAYOR** que la versión instalada. Siempre subí el número.
- El número de `VERSION_APP` (mainCode.py) y el tag del release deben ser el **MISMO** (ej. `12.2` y `v12.2`). Si no coinciden, o la app no detecta la nueva, o se ofrece a sí misma en un bucle.
- Conviene publicar **la versión actual** como release base (hoy la v12.2), así los futuros updates funcionan.

## Nota de seguridad
El instalador queda descargable públicamente en el release. Recordá que el token de WhatsApp
hoy ya está expuesto en el código público (`mainCode.py`); conviene rotarlo y moverlo al
servidor. Ver las recomendaciones que te dejó el asistente.
