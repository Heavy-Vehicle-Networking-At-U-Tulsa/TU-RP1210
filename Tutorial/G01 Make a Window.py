from PyQt5.QtWidgets import (QMainWindow,
                             QWidget,
                             QPushButton,
                             QApplication,
                             QGridLayout,
                             QTableWidget)
from PyQt5.QtCore import QCoreApplication
from PyQt5.QtGui import QIcon, QFont
import sys
import TURP1210


class ExampleRP1210(QMainWindow):
    def __init__(self): 
        super(QMainWindow,self).__init__()
        self.setWindowTitle("Example RP1210")
        self.statusBar().showMessage("Welcome!")

        self.counter = 1

        main_widget = QWidget()
        
        myNewButton = QPushButton("New Action")
        myNewButton.setToolTip("This is a message")
        myNewButton.clicked.connect(self.do_something)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(myNewButton,0,0,1,1)

        main_widget = QWidget()
        main_widget.setLayout(self.grid_layout)

        self.setCentralWidget(main_widget)
        self.show()

    def do_something(self):
        print("I go pressed.")
        self.counter += 1
        self.statusBar().showMessage("I got pressed {} times.".format(self.counter))



app = QApplication(sys.argv)
execute = ExampleRP1210()
sys.exit(app.exec_())