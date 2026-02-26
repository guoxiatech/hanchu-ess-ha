"""AES加密工具"""
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

AES_KEY = b"9z64Qr8mZH7Pg8d1"

def encrypt_data(data: dict) -> str:
    """加密数据"""
    json_str = json.dumps(data, separators=(',', ':'))
    cipher = AES.new(AES_KEY, AES.MODE_CBC, AES_KEY)
    encrypted = cipher.encrypt(pad(json_str.encode('utf-8'), AES.block_size))
    return base64.b64encode(encrypted).decode('utf-8')
