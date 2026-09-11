# Manual - Clase 3: Gestión Avanzada de Paquetes, RPM vs DNF y Compatibilidad de Versiones

Este manual documenta los conceptos, comandos y prácticas realizados durante la **Clase 3**, enfocados en la restauración de repositorios oficiales, la diferencia entre el gestor de bajo nivel (`rpm`) y el gestor de alto nivel (`dnf`), y la compatibilidad de paquetes entre versiones de distribución (`el10` vs `el9`).

---

## 1. Restauración de Repositorios Oficiales tras Práctica Offline

En la clase anterior desactivamos los repositorios con internet moviéndolos a `/root/` y usando `cdrom.repo`. En esta sesión se restauraron los repositorios oficiales de Rocky Linux:

```bash
# 1. Localizar los repositorios existentes en el sistema
find / -name '*.repo'

# 2. Mover cdrom.repo a /root para desactivar el repositorio del CD-ROM
cd /etc/yum.repos.d/
mv cdrom.repo /root/

# 3. Limpiar metadatos en caché y verificar repositorios activos
dnf clean all
dnf repolist
```

### Explicación:
- **`find / -name '*.repo'`**: Busca en todo el disco cualquier archivo de configuración de repositorios.
- **`mv cdrom.repo /root/`**: Al sacar el archivo `.repo` de `/etc/yum.repos.d/`, DNF deja de buscar paquetes en `/mnt/Minimal`.
- **`dnf clean all`**: Limpia la caché local de metadatos para forzar a DNF a conectarse a los servidores oficiales de internet.
- **`dnf repolist`**: Muestra los repositorios activos (`baseos`, `appstream`, `extras`).

---

## 2. Búsqueda de Paquetes con `dnf whatprovides`

Cuando conocemos el nombre de un comando ejecutable (por ejemplo `nc`), pero no sabemos qué paquete lo contiene:

```bash
dnf whatprovides nc
```

### Salida Obtenida:
```text
nmap-ncat-4:7.92-5.el10.x86_64 : Nmap's Netcat replacement
Repositorio : @System
Resultado de:
Proporciona : nc = 4:7.92-5.el10
```

### Puntos Clave de la Salida:
1. **`nmap-ncat`**: Es el paquete que provee el comando `nc`.
2. **`@System`**: Indica que el paquete **ya se encuentra instalado** en la máquina virtual.
3. **`.el10`**: Indica que el paquete está compilado para la arquitectura **Enterprise Linux 10** (Rocky Linux 10).

---

## 3. Compatibilidad de Versiones del Sistema Operativo (`cat /etc/os-release`)

Para comprobar qué versión exacta de Linux estamos ejecutando y qué paquetes RPM son compatibles:

```bash
cat /etc/os-release
```

### Parámetros Clave:
- **`VERSION_ID="10.2"`**: Versión 10.2 de Rocky Linux.
- **`PLATFORM_ID="platform:el10"`**: Familia de plataforma **Enterprise Linux 10**.

> **Regla de compatibilidad de RPMs:**
> - Los paquetes con sufijo **`.el10.x86_64.rpm`** son nativos y totalmente compatibles con Rocky Linux 10.
> - Los paquetes con sufijo **`.el9.x86_64.rpm`** corresponden a Rocky Linux 9 y provocarán errores de dependencias (librerías compartidas más antiguas de `glibc` u OpenSSL).

---

## 4. Diferencia entre `rpm` y `dnf`

| Característica | `rpm` (Bajo Nivel) | `dnf` (Alto Nivel) |
| :--- | :--- | :--- |
| **Resolución de dependencias** | ❌ No resuelve dependencias; si falta una librería, falla y aborta. | ✔️ Resuelve y descarga automáticamente todas las dependencias necesarias. |
| **Uso de repositorios** | ❌ Solo trabaja con archivos `.rpm` locales que ya estén descargados. | ✔️ Busca y descarga desde repositorios locales o en internet. |
| **Velocidad de ejecución** | Muy rápido para consultar o instalar paquetes locales individuales. | Más completo, actualiza metadatos y verifica firmas GPG. |

