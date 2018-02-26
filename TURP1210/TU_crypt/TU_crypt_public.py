
#!/bin/env/python
# the cryptography module can be supplied by PGPy 
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.asymmetric.padding import OAEP
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa as RSA
from cryptography.hazmat.primitives.serialization import load_ssh_public_key, load_pem_private_key
import base64
import os

def load_public_key(keyfile):
    """
    Loads an SSH (PEM) public key from a the path.
    """
    try:
        with open(keyfile, 'rb') as f:
            keystring = f.read()
    except (FileNotFoundError, OSError):
        keystring = bytes(keyfile,'ascii')

    return load_ssh_public_key(keystring, default_backend())

def encrypt_bytes(data, keyfile):
    """
    Encrypt data using envelope encryption. 
    keyfile can be a path to the public key file or a variable with the public key string 
    """
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data)
    padded_data += padder.finalize()

    iv = os.urandom(16)
    symkey = os.urandom(16)
    pubkey = load_public_key(keyfile)
    if not pubkey:
        print("Public Key Not Found.")
        return 
    cipher = Cipher(algorithms.AES(symkey), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_data)
    encryptor.finalize()

    cryptkey = pubkey.encrypt(symkey, 
                    OAEP(mgf=asym_padding.MGF1(algorithm=SHA256()),
                                 algorithm=SHA256(),
                                 label=None))
    safecipher = base64.b64encode(ciphertext)
    safekey = base64.b64encode(cryptkey)
    safeiv = base64.b64encode(iv)
    package = {"key": safekey.decode('ascii'), "iv": safeiv.decode(
        'ascii'), "cipher": safecipher.decode('ascii')}   
    return package

