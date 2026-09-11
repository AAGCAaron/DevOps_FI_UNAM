# Manual Práctico - Clase 2: Ejecución, Objetivos y Comandos Paso a Paso

Este manual describe detalladamente **qué hace cada comando, su objetivo técnico y el resultado esperado** de todas las prácticas realizadas durante la Clase 2 en la máquina virtual Rocky Linux.

---

## Índice de Prácticas
1. [Fase 1: Diagnóstico de Almacenamiento y Reducción de Swap](#fase-1-diagnóstico-de-almacenamiento-y-reducción-de-swap)
2. [Fase 2: Creación, Formato y Montaje de Volúmenes LVM (50 MB)](#fase-2-creación-formato-y-montaje-de-volúmenes-lvm-50-mb)
3. [Fase 3: Creación de Grupos y Usuarios con Identificadores Fijos](#fase-3-creación-de-grupos-y-usuarios-con-identificadores-fijos)
4. [Fase 4: Asignación de Propietarios y Permisos 770](#fase-4-asignación-de-propietarios-y-permisos-770)
5. [Fase 5: Configuración de Permisos Extendidos con ACLs](#fase-5-configuración-de-permisos-extendidos-con-acls)
6. [Fase 6: Demostración de Permisos con `umask`](#fase-6-demostración-de-permisos-con-umask)
7. [Fase 7: Identificación e Instalación de Herramientas (`dnf whatprovides`)](#fase-7-identificación-e-instalación-de-herramientas-dnf-whatprovides)
8. [Fase 8: Configuración de Repositorio Local Offline desde CD-ROM](#fase-8-configuración-de-repositorio-local-offline-desde-cd-rom)

---

## Fase 1: Diagnóstico de Almacenamiento y Reducción de Swap

### Objetivo:
Liberar al menos 300 MB en el Volume Group `rlm` para poder alojar los nuevos volúmenes lógicos, ya que el disco estaba 100% asignado (`VFree = 0`). Se reduce la partición swap de 1 GB a 500 MB de forma segura.

### Comandos y Explicación:
```bash
# 1. Desactivar el uso de memoria swap en el sistema
swapoff -a
```
* **¿Qué hace?** Le dice al kernel de Linux que deje de usar el espacio de intercambio en disco y libere el dispositivo para poder manipularlo.

```bash
# 2. Eliminar el volumen lógico de swap existente
lvremove -y /dev/rlm/swap
```
* **¿Qué hace?** Destruye el volumen de 1 GB. El parámetro `-y` responde automáticamente "sí" a la confirmación de eliminación. Libera 1 GB completo en el grupo `rlm`.

```bash
# 3. Crear el nuevo volumen de swap reducido a 500 MB
lvcreate -y -L 500M -n swap rlm
```
* **¿Qué hace?** Reserva únicamente 500 MB para la nueva swap, dejando libres más de 500 MB en `rlm` para los siguientes ejercicios.

```bash
# 4. Formatear la swap preservando el UUID de /etc/fstab
mkswap -U f4f2dc9d-137e-49ad-9376-521b1e517db5 /dev/rlm/swap
```
* **¿Qué hace?** Inicializa la firma de swap asignando con `-U` el mismo UUID que el sistema tiene registrado en `/etc/fstab`, evitando errores al reiniciar.

```bash
# 5. Reactivar el swap
swapon -a
```
* **¿Qué hace?** Lee `/etc/fstab` y activa nuevamente la partición swap ya redimensionada.

```bash
# 6. Validar espacio disponible
vgs
```
* **Resultado:** La columna `VFree` ahora muestra `524.00m` de espacio libre disponible.

---

## Fase 2: Creación, Formato y Montaje de Volúmenes LVM (50 MB)

### Objetivo:
Crear 3 particiones virtuales independientes (`aves`, `peces` y `felinos`) con sistema de archivos `ext4` y conectarlas a sus respectivos directorios del sistema de archivos.

### Comandos y Explicación:
```bash
# 1. Crear los 3 Logical Volumes en el VG rlm
lvcreate -y -L 50M -n aves rlm
lvcreate -y -L 50M -n peces rlm
lvcreate -y -L 50M -n felinos rlm
```
* **¿Qué hace?** Asigna 50 MB de almacenamiento lógico para cada partición. Por la arquitectura de extents (bloques de 4 MB), LVM asigna automáticamente 52 MB a cada una.

```bash
# 2. Dar formato ext4 a cada volumen
mkfs.ext4 /dev/rlm/aves
mkfs.ext4 /dev/rlm/peces
mkfs.ext4 /dev/rlm/felinos
```
* **¿Qué hace?** Escribe las estructuras de datos (inodos, superbloques, tablas de archivos) del sistema de archivos `ext4` para que el sistema operativo pueda guardar archivos.

```bash
# 3. Crear las carpetas de punto de montaje
mkdir -p /aves /peces /felinos
```
* **¿Qué hace?** Crea los directorios en la raíz del sistema que servirán como puerta de acceso a los volúmenes formateados.

```bash
# 4. Montar los volúmenes en las carpetas
mount /dev/rlm/aves /aves
mount /dev/rlm/peces /peces
mount /dev/rlm/felinos /felinos
```
* **¿Qué hace?** Vincula el almacenamiento lógico con las carpetas recién creadas.

```bash
# 5. Validar el montaje
df -h | grep -E "aves|peces|felinos"
```
* **Resultado:** Muestra cada partición montada con un tamaño disponible de ~44 MB útiles.

---

## Fase 3: Creación de Grupos y Usuarios con Identificadores Fijos

### Objetivo:
Establecer una jerarquía de acceso controlada asignando a cada especie su propio grupo con un GID fijo y creando los usuarios correspondientes en sus rangos de UID específicos.

### Comandos y Explicación:
```bash
# 1. Crear los grupos con GID asignado
groupadd -g 1001 felinos
groupadd -g 2000 aves
groupadd -g 3000 peces
```
* **¿Qué hace?** Registra los 3 grupos en `/etc/group` garantizando identificadores fijos para auditoría y administración.

```bash
# 2. Crear usuarios del grupo felinos (UID 1000 - 1999)
useradd -u 1000 -g felinos puma
useradd -u 1002 -g felinos tigre
useradd -u 1003 -g felinos leon

# 3. Crear usuarios del grupo aves (UID 2001 - 2999)
useradd -u 2001 -g aves aguila
useradd -u 2002 -g aves cardenal
useradd -u 2003 -g aves colibri

# 4. Crear usuarios del grupo peces (UID 3001 - 3999)
useradd -u 3001 -g peces tiburon
useradd -u 3002 -g peces marlin
useradd -u 3003 -g peces ballena
```
* **¿Qué hace?** Registra cada usuario en `/etc/passwd` y `/etc/shadow`, asignando su UID exacto (`-u`) y vinculándolo de forma directa a su grupo principal (`-g`).

```bash
# 5. Validar la configuración
id puma && id aguila && id tiburon
```
* **Resultado:** Muestra que `puma` tiene UID 1000 y GID 1001, `aguila` tiene UID 2001 y GID 2000, y `tiburon` tiene UID 3001 y GID 3000.

---

## Fase 4: Asignación de Propietarios y Permisos 770

### Objetivo:
Asegurar las carpetas montadas para que únicamente el líder de cada especie (dueño) y los miembros de su grupo puedan acceder, leer y escribir archivos, bloqueando completamente al resto de los usuarios del sistema.

### Comandos y Explicación:
```bash
# 1. Asignar usuario líder y grupo correspondiente
chown puma:felinos /felinos
chown aguila:aves /aves
chown tiburon:peces /peces
```
* **¿Qué hace?** Asigna en una sola instrucción al usuario dueño y al grupo propietario de cada punto de montaje.

```bash
# 2. Configurar permisos 770 (rwxrwx---)
chmod 770 /felinos /aves /peces
```
* **¿Qué hace?**
  - **7 (rwx) al Dueño:** `puma`, `aguila` y `tiburon` tienen control total en su carpeta.
  - **7 (rwx) al Grupo:** Todos los miembros del grupo pueden crear, editar y listar archivos.
  - **0 (---) a Otros:** Usuarios ajenos tienen denegado cualquier intento de lectura o entrada.

```bash
# 3. Validar permisos
ls -ld /felinos /aves /peces
```
* **Resultado:**
  ```text
  drwxrwx---. 3 puma    felinos 1024 ... /felinos
  drwxrwx---. 3 aguila  aves    1024 ... /aves
  drwxrwx---. 3 tiburon peces   1024 ... /peces
  ```

---

## Fase 5: Configuración de Permisos Extendidos con ACLs

### Objetivo:
Permitir que el usuario `puma` (que pertenece a `felinos`) tenga permisos completos dentro de la carpeta `/aves`, sin cambiar el dueño ni agregarlo al grupo de las aves.

### Comandos y Explicación:
```bash
# 1. Instalar las herramientas de ACL (si no están presentes)
dnf install -y acl
```
* **¿Qué hace?** Descarga e instala los binarios `getfacl` y `setfacl`.

```bash
# 2. Asignar regla de ACL recursiva para puma
setfacl -R -m u:puma:rwx /aves
```
* **¿Qué hace?** Agrega una entrada en la tabla de control de acceso de `/aves` que otorga lectura, escritura y ejecución exclusivamente a `puma`.

```bash
# 3. Consultar las reglas activas
getfacl /aves
```
* **Resultado:** Se observa la línea `user:puma:rwx`, confirmando el permiso extendido.

```bash
# 4. Probar el acceso como puma
su - puma
touch /aves/archivo_de_puma.txt
ls -l /aves
exit
```
* **Resultado:** `puma` crea el archivo exitosamente a pesar de que los permisos tradicionales de `/aves` bloqueaban a cualquier usuario fuera del grupo `aves`.

---

## Fase 6: Demostración de Permisos con `umask`

### Objetivo:
Comprobar en la práctica cómo la máscara de permisos condiciona los permisos asignados automáticamente a los archivos y carpetas recién creados.

### Comandos y Explicación:
```bash
# 1. Establecer máscara restrictiva 077
umask 0077

# 2. Crear carpeta y archivo de prueba
mkdir /prueba_umask
touch /prueba_umask/archivo.txt

# 3. Verificar permisos resultantes
ls -ld /prueba_umask
ls -l /prueba_umask/archivo.txt
```
* **¿Qué hace y qué resultado da?**
  - Directorio: `777 - 077 = 700` (`drwx------`). Solo el usuario creador puede entrar; nadie más.
  - Archivo: `666 - 077 = 600` (`-rw-------`). Solo el usuario creador puede leer y editar; nadie más.

---

## Fase 7: Identificación e Instalación de Herramientas (`dnf whatprovides`)

### Objetivo:
Encontrar qué paquete proporciona la herramienta `nc` (Netcat) cuando no se conoce el nombre exacto del paquete en los repositorios e instalarla.

### Comandos y Explicación:
```bash
# 1. Consultar qué paquete contiene el comando nc
dnf whatprovides nc
```
* **¿Qué hace?** Escanea las bases de datos de metadatos y muestra que `/usr/bin/nc` proviene del paquete **`nmap-ncat`**.

```bash
# 2. Instalar el paquete identificado
dnf install -y nmap-ncat
```
* **¿Qué hace?** Instala la herramienta Netcat en el sistema.

```bash
# 3. Comprobar la instalación
nc
```
* **Resultado:** Responde `Ncat: You must specify a host to connect to. QUITTING.`, confirmando que el comando ya está disponible.

---

## Fase 8: Configuración de Repositorio Local Offline desde CD-ROM

### Objetivo:
Permitir la instalación de paquetes y dependencias en un entorno aislado sin conexión a internet, utilizando la imagen ISO montada en `/mnt`.

### Comandos y Explicación:
```bash
# 1. Montar el CD-ROM / ISO en /mnt
mount /dev/cdrom /mnt/
```
* **¿Qué hace?** Carga los archivos del medio de instalación en `/mnt` en modo solo lectura (`mounted read-only`).

```bash
# 2. Respaldar los repositorios oficiales de internet
cd /etc/yum.repos.d/
mv rocky* /root/
```
* **¿Qué hace?** Mueve temporalmente los archivos `.repo` de internet a `/root` para obligar a DNF a trabajar únicamente con el medio local.

```bash
# 3. Crear el archivo de repositorio local cdrom.repo
cat << 'EOF' > /etc/yum.repos.d/cdrom.repo
[InstallMedia]
name=Rocky Linux Minimal
baseurl=file:///mnt/Minimal
enabled=1
gpgcheck=0
EOF
```
* **¿Qué hace?** Configura DNF para leer los paquetes de la carpeta `/mnt/Minimal` (correspondiente a la ISO Minimal de Rocky Linux 10) usando el protocolo local `file://`.

```bash
# 4. Limpiar caché y consultar el catálogo offline
dnf clean all
dnf list | wc -l
```
* **Resultado:** Muestra **675** paquetes listos para instalarse localmente sin conexión a internet.

```bash
# 5. Instalar un paquete como prueba offline
dnf install -y bzip2
```
* **Resultado:** Se instala el paquete leyendo directamente desde el origen **`InstallMedia`**.

```bash
# 6. Restaurar los repositorios normales al terminar la práctica
mv /root/rocky* /etc/yum.repos.d/
dnf clean all
```
* **¿Qué hace?** Regresa los repositorios oficiales a su lugar y actualiza la caché para volver a tener acceso a internet cuando sea necesario.

---

## 9. Resumen Breve de Comandos (Cheat Sheet)

| Comando / Sintaxis | Categoría | Objetivo Práctico |
| :--- | :--- | :--- |
| **`vgs` / `lvs` / `lsblk`** | Almacenamiento | Diagnosticar espacio libre (`VFree`) y discos. |
| **`swapoff -a` / `swapon -a`** | Memoria Swap | Desactivar / reactivar el espacio swap para modificarlo. |
| **`lvcreate -y -L 50M -n <nom> <vg>`** | LVM | Crear volumen lógico (ajustado a 52 MB por PE de 4M). |
| **`lvremove -y <ruta>`** | LVM | Destruir un volumen lógico sin confirmación interactiva. |
| **`mkfs.ext4 <dispositivo>`** | Sistema de Archivos | Formatear una partición con sistema de archivos ext4. |
| **`mount <disp> <carpeta>`** | Puntos de Montaje | Conectar el volumen lógico a su carpeta en el sistema. |
| **`groupadd -g <GID> <grupo>`** | Grupos | Registrar grupo con identificador numérico fijo. |
| **`useradd -u <UID> -g <grp> <usr>`** | Usuarios | Crear usuario con UID específico y grupo principal. |
| **`chown <usr>:<grp> <carpeta>`** | Propiedad | Asignar usuario líder y grupo a la vez. |
| **`chmod 770 <carpeta>`** | Permisos | Conceder `rwxrwx---` (acceso a dueño/grupo, denegado a otros). |
| **`setfacl -R -m u:<usr>:rwx <dir>`**| Permisos ACL | Permitir acceso especial a un usuario ajeno al grupo. |
| **`getfacl <carpeta>`** | Auditoría ACL | Ver lista detallada de permisos y reglas extendidas. |
| **`umask 0077`** | Seguridad | Forzar que nuevos archivos/carpetas se creen como privados. |
| **`dnf whatprovides <comando>`** | DNF / YUM | Localizar qué paquete contiene una herramienta faltante. |
| **`mount /dev/cdrom /mnt/`** | Offline | Montar la ISO como repositorio local sin conexión. |
| **`dnf clean all`** | DNF / YUM | Limpiar la caché local de metadatos de repositorios. |
| **`cd -` / `pwd`** | Navegación | Volver a la ruta anterior / Consultar directorio actual. |