### Significado de las banderas en `rpm -ivh`:
- **`-i`** (*install*): Instala el paquete en el sistema.
- **`-v`** (*verbose*): Muestra información detallada del proceso.
- **`-h`** (*hash*): Muestra una barra de progreso visual usando almohadillas (`# [100%]`).

### Comportamiento cuando un paquete ya está instalado:
```bash
rpm -ivh nmap-ncat-*.el10.x86_64.rpm
```
**Salida:**
```text
Verifying...       ################################# [100%]
Preparando...      ################################# [100%]
    el paquete nmap-ncat-4:7.92-5.el10.x86_64 ya está instalado
```
`rpm` protege la integridad del sistema impidiendo sobreescribir un paquete existente a menos que se use explícitamente `--replacepkgs` o `-U` (*upgrade*).

---

---

## 5. Control de Acceso por IP usando Zonas de Firewall (Zona `trusted`)

### 5.1 ¿Qué es `firewalld` y `firewall-cmd`?
`firewalld` es el demonio de firewall dinámico predeterminado en **Rocky Linux**, **RHEL** y **Fedora**. Actúa como una capa de abstracción de alto nivel sobre el subsistema del kernel de Linux (`nftables` / `iptables`).

A diferencia del antiguo `iptables`, `firewalld`:
- Permite modificar reglas en caliente sin reiniciar el demonio ni interrumpir las conexiones de red activas.
- Utiliza el concepto de **Zonas** para definir niveles de confianza para diferentes conexiones de red.
- Ofrece la herramienta de línea de comandos **`firewall-cmd`** para consultar y configurar su comportamiento.

---

### 5.2 Mecanismo de Evaluación y Prioridad de Zonas

En `firewalld`, el tráfico entrante no se evalúa al azar; sigue un orden estricto de **dos niveles de precedencia**:

```text
[ Paquete Entrante ]
         │
         ▼
¿Coincide la IP de origen con un "source" en alguna zona?
   ├── SÍ ──► [ Se procesa en esa Zona (ej. "trusted") ] ──► ACCEPT / REJECT
   │
   └── NO ──► ¿A qué interfaz pertenece? (ej. enp0s3)
                    │
                    ▼
              [ Se procesa en la Zona asignada a la Interfaz (ej. "public") ]
```

1. **Prioridad 1 (IP de Origen - `source`):** Si una IP o subred está asignada a una zona específica con `--add-source`, esa regla tiene prioridad absoluta sobre cualquier interfaz.
2. **Prioridad 2 (Interfaz de Red - `interface`):** Si la IP de origen no coincide con ninguna zona de origen, el paquete cae en la zona asignada a la tarjeta de red (por defecto, la zona `public`).

---

### 5.3 ¿Cómo funciona la Zona `trusted`?

Cada zona tiene un atributo llamado **`target`** que determina qué hacer con los paquetes por defecto:

| Zona | Target por Defecto | Comportamiento |
| :--- | :---: | :--- |
| **`trusted`** | **`ACCEPT`** | Acepta **todo** el tráfico entrante de cualquier origen que pertenezca a esta zona, sin necesidad de abrir servicios o puertos individuales. |
| **`public`** | **`default` (REJECT/DROP)** | Rechaza todo el tráfico entrante excepto los servicios y puertos que hayan sido explícitamente abiertos (como `ssh`). |
| **`drop`** | **`DROP`** | Descarta silenciosamente todos los paquetes entrantes sin enviar respuesta de rechazo. |

Al colocar una IP (ej. `192.168.1.50`) dentro de `trusted` y retirar `http` de la zona `public`:
- La IP `192.168.1.50` coincide con la **Prioridad 1** (`trusted`) y su petición HTTP es **aceptada** de inmediato.
- Cualquier otra IP cae en la **Prioridad 2** (`public`), donde el puerto 80 está cerrado, y la petición es **rechazada**.

---

### 5.4 Desglose Detallado de Parámetros de `firewall-cmd`

