# Pods en Podman: Teoría y Ejercicio Integral

Este documento recopila de forma íntegra y detallada todo el contenido del laboratorio de **Clase 5**: qué es realmente un pod, qué namespaces comparten sus contenedores, cómo gestionar redes y volúmenes, la resolución completa del **Ejercicio Integral de Laboratorio**, la automatización del arranque mediante **Quadlet con systemd**, retos adicionales y comandos esenciales.

---

## 1. ¿Qué es un Pod?

Un **pod** es un grupo de contenedores que comparten un conjunto de namespaces del kernel de Linux y se administran como una sola unidad lógica. El concepto proviene de Kubernetes y Podman lo implementa de forma nativa a nivel de host (*Pod Manager*).

### El Contenedor de Infraestructura (`infra` / `podman-pause`)
Cuando ejecutas `podman pod create`, Podman levanta automáticamente un contenedor oculto denominado **contenedor de infraestructura** (*infra container*), basado en la imagen `localhost/podman-pause` (construida a partir del binario `catatonit`).

- **Su función:** Dormir. Sostiene los namespaces compartidos del pod.
- **Ventaja clave:** Mientras el contenedor de infraestructura exista, los namespaces del pod siguen vivos aunque todos los contenedores de aplicación se detengan, fallen o se reemplacen. Por ello, puedes destruir y recrear un contenedor sin que el pod pierda su IP privada ni sus puertos publicados.

```text
┌──────────────────────────────── pod: lab-pod ────────────────────────────────┐
│                                                                              │
│   ┌───────────────┐          ┌───────────────┐          ┌────────────────┐   │
│   │     infra     │          │    lab-api    │          │     lab-db     │   │
│   │ (podman-pause)│          │               │          │                │   │
│   │ sostiene los  │          │   volumen:    │          │    volumen:    │   │
│   │  namespaces   │          │   api-datos   │          │    db-datos    │   │
│   └───────────────┘          └───────────────┘          └────────────────┘   │
│                                                                              │
│   COMPARTIDO: net · ipc · uts · cgroup                                       │
│   PROPIO:     mount (volúmenes) · pid · user                                 │
└──────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼ puertos publicados: siempre a nivel de pod
                                   Host RHEL / Rocky
```

### ¿Por qué agrupar contenedores en un Pod en vez de usarlos sueltos?
1. **Ciclo de vida conjunto:** `podman pod stop` detiene todo el conjunto y `podman pod rm -f` lo elimina completo.
2. **Comunicación por `localhost`:** Un contenedor sidecar (o la API) se comunica con la base de datos o el proxy en `127.0.0.1` sin exponer puertos a la red externa.
3. **Límites agregados de recursos:** Con `--cpus` y `--memory` definidos a nivel de pod, el cgroup padre limita al conjunto entero y no a cada pieza por separado.
4. **Puente directo hacia Kubernetes:** `podman kube generate` traduce el pod a un manifiesto YAML de Kubernetes, y `podman kube play` hace el proceso inverso.

### Casos de Uso Típicos
- Aplicación web + Proxy inverso que termina TLS (SSL).
- Aplicación principal + Agente sidecar de logs o métricas que lee un directorio.
- Base de datos + Contenedor de respaldo que se conecta localmente por `localhost`.
- Contenedor de inicialización (*init container*) que migra o prepara datos antes de que arranque la aplicación principal.

---

## 2. ¿Qué Comparten los Contenedores y Qué No?

Esta asimetría es la base técnica de los pods. La mayoría de los errores surgen al asumir que se comparte algo que en realidad es privado de cada contenedor:

| Namespace | ¿Compartido en el Pod? | Consecuencia Práctica |
| :--- | :---: | :--- |
| **`net`** | **SÍ** | Una sola IP y una sola tabla de puertos para todo el pod. Los contenedores se comunican internamente a través de `127.0.0.1`. |
| **`ipc`** | **SÍ** | Memoria compartida y semáforos POSIX visibles entre todos los contenedores del pod. |
| **`uts`** | **SÍ** | Todos los contenedores comparten el mismo nombre de host (*hostname*). |
| **`cgroup`**| **SÍ** | Los límites de CPU y memoria asignados al pod aplican al conjunto de contenedores. |
| **`pid`** | **NO** | Cada contenedor ve únicamente sus propios procesos. *(Se puede compartir explícitamente con `--share pid`)*. |
| **`mount`** | **NO** | **Cada contenedor monta sus propios volúmenes.** No se heredan automáticamente. |
| **`user`** | **NO** | Cada contenedor define su propio usuario de ejecución (`USER`) y mapeo de UID. |

> 📌 **Regla de Oro:**
> - Los **volúmenes son por contenedor** porque el namespace de montaje (`mount`) **no se comparte**.
> - Las **redes son por pod** porque el namespace de red (`net`) **sí se comparte**.

---

## 3. Redes Dentro de un Pod

### Regla Crucial:
> ⚠️ **Dos contenedores del mismo pod no pueden tener redes distintas.**
> Comparten el namespace de red (interfaces, IP, rutas y puertos). Si intentas pasar `--network` a un contenedor que se une a un pod existente, Podman responderá con:
> `cannot set network namespace when running in a pod`
> **La red y los puertos se definen una sola vez: al crear el pod.**

### Soluciones y Variantes:
1. **Un pod conectado a varias redes simultáneas:** El pod se une a `red-frontend` y `red-backend` al mismo tiempo. Ambos contenedores reciben ambas interfaces de red y pueden comunicarse tanto con el segmento público como con el privado.
2. **Publicación de Puertos:** Los puertos se publican con `--publish` al crear el pod, **nunca al crear los contenedores**. Como comparten la tabla de puertos, dos contenedores en el mismo pod no pueden escuchar en el mismo puerto (el segundo fallaría con `address already in use`).
3. **Backend de Red DNS:** En RHEL 9 / Rocky Linux se utiliza **`netavark`** junto con **`aardvark-dns`**. En redes definidas por el usuario, el nombre del pod es resoluble por DNS interno automáticamente.

---

## 4. Comandos Esenciales de Pods

```bash
# Crear un pod publicando un puerto
podman pod create --name mi-pod -p 8080:8080

# Listar pods activos
podman pod ls

# Listar contenedores mostrando a qué pod pertenecen
podman ps --pod

# Inspección y métricas
podman pod inspect mi-pod
podman pod stats mi-pod
podman pod top mi-pod

# Agregar un contenedor a un pod existente
podman run -d --pod mi-pod --name c1 imagen:tag

# Control del ciclo de vida
podman pod start mi-pod
podman pod stop mi-pod
podman pod pause mi-pod
podman pod restart mi-pod
podman pod rm -f mi-pod      # -f elimina el pod y todos sus contenedores

# Integración con Kubernetes
podman kube generate mi-pod -f mi-pod.yaml
podman kube play mi-pod.yaml
```

---

## 5. Ejercicio Integral: Pod de Laboratorio

Despliegue de un pod llamado **`lab-pod`** que contiene dos contenedores:
1. **`lab-api`**: Servicio web en Python puro con su propio volumen de bitácora (`api-datos`).
2. **`lab-db`**: Base de datos PostgreSQL con su propio volumen de datos (`db-datos`).
- El pod se conecta simultáneamente a dos redes (`red-frontend` y `red-backend`).
- Publica únicamente el puerto `8080` (la base de datos se comunica internamente por `127.0.0.1:5432` sin exponer su puerto al exterior).

```text
lab-pod/
├── Containerfile
└── api.py
```

---

### Paso 1: Código de la Aplicación (`api.py`)
Utiliza únicamente la librería estándar de Python. Registra cada visita en `/opt/app-root/src/datos/bitacora.log` y comprueba la conexión a PostgreSQL a través de `127.0.0.1:5432`:

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import datetime
import json
import os
import socket

BITACORA = "/opt/app-root/src/datos/bitacora.log"

