# Manual Clase 5 — Parte 2: Práctica de Laboratorio, Errores y Soluciones

Este documento recopila la **ejecución paso a paso del laboratorio práctico de Pods en Podman**, documentando cada uno de los comandos reales ejecutados en la máquina virtual Rocky Linux, las salidas obtenidas, todos los **errores técnicos encontrados**, su causa raíz (post-mortem) y la **solución definitiva aplicada** en cada caso.

---

## 1. Resumen de la Arquitectura Desplegada

El objetivo fue construir e implementar un **Pod multicontenedor** (`lab-pod`) que simula un entorno productivo de microservicios:

```text
                               [ Host: Rocky Linux ]
                                         │
                         ┌───────────────┴───────────────┐
                         ▼ (Port Forwarding: 8080:8080)   ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │ POD: lab-pod (Hostname: laboratorio)                                   │
    │ Redes: red-frontend, red-backend                                       │
    │                                                                        │
    │  ┌─────────────────────────┐           ┌────────────────────────────┐  │
    │  │ Contenedor: lab-api     │           │ Contenedor: lab-db         │  │
    │  │ Imagen: lab-api:1.0     │           │ Imagen: postgres:16        │  │
    │  │ Puerto: 8080            │  Loopback │ Puerto: 5432 (interno)     │  │
    │  │ Usuario: 1001 (non-root)│◄─────────►│ BD: laboratorio            │  │
    │  │                         │ 127.0.0.1 │                            │  │
    │  └───────────┬─────────────┘           └─────────────┬──────────────┘  │
    │              │                                       │                 │
    └──────────────┼───────────────────────────────────────┼─────────────────┘
                   ▼                                       ▼
          [ Volumen: api-datos ]                  [ Volumen: db-datos ]
         /opt/app-root/src/datos                 /var/lib/postgresql/data
         (Almacena bitacora.log)                  (Almacena tablas y WALs)
```

---

## 2. Bitácora de Ejecución Paso a Paso

### Fase 1: Creación de la Aplicación API Python y Containerfile

Ubicación de trabajo en la máquina virtual: `/root/lab-pod`.

#### 1. Archivo `api.py`
Se creó el servicio HTTP ligero en Python que:
- Escribe una marca de tiempo y ruta visitada en `/opt/app-root/src/datos/bitacora.log`.
- Verifica la disponibilidad de la base de datos PostgreSQL conectándose a través del adaptador de loopback (`127.0.0.1:5432`).
- Expone los endpoints `/`, `/health` y `/bitacora`.

```python
import os
import json
import socket
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

BITACORA = "/opt/app-root/src/datos/bitacora.log"

def registrar(ruta):
    os.makedirs(os.path.dirname(BITACORA), exist_ok=True)
    with open(BITACORA, "a") as f:
        linea = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {ruta}\n"
        f.write(linea)

def probar_db():
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
                f"<h1>Pod de laboratorio</h1>\n"
                f"<p>Hostname del pod: {socket.gethostname()}</p>\n"
                f"<p>Base de datos: {probar_db()}</p>\n"
                f"<p><a href='/bitacora'>Ver bitacora</a></p>\n"
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

#### 2. Archivo `Containerfile`
Se construyó usando la imagen ligera comunitaria de Python en caché local, configurando usuario sin privilegios root (`1001`):

```dockerfile
FROM docker.io/library/python:3.11-slim

LABEL description="API de bitacora para el pod de laboratorio"

WORKDIR /opt/app-root/src

COPY --chown=1001:0 api.py .

RUN mkdir -p /opt/app-root/src/datos && chown -R 1001:0 /opt/app-root/src/datos

ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
USER 1001

