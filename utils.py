import hashlib


def md5(input_string):
    md5_hash = hashlib.md5(input_string.encode())
    return md5_hash.hexdigest()
