import unittest

from cryptography.exceptions import InvalidTag

from wsproxy.enigma import AesGcm


class TestModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        pass

    @classmethod
    def tearDownClass(cls) -> None:
        pass

    def setUp(self):
        self.key = b'00000000000000000000000000000000'
        self.associated = b'authenticated but not encrypted payload'
        self.plaintext = b'a secret text'
        self.fake_key = b'10000000000000000000000000000000'
        self.fake_associated = b'some fake payload to authenticated'

    def tearDown(self):
        AesGcm.clear_instance()

    def test_aes_gcm(self):
        def fake_aes_gcm_iv(cypher_text: bytes, one_byte: bytes = b'\xc6'):
            return one_byte + cypher_text[1:]

        def fake_aes_gcm_tag(cypher_text: bytes, one_byte: bytes = b'\xc6'):
            return cypher_text[:13] + one_byte + cypher_text[14:]

        def fake_aes_gcm_data(cypher_text: bytes, one_byte: bytes = b'\xc6'):
            return cypher_text + one_byte

        # correct cypher instance
        aes_gcm = AesGcm(self.key, self.associated)
        cypher_code = aes_gcm.block_encrypt(self.plaintext)
        self.assertEqual(self.plaintext, aes_gcm.block_decrypt(cypher_code))
        self.assertRaises(
            InvalidTag,
            lambda: aes_gcm.block_decrypt(fake_aes_gcm_iv(cypher_code)))
        self.assertRaises(
            InvalidTag,
            lambda: aes_gcm.block_decrypt(fake_aes_gcm_tag(cypher_code)))
        self.assertRaises(
            AssertionError,
            lambda: aes_gcm.block_decrypt(fake_aes_gcm_data(cypher_code)))
        AesGcm.clear_instance()

        # cypher instance with wrong key
        fake_aes_key = AesGcm(self.fake_key, self.associated)
        self.assertRaises(InvalidTag,
                          lambda: fake_aes_key.block_decrypt(cypher_code))
        self.assertRaises(
            InvalidTag,
            lambda: fake_aes_key.block_decrypt(fake_aes_gcm_tag(cypher_code)))
        AesGcm.clear_instance()

        # cypher instance with wrong associated data
        fake_aes_ass = AesGcm(self.key, self.fake_associated)
        self.assertRaises(InvalidTag,
                          lambda: fake_aes_ass.block_decrypt(cypher_code))
        self.assertRaises(
            InvalidTag,
            lambda: fake_aes_ass.block_decrypt(fake_aes_gcm_tag(cypher_code)))
        AesGcm.clear_instance()


if __name__ == '__main__':
    unittest.main(verbosity=2)