CMD ["python", "api.py"]
```

#### 3. Construcción de la imagen:
```bash
podman build -t lab-api:1.0 .
podman images | grep lab-api
```

---

### Fase 2: Creación de Recursos de Red y Almacenamiento

#### 1. Volúmenes de datos:
```bash
podman volume create api-datos
podman volume create db-datos
podman volume ls
```
Salida confirmada:
```text
DRIVER      VOLUME NAME
local       volmysql01
local       pgdata
local       api-datos
local       db-datos
```

#### 2. Redes del clúster:
```bash
podman network create red-frontend
podman network create red-backend
podman network ls
```

---

### Fase 3: Creación del Pod y Lanzamiento de Contenedores

#### 1. Creación del Pod con puertos y redes:
```bash
# Limpiar puerto 8080 por si estaba en uso por prácticas previas
podman rm -f web 2>/dev/null

# Crear el pod multicontenedor
podman pod create \
  --name lab-pod \
  --network red-frontend,red-backend \
  --publish 8080:8080 \
  --hostname laboratorio
```

#### 2. Iniciar la base de datos PostgreSQL dentro del pod:
```bash
podman run -d --pod lab-pod --name lab-db \
  -e POSTGRES_PASSWORD='Admin2026!' \
  -e POSTGRES_DB=laboratorio \
  -e PGDATA=/var/lib/postgresql/data/pgdata \
  -v db-datos:/var/lib/postgresql/data \
  docker.io/library/postgres:16
```

#### 3. Iniciar la API dentro del pod:
```bash
podman run -d --pod lab-pod --name lab-api \
  -v api-datos:/opt/app-root/src/datos \
  localhost/lab-api:1.0
```

#### 4. Comprobación del estado de los contenedores en el pod:
```bash
podman ps -a --pod
```
Salida obtenida:
```text
CONTAINER ID  IMAGE                           COMMAND               CREATED         STATUS         PORTS                              NAMES               POD ID        PODNAME
c1ab1af7841c                                                        30 seconds ago  Up 10 seconds  0.0.0.0:8080->8080/tcp             ba89829db423-infra  ba89829db423  lab-pod
2ff4c24361f6  docker.io/library/postgres:16   postgres              10 seconds ago  Up 10 seconds  0.0.0.0:8080->8080/tcp, 5432/tcp   lab-db              ba89829db423  lab-pod
785ac620c072  localhost/lab-api:1.0           python api.py         4 seconds ago   Up 5 seconds   0.0.0.0:8080->8080/tcp             lab-api             ba89829db423  lab-pod
```

---

### Fase 4: Pruebas y Verificaciones Técnicas

#### 1. Verificación del UTS Namespace (Hostname compartido):
```bash
podman exec lab-api hostname
podman exec lab-db hostname
```
**Resultado:** Ambos contenedores responden `laboratorio`.

#### 2. Verificación de Aislamiento de Volúmenes:
```bash
podman exec lab-db ls /opt/app-root/src/datos
```
**Resultado:**
```text
ls: cannot access '/opt/app-root/src/datos': No such file or directory
```
*Demostración: Los volúmenes son aislados por contenedor; `lab-db` no tiene acceso al almacenamiento de `lab-api`.*

#### 3. Verificación de Endpoints y Bitácora Persistente:
```bash
curl -s http://localhost:8080/health
# Respuesta: {"status": "ok"}

