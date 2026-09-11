# Manual práctico de particiones y LVM

## 1. Idea general

Cuando trabajas con almacenamiento en Linux, normalmente haces esto:

1. Crear la partición
2. Convertirla en un Physical Volume (PV)
3. Agregarla a un Volume Group (VG)
4. Crear o extender un Logical Volume (LV)
5. Dar formato al LV
6. Montarlo en un directorio
7. Guardar ese montaje en `/etc/fstab`
8. Validar que todo quede activo

> La partición 4 suele ocupar el espacio libre restante del disco y se usa como base para LVM.

---

## 2. Flujo básico para crear almacenamiento con LVM

### Paso 1: crear la partición

```bash
parted /dev/nvme0n1
mkpart
```

### ¿Para qué sirve?

- `parted` abre la herramienta para crear particiones.
- `mkpart` crea una nueva partición en el disco.
- En este caso, se crea la partición que será usada por LVM.

---

### Paso 2: crear el physical volume

```bash
pvcreate /dev/nvme0n1p4
```

### ¿Para qué sirve?

- Inicializa la partición como un volumen físico de LVM.
- El sistema la reconoce como almacenamiento administrable por LVM.

---

### Paso 3: crear o extender el volume group

```bash
vgcreate rl /dev/nvme0n1p4
```

O si ya existe:

```bash
vgextend rl /dev/nvme0n1p4
```

### ¿Para qué sirve?

- `vgcreate` crea un grupo de volúmenes.
- `vgextend` agrega más espacio a ese grupo.
- El VG agrupa discos/particiones para administrarlos juntos.

---

### Paso 4: crear o extender el logical volume

Crear uno nuevo:

```bash
lvcreate -L 100M -n lv_test01 rl
```

Extender uno existente:

```bash
lvextend -L 4.1G /dev/rl/root
```

### ¿Para qué sirve?

- `lvcreate` crea un nuevo volumen lógico.
- `lvextend` aumenta el tamaño de uno ya existente.
- El LV es la parte que finalmente el sistema usa como disco.

---

### Paso 5: darle formato al volumen

```bash
mkfs.xfs /dev/rl/lv_test01
```

O si es un volumen existente que ya estaba formateado:

```bash
xfs_growfs /dev/rl/root
```

### ¿Para qué sirve?

- `mkfs.xfs` crea el sistema de archivos (XFS) en un LV nuevo.
- `xfs_growfs` hace crecer el sistema de archivos para usar el espacio nuevo del LV.

---

### Paso 6: montar la partición o LV en un directorio

```bash
mkdir /test01
mount /dev/rl/lv_test01 /test01/
```

### ¿Para qué sirve?

- Conecta el volumen al sistema de archivos para que pueda usarse.
- El directorio `/test01` es el punto de montaje.

---

### Paso 7: agregar el montaje a `/etc/fstab`

```bash
vi /etc/fstab
```

Ejemplo:

```fstab
/dev/rl/lv_test01 /test01 xfs defaults 0 0
```

### ¿Para qué sirve?

- Hace que el montaje se cargue automáticamente al iniciar el sistema.

---

### Paso 8: validar con `mount -a`

```bash
mount -a
```

### ¿Para qué sirve?

- Comprueba si la configuración de `/etc/fstab` es correcta.
- Si hay un error, el comando lo detecta sin reiniciar.

---

### Paso 9: recargar servicios del sistema

```bash
systemctl daemon-reload
```

### ¿Para qué sirve?

- Recarga la configuración de systemd.
- Importante cuando cambian servicios o unidades del sistema.

---

## 3. Historial real explicado

```bash
[root@tsic2 ~]# history
    1  lsblk
    2  vgs
    3  parted
    4  lsblk
    5  pvcreate /dev/nvme0n1p4
    6  pvs
    7  vgs
    8  vgcreate rl /dev/nvme0n1p4
    9  vgextend rl /dev/nvme0n1p4
   10  vgs
   11  lvs
   12  lvextend -L 4.1G /dev/rl/root
   13  xfs_growfs /dev/rl/root
   14  lvs
   15  lsblk
   16  history
```

