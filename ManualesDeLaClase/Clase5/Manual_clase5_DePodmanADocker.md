# Manual Clase 5 — De Podman a Docker Hub: Empaquetado OCI, Versionado, Publicación y Automatización

> **Usuario de Docker Hub:** `agcaaron`  
> **Repositorio de Trabajo:** `docker.io/agcaaron/bitacora-api`  
> **Entorno:** Rocky Linux 9 / Red Hat Enterprise Linux (Podman 5.x)  
> **Basado en:** Manual oficial de la Clase 5 — *De Podman a Docker Hub*

---

## Índice General

1. [Teoría: Anatomía del Nombre de una Imagen OCI](#1-teoría-anatomía-del-nombre-de-una-imagen-oci)
2. [Generación de Cuenta y Token de Acceso Personal (PAT)](#2-generación-de-cuenta-y-token-de-acceso-personal-pat)
3. [Desarrollo de la Aplicación: `bitacora-api`](#3-desarrollo-de-la-aplicación-bitacora-api)
4. [Construcción de la Imagen con Metadatos OCI (`--build-arg`)](#4-construcción-de-la-imagen-con-metadatos-oci---build-arg)
5. [Estrategia de Etiquetado: Versionado Semántico en Cascada](#5-estrategia-de-etiquetado-versionado-semántico-en-cascada)
6. [Publicación de Imágenes en Docker Hub (`podman push`)](#6-publicación-de-imágenes-en-docker-hub-podman-push)
7. [Verificación de la Publicación y Pruebas Remotas](#7-verificación-de-la-publicación-y-pruebas-remotas)
8. [Imágenes Multiarquitectura (Manifest Lists) y Firma con Cosign](#8-imágenes-multiarquitectura-manifest-lists-y-firma-con-cosign)
9. [Publicación Automatizada con CI/CD (GitHub Actions)](#9-publicación-automatizada-con-cicd-github-actions)
10. [Retos y Buenas Prácticas de Ingeniería](#10-retos-y-buenas-prácticas-de-ingeniería)
11. [Guía de Ejecución Paso a Paso en la Máquina Virtual](#11-guía-de-ejecución-paso-a-paso-en-la-máquina-virtual)

---

## 1. Teoría: Anatomía del Nombre de una Imagen OCI

Antes de publicar imágenes de contenedores, es indispensable comprender que en estándares OCI (Open Container Initiative), el nombre de una imagen no es una simple etiqueta arbitraria; es un **Localizador Uniforme de Recursos (URL)** completo estructurado en cuatro partes:

```text
docker.io  /  agcaaron   /  bitacora-api  :  1.0.0
─────────     ────────   ────────────     ─────
Registro      Namespace   Repositorio      Tag
```

| Componente | Función Técnica | Ejemplo |
| :--- | :--- | :--- |
| **Registro** | Servidor FQDN donde reside el registry OCI. | `docker.io`, `quay.io`, `registry.redhat.io` |
| **Namespace** | Usuario personal o cuenta de organización dentro del registro. | `agcaaron` |
| **Repositorio** | Nombre del proyecto o artefacto de software. | `bitacora-api` |
| **Tag** | Etiqueta mutable que identifica una versión específica. | `1.0.0`, `1.0`, `latest` |

### Diferencia Clave: Podman vs Docker

- **Docker CLI:** Si escribes `docker pull nginx`, asume ciegamente `docker.io/library/nginx:latest`.
- **Podman CLI:** Consulta `/etc/containers/registries.conf`. Si un nombre es corto o ambiguo, Podman bloquea o pregunta explícitamente al usuario qué registro desea utilizar. Esta es una **característica de seguridad deliberada** para prevenir ataques de sustitución de dependencias y *typosquatting*.

### Tag vs Digest (Inmutabilidad)

- **Tag (`1.0.0`):** Es un puntero móvil. Puede ser reescrito deliberada o accidentalmente en el servidor.
- **Digest (`sha256:...`):** Es la suma de comprobación criptográfica del manifiesto de la imagen. **Es 100% inmutable**. En entornos de producción y clústeres de Kubernetes de alta seguridad, se despliega siempre por digest, reservando los tags para legibilidad humana.

### ¿Qué viaja realmente durante un `podman push`?

Una imagen de contenedor es la suma de un archivo de manifiesto (JSON) y una colección de capas tar comprimidas (bloques de sistema de archivos). Al hacer `push`, el cliente negocia con el registro: solo transfiere las capas que el registro **no posee previamente**. Si solo modificaste tu código fuente (`app.py`), únicamente subirá una capa de pocos kilobytes en segundos.

| Característica | Docker | Podman |
| :--- | :--- | :--- |
| **Daemon central** | Requiere `dockerd` corriendo como root | Sin daemon: arquitectura fork/exec directo |
| **Almacenamiento de credenciales** | `~/.docker/config.json` | `${XDG_RUNTIME_DIR}/containers/auth.json` |
| **Manejo de nombres cortos** | Asume siempre Docker Hub | Consulta políticas en `registries.conf` |
| **Estándar de publicación** | `docker push` | `podman push` (compatible con API OCI v2) |

---

## 2. Generación de Cuenta y Token de Acceso Personal (PAT)

> ⚠️ **Regla de Oro de Seguridad:** Nunca utilices tu contraseña principal de Docker Hub en la consola de comandos. Genera un **Personal Access Token (PAT)**; si una máquina o servidor se ve comprometido, puedes revocar el token de inmediato sin alterar tus credenciales maestras.

### 2.1 Generar el Token en Docker Hub
1. Ingresa en tu navegador a [https://hub.docker.com](https://hub.docker.com) e inicia sesión con tu cuenta: **`agcaaron`**.
2. Dirígete a la esquina superior derecha: **Menú de usuario** ➔ **Account settings** ➔ **Personal access tokens**.
3. Haz clic en **Generate new token**:
   - **Description:** `podman-rhel-laboratorio`
   - **Access permissions:** `Read & Write`
4. Haz clic en **Generate** y **copia el token inmediatamente** (no volverá a mostrarse en pantalla).

### 2.2 Autenticación Segura desde Podman

En la terminal de la máquina virtual:

```bash
# 1. Almacenar el token temporalmente sin dejar rastros en el historial de bash
read -rsp "Token de Docker Hub: " DH_TOKEN && echo

# 2. Iniciar sesión pasando el token por STDIN (no queda visible en ps ni en logs)
echo "$DH_TOKEN" | podman login docker.io --username agcaaron --password-stdin

# 3. Comprobar que la sesión es válida
podman login --get-login docker.io

# 4. Eliminar la variable de memoria por seguridad
unset DH_TOKEN
```

### Ubicación y Persistencia de Credenciales
- En modo rootless, las credenciales residen en `${XDG_RUNTIME_DIR}/containers/auth.json`.
- Como `/run/user/$UID` se limpia al cerrar la sesión, habilita persistencia con:
  ```bash
  loginctl enable-linger root
  ```
- O almacena las credenciales en una ruta fija:
  ```bash
  podman login --authfile ~/.config/containers/auth.json docker.io ...
  ```

---

## 3. Desarrollo de la Aplicación: `bitacora-api`

Construiremos un microservicio web en **Python puro**, sin dependencias externas como Flask o FastAPI, que reporta su propia versión, hash de commit, fecha de compilación, host y arquitectura de procesador.

### 3.1 Estructura del Proyecto
```text
/root/bitacora-api/
├── Containerfile
├── app.py
└── .dockerignore
```

### 3.2 Código Fuente: `app.py`

```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import platform
import socket

# Variables inyectadas en tiempo de build o ejecución
VERSION = os.environ.get("APP_VERSION", "desconocida")
COMMIT = os.environ.get("APP_COMMIT", "local")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            datos = {"status": "ok"}
        else:
            datos = {
                "servicio": "bitacora-api",
                "version": VERSION,
                "commit": COMMIT,
                "host": socket.gethostname(),
                "arquitectura": platform.machine(),
                "python": platform.python_version(),
            }

        cuerpo = json.dumps(datos, indent=2, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8080))
    print(f"bitacora-api {VERSION} escuchando en 0.0.0.0:{puerto}", flush=True)
    HTTPServer(("0.0.0.0", puerto), Handler).serve_forever()
```

### 3.3 Archivo de Construcción: `Containerfile`

Implementa directivas `ARG` para recibir metadatos dinámicos, define etiquetas OCI estándar, asegura que la aplicación corra con usuario sin privilegios root (`USER 1001`) e incluye una sonda de salud (`HEALTHCHECK`):

```dockerfile
# Se puede usar python:3.11-slim (local libre) o registry.access.redhat.com/ubi9/python-311
FROM docker.io/library/python:3.11-slim

# Valores que se inyectan al construir
ARG APP_VERSION=0.0.0
ARG APP_COMMIT=local
ARG BUILD_DATE

# Etiquetas OCI estandar: las leen Docker Hub, Skopeo y escaneres de seguridad
LABEL org.opencontainers.image.title="bitacora-api" \
      org.opencontainers.image.description="API de bitacora en Python puro" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${APP_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="agcaaron" \
      org.opencontainers.image.source="https://github.com/AAGCAaron/DevOps_FI_UNAM" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /opt/app-root/src

COPY --chown=1001:0 app.py .

ENV APP_VERSION=${APP_VERSION} \
    APP_COMMIT=${APP_COMMIT} \
    PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
USER 1001

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"

CMD ["python", "app.py"]
```

### 3.4 Filtro de Exclusiones: `.dockerignore`

Evita la fuga accidental de secretos, llaves o archivos pesados al contexto de compilación:

```text
.git
.github
*.md
__pycache__/
*.pyc
.env
*.log
```

---

## 4. Construcción de la Imagen con Metadatos OCI (`--build-arg`)

Los valores dinámicos se inyectan en tiempo de construcción. La fecha se genera en formato estandarizado **RFC 3339**:

```bash
cd /root/bitacora-api

# Definir variables dinámicas
VERSION=1.0.0
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo manual)
FECHA=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

# Construcción de la imagen
podman build \
  --build-arg APP_VERSION="$VERSION" \
  --build-arg APP_COMMIT="$COMMIT" \
  --build-arg BUILD_DATE="$FECHA" \
  -t bitacora-api:"$VERSION" .
```

### Prueba Local Obligatoria (Antes de Publicar)
> ⚠️ **Regla de Calidad DevOps:** *Nunca se sube a un registro una imagen que no ha arrancado y respondido exitosamente de forma local.*

```bash
# Lanzar contenedor temporal de prueba
podman run -d --name prueba -p 8080:8080 bitacora-api:"$VERSION"

# Validar endpoint raíz y healthcheck
curl -s http://localhost:8080 ; echo
curl -s http://localhost:8080/health ; echo

# Limpiar contenedor de prueba
podman rm -f prueba

# Inspeccionar las etiquetas OCI embebidas en la imagen
podman inspect bitacora-api:"$VERSION" \
  --format '{{json .Labels}}' | python3 -m json.tool
```

---

## 5. Estrategia de Etiquetado: Versionado Semántico en Cascada

Un mismo contenedor puede y debe tener múltiples etiquetas que apunten al mismo `Image ID` (mismo digest). Esto no duplica espacio en disco ni en la red:

```bash
REPO=docker.io/agcaaron/bitacora-api

# Versionado semantico en cascada
podman tag bitacora-api:"$VERSION" "$REPO":"$VERSION" # 1.0.0 (Version fija)
podman tag bitacora-api:"$VERSION" "$REPO":1.0        # 1.0 (Rama menor)
podman tag bitacora-api:"$VERSION" "$REPO":1          # 1 (Rama mayor)
podman tag bitacora-api:"$VERSION" "$REPO":latest     # latest (Ultima estable)

# Verificar todas las etiquetas locales creadas
podman images --filter reference="$REPO"
```

### ¿Por qué `latest` NO significa lo más reciente?
- `latest` es solo la etiqueta por defecto cuando no se escribe ningún tag.
- Si publicas la versión `2.0.0` y no mueves manualmente la etiqueta `latest`, cualquier usuario que haga `podman pull` seguirá recibiendo la versión obsoleta `1.0.0`.
- **En producción nunca se debe usar `latest`**, ya que rompe la reproducibilidad e impide hacer rollback seguro.

---

## 6. Publicación de Imágenes en Docker Hub (`podman push`)

Publicamos todas las etiquetas hacia tu cuenta de Docker Hub:

```bash
# Publicación individual o en cascada
for t in "$VERSION" 1.0 1 latest; do
  podman push "$REPO":"$t"
done
```

> **Nota:** La primera etiqueta (`1.0.0`) transferirá las capas binarias completas al registro. Las subsecuentes (`1.0`, `1`, `latest`) tardarán solo un par de segundos porque el registro detecta que los hashes de las capas ya existen y solo registra los nuevos nombres.

### Errores Comunes durante el Push y Solución

| Mensaje de Error | Causa Raíz | Solución Inmediata |
| :--- | :--- | :--- |
| `unauthorized: authentication required` | No se inició sesión o el token expiró. | Ejecutar nuevamente `podman login docker.io`. |
| `requested access to the resource is denied` | El namespace no coincide con tu cuenta. | Asegurarse de que el tag empiece por `docker.io/agcaaron/`. |
| `denied: insufficient scopes` | El token fue creado con permisos de solo lectura. | Generar un nuevo PAT en Docker Hub con permisos **Read & Write**. |
| `toomanyrequests` | Se excedió el límite de peticiones de Docker Hub. | Esperar unos minutos o autenticarse también para pulls. |
| `short-name did not resolve` | Falta el dominio del registro en el tag. | Incluir siempre el prefijo completo `docker.io/...`. |

---

## 7. Verificación de la Publicación y Pruebas Remotas

No basta con que el comando `push` termine sin errores; se debe verificar desde el exterior sin utilizar la caché de la máquina:

```bash
# A) Inspeccionar metadatos remotos en Docker Hub sin descargar la imagen (Skopeo)
skopeo inspect docker://"$REPO":1.0.0

# B) Listar todos los tags publicados en el repositorio remoto
skopeo list-tags docker://"$REPO"

# C) Comparar el Digest local contra el Digest remoto (deben ser identicos)
podman inspect "$REPO":1.0.0 --format '{{index .RepoDigests 0}}'
skopeo inspect docker://"$REPO":1.0.0 | grep -i digest

# D) Prueba de fuego: Eliminar las imagenes locales y hacer pull desde Docker Hub
podman rmi -f "$REPO":1.0.0 "$REPO":1.0 "$REPO":1 "$REPO":latest bitacora-api:1.0.0
podman pull "$REPO":1.0.0

# Desplegar desde Docker Hub y verificar que responde
podman run --rm -p 8080:8080 -d --name verif "$REPO":1.0.0
curl -s http://localhost:8080 ; echo
podman rm -f verif

# E) Despliegue inmutable por Digest (Recomendado para Produccion)
DIGEST=$(skopeo inspect docker://"$REPO":1.0.0 --format '{{.Digest}}')
podman run --rm "$REPO"@"$DIGEST" python -c "print('Digest inmutable verificado exitosamente')"
```

---

## 8. Imágenes Multiarquitectura (Manifest Lists) y Firma con Cosign

Si un desarrollador con Mac Apple Silicon (`arm64`) intenta correr una imagen compilada únicamente para `amd64`, experimentará fallos o emulación muy lenta. La solución estándar en la industria es crear un **Manifest List** (índice multiarquitectura):

```text
Manifest List :1.0.0
├── linux/amd64 ──► sha256:aaa... (Intel/AMD)
└── linux/arm64 ──► sha256:bbb... (ARM / Apple Silicon / Raspberry Pi)
```

### 8.1 Compilación Multiarquitectura con Podman

```bash
# 1. Instalar emulador QEMU en el host (solo una vez)
sudo dnf install -y qemu-user-static
sudo systemctl restart systemd-binfmt

# 2. Construir ambas arquitecturas bajo un único manifiesto
podman build \
  --platform linux/amd64,linux/arm64 \
  --manifest "$REPO":"$VERSION" \
  --build-arg APP_VERSION="$VERSION" \
  --build-arg APP_COMMIT="$COMMIT" \
  --build-arg BUILD_DATE="$FECHA" \
  .

# 3. Inspeccionar el indice local
podman manifest inspect "$REPO":"$VERSION"

# 4. Publicar el indice completo (usar 'manifest push', no 'push')
podman manifest push --all "$REPO":"$VERSION" docker://"$REPO":"$VERSION"

# 5. Confirmar que Docker Hub expone ambas arquitecturas
skopeo inspect --raw docker://"$REPO":"$VERSION" | python3 -m json.tool | grep -A2 architecture
```

### 8.2 Firma Criptográfica de Imágenes con Cosign

Permite a los consumidores verificar criptográficamente que la imagen proviene del autor legítimo y no fue alterada en el trayecto:

```bash
# 1. Generar par de llaves criptograficas
cosign generate-key-pair

# 2. Firmar la imagen publicada en Docker Hub
cosign sign --key cosign.key "$REPO":"$VERSION"

# 3. Verificar la firma usando la llave publica
cosign verify --key cosign.pub "$REPO":"$VERSION"
```

> 🔒 **Seguridad:** Agrega `cosign.key` a tu `.gitignore`. La llave privada nunca debe subirse al repositorio de Git.

---

## 9. Publicación Automatizada con CI/CD (GitHub Actions)

Para automatizar la entrega continua sin tocar la terminal, cada vez que se cree un tag en Git (ej. `git tag -a v1.1.0`), GitHub Actions construirá y publicará la imagen:

### Configurar Secretos en GitHub:
En tu repositorio de GitHub ➔ **Settings** ➔ **Secrets and variables** ➔ **Actions**:
- `DOCKERHUB_USER`: `agcaaron`
- `DOCKERHUB_TOKEN`: *(El Personal Access Token generado en Docker Hub)*

### Archivo de Workflow: `.github/workflows/publicar.yml`

```yaml
name: Publicar en Docker Hub

on:
  push:
    tags: ['v*.*.*']
  workflow_dispatch:

jobs:
  publicar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Calcular version y fecha
        id: meta
        run: |
          echo "version=${GITHUB_REF_NAME#v}" >> "$GITHUB_OUTPUT"
          echo "fecha=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" >> "$GITHUB_OUTPUT"

      - name: Construir imagen con Buildah
        id: build
        uses: redhat-actions/buildah-build@v2
        with:
          image: bitacora-api
          tags: ${{ steps.meta.outputs.version }} latest
          platforms: linux/amd64,linux/arm64
          containerfiles: ./Containerfile
          build-args: |
            APP_VERSION=${{ steps.meta.outputs.version }}
            APP_COMMIT=${{ github.sha }}
            BUILD_DATE=${{ steps.meta.outputs.fecha }}

      - name: Publicar en Docker Hub
        uses: redhat-actions/push-to-registry@v2
        with:
          image: ${{ steps.build.outputs.image }}
          tags: ${{ steps.build.outputs.tags }}
          registry: docker.io/agcaaron
          username: ${{ secrets.DOCKERHUB_USER }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}
```

Disparador en terminal:
```bash
git tag -a v1.1.0 -m "Nueva version con endpoint de metadatos"
git push origin v1.1.0
```

---

## 10. Retos y Buenas Prácticas de Ingeniería

### Reto 1: Reducción de Tamaño con Construcción Multietapa (`Containerfile.multietapa`)
Separa el entorno de compilación de la imagen productiva final:

```dockerfile
FROM docker.io/library/python:3.11-slim AS builder
WORKDIR /build
COPY app.py .
RUN python -m compileall -q app.py

FROM docker.io/library/python:3.11-slim
WORKDIR /opt/app-root/src
COPY --from=builder --chown=1001:0 /build/app.py .
ENV PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
USER 1001
CMD ["python", "app.py"]
```

### Reto 2: Escaneo de Vulnerabilidades antes de Publicar (Trivy)
```bash
podman run --rm -v /var/run:/var/run:Z \
  docker.io/aquasec/trivy:latest image "$REPO":1.0.0

# Bloquear build si existen vulnerabilidades criticas
trivy image --exit-code 1 --severity CRITICAL "$REPO":1.0.0
```

### Reto 3: Transferencia Directa Registro a Registro con Skopeo
Promover la imagen de Docker Hub a Quay.io sin descargar al disco:
```bash
podman login quay.io
skopeo copy --all \
  docker://docker.io/agcaaron/bitacora-api:1.0.0 \
  docker://quay.io/agcaaron/bitacora-api:1.0.0
```

### Reto 4: Auto-actualización Automática de Pods (`AutoUpdate`)
Permite que los contenedores del Pod se actualicen automáticamente al detectar una nueva versión en Docker Hub:
```bash
systemctl --user enable --now podman-auto-update.timer
podman auto-update --dry-run
podman auto-update
```

---

## 11. Guía de Ejecución Paso a Paso en la Máquina Virtual

Esta sección contiene la lista rápida de comandos que debes ejecutar en orden en la terminal de tu máquina virtual:

```bash
# 1. Crear directorio y navegar a el
mkdir -p /root/bitacora-api
cd /root/bitacora-api

# 2. Crear .dockerignore
cat <<'EOF' > .dockerignore
.git
.github
*.md
__pycache__/
*.pyc
.env
*.log
EOF

# 3. Crear app.py
cat <<'EOF' > app.py
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os
import platform
import socket

VERSION = os.environ.get("APP_VERSION", "desconocida")
COMMIT = os.environ.get("APP_COMMIT", "local")

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            datos = {"status": "ok"}
        else:
            datos = {
                "servicio": "bitacora-api",
                "version": VERSION,
                "commit": COMMIT,
                "host": socket.gethostname(),
                "arquitectura": platform.machine(),
                "python": platform.python_version(),
            }

        cuerpo = json.dumps(datos, indent=2, ensure_ascii=False).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)

if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 8080))
    print(f"bitacora-api {VERSION} escuchando en 0.0.0.0:{puerto}", flush=True)
    HTTPServer(("0.0.0.0", puerto), Handler).serve_forever()
EOF

# 4. Crear Containerfile
cat <<'EOF' > Containerfile
FROM docker.io/library/python:3.11-slim

ARG APP_VERSION=0.0.0
ARG APP_COMMIT=local
ARG BUILD_DATE

LABEL org.opencontainers.image.title="bitacora-api" \
      org.opencontainers.image.description="API de bitacora en Python puro" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${APP_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.authors="agcaaron" \
      org.opencontainers.image.source="https://github.com/AAGCAaron/DevOps_FI_UNAM" \
      org.opencontainers.image.licenses="MIT"

WORKDIR /opt/app-root/src

COPY --chown=1001:0 app.py .

ENV APP_VERSION=${APP_VERSION} \
    APP_COMMIT=${APP_COMMIT} \
    PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
USER 1001

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health')"

CMD ["python", "app.py"]
EOF

# 5. Iniciar sesion en Docker Hub
read -rsp "Ingresa tu Token de Docker Hub: " DH_TOKEN && echo
echo "$DH_TOKEN" | podman login docker.io --username agcaaron --password-stdin
unset DH_TOKEN

# 6. Construir con metadatos
VERSION=1.0.0
COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo manual)
FECHA=$(date -u +'%Y-%m-%dT%H:%M:%SZ')

podman build \
  --build-arg APP_VERSION="$VERSION" \
  --build-arg APP_COMMIT="$COMMIT" \
  --build-arg BUILD_DATE="$FECHA" \
  -t bitacora-api:"$VERSION" .

# 7. Etiquetar para Docker Hub
REPO=docker.io/agcaaron/bitacora-api

podman tag bitacora-api:"$VERSION" "$REPO":"$VERSION"
podman tag bitacora-api:"$VERSION" "$REPO":1.0
podman tag bitacora-api:"$VERSION" "$REPO":1
podman tag bitacora-api:"$VERSION" "$REPO":latest

podman images --filter reference="$REPO"

# 8. Publicar en Docker Hub
for t in "$VERSION" 1.0 1 latest; do
  podman push "$REPO":"$t"
done

# 9. Verificar la publicacion con Skopeo
skopeo list-tags docker://"$REPO"
```
