# Manual Teórico - Clase 2: Fundamentos de Linux para DevOps

Este manual reúne de forma exhaustiva toda la **teoría, arquitectura interna, significado de comandos, parámetros, notas y tips** abordados durante la Clase 2.

---

## 1. Arquitectura de Almacenamiento y LVM (Logical Volume Manager)

LVM es una capa de abstracción entre los discos físicos y el sistema de archivos que permite redimensionar, mover y gestionar almacenamiento de forma dinámica y flexible.

```
+-------------------------------------------------------------+
|              Puntos de Montaje (/aves, /peces)             |
+-------------------------------------------------------------+
|              Sistemas de Archivos (ext4, xfs)               |
+-------------------------------------------------------------+
|               Logical Volumes (LV: aves, swap...)           |
+-------------------------------------------------------------+
|                  Volume Groups (VG: rlm)                    |
+-------------------------------------------------------------+
|             Physical Volumes (PV: /dev/nvme0n1p3)           |
+-------------------------------------------------------------+
|                 Particiones Físicas del Disco               |
+-------------------------------------------------------------+
```

### Conceptos Clave
- **Physical Volume (PV):** Partición o disco físico inicializado para LVM (`pvcreate`).
- **Volume Group (VG):** Conjunto o bolsa compartida de espacio agrupado (`vgcreate`, `vgextend`).
- **Logical Volume (LV):** Partición virtual que se entrega al sistema operativo para formatear y montar (`lvcreate`, `lvreduce`, `lvextend`).
- **Physical Extent (PE):** Bloque mínimo indivisible de asignación en LVM. Su tamaño por defecto es de **4 MB**.
  > **Nota sobre los Extents:** Cuando solicitas un tamaño como 10 MB o 50 MB, LVM lo redondea al múltiplo más cercano de 4 MB:
  > - 10 MB ➔ **12 MB** (3 extents × 4 MB)
  > - 50 MB ➔ **52 MB** (13 extents × 4 MB)

---

## 2. Gestión de Usuarios, Grupos y Archivos del Sistema

En Linux, la seguridad se basa en que cada proceso y archivo pertenece a un **UID** (User ID) y un **GID** (Group ID).

### Rangos de Identificadores (UID y GID)
| Rango de ID | Tipo de Cuenta | Descripción |
| :--- | :--- | :--- |
| **0** | Superusuario (`root`) | Acceso total e irrestricto al sistema. |
| **1 - 999** | Cuentas de Sistema | Servicios y demonios (`sshd`, `mail`, `chrony`, etc.). No inician sesión interactiva. |
| **1000 - 60000+** | Usuarios Regulares | Cuentas creadas para personas y operadores del sistema. |

### Archivos Críticos de Cuentas en `/etc/`
1. **`/etc/passwd`**: Base de datos de cuentas legibles por todos.
   - Formato: `usuario:x:UID:GID:Comentario:Home:Shell`
   - Ejemplo: `puma:x:1000:1001::/home/puma:/bin/bash`
   - La `x` indica que la contraseña cifrada está protegida en `/etc/shadow`.
2. **`/etc/shadow`**: Contraseñas cifradas con hash (SHA-512) y políticas de caducidad. Solo accesible por `root` (`chmod 000` / `chmod 400`).
3. **`/etc/group`**: Define los grupos y qué usuarios pertenecen a ellos como grupo secundario.
   - Formato: `grupo:x:GID:usuarios_secundarios`
   - Ejemplo: `aves:x:2000:aguila,puma`

### Comandos y Banderas Clave
- **`useradd`**:
  - `-u <UID>`: Fija un identificador de usuario manual.
  - `-g <grupo|GID>`: Define el **grupo primario**.
  - `-G <grupo1,grupo2>`: Asigna **grupos secundarios o suplementarios**.
  - `-m`: Crea el directorio home (`/home/usuario`) si no existe.
  - `-s <shell>`: Asigna la shell por defecto (ej. `/bin/bash` o `/sbin/nologin`).
- **`usermod`**:
  - `-G <grupos>`: Sobrescribe los grupos secundarios.
  - `-aG <grupo>`: **Tip de oro:** Agrega (`append`) un grupo secundario **sin borrar** los grupos que el usuario ya tenía.
- **`groupadd`**:
  - `-g <GID>`: Fija un identificador numérico al grupo.
- **`id <usuario>`**: Muestra el UID, GID primario y todos los grupos secundarios a los que pertenece el usuario.

---

## 3. Permisos Tradicionales en Linux (`chmod`)

Los permisos definen quién puede leer (`r`), modificar (`w`) o ejecutar/acceder (`x`) un archivo o directorio.

