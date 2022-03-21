
# -*- coding: utf-8 -*-
from setuptools import setup

import codecs

with codecs.open('README.md', encoding="utf-8") as fp:
    long_description = fp.read()
INSTALL_REQUIRES = [
    'cryptography>=36.0.2',
]
EXTRAS_REQUIRE = {
    'ipy': [
        'jupyter>=1.0.0',
    ],
}
ENTRY_POINTS = {
    'console_scripts': [
        'pyagent = app.cli:cli',
    ],
}

setup_kwargs = {
    'name': 'py-agent',
    'version': '0',
    'description': 'encryption proxy',
    'long_description': long_description,
    'license': 'Apache-2.0',
    'author': '',
    'author_email': 'ZHANG Meng <ztz2000@gmail.com>',
    'maintainer': None,
    'maintainer_email': None,
    'url': 'https://github.com/ppmzhang2/pyagent',
    'packages': [
        'app',
    ],
    'package_dir': {'': 'src'},
    'package_data': {'': ['*']},
    'long_description_content_type': 'text/markdown',
    'classifiers': [
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Topic :: Software Development :: Build Tools',
    ],
    'install_requires': INSTALL_REQUIRES,
    'extras_require': EXTRAS_REQUIRE,
    'python_requires': '>=3.9,<3.11',
    'entry_points': ENTRY_POINTS,

}


setup(**setup_kwargs)