### Qué estaba pasando ahí

#### `lsblk`
Muestra los discos y particiones.

#### `vgs`
Muestra los grupos de volumenes ya creados.

#### `parted`
Abre el particionador para crear o modificar particiones.

#### `pvcreate /dev/nvme0n1p4`
Convierte la partición 4 en un Physical Volume.

#### `pvs`
Lista los PVs existentes.

#### `vgcreate rl /dev/nvme0n1p4`
Crea el grupo de volumen `rl` usando esa partición.

#### `vgextend rl /dev/nvme0n1p4`
Agrega la partición al VG si se necesita más espacio.

#### `lvs`
Muestra los Logical Volumes creados.

#### `lvextend -L 4.1G /dev/rl/root`
Aumenta el tamaño del volumen raíz.

#### `xfs_growfs /dev/rl/root`
Hace crecer el sistema de archivos para usar ese espacio adicional.

---

## 4. Ejemplo de creación de un volumen nuevo

```bash
lvcreate -L 100M -n lv_test01 rl
lvs
mkfs.xfs /dev/rl/lv_test01
mkdir /test01
mount /dev/rl/lv_test01 /test01/
lsblk
vi /etc/fstab
mount -a
vi /etc/fstab
mount -a
systemctl daemon-reload
history
```

### ¿Qué hace cada paso?

#### `lvcreate -L 100M -n lv_test01 rl`
Crea un volumen lógico llamado `lv_test01` con 100 MB en el VG `rl`.

#### `lvs`
Muestra los volúmenes lógicos actuales.

#### `mkfs.xfs /dev/rl/lv_test01`
Formatea el volumen con XFS.

#### `mkdir /test01`
Crea el directorio de montaje.

#### `mount /dev/rl/lv_test01 /test01/`
Monta el volumen en `/test01`.

#### `lsblk`
Verifica el resultado final.

#### `vi /etc/fstab`
Agrega la entrada para montar automáticamente al reiniciar.

#### `mount -a`
Prueba si el archivo `/etc/fstab` está bien escrito.

#### `systemctl daemon-reload`
Recarga la configuración del sistema.

---

## 5. Resumen corto para estudiar

### Secuencia normal

```bash
parted
pvcreate /dev/nvme0n1p4
vgcreate rl /dev/nvme0n1p4
lvcreate -L 100M -n lv_test01 rl
mkfs.xfs /dev/rl/lv_test01
mkdir /test01
mount /dev/rl/lv_test01 /test01/
vi /etc/fstab
mount -a
```

### Secuencia para extender espacio

```bash
lvextend -L 4.1G /dev/rl/root
xfs_growfs /dev/rl/root
```

---

## 6. Regla rápida para recordar

- `parted` = crear la partición
- `pvcreate` = convertir en volumen físico
- `vgcreate` / `vgextend` = crear o ampliar el grupo
- `lvcreate` / `lvextend` = crear o ampliar el volumen lógico
- `mkfs.xfs` / `xfs_growfs` = formatear o crecer sistema de archivos
- `mount` = montar en un directorio
- `/etc/fstab` = montar automáticamente al iniciar
- `mount -a` = validar la configuración

<span style="background-color: #EAF2F8; color: #1B4F72; padding: 4px 8px; border-radius: 6px;">Este flujo es la base para gestionar almacenamiento en Linux con LVM.</span>

---

## 7. Resumen visual

- <span style="color: #2E86C1;">Partición</span> = espacio físico en el disco
- <span style="color: #E67E22;">PV</span> = volumen físico administrado por LVM
- <span style="color: #28B463;">VG</span> = grupo de almacenamiento
- <span style="color: #8E44AD;">LV</span> = volumen lógico que el sistema usa
- <span style="color: #D35400;">FS</span> = sistema de archivos (XFS)
- <span style="color: #1F618D;">Mount</span> = conectar ese volumen a un directorio

> Si entiendes esta relación, ya entiendes casi todo el concepto de LVM en Linux.