### Valores Numéricos Octales
| Permiso | Letra | Valor Octal | En Archivos | En Directorios |
| :--- | :---: | :---: | :--- | :--- |
| **Lectura** | `r` | **4** | Ver el contenido del archivo | Listar el contenido de la carpeta (`ls`) |
| **Escritura** | `w` | **2** | Modificar/borrar contenido | Crear o borrar archivos dentro de la carpeta |
| **Ejecución** | `x` | **1** | Ejecutar como script/programa | Entrar a la carpeta (`cd`) |
| **Sin permiso**| `-` | **0** | Denegado | Denegado |

### Las Tres Ternas de Permisos: `[U] [G] [O]`
Un conjunto de permisos se compone de 9 caracteres divididos en 3 ternas:
1. **User (U):** Usuario propietario.
2. **Group (G):** Integrantes del grupo propietario.
3. **Others (O):** Cualquier otro usuario del sistema.

### Desglose de Permisos Comunes
- **`777` (`rwxrwxrwx`):** Control total para todos (Lectura: 4 + Escritura: 2 + Ejecución: 1 = 7).
- **`755` (`rwxr-xr-x`):** Dueño total (`7`), grupo y otros solo lectura y entrada (`5`).
- **`770` (`drwxrwx---`):** Dueño (`7`) y grupo (`7`) tienen control total. **Otros (`0`) no tienen ningún acceso**.
- **`644` (`-rw-r--r--`):** Archivo de texto típico. Dueño lee y escribe (`6`), los demás solo leen (`4`).

---

## 4. Propietarios y Grupos (`chown` y `chgrp`)

Todo recurso en Linux pertenece a **un usuario** y a **un grupo**.

- **`chown` (Change Owner):**
  - Cambiar usuario dueño: `chown puma /felinos`
  - Cambiar usuario y grupo a la vez: `chown puma:felinos /felinos`
  - Cambiar solo el grupo: `chown :felinos /felinos`
- **`chgrp` (Change Group):**
  - Cambia exclusivamente el grupo propietario: `chgrp felinos /felinos`

---

## 5. Listas de Control de Acceso Extendidas (ACLs - `getfacl` y `setfacl`)

### ¿Por qué existen las ACLs?
El modelo estándar de Linux (`UGO`) solo permite **un dueño** y **un grupo**. Si necesitas darle permisos de escritura al usuario `puma` dentro de `/aves` sin cambiar el grupo de la carpeta ni meter a `puma` en el grupo `aves`, los permisos tradicionales no alcanzan. Las **ACLs** resuelven este problema permitiendo reglas por usuario y grupo individual.

### Comandos Principales
- **`getfacl <ruta>`**: Muestra la lista detallada de permisos tradicionales y extendidos.
- **`setfacl -m u:<usuario>:<permisos> <ruta>`**:
  - `-m`: Modificar la ACL.
  - `-R`: Aplicar de forma recursiva a subdirectorios y archivos.
  - `u:puma:rwx`: Asigna permisos específicos a un usuario.
  - `g:docentes:rx`: Asigna permisos específicos a un grupo adicional.
- **`setfacl -x u:<usuario> <ruta>`**: Elimina la regla ACL para ese usuario.
- **`setfacl -b <ruta>`**: Borra todas las reglas ACL extendidas.

> **Tip de diagnóstico:** Cuando una carpeta o archivo tiene una ACL configurada, el comando `ls -l` mostrará un signo de suma **`+`** al final de los permisos:
> `drwxrwx---+ 3 root aves 1024 ... /aves`

---

## 6. Máscara de Permisos por Defecto (`umask`)

La **`umask`** es una máscara en octal que filtra o resta permisos de los valores máximos al momento de crear archivos o carpetas.

### Permisos Base Máximos:
- **Directorios:** `777` (`rwxrwxrwx`) - Requieren ejecución (`x`) para poder navegar con `cd`.
- **Archivos:** `666` (`rw-rw-rw-`) - Por seguridad, nunca se crean con permiso de ejecución por defecto.

### Cálculo de Permisos con `umask`:
$$\text{Permisos Resultantes} = \text{Permisos Base} - \text{umask}$$

1. **Con `umask 022` (por defecto para `root`):**
   - Directorios: `777 - 022 = 755` (`drwxr-xr-x`)
   - Archivos: `666 - 022 = 644` (`-rw-r--r--`)
2. **Con `umask 077` (modo privado / estricto):**
   - Directorios: `777 - 077 = 700` (`drwx------`)
   - Archivos: `666 - 077 = 600` (`-rw-------`)
   *(Solo el creador puede ver o modificar el archivo/carpeta; grupo y otros tienen cero acceso).*

---

## 7. Repositorios de Paquetes y Gestión Offline (DNF / YUM)

