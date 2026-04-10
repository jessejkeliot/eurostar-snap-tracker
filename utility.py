from hashlib import sha256
def hash_for_db(to_hash: str):
    sha256_hash = sha256()
    sha256_hash.update(to_hash.encode())
    return sha256_hash.hexdigest()