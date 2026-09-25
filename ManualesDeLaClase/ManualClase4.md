# Manual - Clase 4: Contenedores con Podman, Redes y Gestión de Servicios

Este manual documenta de forma exhaustiva los conceptos teóricos, la ejecución práctica y la arquitectura detrás de los comandos de la **Clase 4**, enfocados en la administración de usuarios del sistema con SSSD/Sudo y el despliegue de **contenedores con Podman**, mapeo de puertos, inspección de redes y ciclo de vida de contenedores.

---

## 1. Gestión de Identidad y Privilegios (SSSD y Sudo)

En entornos empresariales (RHEL, Rocky Linux), la autenticación de usuarios suele centralizarse mediante **SSSD (System Security Services Daemon)**, el cual conecta el sistema con servidores LDAP, Active Directory o FreeIPA.

```bash
# 1. Invalidar la memoria caché de SSSD y reiniciar el demonio
sss_cache -E && systemctl restart sssd

# 2. Consultar qué privilegios de sudo tiene asignados el usuario operador01
sudo -l -U operador01

# 3. Cambiar de sesión al usuario operador01 con su entorno completo
su - operador01
```

### Explicación Técnica:
- **`sss_cache -E`**: Expira y vacía inmediatamente toda la caché local de usuarios, grupos y reglas de red para forzar la revalidación con el servidor de identidad.
- **`sudo -l -U <usuario>`**: Lista los comandos que el usuario especificado tiene permitido ejecutar como superusuario según las políticas en `/etc/sudoers` o `/etc/sudoers.d/`.
- **`su - <usuario>`**: Inicia sesión como el usuario cargando sus variables de entorno (`PATH`, `HOME`, etc.).

> **Nota:** Si `operador01` es un usuario local y aún no ha sido creado en tu máquina virtual, se puede crear con: `useradd -m operador01 && passwd operador01`.

---

## 2. Fundamentos de Podman (Pod Manager)

### ¿Qué es Podman y en qué se diferencia de Docker?
**Podman** es el motor de contenedores estándar en el ecosistema Red Hat Enterprise Linux y Rocky Linux. Está diseñado como un reemplazo directo y compatible con Docker (`alias docker=podman`), pero con diferencias arquitectónicas fundamentales:

| Característica | Docker | Podman |
| :--- | :--- | :--- |
| **Arquitectura de Demonio** | Requiere un demonio central en segundo plano (`dockerd`) que corre como `root`. | **Daemonless:** No requiere ningún demonio corriendo. Los contenedores son procesos hijos directos. |
| **Contenedores Rootless** | Complejo de configurar; por defecto requiere privilegios de `root`. | **Rootless nativo:** Los usuarios sin privilegios pueden crear y gestionar contenedores sin `sudo`. |
| **Seguridad y Fork/Exec** | Si el demonio cae, todos los contenedores se ven afectados. | Utiliza el modelo estándar de Linux `fork/exec`, integrándose con `systemd`, `auditd` y `cgroups v2`. |
| **Registro de Imágenes** | Docker Hub por defecto. | Consulta registros configurables (`quay.io`, `docker.io`, `registry.access.redhat.com`). |

---

## 3. Instalación de Podman y Gestión de Imágenes

```bash
# 1. Instalar Podman (requiere privilegios de root o sudo)
dnf install -y podman

# 2. Listar las imágenes de contenedores almacenadas localmente
podman images

# 3. Descargar la imagen oficial de Nginx desde Docker Hub
podman pull docker.io/library/nginx

# 4. Verificar que la imagen se haya descargado correctamente
podman images
```

### Desglose de la Salida de `podman images`:
```text
REPOSITORY               TAG         IMAGE ID      CREATED      SIZE
docker.io/library/nginx  latest      bf325c933fbb  2 days ago   192 MB
```
- **REPOSITORY**: Ruta completa del registro y repositorio de la imagen.
- **TAG**: Etiqueta de versión (por defecto `latest`).
- **IMAGE ID**: Hash identificador único de la imagen.
- **SIZE**: Tamaño de la imagen comprimida con sus capas.

---

## 4. Despliegue de Contenedores Nginx

### Caso A: Contenedor sin Mapeo de Puertos (`nginx01`)
```bash
podman run -dit --name nginx01 docker.io/library/nginx
```
- **`-d`** (*detached*): Ejecuta el contenedor en segundo plano (demonio).
- **`-i`** (*interactive*): Mantiene abierto el canal STDIN para interactuar si fuera necesario.
- **`-t`** (*tty*): Asigna una pseudo-terminal al contenedor.
- **`--name nginx01`**: Asigna un nombre amigable al contenedor para evitar referirse a él por su hash.

