"""encryption"""
import os
from struct import pack
from struct import unpack
from typing import NoReturn

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers import algorithms
from cryptography.hazmat.primitives.ciphers import modes

__all__ = ['AesGcm']


class SingletonMeta(type):
    """singleton meta-class"""
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
    IV_SIZE = 12
    TAG_SIZE = 16
    DATA_LEN_SIZE = 2
    DATA_SIZE = 65535
    FULL_BLOCK_SIZE = IV_SIZE + TAG_SIZE + DATA_LEN_SIZE + DATA_SIZE

    __slots__ = ['key', 'associated']

    def __init__(self, key: bytes, associated: bytes):
        """initialize an AES-GCM cypher instance

        :param key: secret bytes to construct the cipher
        :param associated: authenticated but not encrypted payload. It will be
          authenticated but not encrypted, it must also be passed in on
          decryption.
        """
        self.key = key
        self.associated = associated

    @classmethod
    def clear_instance(cls) -> NoReturn:
        """clear instance"""
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
        encryptor = Cipher(algorithms.AES(self.key),
                           modes.GCM(iv),
                           backend=default_backend()).encryptor()

        # associated_data will be authenticated but not encrypted,
        # it must also be passed in on decryption.
        encryptor.authenticate_additional_data(self.associated)

        # Encrypt the plaintext and get the associated ciphertext.
        # GCM does not require padding.
        cipher_text = encryptor.update(plaintext) + encryptor.finalize()

        return iv, encryptor.tag, cipher_text

    def decrypt(self, iv: bytes, tag: bytes, data: bytes) -> bytes:
        """decrypt cipher text

        :param iv:
        :param tag:
        :param data:
        :return:
        """
        # Construct a Cipher object, with the key, iv, and additionally the
        # GCM tag used for authenticating the message.
        decryptor = Cipher(algorithms.AES(self.key),
                           modes.GCM(iv, tag),
                           backend=default_backend()).decryptor()

        # We put associated_data back in or the tag will fail to verify
        # when we finalize the decryptor.
        decryptor.authenticate_additional_data(self.associated)

        # Decryption gets us the authenticated plaintext.
        # If the tag does not match an InvalidTag exception will be raised.
        return decryptor.update(data) + decryptor.finalize()

    def block_encrypt(self, plaintext: bytes) -> bytes:
        """encrypt plain text into fixed size cypher block

        :param plaintext: bytes to encrypt
        :return: ciphered data block containing:
          1. iv (12 bit); 2. tag (16 bit); 3. encrypted data block (65537 bit)
        """
        # return empty byte when not input
        if not plaintext:
            return b''

        # data size must be smaller than the block size
        length = len(plaintext)
        assert length <= self.DATA_SIZE

        # random padding
        padding = os.urandom(self.DATA_SIZE - length)

        # include both actual data length and padding
        plain_block = pack('!H', length) + plaintext + padding

        iv, tag, cypher = self.encrypt(plain_block)

        return iv + tag + cypher

    def block_decrypt(self, cypher_block: bytes) -> bytes:
        """block decrypt"""
        # return empty byte when not input
        if not cypher_block:
            return b''

        # check block size
        assert len(cypher_block) == self.FULL_BLOCK_SIZE
        iv = cypher_block[:12]
        tag = cypher_block[12:28]
        data_block = cypher_block[28:]
        plain_block = self.decrypt(iv, tag, data_block)
        actual_size = unpack('!H', plain_block[:2])[0]
        return plain_block[2:actual_size + 2]
