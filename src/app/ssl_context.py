"""SSL context"""
from __future__ import annotations

import logging.config
import ssl

from . import cfg

LOGGER = logging.getLogger(__name__)


def get_ssl_context(server_side: bool = False):
    """get SSL context"""

    def passwd():
        return cfg.CERT_PASS

    if server_side:
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_ctx.options |= ssl.OP_SINGLE_DH_USE
        ssl_ctx.options |= ssl.OP_SINGLE_ECDH_USE
    else:
        ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_ctx.options |= ssl.OP_NO_TLSv1
    ssl_ctx.options |= ssl.OP_NO_TLSv1_1
    ssl_ctx.load_cert_chain(cfg.CERT_FILE,
                            keyfile=cfg.CERT_KEY,
                            password=passwd)
    ssl_ctx.check_hostname = False
    # pylint: disable=no-member
    ssl_ctx.verify_mode = ssl.VerifyMode.CERT_NONE
    ssl_ctx.set_ciphers(
        'ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384')
    return ssl_ctx