### Caso B: Contenedor con Mapeo de Puertos hacia el Host (`nginx02`)
```bash
podman run -dit --name nginx02 -p 8080:80 docker.io/library/nginx:latest
```
- **`-p 8080:80`** (*Port Forwarding*): Conecta el **puerto 8080 de la máquina host** con el **puerto 80 interno del contenedor**. Cualquier petición a `localhost:8080` se redirige automáticamente a Nginx dentro del contenedor.

### Comprobación de Contenedores Activos:
```bash
podman ps -a
```
- **`-a`** (*all*): Muestra tanto los contenedores en ejecución (*Up*) como los que están detenidos (*Exited*).

---

## 5. Redes en Podman e Inspección de Contenedores

Al instalar y ejecutar Podman, se crea un puente de red virtual (normalmente llamado `podman0` en el rango `10.88.0.0/16`):

```bash
# 1. Ver interfaces de red y la IP del puente de Podman
ip addr

# 2. Inspeccionar la configuración de red y la IP interna asignada al contenedor
podman inspect nginx02 | grep -i IPAddress
```

### Pruebas de Conectividad con `curl`:

1. **Acceso directo por la IP interna de la red de Podman:**
   ```bash
   curl 10.88.0.3
   ```
   *(Funciona internamente desde la máquina virtual porque el host tiene ruta directa a la red `10.88.0.0/16`).*

2. **Acceso mediante el puerto publicado en localhost:**
   ```bash
   curl localhost:8080
   ```
   *(Demuestra que el mapeo de puertos `-p 8080:80` está funcionando).*

3. **Acceso desde la IP de la máquina virtual en la red local:**
   ```bash
   curl 192.168.100.148:8080
   ```
   *(Permite que otros equipos de la red accedan al servicio web expuesto).*

---

## 6. Ciclo de Vida de los Contenedores (`stop` y `start`)

Los contenedores son efímeros pero conservan su estado mientras no sean destruidos con `podman rm`.

```bash
# 1. Detener el contenedor
podman stop nginx02
# (o usando su ID: podman stop <CONTAINER_ID>)

# 2. Comprobar que el servicio ya no responde
curl localhost:8080
# Salida esperada: curl: (7) Failed to connect to localhost port 8080: Conexión rehusada

# 3. Iniciar nuevamente el contenedor existente
podman start nginx02

# 4. Validar que vuelve a responder de inmediato
curl localhost:8080
# Salida: Código HTML de "Welcome to nginx!"
```

---

---

## 7. Acceso e Interacción con el Contenedor (`podman exec`)

Para entrar a inspeccionar o modificar la configuración interna de un contenedor en ejecución sin detenerlo:

```bash
podman exec -it nginx02 /bin/bash
```

### Explicación de los Parámetros:
- **`exec`**: Ejecuta un comando dentro de un contenedor que **ya está en ejecución** (a diferencia de `run`, que crea uno nuevo).
- **`-i`** (*interactive*): Mantiene abierto el flujo estándar de entrada (STDIN) para recibir órdenes desde el teclado.
- **`-t`** (*tty*): Asigna un terminal virtual con colores y prompt interactivo.
- **`/bin/bash`**: La shell que se ejecutará dentro del contenedor.

> 💡 **Para salir:** Escribe `exit` y presionar Enter para regresar a la terminal de tu máquina virtual sin detener el contenedor.

---

## 8. Redes Personalizadas en Podman (`podman network`)

Por defecto, todos los contenedores se conectan a la red virtual predeterminada `podman` (típicamente en el segmento `10.88.0.0/16`). Para segmentar tráfico, aislar aplicaciones de producción o asignar rangos de red específicos, Podman permite crear redes virtuales personalizadas.

### Paso 1: Listar las redes existentes
```bash
podman network ls
```

### Paso 2: Crear una red personalizada llamada `prod`
```bash
podman network create --subnet 10.89.0.0/16 --gateway 10.89.0.1 prod
```
- **`--subnet 10.89.0.0/16`**: Define el rango de direccionamiento IP disponible para los contenedores (desde `10.89.0.2` hasta `10.89.255.254`).
- **`--gateway 10.89.0.1`**: Dirección IP de la puerta de enlace virtual asignada al host para enrutar el tráfico de esta red.
- **`prod`**: Nombre asignado a la red.

### Paso 3: Inspeccionar la configuración de la red `prod`
```bash
podman network inspect prod
```
Muestra la definición en formato JSON con la subred, el gateway y los plugins de red asignados.

