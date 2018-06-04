
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
from TURP1210.micropyGPS import MicropyGPS
from TURP1210.UserData import get_storage_path

logger = logging.getLogger(__name__)

class GPSThread(threading.Thread):
    '''This thread is designed to receive messages from a GPS,
       using the MicroPyGPS https://github.com/inmcm/micropyGPS
    '''

    def __init__(self, rx_queue, serial_port):
        threading.Thread.__init__(self)
        self.rx_queue = rx_queue
        self.ser = serial_port
        self.runSignal = True
        self.message = None
        self.gps = MicropyGPS()
        self.gpstime = None
        self.gpslon = None
        self.gpslat = None
        self.gpsalt = None
        logger.debug("Started GPSThread on {}".format(self.ser.port))

    def run(self):
        while self.runSignal:
            try:
                gps_data = self.ser.readline().decode('ascii','ignore')

                for b in gps_data:
                    self.gps.update(b)
                try: 
                    time_struct = time.strptime("{} {} {} ".format(self.gps.date[0],self.gps.date[1],self.gps.date[2]) + "{} {} {}".format(self.gps.timestamp[0],self.gps.timestamp[1],int(self.gps.timestamp[2])), "%d %m %y %H %M %S")
                    self.gpstime = calendar.timegm(time_struct) #Put into floating point UTC
                except ValueError:
                    self.gpstime = None
                
                self.gpslat = self.gps.latitude[0] + self.gps.latitude[1]/60
                if self.gps.latitude[2] == 'S':
                     self.gpslat = -self.gpslat

                self.gpslon = self.gps.longitude[0] + self.gps.longitude[1]/60
                if self.gps.longitude[2] == 'W':
                     self.gpslon = -self.gpslon

                self.gpsalt = self.gps.altitude

            except:
                logger.debug("Error within GPS Read Thread.")
                logger.debug(traceback.format_exc())
                self.gpstime = None
                self.gpslon = None
                self.gpslat = None
                self.gpsalt = None
                break
            
        logger.debug("GPS Receive Thread is finished.")


class GPSDialog(QDialog):
    def __init__(self,title):
        super(GPSDialog,self).__init__()
        #self.root = parent
        self.baudrate = 4800
        self.comport = "COM1"
        self.setup_dialog()
        self.setWindowTitle("Select GPS")
        self.setWindowModality(Qt.ApplicationModal)
        self.connected = False
        self.ser = None
        self.gps_settings_file = os.path.join(get_storage_path(title), "GPS_setting.txt")


    def setup_dialog(self):

        gps_port_label = QLabel("GPS Communications Port")
        self.gps_port_combo_box = QComboBox()
        self.gps_port_combo_box.setInsertPolicy(QComboBox.NoInsert)
        for device in sorted(serial.tools.list_ports.comports(), reverse = True):
            self.gps_port_combo_box.addItem("{} - {}".format(device.device, device.description))
        self.gps_port_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        
        baud_list = ["{}".format(b) for b in [4800, 9600, 115200, 1200, 1800, 2400, 19200, 38400, 57600, 115200, 
                     230400, 460800, 500000, 576000, 921600, 1000000, 1152000, 1500000, 
                     2000000, 2500000, 3000000, 3500000, 4000000]]

        baud_label = QLabel("GPS Baud Rate")
        self.baud_combo_box = QComboBox()
        self.baud_combo_box.setInsertPolicy(QComboBox.NoInsert)
        self.baud_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.baud_combo_box.addItems(baud_list)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.accepted.connect(self.set_GPS)
        #self.rejected.connect(self.reject_GPS)

        self.v_layout = QVBoxLayout()
        self.v_layout.addWidget(gps_port_label)
        self.v_layout.addWidget(self.gps_port_combo_box)
        self.v_layout.addWidget(baud_label)
        self.v_layout.addWidget(self.baud_combo_box)
        self.v_layout.addWidget(self.buttons)

        self.setLayout(self.v_layout)
    
    def run(self):
        self.gps_port_combo_box.clear()
        for device in sorted(serial.tools.list_ports.comports(), reverse = True):
            self.gps_port_combo_box.addItem("{} - {}".format(device.device, device.description))
        self.gps_port_combo_box.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.exec_()

    def set_GPS(self): 
        self.comport = self.gps_port_combo_box.currentText().split('-')[0].strip()
        self.baud = int(self.baud_combo_box.currentText())
        return self.connect_GPS()

    def connect_GPS(self): 
        logger.debug("Trying to connect GPS.")
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
                QMessageBox.information(self,"GPS Status","The port {} is already in use. Please unplug and replug the GPS unit.".format(self.comport))
            else:
                self.connected = False
                return False
        try:
            test_sentence = self.ser.readline().decode('ascii','ignore')
            if len(test_sentence) > 0:
                logger.info("Successful GPS connection on {}".format(self.comport))
                with open(self.gps_settings_file,"w") as out_file:
                    out_file.write("{},{}\n".format(self.comport, self.baud))
                self.connected = True
                return True
            else:
                logger.debug("Could not find GPS connection on {}".format(self.comport))
                QMessageBox.information(self,"No Connection","Could not find GPS connection on {}".format(self.comport))
                self.connected = False
                return False
        except:
            logger.debug(traceback.format_exc())
            return False

    def try_GPS(self):
        try:
            with open(self.gps_settings_file, "r") as in_file:
                lines = in_file.readlines()
            line_list = lines[0].split(",")
            self.comport = line_list[0]
            self.baud = line_list[1]
            self.connected = self.connect_GPS()

        except FileNotFoundError:
            self.connected = False
        return self.connected 


