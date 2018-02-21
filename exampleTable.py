from PyQt5.QtWidgets import (QMainWindow,
                             QWidget,
                             QTreeView,
                             QMessageBox,
                             QFileDialog,
                             QLabel,
                             QSlider,
                             QCheckBox,
                             QLineEdit,
                             QVBoxLayout,
                             QApplication,
                             QPushButton,
                             QTableWidget,
                             QTableView,
                             QTableWidgetItem,
                             QScrollArea,
                             QAbstractScrollArea,
                             QAbstractItemView,
                             QSizePolicy,
                             QGridLayout,
                             QGroupBox,
                             QComboBox,
                             QAction,
                             QDockWidget,
                             QDialog,
                             QFrame,
                             QDialogButtonBox,
                             QInputDialog,
                             QProgressDialog,
                             QTabWidget)
from PyQt5.QtCore import Qt, QTimer, QAbstractTableModel, QCoreApplication, QSize
from PyQt5.QtGui import QIcon,QBrush
import sys

class Model(QAbstractTableModel):
    def __init__(self, parent=None):
        super(Model, self).__init__(parent)

        # list of lists containing [data for cell, changed]
        self._data = [[['%d - %d' % (i, j), False] for j in range(10)] for i in range(10)]

    def rowCount(self, parent):
        return len(self._data)

    def columnCount(self, parent):
        return len(self._data[0])

    def flags(self, index):
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def data(self, index, role):
        if index.isValid():
            data, changed = self._data[index.row()][index.column()]

            if role in [Qt.DisplayRole, Qt.EditRole]:
                return data

            if role == Qt.BackgroundRole and changed:
                return QBrush(Qt.darkBlue)

    def setData(self, index, value, role):
        if role == Qt.EditRole:
            # set the new value with True `changed` status
            self._data[index.row()][index.column()] = ["hi", True]
            self.dataChanged.emit(index, index)
            return True
        return False

if __name__ == '__main__':
    app = QApplication(sys.argv)

    t = QTableView()
    m = Model(t)
    t.setModel(m)
    t.show()

    sys.exit(app.exec_())
