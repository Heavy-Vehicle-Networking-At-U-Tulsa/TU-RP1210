
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
from PyQt5.QtCore import Qt, QTimer, QAbstractTableModel, QCoreApplication, QVariant, QAbstractItemModel, QSortFilterProxyModel
from PyQt5.QtGui import QIcon
import threading
import queue
import time
import calendar
import struct
import base64
import traceback
from collections import OrderedDict
from TURP1210.RP1210.RP1210Functions import *
from TURP1210.TableModel.TableModel import *
from TURP1210.Graphing.graphing import *
from TURP1210.ISO15765 import *

import logging
logger = logging.getLogger(__name__)

class J1939Tab(QWidget):
    def __init__(self, parent, tabs):
        super(J1939Tab,self).__init__()
        self.root = parent
        self.tabs = tabs
        
        self.iso_queue = queue.Queue()
        self.iso_recorder = ISO15765Driver(self.root, self.iso_queue)

        self.previous_spn_length = 0
        self.previous_uds_length = 0
        self.reset_data()

        self.spn_needs_updating = True
        self.dm01_needs_updating = True
        self.dm02_needs_updating = True

        self.init_pgn()
        self.init_spn()
        self.init_dtc()
        self.init_uds()
        
        self.j1939db = self.root.j1939db
        self.time_spns = [959, 960, 961, 963, 962, 964]
        
        

        stop_broadcast_timer = QTimer(self)
        stop_broadcast_timer.timeout.connect(self.stop_broadcast)
        stop_broadcast_timer.start(5000) #milliseconds

        uds_fill_timer = QTimer(self)
        uds_fill_timer.timeout.connect(self.fill_uds_table)
        uds_fill_timer.start(500)

        # spn_table_timer = QTimer(self)
        # spn_table_timer.timeout.connect(self.fill_spn_table)
        # spn_table_timer.start(500) #milliseconds

        self.j1939_request_pgns = [40448, 64891, 64920, 64966, 64981, 65154, 65155, 65164, 65193,
                                   65260, 65200, 65101, 65210, 64888, 64889, 65199, 65214, 65244,
                                   65203, 64896, 64951, 65131, 64898, 64952, 65202, 64950, 64949,
                                   49408, 49664, 65230, 65229, 65231, 65254, 65227, 65212, 65203,
                                   40960, 65208, 65255, 65205, 65211, 65209, 65257, 65236, 40704,
                                   65234, 65259, 65242, 54016, 65206, 65207, 65204, 65248, 64792,
                                   64957, 64969, 65099, 65194, 65201, 65216, 65249, 65250, 65253,
                                   65261]
        self.j1939_request_pgns += [65259 for i in range(6)] #Component ID
        self.j1939_request_pgns += [65260 for i in range(6)] #VIN 
        self.j1939_request_pgns += [65242 for i in range(6)] #Software ID
        
        self.pgns_to_not_decode = [  59392, #Ack
                                    0xEA00, #request messages
                                    0xEB00, # Transport
                                    0xEC00, # Transport
                                    0xDA00, #ISO 15765
                                    65247, # EEC3 at 20 ms
                                    #65265, # Cruise COntrol Vehicle SPeed
                                    0xF001,
                                    0xF002,
                                    0xF003,
                                    0xF004,
                                    57344, #CM1 message
                                    ]
    def get_pgn_label(self, pgn):

        try:
            return self.j1939db["J1939PGNdb"]["{}".format(pgn)]["Name"]
        except KeyError:
            
            return "Not Provided"

    def reset_data(self):
        self.j1939_count = 0  # successful 1939 messages
        self.ecm_time = {}
        self.battery_potential = {}
        self.speed_record = {}
        self.pgn_rows = []
        self.j1939_unique_ids = OrderedDict()
        self.unique_spns = OrderedDict()
        self.active_trouble_codes = {}
        self.previous_trouble_codes = {}
        self.freeze_frame = {}
        self.iso_recorder.uds_messages = OrderedDict()
        #self.root.data_package["UDS Messages"] = self.iso_recorder.uds_messages
        

    def init_pgn(self):
        logger.debug("Setting up J1939 PGN Tab.")
        self.j1939_tab = QWidget()
        self.tabs.addTab(self.j1939_tab,"J1939 PGNs")
        tab_layout = QVBoxLayout()
        j1939_id_box = QGroupBox("J1939 Parameter Group Numbers")
        
        self.add_message_button = QCheckBox("Dynamically Update Table")
        self.add_message_button.setChecked(True)

        self.stop_broadcast_button = QCheckBox("Stop J1939 Broadcast")
        self.stop_broadcast_button.setChecked(False)

        clear_button = QPushButton("Clear J1939 PGN Table")
        clear_button.clicked.connect(self.clear_j1939_table)
        
        #Set up the Table Model/View/Proxy
        self.j1939_id_table = QTableView()
        self.pgn_data_model = J1939TableModel()
        self.pgn_table_proxy = Proxy()
        self.pgn_data_model.setDataDict(self.j1939_unique_ids)
        self.j1939_id_table_columns = ["PGN","Acronym","Parameter Group Label","SA","Source","Message Count","Period (ms)","Raw Hexadecimal"]
        self.pgn_resizable_rows = [0,1,2,3,4]
        self.pgn_data_model.setDataHeader(self.j1939_id_table_columns)
        self.pgn_table_proxy.setSourceModel(self.pgn_data_model)
        self.j1939_id_table.setModel(self.pgn_table_proxy)
        self.j1939_id_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.j1939_id_table.setSortingEnabled(True)
        self.j1939_id_table.setWordWrap(False)
        
        #Create a layout for that box using a grid
        j1939_id_box_layout = QGridLayout()
        #Add the widgets into the layout
        j1939_id_box_layout.addWidget(self.j1939_id_table,0,0,1,5)
        j1939_id_box_layout.addWidget(self.add_message_button,1,0,1,1)
        j1939_id_box_layout.addWidget(self.stop_broadcast_button,1,1,1,1)
        j1939_id_box_layout.addWidget(clear_button,1,2,1,1)
       
        #setup the layout to be displayed in the box
        j1939_id_box.setLayout(j1939_id_box_layout)
        tab_layout.addWidget(j1939_id_box)
        self.j1939_tab.setLayout(tab_layout)
    
    def init_uds(self):
        logger.debug("Setting up ISO/UDS Tab.")
        self.uds_tab = QWidget()
        self.tabs.addTab(self.uds_tab,"Unified Diagnostic Services")
        tab_layout = QVBoxLayout()
        uds_box = QGroupBox("UDS Data")
        
        #Set up the Table Model/View/Proxy
        self.uds_table = QTableView()
        self.uds_data_model = J1939TableModel()
        self.uds_table_proxy = Proxy()
        self.uds_data_model.setDataDict(self.iso_recorder.uds_messages)
        self.uds_table_columns = ["Line","SA","Source","DA","SID","Service Name","Raw Hexadecimal","Meaning","Value","Units","Raw Bytes"]
        self.uds_resizable_cols = [0,1,2,3,4,5,7,8,9]
        self.uds_data_model.setDataHeader(self.uds_table_columns)
        self.uds_table_proxy.setSourceModel(self.uds_data_model)
        self.uds_table.setModel(self.uds_table_proxy)
        self.uds_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.uds_table.setSortingEnabled(True)
        self.uds_table.setWordWrap(False)
        
        #Create a layout for that box using a grid
        uds_box_layout = QGridLayout()
        #Add the widgets into the layout
        uds_box_layout.addWidget(self.uds_table,0,0,1,1)
        
        #setup the layout to be displayed in the box
        uds_box.setLayout(uds_box_layout)
        tab_layout.addWidget(uds_box)
        self.uds_tab.setLayout(tab_layout)

    def init_dtc(self):
        
        self.tabs.currentChanged.connect(self.fill_dm01_table)
        
        logger.debug("Setting up J1939 DTC User Interface Tab.")
        self.j1939_dtc_tab = QWidget()
        self.tabs.addTab(self.j1939_dtc_tab,"J1939 Diagnostic Codes")
        tab_layout = QGridLayout()
        
        #Set up the Table Model/View/Proxy for SPNs
        dm01_box = QGroupBox("J1939 Active Diagnostic Trouble Codes (DM1)")
        self.dm01_table = QTableView()
        self.dm01_data_model = J1939TableModel()
        self.dm01_table_proxy = Proxy()
        self.dm01_data_model.setDataDict(self.active_trouble_codes)
        self.dm01_table_columns = ["SA","Source","SPN","Suspect Parameter Number Label","FMI","FMI Meaning","FMI Severity","Count","Raw Hexadecimal"]
        self.dm01_data_model.setDataHeader(self.dm01_table_columns)
        self.dm01_table_proxy.setSourceModel(self.dm01_data_model)
        self.dm01_table.setModel(self.dm01_table_proxy)
        self.dm01_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dm01_table.setSortingEnabled(True)

        #Create a layout for that box using the vertical
        dm01_box_layout = QGridLayout()
        dm01_box_layout.addWidget(self.dm01_table,0,0,1,1)
        dm01_box.setLayout(dm01_box_layout)
        
        #Set up the Table Model/View/Proxy for SPNs
        dm02_box = QGroupBox("J1939 Previously Active Diagnostic Trouble Codes (DM2)")
        self.dm02_table = QTableView()
        self.dm02_data_model = J1939TableModel()
        self.dm02_table_proxy = Proxy()
        self.dm02_data_model.setDataDict(self.previous_trouble_codes)
        self.dm02_table_columns = ["SA","Source","SPN","Suspect Parameter Number Label","FMI","FMI Meaning","FMI Severity","Count","Raw Hexadecimal"]
        self.dm02_data_model.setDataHeader(self.dm02_table_columns)
        self.dm02_table_proxy.setSourceModel(self.dm02_data_model)
        self.dm02_table.setModel(self.dm02_table_proxy)
        self.dm02_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dm02_table.setSortingEnabled(True)

        self.dm02_request_button = QPushButton("Request Previously Active DTCs (DM2)")
        self.dm02_request_button.setToolTip("Send a J1939 Request Message for the DM02 message (PGN 65227).")
        self.dm02_request_button.clicked.connect(self.request_dm02)

        #Create a layout for that box using the vertical
        dm02_box_layout = QGridLayout()
        dm02_box_layout.addWidget(self.dm02_table,0,0,1,2)
        dm02_box_layout.addWidget(self.dm02_request_button,1,0,1,1)
        dm02_box.setLayout(dm02_box_layout)
        
        self.j1939_dm4_tab = QWidget()
        self.tabs.addTab(self.j1939_dm4_tab,"J1939 Freeze Frames")
        dm4_layout = QGridLayout()
        #Set up the Table Model/View/Proxy for SPNs
        dm04_box = QGroupBox("J1939 Freeze Frame Parameters (DM4)")
        self.dm04_table = QTableView()
        self.dm04_data_model = J1939TableModel()
        self.dm04_table_proxy = Proxy()
        self.dm04_data_model.setDataDict(self.freeze_frame)
        self.dm04_table_columns = ["SA","Source","SPN","Suspect Parameter Number Label","FMI","FMI Meaning","FMI Severity","Count","Freeze Frame Data","Raw Hexadecimal"]
        self.dm04_data_model.setDataHeader(self.dm04_table_columns)
        self.dm04_table_proxy.setSourceModel(self.dm04_data_model)
        self.dm04_table.setModel(self.dm04_table_proxy)
        self.dm04_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.dm04_table.setSortingEnabled(True)
        self.dm04_request_button = QPushButton("Request Freeze Frame Parameters")
        self.dm04_request_button.setToolTip("Send a J1939 Request Message for the DM04 message (PGN 65229).")
        self.dm04_request_button.clicked.connect(self.request_dm04)

        #Create a layout for that box using the vertical
        dm04_box_layout = QGridLayout()
        dm04_box_layout.addWidget(self.dm04_table,0,0,1,2)
        dm04_box_layout.addWidget(self.dm04_request_button,1,0,1,1)
        dm04_box.setLayout(dm04_box_layout)
        
        
        #setup the layout to be displayed in the box
        tab_layout.addWidget(dm01_box,0,0,1,1)
        tab_layout.addWidget(dm02_box,1,0,1,1)
        dm4_layout.addWidget(dm04_box,0,0,1,1)


        self.j1939_dtc_tab.setLayout(tab_layout)
        self.j1939_dm4_tab.setLayout(dm4_layout)
    
    def init_spn(self):
        
        self.tabs.currentChanged.connect(self.fill_spn_table)
        
        logger.debug("Setting up J1939 SPN User Interface Tab.")
        self.j1939_spn_tab = QWidget()
        self.tabs.addTab(self.j1939_spn_tab,"J1939 SPNs")
        tab_layout = QVBoxLayout()
        self.spn_table = QTableWidget()
        spn_box = QGroupBox("J1939 Suspect Parameter Numbers and Values")
        
        #Set up the Table Model/View/Proxy for SPNs
        self.spn_table = QTableView()
        self.spn_data_model = J1939TableModel()
        self.spn_table_proxy = Proxy()
        self.spn_data_model.setDataDict(self.unique_spns)
        self.spn_table_columns = ["Acronym","PGN","SA","Source","SPN","Suspect Parameter Number Label","Value","Units","Meaning"]
        self.spn_resizable_rows = [0,1,2,4,5,6,7,8]
        self.spn_data_model.setDataHeader(self.spn_table_columns)
        self.spn_table_proxy.setSourceModel(self.spn_data_model)
        self.spn_table.setModel(self.spn_table_proxy)
        self.spn_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.spn_table.setSortingEnabled(True)
        self.spn_table.setWordWrap(False)

        #Create a layout for that box using the vertical
        spn_box_layout = QGridLayout()
        spn_box_layout.addWidget(self.spn_table,0,0,1,1)
        
        #setup the layout to be displayed in the box
        spn_box.setLayout(spn_box_layout)
        tab_layout.addWidget(spn_box)
        self.j1939_spn_tab.setLayout(tab_layout)
    
    def request_dm04(self):
        for i in range(3):
            time.sleep(.1)
            self.root.send_j1939_request(65229)
        logger.info("User initiated request for DM04.")

    def request_dm02(self):
        for i in range(3):
            time.sleep(.1)
            self.root.send_j1939_request(65227)
        logger.info("User initiated request for DM02.")
    
    def fill_uds_table(self):
        #self.root.data_package["UDS Messages"].update(self.iso_recorder.uds_messages)
        if self.tabs.currentIndex() == self.tabs.indexOf(self.uds_tab):
            if len(self.iso_recorder.uds_messages) > self.previous_uds_length:
                self.previous_uds_length = len(self.iso_recorder.uds_messages)
                self.uds_data_model.aboutToUpdate()
                self.uds_data_model.setDataDict(self.iso_recorder.uds_messages)
                self.uds_data_model.signalUpdate()
                self.uds_table.resizeRowsToContents()
                for r in self.uds_resizable_cols:
                    self.uds_table.resizeColumnToContents(r)
                self.uds_table.scrollToBottom()

    def fill_dm01_table(self):
        #if self.tabs.currentIndex() == self.tabs.indexOf(self.j1939_dtc_tab):
        self.dm01_data_model.aboutToUpdate()
        self.dm01_data_model.signalUpdate()
        self.dm01_table.resizeColumnsToContents()
        self.dm01_table.resizeRowsToContents()
        self.root.data_package["Diagnostic Codes"]["DM01"] = self.active_trouble_codes

    def fill_dm02_table(self):
        #if self.tabs.currentIndex() == self.tabs.indexOf(self.j1939_dtc_tab):
        self.dm02_data_model.aboutToUpdate()
        self.dm02_data_model.signalUpdate()
        self.dm02_table.resizeColumnsToContents()
        self.dm02_table.resizeRowsToContents()
        self.root.data_package["Diagnostic Codes"]["DM02"] = self.previous_trouble_codes


    def fill_dm04_table(self):
        #if self.tabs.currentIndex() == self.tabs.indexOf(self.j1939_dm04_tab):
        self.dm04_data_model.aboutToUpdate()
        self.dm04_data_model.signalUpdate()
        self.dm04_table.resizeColumnsToContents()
        self.dm04_table.resizeRowsToContents()
        #for row in range(self.dm04_data_model.rowCount()):
        #    self.dm04_table.resizeRowToContents(row)
        self.root.data_package["Diagnostic Codes"]["DM04"] = self.freeze_frame

    def fill_spn_table(self):
        if self.tabs.currentIndex() == self.tabs.indexOf(self.j1939_spn_tab):
            if len(self.unique_spns) > self.previous_spn_length:
                self.previous_spn_length = len(self.unique_spns)
                self.spn_data_model.aboutToUpdate()
                self.spn_data_model.signalUpdate()
                self.spn_table.resizeRowsToContents()
                for r in self.spn_resizable_rows:
                    self.spn_table.resizeColumnToContents(r)
        #self.spn_table.scrollToBottom()

    def clear_j1939_table(self):

        self.pgn_data_model.beginResetModel()
        self.j1939_unique_ids = OrderedDict()
        self.pgn_data_model.setDataDict(self.j1939_unique_ids)
        self.pgn_data_model.endResetModel()
        
        self.spn_data_model.beginResetModel()
        self.unique_spns = OrderedDict()
        self.spn_data_model.setDataDict(self.unique_spns)
        self.spn_data_model.endResetModel()
        
        self.dm01_data_model.beginResetModel()
        self.active_trouble_codes = {}
        self.dm01_data_model.setDataDict(self.active_trouble_codes)
        self.dm01_data_model.endResetModel()
        
        self.dm02_data_model.beginResetModel()
        self.previous_trouble_codes = {}
        self.dm02_data_model.setDataDict(self.previous_trouble_codes)
        self.dm02_data_model.endResetModel()
        
        self.dm04_data_model.beginResetModel()
        self.freeze_frame = {}
        self.dm04_data_model.setDataDict(self.freeze_frame)
        self.dm04_data_model.endResetModel()

        self.uds_data_model.beginResetModel()
        self.iso_recorder.uds_messages = OrderedDict()
        self.uds_data_model.setDataDict(self.iso_recorder.uds_messages)
        self.uds_data_model.endResetModel()
        
    def fill_j1939_table(self, j1939_buffer):
        #See The J1939 Message from RP1210_ReadMessage in RP1210
        current_time = j1939_buffer[0]
        rx_buffer = j1939_buffer[1]
        try:
            vda_time = struct.unpack(">L", rx_buffer[0:4])[0]
            pgn = rx_buffer[5] + (rx_buffer[6] << 8) + (rx_buffer[7] << 16)
            pri = rx_buffer[8] # how/priority
            sa = rx_buffer[9] #Source Address
            da = rx_buffer[10] #Destination Address
        except (struct.error, IndexError):
            return

        if pgn == 0xDA00: #ISO
            self.iso_queue.put((pgn, pri, sa, da, rx_buffer[11:]))
            self.iso_recorder.read_message(True)
            self.root.data_package["UDS Messages"].update(self.iso_recorder.uds_messages)
            return
        
        if rx_buffer[4] == 1: #Echo message
            # Return when the VDA is the one that sent the message. 
            # The message gets logged, but not displayed in the table
            return 

        if pgn in self.pgns_to_not_decode:
            # Return when we aren't interested in the data.
            return

        pgn_key = repr((pgn,sa))
        source_key = "{} on J1939".format(self.get_sa_name(sa))
        if sa not in self.battery_potential.keys():
            self.battery_potential[sa] = []
            logger.debug("Set battery potential for SA {} to an empty list.".format(sa))

        if sa not in self.speed_record.keys():
            self.speed_record[sa] = []
            logger.debug("Set speed record for SA {} to an empty list.".format(sa))

        if sa not in self.root.source_addresses:
        #if sa not in self.ecm_time.keys():
            #self.ecm_time[sa]=[]

            self.root.source_addresses.append(sa)
            self.root.data_package["Time Records"][source_key] = {}
            self.root.data_package["Component Information"][source_key] = {}
            self.root.data_package["ECU Time Information"][source_key] = {}
            self.root.data_package["Distance Information"][source_key] = {}
            
            logger.info("Added source address {} - {} to the list of known source addresses.".format(sa,self.get_sa_name(sa)))
        
         

        data_bytes = rx_buffer[11:]
        
        try:
            self.j1939_unique_ids[pgn_key]["Num"] += 1
            previous_data_bytes = base64.b64decode(self.j1939_unique_ids[pgn_key]["Message List"].encode('ascii'))
        except KeyError:
            previous_data_bytes = base64.b64encode(b'').decode()
            self.j1939_unique_ids[pgn_key] = {"Num": 1}
            self.pgn_rows = list(self.j1939_unique_ids.keys())
            #self.j1939_unique_ids[pgn_key]["Table Key"] = pgn_key
            self.j1939_unique_ids[pgn_key]["Start Time"] = current_time
            self.j1939_unique_ids[pgn_key]["Message Time"] = current_time
            self.j1939_unique_ids[pgn_key]["Message List"] = base64.b64encode(data_bytes).decode()
            self.j1939_unique_ids[pgn_key]["VDATime List"] = vda_time
            try:
                self.j1939_unique_ids[pgn_key]["Acronym"] = self.j1939db["J1939PGNdb"]["{}".format(pgn)]["Label"]
            except KeyError:
                self.j1939_unique_ids[pgn_key]["Acronym"] = "Unknown"
            try:
                self.j1939_unique_ids[pgn_key]["Parameter Group Label"] = self.j1939db["J1939PGNdb"]["{}".format(pgn)]["Name"]
            except KeyError:
                self.j1939_unique_ids[pgn_key]["Parameter Group Label"] = "Not Provided"
            try:
                self.j1939_unique_ids[pgn_key]["Source"] = self.j1939db["J1939SATabledb"]["{}".format(sa)]
            except KeyError:
                self.j1939_unique_ids[pgn_key]["Source"] = "Reserved"
            self.look_up_spns(pgn, sa, data_bytes)

        self.j1939_unique_ids[pgn_key]["Message Count"] = "{:12d}".format(self.j1939_unique_ids[pgn_key]["Num"])
        self.j1939_unique_ids[pgn_key]["VDATime"] = vda_time
        self.j1939_unique_ids[pgn_key]["PGN"] = "{:6d}".format(pgn)
        self.j1939_unique_ids[pgn_key]["SA"] = "{:3d}".format(sa)
        self.j1939_unique_ids[pgn_key]["Bytes"] = data_bytes
        self.j1939_unique_ids[pgn_key]["Raw Hexadecimal"] = bytes_to_hex_string(data_bytes)
        self.j1939_unique_ids[pgn_key]["Period (ms)"] = "{:10.2f}".format(1000 * (current_time - self.j1939_unique_ids[pgn_key]["Start Time"])/self.j1939_unique_ids[pgn_key]["Num"])
        
        if self.j1939_unique_ids[pgn_key]["Num"] == 1:
            #logger.debug("Adding Row to PGN Table:")
            #logger.debug(self.j1939_unique_ids[pgn_key])
            self.pgn_data_model.aboutToUpdate()
            self.pgn_data_model.setDataDict(self.j1939_unique_ids)
            self.pgn_data_model.signalUpdate()
            self.j1939_id_table.resizeRowsToContents()     
            self.j1939_id_table.scrollToBottom()
            for r in self.pgn_resizable_rows:
                self.j1939_id_table.resizeColumnToContents(r)

            QCoreApplication.processEvents()

        elif self.add_message_button.isChecked():
           
            row = self.pgn_rows.index(pgn_key)
            col = self.j1939_id_table_columns.index("Message Count")
            idx = self.pgn_data_model.index(row, col)
            entry = self.j1939_unique_ids[pgn_key]["Message Count"]
            self.pgn_data_model.setData(idx, entry)
                
            col = self.j1939_id_table_columns.index("Period (ms)")
            idx = self.pgn_data_model.index(row, col)
            entry = self.j1939_unique_ids[pgn_key]["Period (ms)"]
            self.pgn_data_model.setData(idx, entry)
            
            if not base64.b64encode(data_bytes).decode() == self.j1939_unique_ids[pgn_key]["Message List"]:
                self.j1939_unique_ids[pgn_key]["Message Time"] = current_time
                self.j1939_unique_ids[pgn_key]["Message List"] = base64.b64encode(data_bytes).decode()
                self.j1939_unique_ids[pgn_key]["VDATime List"] = vda_time
                self.look_up_spns(pgn, sa, data_bytes)

                col = self.j1939_id_table_columns.index("Raw Hexadecimal")
                idx = self.pgn_data_model.index(row, col)
                entry = self.j1939_unique_ids[pgn_key]["Raw Hexadecimal"]
                self.pgn_data_model.setData(idx, entry)
        
        # Update if something has changed or if the time or voltage PGN comes in.
        if  data_bytes != previous_data_bytes or pgn in [65254, 65271]:
            self.look_up_spns(pgn, sa, data_bytes)
            if pgn == 65254:  #Time / Date PGN    
                seconds = int(self.unique_spns[repr((959, sa))]["Value"])
                minutes = int(self.unique_spns[repr((960, sa))]["Value"])
                hours   = int(self.unique_spns[repr((961, sa))]["Value"])
                month   = int(self.unique_spns[repr((963, sa))]["Value"])
                day     = int(self.unique_spns[repr((962, sa))]["Value"])
                year    = int(self.unique_spns[repr((964, sa))]["Value"])
                time_struct = time.strptime("{:02d} {:02d} {} ".format(day, month, year) + 
                    "{:02d} {:02d} {:02d}".format(hours, minutes, seconds), "%d %m %Y %H %M %S")
            
                # Save ecm time along with PC time as a tuple
                new_ecm_time = calendar.timegm(time_struct) #Convert to UTC
                #self.ecm_time[sa].append((time.time(), new_ecm_time)) #Put into floating point UTC
                self.root.data_package["Time Records"][source_key]["Last ECM Time"] = new_ecm_time
                self.root.data_package["Time Records"][source_key]["PC Time minus ECM Time"] = time.time() - new_ecm_time

            elif pgn == 65259: #Component ID
                make   = self.unique_spns[repr((586, sa))]["Value"]
                model  = self.unique_spns[repr((587, sa))]["Value"]
                serial = self.unique_spns[repr((588, sa))]["Value"]
                unit   = self.unique_spns[repr((233, sa))]["Value"]
                self.root.data_package["Component Information"][source_key].update({"Make": make,
                                                                                    "Model":model,
                                                                                    "Serial":serial, 
                                                                                    "Unit":unit})
            elif pgn == 65260: #VIN
                VIN = self.unique_spns[repr((237, sa))]["Value"].replace(b'\x00'.decode('ascii','ignore'),'') #Take out non-printable characters
                self.root.data_package["Component Information"][source_key].update({"VIN": VIN})
            elif pgn == 65242: #Software ID
                #num_fields = self.unique_spns[repr((965, sa))]["Value"]
                software = self.unique_spns[repr((234, sa))]["Value"].replace(b'\x00'.decode('ascii','ignore'),'') #Take out non-printable characters
                self.root.data_package["Component Information"][source_key].update({"Software": software})
            elif pgn == 65265: #Cruise Control Vehcile Speed
                if "Out" not in self.unique_spns[repr((84,sa))]["Meaning"]: 
                    # The speed data is not out of range
                    #Save speed from the ECU as a tuple along with PC time.
                    self.speed_record[sa].append((time.time(), float(self.unique_spns[repr((84,sa))]["Value"]) ))
                    if len(self.speed_record[sa]) > 1000:
                        self.speed_record[sa].pop(0)
                    self.root.speed_graph.add_data(self.speed_record[sa], 
                        marker = '.', 
                        label = self.j1939_unique_ids[pgn_key]["Source"]+": SPN 84")
                    self.root.speed_graph.plot()
            elif pgn == 65271:  # Vehicle Electrical Power 
                if "Out" not in self.unique_spns[repr((168,sa))]["Meaning"]: 
                    # The voltage data is not out of range
                    #Save Battery voltage from the ECU as a tuple along with PC time.
                    self.battery_potential[sa].append((time.time(), float(self.unique_spns[repr((168,sa))]["Value"]) ))
                    if len(self.battery_potential[sa]) > 1000:
                        self.battery_potential[sa].pop(0)
                    self.root.voltage_graph.add_data(self.battery_potential[sa], 
                        marker = 'o-', 
                        label = self.j1939_unique_ids[pgn_key]["Source"]+": SPN 168")
                    self.root.voltage_graph.plot()
                    
                if "Out" not in self.unique_spns[repr((158,sa))]["Meaning"]:
                    self.battery_potential[sa].append((time.time(), float(self.unique_spns[repr((158,sa))]["Value"]) ))
                    if len(self.battery_potential[sa]) > 1000:
                        self.battery_potential[sa].pop(0)
                    self.root.voltage_graph.add_data(self.battery_potential[sa], 
                        marker = '<-', 
                        label = self.j1939_unique_ids[pgn_key]["Source"]+": SPN 158")
                    self.root.voltage_graph.plot()
            
            elif pgn == 65253:  # Engine Hours / Revolutions
                if "Out" not in self.unique_spns[repr((247,sa))]["Meaning"]: 
                    # The value is not out of range
                    val = float(self.unique_spns[repr((247,sa))]["Value"])
                    units = self.unique_spns[repr((247,sa))]["Units"]
                    self.root.data_package["ECU Time Information"][source_key].update({"Total Engine Hours of Operation":"{:0.2f} {}".format(val,units)})
            
            elif pgn == 65255:  # Vehicle Hours
                if "Out" not in self.unique_spns[repr((246,sa))]["Meaning"]: 
                    # The value is not out of range
                    val = float(self.unique_spns[repr((246,sa))]["Value"])
                    units = self.unique_spns[repr((246,sa))]["Units"]
                    self.root.data_package["ECU Time Information"][source_key].update({"Total Vehicle Hours":"{:0.2f} {}".format(val,units)})
            
            elif pgn == 65248:  # Total Vehicle Distance
                if "Out" not in self.unique_spns[repr((245,sa))]["Meaning"]: 
                    # The value is not out of range
                    val = float(self.unique_spns[repr((245,sa))]["Value"])
                    units = self.unique_spns[repr((245,sa))]["Units"]
                    self.root.data_package["Distance Information"][source_key].update({"Total Vehicle Distance":"{:0.2f} {}".format(val,units)})
            
            elif pgn == 65217:  # High Resolution Distance
                if "Out" not in self.unique_spns[repr((917,sa))]["Meaning"]: 
                    # The value is not out of range
                    val = float(self.unique_spns[repr((917,sa))]["Value"])
                    units = self.unique_spns[repr((917,sa))]["Units"]
                    if "METER" in units.upper():
                        val = val * 0.000621371192 
                        units = "miles"
                    self.root.data_package["Distance Information"][source_key].update({"High Resolution Total Vehicle Distance":"{:0.4f} {}".format(val,units)})
            
            elif pgn == 65226: # DM01
                self.dm01_data_model.aboutToUpdate()
                self.active_trouble_codes.update(self.get_DM(sa, data_bytes))
                self.dm01_data_model.setDataDict(self.active_trouble_codes)
                self.fill_dm01_table()

            elif pgn == 65227: # DM02
                self.dm02_data_model.aboutToUpdate()
                self.previous_trouble_codes.update(self.get_DM(sa, data_bytes))
                self.dm02_data_model.setDataDict(self.previous_trouble_codes)
                self.fill_dm02_table()

            elif pgn == 65229: # DM04
                logger.debug("Found DM04.")
                self.dm04_data_model.aboutToUpdate()
                self.freeze_frame.update(self.get_freeze_frame(sa, data_bytes))
                self.dm04_data_model.setDataDict(self.freeze_frame)
                self.fill_dm04_table()

        self.root.data_package["J1939 Parameter Group Numbers"].update(self.j1939_unique_ids)

    def get_freeze_frame(self, sa, data):
        idx = 0
        data_length = len(data)
        logger.debug("DM04 data length is {} bytes.".format(data_length))
        dm4_dict = {}
        while idx < data_length - 1:
            length = data[idx] + 1 #Need to include the length code.
            # SPN is Suspect Parameter Number from J1939
            # FMI is Failure Mode Indicator from J1939 docs
            # CM is conversion mode from DM01 definition in J1939-73
            # OC is the occurrence count
            SPN, FMI, CM, OC = self.get_SPN_FMI_CM_OC(data[idx + 1:idx + 5]) 
            dm_dict = self.build_dtc_dict(sa, SPN, FMI, OC, CM)
            dm_dict["Raw Hexadecimal"] = bytes_to_hex_string(data[idx:idx+length])
                            
            engine_torque_mode = self.j1939db["J1939BitDecodings"]["899"]["{:d}".format(data[idx + 5])].strip().capitalize()
            boost = "{:0.1f} psi".format(data[idx+ 6] * 0.290075476) 
            engine_speed = "{:0.3f} rpm".format(struct.unpack("<H", data[idx+7:idx+9])[0] * 0.125 )
            engine_load = "{:0.1f} %".format(data[idx+9])
            coolant_temp = "{:0.1f} deg F".format(data[idx+10] * 1.8 - 40 )
            vehicle_speed = "{:0.2f} mph".format(struct.unpack("<H", data[idx+11:idx+13])[0] * 0.00242723046875 )
            manufacture_specific = bytes_to_hex_string(data[idx+13:idx+length])
            dm_dict["Freeze Frame Data"] =  "Engine Torque Mode (SPN 899): " + engine_torque_mode + "\n"
            dm_dict["Freeze Frame Data"] += "Boost (SPN 102): " + boost + "\n"
            dm_dict["Freeze Frame Data"] += "Engine Speed (SPN 190): " + engine_speed + "\n"
            dm_dict["Freeze Frame Data"] += "Engine Load (SPN 92): " + engine_load + "\n"
            dm_dict["Freeze Frame Data"] += "Engine Coolant Temp. (SPN 110): " + coolant_temp + "\n"
            dm_dict["Freeze Frame Data"] += "Vehicle Speed (SPN 84): " + vehicle_speed + "\n"
            if length > 13:
                dm_dict["Freeze Frame Data"] += "Additional Manufacture Codes: " + manufacture_specific
                                  
            dm4_dict[(sa,idx)] = dm_dict
            idx += length

            logger.debug(dm_dict)
            logger.debug("New index is {}".format(idx))
        return dm4_dict

    def get_SPN_FMI_CM_OC(self,data):
        SPN = data[0] + data[1]*256 + ((data[2] & 0xE0) >> 5)*65536
        FMI = data[2] & 0x1F
        conversion_method = data[3] & 0x80
        occurance_count = data[3] & 0x7F
        return (SPN, FMI, conversion_method, occurance_count)
    
    def build_dtc_dict(self, sa, SPN, FMI, occurance_count, conversion_method):
        dm_dict = { "SA":"{:3d}".format(sa), 
                    "SPN": "{:5d}".format(SPN), 
                    "FMI": "{:2d}".format(FMI), 
                    "Count": "{:3d}".format(occurance_count), 
                    "CM": conversion_method}
        try:
            dm_dict["Suspect Parameter Number Label"] = self.j1939db["J1939SPNdb"]["{}".format(SPN)]["Name"]
        except KeyError:
            dm_dict["Suspect Parameter Number Label"] = "Unknown Suspect Parameter Number"
        try:
            dm_dict["Source"] = self.j1939db["J1939SATabledb"]["{}".format(sa)]
        except KeyError:
            dm_dict["Source"] = "Unknown Source"

        dm_dict["FMI Meaning"] = self.j1939db["J1939FMITabledb"]["{}".format(FMI)]["Name"]
        dm_dict["FMI Severity"] = self.j1939db["J1939FMITabledb"]["{}".format(FMI)]["Severity"]

        return dm_dict

    def get_DM(self, sa, data):
        # We will start with the third byte since the Indicators Lamps are 
        # taken care of by the SPN lookup
        dtcs = {} #list to hold all the diagnostic trouble codes
        byte_index = 2
        while byte_index < len(data):
            #SPNs are 19 bits long. See J1939-73.
            try:
                SPN, FMI, conversion_method, occurance_count = self.get_SPN_FMI_CM_OC(data[byte_index:byte_index+4])
                dtc = self.build_dtc_dict(sa, SPN, FMI, occurance_count, conversion_method)
                dtc["Raw Hexadecimal"] = bytes_to_hex_string(data[byte_index:byte_index+4])
                dtcs[repr((sa,byte_index-2))] = dtc
                byte_index += 4
            except IndexError:
                break
            
        return dtcs

    def clear_voltage_history(self):
        for key in self.battery_potential:
            self.battery_potential[key]=[]

    def look_up_spns(self, pgn, sa, data_bytes):
        try:
            spn_list = self.j1939db["J1939PGNdb"]["{}".format(pgn)]["SPNs"]
        except KeyError:
            return False #We don't have meaning for the data
        if pgn in self.pgns_to_not_decode:
            return False

        for spn in spn_list:
            spn_key = repr((spn, sa))
            if spn_key in self.unique_spns:
                spn_dict = self.unique_spns[spn_key]
            else:
                spn_dict = {}
                spn_dict["Value"] = ""
                spn_dict["Last Value"] = ""
                spn_dict["Units"] = self.j1939db["J1939SPNdb"]["{}".format(spn)]["Units"]
                spn_dict["Meaning"] = ""
                #spn_dict["Value List"] = []
                #spn_dict["Time List"] = []
                #spn_dict["Table Key"] = repr(spn_key)
                spn_dict["Acronym"] = self.j1939db["J1939PGNdb"]["{}".format(pgn)]["Label"]
                spn_dict["PGN"] = "{:6d}".format(pgn)
                spn_dict["SA"] = "{:3d}".format(sa)
                spn_dict["Source"] = self.get_sa_name(sa)
                spn_dict["SPN"] = "{:5d}".format(spn)
                spn_dict["Suspect Parameter Number Label"] = self.j1939db["J1939SPNdb"]["{}".format(spn)]["Name"]
                self.unique_spns[spn_key] = spn_dict
                #self.spn_needs_updating = True
                self.spn_data_model.aboutToUpdate()
                self.spn_data_model.setDataDict(self.unique_spns)
                self.fill_spn_table()


            spn_start = self.j1939db["J1939SPNdb"]["{}".format(spn)]["StartBit"]
            spn_length = self.j1939db["J1939SPNdb"]["{}".format(spn)]["SPNLength"]
            scale = self.j1939db["J1939SPNdb"]["{}".format(spn)]["Resolution"]
            offset = self.j1939db["J1939SPNdb"]["{}".format(spn)]["Offset"]
            high_value = self.j1939db["J1939SPNdb"]["{}".format(spn)]["OperationalHigh"]
            low_value = self.j1939db["J1939SPNdb"]["{}".format(spn)]["OperationalLow"]
            
            if pgn == 65259: # Component ID
                    comp_id_string = get_printable_chars(data_bytes)
                    comp_id_list = comp_id_string.split("*")
                    if spn == 586: # Make
                        value = comp_id_list[0]
                    elif spn == 587: # Model
                        try:
                            value = comp_id_list[1]
                        except IndexError:
                            value = ""
                    elif spn == 588: #Serial Number
                        try:
                            value = comp_id_list[2]
                        except IndexError:
                            value = ""
                    elif spn == 233: #Unit Number
                        try:
                            value = comp_id_list[3]
                        except IndexError:
                            value = ""
            elif spn_dict["Units"] == 'ASCII':
                value = get_printable_chars(data_bytes)
            
            elif scale > 0 or scale == -3:
                while (spn_start+spn_length) > 64:
                    spn_start -= 64
                    data_bytes = data_bytes[8:]
                if len(data_bytes) < 8:
                    data_bytes = bytes(list(data_bytes) + [0xFF]*(8 - len(data_bytes)))

                if spn_length <= 8:
                        fmt = "B"
                        rev_fmt = "B"
                elif spn_length <= 16:
                    fmt = ">H"
                    rev_fmt = "<H"
                elif spn_length <= 32:
                    fmt = ">L"
                    rev_fmt = "<L"
                elif spn_length <= 64:
                    fmt = ">Q"
                    rev_fmt = "<Q"
                shift = 64 - spn_start - spn_length
                
                #Create a mask one bit at a time
                try:
                    mask = 0
                    for m in range(spn_length):
                        mask += 1 << (63 - m - spn_start) 
                except ValueError:
                    logger.debug("Experienced a ValueError on the Bit Masks with SPN {}".format(spn))
                    logger.debug("mask: {:08X}".format(mask))
                    logger.debug("spn_start: {}".format(spn_start))
                    logger.debug("spn_length: {}".format(spn_length))
                    return
                if scale <= 0:
                    scale = 1
                try:
                    
                    decimal_value = struct.unpack(">Q",data_bytes[0:8])[0] & mask
                except:
                    logger.debug(traceback.format_exc())
                    return
                #the < takes care of reverse byte orders
                shifted_decimal = decimal_value >> shift
                #reverse the byte order
                reversed_decimal = struct.unpack(fmt,struct.pack(rev_fmt, shifted_decimal))[0]
                numerical_value = reversed_decimal * scale + offset
                
                # Check for out of range numbers
                if numerical_value > high_value:
                    spn_dict["Meaning"] = "Out of Range - High"
                elif numerical_value < low_value:
                    spn_dict["Meaning"] = "Out of Range - Low"
                elif spn_dict["Units"] == 'bit':
                    spn_dict["Meaning"] = self.get_j1939_bits_decoded(spn,numerical_value)
                else:
                    spn_dict["Meaning"] = ""
                
                # Display the results
                if scale >= 1 or spn in self.time_spns:
                    try:
                        value = "{:d}".format(int(numerical_value))
                    except ValueError:
                        value = "{}".format(numerical_value)
                else:
                    try:
                        value = "{:0.3f}".format(numerical_value)
                    except ValueError:
                        value = "{}".format(numerical_value)

            else: #Should not be converted to a decimal number
                value = repr(data_bytes)

            spn_dict["Value"] = value
            self.unique_spns[spn_key].update(spn_dict)
            
            if spn_dict["Value"] != self.unique_spns[spn_key]["Last Value"]: #Check to see if the SPN value changed from last time.
                self.spn_rows = list(self.unique_spns.keys())
                row = self.spn_rows.index(spn_key)
                col = self.spn_table_columns.index("Value")
                idx = self.spn_data_model.index(row, col)
                entry = str(spn_dict["Value"])
                self.spn_data_model.setData(idx, entry)
                
                col = self.spn_table_columns.index("Meaning")
                idx = self.spn_data_model.index(row, col)
                entry = str(spn_dict["Meaning"])
                self.spn_data_model.setData(idx, entry)
                self.unique_spns[spn_key]["Last Value"] = spn_dict["Value"]
            
            self.root.data_package["J1939 Suspect Parameter Numbers"].update(self.unique_spns)        
            
            #logger.debug("Updated SPN Dictionary")
            #logger.debug(self.unique_spns[spn_key])
        return True
    def get_sa_name(self, sa):
        try:
            return self.j1939db["J1939SATabledb"]["{}".format(sa)]
        except KeyError:
            return "Unknown"

    def get_j1939_bits_decoded(self, spn, value):
        try:
            return self.j1939db["J1939BitDecodings"]["{}".format(spn)]["{:d}".format(int(value))].strip().capitalize()
        except KeyError:
            return ""

    def stop_broadcast(self):
        try:
            if self.root.client_ids["J1939"] is not None and self.stop_broadcast_button.isChecked():
                    message = bytes([0, 0, 0x3f, 0x0f, 0xff, 0xff, 0xff, 0xff])
                    self.root.send_j1939_message(0xDF00, message)
        except (KeyError, AttributeError) as e:
            pass

