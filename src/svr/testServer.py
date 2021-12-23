import sys
import cgi
import os
import sys
import io
import json
from Crypto import Random
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5 as PKCS1_cipher
import base64
from urllib import parse
import xml.etree.cElementTree as ET
from http.server import HTTPServer
from http.server import BaseHTTPRequestHandler

CORPUS_DIR = "../../resource/corpus"
USER_LOG_FILE = "../../resource/user.json"
PUB_KEY_FILE = "../../resource/key/public_key.rsa"
PRI_KEY_FILE = "../../resource/key/private_key.rsa"
legal_action = {'1000': True,  # register 
                '1001': True,  # login
                '1002': True,  # query a RSA public key
                '1003': True,  # get sample
                '1004': True   # submit
            }

# init key
if not os.path.exists(PUB_KEY_FILE) \
    or not os.path.exists(PRI_KEY_FILE):
    random_generator = Random.new().read
    rsa = RSA.generate(2048, random_generator)
    
    private_key = rsa.exportKey()
    with open(PRI_KEY_FILE, 'wb') as f:
        f.write(private_key)
    
    public_key = rsa.publickey().exportKey()
    with open(PUB_KEY_FILE, 'wb') as f:
        f.write(public_key)
else:
    public_key = open(PUB_KEY_FILE, 'rb').read()
    private_key = RSA.importKey(open(PRI_KEY_FILE, 'rb').read())

cipher = PKCS1_cipher.new(private_key)

# init users database
users = {}
if not os.path.exists(USER_LOG_FILE):
    f = open(USER_LOG_FILE, 'w')
    f.close()
else:
    f = open(USER_LOG_FILE)
    for line in f:
        users.update(json.loads(line))
    f.close()

class GetHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        """ Sets headers required for CORS """
        self.send_header('Content-type', 'application/json')
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")

    def _register(self, username, password_encrypted):
        if username in users:
            errcode = -1
            errmsg = '用户名已被注册'
        else:
            password = cipher.decrypt(base64.b64decode(password_encrypted), 0)
            password = password.decode('utf-8')
            new_user = {username: password}
            users.update(new_user)
            f = open(USER_LOG_FILE, 'a')
            f.write(json.dumps(new_user) + '\n')
            f.close()

            errcode = 0
            errmsg = ''

        return json.dumps({'errcode': errcode, 'errmsg': errmsg})

    def _authorize(self, username, password_encrypted):
        # password = cipher.decrypt(base64.b64decode(password_encrypted), 0)
        # password = password.decode('utf-8')
        password = password_encrypted
        if username not in users:
            errcode = -1
            errmsg = '用户不存在'
        elif password != users[username]:
            errcode = -1
            errmsg = '用户名与密码不符'
        else:
            errcode = 0
            errmsg = ''

        return json.dumps({'errcode': errcode, 'errmsg': errmsg})

    def _sample(self, username):
        # if username not in users:
        #     errcode = -1
        #     errmsg = '非法用户'
        # else:
        #     text = corpus_sample(username)
        #     if text == '':
        #         errcode = -1
        #         errmsg = '无可用样本'
        #     else:
        #         errcode = 0
        #         errmsg = ''
        
        text = "医生您好！我的小腹为什么这么这么疼？我的胃口也不太好？"
        return json.dumps({'errcode': 0, 'errmsg': '', 'type': 1, 'text': text})

    def _parse(self, query):
        result = {}
        items = query.split('&')
        for item in items:
            k, v = item.split('=', 1)
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
                sRespData = self._register(parsed_result['username'], parsed_result['password'])
            elif parsed_result['action'] == '1001':
                sRespData = self._authorize(parsed_result['username'], parsed_result['password'])
            elif parsed_result['action'] == '1002':
                sRespData = json.dumps({'errcode': 0, 'errmsg': '', 'public_key': public_key.decode('utf-8')})
            elif parsed_result['action'] == '1003':
                sRespData = self._sample(parsed_result['username'])
            elif parsed_result['action'] == '1004':
                pass
            else:
                sRespData = json.dumps({'errcode': -1, 'errmsg': '未定义的操作'})
            print(sRespData)
            self.wfile.write(sRespData.encode())
        else:
            self.send_response(404)
            self._send_cors_headers()
            self.end_headers()

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8008), GetHandler)
    print('Starting server, use <Ctrl-C> to stop')
    server.serve_forever()