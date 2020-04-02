import os
from typing import NoReturn

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

__all__ = ['AesGcm']


class SingletonMeta(type):
    _instance = None

    def __call__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instance


class AesGcm(metaclass=SingletonMeta):
    """AES-GCM cypher class

    reference:
    https://cryptography.io/en/latest/hazmat/primitives/symmetric-encryption/
    """

    __slots__ = ['algorithm', 'associated']

    def __init__(self, key: bytes, associated: bytes):
        """initialize an AES-GCM cypher instance

        :param key: secret bytes to construct the cipher
        :param associated: authenticated but not encrypted payload. It will be
          authenticated but not encrypted, it must also be passed in on
          decryption.
        """
        self.algorithm = algorithms.AES(key)
        self.associated = associated

    @classmethod
    def clear_instance(cls) -> NoReturn:
        try:
            del cls._instance
        except AttributeError:
            pass

    def encrypt(self, plaintext: bytes) -> bytes:
        """encrypt plain text bytes

        :param plaintext: bytes to encrypt
        :return: cipher text combined with:
          1. iv (12 len); 2. tag (16 len); 3. data
        """
        # Generate a random 96-bit IV.
        iv = os.urandom(12)

        # Construct an AES-GCM Cipher object with the given key and a
        # randomly generated IV.
        encryptor = Cipher(self.algorithm,
                           modes.GCM(iv),
                           backend=default_backend()).encryptor()

        # associated_data will be authenticated but not encrypted,
        # it must also be passed in on decryption.
        encryptor.authenticate_additional_data(self.associated)

        # Encrypt the plaintext and get the associated ciphertext.
        # GCM does not require padding.
        cipher_text = encryptor.update(plaintext) + encryptor.finalize()

        return iv + encryptor.tag + cipher_text

    def decrypt(self, cipher_text: bytes) -> bytes:
        """decrypt cipher text

        :param cipher_text: encrypted text with three parts:
          1. IV of length 12; 2. encryptor tag with length 16; 3. encrypted data
        :return:
        """
        iv = cipher_text[:12]
        tag = cipher_text[12:28]
        data = cipher_text[28:]
        # Construct a Cipher object, with the key, iv, and additionally the
        # GCM tag used for authenticating the message.
        decryptor = Cipher(self.algorithm,
                           modes.GCM(iv, tag),
                           backend=default_backend()).decryptor()

        # We put associated_data back in or the tag will fail to verify
        # when we finalize the decryptor.
        decryptor.authenticate_additional_data(self.associated)

        # Decryption gets us the authenticated plaintext.
        # If the tag does not match an InvalidTag exception will be raised.
        return decryptor.update(data) + decryptor.finalize()