curl -s http://localhost:8080/bitacora
# Respuesta:
# 2026-09-25 07:07:54 /
# 2026-09-25 07:08:05 /health
# 2026-09-25 07:08:57 /bitacora
```

#### 4. Generación del Manifiesto Kubernetes:
```bash
podman kube generate lab-pod -f lab-pod.yaml
cat lab-pod.yaml
```
*Se generó exitosamente el archivo declarativo YAML con la especificación completa del Pod, ambos contenedores, puertos y los PersistentVolumeClaims correspondientes.*

---

### Fase 5: Arranque Automático con systemd y Comprobación tras Reinicio

Para garantizar alta disponibilidad y persistencia ante reinicios del sistema operativo de la máquina virtual:

#### 1. Generación de unidades de servicio systemd con Podman:
```bash
podman generate systemd --files --name lab-pod
```
Archivos generados:
- `/root/pod-lab-pod.service`
- `/root/container-lab-pod-lab-api.service`
- `/root/container-lab-pod-lab-db.service`

#### 2. Instalación en el directorio de servicios de systemd del usuario:
```bash
mkdir -p $HOME/.config/systemd/user/
mv *.service $HOME/.config/systemd/user/
```

#### 3. Configuración de persistencia (Linger) y recarga de daemons:
```bash
loginctl enable-linger root
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user daemon-reload
```

#### 4. Habilitación del servicio del Pod:
```bash
systemctl --user enable pod-lab-pod.service
systemctl --user is-enabled pod-lab-pod.service # Devuelve: enabled
```

#### 5. Prueba de reinicio y verificación post-boot:
```bash
reboot
```

Tras reiniciar y volver a conectar por SSH:
```bash
podman ps -a --pod
```
**Resultado obtenido:**
```text
CONTAINER ID  IMAGE                           COMMAND         STATUS      PORTS                              NAMES               POD ID        PODNAME
93d29ed7da8e                                                  Up 7 hours  0.0.0.0:8080->8080/tcp             7ed610636a45-infra  7ed610636a45  lab-pod
1344597df9cc  docker.io/library/postgres:16   postgres        Up 7 hours  0.0.0.0:8080->8080/tcp, 5432/tcp   lab-pod-lab-db      7ed610636a45  lab-pod
d9c1bb6bbb6c  localhost/lab-api:1.0           python api.py   Up 7 hours  0.0.0.0:8080->8080/tcp             lab-pod-lab-api     7ed610636a45  lab-pod
```
*Demostración: systemd detectó el arranque del sistema, levantó el contenedor `infra` y posteriormente inició en orden de dependencias `lab-pod-lab-db` y `lab-pod-lab-api` sin intervención humana.*

---

## 3. Catálogo de Errores Presentados y Cómo se Resolvieron

A continuación se detalla cada fallo ocurrido durante la sesión, su explicación técnica y la solución implementada:

---

### Error 1: Fallo al descargar imágenes externas (`i/o timeout` / DNS)

#### Mensaje del error:
```text
WARN[0030] Failed, retrying in 1s ... (1/3). Error: initializing source docker://ubuntu:latest:
pinging container registry registry-1.docker.io: Get "https://registry-1.docker.io/v2/": dial tcp: lookup registry-1.docker.io: i/o timeout
Error: unable to copy from source docker://ubuntu:latest: initializing source docker://ubuntu:latest: pinging container registry registry-1.docker.io
```

#### Causa técnica:
La máquina virtual presentó intermitencias de resolución de nombres DNS hacia servidores de internet externos o timeout al consultar Docker Hub / Red Hat Registry.

#### Solución aplicada:
1. Se inspeccionaron las imágenes ya descargadas localmente en Podman:
   ```bash
   podman images
   ```
   Se detectó que ya existían imágenes funcionales en la caché local:
   - `docker.io/library/python:3.11-slim`
   - `docker.io/library/postgres:16`
   - `docker.io/library/ubuntu:24.04`
2. En lugar de forzar descargas de registros externos o de UBI de Red Hat (que podían requerir suscripción o tardar por red), se ajustó el `Containerfile` para construir directamente a partir de la imagen local disponible `docker.io/library/python:3.11-slim`.

---

### Error 2: Intentar crear el contenedor antes de crear el Pod

#### Comando ejecutado:
```bash
podman run -d --pod lab-pod --name lab-db \
  -e POSTGRES_PASSWORD='Admin2026!' \
  ...
```

#### Mensaje del error:
```text
Error: no pod with name or ID lab-pod found: no such pod
```

#### Causa técnica:
En Podman, un pod no es una entidad virtual abstracta generada automáticamente al vuelo; es un objeto que debe ser creado primero en el motor de contenedores (`podman pod create`) para que asigne el contenedor de infraestructura (`infra`), los namespaces y los cgroups correspondientes.

#### Solución aplicada:
Crear primero el pod indicando sus redes y puertos mapeados al host:
```bash
podman pod create \
  --name lab-pod \
  --network red-frontend,red-backend \
  --publish 8080:8080 \
  --hostname laboratorio
