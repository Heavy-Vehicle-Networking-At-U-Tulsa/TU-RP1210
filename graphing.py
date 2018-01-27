
#from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMessageBox,
                             QFileDialog,
                             QLabel,
                             QGridLayout,
                             QPushButton,
                             QGroupBox,
                             QDialog,
                             QWidget,
                             QTableWidget,
                             QAbstractItemView,
                             QCheckBox,
                             QVBoxLayout)
from matplotlib.backends import qt_compat
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import matplotlib.dates as md
import datetime as dt
import os
import csv
from RP1210Functions import *
import logging
logger = logging.getLogger(__name__)

from matplotlib import rcParams
rcParams.update({'figure.autolayout': True}) #Depends on matplotlib from graphing
markers = [ "D", "o", "v", "*", "^", "<", ">", "1", "2", "3", "4", "8", "s", "p", "P", "h", "H", "+", "x", "X", "d", "|"]
 
class GraphDialog(QDialog):
    def __init__(self, parent=None, title="Graph"):
        super(GraphDialog, self).__init__(parent)
        self.setWindowTitle(title)
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.data = {}

        self.ax = self.figure.add_subplot(111)
        self.ymin = None
        self.ymax = None
        self.x_label = ""
        self.y_label = ""
        self.title = ""

        self.update_button = QCheckBox("Dynamically Update Table")
        self.update_button.setChecked(True)

        # set the layout
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.update_button)
        layout.addWidget(self.toolbar)
        self.setLayout(layout)
        self.show()
         
    def plot(self):
        ''' plot data '''
        self.ax.cla()
        #self.ax.hold(False)
        for key, value in self.data.items():
            self.ax.plot(value["X"],value["Y"],value["Marker"],label=key)
        self.ax.grid(True)
        self.ax.legend()
        [xmin, xmax, ymin, ymax] = self.ax.axis()
        try:
            self.ax.axis([xmin, xmax, self.ymin, self.ymax])
        except:
            pass
        xfmt = md.DateFormatter('%Y-%m-%d %H:%M:%S')
        self.ax.xaxis.set_major_formatter(xfmt)
        self.figure.autofmt_xdate()
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_title(self.title)
        if self.update_button.isChecked():
            self.canvas.draw()
    
    def plot_xy(self):
        self.ax.cla()
        #self.ax.hold(False)
        for key, value in self.data.items():
            self.ax.plot(value["X"], value["Y"], value["Marker"],label=key)
        self.ax.grid(True)
        self.ax.legend()
        [xmin, xmax, ymin, ymax] = self.ax.axis()
        try:
            self.ax.axis([xmin, xmax, self.ymin, self.ymax])
        except:
            pass
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_title(self.title)
        if self.update_button.isChecked():
            self.canvas.draw()
    
    def add_data(self, data, marker='*-', label=""):
        x, y = zip(*data) #unpacks a list of tuples
        dates = [dt.datetime.fromtimestamp(ts) for ts in x]
        self.data[label] = {"X": dates, "Y": y, "Marker": marker}
    
    def add_xy_data(self, data, marker='*-', label=""):
        x, y = zip(*data) #unpacks a list of tuples
        self.data[label] = {"X": x, "Y": y, "Marker": marker}
        

    def set_yrange(self,min_y, max_y):
        self.ymax = max_y
        self.ymin = min_y
            
    
    def set_xlabel(self,label):
        self.x_label = label
    
    def set_ylabel(self,label):
        self.y_label = label
    
    def set_title(self,label):
        self.title = label
    