| Parámetro | Tipo | ¿Qué hace internamente? |
| :--- | :---: | :--- |
| **`--permanent`** | Persistencia | Guarda la configuración en los archivos XML de disco (`/etc/firewalld/zones/`). Si no se incluye, la regla solo vive en la memoria RAM (*runtime*) y se perderá al reiniciar o recargar el firewall. |
| **`--zone=<nombre>`** | Ámbito | Especifica sobre cuál de las zonas predefinidas (`public`, `trusted`, `internal`, `dmz`, etc.) se aplicará la acción. Si se omite, se aplica sobre la zona predeterminada (`default-zone`). |
| **`--add-source=<IP/CIDR>`** | Enrutamiento | Asocia una dirección IP individual (ej. `192.168.1.50`) o una subred completa (ej. `192.168.1.0/24`) a la zona especificada. |
| **`--remove-service=<servicio>`** | Restricción | Elimina la apertura preconfigurada de puertos de un servicio (ej. `http` cierra automáticamente el puerto `80/tcp`). Los servicios están definidos en `/usr/lib/firewalld/services/`. |
| **`--remove-port=<puerto/proto>`**| Restricción | Cierra un puerto numérico específico junto con su protocolo de transporte (ej. `80/tcp`). |
| **`--reload`** | Aplicación | Vuelve a leer los archivos XML permanentes de `/etc/firewalld/` y los compila en el kernel (`nftables`) sin cerrar ni interrumpir sesiones activas (como conexiones SSH). |
| **`--list-all`** | Consulta | Inspecciona en pantalla el estado completo de una zona: target, interfaces vinculadas, fuentes (`sources`), servicios habilitados, puertos y rich rules. |

---

### 5.5 Comandos de Ejecución Paso a Paso

#### Paso 1: Asegurarse de que HTTP esté cerrado para el público general
```bash
firewall-cmd --permanent --zone=public --remove-service=http
firewall-cmd --permanent --zone=public --remove-port=80/tcp
```
* **Objetivo:** Evitar que cualquier usuario o IP que caiga en la zona predeterminada (`public`) pueda conectarse al servidor web.

#### Paso 2: Asignar la IP permitida a la zona `trusted`
```bash
firewall-cmd --permanent --zone=trusted --add-source=192.168.1.50
```
* **Objetivo:** Registrar la IP `192.168.1.50` en el archivo XML `/etc/firewalld/zones/trusted.xml`, otorgándole paso libre hacia cualquier servicio del servidor.

#### Paso 3: Aplicar los cambios en el kernel
```bash
firewall-cmd --reload
```
* **Objetivo:** Compilar la nueva configuración en memoria en tiempo real sin cortar conexiones activas.

#### Paso 4: Validar la configuración
```bash
# Ver que la IP esté dentro de la zona trusted
firewall-cmd --zone=trusted --list-all

# Ver que la zona public NO tenga abierto el servicio http
firewall-cmd --zone=public --list-all
```

#### Salida esperada en `trusted`:
```text
trusted (active)
  target: ACCEPT
  sources: 192.168.1.50
  services: 
  ports: 
  protocols: 
  masquerade: no
  forward-ports: 
  source-ports: 
  icmp-blocks: 
  rich rules: 
```

---

## 6. SELinux (Security-Enhanced Linux) y Servidor Web Apache (`httpd`)

### 6.1 ¿Qué es SELinux y cuáles son sus modos?
SELinux es un sistema de **Control de Acceso Obligatorio (MAC - Mandatory Access Control)** implementado en el kernel de Linux. A diferencia de los permisos tradicionales (`rwxrwxrwx`), donde el dueño del archivo decide quién accede (DAC - Discretionary Access Control), en SELinux **el kernel aplica políticas de seguridad estrictas que ni siquiera el usuario `root` puede violar sin autorización explícita**.

