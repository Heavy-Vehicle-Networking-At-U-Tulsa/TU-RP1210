import sys
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
from PyQt5.QtCore import Qt, QTimer, QCoreApplication
from PyQt5.QtGui import QIcon
import os
import serial
import serial.tools.list_ports
import time
import calendar
import logging
import threading
import traceback
import json
import logging.config

logger = logging.getLogger(__name__)

def get_storage_path(progname):
    storage = os.path.join(os.getenv('LOCALAPPDATA'), progname )
    if not os.path.isdir(storage):
        os.makedirs(storage)
    return storage

class CANLoggerThread(threading.Thread):
    '''This thread is designed to receive messages from a usb,
       using the MicroPyusb https://github.com/inmcm/micropyusb
    '''

    def __init__(self, rx_queue, serial_port):
        threading.Thread.__init__(self)
        self.rx_queue = rx_queue
        self.ser = serial_port
        self.runSignal = True
        self.message = None
        logger.debug("Started CANLoggerThread on {}".format(self.ser.port))

    def run(self):
        while self.runSignal:
            try:
                self.rx_queue.put(self.ser.read())
                #.decode('ascii','ignore')
            except:
                logger.debug("Error within usb Read Thread.")
                logger.debug(traceback.format_exc())
                break            
        logger.debug("usb Receive Thread is finished.")


class NMFTALogger2Dialog(QDialog):
    def __init__(self,title):
        super(NMFTALogger2Dialog,self).__init__()
        logger.debug("Starting Logger 2 Interface")
        storage = get_storage_path(title)
        self.usb_settings_file = os.path.join(get_storage_path(title), "GPS_setting.txt")
        logger.debug("Using {} for usb_settings_file".format(self.usb_settings_file))
        self.ser = None
        self.baud = "115200"
        self.comport = "COM1"
        self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)
        logger.debug("Trying automatic USB connection.")
        self.try_usb()
        if not self.connected:
            self.setup_dialog()
        #if self.connected:
        self.setup_ui()

    def setup_dialog(self):

        usb_port_label = QLabel("USB Communications Port")
        self.usb_port_combo_box = QComboBox()
        self.usb_port_combo_box.setInsertPolicy(QComboBox.NoInsert)
        for device in sorted(serial.tools.list_ports.comports(), reverse = True):
            self.usb_port_combo_box.addItem("{} - {}".format(device.device, device.description))
        self.usb_port_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.accepted.connect(self.set_usb)
        #self.rejected.connect(self.reject_usb)

        self.v_layout = QVBoxLayout()
        self.v_layout.addWidget(usb_port_label)
        self.v_layout.addWidget(self.usb_port_combo_box)
        
        self.v_layout.addWidget(self.buttons)

        self.layout = self.setLayout(self.v_layout)
        self.show()
        
    def setup_ui(self):
        """
        Sets up the Graphical User interface for the dialog box. 
        There are 4 main areas
        """
        
        
        command_button_frame = QGroupBox("Logger Commands")
        console_output_frame = QGroupBox("Logger Console Output")
        data_processing_frame = QGroupBox("Data Functions")
        
        
        command_button_frame_layout = QVBoxLayout()
        command_button_frame.setLayout(command_button_frame_layout)
        
        console_output_frame_layout = QVBoxLayout()
        console_output_frame.setLayout(console_output_frame_layout)
        
        data_processing_frame_layout = QVBoxLayout()
        data_processing_frame.setLayout(data_processing_frame_layout)
                        
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        
        
        dialog_box_layout = QGridLayout()

        dialog_box_layout.addWidget(command_button_frame,0,0,1,1)
        dialog_box_layout.addWidget(console_output_frame, 0,1,1,2)
        dialog_box_layout.addWidget(data_processing_frame, 0,3,1,1)
        
        self.dialog_box = QWidget()        
        self.dialog_box.setLayout(dialog_box_layout)
        self.setWindowTitle("CAN Logger 2 Interface")
        self.setWindowModality(Qt.ApplicationModal) 
        self.dialog_box.show()
       
    def close(self):
        self.dialog_box.close()

    def set_usb(self): 
        self.comport = self.usb_port_combo_box.currentText().split('-')[0].strip()
        return self.connect_usb()

    def connect_usb(self): 
        logger.debug("Trying to connect CAN Logger.")
        try:
            self.ser.close()
            del self.ser
        except AttributeError:
            pass
        try:
            self.ser = serial.Serial(self.comport, baudrate=self.baud, timeout=2)
        except serial.serialutil.SerialException:
            logger.debug(traceback.format_exc())
            if "PermissionError" in repr(traceback.format_exc()):
                QMessageBox.information(self,"usb Status","The port {} is already in use. Please unplug and replug the usb unit.".format(self.comport))
            else:
                self.connected = False
                return self.connected
        try:
            self.ser.write(b'TEST\n')
            test_sentence = self.ser.readline().decode('ascii','ignore')
            if len(test_sentence) > 0:
                logger.info("Successful usb connection on {}".format(self.comport))
                with open(self.usb_settings_file,"w") as out_file:
                    out_file.write("{},{}\n".format(self.comport, self.baud))
                self.connected = True
                return True
            else:
                logger.debug("Could not find usb connection on {}".format(self.comport))
                QMessageBox.information(self,"No Connection","Could not find usb connection on {}".format(self.comport))
                self.connected = False
                return self.connected
        except:
            logger.debug(traceback.format_exc())
            return self.connected

    def try_usb(self):
        try:
            with open(self.usb_settings_file, "r") as in_file:
                lines = in_file.readlines()
            line_list = lines[0].split(",")
            self.comport = line_list[0]
            self.baud = line_list[1]
            self.connected = self.connect_usb()

        except FileNotFoundError:
            self.connected = False
        return self.connected 

if __name__ == '__main__':
    with open("logging.config.json",'r') as f:
        logging_dictionary = json.load(f)
        logging.config.dictConfig(logging_dictionary)
    app = QApplication(sys.argv)
    execute = NMFTALogger2Dialog("CAN Logger 2")
    sys.exit(app.exec_())

