"""
Including Python Setup module
"""
from setuptools import setup


setup(name='wcs',
      version='0.1.0',
      description='Python Client API for Web Coverage Service 2.0',
      url='https://github.com/eows/wcs-py',
      author='Gilberto Ribeiro de Queiroz',
      author_email='gribeiro@dpi.inpe.br',
      license='LGPL3',
      packages=['wcs'],
      install_requires=[
          "requests",
          "xmltodict"
      ],
      zip_safe=False)
