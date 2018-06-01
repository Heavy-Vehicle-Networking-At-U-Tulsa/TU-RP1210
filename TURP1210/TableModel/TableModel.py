
from PyQt5.QtCore import Qt, QAbstractTableModel, QSortFilterProxyModel, QVariant, QModelIndex
from PyQt5.QtGui import QIcon, QBrush, QColor

from collections import OrderedDict

color_dict = {'maroon':'#800000','dark red':'#8B0000','brown':'#A52A2A','firebrick':'#B22222',
            'crimson':'#DC143C','red':'#FF0000','tomato':'#FF6347','coral':'#FF7F50',
            'indian red':'#CD5C5C','light coral':'#F08080','dark salmon':'#E9967A','salmon':'#FA8072',
            'light salmon':'#FFA07A','orange red':'FF4500','dark orange':'#FF8C00','orange':'#FFA500',
            'gold':'#FFD700','dark golden rod':'#B8860B','golden rod':'#DAA520','pale golden rod':'#EEE8AA',
            'dark khaki':'#BDB76B','khaki':'#F0E68C','olive':'#808000','yellow':'#FFFF00',
            'yellow green':'#9ACD32','dark olive green':'#556B2F','olive drab':'#6B8E23','lawn green':'7CFC00',
            'green yellow':'#ADFF2F','dark green':'#006400','green':'#008000','forest green':'#228B22',
            'lime':'#00FF00','lime green':'#32CD32','light green':'#90EE90','pale green':'#98FB98',
            'dark sea green':'#8FBC8F','medium spring green':'#00FA9A','spring green':'#00FF7F',
            'sea green':'#2E8B57','medium aqua marine':'#66CDAA','light sea green':'#20B2AA',
            'dark slate gray':'#2F4F4F','teal':'#008080','dark cyan':'#008B8B','aqua':'#00FFFF',
            'cyan':'#00FFFF','light cyan':'#E0FFFF','dark turquoise':'#00CED1','turquoise':'#40E0D0',
            'medium turquoise':'#48D1CC','pale turquoise':'#AFEEEE','aqua marine':'#7FFFD4',
            'powder blue':'#B0E0E6','cadet blue':'#5F9EA0','steel blue':'#4682B4','corn flower blue':'#6495ED',
            'deep sky blue':'#00BFFF','dodger blue':'#1E90FF','light blue':'#ADD8E6','sky blue':'#87CEEB',
            'light sky blue':'#87CEFA','midnight blue':'#191970','navy':'#000080','dark blue':'#00008B',
            'medium blue':'#0000CD','blue':'#0000FF','royal blue':'#4169E1','blue violet':'#8A2BE2',
            'indigo':'#4B0082','dark slate blue':'#483D8B','slate blue':'#6A5ACD','medium slate blue':'#7B68EE',
            'medium purple':'#9370DB','dark magenta':'#8B008B','dark violet':'#9400D3','dark orchid':'#9932CC',
            'medium orchid':'#BA55D3','purple':'#800080','thistle':'#D8BFD8','plum':'#DDA0DD','violet':'#EE82EE',
            'magenta':'#FF00FF','orchid':'#DA70D6','medium violet red':'#C71585','pale violet red':'#DB7093',
            'deep pink':'#FF1493','hot pink':'#FF69B4','light pink':'#FFB6C1','pink':'#FFC0CB',
            'antique white':'#FAEBD7','beige':'#F5F5DC','bisque':'#FFE4C4','blanched almond':'#FFEBCD',
            'wheat':'#F5DEB3','corn silk':'#FFF8DC','lemon chiffon':'#FFFACD','light golden rod yellow':'#FAFAD2',
            'light yellow':'#FFFFE0','saddle brown':'#8B4513','sienna':'#A0522D','chocolate':'#D2691E',
            'peru':'#CD853F','sandy brown':'#F4A460','burly wood':'#DEB887','tan':'#D2B48C',
            'rosy brown':'#BC8F8F','moccasin':'#FFE4B5','navajo white':'#FFDEAD','peach puff':'#FFDAB9',
            'misty rose':'#FFE4E1','lavender blush':'#FFF0F5','linen':'#FAF0E6','old lace':'#FDF5E6',
            'papaya whip':'#FFEFD5','sea shell':'#FFF5EE','mint cream':'#F5FFFA','slate gray':'#708090',
            'light slate gray':'#778899','light steel blue':'#B0C4DE','lavender':'#E6E6FA','floral white':'#FFFAF0',
            'alice blue':'#F0F8FF','ghost white':'#F8F8FF','honeydew':'#F0FFF0','ivory':'#FFFFF0',
            'azure':'#F0FFFF','snow':'#FFFAFA','black':'#000000','dim gray':'#696969','gray':'#808080',
            'dark gray':'#A9A9A9','silver':'#C0C0C0','light gray':'#D3D3D3','gainsboro':'#DCDCDC',
            'white smoke':'#F5F5F5','white':'#FFFFFF'}

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
                stringSA = self.data_dict[key]['SA']
                SA = int(stringSA)
                if SA == 0:
                    return QBrush(QColor(255,177,0))
                elif SA == 15:
                    return QBrush(QColor(255,0,0))
                elif SA == 49:
                    return QBrush(QColor(60,200,245))
                elif SA == 23:
                    return QBrush(QColor(180,95,225))
                elif SA == 33:
                    return QBrush(QColor(245,130,190))
                elif SA == 40:
                    return QBrush(QColor(178,177,124))
                elif SA == 250:
                    return QBrush(QColor(3,180,140))
            elif self.first == "Line":
                key = self.table_rows[index.row()]
                col_name = self.header[index.column()]
                stringSID = self.data_dict[key]['SID']
                if stringSID == '2E':
                    return QBrush(QColor(255,0,0))
                elif stringSID == '22':
                    return QBrush(QColor(0,255,0)) 
                elif stringSID == '7F':
                    return QBrush(QColor(255,154,0))
                elif stringSID == '62':
                    return QBrush(QColor(60,215,245))
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