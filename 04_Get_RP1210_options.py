#!/bin/env/python
# An introduction sample source code that provides RP1210 capabilities

#Import 
from PyQt5.QtWidgets import (QMainWindow,
                             QWidget, 
                             QTreeView, 
                             QMessageBox, 
                             QHBoxLayout, 
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
                             QProgressDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QIcon 

#Use ctypes to import the RP1210 DLL
from ctypes import *
from ctypes.wintypes import HWND

#Use threads to set up asynchronous communications
import threading
import queue
import time
import collections 
import sys
import struct
import json

import configparser

class RP1210ReadMessageThread(threading.Thread):
    '''This thread is designed to recieve messages from the vehicle diagnostic adapter (VDA) and put the
    data into a queue. The class arguments are as follows:
    rx_queue - A datastructure that takes the recieved message.
    RP1210_ReadMessage - a function handle to the VDA DLL.
    nClientID - this lets us know which network is being used to recieve the messages. This will likely be '''
    def __init__(self, parent, rx_queue, RP1210_ReadMessage, nClientID):
        #super().__init__()
        threading.Thread.__init__(self)
        self.root = parent
        self.rx_queue = rx_queue
        self.RP1210_ReadMessage = RP1210_ReadMessage
        self.nClientID = nClientID
        self.runSignal = True

    def run(self):
        ucTxRxBuffer = (c_char*2000)()
        NON_BLOCKING_IO = 0
        BLOCKING_IO = 1
        
        #display a valid connection upon start.
        print("Read Message Client ID: {}".format(self.nClientID))
        
        while self.runSignal:
            nRetVal = self.RP1210_ReadMessage( c_short( self.nClientID ), byref( ucTxRxBuffer ),
                                        c_short( 2000 ), c_short( BLOCKING_IO ) )
            if nRetVal > 0:
                self.rx_queue.put(ucTxRxBuffer[:nRetVal])
                #print(ucTxRxBuffer[:nRetVal])
            time.sleep(.0005)
        print("RP1210 Recieve Thread is finished.")

class RP1210():
    """A class to access RP1210 libraries for different devices."""
    def __init__(self):
       pass

    def setup_RP1210(self,dll_name,protocol,deviceID):        
        #Load the Windows Device Library
        print("Loading the {} file using the {} protocol for device {:d}".format(dll_name + ".dll", protocol, deviceID))
        try:
            RP1210DLL = windll.LoadLibrary(dll_name + ".dll")
        except Exception as e:
            print(e)
            print("\nIf RP1210 DLL fails to load, please check to be sure you are using"
                + "a 32-bit version of Python and you have the correct drivers for the VDA installed.")
            return None

        # Define windows prototype functions:
        try:
            prototype = WINFUNCTYPE(c_short, HWND, c_short, c_char_p, c_long, c_long, c_short)
            self.ClientConnect = prototype(("RP1210_ClientConnect", RP1210DLL))

            prototype = WINFUNCTYPE(c_short, c_short)
            self.ClientDisconnect = prototype(("RP1210_ClientDisconnect", RP1210DLL))

            prototype = WINFUNCTYPE(c_short, c_short,  POINTER(c_char*2000), c_short, c_short, c_short)
            self.SendMessage = prototype(("RP1210_SendMessage", RP1210DLL))

            prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*2000), c_short, c_short)
            self.ReadMessage = prototype(("RP1210_ReadMessage", RP1210DLL))

            prototype = WINFUNCTYPE(c_short, c_short, c_short, POINTER(c_char*2000), c_short)
            self.SendCommand = prototype(("RP1210_SendCommand", RP1210DLL))
        except Exception as e:
            print(e)
            print("\n Critical RP1210 functions were not able to be loaded. There is something wrong with the DLL file.")
            return None
        
        try:
            prototype = WINFUNCTYPE(c_short, c_char_p, c_char_p, c_char_p, c_char_p)
            self.ReadVersion = prototype(("RP1210_ReadVersion", RP1210DLL))
        except Exception as e:
            print(e)
        
        try:
            prototype = WINFUNCTYPE( c_short, c_short, POINTER(c_char*17), POINTER(c_char*17), POINTER(c_char*17) )
            self.ReadDetailedVersion  = prototype( ("RP1210_ReadDetailedVersion", RP1210DLL ) )
        except Exception as e:
            print(e)
            self.ReadDetailedVersion = None

        try:
            prototype = WINFUNCTYPE( c_short, c_short, c_char_p, c_short, c_short             )
            self.GetHardwareStatus = prototype( ("RP1210_GetHardwareStatus", RP1210DLL ) )
        except Exception as e:
            print(e)
            self.GetHardwareStatus = None

        try:
            prototype = WINFUNCTYPE( c_short, c_short, c_char_p                           )
            self.GetErrorMsg = prototype( ("RP1210_GetErrorMsg", RP1210DLL ) )
        except Exception as e:
            print(e)
            self.GetErrorMsg = None
        
        try:
            prototype = WINFUNCTYPE( c_short, c_void_p, c_char_p, c_short             )
            self.GetLastErrorMsg = prototype( ("RP1210_GetLastErrorMsg", RP1210DLL ) )
        except Exception as e:
            print(e)
            self.GetLastErrorMsg = None
        
        protocol_name = bytes(protocol,'ascii')
        nClientID = self.ClientConnect(HWND(None), c_short(deviceID), protocol_name, 0, 0, 0  )

        print("The Client ID is: {}".format(nClientID))
        
        if nClientID < 128:
            file_contents = {nClientID:{"dll_name":dll_name, "protocol":protocol ,"deviceID":deviceID}}
            with open("Last_RP1210_Connection.json","w") as rp1210_file:
                json.dump(file_contents, rp1210_file, sort_keys=True, indent = 4)
        
        # Set all filters to pass.  This allows messages to be read.
        RP1210_Set_All_Filters_States_to_Pass = 3 
        nRetVal = self.SendCommand(c_short(RP1210_Set_All_Filters_States_to_Pass), c_short(nClientID), None, 0)
        if nRetVal == 0 :
           print("RP1210_Set_All_Filters_States_to_Pass - SUCCESS" )
        else :
           print('RP1210_Set_All_Filters_States_to_Pass returns {:d}'.format(nRetVal))
        
        return nClientID


