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
                             QDialog,
                             QDialogButtonBox,
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

from RP1210Constants import *

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

class RP1210Class():
    """A class to access RP1210 libraries for different devices."""
    def __init__(self,dll_name,protocol,deviceID):        
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
        self.nClientID = self.ClientConnect(HWND(None), c_short(deviceID), protocol_name, 0, 0, 0  )

        print("The Client ID is: {}".format(self.nClientID))

class SelectRP1210(QDialog):
    def __init__(self):
        super(SelectRP1210,self).__init__()
        RP1210_config = configparser.ConfigParser()
        RP1210_config.read("c:/Windows/RP121032.ini")
        self.apis = sorted(RP1210_config["RP1210Support"]["apiimplementations"].split(","))
        self.current_api_index = 0
        print("Current RP1210 APIs installed are: " + ", ".join(self.apis))
        self.dll_name = None
        self.setup_dialog()
        self.setWindowTitle("Select RP1210")
        self.setWindowModality(Qt.ApplicationModal)
        self.exec_()

    def setup_dialog(self):
        
        vendor_label = QLabel("System RP1210 Vendors:")
        self.vendor_combo_box = QComboBox()
        self.vendor_combo_box.setInsertPolicy(QComboBox.NoInsert)
        self.vendor_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.vendor_combo_box.activated.connect(self.fill_device)

        device_label = QLabel("Available RP1210 Vendor Devices:")
        self.device_combo_box = QComboBox()
        self.device_combo_box.setInsertPolicy(QComboBox.NoInsert)
        self.device_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.device_combo_box.activated.connect(self.fill_protocol)
        
        protocol_label = QLabel("Available Device Protocols:")
        self.protocol_combo_box = QComboBox()
        self.protocol_combo_box.setInsertPolicy(QComboBox.NoInsert)
        self.protocol_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        #self.protocol_combo_box.activated.connect(self.accept)
        

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.accepted.connect(self.connect_RP1210)
        self.rejected.connect(self.reject_RP1210)
        
        try:
            with open("RP1210_selection.txt","r") as selection_file:
                previous_selections = selection_file.read()
        except FileNotFoundError:
            print("RP1210_selection.txt not Found!")
            previous_selections = "0,0,0"
        self.selection_index = previous_selections.split(',')

        self.fill_vendor()

        self.v_layout = QVBoxLayout()
        self.v_layout.addWidget(vendor_label)
        self.v_layout.addWidget(self.vendor_combo_box)
        self.v_layout.addWidget(device_label)
        self.v_layout.addWidget(self.device_combo_box)
        self.v_layout.addWidget(protocol_label)
        self.v_layout.addWidget(self.protocol_combo_box)
        self.v_layout.addWidget(self.buttons)

        self.setLayout(self.v_layout)

    def fill_vendor(self):
        self.vendor_combo_box.clear()
        vendor_combo_box_entries = []
        self.vendor_configs = {} 
        for api_string in self.apis:
            self.vendor_configs[api_string] = configparser.ConfigParser()
            try:
                self.vendor_configs[api_string].read("c:/Windows/" + api_string + ".ini")
                #print("api_string = {}".format(api_string))
                #print("The api ini file has the following sections:")
                #print(vendor_config.sections())
                vendor_name = self.vendor_configs[api_string]['VendorInformation']['name']
                #print(vendor_name)
                if vendor_name is not None:
                    vendor_combo_box_entries.append("{:8} - {}".format(api_string,vendor_name))
                else:
                    self.apis.remove(api_string) #remove faulty/corrupt api_string   
            except Exception as e:
                print(e)
                self.apis.remove(api_string) #remove faulty/corrupt api_string 

        self.vendor_combo_box.addItems(vendor_combo_box_entries)
        try:
            self.vendor_combo_box.setCurrentIndex(int(self.selection_index[0]))
        except:
            pass

        self.fill_device()
    
    def fill_device(self):
        idx = self.vendor_combo_box.currentIndex()
        self.api_string = self.vendor_combo_box.itemText(idx).split("-")[0].strip()
        self.device_combo_box.clear()
        for key in self.vendor_configs[self.api_string]:
            if "DeviceInformation" in key:
                try:
                    device_id = self.vendor_configs[self.api_string][key]["DeviceID"]
                except KeyError:
                    device_id = None
                    print("No Device ID for {} in {}.ini".format(key,self.api_string))
                try:
                    device_description = self.vendor_configs[self.api_string][key]["DeviceDescription"]
                except KeyError:
                    device_description = "No device description available"
                try:
                    device_MultiCANChannels = self.vendor_configs[self.api_string][key]["MultiCANChannels"]
                except KeyError:
                    device_MultiCANChannels = None
                try:
                    device_MultiJ1939Channels = self.vendor_configs[self.api_string][key]["MultiJ1939Channels"]
                except KeyError:
                    device_MultiJ1939Channels = None
                try:
                    device_MultiISO15765Channels = self.vendor_configs[self.api_string][key]["MultiISO15765Channels"]
                except KeyError:
                    device_MultiISO15765Channels = None
                try:
                    device_name = self.vendor_configs[self.api_string][key]["DeviceName"]
                except KeyError:
                    device_name = "Device name not provided"
                device_combo_box_entry = "{}: {}, {}".format(device_id,device_name,device_description)
                self.device_combo_box.addItem(device_combo_box_entry)
        try:
            self.device_combo_box.setCurrentIndex(int(self.selection_index[1]))
        except:
            pass

        self.fill_protocol()

    def fill_protocol(self):
        idx = self.device_combo_box.currentIndex()
        self.device_id = self.device_combo_box.itemText(idx).split(":")[0].strip()
        self.protocol_combo_box.clear()
        for key in self.vendor_configs[self.api_string]:
            if "ProtocolInformation" in key:
                try:
                    protocol_string = self.vendor_configs[self.api_string][key]["ProtocolString"]
                except KeyError:
                    protocol_string = None
                    print("No Protocol Name for {} in {}.ini".format(key,self.api_string))
                try:
                    protocol_description = self.vendor_configs[self.api_string][key]["ProtocolDescription"]
                except KeyError:
                    protocol_description = "No protocol description available"
                try:
                    protocol_speed = self.vendor_configs[self.api_string][key]["ProtocolSpeed"]
                except KeyError:
                    protocol_speed = "No Speed Specified"
                try:
                    protocol_params = self.vendor_configs[self.api_string][key]["ProtocolParams"]
                except KeyError:
                    protocol_params = ""
                
                devices = self.vendor_configs[self.api_string][key]["Devices"].split(',')
                if self.device_id in devices and protocol_string is not None:
                    device_combo_box_entry = "{}: {}".format(protocol_string,protocol_description)
                    self.protocol_combo_box.addItem(device_combo_box_entry)
        try:
            self.protocol_combo_box.setCurrentIndex(int(self.selection_index[2]))
        except:
            pass
   
    def connect_RP1210(self):
        print("Accepted Dialog OK")
        vendor_index = self.vendor_combo_box.currentIndex()
        device_index = self.device_combo_box.currentIndex()
        protocol_index = self.protocol_combo_box.currentIndex()
        with open("RP1210_selection.txt","w") as selection_file:
            selection_file.write("{},{},{}".format(vendor_index,device_index,protocol_index))
        self.dll_name = self.vendor_combo_box.itemText(vendor_index).split("-")[0].strip()
        self.deviceID = int(self.device_combo_box.itemText(device_index).split(":")[0].strip())
        self.protocol = self.protocol_combo_box.itemText(protocol_index).split(":")[0].strip()
        file_contents={"dll_name":self.dll_name,"protocol":self.deviceID,"deviceID":self.protocol}
        with open("Last_RP1210_Connection.json","w") as rp1210_file:
                 json.dump(file_contents,rp1210_file)
    
    def reject_RP1210(self):
        self.dll_name = None
        self.protocol = None
        self.deviceID = None