```
Posteriormente, los comandos `podman run --pod lab-pod ...` se ejecutaron sin problemas.

---

### Error 3: Intentar asociar el Pod a redes no existentes

#### Mensaje del error:
```text
Error: unable to find network with name or ID red-backend: network not found
```

#### Causa técnica:
Al ejecutar `podman pod create --network red-frontend,red-backend`, la red `red-backend` aún no había sido registrada en el CNI/Netavark de Podman.

#### Solución aplicada:
Crear previamente las redes necesarias con `podman network create`.

---

### Error 4: Conflicto de Subred (`subnet already used on the host`)

#### Comando ejecutado:
```bash
podman network create --subnet 10.89.20.0/24 --gateway 10.89.20.1 red-backend
```

#### Mensaje del error:
```text
Error: subnet 10.89.20.0/24 is already used on the host or by another config
```

#### Causa técnica:
En la práctica de la Clase 4 anterior, se había creado una red llamada `prod` que ya tenía reservada la subred `10.89.20.0/24`. Podman valida a nivel de kernel/enrutamiento que no existan subredes superpuestas para evitar colisiones de rutas IP.

#### Solución aplicada:
Permitir que el gestor IPAM (IP Address Management) de Podman elija automáticamente una subred libre disponible ejecutando la creación sin forzar el parámetro `--subnet`:
```bash
podman network create red-backend
```
Podman asignó de forma automática una subred no utilizada sin ningún conflicto.

---

### Error 5: Comando `ip` no encontrado en el contenedor de base de datos

#### Comando ejecutado:
```bash
podman exec lab-db ip -br addr
```

#### Mensaje del error:
```text
Error: crun: executable file `ip` not found in $PATH: No such file or directory: OCI runtime attempted to invoke a command that was not found
```

#### Causa técnica:
Las imágenes modernas optimizadas para producción (como `postgres:16` basada en Debian Slim) eliminan paquetes innecesarios para reducir el peso y mejorar la seguridad, por lo que el paquete `iproute2` no viene preinstalado.

#### Solución aplicada:
Utilizar utilidades disponibles en la imagen para comprobar el namespace y la identidad de red:
```bash
podman exec lab-api hostname -I
podman exec lab-db hostname -I
podman exec lab-api hostname
podman exec lab-db hostname
```
Ambos devolvieron exactamente las mismas direcciones IP y el mismo nombre de host (`laboratorio`), confirmando que comparten el UTS y Network Namespace.

---

### Error 6: Intento de pasar `--network` a un contenedor dentro de un Pod

#### Comando ejecutado en pruebas preliminares:
```bash
podman run -dit --name myhttp --pod mypod --network prod -p 8090:80 nginx
```

#### Mensaje del error:
```text
Error: cannot set network when creating a container in a pod
```

#### Causa técnica:
Regla fundamental de arquitectura en Pods: **Los contenedores dentro de un pod comparten forzosamente el Network Namespace del contenedor de infraestructura (`infra`)**. Por lo tanto, la red y la publicación de puertos (`-p`) se definen exclusivamente a nivel de Pod, nunca a nivel de contenedor individual.

#### Solución aplicada:
Definir los puertos y redes en `podman pod create`, y al invocar `podman run` simplemente omitir `--network` y `-p`.

---

## 4. Estado Final del Laboratorio

| Componente | Nombre | Configuración / Estado |
| :--- | :--- | :--- |
| **Pod** | `lab-pod` | `Up` (Infra: `ba89829db423-infra`) |
| **Redes del Pod** | `red-frontend`, `red-backend` | Bridge activo con resolución interna |
| **Contenedor 1** | `lab-db` | PostgreSQL 16, persistencia en `db-datos` |
| **Contenedor 2** | `lab-api` | Python 3.11 Microservicio, persistencia en `api-datos` |
| **Puertos expuestos** | `8080:8080` | Mapeado al host Rocky Linux |
| **Hostname** | `laboratorio` | Compartido por ambos contenedores |
| **Manifiesto K8s** | `lab-pod.yaml` | Exportado y listo para migración a clúster Kubernetes |
