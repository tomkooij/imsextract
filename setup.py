#
# py2exe
#
# usage: python setup.py py2exe
#  this creates .exe in ../dist/
from distutils.core import setup
import py2exe

setup(console=['imsextract.py'])
