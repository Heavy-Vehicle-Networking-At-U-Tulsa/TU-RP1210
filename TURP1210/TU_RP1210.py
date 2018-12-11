"""
TU RP1210 is a 32-bit Python 3 program that uses the RP1210 API from the 
American Trucking Association's Technology and Maintenance Council (TMC). This 
framework provides an introduction sample source code with RP1210 capabilities.
To get the full utility from this program, the user should have an RP1210 compliant
device installed. To make use of the device, you should also have access to a vehicle
network with either J1939 or J1708.

The program is release under one of two licenses.  See LICENSE.TXT for details. The 
default license is as follows:

    Copyright (C) 2018  Jeremy Daily, The University of Tulsa

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

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
from PyQt5.QtCore import Qt, QTimer, QAbstractTableModel, QCoreApplication, QSize
from PyQt5.QtGui import QIcon
import winshell
import cryptography
import pgpy
from pgpy.constants import (PubKeyAlgorithm, 
                            KeyFlags, 
                            HashAlgorithm, 
                            SymmetricKeyAlgorithm, 
                            CompressionAlgorithm, 
                            EllipticCurveOID, 
                            SignatureType)

import subprocess 
import requests
import queue
import time
import shutil
import base64
import sys
import struct
import json
import humanize
import random
import os
import threading
import binascii

from TURP1210.RP1210.RP1210 import *
from TURP1210.RP1210.RP1210Functions import *
from TURP1210.RP1210.RP1210Select import *
from TURP1210.GPSInterface import *
from TURP1210.J1939Tab import *
from TURP1210.J1587Tab import *
from TURP1210.ComponentInfoTab import *
from TURP1210.UserData import *
from TURP1210.PDFReports import *
from TURP1210.ISO15765 import *
from TURP1210.Graphing.graphing import * 

import logging
import logging.config

if getattr(sys, 'frozen', False):
    # frozen
    module_directory = os.path.dirname(sys.executable)
else:
    # unfrozen
    module_directory = os.path.dirname(os.path.realpath(__file__))

try:
    with open("logging.config.json",'r') as f:
        logging_dictionary = json.load(f)
except FileNotFoundError:
    try:
        with open(os.path.join(module_directory,"logging.config.json"),'r') as f:
            logging_dictionary = json.load(f)
    except FileNotFoundError:
        print("No logging.config.json file found.")

logging.config.dictConfig(logging_dictionary)
logger = logging.getLogger(__name__)

CANlogger = logging.getLogger("CANLogger")
J1708logger = logging.getLogger("J1708Logger")
J1939logger = logging.getLogger("J1939Logger")

try:
    with open('version.json') as f:
        TU_RP1210_version = json.load(f)
except:
    print("This is a module that should be run from another program. See the demo code.")

start_time = time.strftime("%Y-%m-%dT%H%M%S %Z", time.localtime())

current_machine_id = subprocess.check_output('wmic csproduct get uuid').decode('ascii','ignore').split('\n')[1].strip() 
current_drive_id = subprocess.check_output('wmic DISKDRIVE get SerialNumber').decode('ascii','ignore').split('\n')[1].strip() 

class TU_RP1210(QMainWindow):
    def __init__(self, title, connect_gps=False, backup_interval=False):
        super(TU_RP1210,self).__init__()
        
        self.logfile = logging_dictionary["handlers"]["file_handler"]["filename"]
        logger.info("Session log file is {}".format(self.logfile))

        self.title = title
        self.setWindowTitle(self.title)

        progress = QProgressDialog(self)
        progress.setMinimumWidth(600)
        progress.setWindowTitle("Starting Application")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMaximum(10)
        progress_label = QLabel("Loading the J1939 Database")
        #load the J1939 Database
        progress.setLabel(progress_label)
        try:
            with open("J1939db.json",'r') as j1939_file:
                self.j1939db = json.load(j1939_file) 
        except FileNotFoundError:
            try:
                with open(os.path.join(module_directory,"J1939db.json"),'r') as j1939_file:
                    self.j1939db = json.load(j1939_file) 
            except FileNotFoundError: 
                # Make a data structure to do something anyways
                logger.debug("J1939db.json file was not found.")
                self.j1939db = {"J1939BitDecodings":{},
                                "J1939FMITabledb": {},
                            "J1939LampFlashTabledb": {},
                            "J1939OBDTabledb": {},
                            "J1939PGNdb": {},
                            "J1939SAHWTabledb": {},
                            "J1939SATabledb": {},
                            "J1939SPNdb": {} }
        logger.info("Done Loading J1939db")
        progress.setValue(1)
        QCoreApplication.processEvents()

        self.rx_queues = {}

        progress_label.setText("Loading the J1587 Database")
        try:
            with open(os.path.join(module_directory,"J1587db.json"),'r') as j1587_file:
                self.j1587db = json.load(j1587_file)
        except FileNotFoundError:
            logger.debug("J1587db.json file was not found.")
            self.j1587db = { "FMI": {},
                             "MID": {},
                             "MIDAlias": {},
                             "PID": {"168":{"BitResolution" : 0.05,
                                            "Category" : "live",
                                            "DataForm" : "a a",
                                            "DataLength" : 2,
                                            "DataType" : "Unsigned Integer",
                                            "FormatStr" : "%0.2f",
                                            "Maximum" : 3276.75,
                                            "Minimum" : 0.0,
                                            "Name" : "Battery Potential (Voltage)",
                                            "Period" : "1",
                                            "Priority" : 5,
                                            "Unit" : "volts"},
                                    "245" : { "BitResolution" : 0.1,
                                              "Category" : "hist",
                                              "DataForm" : "n a a a a",
                                              "DataLength" : 4,
                                              "DataType" : "Unsigned Long Integer",
                                              "FormatStr" : "%0.1f",
                                              "Maximum" : 429496729.5,
                                              "Minimum" : 0.0,
                                              "Name" : "Total Vehicle Distance",
                                              "Period" : "10",
                                              "Priority" : 7,
                                              "Unit" : "miles"},
                                    "247" : {
                                        "BitResolution" : 0.05,
                                        "Category" : "hist",
                                        "DataForm" : "n a a a a",
                                        "DataLength" : 4,
                                        "DataType" : "Unsigned Long Integer",
                                        "FormatStr" : "%0.2f",
                                        "Maximum" : 214748364.8,
                                        "Minimum" : 0.0,
                                        "Name" : "Total Engine Hours",
                                        "Period" : "On request",
                                        "Priority" : 8,
                                        "Unit" : "hours"}
                                    },
                             "PIDNames": {},
                             "SID": {} }
        logger.info("Done Loading J1587db")
        progress.setValue(2)
        QCoreApplication.processEvents()
        

        progress_label.setText("Initializing System Variables")
        os.system("TASKKILL /F /IM DGServer2.exe")
        os.system("TASKKILL /F /IM DGServer1.exe")  
        
        self.update_rate = 100

        self.module_directory = module_directory
        
        self.user_data = UserData(self.title)

        self.isodriver = None

        self.source_addresses=[]
        self.long_pgn_timeouts = [65227, ]
        self.long_pgn_timeout_value = 2
        self.short_pgn_timeout_value = .1

        self.export_path =  os.path.join(winshell.my_documents(), __name__)
        if not os.path.isdir(self.export_path):
            os.makedirs(self.export_path)

        self.setGeometry(0,50,1600,850)
        self.RP1210 = None
        self.network_connected = {"J1939": False, "J1708": False}
        self.RP1210_toolbar = None
        progress.setValue(3)
        QCoreApplication.processEvents()

        progress_label.setText("Setting Up the Graphical Interface")
        self.init_ui()
        self.graph_tabs = {}
        logger.debug("Done Setting Up User Interface.")
        progress.setValue(4)
        QCoreApplication.processEvents()

        progress_label.setText("Setting up the RP1210 Interface")
        self.selectRP1210(automatic=True)
        logger.debug("Done selecting RP1210.")
        progress.setValue(5)
        QCoreApplication.processEvents()

        progress_label.setText("Initializing a New Document")
        self.create_new(False)
        progress.setValue(6)
        QCoreApplication.processEvents()

        progress_label.setText("Setting up the GPS System")
        self.GPS = GPSDialog(self.title)
        if connect_gps:
            self.setup_gps(dialog = False)
        progress.setValue(7)
        QCoreApplication.processEvents()
        
        progress_label.setText("Loading the PDF Report Generator")
        self.pdf_engine = FLAReportTemplate(self)
        progress.setValue(8)
        QCoreApplication.processEvents()
        

        progress_label.setText("Starting Loop Timers")
        connections_timer = QTimer(self)
        connections_timer.timeout.connect(self.check_connections)
        connections_timer.start(1500) #milliseconds

        read_timer = QTimer(self)
        read_timer.timeout.connect(self.read_rp1210)
        read_timer.start(self.update_rate) #milliseconds
        
        # if backup_interval > 1000:
        #     backup_timer = QTimer(self)
        #     backup_timer.timeout.connect(self.save_backup_file)
        #     backup_timer.start(backup_interval)
        progress.setValue(10)
        QCoreApplication.processEvents()

    def init_ui(self):
        # Builds GUI
        # Start with a status bar
        self.statusBar().showMessage("Welcome!")

        self.grid_layout = QGridLayout()
        
        # Build common menu options
        menubar = self.menuBar()

        # File Menu Items
        file_menu = menubar.addMenu('&File')
        new_file = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_New_Ticket_48px.png')), '&New', self)
        new_file.setShortcut('Ctrl+N')
        new_file.setStatusTip('Create a new record.')
        new_file.triggered.connect(self.new_file)
        file_menu.addAction(new_file)

        open_file = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Open_48px_1.png')), '&Open', self)
        open_file.setShortcut('Ctrl+O')
        open_file.setStatusTip('Open an existing data file.')
        open_file.triggered.connect(self.open_file)
        file_menu.addAction(open_file)

        open_logger2 = QAction(QIcon(os.path.join(module_directory,r'icons/logger2_48px.png')), '&Import CAN Logger 2', self)
        open_logger2.setShortcut('Ctrl+I')
        open_logger2.setStatusTip('Open a file from the NMFTA/TU CAN Logger 2')
        open_logger2.triggered.connect(self.open_open_logger2)
        file_menu.addAction(open_logger2)


        save_file = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Save_48px.png')), '&Save', self)
        save_file.setShortcut('Ctrl+S')
        save_file.setStatusTip('Save the current data file.')
        save_file.triggered.connect(self.save_file)
        file_menu.addAction(save_file)

        save_file_as = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Save_as_48px.png')), 'Save &As...', self)
        save_file_as.setShortcut('Ctrl+Shift+S')
        save_file.setStatusTip('Save current data file with a new name.')
        save_file_as.triggered.connect(self.save_file_as)
        file_menu.addAction(save_file_as)

        export_to_pdf = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_PDF_48px.png')), 'Export to &PDF', self)
        export_to_pdf.setShortcut('Ctrl+P')
        export_to_pdf.setStatusTip('Export the file as a PDF for printing.')
        export_to_pdf.triggered.connect(self.export_to_pdf)
        file_menu.addSeparator()
        file_menu.addAction(export_to_pdf)

        export_to_json = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_CSV_48px.png')), 'Expor&t to JSON', self)
        export_to_json.setShortcut('Ctrl+J')
        export_to_json.setStatusTip('Export signed data file as human readable java script object notation (JSON) file.')
        export_to_json.triggered.connect(self.export_to_json)
        file_menu.addAction(export_to_json)

        sign_file_action = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Hand_With_Pen_48px.png')), 'Si&gn File', self)
        sign_file_action.setShortcut('Ctrl+G')
        sign_file_action.setStatusTip('Sign a file with a Digital Signing System to guarantee integrity and non-repudiation.')
        sign_file_action.triggered.connect(self.open_and_sign_file)
        file_menu.addSeparator()
        file_menu.addAction(sign_file_action)
        
        verify_file_action = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Approval_48px_1.png')), '&Verify File', self)
        verify_file_action.setShortcut('Ctrl+V')
        verify_file_action.setStatusTip('Check a file with a Digital Signing System to guarantee integrity and non-repudiation.')
        verify_file_action.triggered.connect(self.open_and_verify_file)
        file_menu.addAction(verify_file_action)


        exit_action = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Close_Window_48px.png')), '&Quit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit the program.')
        exit_action.triggered.connect(self.confirm_quit)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)
        
        #build the entries in the dockable tool bar
        file_toolbar = self.addToolBar("File")
        file_toolbar.addAction(new_file)
        file_toolbar.addAction(open_file)
        file_toolbar.addAction(save_file)
        file_toolbar.addAction(save_file_as)
        file_toolbar.addAction(export_to_pdf)
        file_toolbar.addSeparator()
        file_toolbar.addAction(sign_file_action)
        file_toolbar.addAction(verify_file_action)
        file_toolbar.addSeparator()
        file_toolbar.addAction(exit_action)
        
        # RP1210 Menu Items
        self.rp1210_menu = menubar.addMenu('&RP1210')
        
        self.run_menu = menubar.addMenu("&Download")
        run_action = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Go_48px.png')), 'Get All &Known Data', self)
        run_action.setShortcut('Ctrl+Shift+K')
        run_action.setStatusTip('Scan for all data using standard data and known EDR recovery routines.')
        run_action.triggered.connect(self.start_scan)
        self.run_menu.addAction(run_action)
        
        setup_gps_action = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_GPS_Signal_48px.png')), 'Setup &GPS', self)
        setup_gps_action.setShortcut('Ctrl+Shift+G')
        setup_gps_action.setStatusTip('Adjust settings for integrating GPS data into the report.')
        setup_gps_action.triggered.connect(self.setup_gps)
        self.run_menu.addAction(setup_gps_action)
        
        upload_action = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Upload_to_Cloud_48px.png')), 'Upload to EDR Data', self)
        upload_action.setShortcut('Ctrl+Shift+U')
        upload_action.setStatusTip('Upload the data package to the central server to be decoded.')
        upload_action.triggered.connect(self.upload_data_package)
        self.run_menu.addAction(upload_action)


        self.run_toolbar = self.addToolBar("&Download")
        self.run_toolbar.addAction(run_action)
        self.run_toolbar.addAction(setup_gps_action)
        self.run_toolbar.addAction(upload_action)
        
        self.graph_menu = menubar.addMenu('&Graph')
        
        graph_action = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Line_Chart_48px.png')), 'Show G&raphs', self)
        graph_action.setShortcut('Alt+Shift+R')
        graph_action.setStatusTip('Show Available Graphs')
        graph_action.triggered.connect(self.show_graphs)
        self.graph_menu.addAction(graph_action)
            
        clear_voltage_action = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Delete_Table_48px_1.png')), '&Clear Voltage Graphs', self)
        clear_voltage_action.setShortcut('Alt+Shift+C')
        clear_voltage_action.setStatusTip('Clear the time history shown in the vehicle voltage graph.')
        clear_voltage_action.triggered.connect(self.clear_voltage_graph)
        self.graph_menu.addAction(clear_voltage_action)
    
        help_menu = menubar.addMenu('&Help')
        register = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Registration_48px.png')), '&Enter User Information', self)
        register.setShortcut('Alt+Shift+U')
        register.setStatusTip('Enter or edit user details and setup encryption keys.')
        register.triggered.connect(self.register_software)
        help_menu.addAction(register)
        
        
        about = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Help_48px.png')), 'A&bout', self)
        about.setShortcut('F1')
        about.setStatusTip('Display a dialog box with information about the program.')
        about.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about)
        
        help_toolbar = self.addToolBar("Help")
        help_toolbar.addAction(register)
        help_toolbar.addAction(about)

        # Setup the network status windows for logging
        info_box = {}
        info_box_area = {}
        info_layout = {}
        info_box_area_layout = {}
        self.previous_count = {}
        self.status_icon = {}
        self.previous_count = {}
        self.message_count_label = {}
        self.message_rate_label = {}
        self.message_duration_label = {}
        for key in ["J1939","J1708"]:
            # Create the container widget
            info_box_area[key] = QScrollArea()
            info_box_area[key].setWidgetResizable(True)
            info_box_area[key].setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
            bar_size = QSize(150,300)
            info_box_area[key].sizeHint()
            info_box[key] = QFrame(info_box_area[key])
            
            info_box_area[key].setWidget(info_box[key])
            info_box_area[key].setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        
            # create a layout strategy for the container 
            info_layout[key] = QVBoxLayout()
            #set the layout so labels are at the top
            info_layout[key].setAlignment(Qt.AlignTop)
            #assign the layout strategy to the container
            info_box[key].setLayout(info_layout[key])

            info_box_area_layout[key] = QVBoxLayout()
            info_box_area[key].setLayout(info_box_area_layout[key])
            info_box_area_layout[key].addWidget(info_box[key])
            
            #Add some labels and content
            self.status_icon[key] = QLabel("<html><img src='{}/icons/icons8_Unavailable_48px.png'><br>Network<br>Unavailable</html>".format(module_directory))
            self.status_icon[key].setAlignment(Qt.AlignCenter)
            
            self.previous_count[key] = 0
            self.message_count_label[key] = QLabel("Count: 0")
            self.message_count_label[key].setAlignment(Qt.AlignCenter)
            
            #self.message_duration = 0
            self.message_duration_label[key] = QLabel("Duration: 0 sec.")
            self.message_duration_label[key].setAlignment(Qt.AlignCenter)
            
            #self.message_rate = 0
            self.message_rate_label[key] = QLabel("Rate: 0 msg/sec")
            self.message_rate_label[key].setAlignment(Qt.AlignCenter)
            
            csv_save_button = QPushButton("Save as CSV")
            csv_save_button.setToolTip("Save all the {} Network messages to a comma separated values file.".format(key))
            if key == ["J1939"]:
                csv_save_button.clicked.connect(self.save_j1939_csv)
            if key == ["J1708"]:
                csv_save_button.clicked.connect(self.save_j1708_csv)
            
            info_layout[key].addWidget(QLabel("<html><h3>{} Status</h3></html>".format(key)))
            info_layout[key].addWidget(self.status_icon[key])
            info_layout[key].addWidget(self.message_count_label[key])
            info_layout[key].addWidget(self.message_rate_label[key])
            info_layout[key].addWidget(self.message_duration_label[key])
    
        # GPS
        # Create the container widget
        gps_box_area = QScrollArea()
        gps_box_area.setWidgetResizable(True)
        gps_box_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        gps_box = QFrame(gps_box_area)
        gps_box_area.setMinimumWidth(145)
        #gps_box.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        
        gps_box_area.setWidget(gps_box)
        gps_box_area.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        
        # create a layout strategy for the container 
        gps_layout = QVBoxLayout()
        #set the layout so labels are at the top
        gps_layout.setAlignment(Qt.AlignTop)
        #assign the layout strategy to the container
        gps_box.setLayout(gps_layout)
        
        #Add some labels and content
        self.gps_icon = QLabel("<html><img src='{}/icons/icons8_GPS_Disconnected_48px.png'><br>Disconnected</html>".format(module_directory))
        self.gps_icon.setAlignment(Qt.AlignCenter)
        
        self.gps_time_label = QLabel("GPS Time:\nSearching...")
        self.gps_time_label.setAlignment(Qt.AlignCenter)
        
        #self.message_duration = 0
        self.gps_lat_label = QLabel("Latitude:\nSearching...")
        self.gps_lat_label.setAlignment(Qt.AlignCenter)
        self.gps_lon_label = QLabel("Longitude:\nSearching...")
        self.gps_lon_label.setAlignment(Qt.AlignCenter)
        
        gps_layout.addWidget(QLabel("<html><h3>GPS Status</h3></html>"))
        gps_layout.addWidget(self.gps_icon)
        gps_layout.addWidget(self.gps_time_label)
        gps_layout.addWidget(self.gps_lat_label)
        gps_layout.addWidget(self.gps_lon_label)
        #gps_layout.addWidget(gps_setup_button)

        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tabs.setTabShape(QTabWidget.Triangular)
        self.J1939 = J1939Tab(self, self.tabs)
        self.J1587 = J1587Tab(self, self.tabs)
        self.Components = ComponentInfoTab(self, self.tabs)

        
        self.voltage_graph = GraphDialog(self, title="Vehicle Voltage")
        self.voltage_graph.set_yrange(9, 15)
        self.voltage_graph.set_xlabel("Time")
        self.voltage_graph.set_ylabel("Voltage")
        self.voltage_graph.set_title("Battery Voltage Measurements from Vehicle Electronic Control Units")
        
        self.speed_graph = GraphDialog(self, title="Tone Ring Base Speed")
        #self.speed_graph.set_yrange(9, 15)
        self.speed_graph.set_xlabel("Time")
        self.speed_graph.set_ylabel("Speed [km/h]")
        self.speed_graph.set_title("Wheel-based Vehicle Speed from Vehicle Networks")
        
        self.grid_layout.addWidget(info_box_area["J1939"],0,0,1,1)
        self.grid_layout.addWidget(info_box_area["J1708"],1,0,1,1)
        self.grid_layout.addWidget(gps_box_area,2,0,1,1)
        self.grid_layout.addWidget(self.tabs,0,1,4,1)

        main_widget = QWidget()
        main_widget.setLayout(self.grid_layout)
        self.setCentralWidget(main_widget)
        
        self.show()
    
    def get_plot_bytes(self, fig):
        img = BytesIO()
        fig.figsize=(7.5, 10)
        fig.savefig(img, format='PDF',)
        return img

    def setup_RP1210_menus(self):
        connect_rp1210 = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Connected_48px.png')), '&Client Connect', self)
        connect_rp1210.setShortcut('Ctrl+Shift+C')
        connect_rp1210.setStatusTip('Connect Vehicle Diagnostic Adapter')
        connect_rp1210.triggered.connect(self.selectRP1210)
        self.rp1210_menu.addAction(connect_rp1210)

        rp1210_version = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Versions_48px.png')), '&Driver Version', self)
        rp1210_version.setShortcut('Ctrl+Shift+V')
        rp1210_version.setStatusTip('Show Vehicle Diagnostic Adapter Driver Version Information')
        rp1210_version.triggered.connect(self.display_version)
        self.rp1210_menu.addAction(rp1210_version)

        rp1210_detailed_version = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_More_Details_48px.png')), 'De&tailed Version', self)
        rp1210_detailed_version.setShortcut('Ctrl+Shift+T')
        rp1210_detailed_version.setStatusTip('Show Vehicle Diagnostic Adapter Detailed Version Information')
        rp1210_detailed_version.triggered.connect(self.display_detailed_version)
        self.rp1210_menu.addAction(rp1210_detailed_version)

        rp1210_get_hardware_status = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Steam_48px.png')), 'Get &Hardware Status', self)
        rp1210_get_hardware_status.setShortcut('Ctrl+Shift+H')
        rp1210_get_hardware_status.setStatusTip('Determine details regarding the hardware interface status and its connections.')
        rp1210_get_hardware_status.triggered.connect(self.get_hardware_status)
        self.rp1210_menu.addAction(rp1210_get_hardware_status)

        rp1210_get_hardware_status_ex = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_System_Information_48px.png')), 'Get &Extended Hardware Status', self)
        rp1210_get_hardware_status_ex.setShortcut('Ctrl+Shift+E')
        rp1210_get_hardware_status_ex.setStatusTip('Determine the hardware interface status and whether the VDA device is physically connected.')
        rp1210_get_hardware_status_ex.triggered.connect(self.get_hardware_status_ex)
        self.rp1210_menu.addAction(rp1210_get_hardware_status_ex)

        disconnect_rp1210 = QAction(QIcon(os.path.join(module_directory,r'icons/icons8_Disconnected_48px.png')), 'Client &Disconnect', self)
        disconnect_rp1210.setShortcut('Ctrl+Shift+D')
        disconnect_rp1210.setStatusTip('Disconnect all RP1210 Clients')
        disconnect_rp1210.triggered.connect(self.disconnectRP1210)
        self.rp1210_menu.addAction(disconnect_rp1210)

        self.RP1210_toolbar = self.addToolBar("RP1210")
        self.RP1210_toolbar.addAction(connect_rp1210)
        self.RP1210_toolbar.addAction(rp1210_version)
        self.RP1210_toolbar.addAction(rp1210_detailed_version)
        self.RP1210_toolbar.addAction(rp1210_get_hardware_status)
        self.RP1210_toolbar.addAction(rp1210_get_hardware_status_ex)
        self.RP1210_toolbar.addAction(disconnect_rp1210)

    def create_new(self, new_file=True):

        J1939logger.handlers[0].close()
        CANlogger.handlers[0].close()
        J1708logger.handlers[0].close()


        self.source_addresses = []

        try:
            self.export_path = os.path.join(os.path.expanduser('~'),"Documents","{}".format(self.title))
            if not os.path.exists(self.export_path):
                os.makedirs(self.export_path)
        except FileNotFoundError:
            logger.debug(traceback.format_exc())
            self.export_path = os.path.expanduser('~')

        self.filename = os.path.join(self.export_path,
            "{}data {}.cpt".format(self.title, time.strftime("%Y-%m-%d %H%M%S", time.localtime())))
        if new_file:
            fname = QFileDialog.getSaveFileName(self,
                                             "Create New {} Data File".format(self.title),
                                             os.path.join(self.export_path, self.filename),
                                             "",
                                             "")
            if not fname[0]:
                #the user pressed cancel
                return
        else: 
            fname=[False]
        
        if fname[0]:
            self.export_path, self.filename = os.path.split(fname[0])
        logger.info("Current Data Directory is set to {}".format(self.export_path))
        logger.info("Current Data Package file is set to {}".format(self.filename))

        self.data_package = {"File Format":{"major":TU_RP1210_version["major"],
                                            "minor":TU_RP1210_version["minor"],
                                            "patch":TU_RP1210_version["minor"]}}
        
        try:
            self.CAN_file_name = logging_dictionary['handlers']["can_handler"]["filename"]
        except:
            logger.debug(traceback.format_exc())
            self.CAN_file_name = "No file available"

        try:
            self.J1708_log_name = logging_dictionary['handlers']["j1708_handler"]["filename"]
        except:
            logger.debug(traceback.format_exc())
            self.J1708_log_name = "No file available"

        self.data_package["Network Logs"] = {"CAN Log File":{"Name": self.CAN_file_name},
                                             "J1708 Log File":{"Name": self.J1708_log_name},
                                             "Session Log File":{"Name": self.logfile}
                                             }

        self.data_package["File Name"] = self.filename

        self.data_package["Machine UUID"] = current_machine_id
        self.data_package["Harddrive UUID"] = current_drive_id
        logger.info("{} running on a machine with UUID: {}".format(self.title, current_machine_id))
        logger.info("{} running on a diskdrive with Serial Number: {}".format(self.title, current_drive_id))
        
        self.data_package["Time Records"] = {"Personal Computer":{
                                                 "PC Start Time": time.time(),
                                                 "Last PC Time": None,
                                                 "Last GPS Time": None,
                                                 "Permission Time": None,
                                                 "PC Time at Last GPS Reading": None,
                                                 "PC Time minus GPS Time": []
                                                 }
                                            }
        
        
        self.data_package["User Data"] = self.user_data.get_current_data()
        self.data_package["Warnings"] = []
        self.data_package["J1587 Message and Parameter IDs"] = {}
        self.data_package["J1939 Parameter Group Numbers"] = {}
        self.data_package["J1939 Suspect Parameter Numbers"] = {}
        self.data_package["UDS Messages"] = {}
        self.data_package["Component Information"] = {}
        self.data_package["Distance Information"] = {}
        self.data_package["ECU Time Information"] = {}
        self.data_package["Event Data"] = {}
        self.data_package["GPS Data"] = {
            "Altitude": 0.0,
            "GPS Time": None,
            "Latitude": None,
            "Longitude": None,
            "System Time": time.time(),
            "Address": "Not Available"}
        self.data_package["Diagnostic Codes"] = {"DM01":{},
                                                 "DM02":{},
                                                 "DM04":{}
                                                 }
        self.request_timeout = 1

        self.J1939.reset_data()
        self.J1939.clear_j1939_table()
        self.J1587.clear_J1587_table()
        self.Components.rebuild_trees()

    # def setup_logger(self, logger_name, log_file, level=logging.INFO):
    #     l = logging.getLogger(logger_name)
    #     l.propagate = False
    #     l.setLevel(level)
    #     l.removeHandler(logging.StreamHandler)
        
    #     formatter = logging.Formatter('%(message)s')
    #     fileHandler = logging.FileHandler(log_file, mode='w')
    #     fileHandler.setFormatter(formatter)
    #     fileHandler.setLevel(logging.DEBUG)
    #     l.addHandler(fileHandler)
    #     streamHandler = logging.StreamHandler()
    #     streamHandler.setLevel(logging.CRITICAL)
    #     l.addHandler(streamHandler)    
    #
    def open_open_logger2(self):
        filters = "{} Data Files (*.bin);;All Files (*.*)".format(self.title)
        selected_filter = "CAN Logger 2 Data Files (*.bin)"
        fname,_ = QFileDialog.getOpenFileName(self, 
                                            'Open CAN Logger 2 File',
                                            self.export_path,
                                            filters,
                                            selected_filter)
        if fname:
            file_size = os.path.getsize(fname)
            bytes_processed = 0
            #update the data package
            progress = QProgressDialog(self)
            progress.setMinimumWidth(600)
            progress.setWindowTitle("Processing CAN Logger 2 Data File")
            progress.setMinimumDuration(0)
            progress.setWindowModality(Qt.WindowModal)
            progress.setMaximum(file_size)
            progress_label = QLabel("Processed {:0.3f} of {:0.3f} Mbytes.".format(bytes_processed/1000000,file_size/1000000))
            progress.setLabel(progress_label)
        
            logger.debug("Importing file {}".format(fname))
            with open(fname,'rb') as f:
                while True:
                    line = f.read(512)
                    if len(line) < 512:
                        logger.debug("Reached end of file {}".format(fname))
                        break
                    #check integrity
                    bytes_to_check = line[0:508]
                    crc_value = struct.unpack('<L',line[508:512])[0]
                    
                    if binascii.crc32(bytes_to_check) != crc_value:
                        logger.warning("CRC Failed")
                        break
                    #print('CRC Passed')
                    #print(line)
                    #print(" ".join(["{:02X}".format(c) for c in line]))
                    prefix = line[0:4]
                    RXCount0 = struct.unpack('<L',line[479:483])[0]
                    RXCount1 = struct.unpack('<L',line[483:487])[0]   
                    RXCount2 = struct.unpack('<L',line[487:491])[0]
                    # CAN Controller Receive Error Counters.
                    Can0_REC = line[491]
                    Can1_REC = line[492]
                    Can2_REC = line[493]
                    # CAN Controller Transmit Error Counters
                    Can0_TEC = line[494]
                    Can1_TEC = line[495]
                    Can2_TEC = line[496]
                    # A constant ASCII Text file to preserve the original filename (and take up space)
                    block_filename = line[497:505]
                    #micro seconds to write the previous 512 bytes to the SD card (only 3 bytes so mask off the MSB)
                    buffer_write_time = struct.unpack('<L',line[505:509])[0] & 0x00FFFFFF
                    for i in range(4,487,25):
                        # parse data from records
                        channel = line[i]
                        timestamp = struct.unpack('<L',line[i+1:i+5])[0]
                        system_micros = struct.unpack('<L',line[i+5:i+9])[0]
                        can_id = struct.unpack('<L',line[i+9:i+13])[0]
                        dlc = line[i+13]
                        if dlc == 0xFF:
                            break
                        micros_per_second = struct.unpack('<L',line[i+13:i+17])[0] & 0x00FFFFFF
                        timestamp += micros_per_second/1000000
                        data_bytes = line[i+17:i+25]
                        data = struct.unpack('8B',data_bytes)[0]

                        #create an RP1210 data structure
                        sa =  can_id & 0xFF
                        priority = (can_id & 0x1C000000) >> 26
                        edp = (can_id & 0x02000000) >> 25
                        dp =  (can_id & 0x01000000) >> 24
                        pf =  (can_id & 0x00FF0000) >> 16
                        if pf >= 0xF0:
                            ps = (can_id & 0x0000FF00) >> 8
                            da = 0xFF
                        else:
                            ps = 0
                            da = (can_id & 0x0000FF00) >> 8
                        ps = struct.pack('B', ps)
                        pf = struct.pack('B', pf)
                        pgn = ps + pf + struct.pack('B', edp + dp)
                        rp1210_message = struct.pack('<L',system_micros) 
                        rp1210_message += b'\x01' 
                        rp1210_message += pgn  
                        rp1210_message += struct.pack('B', priority) 
                        rp1210_message += struct.pack('B', sa) 
                        rp1210_message += struct.pack('B', da) 
                        rp1210_message += data_bytes
                        self.rx_queues["Logger"].put((timestamp, rp1210_message))
                    bytes_processed += 512
                    progress.setValue(bytes_processed)
                    QCoreApplication.processEvents()
                    
            progress.deleteLater()
        

    def upload_data_package(self):
        returned_message = self.user_data.upload_data(self.data_package)
        logger.debug("returned_message:")
        logger.debug(returned_message)
        
    def edit_user_data(self):
        self.user_data.show_dialog() 

    def save_backup_file(self):
        #print(self.data_package["J1587"])
        self.save_file(backup=True)

    def clear_voltage_graph(self):
        self.J1939.clear_voltage_history()
        self.J1587.clear_voltage_history()

    def show_graphs(self):
        self.voltage_graph.show()
        self.speed_graph.show()

    def new_file(self):
        logger.debug("New File Selected.")
        self.create_new(True)

    def open_file(self):  
        """

        Returns: a tuple as (filename, data_dictionary)
                or 
                None if something went wrong.
        """  
        filters = "{} Data Files (*.cpt);;All Files (*.*)".format(self.title)
        selected_filter = "{} Data Files (*.cpt)".format(self.title)
        fname = QFileDialog.getOpenFileName(self, 
                                            'Open File',
                                            self.export_path,
                                            filters,
                                            selected_filter)
        if fname[0]:
            try:
                pgp_file_contents = pgpy.PGPMessage.from_file(fname[0])
                logger.info("User opened signed file {}".format(fname[0]))
            except:
                err_msg = "File {} was not a properly formatted {} file.".format(self.filename, self.title)
                QMessageBox.warning(self, "File Format Error", err_msg)
                logger.info(err_msg)
                logger.debug(traceback.format_exc())
                return

            try:
                new_data_package = json.loads(pgp_file_contents.message)
                logger.info("Loaded data package from pgp file contents.")
            except KeyError:
                err_msg = "File {} was missing critical information.".format(fname[0])
                QMessageBox.warning(self, "File Format Error", err_msg)
                logger.debug(traceback.format_exc())
                logger.info(err_msg)
                return
            except:
                err_msg = "Failed to load data_package."
                QMessageBox.warning(self, "File Loading Error", err_msg)
                logger.debug(traceback.format_exc())
                logger.info(err_msg)
                return

            try:
                if pgp_file_contents.is_signed:
                    logger.debug("File is signed.")
                    verification = self.verify_stream(pgp_file_contents, self.user_data.private_key)
                else:
                    verification = False
                    logger.debug("File is not signed.")
            except:
                logger.debug(traceback.format_exc())
                verification = False

            if verification:
                logger.info("The file was verified with a PGP signature")
            else:
                new_data_package["Warnings"].append("File signature not verified.")
                err_msg = "File {} was not verified. It may have been altered or the verification key is invalid.".format(fname[0])
                warn = QMessageBox.warning(self, "File Format Error",
                                           err_msg + "\nWould you like to proceed anyways?",
                                           QMessageBox.Yes | QMessageBox.No,
                                           QMessageBox.No)
                logger.info(err_msg)
                if warn == QMessageBox.No:
                    return
            #if reload:    
            self.data_package = new_data_package
            self.export_path, self.filename = os.path.split(fname[0])
            self.setWindowTitle('{} {}.{} - {}'.format(self.title,
                                                       TU_RP1210_version["major"],
                                                       TU_RP1210_version["minor"],
                                                       self.filename))
            self.data_package["File Name"] = self.filename 
            self.reload_data()
            logger.info("Opened File: {}".format(self.filename))
            logger.info("Export Path: {}".format(self.export_path))
            return (fname[0], new_data_package)   
        
    def reload_data(self):
        """
        Reload and refresh the data tables.
        """
        self.J1939.pgn_data_model.aboutToUpdate()
        self.J1939.j1939_unique_ids = self.data_package["J1939 Parameter Group Numbers"]
        self.J1939.pgn_data_model.setDataDict(self.J1939.j1939_unique_ids)
        self.J1939.pgn_data_model.signalUpdate()
        #TODO: Add the row and column resizers like the one for UDS.

        self.J1939.pgn_rows = list(self.J1939.j1939_unique_ids.keys())
        
        self.J1939.spn_data_model.aboutToUpdate()
        self.J1939.unique_spns = self.data_package["J1939 Suspect Parameter Numbers"]
        self.J1939.spn_data_model.setDataDict(self.J1939.unique_spns)
        self.J1939.spn_data_model.signalUpdate()

        self.J1939.dm01_data_model.aboutToUpdate()
        self.J1939.active_trouble_codes = self.data_package["Diagnostic Codes"]["DM01"]
        self.J1939.dm01_data_model.setDataDict(self.J1939.active_trouble_codes)
        self.J1939.dm01_data_model.signalUpdate()

        self.J1939.dm02_data_model.aboutToUpdate()
        self.J1939.previous_trouble_codes = self.data_package["Diagnostic Codes"]["DM02"]
        self.J1939.dm02_data_model.setDataDict(self.J1939.previous_trouble_codes)
        self.J1939.dm02_data_model.signalUpdate()

        self.J1939.dm04_data_model.aboutToUpdate()
        self.J1939.freeze_frame = self.data_package["Diagnostic Codes"]["DM04"]
        self.J1939.dm04_data_model.setDataDict(self.J1939.freeze_frame)
        self.J1939.dm04_data_model.signalUpdate()

        self.J1939.uds_data_model.aboutToUpdate()
        self.J1939.iso_recorder.uds_messages = self.data_package["UDS Messages"]
        self.J1939.uds_data_model.setDataDict(self.J1939.iso_recorder.uds_messages)
        self.J1939.uds_data_model.signalUpdate()
        self.J1939.uds_table.resizeRowsToContents()
        for c in self.J1939.uds_resizable_cols:
            self.J1939.uds_table.resizeColumnToContents(c)
        

        self.plot_decrypted_data()
        
    def plot_decrypted_data(self):
        pass

    def save_file(self, backup=False):
        """
        Save the file as a CPT (short for TruckCRYPT) file to the
        current path. 
        """

        #update the data package
        progress = QProgressDialog(self)
        progress.setMinimumWidth(600)
        progress.setWindowTitle("Saving and Digitally Signing Files")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMaximum(4)
        
        if backup:
            temp_name = os.path.basename(self.filename)
            temp_name.strip("Backup_")
            backup_name = "Backup_{}".format(temp_name)
            filename = os.path.normpath(os.path.join(self.export_path, backup_name))
        else:
            filename = os.path.normpath(os.path.join(self.export_path, self.filename))
            self.data_package["File Name"] = self.filename

        progress_label = QLabel("Saving and signing {} file to {}".format(self.title,filename))
        progress.setLabel(progress_label)

        saved_pgp_message = self.user_data.make_pgp_message(self.data_package)
        with open(filename,'w') as file_out:
            file_out.write(str(saved_pgp_message))

        if not backup:
            with open(filename[:-3] + 'json', 'w') as outfile:
                outfile.write(saved_pgp_message.message)
            msg = "Saved signed file to {}".format(filename)
            logger.info(msg)
            self.filename = os.path.basename(self.filename)
            self.setWindowTitle('{} {}.{} - {}'.format(self.title,
                                                       TU_RP1210_version["major"],
                                                       TU_RP1210_version["minor"],
                                                       self.filename))
            self.statusBar().showMessage(msg)
        progress.setValue(1)
        
        #CAN Logs
        progress_label.setText("Saving and signing CAN logs.")
        QCoreApplication.processEvents()
        self.sign_and_save_support_files(logging_dictionary["handlers"]["can_handler"]["filename"],
                                             " CAN Log", 
                                             "CAN Log File")
        progress.setValue(2)
        
        progress_label.setText("Saving and signing J1708 logs.")
        QCoreApplication.processEvents()
        self.sign_and_save_support_files(logging_dictionary["handlers"]["j1708_handler"]["filename"],
                                             " J1708 Log", 
                                             "J1708 Log File")
        progress.setValue(3)
        
        
        # Session Logs
        progress_label.setText("Saving and signing session debug logs.")
        QCoreApplication.processEvents()
        self.sign_and_save_support_files(logging_dictionary["handlers"]["file_handler"]["filename"],
                                         " Session Log", 
                                         "Session Log File")
        progress.setValue(4)
        progress_label.setText("Done with saving and signing all the user files.")
        QCoreApplication.processEvents()
        
        self.Components.rebuild_trees()
        return saved_pgp_message
    
    def sign_and_save_support_files(self, support_filename, suffix, key_name):
        """
        A routine to use PGP signing on all the supporting files for the cpt file. This
        includes CAN Logs, J1708 Logs, and Session logs.
        """
        filename = os.path.normpath(os.path.join(self.export_path, self.filename))
        try:
            
            with open(support_filename,'rb') as can_file:
                file_contents = can_file.read()
            pgp_message = self.user_data.make_pgp_message({suffix: base64.b64encode(file_contents).decode('ascii','strict')})
            if pgp_message.is_signed:
                can_signature = ", ".join([str(s) for s in pgp_message.signatures])
                can_signer = ", ".join(pgp_message.signers)
                if ", ".join(pgp_message.signers) == can_signer:
                    can_signer += " ({})".format(self.user_data.private_key.userids[0])
                else:
                    can_signer += " (Unknown ID)"
                logger.info("PGP Message Signers are {}".format(can_signer))
            else:
                can_signature = "No Signature Information Available"
                can_signer = None
            new_file_name = filename[:-4] + suffix +".pgp"
            if support_filename[-4:] == 'json':
                shutil.copy(support_filename, new_file_name[:-3]+support_filename[-4:])
            else:
                shutil.copy(support_filename, new_file_name[:-3]+support_filename[-3:])
            with open(new_file_name,'w') as file_out:
                file_out.write(str(pgp_message))
            can_file_size = humanize.naturalsize(os.path.getsize(new_file_name), binary=True)
            logger.debug("Saved{} with a size of {}".format(suffix,can_file_size))
        except:
            logger.debug(traceback.format_exc())
            can_signature = "There was an error digitally signing the {}.".format(suffix)
            can_signer = "Not Signed"
            can_file_size = None

        
        self.data_package["Network Logs"][key_name]["Name"] = new_file_name
        self.data_package["Network Logs"][key_name]["Size"] = can_file_size
        self.data_package["Network Logs"][key_name]["Signature"] = can_signature
        self.data_package["Network Logs"][key_name]["Signer"] = can_signer


    def save_file_as(self):
        filters = "{} Data Files (*.cpt);;All Files (*.*)".format(self.title)
        selected_filter = "{} Data Files (*.cpt)".format(self.title)
        fname = QFileDialog.getSaveFileName(self, 
                                            'Save File As',
                                            os.path.join(self.export_path,self.filename),
                                            filters,
                                            selected_filter)
        if fname[0]:
            if fname[0][-4:] ==".cpt":
                self.filename = fname[0]
            else:
                self.filename = fname[0]+".cpt"
            self.export_path, self.filename = os.path.split(fname[0])
            return self.save_file()
    
    def export_to_pdf(self):
        
        progress = QProgressDialog(self)
        progress.setMinimumWidth(600)
        progress.setWindowTitle("Generating PDF Report")
        progress.setMinimumDuration(0)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMaximum(2)

        logger.debug("Export to PDF Selected.")
        data_message = self.save_file()
        fname = os.path.join(self.export_path, self.filename)
        progress.setValue(1)
        QCoreApplication.processEvents()
        try:

            ret = self.pdf_engine.go(data_message, fname[:-3]+'pdf')
        except:
            logger.warning(traceback.format_exc())
            ret = "Error"
        logger.info("PDF Export returned {}".format(ret))
        progress.setValue(2)
        if ret == "Success":
            try:
                os.startfile(os.path.join(self.export_path, self.filename[:-3]+'pdf'), 'open')
            except:
                logger.debug(traceback.format_exc())
                QMessageBox.information(self,"PDF Generation","Successfully exported PDF file to {} in\n{}".format(self.filename[:-3]+'pdf', self.export_path))
        else:
            QMessageBox.warning(self,"PDF Generation","There was an issue generating the PDF: {}".format(ret))
        
        del self.pdf_engine    
        self.pdf_engine = FLAReportTemplate(self)
        
    def export_to_json(self):
        logger.debug("Export to JSON Selected.")
        self.save_file() 
        try:
            filename = os.path.join(self.export_path,self.filename)
            with open(filename[:-3] + 'json', 'w') as outfile:
                json.dump(self.data_package, outfile, indent=4, sort_keys=True)
            info = "Successfully exported JSON file from {}".format(filename)
            QMessageBox.information(self,"Export Successful",info)
            logger.info(info)
        except:
            logger.debug(traceback.format_exc())
            QMessageBox.warning(self,"JSON Export Error","There was an error exporting the JSON format from {}".format(filename))
        

    def confirm_quit(self):
        self.close()
    
    def closeEvent(self, event):
        result = QMessageBox.question(self, "Confirm Exit",
            "Are you sure you want to quit the program?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes)
        if result == QMessageBox.Yes:
            logger.debug("Quitting.")
            event.accept()
        else:
            event.ignore()

    def save_j1708_binary(self):
        logger.debug("Save J1708 Log to Binary")
    
    def save_j1708_csv(self):
        logger.debug("Save J1708 Log to Comma Separated Values Table")
    
    def save_j1939_binary(self):
        logger.debug("Save J1939 Log to Binary")
    
    def save_j1939_csv(self):
        logger.debug("Save J1939 Log to Comma Separated Values Table")

    def selectRP1210(self, automatic=False):
        logger.debug("Select RP1210 function called.")
        selection = SelectRP1210(self.title)
        logger.debug(selection.dll_name)
        if not automatic:
            selection.show_dialog()
        elif not selection.dll_name:
            selection.show_dialog()
        
        dll_name = selection.dll_name
        protocol = selection.protocol
        deviceID = selection.deviceID
        speed    = selection.speed

        if dll_name is None: #this is what happens when you hit cancel
            return
        #Close things down
        try:
            self.close_clients()
        except AttributeError:
            pass
        try:
            for thread in self.read_message_threads:
                thread.runSignal = False
        except AttributeError:
            pass
        
        progress = QProgressDialog(self)
        progress.setMinimumWidth(600)
        progress.setWindowTitle("Setting Up RP1210 Clients")
        progress.setMinimumDuration(3000)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMaximum(6)
      
        # Once an RP1210 DLL is selected, we can connect to it using the RP1210 helper file.
        self.RP1210 = RP1210Class(dll_name)
    
        if self.RP1210_toolbar is None:
            self.setup_RP1210_menus()
        
        # We want to connect to multiple clients with different protocols.
        self.client_ids={}
        self.client_ids["CAN"] = self.RP1210.get_client_id("CAN", deviceID, "{}".format(speed))
        progress.setValue(1)
        self.client_ids["J1708"] = self.RP1210.get_client_id("J1708", deviceID, "Auto")
        progress.setValue(2)
        self.client_ids["J1939"] = self.RP1210.get_client_id("J1939", deviceID, "{}".format(speed))
        progress.setValue(3)
        #self.client_ids["ISO15765"] = self.RP1210.get_client_id("ISO15765", deviceID, "Auto")
        #progress.setValue(3)
        
        logger.debug('Client IDs: {}'.format(self.client_ids))

        # If there is a successful connection, save it.
        file_contents={ "dll_name":dll_name,
                        "protocol":protocol,
                        "deviceID":deviceID,
                        "speed":speed
                       }
        with open(selection.connections_file,"w") as rp1210_file:
            json.dump(file_contents, rp1210_file)

        self.rx_queues={"Logger":queue.Queue(10000)}
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
            progress.setValue(3+i)
        
        if self.client_ids["J1939"] is None or self.client_ids["J1708"] is None:
            QMessageBox.information(self,"RP1210 Client Not Connected.","The default RP1210 Device was not found or is unplugged. Please reconnect your Vehicle Diagnostic Adapter (VDA) and select the RP1210 device to use.")
            self.voltage_graph.hide()
        else:
            self.voltage_graph.show()
            self.speed_graph.show()
        progress.deleteLater()

    def check_connections(self):
        '''
        This function checks the VDA hardware status function to see if it has seen network traffic in the last second.
        
        '''    
        network_connection = {}

        for key in ["J1939", "J1708"]:
            network_connection[key]=False            
            try:
                current_count = self.read_message_threads[key].message_count
                duration = time.time() - self.read_message_threads[key].start_time
                self.message_duration_label[key].setText("<html><img src='{}/icons/icons8_Connected_48px.png'><br>Client Connected<br>{:0.0f} sec.</html>".format(module_directory, duration))
                network_connection[key] = True
            except (KeyError, AttributeError) as e:
                current_count = 0
                duration = 0
                self.message_duration_label[key].setText("<html><img src='{}/icons/icons8_Disconnected_48px.png'><br>Client Disconnected<br>{:0.0f} sec.</html>".format(module_directory, duration))
                
            count_change = current_count - self.previous_count[key]
            self.previous_count[key] = current_count
            # See if messages come in. Change the 
            if count_change > 0 and not self.network_connected[key]: 
                self.status_icon[key].setText("<html><img src='{}/icons/icons8_Ok_48px.png'><br>Network<br>Online</html>".format(module_directory))
                self.network_connected[key] = True
            elif count_change == 0 and self.network_connected[key]:             
                self.status_icon[key].setText("<html><img src='{}/icons/icons8_Unavailable_48px.png'><br>Network<br>Unavailable</html>".format(module_directory))
                self.network_connected[key] = False

            self.message_count_label[key].setText("Message Count:\n{}".format(humanize.intcomma(current_count)))
            self.message_rate_label[key].setText("Message Rate:\n{} msg/sec".format(count_change))
        
        #Get ECM Clock and Date from J1587 if available
        self.data_package["Time Records"]["Personal Computer"]["Last PC Time"] = time.time()
        try:
            if self.ok_to_send_j1587_requests and self.client_ids["J1708"] is not None:
                for pid in [251, 252]: #Clock and Date
                    for tool in [0xB6]: #or 0xAC
                        j1587_request = bytes([0x03, tool, 0, pid])
                        self.RP1210.send_message(self.client_ids["J1708"], j1587_request)
        except (KeyError, AttributeError):
            pass
        
        # Request Time and Date
        try:
            if self.client_ids["J1939"] is not None: 
                self.send_j1939_request(65254)
        except (KeyError, AttributeError):
            pass

        #return True if any connection is present.
        for key, val in network_connection.items():
            if val: 
                return True
        return False

    def get_hardware_status_ex(self):
        """
        Show a dialog box for valid connections for the extended get hardware status command implemented in the 
        vendor's RP1210 DLL.
        """
        logger.debug("get_hardware_status_ex")
        for protocol,nClientID in self.client_ids.items():
            if nClientID is not None:
                self.RP1210.get_hardware_status_ex(nClientID)
                return
        QMessageBox.warning(self, 
                    "Connection Not Present",
                    "There were no Client IDs for an RP1210 device that support the extended hardware status command.",
                    QMessageBox.Cancel,
                    QMessageBox.Cancel)

    def get_hardware_status(self):
        """
        Show a dialog box for valid connections for the regular get hardware status command implemented in the 
        vendor's RP1210 DLL.
        """
        logger.debug("get_hardware_status")
        for protocol,nClientID in self.client_ids.items():
            if nClientID is not None:
                self.RP1210.get_hardware_status(nClientID)
                return
        QMessageBox.warning(self, 
                    "Connection Not Present",
                    "There were no Client IDs for an RP1210 device that support the hardware status command.",
                    QMessageBox.Cancel,
                    QMessageBox.Cancel)
                
    def display_detailed_version(self):
        """
        Show a dialog box for valid connections for the detailed version command implemented in the 
        vendor's RP1210 DLL.
        """
        logger.debug("display_detailed_version")
        for protocol, nClientID in self.client_ids.items():
            if nClientID is not None:
                self.RP1210.display_detailed_version(nClientID)
                return
        # otherwise show a dialog that there are no client IDs
        QMessageBox.warning(self, 
                    "Connection Not Present",
                    "There were no Client IDs for an RP1210 device.",
                    QMessageBox.Cancel,
                    QMessageBox.Cancel)
    
    def display_version(self):
        """
        Show a dialog box for valid connections for the extended get hardware status command implemented in the 
        vendor's RP1210 DLL. This does not require connection to a device, just a valid RP1210 DLL.
        """
        logger.debug("display_version")
        self.RP1210.display_version()

    def disconnectRP1210(self):
        """
        Close all the RP1210 read message threads and disconnect the client.
        """
        logger.debug("disconnectRP1210")
        for protocol, nClientID in self.client_ids.items():
            try:
                self.read_message_threads[protocol].runSignal = False
                del self.read_message_threads[protocol]
            except KeyError:
                pass
            self.client_ids[protocol] = None
        for n in range(128):
            try:
                self.RP1210.ClientDisconnect(n)
            except:
                pass
        logger.debug("RP1210.ClientDisconnect() Finished.")

    def get_iso_parameters(self, additional_params=[]):
        """
        Get Parameters defined in ISO 14229-1 Annex C.
        Additional 2-byte parameters can be passed in as a list.
        Returns a dictionary sieht the 2-byte request parameters as the key and the data as the value.
        """
        container = {}
        data_page_numbers = [[0xf1, b] for b in range(0x80,0x9F)]
        # There are 33 of these. We should move them to a JSON file and have dictionary that we can reference.
        for i in range(len(data_page_numbers)):
            QCoreApplication.processEvents()
            progress_message = "Requesting ISO Data Element 0x{:02X}{:02X}".format(data_page_numbers[i][0],data_page_numbers[i][1])
            logger.info(progress_message)
            message_bytes = bytes(data_page_numbers[i])
            data = self.isodriver.uds_read_data_by_id(message_bytes)
            logger.debug(data)
            container[bytes_to_hex_string(message_bytes)] = data
        return container

    def start_scan(self):
        """
        Perform a scan of the vehicle network by sending a series of request messages over the
        different vehicle networks. The requests are randomized.
        """
        if not self.check_connections():
            logger.info("No Vehicle Network Traffic Detected.")
            QMessageBox.warning(self, 
                    "No Vehicle Network",
                    "There was no vehicle network traffic detected. Please check the ignition key switch and battery voltage.",
                    QMessageBox.Cancel,
                    QMessageBox.Cancel)
            return

        if not self.GPS.connected:
            logger.info("No GPS detected at start of scan.")
            QMessageBox.warning(self, 
                    "No GPS Signal",
                    "The GPS signal is not detected. The location and GPS time data in the report may be inaccurate without a current GPS fix.",
                    QMessageBox.Cancel,
                    QMessageBox.Cancel)

        if self.ask_permission():
            logger.info("Starting Vehicle Network Scan.")
            # Ensure brakes, engine and global sources are in the source addresses.
            for sa in [0x00, 0x0B, 0xFF]:
                if sa not in self.source_addresses:
                    self.source_addresses.append(sa)
            # Log the time when this starts
            self.extraction_time_pc = time.time()
            try:
                self.extraction_time_gps = self.gps_thread.gpstime
            except:
                logger.debug(traceback.format_exc())
                self.extraction_time_gps = 0
            logger.debug("PC Time = {}, GPS time = {}, PC - GPS = {:02f} seconds".format(self.extraction_time_pc, 
                self.extraction_time_gps, self.extraction_time_pc - self.extraction_time_gps))

            passes = 5
            total_requests = passes * (len(self.J1939.j1939_request_pgns) * len(self.source_addresses) + 33) #for ISO

            progress = QProgressDialog(self)
            progress.setMinimumWidth(600)
            progress.setWindowTitle("Requesting Vehicle Network Messages")
            progress.setMinimumDuration(0)
            #progress.setWindowModality(Qt.WindowModal) # Improves stability of program
            progress.setModal(False) #Will lead to instability when trying to click around.
            progress.setMaximum(int(total_requests*1.02))
            progress_label = QLabel("Asking for UDS data (ISO 15765)")
            progress.setLabel(progress_label)

            request_count = int(0.021*total_requests)
            progress.setValue(request_count)
            
            

            self.J1587.j1587_request_pids.sort(reverse=True)

            j1587_tool_mids = [0xac, 0xb6]
            for request_pass in range(passes):
                self.get_iso_parameters()
                j1587_parameter_count = 0
                logger.info("Starting Pass {}".format(request_pass))
                for pgn in self.J1939.j1939_request_pgns:
                    if pgn in self.long_pgn_timeouts:  
                        self.request_timeout = self.long_pgn_timeout_value
                    else:
                        self.request_timeout = self.short_pgn_timeout_value
                    logger.debug("Sending J1939 request for PGN {}".format(pgn))
                    progress.setValue(request_count)
                    try:
                        pgn_name = self.J1939.j1939db["J1939PGNdb"]["{}".format(pgn)]["Name"]
                    except:
                        pgn_name= ""
                    progress_label.setText("Pass {}: Requesting PGN {} - {}".format(request_pass+1, pgn, pgn_name))
                    
                    random.shuffle(self.source_addresses)
                    for address in self.source_addresses:
                        request_count += 1
                        # Send the request for a PGN onto the J1939 Network
                        # and wait for a response
                        start_time = time.time()
                        self.send_j1939_request(pgn, DA=address)
                        while (not progress.wasCanceled() and
                               time.time() - start_time < self.request_timeout and 
                               not self.find_j1939_data(pgn, sa=address)):
                            time.sleep(.1)
                            # Send out the request 3 times
                            QApplication.processEvents() 
                            #time.sleep(.01) # do nothing while we wait. 

                        if progress.wasCanceled():
                            logger.info("Network scan stopped by user.")
                            progress.deleteLater()
                            self.start_oem_scan()
                            return
                    self.Components.rebuild_trees()

                    #J1587
                    tool = j1587_tool_mids[request_pass % 2] #Switch between requesting tool MIDs
                    j1587_parameter_count += 1
                    try:
                        pid = self.J1587.j1587_request_pids[j1587_parameter_count]
                        if pid < 255:
                            j1587_request = bytes([0x03, tool, 0, pid])
                        else:
                            j1587_request = bytes([0x04, tool, 0, 255, pid % 256])
                        self.RP1210.send_message(self.client_ids["J1708"], j1587_request)
                        logger.debug("Sent J1587 request for PID {}".format(pid))   
                    except IndexError:
                        pass   

                random.shuffle(self.J1939.j1939_request_pgns)
                random.shuffle(self.J1587.j1587_request_pids) 
            
            progress.deleteLater()
            logger.info("Finished with Standards Based Data Extraction.")
            
            self.start_oem_scan()
    
    def start_oem_scan(self):
        #override this function 
        pass
  
    def copy_and_sign_files(self, additional_files=[]):
        
        self.save_file_as()

        with open(os.path.join(self.export_path,'PGPpublicKeyFile.txt'), 'w') as outfile:
            outfile.write(str(self.user_data.private_key.pubkey))
        with open(os.path.join(self.export_path,'README.txt'), 'w') as outfile:
            outfile.write("The files in this directory ending in pgp are signed PGPmessage files that have contain the original data. The files can be verified using the PGP public key.")
        
        file_list = [self.data_package["Network Logs"]["CAN Log File Name"],
                     self.data_package["Network Logs"]["J1708 Log File Name"],
                     self.title + ".log"
                    ] + additional_files
        logger.debug("Signing and Copying the following files to {}".format(self.export_path))
        logger.debug(file_list)
        main_file = self.filename[:-4]
        
        for file in file_list:
            self.sign_file(file)
            shutil.copy2(file, os.path.join(self.export_path, main_file + ' ' + file))
            shutil.copy2(file + ".pgp", os.path.join(self.export_path, main_file + ' ' + file + ".pgp"))
    
    def open_and_sign_file(self):
        fname = QFileDialog.getOpenFileName(self, 'Open file')
        if fname[0]:
            signed_file = self.sign_file(fname[0])
            if self.verify_file(signed_file):
                msg_box = QMessageBox.information(self, "Signed and Verified File",
                "A signature file was saved in the same directory as\n{}".format(signed_file),
                QMessageBox.Ok,
                QMessageBox.Ok)          
            else:
                QMessageBox.warning(self, 
                    "Could Not sign or Verify File",
                    "There was a problem signing and verifying the file\n{}".format(fname[0]),
                    QMessageBox.Cancel,
                    QMessageBox.Cancel)


    def open_and_verify_file(self):
        fname = QFileDialog.getOpenFileName(self, 'Open File to Verify')
        if fname[0]:
            file_ok = self.verify_file(fname[0])
        else:
            return

        if file_ok is None:
            return
        elif file_ok:
            msg_box = QMessageBox.information(self, "Verified File",
                "The File and the Signature match, which means the selected file is authentic.\nWould you like an Authenication Report in PDF format?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes)
            if msg_box == QMessageBox.Yes:
                logger.debug("Generating authenticity report for {}".format(fname[0]))
                self.generate_authenticity_report(fname[0])
                
        else:
            QMessageBox.warning(self, 
                "Could Not Verify File",
                "The file did not have a digital signature, or\nthe selected file did not match the digital signature, which means it could have been altered, or\nthe signature is for a different file.",
                QMessageBox.Cancel,
                QMessageBox.Cancel)

    def generate_authenticity_report(self, file_to_verify_name):
        """
        Only call this function if the report is known to be good.
        """
        filters = "Portable Document Format (*.pdf);;All Files (*.*)"
        selected_filter = "Portable Document Format (*.pdf)"
        fname = QFileDialog.getSaveFileName(self, 
                                            'Save Authenticity Report File As',
                                            os.path.join(self.export_path,file_to_verify_name + '_verification.pdf'),
                                            filters,
                                            selected_filter)
        if fname[0]:
            data_dict = {}
            data_dict["Signer"] = self.data_package["User Data"]
            with open(file_to_verify_name, 'rb') as f:
                data_dict["First File Bytes"] = f.read(150)
            data_dict["File Name"] = file_to_verify_name
            data_dict["Signature File Name"] = file_to_verify_name + '.pgp' 
            data_dict["Signature"] = 'PGP Signature Block'
            data_dict["Public Key"] = str(self.user_data.private_key.pubkey)
            logger.debug("Verification Report inputs:")
            logger.debug(" {}".format(data_dict))
            report = SignatureVerificationReport(fname[0], data_dict)
            result = report.go()
            logger.info("Authenticity Report Build returned: {}".format(result))
            if result == "Success":
                msg_box = QMessageBox.information(self, "Successful Export",
                    "The authenticity report was successfully exported to\n{}".format(fname[0]),
                    QMessageBox.Ok,
                    QMessageBox.Ok)
            else:
                QMessageBox.warning(self, 
                    "Permission Error",
                    "The Authenticity report failed to export to PDF.\nPlease close the following file and try again.\n{}".format(fname[0]),
                    QMessageBox.Close,
                    QMessageBox.Close)  
    
    def sign_file(self, filename,show_dialog=True):
        logger.info("Begin PGP Signing of {}".format(filename))
        try:
            with open(filename,'rb') as f:
                message = f.read()
        except FileNotFoundError:
            logger.debug(traceback.format_exc())
            return False

        new_file = filename + ".pgp"
        try:
            signed_stream = self.sign_stream(message, self.user_data.private_key)
            
            with open(new_file, 'w') as signed_file:
                signed_file.write(str(signed_stream))
            info_message = "Successfully wrote a signed PGP message to {}".format(new_file)
            logger.info(info_message)
            if show_dialog:
                msg_box = QMessageBox.information(self, "Successful Signing",
                    info_message,
                    QMessageBox.Ok,
                    QMessageBox.Ok)
            return new_file
        except:
            logger.debug(traceback.format_exc())
            warning_message = "Encountered an error when writing a signed PGP message to {}".format(new_file)
            logger.info(warning_message)
            QMessageBox.warning(self, 
                    "File Writing Error",
                    warning_message,
                    QMessageBox.Close,
                    QMessageBox.Close)
            return False    
    
    def load_private_key(self, private_key_file):
        #Load the key
        try:
            private_key, properties = pgpy.PGPKey.from_file(private_key_file)
            logger.info("Using a PGP private key to sign files with the following fingerprint {}".format(private_key.fingerprint))
            self.user_data.private_key = private_key
            self.user_public_key = private_key.pubkey
        except FileNotFoundError:
            logger.debug(traceback.format_exc())
            logger.info("Missing Private Key File.")
            #TODO open dialog 
        except ValueError:
            logger.debug(traceback.format_exc())
            logger.info("Expecting PGP data")
        except:
            logger.debug(traceback.format_exc())


    def sign_stream(self, message):
        """
        Returns: a signed PGP message
        """
        # Make a PGP message and sign it.
        try:
            signed_stream = pgpy.PGPMessage.new(message,
                                 cleartext=False,
                                 sensitive=False,
                                 compression=CompressionAlgorithm.ZIP)
            signed_stream |= self.user_data.private_key.sign(signed_stream)
            return signed_stream
        except:
            logger.debug(traceback.format_exc())
            return

    def verify_stream(self, message, key):
        """
        message should be a PGP signed message.
        key should be a PGP public or private key 

        Returns: verified origninal file
        """
        try:
            result = key.verify(message)
            for verified, by, signature, subject in result.good_signatures:
                if verified == True:
                    logger.debug("Message signature verified by key: {}".format(by))
                    logger.info("The file is verified.")
                    return subject
            
            # If no good signatures    
            warning_message = "There were no good signatures found. The file is NOT verified."
            logger.info(warning_message)
            QMessageBox.warning(self, 
                    "Signature Not Verified",
                    warning_message,
                    QMessageBox.Close,
                    QMessageBox.Close)
            return False

        except:
            logger.debug(traceback.format_exc())
            warning_message = "There was an issue with verifying a message data stream."
            logger.info(warning_message)
            QMessageBox.warning(self, 
                    "Signature Verification Error",
                    warning_message,
                    QMessageBox.Close,
                    QMessageBox.Close)
            return False

    def verify_file(self, filename):
        """
        filename should be a file that was saved as a PGP message and signed with the user's private key.
        """
        #Load the PGP message
        try:
            message = pgpy.PGPMessage.from_file(filename)
            logger.info("Successfully opened {} as a PGP message.".format(filename))
        except:
            logger.debug(traceback.format_exc())
            logger.info("Failed to open {} as a PGP message.".format(filename))
            QMessageBox.warning(self, 
                "Invalid File",
                "Failed to open {} as a valid PGP message. Be sure the file was saved by {}".format(filename,self.title),
                QMessageBox.Close,
                QMessageBox.Close)
            return False
        
        return self.verify_stream(message, self.user_data.private_key)
    
    def send_can_message(self, data_bytes):
        #initialize the buffer
        if self.client_ids["CAN"] is not None:
            message_bytes = b'\x01'
            message_bytes += data_bytes
            self.RP1210.send_message(self.client_ids["CAN"], message_bytes)

    def send_j1939_message(self, PGN, data_bytes, DA=0xff, SA=0xf9, priority=6, BAM=True):
        #initialize the buffer
        if self.client_ids["J1939"] is not None:
            b0 =  PGN & 0xff
            b1 = (PGN & 0xff00) >> 8
            b2 = (PGN & 0xff0000) >> 16
            if BAM and len(data_bytes) > 8:
                priority |= 0x80
            message_bytes = bytes([b0, b1, b2, priority, SA, DA])
            message_bytes += data_bytes
            self.RP1210.send_message(self.client_ids["J1939"], message_bytes)
    
    def find_j1939_data(self, pgn, sa=0):
        '''
        A function that returns bytes data from the data dictionary holding J1939 data.
        This function is used to check the presence of data in the dictionary.
        '''
        
        try:
            return self.J1939.j1939_unique_ids[repr((pgn,sa))]["Bytes"]
        except KeyError:
            return False
          

    def send_j1939_request(self, PGN_to_request, DA=0xff, SA=0xf9): 
        if self.client_ids["J1939"] is not None:
            b0 =  PGN_to_request & 0xff
            b1 = (PGN_to_request & 0xff00) >> 8
            b2 = (PGN_to_request & 0xff0000) >> 16
            message_bytes = bytes([0x00, 0xEA, 0x00, 0x06, SA, DA, b0, b1, b2])
            self.RP1210.send_message(self.client_ids["J1939"], message_bytes)

    def send_j1587_request(self, pid, tool = 0xB6): 
        if self.client_ids["J1708"] is not None:
            if pid < 255:
                j1587_request = bytes([0x03, tool, 0, pid])
            elif pid > 256 and pid < 65535:
                j1587_request = bytes([0x04, tool, 255, 0, pid%256])
            else:
                return 
            self.RP1210.send_message(self.client_ids["J1708"], j1587_request)    

    def setup_gps(self, dialog=True):
        
        logger.debug("Setup GPS with file.")
        success = self.GPS.try_GPS()
        if not success:
            logger.debug("Setup GPS with dialog box.")
            self.GPS.run()
        
        if self.GPS.connected:
            self.gps_icon.setText("<html><img src='{}/icons/icons8_GPS_Signal_48px.png'><br>Connected on {}</html>".format(module_directory,self.GPS.ser.port))
             
            self.gps_queue = queue.Queue()
            self.gps_thread = GPSThread(self.gps_queue,self.GPS.ser)
            self.gps_thread.setDaemon(True) #needed to close the thread when the application closes.
            self.gps_thread.start()
            logger.debug("Started GPS Thread.")

            self.gps_timer = QTimer()
            self.gps_timer.timeout.connect(self.update_gps)
            self.gps_timer.start(1000) #milliseconds
            logger.debug("Started gps_timer loop")
        else:
            logger.debug("Setup GPS Failed.")
            self.gps_icon.setText("<html><img src='{}/icons/icons8_GPS_Disconnected_48px.png'><br>Disconnected</html>".format(module_directory))
       

    def update_gps(self):
        try:
            if self.gps_thread.gpslat is None:
                self.gps_lat_label.setText("Searching...")
            else:
                self.gps_lat_label.setText("Latitude:\n{:9.6f}".format(self.gps_thread.gpslat))
            
            if self.gps_thread.gpslon is None:
                self.gps_lon_label.setText("Searching...")
            else:
                self.gps_lon_label.setText("Longitude:\n{:9.6f}".format(self.gps_thread.gpslon))
            
            if self.gps_thread.gpstime is not None and self.gps_thread.gps.time_since_fix() < 1:
                # if time.daylight:
                #     corrected_time = time.localtime(self.gps_thread.gpstime - time.altzone)
                # else:
                #     corrected_time = time.localtime(self.gps_thread.gpstime - time.timezone)
                self.gps_time_label.setText(time.strftime("GPS Time:\n%d %b %Y %H:%M:%S\n%Z", time.localtime(self.gps_thread.gpstime)))
                self.data_package["Time Records"]["Personal Computer"]["PC Time at Last GPS Reading"]=time.time()
                self.data_package["Time Records"]["Personal Computer"]["Last GPS Time"] = self.gps_thread.gpstime
                self.data_package["Time Records"]["Personal Computer"]["PC Time minus GPS Time"] = time.time() - self.gps_thread.gpstime
                self.data_package["GPS Data"].update({"Latitude": self.gps_thread.gpslat,
                                                      "Longitude": self.gps_thread.gpslon,
                                                      "Altitude": self.gps_thread.gpsalt,
                                                      "GPS Time": self.gps_thread.gpstime,
                                                      "System Time": time.time()})
                self.gps_icon.setText("<html><img src='{}/icons/icons8_GPS_Signal_48px.png'><br>Connected on {}</html>".format(module_directory,self.GPS.ser.port))
    
            else:
                self.gps_time_label.setText("{}".format("Searching..."))  
                self.gps_icon.setText("<html><img src='{}/icons/icons8_GPS_Disconnected_48px.png'><br>Disconnected</html>".format(module_directory))
                self.gps_lat_label.setText("Searching...")
                self.gps_lon_label.setText("Searching...")
            return
        except:
            logger.debug(traceback.format_exc())
            self.gps_icon.setText("<html><img src='{}/icons/icons8_GPS_Disconnected_48px.png'><br>Disconnected</html>".format(module_directory))
        
        try:
            del self.gps_thread
            del self.gps_timer
            del self.gps_queue
            self.GPS.ser = None
        except:
            logger.debug(traceback.format_exc())

    def setup_scan(self):
        logger.debug("Setup Network Requests")

    def ask_permission(self):
        permission_box = QMessageBox()
        permission_box.setIcon(QMessageBox.Question)
        permission_box.setWindowTitle('Permission')
        permission_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        permission_box.setDefaultButton(QMessageBox.No)
        permission_box.setText("Do you have proper permission to download data?")
        return_button = permission_box.exec_()
        if return_button == QMessageBox.Yes:
            logger.info("User acknowledged proper permission to access vehicle data.")
            self.data_package["Time Records"]["Personal Computer"]["Permission Time"] = time.time()
            return True
        else:
            return False

    # def start_cat(self):
    #     pass
    

    def read_rp1210(self):
        # This function needs to run often to keep the queues from filling
        #try:
        for protocol in self.rx_queues.keys():
            if protocol in self.rx_queues:
                start_time = time.time()
                while self.rx_queues[protocol].qsize():
                    #Get a message from the queue. These are raw bytes
                    #if not protocol == "J1708":
                    rxmessage = self.rx_queues[protocol].get()                                   
                    if protocol == "CAN":
                        #Just great a log file.
                        CANlogger.info("{:0.6f},{},{:08X},{},".format(rxmessage[0],
                                                                      rxmessage[1],
                                                                      rxmessage[2],
                                                                      rxmessage[3]) + 
                                       ",".join("{:02X}".format(c) for c in rxmessage[4]))
                    
                    elif protocol == "J1939" or protocol == "Logger" :
                        try:
                            self.J1939.fill_j1939_table(rxmessage)
                            #J1939logger.info(rxmessage)
                        except:
                            logger.debug(traceback.format_exc())
                    elif protocol == "J1708":
                        try:
                            self.J1587.fill_j1587_table(rxmessage)    
                            J1708logger.info("{:0.6f},".format(rxmessage[0]) + ",".join("{:02X}".format(c) for c in rxmessage[1]))
                        except:
                            logger.debug(traceback.format_exc())
                    
                    if time.time() - start_time + 50 > self.update_rate: #give some time to process events
                        logger.debug("Can't keep up with messages.")
                        return
    def register_software(self):
        logging.debug("Register Software Request")                      
        self.edit_user_data()
        
    def show_about_dialog(self):
        logger.debug("show_about_dialog Request")
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText("About {}".format(self.title))
        msg.setInformativeText("""Icons by Icons8\nhttps://icons8.com/""")
        msg.setWindowTitle("About")
        msg.setDetailedText("There will be some details here.")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.setWindowModality(Qt.ApplicationModal)
        msg.exec_()



    def get_address_from_gps(self):
        if self.GPS.lat and self.GPS.lon:
            try:
                geolocator = Nominatim()
                loc = geolocator.reverse((self.lat, self.lon), timeout=5, language='en-US')
                gps_location_string = loc.address
                self.general_location_gps = gps_location_string
            except GeopyError:
                pass  

    def close_clients(self):
        logger.debug("close_clients Request")
        for protocol,nClientID in self.client_ids.items():
            logger.debug("Closing {}".format(protocol))
            self.RP1210.disconnectRP1210(nClientID)
            if protocol in self.read_message_threads:
                self.read_message_threads[protocol].runSignal = False
        try:
            self.GPS.ser.close()
        except:
            pass
        
        logger.debug("Exiting.")

    def decode_can_log_file(self, filename):
        pass