def registrar(ruta):
    linea = f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {ruta}\n"
    os.makedirs(os.path.dirname(BITACORA), exist_ok=True)
    with open(BITACORA, "a") as f:
        f.write(linea)

def probar_db():
    """La base vive en otro contenedor del mismo pod: se alcanza por localhost."""
    try:
        with socket.create_connection(("127.0.0.1", 5432), timeout=2):
            return "alcanzable en 127.0.0.1:5432"
    except OSError as e:
        return f"no alcanzable ({e.__class__.__name__})"

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        registrar(self.path)
        if self.path == "/health":
            cuerpo = json.dumps({"status": "ok"}).encode()
            tipo = "application/json"
        elif self.path == "/bitacora":
            try:
                with open(BITACORA) as f:
                    lineas = f.readlines()[-20:]
            except FileNotFoundError:
                lineas = []
            cuerpo = "".join(lineas).encode()
            tipo = "text/plain; charset=utf-8"
        else:
            cuerpo = (
                f"<h1>Pod de laboratorio</h1>"
                f"<p>Hostname del pod: {socket.gethostname()}</p>"
                f"<p>Base de datos: {probar_db()}</p>"
                f"<p><a href='/bitacora'>Ver bitacora</a></p>"
            ).encode()
            tipo = "text/html; charset=utf-8"

        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8080))
    print(f"API escuchando en 0.0.0.0:{puerto}", flush=True)
    HTTPServer(("0.0.0.0", puerto), Handler).serve_forever()
```

---

### Paso 2: Archivo de Construcción (`Containerfile`)
```dockerfile
FROM registry.access.redhat.com/ubi9/python-311

LABEL description="API de bitacora para el pod de laboratorio"

WORKDIR /opt/app-root/src

COPY --chown=1001:0 api.py .

# El volumen se montará aquí: el directorio debe existir y tener permisos de escritura
RUN mkdir -p /opt/app-root/src/datos && chown 1001:0 /opt/app-root/src/datos

ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
USER 1001

CMD ["python", "api.py"]
```

---

### Paso 3: Construcción de la Imagen
```bash
cd /root/lab-pod
podman build -t lab-api:1.0 .
podman images | grep lab-api
```

---

### Paso 4: Creación de las Dos Redes y los Dos Volúmenes
```bash
# Redes con DNS interno (aardvark-dns)
podman network create red-frontend
podman network create --subnet 10.89.20.0/24 --gateway 10.89.20.1 red-backend
podman network ls

# Volúmenes independientes por contenedor
podman volume create api-datos
podman volume create db-datos
podman volume ls
```

---

### Paso 5: Creación del Pod Unido a Ambas Redes
```bash
podman pod create \
  --name lab-pod \
  --network red-frontend,red-backend \
  --publish 8080:8080 \
  --hostname laboratorio

# Inspeccionar el contenedor de infraestructura (infra)
podman pod inspect lab-pod --format '{{.Name}} -> {{.InfraContainerID}}'
```

---

### Paso 6: Agregar los Contenedores al Pod
```bash
# 1. Contenedor de Base de Datos PostgreSQL
podman run -d --pod lab-pod --name lab-db \
  -e POSTGRES_PASSWORD='Admin2026!' \
  -e POSTGRES_DB=laboratorio \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v db-datos:/var/lib/postgresql/data \
  docker.io/library/postgres:16

# 2. Contenedor de la API en Python
podman run -d --pod lab-pod --name lab-api \
  -v api-datos:/opt/app-root/src/datos \
  localhost/lab-api:1.0

# 3. Comprobar que ambos contenedores y el infra están en ejecución
podman ps --pod
```

> ⚠️ **Comportamiento esperado al intentar pasar `--network` a un contenedor del pod:**
> Si ejecutas:
> `podman run -d --pod lab-pod --network red-backend ...`
> Fallará con error porque el contenedor **hereda obligatoriamente el namespace de red del pod**.

---

### Paso 7: Comprobaciones y Verificaciones de Laboratorio

```bash
# A) Ambos contenedores ven exactamente las mismas interfaces y las mismas IPs
podman exec lab-api ip -br addr
podman exec lab-db ip -br addr