### Paso 4: Desplegar un contenedor en la nueva red (`nginx03`)
```bash
podman run -dit --name nginx03 --network prod -p 8081:80 nginx
```
- **`--network prod`**: Conecta el contenedor a la red `prod` en lugar de la red por defecto.
- **`-p 8081:80`**: Publica el servicio en el puerto `8081` del host.

### Paso 5: Validar la asignación de IP
```bash
podman inspect nginx03 | grep -i IPAddress
```
* **Resultado:** La IP asignada pertenece al nuevo segmento de producción (ej. `10.89.0.2`).

---

## 9. Volúmenes Persistentes en Podman y Despliegue de MySQL

Por defecto, los contenedores son **efímeros**: si un contenedor se elimina, todos los datos creados dentro de él se pierden. Para bases de datos y aplicaciones de producción, es obligatorio usar **Volúmenes Persistentes (`podman volume`)**, que almacenan los datos directamente en el sistema de archivos del host (`/var/lib/containers/storage/volumes/`).

### 9.1 Ruta Interna de Almacenamiento de MySQL
En la imagen oficial de MySQL:
- El directorio interno donde se guardan todas las bases de datos, tablas y transacciones es **`/var/lib/mysql`**.
- El puerto de red por defecto para conexiones de clientes de MySQL es el **`3306`**.
- La imagen exige por seguridad definir una contraseña de administrador mediante la variable de entorno **`-e MYSQL_ROOT_PASSWORD=<contraseña>`**.

---

### 9.2 Paso a Paso de la Práctica de MySQL

#### Paso 1: Descargar la imagen oficial de MySQL
```bash
podman pull docker.io/library/mysql:latest
```

#### Paso 2: Crear e inspeccionar el volumen persistente `volmysql01`
```bash
# 1. Crear el volumen
podman volume create volmysql01

# 2. Listar los volúmenes existentes
podman volume ls

# 3. Inspeccionar la ruta física del volumen en el host
podman volume inspect volmysql01
```

#### Paso 3: Desplegar el contenedor de MySQL
```bash
podman run -dit \
  --name mysql01 \
  -p 3306:3306 \
  --network prod \
  --volume volmysql01:/var/lib/mysql \
  -e MYSQL_ROOT_PASSWORD=AGCaldo23 \
  docker.io/library/mysql:latest
```

#### Desglose de los Parámetros Utilizados:
- **`-dit`**: Ejecuta en segundo plano de forma interactiva y con pseudo-terminal.
- **`--name mysql01`**: Nombre único asignado al contenedor.
- **`-p 3306:3306`**: Mapea el puerto `3306` del host al puerto `3306` interno de MySQL.
- **`--network prod`**: Conecta el contenedor a la red de producción creada anteriormente.
- **`--volume volmysql01:/var/lib/mysql`**: Conecta el volumen persistente `volmysql01` del host a la carpeta interna de datos de MySQL (`/var/lib/mysql`).
- **`-e MYSQL_ROOT_PASSWORD=AGCaldo23`**: Establece la contraseña obligatoria del usuario `root` de MySQL.

#### Paso 4: Validar el funcionamiento de MySQL
```bash
# 1. Ver el estado del contenedor
podman ps -a

# 2. Ver los logs de inicialización de la base de datos
podman logs -f mysql01
# (Presionar Ctrl + C para salir de los logs)

# 3. Probar conexión interactiva al cliente MySQL dentro del contenedor
podman exec -it mysql01 mysql -u root -pAGCaldo23 -e "SHOW DATABASES;"
```

---

---

## 10. Construcción de Imágenes Personalizadas (`podman build`) y Microservicios Python

En DevOps, la mayoría de aplicaciones personalizadas no vienen preconstruidas, sino que se empaquetan a partir de un archivo **`Containerfile`** (o `Dockerfile`) mediante el comando **`podman build`**.

### 10.1 Imagen Base Gratuita y Libre: `python:3.11-slim` vs Red Hat UBI
- **Universal Base Image de Red Hat (`ubi9/python-311`)**: A pesar de estar alojada en `registry.access.redhat.com`, la imagen UBI es **100% gratuita, redistribuible y no requiere suscripción**.
- **`python:3.11-slim` (Docker Hub)**: Es la imagen comunitaria estándar oficial de la comunidad de Python en Docker Hub. Es sumamente ligera (~45 MB descargada) y completamente libre.

---

### 10.2 Estructura del `Containerfile`
```dockerfile
FROM docker.io/library/python:3.11-slim

LABEL description="Webserver en Python puro con http.server"

WORKDIR /app

# Buenas prácticas de seguridad: crear un usuario no root
RUN useradd -u 1001 -m appuser

# Copiar el código fuente con permisos para el usuario 1001
COPY --chown=1001:1001 server.py .

ENV PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
USER 1001

CMD ["python", "server.py"]
```

