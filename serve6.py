import http.server
import socketserver
import socket

PORT = 28965

class Handler(http.server.SimpleHTTPRequestHandler):
    pass

class IPv6Server(socketserver.TCPServer):
    address_family = socket.AF_INET6

with IPv6Server(("::", PORT), Handler) as httpd:
    print(f"Serving on IPv6 port {PORT}")
    httpd.serve_forever()
