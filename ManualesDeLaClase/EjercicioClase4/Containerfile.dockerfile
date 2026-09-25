FROM docker.io/library/python:3.11-slim

LABEL description="Webserver en Python puro con http.server"

WORKDIR /app

# Creamos un usuario no-root por seguridad
RUN useradd -u 1001 -m appuser

# Copiamos el código asignando permisos al usuario no root
COPY --chown=1001:1001 server.py .

ENV PORT=8080 \
    PYTHONUNBUFFERED=1

EXPOSE 8080
USER 1001

CMD ["python", "server.py"]