---

### 10.3 Ejecución del Ejercicio Paso a Paso

#### Paso 1: Crear la carpeta de trabajo
```bash
mkdir -p /root/web-python
cd /root/web-python
```

#### Paso 2: Crear `server.py`
```bash
cat << 'EOF' > server.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import datetime
import json
import os
import socket

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = json.dumps({"status": "ok"}).encode()
            ctype = "application/json"
        else:
            html = (
                "<h1>Hola desde Podman</h1>"
                f"<p>Contenedor: {socket.gethostname()}</p>"
                f"<p>Hora: {datetime.datetime.now():%Y-%m-%d %H:%M:%S}</p>"
            )
            body = html.encode()
            ctype = "text/html; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"Escuchando en 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
EOF
```

#### Paso 3: Crear el `Containerfile`
```bash
cat << 'EOF' > Containerfile
FROM docker.io/library/python:3.11-slim

LABEL description="Webserver en Python puro con http.server"

WORKDIR /app

RUN useradd -u 1001 -m appuser
COPY --chown=1001:1001 server.py .

ENV PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
USER 1001

CMD ["python", "server.py"]
EOF
```

#### Paso 4: Construir la Imagen (`podman build`)
```bash
podman build -t py-web:1.0 .
```
- **`-t py-web:1.0`**: Tag/nombre de la imagen resultante.
- **`.`**: Contexto del directorio actual.

#### Paso 5: Detener contenedores que ocupen el puerto 8080 y desplegar `web`
```bash
# Detener el nginx02 previo si estaba ocupando el puerto 8080
podman stop nginx02 2>/dev/null

# Levantar el nuevo contenedor py-web
podman run -d --name web -p 8080:8080 py-web:1.0
```

#### Paso 6: Validar y consultar logs
```bash
# Probar la página principal (devuelve HTML con hostname y hora)
curl http://localhost:8080

# Probar el endpoint de salud
curl http://localhost:8080/health

# Ver los logs en tiempo real emitidos por el servidor Python
podman logs web
```

---

## 11. Resumen Rápido de Comandos de la Clase 4 (Cheat Sheet)

| Comando / Sintaxis | Categoría | Propósito Técnico |
| :--- | :--- | :--- |
| **`sss_cache -E`** | SSSD | Invalida y vacía la caché local del demonio de identidades. |
| **`sudo -l -U <usuario>`** | Sudo | Inspecciona los privilegios de administración del usuario. |
| **`dnf install -y podman`** | Paquetes | Instala el motor de contenedores Podman. |
| **`podman images`** | Imágenes | Lista las imágenes locales disponibles en el almacén de Podman. |
| **`podman pull <imagen>`** | Imágenes | Descarga una imagen desde un registro remoto (ej. Docker Hub). |
| **`podman build -t <tag> .`** | Construcción | Compila y crea una imagen personalizada a partir de un `Containerfile`. |
| **`podman run -dit --name <nom> <img>`** | Ejecución | Crea y arranca un contenedor en segundo plano con nombre fijo. |
| **`podman run -dit -p <h>:<c> <img>`** | Puertos | Mapea el puerto del host `<h>` al puerto interno `<c>` del contenedor. |
| **`podman ps -a`** | Estado | Lista todos los contenedores creados (activos y detenidos). |
| **`podman logs <contenedor>`** | Monitoreo | Visualiza la salida estándar (`stdout`/`stderr`) del contenedor. |
| **`podman inspect <id\|nom> \| grep -i IPAddress`** | Red | Extrae la dirección IP privada asignada al contenedor. |
| **`podman exec -it <id\|nom> <comando>`** | Interacción | Ejecuta una orden o abre una shell dentro de un contenedor activo. |
| **`podman network create --subnet <s> <nom>`** | Redes | Crea una red virtual personalizada con rango de IP propio. |
| **`podman volume create <nombre>`** | Volúmenes | Crea un volumen persistente para preservar datos en disco. |
| **`podman volume inspect <nombre>`** | Volúmenes | Muestra la ruta física del volumen en el host (punto de montaje). |
| **`podman run -v <vol>:<dir_interno> ...`** | Volúmenes | Monta un volumen persistente dentro de un directorio del contenedor. |
| **`podman stop <id\|nom>`** | Control | Detiene la ejecución del contenedor de forma segura. |
| **`podman start <id\|nom>`** | Control | Reactiva un contenedor previamente detenido. |
| **`curl <host>:<puerto>`** | Pruebas | Valida la conectividad HTTP y respuesta de un servicio web. |