#### Modos de operación de SELinux:
- **`Enforcing` (1):** Activo y estricto. Cualquier acción no permitida por la política es **bloqueada** y registrada en los registros de auditoría (`/var/log/audit/audit.log`).
- **`Permissive` (0):** Modo diagnóstico. Permite todas las acciones, pero **registra advertencias** en los logs como si estuvieran bloqueadas.
- **`Disabled`:** Completamente apagado (requiere reiniciar el sistema).

#### Comandos de control de modo:
```bash
# Consultar el modo actual
getenforce

# Cambiar temporalmente a modo estricto
setenforce 1

# Cambiar temporalmente a modo diagnóstico
setenforce 0
```

---

### 6.2 Paquetes de Administración de SELinux
En instalaciones mínimas de Rocky Linux / RHEL, las herramientas de configuración de SELinux no vienen preinstaladas.

```bash
dnf install -y policycoreutils-python-utils setroubleshoot-server
```
- **`policycoreutils-python-utils`**: Proporciona el comando imprescindible **`semanage`** para administrar puertos, contextos y políticas.
- **`setroubleshoot-server`**: Analiza automáticamente los bloqueos de SELinux y genera recomendaciones claras de solución legibles para humanos (`sealert`).

---

### 6.3 Contextos de Seguridad de SELinux (`ls -Z`)
Todo archivo, carpeta, puerto y proceso en Linux tiene una etiqueta de seguridad llamada **Contexto de SELinux**. Se visualiza agregando la bandera mayúscula **`-Z`**:

```bash
ls -ldZ /var/www/html
ls -lZ /etc/httpd/
```

#### Estructura de una etiqueta de SELinux:
`system_u:object_r:httpd_sys_content_t:s0`

| Componente | Valor Ejemplo | Significado |
| :--- | :--- | :--- |
| **Usuario** | `system_u` | Identidad de SELinux asignada por el sistema. |
| **Rol** | `object_r` | Rol del objeto (procesos usan roles de usuario; archivos usan `object_r`). |
| **Tipo (Type)** | **`httpd_sys_content_t`** | **El más importante:** Define a qué tipo pertenece el recurso. Apache solo puede leer archivos cuyo tipo sea `httpd_sys_content_t` o `httpd_config_t`. |
| **Nivel** | `s0` | Nivel de sensibilidad de seguridad multinivel (MLS/MCS). |

---

### 6.4 Instalación y Puesta en Marcha de Apache (`httpd`)

```bash
# 1. Instalar el servidor web
dnf install -y httpd

# 2. Iniciar el servicio y habilitarlo para que arranque con el sistema
systemctl enable --now httpd

# 3. Probar la conexión local en el puerto estándar 80
curl localhost
```

---

### 6.5 Cambio de Puerto de Apache al Puerto 81 y Conflicto con SELinux

#### El Procedimiento:
1. Editar la configuración de Apache:
   ```bash
   vi /etc/httpd/conf/httpd.conf
   ```
2. Modificar la directiva de puerto:
   ```apache
   Listen 81
   ```
   *(Guardar con `:wq` y presionar Enter)*.

3. Al intentar reiniciar el servicio:
   ```bash
   systemctl restart httpd
   ```
   *(Si el puerto no está en la política de SELinux, el comando fallará con un error de inicio)*.

4. Comprobar el error:
   ```bash
   systemctl status httpd
   ```
   *(Para salir del visor de estado, se presiona la tecla **`q`**)*.

#### ¿Por qué ocurre el bloqueo de SELinux?
Por defecto, SELinux tiene una política llamada **`http_port_t`** que define en qué puertos de red tiene permiso de escuchar el proceso de Apache (usualmente 80, 443, 8080, etc.). Si Apache intenta escuchar en un puerto no autorizado, SELinux intercepta la llamada al sistema (`bind`) y la rechaza con un error de `Permission denied`.

---

### 6.6 Solución: Autorizar el Puerto 81 en SELinux con `semanage port`

