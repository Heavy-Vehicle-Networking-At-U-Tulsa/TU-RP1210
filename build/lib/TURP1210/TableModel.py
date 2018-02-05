
from PyQt5.QtCore import Qt, QAbstractTableModel, QSortFilterProxyModel, QVariant
from PyQt5.QtGui import QIcon

from collections import OrderedDict

class J1939TableModel(QAbstractTableModel):
    ''' data model for a J1939 Data class '''
    def __init__(self):
        super(J1939TableModel, self).__init__()
        self.data_dict = OrderedDict()
        self.header = []
        self.table_rows = []

    def setDataHeader(self, header):
        self.header = header
        self.header_len = len(self.header)
        
    def setDataDict(self, new_dict):
        self.data_dict = OrderedDict(new_dict)
        self.table_rows = list(new_dict.keys())
        
    def aboutToUpdate(self):
        self.layoutAboutToBeChanged.emit()

    def signalUpdate(self):
        ''' tell viewers to update their data (this is full update, not
        efficient)'''
        self.layoutChanged.emit()

    def headerData(self, section, orientation = Qt.Horizontal, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.header[section]
        elif orientation == Qt.Vertical and role == Qt.DisplayRole:
            return section + 1
        else:
            return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            key = self.table_rows[index.row()]
            col_name = self.header[index.column()]
            return str(self.data_dict[key][col_name])
        else:
            return QVariant()
    
    def flags(self, index):
            flags = super(J1939TableModel, self).flags(index)
            flags |= ~Qt.ItemIsEditable
            return flags

    def setData(self, index, value, role = Qt.DisplayRole):
        if role == Qt.DisplayRole and index.isValid():
            self.dataChanged.emit(index, index)
            return True
        else:
            return False

    def rowCount(self, index=QVariant()):
        return len(self.data_dict)

    def columnCount(self, index=QVariant()):
        return len(self.header)

class Proxy(QSortFilterProxyModel):
    def __init__(self):
        super(Proxy, self).__init__()

    def headerData(self, section, orientation, role):
        return self.sourceModel().headerData(section, orientation, role)