# B) Comparten el mismo hostname (namespace UTS)
podman exec lab-api hostname
podman exec lab-db hostname

# C) Aislamiento de volúmenes: cada uno ve únicamente su almacenamiento
podman exec lab-api ls -l /opt/app-root/src/datos
podman exec lab-db ls /opt/app-root/src/datos # Error esperado: No such file or directory

# D) La API alcanza la base de datos por localhost:5432 sin exponer el puerto 5432
curl -s http://localhost:8080 | grep -i "Base de datos"
# Salida esperada: <p>Base de datos: alcanzable en 127.0.0.1:5432</p>

# E) Comprobar escritura persistente en la bitácora
curl -s http://localhost:8080/health > /dev/null
curl -s http://localhost:8080/bitacora

# F) Los procesos están aislados (namespace PID no compartido)
podman exec lab-api ps -ef

# G) Métricas y procesos agregados del pod
podman pod top lab-pod
podman pod stats --no-stream lab-pod
```

---

### Paso 8: Probar la Persistencia del Almacenamiento
Si se destruye el contenedor de la API y se vuelve a crear, la bitácora de visitas anterior permanece intacta:

```bash
# 1. Eliminar el contenedor de la API
podman rm -f lab-api

# 2. Recrear el contenedor con el mismo volumen
podman run -d --pod lab-pod --name lab-api \
  -v api-datos:/opt/app-root/src/datos \
  localhost/lab-api:1.0

# 3. Verificar que las líneas previas siguen existiendo
curl -s http://localhost:8080/bitacora
```

---

### Paso 9: Exportar a Manifiesto de Kubernetes
```bash
podman kube generate lab-pod -f lab-pod.yaml
head -n 40 lab-pod.yaml
```

---

## 6. Arranque Automático con el Sistema Operativo (Quadlet y systemd)

**Quadlet** es el generador oficial en RHEL 9 / Rocky Linux que traduce archivos declarativos (`.container`, `.volume`, `.network`, `.pod`) a servicios gestionados por **systemd** al ejecutar `daemon-reload`. Sustituye al método obsoleto `podman generate systemd`.

### Ubicación de los Archivos Quadlet
- **Modo Rootless (Recomendado):** `~/.config/containers/systemd/` (se gestiona con `systemctl --user`).
- **Modo Root:** `/etc/containers/systemd/` (se gestiona con `sudo systemctl`).

### 6.1 Preparación del Entorno
```bash
# Limpiar recursos manuales previos
podman pod rm -f lab-pod 2>/dev/null
podman volume rm api-datos db-datos 2>/dev/null
podman network rm red-frontend red-backend 2>/dev/null

# Crear el directorio de Quadlet
mkdir -p ~/.config/containers/systemd
cd ~/.config/containers/systemd
```

---

### 6.2 Archivos de Red: `red-frontend.network` y `red-backend.network`

```ini
# red-frontend.network
[Unit]
Description=Red frontend del laboratorio

[Network]
NetworkName=red-frontend
```

```ini
# red-backend.network
[Unit]
Description=Red backend del laboratorio

[Network]
NetworkName=red-backend
Subnet=10.89.20.0/24
Gateway=10.89.20.1
```

---

### 6.3 Archivos de Volúmenes: `api-datos.volume` y `db-datos.volume`

```ini
# api-datos.volume
[Unit]
Description=Volumen de bitacora de la API

[Volume]
VolumeName=api-datos
```

```ini
# db-datos.volume
[Unit]
Description=Volumen de datos de PostgreSQL

[Volume]
VolumeName=db-datos
```

---

### 6.4 Archivo del Pod: `laboratorio.pod`

```ini
# laboratorio.pod
[Unit]
Description=Pod de laboratorio (API + PostgreSQL)

[Pod]
PodName=lab-pod
Network=red-frontend.network
Network=red-backend.network
PublishPort=8080:8080
PodmanArgs=--hostname laboratorio

