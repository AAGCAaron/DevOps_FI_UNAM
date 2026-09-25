# Tres Containerfiles para Podman en Red Hat / Rocky Linux

Este documento recopila y analiza los tres ejercicios prácticos del laboratorio:
1. **Webserver en Python puro:** Microservicio sin dependencias externas que corre con usuario no root.
2. **Base de datos PostgreSQL con usuarios:** Base de datos relacional con inicialización automatizada mediante scripts SQL y control de accesos por roles (escritura vs solo lectura).
3. **Ubuntu con aprovisionamiento automatizado de usuarios:** Contenedor basado en Ubuntu 24.04 que se actualiza en el build y da de alta cuentas desde un archivo de texto con configuración de `sudo`.

---

## Prerrequisitos en el Sistema Host

Verificar que Podman esté instalado y funcional en la máquina virtual:

```bash
sudo dnf install -y podman && podman --version
```

---

## Ejercicio 1: Webserver con Python Puro

Microservicio web HTTP desarrollado con la librería estándar de Python (`http.server`), sin dependencias de terceros (como Flask o FastAPI). Diseñado para correr con usuario no root (`UID 1001`) sobre la imagen base UBI 9 de Red Hat (o alternativamente `python:3.11-slim`).

### Estructura de Directorios
```text
web-python/
├── Containerfile
└── server.py
```

### 1.1 Código de la Aplicación: `server.py`
```python
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
```

### 1.2 Definición del Contenedor: `Containerfile`
```dockerfile
FROM registry.access.redhat.com/ubi9/python-311

LABEL description="Webserver en Python puro con http.server"

WORKDIR /opt/app-root/src

# Copiamos el código con el usuario no root de la imagen (1001)
COPY --chown=1001:0 server.py .

ENV PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
USER 1001

CMD ["python", "server.py"]
```

> 💡 **Alternativa libre comunitaria de Docker Hub:** Si prefieres no usar el registro de Red Hat, puedes sustituir la primera línea por `FROM docker.io/library/python:3.11-slim` y adaptar el `WORKDIR /app` con `RUN useradd -u 1001 -m appuser`.

### 1.3 Comandos de Construcción y Prueba
```bash
# 1. Entrar al directorio
cd web-python

# 2. Construir la imagen
podman build -t py-web:1.0 .

# 3. Ejecutar el contenedor en segundo plano mapeando el puerto 8080
podman run -d --name web -p 8080:8080 py-web:1.0

# 4. Probar los endpoints HTTP
curl http://localhost:8080
curl http://localhost:8080/health

# 5. Visualizar los registros (logs) del contenedor
podman logs web
```

---

## Ejercicio 2: Base de Datos PostgreSQL con Usuarios y Roles

Despliegue de un motor PostgreSQL 16 donde la creación de usuarios, asignación de permisos diferenciados (escritura vs solo lectura), tablas y datos de prueba se ejecutan automáticamente durante el primer arranque a través del directorio especial `/docker-entrypoint-initdb.d/`.

### Estructura de Directorios
```text
db-postgres/
├── Containerfile
└── init.sql
```

### 2.1 Script de Inicialización: `init.sql`
```sql
-- Usuarios
CREATE USER app_user WITH PASSWORD 'App2026!';
CREATE USER reporte  WITH PASSWORD 'Rep2026!';

-- Base de datos cuyo dueño es app_user
CREATE DATABASE inventario OWNER app_user;

\connect inventario

CREATE TABLE productos (
    id        SERIAL PRIMARY KEY,
    nombre    VARCHAR(100) NOT NULL,
    cantidad  INTEGER      NOT NULL DEFAULT 0,
    creado    TIMESTAMP    NOT NULL DEFAULT now()
);
ALTER TABLE productos OWNER TO app_user;

INSERT INTO productos (nombre, cantidad) VALUES
    ('Servidor ProLiant', 4),
    ('Switch 48p', 2),
    ('Disco NVMe 3.84TB', 12);

-- reporte: solo lectura
GRANT CONNECT ON DATABASE inventario TO reporte;
GRANT USAGE   ON SCHEMA public       TO reporte;
GRANT SELECT  ON ALL TABLES IN SCHEMA public TO reporte;
ALTER DEFAULT PRIVILEGES FOR ROLE app_user IN SCHEMA public
    GRANT SELECT ON TABLES TO reporte;
```

### 2.2 Definición del Contenedor: `Containerfile`
```dockerfile
FROM docker.io/library/postgres:16

LABEL description="PostgreSQL con usuarios y datos iniciales"

# Se ejecuta solo si el directorio de datos está vacío
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql

ENV TZ=America/Mexico_City

EXPOSE 5432
```

### 2.3 Comandos de Construcción y Prueba
```bash
# 1. Entrar al directorio
cd db-postgres

# 2. Construir la imagen
podman build -t pg-usuarios:1.0 .

# 3. Crear el volumen persistente para no perder la información al reiniciar
podman volume create pgdata

# 4. Levantar el contenedor pasando la contraseña de superusuario en tiempo de ejecución
podman run -d --name db \
  -e POSTGRES_PASSWORD='Admin2026!' \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  pg-usuarios:1.0

# 5. Esperar a que inicialice la base de datos (presionar Ctrl+C al ver "ready to accept connections")
podman logs -f db

# 6. Verificar que los usuarios existan en PostgreSQL
podman exec -it db psql -U postgres -c '\du'

# 7. Consultar datos como app_user y como reporte
podman exec -it db psql -U app_user -d inventario -c 'SELECT * FROM productos;'
podman exec -it db psql -U reporte -d inventario -c 'SELECT count(*) FROM productos;'

# 8. Comprobar que el usuario 'reporte' no puede escribir (debe fallar con error de permisos)
podman exec -it db psql -U reporte -d inventario \
  -c "INSERT INTO productos(nombre) VALUES ('prueba');"
```