```bash
# 1. Consultar la lista de puertos autorizados para Apache en SELinux
semanage port -l | grep http_port_t

# 2. Agregar formalmente el puerto 81 TCP a la política http_port_t
semanage port -a -t http_port_t -p tcp 81

# 3. Reiniciar el servicio Apache
systemctl restart httpd

# 4. Validar que Apache está escuchando exitosamente en el puerto 81
systemctl status httpd

# 5. Probar respuesta HTTP en el puerto 81
curl localhost:81
```

#### Parámetros del comando `semanage port`:
- **`-a`** (*add*): Agrega una nueva regla de puerto.
- **`-t http_port_t`** (*type*): Especifica el tipo de puerto de SELinux asignado al servicio web.
- **`-p tcp`** (*protocol*): Protocolo de transporte (`tcp` o `udp`).
- **`81`**: El número de puerto específico a autorizar.

---

### 6.7 Booleanos de SELinux (`getsebool` / `setsebool`)
Los **booleanos** son interruptores binarios (on/off) que permiten modificar el comportamiento de SELinux en tiempo de ejecución sin recompilar políticas:

```bash
# Consultar todos los booleanos relacionados con Apache
getsebool -a | grep httpd
```

#### Ejemplos comunes de booleanos en DevOps:
- **`httpd_can_network_connect`**: Permite a Apache conectarse a servicios de red externos (ej. bases de datos en otros servidores).
- **`httpd_enable_homedirs`**: Permite a Apache leer contenido web desde las carpetas `/home/` de los usuarios.
- Para cambiar un booleano de forma permanente:
  ```bash
  setsebool -P httpd_can_network_connect on
  ```
  *(La bandera `-P` hace que el cambio sobreviva a reinicios del servidor)*.

---

## 7. Resumen Breve de Comandos de la Clase 3 (Cheat Sheet)

| Comando / Sintaxis | Categoría | Propósito Rápido |
| :--- | :--- | :--- |
| **`find / -name '*.repo'`** | Búsqueda | Encuentra todos los archivos de configuración de repositorios. |
| **`dnf clean all`** | DNF | Limpia la caché local de metadatos de repositorios. |
| **`dnf repolist`** | DNF | Lista los repositorios que están activos actualmente. |
| **`dnf whatprovides <cmd>`** | DNF | Busca qué paquete RPM contiene un ejecutable o archivo. |
| **`dnf download <paquete>`** | DNF | Descarga el archivo `.rpm` al directorio actual sin instalarlo. |
| **`cat /etc/os-release`** | Sistema | Consulta la versión de Rocky Linux y plataforma (`el10` vs `el9`). |
| **`rpm -ivh <archivo.rpm>`** | RPM | Instala un RPM local de bajo nivel con barra de progreso `###`. |
| **`dnf install <archivo.rpm>`** | DNF | Instala un RPM local resolviendo dependencias de forma idempotente. |
| **`firewall-cmd --zone=trusted --add-source=<IP>`** | Firewall | Añade una IP de confianza a la zona `trusted` (`target: ACCEPT`). |
| **`firewall-cmd --reload`** | Firewall | Recarga y aplica las reglas permanentes sin cortar conexiones. |
| **`firewall-cmd --list-all`** | Firewall | Inspecciona los puertos, servicios y fuentes activas de una zona. |
| **`getenforce` / `setenforce 1`** | SELinux | Consulta o fija el modo de operación (`Enforcing` o `Permissive`). |
| **`ls -ldZ <ruta>`** | SELinux | Muestra el contexto de seguridad (`usuario:rol:tipo:nivel`). |
| **`systemctl enable --now httpd`** | Systemd | Inicia y habilita el servidor web Apache al mismo tiempo. |
| **`semanage port -l \| grep http_port_t`** | SELinux | Lista los puertos de red autorizados para Apache. |
| **`semanage port -a -t http_port_t -p tcp <puerto>`** | SELinux | Autoriza un puerto TCP personalizado para Apache en SELinux. |
| **`getsebool -a \| grep httpd`** | SELinux | Muestra los interruptores booleanos configurados para Apache. |
| **`curl localhost:<puerto>`** | Red | Prueba y descarga la respuesta HTTP de un servicio web local. |