### Estructura de un Archivo `.repo` en `/etc/yum.repos.d/`
Los gestores DNF y YUM buscan repositorios en archivos con extensión `.repo`:
```ini
[Identificador_Unico]
name=Nombre descriptivo del repositorio
baseurl=file:///ruta/o/url/del/repositorio
enabled=1
gpgcheck=0
```
- **`[Identificador]`**: Nombre interno del repositorio (sin espacios).
- **`baseurl`**: Protocolo y ubicación. Puede ser `file://` (disco local) o `http://` / `https://` (internet).
- **`enabled=1`**: Activa el repositorio (`0` lo desactiva).
- **`gpgcheck=0`**: `0` desactiva la validación de firma criptográfica; `1` la exige.

### Tipos de Imágenes ISO de Rocky Linux:
1. **DVD Full (~10 GB):** Contiene repositorios divididos en `BaseOS` (núcleo del SO) y `AppStream` (servidores y aplicaciones como `httpd`, `mariadb`, `nginx`).
2. **Minimal (~1.5 GB):** Contiene un solo repositorio llamado **`Minimal`** con únicamente los ~675 paquetes esenciales para levantar el sistema operativo.

### Comandos de Utilidad DNF:
- **`dnf clean all`**: Purga la caché local de metadatos para forzar la relectura de los repositorios.
- **`dnf list | wc -l`**: Cuenta cuántos paquetes están disponibles en los repositorios configurados.
- **`dnf list available`**: Muestra los paquetes que están en los repositorios pero aún no han sido instalados.
- **`dnf whatprovides <comando|archivo>`**: Identifica a qué paquete pertenece un comando que no está instalado (ej. `dnf whatprovides nc` ➔ paquete `nmap-ncat`).

---

## 8. Tips de Terminal y Productividad

- **`cd -`**: Regresa inmediatamente al directorio de trabajo anterior (función *Atrás*).
- **`cd ~` o simplemente `cd`**: Te traslada a tu carpeta de usuario (`/root` o `/home/usuario`).
- **`pwd`** (*Print Working Directory*): Imprime la ruta absoluta en la que te encuentras.
- **`ls -ld <carpeta>`**: Muestra los permisos y propietarios de la carpeta en sí, sin listar su contenido interior.
- **`mount -a`**: Prueba y monta todas las particiones configuradas en `/etc/fstab` sin necesidad de reiniciar la máquina.

---

## 9. Resumen Breve de Comandos (Cheat Sheet)

| Comando / Sintaxis | Categoría | Propósito Rápido |
| :--- | :--- | :--- |
| **`vgs` / `lvs` / `lsblk`** | Almacenamiento | Inspecciona grupos, volúmenes lógicos y discos. |
| **`lvcreate -L 50M -n <nom> <vg>`** | LVM | Crea un Logical Volume (redondeado a 52 MB por PE de 4M). |
| **`lvremove -y <ruta>`** | LVM | Elimina un volumen lógico sin pedir confirmación. |
| **`mkfs.ext4 <dispositivo>`** | Sistema de Archivos | Formatea una partición en formato ext4. |
| **`mount <disp> <carpeta>`** | Montaje | Conecta una partición a un directorio del sistema. |
| **`groupadd -g <GID> <grupo>`** | Grupos | Crea un grupo con identificador numérico fijo. |
| **`useradd -u <UID> -g <grp> <usr>`** | Usuarios | Crea un usuario con UID fijo y grupo primario asignado. |
| **`chmod 770 <carpeta>`** | Permisos | Aplica `rwxrwx---` (control total a dueño y grupo, nada a otros). |
| **`chown <usr>:<grp> <carpeta>`** | Propietarios | Cambia usuario dueño y grupo en una sola instrucción. |
| **`chgrp <grp> <carpeta>`** | Propietarios | Cambia únicamente el grupo propietario. |
| **`setfacl -R -m u:<usr>:rwx <dir>`**| ACL | Otorga permisos especiales a un usuario sobre una carpeta ajena. |
| **`getfacl <carpeta>`** | ACL | Muestra las reglas detalladas de control de acceso extendido. |
| **`umask <máscara>`** | Permisos | Configura la máscara de permisos para nuevos archivos (`777/666 - umask`). |
| **`dnf whatprovides <comando>`** | Paquetes | Averigua qué paquete provee un comando no instalado. |
| **`mount /dev/cdrom /mnt/`** | Repositorios | Monta la ISO localmente para instalaciones sin internet. |
| **`dnf clean all`** | Paquetes | Purga la caché de DNF para refrescar repositorios. |
| **`cd -` / `pwd`** | Navegación | Regresa al directorio anterior / Muestra la ruta actual. |