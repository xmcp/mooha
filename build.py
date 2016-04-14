import sys
import os,shutil
from cx_Freeze import setup, Executable
base = None
if sys.platform == 'win32':
    base = 'Win32GUI'
executables = [Executable(script='Mooha.pyw',
               base=base,
               targetName="Mooha.exe",
               compress=True),
               Executable(script='MoohaCLI.py',
               base=None,
               targetName="[CLI]Mooha.exe",
               compress=True)]
setup(name='Mooha',
      version='1.0',
      description='Moodle file manager',
      executables=executables)

print('===== CLEANING UP =====')

#os.remove('build/exe.win32-3.4/unicodedata.pyd')
os.remove('build/exe.win32-3.4/_hashlib.pyd')
shutil.rmtree('build/exe.win32-3.4/tcl/tzdata')
shutil.rmtree('build/exe.win32-3.4/tcl/msgs')
shutil.rmtree('build/exe.win32-3.4/tcl/encoding')
shutil.rmtree('build/exe.win32-3.4/tk/demos')
shutil.rmtree('build/exe.win32-3.4/tk/images')
shutil.rmtree('build/exe.win32-3.4/tk/msgs')

os.rename('build/exe.win32-3.4','build/Mooha-exe.win32-3.4')

print('===== DONE =====')

