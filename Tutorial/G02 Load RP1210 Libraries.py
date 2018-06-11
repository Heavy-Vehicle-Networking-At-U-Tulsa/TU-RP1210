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
from TURP1210.RP1210.RP1210 import *
from TURP1210.RP1210.RP1210Functions import *
from TURP1210.RP1210.RP1210Select import *

import logging
logger = logging.getLogger(__name__)


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
       
        RP1210Button = QPushButton("Slect RP1210")
        RP1210Button.setToolTip("Open the RP1210 Setup Dialog")
        RP1210Button.clicked.connect(self.selectRP1210)
        
        self.grid_layout = QGridLayout()
        self.grid_layout.addWidget(myNewButton,0,0,1,1)
        self.grid_layout.addWidget(RP1210Button,0,1,1,1)

        main_widget = QWidget()
        main_widget.setLayout(self.grid_layout)

        self.setCentralWidget(main_widget)
        self.show()

    def do_something(self):
        print("I got pressed.")
        self.counter += 1
        self.statusBar().showMessage("I got pressed {} times.".format(self.counter))

    def selectRP1210(self):
        logger.debug("Select RP1210 function called.")
        selection = SelectRP1210("Select")
        logger.debug(selection.dll_name)
        selection.show_dialog()

        dll_name = selection.dll_name
        protocol = selection.protocol
        deviceID = selection.deviceID
        speed    = selection.speed

        self.RP1210 = RP1210Class(dll_name)


        # We want to connect to multiple clients with different protocols.
        self.client_ids={}
        self.client_ids["CAN"] = self.RP1210.get_client_id("CAN", deviceID, "{}".format(speed))
        self.client_ids["J1708"] = self.RP1210.get_client_id("J1708", deviceID, "Auto")
        self.client_ids["J1939"] = self.RP1210.get_client_id("J1939", deviceID, "{}".format(speed))

        # Once an RP1210 DLL is selected, we can connect to it using the RP1210 helper file.
        self.RP1210 = RP1210Class(selection.dll_name)
        
        self.rx_queues={}
        self.read_message_threads={}
        self.extra_queues = {}
        # Set all filters to pass.  This allows messages to be read.
        # Constants are defined in an included file
        i = 0
        for protocol, nClientID in self.client_ids.items():
            QCoreApplication.processEvents()
            if nClientID is not None:
                # By turning on Echo Mode, our logger process can record sent messages as well as received.
                fpchClientCommand = (c_char*2000)()
                fpchClientCommand[0] = 1 #Echo mode on
                return_value = self.RP1210.SendCommand(c_short(RP1210_Echo_Transmitted_Messages), 
                                                       c_short(nClientID), 
                                                       byref(fpchClientCommand), 1)
                logger.debug('RP1210_Echo_Transmitted_Messages returns {:d}: {}'.format(return_value,self.RP1210.get_error_code(return_value)))
                
                 #Set all filters to pass
                return_value = self.RP1210.SendCommand(c_short(RP1210_Set_All_Filters_States_to_Pass), 
                                                       c_short(nClientID),
                                                       None, 0)
                if return_value == 0:
                    logger.debug("RP1210_Set_All_Filters_States_to_Pass for {} is successful.".format(protocol))
                    #setup a Receive queue. This keeps the GUI responsive and enables messages to be received.
                    self.rx_queues[protocol] = queue.Queue(10000)
                    self.extra_queues[protocol] = queue.Queue(10000)
                    self.read_message_threads[protocol] = RP1210ReadMessageThread(self, 
                                                                                  self.rx_queues[protocol],
                                                                                  self.extra_queues[protocol],
                                                                                  self.RP1210.ReadMessage, 
                                                                                  nClientID,
                                                                                  protocol, self.title)
                    self.read_message_threads[protocol].setDaemon(True) #needed to close the thread when the application closes.
                    self.read_message_threads[protocol].start()
                    logger.debug("Started RP1210ReadMessage Thread.")

                    self.statusBar().showMessage("{} connected using {}".format(protocol,dll_name))
                    if protocol == "J1939":
                        self.isodriver = ISO15765Driver(self, self.extra_queues["J1939"])
                    
                else :
                    logger.debug('RP1210_Set_All_Filters_States_to_Pass returns {:d}: {}'.format(return_value,self.RP1210.get_error_code(return_value)))

                if protocol == "J1939":
                    fpchClientCommand[0] = 0x00 #0 = as fast as possible milliseconds
                    fpchClientCommand[1] = 0x00
                    fpchClientCommand[2] = 0x00
                    fpchClientCommand[3] = 0x00
                    
                    return_value = self.RP1210.SendCommand(c_short(RP1210_Set_J1939_Interpacket_Time), 
                                                           c_short(nClientID), 
                                                           byref(fpchClientCommand), 4)
                    logger.debug('RP1210_Set_J1939_Interpacket_Time returns {:d}: {}'.format(return_value,self.RP1210.get_error_code(return_value)))
                    
               
            else:
                logger.debug("{} Client not connected for All Filters to pass. No Queue will be set up.".format(protocol))
            i+=1
            
        

app = QApplication(sys.argv)
execute = ExampleRP1210()
sys.exit(app.exec_())