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