class SelectRP1210(QWidget):
    def __init__(self):
        super(SelectRP1210,self).__init__()

        self.setup_dialog()

    def setup_dialog(self):
        self.RP1210DLL_combo_box = QComboBox()
        RP1210_config = configparser.ConfigParser()
        RP1210_config.read("c:\\Windows\\RP121032.ini")
        self.RP1210DLL_combo_box.addItems(RP1210_config["RP1210Support"]["apiimplementations"].split(","))
        self.RP1210DLL_combo_box.activated.connect(self.continue_parsing_inis)

        idx = self.RP1210DLL_combo_box.currentIndex()
        if idx >= 0: 
            self.dll_name = self.RP1210DLL_combo_box.itemText(idx) + ".DLL"
        print(self.dll_name)
        
        v_layout = QVBoxLayout()
        v_layout.addWidget(self.RP1210DLL_combo_box)

    def  fill_vendor(self):
        pass
    def fill_device(self,vendor):
        pass
    def fill_protocol(self,vendor,protocol):
        pass    
    def continue_parsing_inis(self):
        print(self.dll_name[:-4])
        dll_config = configparser.ConfigParser()
        dll_config.read("C:/WINDOWS" + self.dll_name[:-4] + ".INI")
        print(dll_config["VendorInformation"]["Name"])  