---

## Ejercicio 3: Ubuntu que se Actualiza y Crea Usuarios desde Archivo

Construcción de una imagen basada en **Ubuntu 24.04** que automatiza el aprovisionamiento de cuentas del sistema leyendo un archivo de texto plano (`usuarios.txt`). Durante la fase de construcción (`build`), el sistema se actualiza con `apt-get`, crea los directorios home, asigna contraseñas cifradas y configura acceso `sudo` sin contraseña para el grupo `devops`.

### Estructura de Directorios
```text
ubuntu-usuarios/
├── Containerfile
└── usuarios.txt
```

### 3.1 Archivo de Usuarios: `usuarios.txt`
Formato: `usuario:contraseña` (las líneas con `#` y vacías se omiten automáticamente).
```text
# Las lineas con # y las vacias se ignoran
daniel:Daniel2026!
ana:Ana2026!
alumno1:Alumno2026!
alumno2:Alumno2026!
```

### 3.2 Definición del Contenedor: `Containerfile`
```dockerfile
FROM docker.io/library/ubuntu:24.04

LABEL description="Ubuntu actualizado con usuarios desde usuarios.txt"

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=America/Mexico_City

# 1. Actualizar el sistema operativo e instalar utilerías básicas
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y --no-install-recommends sudo tzdata vim-tiny iputils-ping && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# 2. Copiar el archivo que está en la misma ruta que este Containerfile
COPY usuarios.txt /tmp/usuarios.txt

# 3. Crear grupo y usuarios leyendo el archivo
RUN groupadd -f devops && \
    while IFS=: read -r usuario clave || [ -n "$usuario" ]; do \
      case "$usuario" in ''|'#'*) continue ;; esac; \
      useradd -m -s /bin/bash -G devops "$usuario"; \
      echo "$usuario:$clave" | chpasswd; \
      echo "Usuario creado: $usuario"; \
    done < /tmp/usuarios.txt && \
    echo '%devops ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/devops && \
    chmod 440 /etc/sudoers.d/devops && \
    rm -f /tmp/usuarios.txt

WORKDIR /home

CMD ["/bin/bash"]
```

### 3.3 Comandos de Construcción y Prueba
```bash
# 1. Entrar al directorio
cd ubuntu-usuarios

# 2. Construir la imagen
podman build -t ubuntu-usuarios:1.0 .

# 3. Verificar los usuarios y el grupo sin necesidad de entrar al contenedor
podman run --rm ubuntu-usuarios:1.0 getent group devops
podman run --rm ubuntu-usuarios:1.0 ls /home

# 4. Probar en sesión interactiva cambiando al usuario daniel y ejecutando sudo
podman run -it --rm --name ubu ubuntu-usuarios:1.0
su - daniel
sudo apt list --upgradable
exit
exit
```

---

## 4. Notas Técnicas y Buenas Prácticas para Podman en RHEL / Rocky Linux

1. **Nombres de archivo:** Podman busca automáticamente `Containerfile` o `Dockerfile` en el directorio actual. Ambos nombres funcionan exactamente igual. Para usar otro nombre se utiliza la bandera `-f <nombre_archivo>`.
2. **Nombres de imagen calificados (FQIN):** Se recomienda usar rutas de registro completas (ej. `docker.io/library/postgres:16` o `registry.access.redhat.com/...`) para evitar prompts interactivos de *short-names* derivados de `/etc/containers/registries.conf`.
3. **Puertos en modo Rootless:** Como usuario sin privilegios (*rootless*), Linux no permite por seguridad enlazar puertos menores al 1024. Por ello, los contenedores utilizan puertos de usuario como `8080`, `8085` o `5432`.
4. **SELinux y Volúmenes:** Si montas carpetas del host (*bind mounts*) con SELinux en modo `Enforcing`, debes agregar la bandera `:Z` al volumen (ejemplo: `-v ./datos:/data:Z`) para que el kernel aplique la etiqueta de contexto `container_file_t`.
5. **Acceso Externo en el Firewall:** Para que otras computadoras alcancen los servicios publicados, se debe abrir el puerto correspondiente en `firewalld`:
   ```bash
   sudo firewall-cmd --add-port=8080/tcp --permanent
   sudo firewall-cmd --add-port=5432/tcp --permanent
   sudo firewall-cmd --reload
   ```
6. **Seguridad en Producción:** Las contraseñas incluidas en `usuarios.txt` o `init.sql` quedan grabadas en las capas de la imagen. Esto es aceptable en entornos de laboratorio, pero en producción se deben gestionar mediante **`podman secret`** o variables de entorno en tiempo de ejecución.
7. **Comandos de Limpieza al finalizar prácticas:**
   ```bash
   # Detener y eliminar contenedores
   podman rm -f web db 2>/dev/null

   # Eliminar volumen de PostgreSQL
   podman volume rm pgdata 2>/dev/null

   # Eliminar imágenes intermedias huérfanas
   podman image prune -f
   ```

---

*Documento probado y validado con sintaxis de Podman 4.x / 5.x sobre Rocky Linux / RHEL 9 y 10.*
