import sys
import cgi
import io
from urllib import parse
import xml.etree.cElementTree as ET
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

legal_action = {'1000': True,  # register 
                '1001': True,  # login
                '1002': True   # submit
            }

class GetHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        """ Sets headers required for CORS """
        self.send_header('Content-type', 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")

    def _register(self, username, password):
        # to do
        return True

    def _authorize(self, username, password):
        # to do
        return True

    def _parse(self, query):
        result = {}
        items = query.split('&')
        for item in items:
            k, v = item.split('=')
            result[k] = v
        
        if 'action' not in result:
            return None
        elif result['action'] not in legal_action:
            return None
        else:
            return result

    def do_GET(self):
        parsed_path = parse.urlparse(self.path)
        parsed_result = self._parse(parsed_path.query)
        print("GET", parsed_result)

        if parsed_result is not None:
            self.send_response(200)
            self._send_cors_headers()
            self.end_headers()

            if parsed_result['action'] == '1000':
                if self._register(parsed_result['username'], parsed_result['password']):
                    sRespData = "1"
                else:
                    sRespData = "0"
                self.wfile.write(sRespData.encode())      
            elif parsed_result['action'] == '1001':
                if self._authorize(parsed_result['username'], parsed_result['password']):
                    sRespData = "1"
                else:
                    sRespData = "0"
                self.wfile.write(sRespData.encode())
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8008), GetHandler)
    print('Starting server, use <Ctrl-C> to stop')
    server.serve_forever()