import sys
import shutil
import os
from cx_Freeze import setup, Executable
import json
with open("TURP1210/version.json") as fp:
    version = json.load(fp)

#os.environ['TCL_LIBRARY'] = r'C:\Users\dailyadmin\AppData\Local\Programs\Python\Python36-32\tcl\tcl8.6'
#os.environ['TK_LIBRARY'] = r'C:\Users\dailyadmin\AppData\Local\Programs\Python\Python36-32\tcl\tk8.6'

# Dependencies are automatically detected, but it might need fine tuning.

with open("requirements.txt") as req:
    needs = req.readlines()
print([ p.split("=")[0] for p in needs])

try:
    shutil.rmtree(r"build/exe.win32-3.6")
except FileNotFoundError:
    pass
try:
    shutil.rmtree(r"TURP1210/build")
except FileNotFoundError:
    pass

build_exe_options = {"packages": ['cryptography', 
                                  'reportlab', 
                                  'idna',
                                  'requests', 
                                  'pgpy', 
                                  'passlib', 
                                  'humanize', 
                                  'winshell',
                                  'matplotlib',
                                  'numpy',
                                  #'tkinter',  
                                  'pdfrw',
                                  'serial'] ,
                     "include_files": ["TURP1210/SCELogo.pdf",
                                       "TURP1210/logging.config.json",
                                       "TURP1210/Client Public Key.pem",
                                       "TURP1210/J1939db.json",
                                       "TURP1210/J1587db.json",
                                       "TURP1210/icons",
                                      ],
                    
                     "excludes": ["sqlite",
                                  #"scipy",
                                  "IPython",
                                  "PyQt4",
                                  "tkinter",
                                  # "numpy",
                                  # "numbers",
                                  # "nturl2path",
                                  # "multiprocessing",
                                  # "lib2to3",
                                  # "http",
                                  # "email",
                                  # "distutils",
                                  # "doctest",
                                  # "dummy_threading",
                                  # "curses",
                                  # "cycler",
                                  # "dateutil",
                                  # "decimal",
                                  # "difflib",
                                  # "crypt",
                                  # "copyreg",
                                  # "copy",
                                  # "contextlib",
                                  # "concurrent",
                                  # "colorama",
                                  # "codecs",
                                  # "chardet",
                                  # "cgi",
                                  # "certifi",
                                  # "ans1crypto",
                                  # "enum",
                                  # "netbios",
                                  # "win32com",
                                  # "urllib",
                                  # "unittest",
                                  # "typing",
                                  # "tty",
                                   "tornado",
                                  # "token",
                                  # "tokenize",
                                  # "tests",
                                  # "sip",
                                  # "singledispatch",
                                  # "singledispatch_helpers",
                                  # "setuptools",
                                  # "matplotlib.backends.backend_webagg",
                                  # "matplotlib.mpl-data"

                                 ],
                     "optimize": 2,
                     "include_msvcr": True,
                     

                    }

if sys.platform == "win32":
    base = "Win32GUI"

target = Executable(
    script=r"TURP1210\TU_RP1210.py",
    #initScript="",
    base=base,
    #icon="",
    #targetName="",
    #shortcutName,
    #shortcutDir,
    #copyright,
    #trademarks=''

    )

setup(  name = "TU-RP1210",
        version = "{}.{}.{}".format(version["major"],version["minor"],version["patch"]),
        description = "A graphical user interface for Vehicle Diagnostic Adapters compatible with RP1210",
        options = {"build_exe": build_exe_options,
                   "install_exe":{"force":True},
                   "bdist_msi":{"add_to_path":True,
                                "upgrade_code":True}
                  },
        executables = [target])