class GraphTab(QWidget):
    def __init__(self, parent=None, tabs=None, tab_name="Graph Tab"):
        super(GraphTab, self).__init__(parent)
        logger.debug("Setting up Graph Tab.")
        self.root = parent
        self.tabs = tabs
        self.tab_name = tab_name
        self.data_list=[]
        self.init_ui()
    
    def init_ui(self):
        self.graph_tab = QWidget()
        self.tabs.addTab(self.graph_tab, self.tab_name)
        logger.debug("Making Attribution Box")
        attribution_box = QGroupBox("Event Attribution Data")
        tab_layout = QGridLayout()
        self.graph_tab.setLayout(tab_layout)

        self.event_name_label = QLabel("Name of Event: ")
        self.ecm_rtc_label = QLabel("ECM Real Time Clock at Event: ")
        self.actual_rtc_label = QLabel("Actual Real Time Clock at Event: ")
        self.engine_hours_label = QLabel("Engine Hours at Event: ")
        self.odometer_label = QLabel("Distance Reading at Event: ")

        attribution_layout = QVBoxLayout()
        attribution_layout.addWidget(self.event_name_label)
        attribution_layout.addWidget(self.ecm_rtc_label)
        attribution_layout.addWidget(self.actual_rtc_label)
        attribution_layout.addWidget(self.engine_hours_label)
        attribution_layout.addWidget(self.odometer_label)
        attribution_box.setLayout(attribution_layout)
        logger.debug("Finished Setting Attribution Layout")
        
        self.data_table = QTableWidget()
        self.data_table.setSelectionBehavior(QAbstractItemView.SelectColumns)
        logger.debug("Finished with Data Table")
        
        self.csv_button = QPushButton("Export CSV")
        self.csv_button.clicked.connect(self.export_csv)
        logger.debug("Finished with CSV")

        self.figure = plt.figure(figsize=(7,9))
        self.canvas = FigureCanvas(self.figure)
        self.top_axis = self.figure.add_subplot(3,1,1)
        self.top_axis.set_ylabel("Road Speed (mph)")
        self.middle_axis = self.figure.add_subplot(3,1,2)
        self.middle_axis.set_ylabel("Throttle Position (%)")
        self.bottom_axis = self.figure.add_subplot(3,1,3)
        self.bottom_axis.set_ylabel("Brake Switch Status")
        self.bottom_axis.set_xlabel("Event Time (sec)")
        self.canvas.draw()

        self.toolbar = NavigationToolbar(self.canvas, self.graph_tab)
        logger.debug("Finished with toolbar")

        # set the layout
        
        tab_layout.addWidget(attribution_box,0,0,1,1)
        tab_layout.addWidget(self.data_table,1,0,1,1)
        tab_layout.addWidget(self.csv_button,2,0,1,1)
        tab_layout.addWidget(self.canvas,0,1,2,1)
        tab_layout.addWidget(self.toolbar,2,1,1,1) 
        
        logger.debug("Finished with UI for Tab {}".format(self.tab_name))

    def export_csv(self):
        logger.debug("Export CSV")
        filters = "Comma Separated Values (*.csv);;All Files (*.*)"
        selected_filter = "Comma Separated Values (*.csv)"
        fname = QFileDialog.getSaveFileName(self, 
                                            'Export CSV',
                                            self.tab_name + ".csv",
                                            filters,
                                            selected_filter)
        if fname[0]:
            if fname[0][-4:] ==".csv":
                filename = fname[0]
            else:
                filename = fname[0]+".csv"
            try:
                with open(filename,'w', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(["Synercon Technologies, LLC"])

                    writer.writerow(["Date of Creation:", "{}".format(get_local_time_string(time.time()))])
                    
                    
                    writer.writerows(['',["Vehicle Component Information"]])
                    writer.writerows(get_list_from_dict(self.root.data_package["Component Information"]))

                    writer.writerows(['',["Vehicle Distance Information"]])
                    writer.writerows(get_list_from_dict(self.root.data_package["Distance Information"]))

                    writer.writerows(['',["Vehicle Time Information"]])
                    writer.writerows(get_list_from_dict(self.root.data_package["ECU Time Information"]))


                    writer.writerows(['',["Event Attribution Data"]])
                    writer.writerow([''] + self.event_name_label.text().split(": "))
                    writer.writerow([''] + self.ecm_rtc_label.text().split(": "))
                    writer.writerow([''] + self.actual_rtc_label.text().split(": "))
                    writer.writerow([''] + self.engine_hours_label.text().split(": "))
                    writer.writerow([''] + self.odometer_label.text().split(": "))
                    writer.writerows(['',["Event Table Data"]])
                    writer.writerows(self.data_list)

                    writer.writerows(['',["User Data"]])
                    writer.writerows(self.root.user_data.get_user_data_list())
                self.root.sign_file(filename)
                base_name = os.path.basename(filename)
                QMessageBox.information(self,"Export Success","The comma separated values file\n{}\nwas successfully exported. A verification signature was also saved as\n{}.".format(base_name,base_name+".signature"))
            
            except PermissionError:
                logger.info("Permission Error - Please close the file and try again.")
                QMessageBox.warning(self,"Permission Error","Permission Error\nThe file may be open in another application.\nPlease close the file and try again.")
            
    

    def plot_xy(self):
        for key, value in self.data.items():
            self.ax.plot(value["X"], value["Y"], value["Marker"],label=key)
        self.ax.grid(True)
        self.ax.legend()
        [xmin, xmax, ymin, ymax] = self.ax.axis()
        try:
            self.ax.axis([xmin, xmax, self.ymin, self.ymax])
        except:
            pass
        self.ax.set_xlabel(self.x_label)
        self.ax.set_ylabel(self.y_label)
        self.ax.set_title(self.title)
        if self.update_button.isChecked():
            self.canvas.draw()