[Install]
WantedBy=default.target
```

---

### 6.5 Archivos de Contenedores: `lab-db.container` y `lab-api.container`

```ini
# lab-db.container
[Unit]
Description=PostgreSQL del laboratorio

[Container]
ContainerName=lab-db
Image=docker.io/library/postgres:16
Pod=laboratorio.pod
Volume=db-datos.volume:/var/lib/postgresql/data
Environment=POSTGRES_DB=laboratorio
Environment=PGDATA=/var/lib/postgresql/data/pgdata
Secret=pgpass,type=env,target=POSTGRES_PASSWORD

[Service]
Restart=always
TimeoutStartSec=300

[Install]
WantedBy=default.target
```

```ini
# lab-api.container
[Unit]
Description=API de bitacora del laboratorio
Requires=lab-db.service
After=lab-db.service

[Container]
ContainerName=lab-api
Image=localhost/lab-api:1.0
Pod=laboratorio.pod
Volume=api-datos.volume:/opt/app-root/src/datos
Environment=PORT=8080

[Service]
Restart=always
TimeoutStartSec=300

[Install]
WantedBy=default.target
```

---

### 6.6 Creación del Secreto de Contraseña
Para evitar escribir contraseñas en texto plano en los archivos de servicio:
```bash
printf 'Admin2026!' | podman secret create pgpass -
podman secret ls
```

---

### 6.7 Habilitación y Puesta en Marcha con systemd
```bash
# Permitir que los servicios del usuario corran sin sesión gráfica iniciada
loginctl enable-linger $USER

# Generar los servicios de systemd a partir de los archivos Quadlet
systemctl --user daemon-reload

# Iniciar el servicio (el pod y PostgreSQL arrancan automáticamente como dependencia)
systemctl --user start lab-api.service

# Comprobar el estado de los servicios
systemctl --user status laboratorio-pod.service lab-db.service lab-api.service
podman ps --pod

# Prueba funcional
curl -s http://localhost:8080
```

> ⚠️ **Regla de Quadlet:**
> **No uses `systemctl enable` con Quadlet.** Las unidades son generadas dinámicamente en memoria, no existen físicamente como archivos `.service` en disco. La sección `[Install] WantedBy=default.target` es la que garantiza el arranque automático con el sistema.

---

### 6.8 Verificación del Reinicio Real
```bash
sudo reboot

# Tras reiniciar la máquina virtual por SSH:
podman ps --pod
curl -s http://localhost:8080/bitacora
journalctl --user -u lab-api.service --since "10 min ago"

# Herramienta de depuración si algún archivo Quadlet falla:
/usr/libexec/podman/quadlet -user -dryrun
```

---

## 7. Retos Adicionales

1. **Aislamiento real por red:** Separar en dos pods independientes (`pod-front` en `red-frontend` y `pod-data` en `red-backend`) para demostrar aislamiento y luego unirlos con `podman network connect`.
2. **Sidecar con volumen compartido:** Agregar un tercer contenedor que monte `api-datos` en modo lectura (`:ro`) y ejecute `tail -f` continuo sobre la bitácora.
3. **Del Pod a Kubernetes:** Analizar cómo se mapean los volúmenes y las redes en el archivo `lab-pod.yaml` generado.

---

## 8. Comandos de Limpieza Final

```bash
# Detener y limpiar servicios Quadlet
systemctl --user stop lab-api.service lab-db.service laboratorio-pod.service 2>/dev/null
rm -f ~/.config/containers/systemd/{laboratorio.pod,lab-api.container,lab-db.container}
rm -f ~/.config/containers/systemd/{api-datos.volume,db-datos.volume}
rm -f ~/.config/containers/systemd/{red-frontend.network,red-backend.network}
systemctl --user daemon-reload

# Eliminar recursos residuales en Podman
podman pod rm -f lab-pod 2>/dev/null
podman volume rm api-datos db-datos 2>/dev/null
podman network rm red-frontend red-backend 2>/dev/null
podman secret rm pgpass 2>/dev/null
podman image prune -f
```
