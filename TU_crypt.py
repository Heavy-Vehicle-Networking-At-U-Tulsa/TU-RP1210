
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
    with open(keyfile, 'rb') as f:
        keystring = f.read()
    return load_ssh_public_key(keystring, default_backend())

def load_private_key(keyfile, passwd=None):
    """
    Loads a private PEM key from a file. Can also use a password. 
    """
    with open(keyfile, 'rb') as f:
        keystring = f.read()
    return load_pem_private_key(keystring, password=passwd, backend=default_backend())

def encrypt_bytes(data, keyfile):
    """
    Encrypt data using envelope encryption. 
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

def decrypt_bytes(package, keyfile):
    """
    decrypt data using envelope encryption. 
    """
    #unpack the dictionary
    safekey = package["key"].encode('ascii')
    safeiv = package["iv"].encode('ascii')
    safecipher = package["cipher"].encode('ascii')

    #decode the base64 encoded values
    ciphertext = base64.b64decode(safecipher)
    cryptkey = base64.b64decode(safekey)
    iv = base64.b64decode(safeiv)
    
    privkey = load_private_key(keyfile)
    if not privkey:
        print("Public Key Not Found")
        return 
    symkey = privkey.decrypt(cryptkey, 
                    OAEP(mgf=asym_padding.MGF1(algorithm=SHA256()),
                                 algorithm=SHA256(),
                                 label=None))
    cipher = Cipher(algorithms.AES(symkey), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    padded_data = decryptor.update(ciphertext)
    decryptor.finalize()

    unpadder = padding.PKCS7(128).unpadder()
    data = unpadder.update(padded_data)
    data += unpadder.finalize()
    
    return data


if __name__ == '__main__':
    """
    A simple example case
    """
    data = b'This is a test message! Giddie up! \x00' + bytes([x for x in range(256)])
    package = encrypt_bytes(data,"Client Public Key.pem")
    print("The following is the data to be encrypted:")
    print(data)
    print("\nThe encrypted package is as follows:")
    print(package)
    new_data = decrypt_bytes(package,"Client Private Key.pem")
    print("\nDecrypting the data gives back the original message:")
    print(new_data)
    print("\nEquality test results: {}".format(data==new_data))
    print("\nYou should keep your private key unique and secret.")