class TUDiagnostics(QMainWindow):
    def __init__(self):
        super(TUDiagnostics,self).__init__()
        self.setGeometry(200,200,700,500)
        self.init_ui()
        self.selectRP1210(automatic=True)
        
        

    def init_ui(self):
        #Builds GUI

        

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
        connect_rp1210 = QAction(QIcon(r'icons/bug-8x.png'), '&Connect', self)
        connect_rp1210.setShortcut('Ctrl+R')
        connect_rp1210.setStatusTip('Connect Vehicle Diagnostic Adapter')
        connect_rp1210.triggered.connect(self.selectRP1210)
        rp1210_menu.addAction(connect_rp1210)

        version_button = QPushButton('Display Version')
        version_button.clicked.connect(self.display_version)
        
        detailed_version_button = QPushButton('Get Detailed Version')        
        detailed_version_button.clicked.connect(self.display_detailed_version)
     
        get_vin_button = QPushButton('Request VIN on J1939')        
        get_vin_button.clicked.connect(self.get_j1939_vin)
        
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
        
        
        #self.fill_table()

        v_layout = QVBoxLayout()
        #Define where the widgets go in the window        
        
        v_layout.addWidget(version_button)
        v_layout.addWidget(detailed_version_button)
        v_layout.addWidget(get_vin_button)
        v_layout.addWidget(self.scroll_CAN_message_button)
        v_layout.addWidget(self.received_CAN_message_table)
        

        main_widget = QWidget()
        main_widget.setLayout(v_layout)
        self.setCentralWidget(main_widget)
        self.setWindowTitle('RP1210 Interface')
        self.show()
    
    def selectRP1210(self,automatic=False):
        if automatic:
            try:
                # The json file holding the last connection of the RP1210 device is
                # a dictionary of dictionarys where the main keys are the client ids
                # and the entries are a dictionary needed for the connections. 
                # This enables us to connect 2 or more clients at once and remember.
                with open("Last_RP1210_Connection.json","r") as rp1210_file:
                    file_contents = json.load(rp1210_file)
                for clientID,select_dialog in file_contents.items():
                    dll_name = select_dialog["dll_name"]
                    protocol = select_dialog["protocol"]
                    deviceID = select_dialog["deviceID"]
                    self.RP1210 = RP1210Class(dll_name,protocol,deviceID)
                    
            except Exception as e:
                print(e)
                selection = SelectRP1210()
                dll_name = selection.dll_name
                protocol = selection.protocol
                deviceID = selection.deviceID
                self.RP1210 = RP1210Class(dll_name,protocol,deviceID)

        else:
            selection = SelectRP1210()
            dll_name = selection.dll_name
            protocol = selection.protocol
            deviceID = selection.deviceID
            self.RP1210 = RP1210Class(dll_name,protocol,deviceID)

        
        self.statusBar().showMessage("Connected to {}".format(dll_name))
        self.nClientID = self.RP1210.nClientID

        while self.nClientID > 127:
            question_text = "The Client ID is: {}: {}.\nDo you want to try again?".format(self.nClientID,
                                                                                          RP1210Errors[self.nClientID])
            reply = QMessageBox.question(self, "Connection Issue",
                                                question_text,
                                                QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.selectRP1210()
            else:
                return

        if self.nClientID < 128: 
            file_contents = {self.nClientID:{"dll_name":dll_name,
                                             "protocol":protocol,
                                             "deviceID":deviceID}
                                            }
            with open("Last_RP1210_Connection.json","w") as rp1210_file:
                json.dump(file_contents, rp1210_file, sort_keys=True, indent = 4)
        
            # Set all filters to pass.  This allows messages to be read.
            # Constants are defined in an included file
            nRetVal = self.RP1210.SendCommand(c_short(RP1210_Set_All_Filters_States_to_Pass), c_short(self.nClientID), None, 0)
            if nRetVal == 0:
                print("RP1210_Set_All_Filters_States_to_Pass - SUCCESS")
            else :
                print('RP1210_Set_All_Filters_States_to_Pass returns {:d}: {}'.format(nRetVal,RP1210Errors[nRetVal]))
                return

            #setup a Receive queue. This keeps the GUI responsive and enables messages to be received.
            self.rx_queue = queue.Queue()
            self.read_message_thread = RP1210ReadMessageThread(self, self.rx_queue,self.RP1210.ReadMessage,self.nClientID)
            self.read_message_thread.setDaemon(True) #needed to close the thread when the application closes.
            self.read_message_thread.start()
            print("Started RP1210ReadMessage Thread.")
            
            self.statusBar().showMessage("{} connected using {}".format(protocol,dll_name))
            
            #set up an event timer to fill a table of received messages
            table_timer = QTimer(self)
            table_timer.timeout.connect(self.fill_table)
            table_timer.start(20)
        else:
            print("The Client ID is: {}: {}.format(self.nClientID,RP1210Errors[self.nClientID])")

    def get_j1939_vin(self):
        """An Example of requesting a VIN over J1939"""
        pgn = 65260
        print("PGN: {:X}".format(pgn))
        b0 = pgn & 0xff
        print("b0 = {:02X}".format(b0))
        b1 = (pgn & 0xff00) >> 8
        print("b1 = {:02X}".format(b1))
        dlc = 3
        b2 = 0 #(pgn & 0xff0000) >> 16

        #initialize the buffer
        ucTxRxBuffer = (c_char*2000)()
        
        ucTxRxBuffer[0]=0x01 #Message type is extended per RP1210
        ucTxRxBuffer[1]=0x18 #Priority 6
        ucTxRxBuffer[2]=0xEA #Request PGN
        ucTxRxBuffer[3]=0x00 #Destination address of Engine
        ucTxRxBuffer[4]=0xF9 #Source address of VDA
        ucTxRxBuffer[5]=b0
        ucTxRxBuffer[6]=b1
        ucTxRxBuffer[7]=b2
        
        msg_len = 8
            
        return_value = self.RP1210.SendMessage(c_short( self.nClientID ),
                                        byref( ucTxRxBuffer ),
                                        c_short( msg_len ), 0, 0)
        print("return value: {}: {}".format(return_value,RP1210Errors[return_value]))
    

    def open_file(self):
        print("Open Data")  

    
    def fill_table(self):
        #check to see if something is in the queue
        while self.rx_queue.qsize():
            
            #Get a message from the queue. These are raw bytes
            rxmessage = self.rx_queue.get()
            
            if self.scroll_CAN_message_button.isChecked():
                self.received_CAN_message_table.scrollToBottom()
            
            #Parse CAN into tables
            #Get the message counter for the session 
            #Assignment: add a button that resets the counter.
            self.received_CAN_message_count += 1
            timestamp = time.time() #PC Time
            vda_timestamp = struct.unpack(">L",rxmessage[0:4])[0] # Vehicle Diagnostic Adapter Timestamp 
            extended = rxmessage[4]
            if extended:
                can_id = struct.unpack(">L",rxmessage[5:9])[0]
                databytes = rxmessage[9:]
            else:
                can_id = struct.unpack(">H",rxmessage[5:7])[0]
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
            
            #Populate the row with data
            self.received_CAN_message_table.setItem(row_count,0,
                 QTableWidgetItem("{}".format(self.received_CAN_message_count)))
            
            self.received_CAN_message_table.setItem(row_count,1,
                 QTableWidgetItem("{:0.6f}".format(timestamp)))
            
            self.received_CAN_message_table.setItem(row_count,2,
                 QTableWidgetItem("{:0.3f}".format(vda_timestamp* 0.001))) #Figure out what the multiplier is for the time stamp
            
            self.received_CAN_message_table.setItem(row_count,3,
                 QTableWidgetItem("{:08X}".format(can_id)))
            #Assignment: Make the ID format conditional on 29 or 11 bit IDs
            
            self.received_CAN_message_table.setItem(row_count,4,
                 QTableWidgetItem("{}".format(dlc)))
            
            col=5
            for b in databytes:
                self.received_CAN_message_table.setItem(row_count,col,
                    QTableWidgetItem("{:02X}".format(b)))
                col+=1

            
            if self.received_CAN_message_count < 100:
                self.received_CAN_message_table.resizeColumnsToContents()    
                #Assignment: Change this automatic resizer to a button.
            
    def display_version(self):
        if self.RP1210.ReadVersion is None:
            print("RP1210_ReadVersion() is not supported.")
            message_window = QMessageBox()
            message_window.setText("RP1210_ReadVersion() function is not supported.")
            message_window.setIcon(QMessageBox.Information)
            message_window.setWindowTitle('RP1210 Version Information')
            message_window.setStandardButtons(QMessageBox.Ok)
            message_window.show()
            return

        chDLLMajorVersion    = (c_char)()
        chDLLMinorVersion    = (c_char)()
        chAPIMajorVersion    = (c_char)()
        chAPIMinorVersion    = (c_char)()

        self.RP1210.ReadVersion( byref( chDLLMajorVersion ), byref( chDLLMinorVersion ), byref( chAPIMajorVersion ), byref( chAPIMinorVersion  ) )

        print('Successfully Read DLL and API Versions.')
        DLLMajor = chDLLMajorVersion.value.decode('ascii')
        DLLMinor = chDLLMinorVersion.value.decode('ascii')
        APIMajor = chAPIMajorVersion.value.decode('ascii')
        APIMinor = chAPIMinorVersion.value.decode('ascii')
        print("DLL Major Version: {}".format(DLLMajor))
        print("DLL Minor Version: {}".format(DLLMinor))
        print("API Major Version: {}".format(APIMajor))
        print("API Minor Version: {}".format(APIMinor))

        message_window = QMessageBox()
        message_window.setText('Driver software versions are as follows:\nDLL Major Version: %r' %DLLMajor + '\nDLL Minor Version: %r' %DLLMinor + '\nAPI Major Version: %r' %APIMajor + '\nAPI Minor Version: %r' %APIMinor)
        message_window.setIcon(QMessageBox.Information)
        message_window.setWindowTitle('RP1210 Version Information')
        message_window.setStandardButtons(QMessageBox.Ok)

        message_window.exec_()

    def display_detailed_version(self):
        if self.RP1210.ReadDetailedVersion is None:
            print("RP1210_ReadVersion() is not supported.")
            result1 = QMessageBox()
            result1.setText("RP1210_ReadDetailedVersion() function is not supported.")
            result1.setIcon(QMessageBox.Information)
            result1.setWindowTitle('RP1210 Detailed Version')
            result1.setStandardButtons(QMessageBox.Ok)
            result1.show()
            return

        chAPIVersionInfo    = (c_char*17)()
        chDLLVersionInfo    = (c_char*17)()
        chFWVersionInfo     = (c_char*17)()
        nRetVal = self.RP1210.ReadDetailedVersion(c_short(self.nClientID), 
                                                    byref(chAPIVersionInfo),
                                                    byref(chDLLVersionInfo), 
                                                    byref( chFWVersionInfo ) )

        result2 = QMessageBox()
        result2.setIcon(QMessageBox.Information)
        result2.setWindowTitle('RP1210 Detailed Version Information')
        result2.setStandardButtons(QMessageBox.Ok)
        
        if nRetVal == 0 :
           print('Congratulations! You have connected to a VDA! No need to check your USB connection.')
           DLL = chDLLVersionInfo.value
           API = chAPIVersionInfo.value
           FW = chAPIVersionInfo.value
           result2.setText('Congratulations!\nYou have connected to a vehicle diagnostic adapter (VDA)!\nNo need to check your USB connection.\nDLL = {}\nAPI = {}\nFW = {}'.format(DLL.decode('ascii'),API.decode('ascii'),FW.decode('ascii')))
                       
        else :   
           print("RP1210_ReadDetailedVersion fails with a return value of  {}: {}".format(nRetVal,RP1210Errors[nRetVal]))
           result2.setText("RP1210_ReadDetailedVersion fails with a return value of  {}: {}".format(nRetVal,RP1210Errors[nRetVal]))
           
        result2.exec_()
    def closeEvent(self, *args, **kwargs):
        for n in range(self.nClientID):
            nRetVal = self.RP1210.ClientDisconnect(n)
            print("Exiting. RP1210_ClientDisconnect returns {}: {}".format(nRetVal,RP1210Errors[nRetVal]))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    execute = TUDiagnostics()
    sys.exit(app.exec_())