class TUDiagnostics(QMainWindow):
    def __init__(self):
        super(TUDiagnostics,self).__init__()
        # Upon startup, open the vendor specific library. This DLL is named in the c:\Windows\RP1210.ini file
        # TODO: let the user select the RP1210 device after parsing the RP1210 options. Change this to a dialog
        # box control
        dll_name = "DGDPA5MA"
        protocol = "J1708"
        deviceID = 1
        self.RP1210 = RP1210()
        J1708_client_ID = self.RP1210.setup_RP1210(dll_name,protocol,deviceID)
        print(J1708_client_ID)

        try:
            # The json file holding the last connection of the RP1210 device is
            # a dictionary of dictionarys where the main keys are the client ids
            # and the entries are a dictionary needed for the connections. 
            # This enables us to connect 2 or more clients at once and remember.
            with open("Last_RP1210_Connection.json","r") as rp1210_file:
                file_contents = json.load(rp1210_file)

            for clientID,rp1210_settings in file_contents.items():
                dll_name = rp1210_settings["dll_name"]
                protocol = rp1210_settings["protocol"]  
                deviceID = rp1210_settings["deviceID"]
                self.setupRP1210(dll_name,protocol,deviceID)
        except Exception as e:
            print(e)
            SelectRP1210()

        self.init_ui()
        
    def init_ui(self):
        #Builds GUI

        self.setGeometry(200,200,500,500)

        #Start with a status bar
        self.statusBar().showMessage("Welcome!")
        
        #Build common menu options
        menubar = self.menuBar()
        
        #File Menu Items
        file_menu = menubar.addMenu('&File')
        open_file = QAction(QIcon(r'icons8_Open_48px_1.png'), '&Open', self)
        open_file.setShortcut('Ctrl+O')
        open_file.setStatusTip('Open new File')
        open_file.triggered.connect(self.open_file)
        file_menu.addAction(open_file)

        #RP1210 Menu Items
        rp1210_menu = menubar.addMenu('&RP1210')
        connect_rp1210 = QAction(QIcon(r'png/bug-8x.png'), '&Connect', self)
        connect_rp1210.setShortcut('Ctrl+R')
        connect_rp1210.setStatusTip('Connect Vehicle Diagnostic Adapter')
        connect_rp1210.triggered.connect(self.selectRP1210)
        rp1210_menu.addAction(connect_rp1210)

        select_rp1210 = QAction(QIcon(r'png/globe-8x.png'), 'Confi&gure...', self)
        select_rp1210.setShortcut('Ctrl+G')
        select_rp1210.setStatusTip('Select RP1210 (VDA) Device')
        select_rp1210.triggered.connect(self.selectRP1210)
        rp1210_menu.addAction(select_rp1210)

        b1 = QWidget()
        self.version_button = QPushButton(b1)
        self.version_button.setText('Display Version')
        self.version_button.clicked.connect(self.display_version)
        
        b2 = QWidget()
        self.detailed_version_button = QPushButton(b2)
        self.detailed_version_button.setText('Get Detailed Version')        
        self.detailed_version_button.clicked.connect(self.display_detailed_version)
     
        b3 = QWidget()
        self.get_vin_button = QPushButton(b3)
        self.get_vin_button.setText('Request VIN on J1939')        
        self.get_vin_button.clicked.connect(self.get_j1939_vin)
        
        
        #setup a Receive queue
        #self.rx_queue = queue.Queue()
        #self.read_message_thread = RP1210ReadMessageThread(self, self.rx_queue,self.ReadMessage,self.nClientID)
        #self.read_message_thread.setDaemon(True)
        #self.read_message_thread.start()
        #print("Started RP1210ReadMessage Thread.")
        
        self.scroll_CAN_message_button =  QCheckBox("Auto Scroll Message Window")   

        
        #Set up a Table to display recieved messages
        self.received_CAN_message_table = QTableWidget()
        
        #Set the headers
        CAN_table_columns = ["Count","PC Time","VDA Time","ID","DLC","B0","B1","B2","B3","B4","B5","B6","B7"]
        self.received_CAN_message_table.setColumnCount(len(CAN_table_columns))
        self.received_CAN_message_table.setHorizontalHeaderLabels(CAN_table_columns)
        
        #Initialize a counter
        self.received_CAN_message_count = 0
        #use this variable to run a reziser once message traffic appears
        self.received_CAN_message_table_needs_resized = True
        
        self.max_rx_messages = 10000
        self.rx_message_buffer = collections.deque(maxlen=self.max_rx_messages)
        self.max_message_table = 10000
        self.message_table_ids=collections.deque(maxlen=self.max_message_table)
        
        #table_timer = QTimer(self)
        #table_timer.timeout.connect(self.fill_table)
        #table_timer.start(20) 
        #self.fill_table()

        v_layout = QVBoxLayout()
        #Define where the widgets go in the window        
        
        v_layout.addWidget(self.version_button)
        v_layout.addWidget(self.detailed_version_button)
        v_layout.addWidget(self.get_vin_button)
        v_layout.addWidget(self.scroll_CAN_message_button)
        v_layout.addWidget(self.received_CAN_message_table)
        

        main_widget = QWidget()
        main_widget.setLayout(v_layout)
        self.setCentralWidget(main_widget)
        self.setWindowTitle('RP1210 Interface')
        self.show()
    
    def selectRP1210(self):
        print("Calling Select")
        

    def get_j1939_vin(self):
        print("This is a function call")
        pgn = 65260
        print("PGN: {:X}".format(pgn))
        b0 = pgn & 0xff
        print("b0 = {:02X}".format(b0))
        b1 = (pgn & 0xff00) >> 8
        print("b1 = {:02X}".format(b1))
        dlc = 3
        b2 = 0 #(pgn & 0xff0000) >> 16

        ucTxRxBuffer = (c_char*2000)()
        
        ucTxRxBuffer[0]=0x01 #Message type is exetended per RP1210
        ucTxRxBuffer[1]=0x18 #Priority 6
        ucTxRxBuffer[2]=0xEA #Request PGN
        ucTxRxBuffer[3]=0x00 #Destination address of Engine
        ucTxRxBuffer[4]=0xF9 #Source address of VDA
        ucTxRxBuffer[5]=b0
        ucTxRxBuffer[6]=b1
        ucTxRxBuffer[7]=b2
        
            
        return_value = self.SendMessage(c_short( self.nClientID ),
                                        byref( ucTxRxBuffer ),
                                        c_short( 8 ), 0, 0)
        print("return value: {}".format(return_value))
    def open_file(self):
        print("Open Data")  

    
    def fill_table(self):

        while self.rx_queue.qsize():
            
            #Get a message from the queue. These are raw bytes
            rxmessage = self.rx_queue.get()
            
            #Print received message to the console for debugging
            
            
            if self.scroll_CAN_message_button.isChecked():
                self.received_CAN_message_table.scrollToBottom()
            
            #Parse CAN into tables
            #Get the message counter for the session 
            #Assignment: add a button that resets the counter.
            self.received_CAN_message_count += 1
            timestamp = time.time() #PC Time
            vda_timestamp = struct.unpack(">L",rxmessage[0:4])[0] # Vehicle Diagnostic Adapter Timestamp 
            extended = rxmessage[0:4]
            if extended:
                can_id = struct.unpack(">L",rxmessage[5:9])[0]
                databytes = rxmessage[9:]
            else:
                can_id = struct.unpack(">L",rxmessage[5:7])[0]
                databytes = rxmessage[7:]
            dlc = len(databytes)
            
            if (can_id & 0xFF0000) == 0xEC0000:
                if rxmessage[-3] == 0xEC and rxmessage[-2] == 0xFE:
                    print("Found a transport layer connection management message for VIN")
                    message_text = ""
                    for b in rxmessage:
                        message_text+="{:02X} ".format(b)
                    print(message_text)
            #Insert a new row:
            row_count = self.received_CAN_message_table.rowCount()
            self.received_CAN_message_table.insertRow(row_count)
            last_row = row_count
            
            #Populate the row with data
            self.received_CAN_message_table.setItem(last_row,0,
                 QTableWidgetItem("{}".format(self.received_CAN_message_count)))
            
            self.received_CAN_message_table.setItem(last_row,1,
                 QTableWidgetItem("{:0.6f}".format(timestamp)))
            
            self.received_CAN_message_table.setItem(last_row,2,
                 QTableWidgetItem("{:0.3f}".format(vda_timestamp* 0.001))) #Figure out what the multiplier is for the time stamp
            
            self.received_CAN_message_table.setItem(last_row,3,
                 QTableWidgetItem("{:08X}".format(can_id)))
            #Assignment: Make the ID format conditional on 29 or 11 bit IDs
            
            self.received_CAN_message_table.setItem(last_row,4,
                 QTableWidgetItem("{}".format(dlc)))
            
            col=5
            for b in databytes:
                self.received_CAN_message_table.setItem(last_row,col,
                    QTableWidgetItem("{:02X}".format(b)))
                col+=1

            
            if self.received_CAN_message_count < 100:
                self.received_CAN_message_table.resizeColumnsToContents()    
                #Assignment: Change this automatic resizer to a button.
            
    def display_version(self):
        
        chDLLMajorVersion    = (c_char)()
        chDLLMinorVersion    = (c_char)()
        chAPIMajorVersion    = (c_char)()
        chAPIMinorVersion    = (c_char)()

        self.ReadVersion( byref( chDLLMajorVersion ), byref( chDLLMinorVersion ), byref( chAPIMajorVersion ), byref( chAPIMinorVersion  ) )

        print('Successfully Read DLL and API Versions.')
        DLLMajor = chDLLMajorVersion.value.decode('ascii')
        DLLMinor = chDLLMinorVersion.value.decode('ascii')
        APIMajor = chAPIMajorVersion.value.decode('ascii')
        APIMinor = chAPIMinorVersion.value.decode('ascii')
        print("DLL Major Version: {}".format(DLLMajor))
        print("DLL Minor Version: {}".format(DLLMinor))
        print("API Major Version: {}".format(APIMajor))
        print("API Minor Version: {}".format(APIMinor))

        self.result1 = QMessageBox()
        self.result1.setText('Driver software versions are as follows:\nDLL Major Version: %r' %DLLMajor + '\nDLL Minor Version: %r' %DLLMinor + '\nAPI Major Version: %r' %APIMajor + '\nAPI Minor Version: %r' %APIMinor)
        self.result1.setIcon(QMessageBox.Information)
        self.result1.setWindowTitle('RP1210 Version Information')
        self.result1.setStandardButtons(QMessageBox.Ok)

        self.result1.show()

    def display_detailed_version(self, result2):
              
        chAPIVersionInfo    = (c_char*17)()
        chDLLVersionInfo    = (c_char*17)()
        chFWVersionInfo     = (c_char*17)()
        nRetVal = self.ReadDetailedVersion( c_short( self.nClientID ), byref( chAPIVersionInfo ), byref( chDLLVersionInfo ), byref( chFWVersionInfo ) )

        self.result2 = QMessageBox()
        self.result2.setIcon(QMessageBox.Information)
        self.result2.setWindowTitle('RP1210 Detailed Version Information')
        self.result2.setStandardButtons(QMessageBox.Ok)
        
        if nRetVal == 0 :
           print('Congratulations! You have connected to a VDA! No need to check your USB connection.')
           DLL = chDLLVersionInfo.value
           API = chAPIVersionInfo.value
           FW = chAPIVersionInfo.value
           self.result2.setText('Congratulations!\nYou have connected to a vehicle diagnostic adapter (VDA)!\nNo need to check your USB connection.\nDLL = {}\nAPI = {}\nFW = {}'.format(DLL.decode('ascii'),API.decode('ascii'),FW.decode('ascii')))
                       
        else :   
           print("ReadDetailedVersion fails with a return value of  %i" %nRetVal )
           self.result2.setText('RP1210 Detailed Version Information:\nERROR %i' %nRetVal)
           
        self.result2.show()
            
if __name__ == '__main__':

    app = QApplication(sys.argv)
    execute = TUDiagnostics()
    sys.exit(app.exec_())
    print(execute.ClientDisconnect())

