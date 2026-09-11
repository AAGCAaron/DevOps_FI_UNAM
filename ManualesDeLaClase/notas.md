# Temas Selectos de Ingeniería en Computación - Devops

## Instalación de Máquina Virtual
> VMware Workstation Pro
- Instalar el sistema operativo después
- Red Hat Linux 9.7 - 9.8
- Network connection: NAT
- Virtual Disk: NVMe
- Disk: Create virtual Disk

### Particiones del Disco
- `/home` - 1024MiB
- `/` - 4 giB
- `var` -  1024
- `swap` - 1024
- `tmp` - 1024

Particiones físicas:
- `boot` - 1024
- `boot/efi` - 1024

Base selection
- Minimal install

Kdump: Desabilitado y Allow SSH Login with password

### Particiones Físicas y LVM
- Física
- Grupo `vgcreate rl`
- Particiones lógicas
> `vgs // Para crear particiones` 

1. Crear la partición
> `parted // Para crear particiones` 

> `mkpart // Para crear la partición` 

> `lsblk` 
2. Crear el physical volume
> `pvcreate // Crear el volumen` 
> `pvs // mostrar los volumenes`
3. Extender el physical volume group
> `vgextend rl // extender los volumenes`
4. Extender la partición
> `lvextend -Lv 4.41G <particion> // extender una partición del mismo grupo`

> `lvcreate // crear partición`
5. Extender el formato 
> `xfs_grow //`

> `mkfs.fs // Darle formato`

6. Montar el volumen en caso de que sea una nueva partición
> `mkdir /test01 //`
> `mount <particion> <directorio> //`

7. Hacer permanente el volumen (con vi o nano)
> `vi /etc/fstab // Modificar el archivo`

> `mount -a // Validar errores`

> `systemctl daemon-reload // Best-practices`


 