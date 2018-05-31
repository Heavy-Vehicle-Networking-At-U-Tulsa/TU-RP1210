
from PyQt5.QtCore import Qt, QAbstractTableModel, QSortFilterProxyModel, QVariant, QModelIndex
from PyQt5.QtGui import QIcon, QBrush, QColor

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
        self.first = self.header[0]
        print(self.first)
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
            #print(key)
            #print(col_name)
            #print('hey')
            #print(self.data_dict.values())
            return str(self.data_dict[key][col_name])
        if role == Qt.BackgroundRole:
            if self.first == 'PGN':
                key = self.table_rows[index.row()]
                pgn = key.split(',')[0][1:]
                int_pgn = int(pgn)
                if int_pgn == 65264:
                    return QBrush(QColor(255,0,255))
                elif int_pgn == 61440:
                    return QBrush(QColor(255,0,125))
                elif int_pgn == 65271:
                    return QBrush(QColor(0,255,255))
                elif int_pgn == 65270:
                    return QBrush(QColor(125,255,0))  
                elif int_pgn == 65269:
                    return QBrush(QColor(125,0,255))
                elif int_pgn == 65271:
                    return QBrush(QColor(0,0,255))
                elif int_pgn == 65263:
                    return QBrush(QColor(0,255,125))
                elif int_pgn == 65262:
                    return QBrush(QColor(232,149,6))
                elif int_pgn == 65259:
                    return QBrush(QColor(255,250,0))
                elif int_pgn == 65226:
                    return QBrush(QColor(132,11,163))
                elif int_pgn == 65266:
                    return QBrush(QColor(255,119,119))
                elif int_pgn == 65251:
                    return QBrush(QColor(16,205,209))
                elif int_pgn == 65217:
                    return QBrush(QColor(183,228,255))
                elif int_pgn == 65249:
                    return QBrush(QColor(252,166,228))
            elif self.first == "Acronym":
                key = self.table_rows[index.row()]
                col_name = self.header[index.column()]
            elif self.first == "Line":
                key = self.table_rows[index.row()]
                col_name = self.header[index.column()]
                print('hey')
                stringSID = self.data_dict[key]['SID']
                if stringSID == '2E':
                    return QBrush(QColor(255,0,0))
                elif stringSID == '22':
                    return QBrush(QColor(0,255,0)) 
        else:
            return QVariant()
    
    #def colorTable(self, index, role = Qt.BackgroundRole):
        #if index.isValid():



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