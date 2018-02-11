# TU-RP1210
A repository with sample source code for the American Trucking Association's Technology and Maintenance Council (TMC) RP1210 Windows Communication API

This is a PyQt5 project, which means it inherits the GPLv3 license with exceptions. 

The program makes use of the ctypes library in Python to connect to the RP1210 DLL driver files. 

## Installation
Install Python 3.6. It may work with other versions, but hasn't been tested yet.

The Python package for this repository is available on pip. 

```pip install TURP1210```

The example.py program will enable you to import and run the module. Running a program base on the TURP1210 module is as simple as: 

```
import TURP1210 
from TURP1210.TU_RP1210 import *
from PyQt5.QtCore import QCoreApplication

class ExampleGUI(TURP1210.TU_RP1210.TU_RP1210):
    def __init__(self):
        super(ExampleGUI,self).__init__()

app = QApplication(sys.argv)
execute = ExampleGUI()
sys.exit(app.exec_())
```

### Packaging
open a command prompt (cmd) that has the python path ready to go. In the `GitHub\TURP1210` directory (or wherever you saved the file) we will perform the following actions.

  1. Check dependencies and create an up to date `requirements.txt` file by running 

```pipreqs /path/to/project```

 or 

 ```pipreqs --force ./``` if you are already in the  `GitHub\TURP1210` directory

If this doesn't work, try ```pip install pipreqs``` first.

2. Build a wheel

 ```python setup.py bdist_wheel```

3. Upload to PiPy

```twine upload dist/*```

If you get `HTTPError: 400 Client Error: File already exists. for url: https://upload.pypi.org/legacy/`, then make sure you update the version number in setup.py. You'll have to delete the old dist directory and try steps 2 and 3 again.

4. In git, commit and do a pull request to the master branch on GitHub.
 
5. Make an executable distribution by running ```python createFreeze.py build```

6. Test the executable by running ```build\exe.win32-3.6\TU_RP1210.exe```
 
5. Add a version tag in GitHub. 

6. Use the version tag and create a zip file with the executable. For example, `TU_RP1210-1.0.2.zip`

7. Upload the zip file to GitHub. Anyone with Windows 7 or above should be able to extract this file and run the TU_RP1210.exe file. This program requires an installed RP1210 Vehicle Diagnostics Adapter, like a DG Technologies DPA5.
 