class J1939Responder(threading.Thread):
    def __init__(self, parent,  rxqueue):
        threading.Thread.__init__(self)
        self.root = parent
        self.rxqueue = rxqueue #Sign up for a CAN queue
        self.response_dict = self.root.data_package["J1939 Parameter Group Numbers"]
        self.rx_count = 0
        self.runSignal = True
        self.pgns_to_ignore = [65254]
        
    def run(self):
        
        #clear queue
        while self.rxqueue.qsize():
            rxmessage = self.rxqueue.get()

        logger.debug("J1939Responser runSignal: {}".format(self.runSignal))
        previous_time = time.time()
        
        #DM01
        # Time period is the key, PGN is in the list
        periodic_responses_5000 = [65226,]

        while self.runSignal:
            current_time = time.time()
            
            # if (current_time - previous_time) > 5:
            #     previous_time = current_time
            #     for pgn in periodic_responses_5000:
            #         pgn_key = repr((pgn,0))
            #         try:
            #             response = hex_string_to_bytes(self.response_dict[pgn_key]["Raw Hexadecimal"])
            #         except KeyError:
            #             logger.debug("PGN {} not in data set.".format(pgn_request))
            #             continue
            #         self.root.send_j1939_message(pgn, response, DA=255, SA=0)
            #         logger.debug("{:0.0f} Sent PGN: {:X}, SA: 0, DA: 255, Bytes: {}".format(current_time,pgn,bytes_to_hex_string(response[:8])))

            # time.sleep(0.005)
            while self.rxqueue.qsize():
                
                rxmessage = self.rxqueue.get()
                if rxmessage[4] == 0 and rxmessage[7] == 0xEA: #Non-Echo Request Message
                    da_request = 0 #rxmessage[8]
                    sa_request = rxmessage[9]
                    pgn_request = struct.unpack("<L", rxmessage[10:13] +  b'\x00')[0]
                    if pgn_request in self.pgns_to_ignore:
                        continue

                    pgn_key = repr((pgn_request,da_request)) #Switch SA to DA
                    logger.debug("Received Request: {}".format(bytes_to_hex_string(rxmessage[6:])))
                    try:
                        response = hex_string_to_bytes(self.response_dict[pgn_key]["Raw Hexadecimal"])
                    except KeyError:
                        logger.debug("PGN {} not in data set.".format(pgn_request))
                        continue
                    #send_j1939_message(self, PGN, data_bytes, DA=0xff, SA=0xf9, priority=6):
                    self.root.send_j1939_message(pgn_request, response, DA=sa_request, SA=da_request)
                    logger.debug("Responsed with PGN: {:08X}, SA: {}, DA: {}, Bytes: {}".format(pgn_request,sa_request,da_request,bytes_to_hex_string(response)))

                          