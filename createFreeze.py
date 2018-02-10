import sys
import os

from cx_Freeze import setup, Executable

os.environ['TCL_LIBRARY'] = r'C:\Users\dailyadmin\AppData\Local\Programs\Python\Python36-32\tcl\tcl8.6'
os.environ['TK_LIBRARY'] = r'C:\Users\dailyadmin\AppData\Local\Programs\Python\Python36-32\tcl\tk8.6'

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {"packages": ["os","PGPy","cryptography","idna","humanize"],
                         "include_files": ["SCELogo.pdf",
                                           "ExamplePrivatePGPkey.pgp",
                                           "Client Public Key.pem"]}

if sys.platform == "win32":
    base = "Win32GUI"

target = Executable(
    script="TU_RP1210.py",
    base="Win32GUI",
    #icon=""
    )

setup(  name = "TU-RP1210",
        version = "1.0.0",
        description = "A graphical user interface for Vehicle Diagnostic Adapters compatible with RP1210",
        options = {"build_exe": build_exe_options},
        executables = [target])
