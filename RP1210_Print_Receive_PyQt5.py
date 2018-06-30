#!/bin/env/python
# An introduction sample source code that provides RP1210 capabilities

#Import 
from PyQt5.QtWidgets import (QWidget, QTreeView, QMessageBox, QHBoxLayout, QFileDialog, QLabel, QSlider, QCheckBox, QLineEdit, QVBoxLayout, QApplication, QPushButton)
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

class RP1210ReadMessageThread(threading.Thread):
    '''This thread is designed to recieve messages from the vehicle diagnostic adapter (VDA) and put the
    data into a queue. The class arguments are as follows:
    rx_queue - A datastructure that takes the recieved message.
    RP1210_ReadMessage - a finction handle to the VDA DLL.
    nClientID - this lets us know which network is being used to recieve the messages. This will likely be '''
    def __init__(self, parent, rx_queue, RP1210_ReadMessage, nClientID):
        super().__init__()
        self.root = parent
        threading.Thread.__init__(self)
        self.rx_queue = rx_queue
        self.ReadMessage = RP1210_ReadMessage
        self.nClientID = nClientID
        self.runSignal = True

    def run(self):
        ucTxRxBuffer = (c_char*2000)()
        NON_BLOCKING_IO = 0
        BLOCKING_IO = 1
        
        #display a valid connection upon start.
        print(self.ReadMessage)
        print(self.nClientID)
        
        while self.runSignal:
            nRetVal = self.ReadMessage( c_short( self.nClientID ), byref( ucTxRxBuffer ),
                                        c_short( 2000 ), c_short( BLOCKING_IO ) )
            if nRetVal > 0:
                self.rx_queue.put(ucTxRxBuffer[:nRetVal])
                print(ucTxRxBuffer[:nRetVal])
            time.sleep(.001)
    
class RP1210(QWidget):

    def __init__(self):
        super().__init__()

        # Upon startup, open the vendor specific library. This DLL is named in the c:\Windows\RP1210.ini file
        # TODO: let the user select the RP1210 device after parsing the RP1210 options. Change this to a dialog
        # box control
        self.setupRP1210("DGDPA5MA.DLL")

        

        self.init_ui()
                

    def setupRP1210(self,dllName,protocol = "J1939:Channel=1",deviceID = 1):

        #Load the Windows Device Library
        RP1210DLL = windll.LoadLibrary( dllName )
                
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

        print( "Attempting connect to DLL [%s], DeviceID [%d]" %( dllName, deviceID ) )

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

        b1 = QWidget()
        self.version_button = QPushButton(b1)
        self.version_button.setText('Display Version')
        self.version_button.clicked.connect(self.display_version)
        
        b2 = QWidget()
        self.detailed_version_button = QPushButton(b2)
        self.detailed_version_button.setText('Get Detailed Version')        
        self.detailed_version_button.clicked.connect(self.display_detailed_version)
      
        #setup a Receive queue
        self.rx_queue = queue.Queue()
        self.read_message_thread = RP1210ReadMessageThread(self, self.rx_queue,self.ReadMessage,self.nClientID)
        self.read_message_thread.start()
        print("Started RP1210ReadMessage Thread.")
        
        self.received_j1939_message_tree = QTreeView()

        self.scroll_j1939_message_button =  QCheckBox("Auto Scroll Message Window")   

        self.max_rx_messages = 10000
        self.rx_message_buffer = collections.deque(maxlen=self.max_rx_messages)
        self.max_message_tree = 10000
        self.message_tree_ids=collections.deque(maxlen=self.max_message_tree)
        self.fill_tree()

        v_layout = QVBoxLayout()
        
        v_layout.addWidget(self.version_button)
        v_layout.addWidget(self.detailed_version_button)
        v_layout.addWidget(self.scroll_j1939_message_button)
        v_layout.addWidget(self.received_j1939_message_tree)

        self.setLayout(v_layout)
        self.setWindowTitle('RP1210 Interface')

        self.show()

    def fill_tree(self):

        QTimer.singleShot(20, lambda: self.fill_tree)
                    
        while self.rx_queue.qsize():
            
            
            message_text = ""
            rxmessage = self.rx_queue.get()
            print (rxmessage.format(b))

            for b in rxmessage:
                message_text+="{:02X} ".format(b)
            self.message_tree_ids.append(self.recieved_j1939_message_tree.insert('','end',text=message_text))
            if len(self.message_tree_ids) >= self.max_message_tree: 
                self.recieved_j1939_message_tree.delete(self.message_tree_ids.popleft())

            self.rx_message_buffer.append(message_text)

        if self.scroll_j1939_message_button.isChecked():
                if len(self.message_tree_ids) > 1:
                    self.recieved_j1939_message_tree.see(self.message_tree_ids[-1])
         
        
        
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

