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


class RP1210(QMainWindow):

    def __init__(self):
        super().__init__()

        # Upon startup, open the vendor specific library. This DLL is named in the c:\Windows\RP1210.ini file
        # TODO: let the user select the RP1210 device after parsing the RP1210 options. Change this to a dialog
        # box control
        self.RP1210_config = configparser.ConfigParser()
        self.dll_name="DGDPA5MA.DLL"
        self.setupRP1210(protocol = "CAN")

        

        self.init_ui()
                

    def setupRP1210(self,protocol = "J1939:Channel=1",deviceID = 1):

        #Load the Windows Device Library
        RP1210DLL = windll.LoadLibrary( self.dll_name )
                
        # Define windows prototype functions:
        # typedef short (WINAPI *fxRP1210_ClientConnect)       ( HWND, short, char *, long, long, short );
        prototype                   = WINFUNCTYPE( c_short, HWND, c_short, c_char_p, c_long, c_long, c_short)
        self.ClientConnect        = prototype( ( "RP1210_ClientConnect", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_ClientDisconnect)    ( short                                  );
        prototype                   = WINFUNCTYPE( c_short, c_short )
        self.ClientDisconnect     = prototype( ( "RP1210_ClientDisconnect", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_SendMessage)         ( short, char*, short, short, short      );
        prototype                   = WINFUNCTYPE( c_short, c_short,  POINTER( c_char*2000 ), c_short, c_short, c_short      )
        self.SendMessage          = prototype( ("RP1210_SendMessage", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_ReadMessage)         ( short, char*, short, short             );
        prototype                   = WINFUNCTYPE( c_short, c_short, POINTER( c_char*2000 ), c_short, c_short             )
        self.ReadMessage          = prototype( ("RP1210_ReadMessage", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_SendCommand)         ( short, short, char*, short             );
        prototype                   = WINFUNCTYPE( c_short, c_short, c_short, POINTER( c_char*2000 ), c_short             )
        self.SendCommand          = prototype( ("RP1210_SendCommand", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_ReadVersion)         ( char*, char*, char*, char*             );
        prototype                   = WINFUNCTYPE( c_short, c_char_p, c_char_p, c_char_p, c_char_p             )
        self.ReadVersion          = prototype( ("RP1210_ReadVersion", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_ReadDetailedVersion) ( short, char*, char*, char*             );
        prototype                   = WINFUNCTYPE( c_short, c_short, POINTER(c_char*17), POINTER(c_char*17), POINTER(c_char*17) )
        self.ReadDetailedVersion  = prototype( ("RP1210_ReadDetailedVersion", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_GetHardwareStatus)   ( short, char*, short, short             );
        prototype                   = WINFUNCTYPE( c_short, c_short, c_char_p, c_short, c_short             )
        self.GetHardwareStatus    = prototype( ("RP1210_GetHardwareStatus", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_GetErrorMsg)         ( short, char*                           );
        prototype                   = WINFUNCTYPE( c_short, c_short, c_char_p                           )
        self.GetErrorMsg          = prototype( ("RP1210_GetErrorMsg", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_GetLastErrorMsg)     ( short, int *, char*, short             );
        prototype                   = WINFUNCTYPE( c_short, c_void_p, c_char_p, c_short             )
        self.GetLastErrorMsg      = prototype( ("RP1210_GetLastErrorMsg", RP1210DLL ) )

        print( "Attempting connect to DLL [%s], DeviceID [%d]" %( self.dll_name, deviceID ) )

        self.szProtocolName = bytes(protocol,'ascii')
        self.nClientID = self.ClientConnect( HWND(None), c_short( deviceID ), self.szProtocolName, 0, 0, 0  )

        print('The Client ID is: %i' %self.nClientID)

        # Set all filters to pass.  This allows messages to be read.
        RP1210_Set_All_Filters_States_to_Pass = 3 
        nRetVal = self.SendCommand( c_short( RP1210_Set_All_Filters_States_to_Pass ), c_short( self.nClientID ), None, 0 )

        if nRetVal == 0 :
           print("RP1210_Set_All_Filters_States_to_Pass - SUCCESS" )
        else :
           print('RP1210_Set_All_Filters_States_to_Pass returns %i' %nRetVal )

    def init_ui(self):
        #Builds GUI

        self.setGeometry(200,200,500,500)

        #Start with a status bar
        self.statusBar().showMessage(self.dll_name)
        
        #Build common menu options
        menubar = self.menuBar()
        
        #File Menu Items
        file_menu = menubar.addMenu('&File')
        open_file = QAction(QIcon(r'icons8_Open_48px_1.png'), '&Open', self)
        open_file.setShortcut('Ctrl+O')
        open_file.setStatusTip('Open new File')
        open_file.triggered.connect(self.open_data)
        file_menu.addAction(open_file)

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
        self.rx_queue = queue.Queue()
        self.read_message_thread = RP1210ReadMessageThread(self, self.rx_queue,self.ReadMessage,self.nClientID)
        self.read_message_thread.setDaemon(True)
        self.read_message_thread.start()
        print("Started RP1210ReadMessage Thread.")
        
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
        
        table_timer = QTimer(self)
        table_timer.timeout.connect(self.fill_table)
        table_timer.start(20) 
        self.fill_table()

        
        #Define where the widgets go in the window        
        v_layout = QVBoxLayout()
        
        v_layout.addWidget(self.version_button)
        v_layout.addWidget(self.detailed_version_button)
        v_layout.addWidget(self.get_vin_button)
        v_layout.addWidget(self.scroll_CAN_message_button)
        v_layout.addWidget(self.received_CAN_message_table)

        self.setLayout(v_layout)

        main_widget = QWidget()
        main_widget.setLayout(v_layout)
        self.setCentralWidget(main_widget)
        self.setWindowTitle('RP1210 Interface')
        self.show()
        
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
    def open_data(self):
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
    execute = RP1210()
    sys.exit(app.exec_())
    print(execute.ClientDisconnect())

