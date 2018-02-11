import TURP1210 
from TURP1210.TU_RP1210 import *
from PyQt5.QtCore import QCoreApplication

class ExampleGUI(TURP1210.TU_RP1210.TU_RP1210):
    def __init__(self):
        super(ExampleGUI,self).__init__()

app = QApplication(sys.argv)
execute = ExampleGUI()
sys.exit(app.exec_())