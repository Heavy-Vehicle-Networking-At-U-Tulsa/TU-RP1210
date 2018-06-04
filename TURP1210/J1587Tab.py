
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
import base64
import time
import calendar
import struct
import json
import math
import traceback
from TURP1210.RP1210.RP1210Functions import *
from TURP1210.TableModel.TableModel import *
from TURP1210.Graphing.graphing import *

import logging
logger = logging.getLogger(__name__)

class J1587Tab(QWidget):
    def __init__(self,parent,tabs):
        super(J1587Tab,self).__init__()
        self.root = parent
        self.tabs = tabs
        logger.debug("Setting up J1587 Tab.")
        self.J1587_tab = QWidget()
        self.tabs.addTab(self.J1587_tab,"J1587 Data")
        self.init_ui()
        self.J1587_unique_ids = {}
        self.J1587_table_index = {}
        self.battery_potential = {}
        self.byte_set = {}

        self.J1587db = self.root.j1587db
        logger.debug("Done Loading J1587db")

        self.j1587pids = [38, 46, 74, 84, 85, 86, 87, 88, 91, 92, 94, 95, 96, 97, 98, 100, 102, 103, 104, 108, 110, 113, 127, 134, 150, 151, 152,
                          158, 161, 162, 163, 166, 167, 168, 171, 172, 174, 177, 182, 184, 185, 188,
                          189, 190, 191, 193, 194, 195, 196, 206, 209, 228, 233, 234, 235, 236, 237, 241, 242, 243, 244, 245,
                          246, 247, 248, 249, 250, 251, 252, 253, 436, 439, 507, 522, 560, 573, 589, 1002, 1003, 1028,
                          1122, 1123, 1124, 1125, 1126]

        self.j1587_request_pids = [38, 46, 74, 84, 87, 88, 91, 92, 94, 95, 96, 100, 102, 103, 104, 110,
                                   127, 134, 150, 152, 158, 161, 162, 163, 166, 167, 168, 171, 172, 174, 177, 182, 184,
                                   185, 188, 189, 190, 191, 193, 194, 195, 196, 206, 228, 233, 234, 235, 236, 237,
                                   243, 244, 245, 246, 247, 248, 250, 251, 252, 436, 439, 507, 522, 560, 573,
                                   589, 1002, 1003, 1028, 1122, 1123, 1124, 1125, 1126]


        self.pids_to_not_decode = [197, 198, 254]

        self.j1587responses = {}
        self.mids = [] # 128, 130, 136]
        # for mid in self.mids:
        #     self.battery_potential[source_key] = []
        self.multi_section_messages = {}
        self.j1587_count = 0  # successful 1708 messages
        self.more_info_pids = {}
        self.to_send_1587_list = {}
    
    def init_ui(self):
        tab_layout = QVBoxLayout()
        
        self.J1587_id_table = QTableWidget()
        J1587_id_box = QGroupBox("J1587 Messages")
        #self.tabs.addTab(J1587_id_box,"J1587 Data")
        self.add_message_button = QCheckBox("Dynamically Update Table")
        self.add_message_button.setChecked(True)

        clear_button = QPushButton("Clear J1587 Table")
        clear_button.clicked.connect(self.clear_J1587_table)
        
        #Create a layout for that box 
        J1587_id_box_layout = QGridLayout()
        #Add the widgets into the layout
        J1587_id_box_layout.addWidget(self.J1587_id_table,0,0,1,5)
        J1587_id_box_layout.addWidget(self.add_message_button,1,0,1,1)
        J1587_id_box_layout.addWidget(clear_button,1,2,1,1)
        

        self.J1587_id_table_columns = ["Table Key","MID","Message Identification","PID","Parameter Identification","Value","Units","Meaning","Message Count","Period (ms)","Raw Hexadecimal"]
        
        self.J1587_id_table.setColumnCount(len(self.J1587_id_table_columns))
        self.J1587_id_table.setHorizontalHeaderLabels(self.J1587_id_table_columns)
        self.J1587_id_table.hideColumn(0) 
        self.id_selection_list=[] #create an empty list
        
        self.J1587_id_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        #self.can_id_table.itemSelectionChanged.connect(self.create_spn_plot_buttons)
        
        #self.tabs.addWidget(self.J1587_tab)
        #setup the layout to be displayed in the box
        J1587_id_box.setLayout(J1587_id_box_layout)
        tab_layout.addWidget(J1587_id_box)
        self.J1587_tab.setLayout(tab_layout)
    
    def j1708_to_j1587(self, msg):
        try:
            if msg[1] not in [0xc0, 0xc2, 0xc4]:
                return msg
        except IndexError:
            #logger.debug(traceback.format_exc()) 
            return msg

        msg_mid = msg[0]

        if msg[1] == 0xc0: #See section A.192 of J1587
            (mid, pid, last_section, this_section, data) = J1587MultiSectionMessage.parse_message(msg)
            if mid in self.multi_section_messages.keys() and pid in self.multi_section_messages[mid].keys():
                self.multi_section_messages[mid][pid].add_section(this_section, data)
                if self.multi_section_messages[mid][pid].all_sections_recvd():
                    completed_message = self.multi_section_messages[mid][pid].get_message()
                    del(self.multi_section_messages[mid][pid])
                    return completed_message
            else:
                if mid not in self.multi_section_messages.keys():
                    # Create the dictionary entry of a message object if it doesn't exist using the PID as a key.
                    self.multi_section_messages[mid] = {pid: J1587MultiSectionMessage(mid, pid, last_section)}
                elif pid not in self.multi_section_messages[mid].keys():
                    self.multi_section_messages[mid][pid] = J1587MultiSectionMessage(mid, pid, last_section)
                self.multi_section_messages[mid][pid].add_section(this_section, data)
                # Would they send a multi-section message as just one message?
                # Probably not, but it wouldn't surprise me
                if self.multi_section_messages[mid][pid].all_sections_recvd():
                    completed_message = self.multi_section_messages[mid][pid].get_message()
                    del(self.multi_section_messages[mid][pid])
                    return completed_message
            return None    
        # Need to request more information.
        elif msg[1] == 0xc2:
            mid = msg[0]
            data_count = msg[2]
            data_portion = msg[3:3 + data_count]
            more_info_requests = []
            while len(data_portion) > 1:
                sid_pid = data_portion[0]
                code_char = data_portion[1]
                count_included = (code_char & 0b10000000) >> 7
                fault_inactive = (code_char & 0b01000000) >> 6
                standard_code = (code_char & 0b00100000) >> 5
                is_sid = (code_char & 0b00010000) >> 4
                fmi = code_char & 0b1111
                if count_included:
                    occurance_count = data_portion[2]
                else:
                    occurance_count = None
                if standard_code == 0:
                    effective_pid = sid_pid + 256
                else:
                    effective_pid = sid_pid

                data_portion = data_portion[3:]

                if not effective_pid in self.more_info_pids.keys():
                    self.more_info_pids[effective_pid] = [None, None]
                elif not None in self.more_info_pids[effective_pid]:
                    continue
                more_info_requests.append((mid, sid_pid, count_included, fault_inactive, standard_code, is_sid, fmi, occurance_count))
            for more_info in more_info_requests:
                (dest_mid, sid_pid, count_included, fault_inactive, standard_code, is_sid, fmi, occurance_count) = more_info
                my_mid = 0xac
                pid = 0xc3
                data_count = 3
                pid_sid_to_request = sid_pid
                addnl_request = 0b11 << 6
                ascii_request = 0
                code_type = standard_code << 5
                low_char = is_sid << 4
                fmi = fmi & 0b1111
                if code_type == 0:
                    effective_pid = sid_pid + 256
                else:
                    effective_pid = sid_pid

                if self.more_info_pids[effective_pid][0] is None:
                    request1 = bytes(
                        [mid, pid, data_count, dest_mid, sid_pid, ascii_request | code_type | low_char | fmi])
                    if 128 in self.to_send_1587_list:
                        self.to_send_1587_list[128].append(
                            ({'1920' + str(sid_pid): request1}, 0))
                if self.more_info_pids[effective_pid][1] is None:
                    request2 = bytes(
                        [mid, pid, data_count, dest_mid, sid_pid, addnl_request | code_type | low_char | fmi])
                    if 128 in self.to_send_1587_list:
                        self.to_send_1587_list[128].append(
                            ({'1921' + str(sid_pid): request2}, 0))
            try:
                if self.j1587responses[msg_mid][msg_pid] is None:
                    self.j1587responses[msg_mid][msg_pid] = (time.time(), msg)
                    self.j1587_count += 1
            except KeyError:
                pass
            return msg

        elif msg[1] == 0xc4:
            source_mid = msg[0]
            sid_pid = msg[3]
            code = msg[4]
            msg_type = code & 0b11000000
            code_type = code & 0b00100000
            if code_type == 0:
                effective_pid = sid_pid + 256
            else:
                effective_pid = sid_pid

            # this shouldn't ever happen, but who knows
            if not effective_pid in self.more_info_pids.keys():
                return None

            # ascii message
            if msg_type == 0 and self.more_info_pids[effective_pid][0] is None:
                self.more_info_pids[effective_pid][0] = (time.time(), msg)
                self.j1587_count += 1
            # more info message
            elif self.more_info_pids[effective_pid][1] is None:
                self.more_info_pids[effective_pid][1] = (time.time(), msg)
                self.j1587_count += 1
            if self.j1587responses[msg_mid][msg_pid] is None:
                self.j1587responses[msg_mid][msg_pid] = (time.time(), msg)
                self.j1587_count += 1
            return msg
        # elif self.j1587responses[msg_mid][msg_pid] is None:
        #     self.j1587responses[msg_mid][msg_pid] = (time.time(), msg)
        #     self.j1587_count += 1
        #     return msg

        else:
            return msg

    def clear_J1587_table(self):
        self.J1587_id_table.clear()
        self.J1587_id_table.setHorizontalHeaderLabels(self.J1587_id_table_columns)
        self.J1587_id_table.setRowCount(0)
        self.J1587_unique_ids = {}
        self.J1587_table_index = {}
        self.byte_set={}
        logger.info("User cleared J1587 table data.")
        
    def fill_j1587_table(self, j_buffer):
        current_time = j_buffer[0]
        rx_buffer = j_buffer[1]
        #See The J1587 Message from RP1210_ReadMessage in RP1210
        if rx_buffer[4] == 1:
            # Return when the VDA is the one that sent the message. 
            # The message gets logged, but not displayed in the table
            return 
        vda_time = struct.unpack(">L",rx_buffer[0:4])[0]
        #messages = j1708_to_j1587(rx_buffer[5:])
        #print(messages)
        

        msg = self.j1708_to_j1587(rx_buffer[5:])
        if msg is None:
            return

        buffer_length = len(msg)
        #return
        try:
            mid = msg[0]
        except IndexError:
            return

        buffer_index = 1
        pid_list = []
        #logger.debug(bytes_to_hex_string(msg))
        # Generate a list of tuples where each tuple is a PID, Value
        while buffer_index < buffer_length:
            try:
                pid = msg[buffer_index]
                if pid == 255:
                    buffer_index +=1
                    pid = msg[buffer_index] + 256
                buffer_index += 1
                if pid < 128 or pid % 256 < 128:
                    pid_list.append((pid,bytes([msg[buffer_index]])))
                    buffer_index += 1
                elif pid < 192 or pid % 256 < 192:
                    pid_list.append((pid,msg[buffer_index:buffer_index + 2]))
                    buffer_index += 2
                else:
                    n = msg[buffer_index]
                    pid_list.append((pid,msg[buffer_index:buffer_index + n + 1]))
                    buffer_index = buffer_index + n + 1
            except IndexError:
                break
        #print(pid_list)
        if mid < 128:
            return
            
        source_key = "{} on J1587".format(self.get_mid_name(mid))
        
        if mid not in self.mids:
            self.mids.append(mid)
            self.root.data_package["Component Information"][source_key] = {}
            self.root.data_package["Time Records"][source_key] = {}
            self.root.data_package["ECU Time Information"][source_key] = {}
            self.root.data_package["Distance Information"][source_key] = {}
            self.battery_potential[source_key] = []
            logger.info("Added message identifier {} to the list of known MIDs.".format(mid))

        for pid_pair in pid_list:
            pid = pid_pair[0]
            if pid in self.pids_to_not_decode:
                continue
            data_bytes = pid_pair[1]
            pid_key = repr((mid,pid))
            try:
                self.J1587_unique_ids[pid_key]["Num"] += 1  
            except KeyError:
                self.J1587_unique_ids[pid_key] = {"Num":1}
                self.J1587_unique_ids[pid_key]["Table Key"] = pid_key
                self.J1587_unique_ids[pid_key]["Start Time"] = time.time()
                self.J1587_unique_ids[pid_key]["Last Time"] = time.time()
                self.J1587_unique_ids[pid_key]["MID"] = "{:3d}".format(mid)
                self.J1587_unique_ids[pid_key]["PID"] = "{:4d}".format(pid)
                self.byte_set[pid_key] = set()
                self.J1587_unique_ids[pid_key]["Meaning"] = ""
                self.J1587_unique_ids[pid_key]["Message List"]=[]
            
                #self.J1587_table_index[pid_key] = {}
                self.J1587_unique_ids[pid_key]["Message Identification"] = self.get_mid_name(mid)
                self.J1587_unique_ids[pid_key]["Parameter Identification"] = self.get_pid_name(pid)
                
                # self.J1587_unique_ids[pid_key]["Filter"] = QComboBox()
                # self.J1587_unique_ids[pid_key]["Filter"].setInsertPolicy(QComboBox.NoInsert)
                # self.J1587_unique_ids[pid_key]["Filter"].activated.connect(lambda: self.apply_filter(mid,pid))       
                # self.J1587_unique_ids[pid_key]["Filter"].addItems(["Pass","Block"])
                # self.J1587_unique_ids[pid_key]["Filter"].setSizeAdjustPolicy(QComboBox.AdjustToContents)

            current_time = time.time()
            if data_bytes not in self.byte_set[pid_key]:
                self.J1587_unique_ids[pid_key]["Message List"].append((current_time, base64.b64encode(data_bytes).decode()))
                self.byte_set[pid_key].add(data_bytes)
            self.J1587_unique_ids[pid_key]["Message Count"] = "{:12d}".format(self.J1587_unique_ids[pid_key]["Num"])
            self.J1587_unique_ids[pid_key]["Time"] = current_time
            self.J1587_unique_ids[pid_key]["VDATime"] = vda_time
            self.J1587_unique_ids[pid_key]["Raw Hexadecimal"] = bytes_to_hex_string(data_bytes)
            (val, units) = self.get_j1587_value(mid,pid,data_bytes,source_key)
            self.J1587_unique_ids[pid_key]["Value"] = val
            self.J1587_unique_ids[pid_key]["Units"] = units
            self.J1587_unique_ids[pid_key]["Period (ms)"] = "{:10.2f}".format(1000 * (self.J1587_unique_ids[pid_key]["Time"] - self.J1587_unique_ids[pid_key]["Start Time"])/self.J1587_unique_ids[pid_key]["Num"])
            self.J1587_unique_ids[pid_key]["Last Time"] = self.J1587_unique_ids[pid_key]["Time"]
            
            if self.J1587_unique_ids[pid_key]["Num"] == 1:
                self.J1587_id_table.setSortingEnabled(False)
                logger.debug("Adding Row to table:")
                logger.debug(self.J1587_unique_ids[pid_key])
                row = self.J1587_id_table.rowCount()
                self.J1587_id_table.insertRow(row)
                col_num = 0
                for col_name in self.J1587_id_table_columns:
                    try:
                        entry = QTableWidgetItem(self.J1587_unique_ids[pid_key][col_name])
                    except TypeError:
                        entry = QTableWidgetItem(repr(self.J1587_unique_ids[pid_key][col_name]))
                    entry.setFlags(entry.flags() & ~Qt.ItemIsEditable)
                    self.J1587_id_table.setItem(row,col_num,entry)
                    col_num += 1
                self.J1587_id_table.resizeColumnsToContents()
                self.J1587_id_table.resizeRowToContents(row)
                self.J1587_id_table.scrollToBottom()
                self.J1587_id_table.setSortingEnabled(True)

            elif self.add_message_button.isChecked():
                try:
                    item = self.J1587_id_table.findItems(pid_key, Qt.MatchExactly)[0]
                except IndexError:
                    logger.debug("Item {} not found in the J1587 table.".format(pid_key))
                    continue
                
                self.J1587_id_table.setSortingEnabled(False)
                
                row = item.row()
                
                col = self.J1587_id_table_columns.index("Message Count")
                entry = QTableWidgetItem(self.J1587_unique_ids[pid_key]["Message Count"])
                entry.setFlags(entry.flags() & ~Qt.ItemIsEditable)
                self.J1587_id_table.setItem(row, col, entry)
                
                col = self.J1587_id_table_columns.index("Period (ms)")
                entry = QTableWidgetItem(self.J1587_unique_ids[pid_key]["Period (ms)"])
                entry.setFlags(entry.flags() & ~Qt.ItemIsEditable)
                self.J1587_id_table.setItem(row,col,entry)

                col = self.J1587_id_table_columns.index("Value")
                entry = QTableWidgetItem(self.J1587_unique_ids[pid_key]["Value"])
                entry.setFlags(entry.flags() & ~Qt.ItemIsEditable)
                self.J1587_id_table.setItem(row,col,entry)
                
                col = self.J1587_id_table_columns.index("Meaning")
                entry = QTableWidgetItem(self.J1587_unique_ids[pid_key]["Meaning"])
                entry.setFlags(entry.flags() & ~Qt.ItemIsEditable)
                self.J1587_id_table.setItem(row,col,entry)

                col = self.J1587_id_table_columns.index("Raw Hexadecimal")
                entry = QTableWidgetItem(self.J1587_unique_ids[pid_key]["Raw Hexadecimal"])
                entry.setFlags(entry.flags() & ~Qt.ItemIsEditable)
                self.J1587_id_table.setItem(row,col,entry)
                
                self.J1587_id_table.setSortingEnabled(True)
                self.J1587_id_table.resizeRowToContents(row)


            if pid == 168: #Battery Potential
                try:
                    self.battery_potential[source_key].append((time.time(), float(self.J1587_unique_ids[pid_key]["Value"])))
                    self.root.voltage_graph.add_data(self.battery_potential[source_key], 
                        marker = 'x-', 
                        label = self.J1587_unique_ids[pid_key]["Message Identification"]+": PID {}".format(pid))
                    self.root.voltage_graph.plot()
                except ValueError:
                    logger.debug("No Definition for Battery Potential in J1587db")
            elif pid == 245: #Total Vehicle Distance
                val = float(self.J1587_unique_ids[pid_key]["Value"])
                units = self.J1587_unique_ids[pid_key]["Units"]
                self.root.data_package["Distance Information"][source_key].update({"Total Vehicle Distance":"{:0.2f} {}".format(val,units)})

            elif pid == 247: #Total Engine Hours
                val = float(self.J1587_unique_ids[pid_key]["Value"])
                units = self.J1587_unique_ids[pid_key]["Units"]
                self.root.data_package["ECU Time Information"][source_key].update({"Total Engine Hours":"{:0.2f} {}".format(val,units)})


        self.root.data_package["J1587 Message and Parameter IDs"].update(self.J1587_unique_ids)
    
    def get_mid_name(self, mid):
        try:
            return self.J1587db["MID"]["{}".format(mid)]
        except KeyError:
            return "Unknown"
    
    def get_pid_name(self, pid):
        try:
            return self.J1587db["PID"]["{}".format(pid)]["Name"]
        except:
            return "Not Provided"
                
    def clear_voltage_history(self):
        for key in self.battery_potential:
            self.battery_potential[key]=[]

    def get_j1587_bit_meaning(self, pid, value):
        meaning = ""
        if pid in j1587BitDecodingDict.keys():
            for element in j1587BitDecodingDict[pid]:
                meaning += element['string']
                masked_bit = (value & element['mask']) >> element['shift']
                meaning += element['values'][masked_bit]
                meaning += '\n'
        else:
            meaning = "Not Decoded" 
        return meaning.strip()#[:-1] #Strip the last newline off the string

    def get_j1587_value(self, mid, pid, data, source_key):
        pid_key = repr((mid,pid))
        
        try:
            units = self.J1587db["PID"]["{}".format(pid)]["Unit"]

        except KeyError:
            value = repr(data)
            units = ""
            return ("{}".format(value), units)
        else:
            data_length = self.J1587db["PID"]["{}".format(pid)]["DataLength"]
            data_type = self.J1587db["PID"]["{}".format(pid)]["DataType"]
            bit_resolution = self.J1587db["PID"]["{}".format(pid)]["BitResolution"]
            
            if data_type == "Binary Bit-Mapped" and pid != 194:
                #logger.debug("Decoding J1587 Bits. Data = " + repr(data))
                if len(data) == 1:
                    value = struct.unpack("B",data)[0]
                    self.J1587_unique_ids[pid_key]["Meaning"] = self.get_j1587_bit_meaning(pid,value)
                else:
                    value = data
            elif data_type == "Unsigned Short Integer" and data_length == 1 and len(data) == 1:
                value = "{:0.3f}".format(struct.unpack("B",data)[0] * bit_resolution)
            elif data_type == "Unsigned Integer" and data_length == 2 and len(data) == 2:
                value = "{:0.3f}".format(struct.unpack("<H",data)[0] * bit_resolution)
            elif data_type == "Signed Integer" and data_length == 2 and len(data) == 2:
                value = "{:0.3f}".format(struct.unpack("<h",data)[0] * bit_resolution)
            elif data_type == "Signed Integer" and data_length == 2 and len(data) == 3:
                value = "{:0.3f}".format(struct.unpack("<h",data[1:3])[0] * bit_resolution)
            elif data_type == "Unsigned Long Integer" and data_length == 4 and len(data) == 4:
                value = "{:0.3f}".format(struct.unpack("<L",data)[0] * bit_resolution)
            elif data_type == "Unsigned Long Integer" and data_length == 4 and len(data) == 5:
                value = "{:0.3f}".format(struct.unpack("<L",data[1:5])[0] * bit_resolution)
            elif data_type == "Signed Long Integer" and data_length == 4 and len(data) == 5:
                value = "{:0.3f}".format(struct.unpack("<l",data[1:5])[0] * bit_resolution)
            elif pid == 251 and data[0] == 3: #Clock
                seconds = data[1]
                minutes = data[2]
                hours = data[3]
                value = "{:02d}:{:02d}:{:02d}".format(hours, minutes, math.ceil(seconds/4))
                units = "HH:MM:SS"
                self.root.data_package["Time Records"][source_key]["Last ECM Clock"] = value
                try:
                    time_string = self.root.data_package["Time Records"][source_key]["Last ECM Date"] + "T" + self.root.data_package["Time Records"][source_key]["Last ECM Clock"]
                except KeyError:
                    logger.debug("We don't have a date code, so we can't make time.")
                else:
                    try:
                        self.root.data_package["Time Records"][source_key]["Last ECM Time"] = calendar.timegm(time.strptime(time_string,"%m/%d/%YT%H:%M:%S"))
                        self.root.data_package["Time Records"][source_key]["PC Time minus ECM Time"] = time.time() - self.root.data_package["Time Records"][source_key]["Last ECM Time"]
                    except (TypeError, ValueError):
                        logger.debug(traceback.format_exc())
                        self.root.data_package["Time Records"][source_key]["Last ECM Time"] = None
                        self.root.data_package["Time Records"][source_key]["PC Time minus ECM Time"] = None
                    
                    self.root.data_package["Time Records"][source_key]["PC Time at Last ECM Time"] = time.time()
        

                
                    
            elif pid == 252 and data[0] == 3: #Date
                day = data[1]
                month = data[2]
                year = data[3] + 1985
                value = "{:02d}/{:02d}/{:04d}".format(month,math.ceil(day/4),year)
                units = "Month/Day/Year"
                self.root.data_package["Time Records"][source_key]["Last ECM Date"] = value
            elif pid == 243: #Component Identification
                value = data.decode('ascii','ignore').replace(b'\x00'.decode('ascii','ignore'),'')
                component_id_list = value.split("*")
                try:
                    make = component_id_list[0]
                    if "TDSC" in make.upper():
                        self.make = "DTDSC"
                except IndexError:
                    make = None
                try:
                    model = component_id_list[1]
                except IndexError:
                    model = None
                try:
                    serial = component_id_list[2]
                except IndexError:
                    serial = None
                try:
                    unit = component_id_list[3]
                except IndexError:
                    unit = None
                # self.component_id[source_key] = 
                # logger.info("Found J1587 Component ID from MID {}: ".format(mid) + repr(self.component_id[source_key]))
                # if mid == 128: #Engine
                #     self.root.make = make
                #     self.root.model = model
                self.root.data_package["Component Information"][source_key].update({"Make":make, "Model":model, "Serial":serial, "Unit":unit})
            elif pid == 237: #VIN
                value = data[1:].decode("ascii",'ignore').replace(b'\x00'.decode('ascii','ignore'),'')
                logger.info("Found J1587 Vehicle Identification from MID {}: ".format(mid) + value)
                self.root.data_package["Component Information"][source_key].update({"VIN": value})
            
            elif pid == 234: # Software Identification
                value = data[1:].decode('ascii','ignore').replace(b'\x00'.decode('ascii','ignore'),'')
                logger.info("Found J1587 Software Identification from MID {}: ".format(mid) + value)
                self.root.data_package["Component Information"][source_key].update({"Software": value})
            
            elif data_type == "Alphanumeric":
                value = data.decode('ascii','ignore').replace(b'\x00'.decode('ascii','ignore'),'')
            
            elif pid == 194:
                self.count_divisor = 1
                self.J1587_unique_ids[pid_key]["Meaning"] = self.get_j1587_diagnostics(mid,pid,data)
                value = "{:d}".format(self.pid194_count)
                units = "Count"
            else:
                value = ""
        
        return ("{}".format(value),units)  

    def get_j1587_diagnostics(self, mid, pid, data):
        ''' Interpret PID 194 from SAE J1597 standard'''
        message = ""
        byte_count = data[0]
        byte_index = 1
        self.pid194_count = 0
        while byte_index < byte_count + 1:
            try:
                sid = data[byte_index]
                byte_index += 1
                diag_code_char = data[byte_index]
                byte_index += 1
            except IndexError:
                return message
            if (diag_code_char & 0x80) == 0x80:
                occurance_count_included = True
                self.count_divisor = 3
            else:
                occurance_count_included = False
                self.count_divisor = 2
            
            if (diag_code_char & 0x40) == 0x40:
                fault_is_inactive = True
                message += "I - "
            else:
                fault_is_inactive = False
                message += "A - "

            if (diag_code_char & 0x20) == 0x20:
                standard_code = True
            else:
                standard_code = False

            if (diag_code_char & 0x10) == 0x10:
                is_sid_code = True
            else:
                is_sid_code = False
            
            if not standard_code:
                sid += 256

            try:
                if is_sid_code:
                    if "{}".format(mid) in self.J1587db["SID"].keys():
                        sid_string = self.J1587db["SID"]["{}".format(mid)]["{}".format(sid)]
                    else:
                        sid_string = self.J1587db["SID"]["-1"]["{}".format(sid)]
                else:
                    sid_string = self.J1587db["PIDNames"]["{}".format(sid)]
            except KeyError:
                sid_string = "Unknown System ID"
            
            
            message += sid_string
            message += ": "

            fmi = diag_code_char & 0x0F
            fmi_text = self.J1587db["FMI"]["{}".format(fmi)]
            message += fmi_text

            if occurance_count_included:
                try:
                    occurance_count = data[byte_index]
                except IndexError:
                    return message
                byte_index += 1
                message += ". Count: {}\n".format(occurance_count)
            else:
                message += "\n"
            self.pid194_count += 1
        #logger.debug(message)
        return message.strip()    


class J1587MultiSectionMessage():

    def __init__(self, mid, pid, num_sections):
        self.mid = mid
        self.pid = pid
        self.sections = [None] * (num_sections + 1)

    def add_section(self, section_num, data):
        # If not the final section, don't add the checksum to data.
        if section_num < len(self.sections):
            self.sections[section_num] = data[:-1]
        else:
            self.sections[section_num] = data

    def all_sections_recvd(self):
        return not None in self.sections

    def get_message(self):
        data = self.get_data()
        if data is None:
            return None
        # Don't need to consider section 2/3 PIDs because these messages don't
        # support them
        return bytes([self.mid, self.pid]) + data

    def get_data(self):
        if not self.all_sections_recvd():
            return None
        else:
            return b''.join(self.sections)

    @staticmethod
    def parse_message(buf):
        mid = buf[0]
        byte_count = buf[2]
        data_portion = buf[3:3 + byte_count]
        pid = data_portion[0]
        last_section = (data_portion[1] & 0xF0) >> 4
        this_section = data_portion[1] & 0x0F
        if this_section == 0:
            data = data_portion[3:]
        else:
            data = data_portion[2:]

        return (mid, pid, last_section, this_section, data)


activeInactive = {
    0: 'Inactive',
    1: 'Active'
}
onOff = {
    0: 'Off',
    1: 'On'
}
onOffErrorNa = {
    0: 'Off / Inactive',
    1: 'On / Active',
    2: 'Error Condition',
    3: 'Not Avaliable'
}

j1587BitDecodingDict = {
    40: [{
        'mask': 0x03,
        'shift': 4,
        'string': 'Engine Retarder Switch - ',
        'values': onOffErrorNa
        },
        {
        'mask': 0x3C,
        'shift': 4,
        'string': 'Engine Retarder Level Switch - ',
        'values': {0: "0 Cylinders",
                   1: "1 Cylinder",
                   2: "2 Cylinder",
                   3: "3 Cylinder",
                   4: "4 Cylinder",
                   5: "5 Cylinder",
                   6: "6 Cylinder",
                   7: "7 Cylinder",
                   8: "8 Cylinder",
                   9: "Reserved",
                   10: "Reserved",
                   11: "Reserved",
                   12: "Reserved",
                   13: "Reserved",
                   14: "Error",
                   15: "Not Avaliable"}
        },
    ],
    44: [{
        'mask': 0x30,
        'shift': 4,
        'string': 'Protect Lamp Status - ',
        'values': onOffErrorNa
        },
        {
        'mask': 0xc,
        'shift': 2,
        'string': 'Amber Lamp Status - ',
        'values': onOffErrorNa
        },
        {
        'mask': 0x3,
        'shift': 0,
        'string': 'Red Lamp Status - ',
        'values': onOffErrorNa
        }
    ],
    49: [{
        'mask': 0xC0,
        'shift': 6,
        'string': 'ABS off-road function switch - ',
        'values': onOffErrorNa
        },
        {
        'mask': 0x30,
        'shift': 4,
        'string': 'ABS Retarder Control - ',
        'values': onOffErrorNa
        },
        {
        'mask': 0xc,
        'shift': 2,
        'string': 'ABS brake control - ',
        'values': onOffErrorNa
        },
        {
        'mask': 0x3,
        'shift': 0,
        'string': 'ABS warning lamp - ',
        'values': onOffErrorNa
        }
    ],
    70: [{
        'mask': 0x80,
        'shift': 7,
        'string': '',
        'values': activeInactive
        }
    ],
    71: [{
        'mask': 0x80,
        'shift': 7,
        'string': 'Idle shutdown timer status - ',
        'values': activeInactive
        },
        {
        'mask': 0x8,
        'shift': 3,
        'string': 'Idle shutdown timer function - ',
        'values': {
            0: 'Disabled',
            1: 'Enabled'
        }},
        {
        'mask': 0x4,
        'shift': 2,
        'string': 'Idle shutdown timer override - ',
        'values': activeInactive
        },
        {
        'mask': 0x2,
        'shift': 1,
        'string': 'Engine has shutdown by idle timer - ',
        'values': {
            0: 'No',
            1: 'Yes'
        }},
        {
        'mask': 0x1,
        'shift': 0,
        'string': 'Driver Alert Mode - ',
        'values': activeInactive
        }
    ],
    89: [
        {
            'mask': 0x80,
            'shift': 7,
            'string': 'PTO Mode - ',
            'values': activeInactive
        },
        {
            'mask': 0x40,
            'shift': 6,
            'string': 'Clutch Switch - ',
            'values': onOff
        },
        {
            'mask': 0x20,
            'shift': 5,
            'string': 'Brake Switch - ',
            'values': onOff
        },
        {
            'mask': 0x10,
            'shift': 4,
            'string': 'Accel Switch - ',
            'values':
            onOff
        },
        {
            'mask': 0x8,
            'shift': 3,
            'string': 'Resume Switch - ',
            'values': onOff
        },
        {
            'mask': 0x4,
            'shift': 2,
            'string': 'Coast Switch - ',
            'values': onOff
        },
        {
            'mask': 0x2,
            'shift': 1,
            'string': 'Set Switch - ',
            'values': onOff
        },
        {
            'mask': 0x1,
            'shift': 0,
            'string': 'PTO Control Switch - ',
            'values': onOff
        }
    ],
    85: [
        {
            'mask': 0x1,
            'shift': 0,
            'string': 'Cruise Control Switch - ',
            'values': onOff
        },
        {
            'mask': 0x2,
            'shift': 1,
            'string': 'Set Switch - ',
            'values': onOff
        },
        {
            'mask': 0x4,
            'shift': 2,
            'string': 'Coast Switch - ',
            'values': onOff
        },
        {
            'mask': 0x8,
            'shift': 3,
            'string': 'Resume Switch - ',
            'values': onOff
        },
        {
            'mask': 0x10,
            'shift': 4,
            'string': 'Accel Switch - ',
            'values': onOff
        },
        {
            'mask': 0x20,
            'shift': 5,
            'string': 'Brake Switch - ',
            'values': onOff
        },
        {
            'mask': 0x40,
            'shift': 6,
            'string': 'Clutch Switch - ',
            'values': onOff
        },
        {
            'mask': 0x80,
            'shift': 7,
            'string': 'Cruise Mode - ',
            'values': {
                0: 'Not Active',
                1: 'Active'
            }},
    ],
    83: [
        {
            'mask': 0x80,
            'shift': 7,
            'string': 'Road Speed Limiter Currently ',
            'values': {
                0: 'Not Active',
                1: 'Active'
            }}
    ],
    97: [
        {
            'mask': 0x80,
            'shift': 7,
            'string': 'Water in Fuel Tndicator - ',
            'values': {
                0: 'No',
                1: 'Yes'
            }}
    ],
    121: [
        {
            'mask': 0x80,
            'shift': 7,
            'string': 'Engine Retarder -  ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x01,
            'shift': 2,
            'string': '2 Cylinder - ',
            'values': { 0: "Not Active",
                        1: "Active" }
        },
        {
            'mask': 0x02,
            'shift': 2,
            'string': '3 Cylinder - ',
            'values': { 0: "Not Active",
                        1: "Active" }
        },
        {
            'mask': 0x04,
            'shift': 2,
            'string': '4 Cylinder - ',
            'values': { 0: "Not Active",
                        1: "Active" }
        },
        {
            'mask': 0x08,
            'shift': 2,
            'string': '6 Cylinder - ',
            'values': { 0: "Not Active",
                        1: "Active" }
        },
        {
            'mask': 0x10,
            'shift': 2,
            'string': '8 Cylinder - ',
            'values': { 0: "Not Active",
                        1: "Active" }
        }
    ],
    134: [
        {
            'mask': 0x3,
            'shift': 0,
            'string': 'Wheel sensor ABS axle: 4 right - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc,
            'shift': 2,
            'string': 'Wheel sensor ABS axle: 3 right - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x30,
            'shift': 4,
            'string': 'Wheel sensor ABS axle: 2 right - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc0,
            'shift': 6,
            'string': 'Wheel sensor ABS axle: 1 right - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x300,
            'shift': 8,
            'string': 'Wheel sensor ABS axle: 4 left - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc00,
            'shift': 10,
            'string': 'Wheel sensor ABS axle: 3 left - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x3000,
            'shift': 12,
            'string': 'Wheel sensor ABS axle: 2 left - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc000,
            'shift': 14,
            'string': 'Wheel sensor ABS axle: 1 left - ',
            'values': onOffErrorNa
        },
    ],
    150: [
        {
            'mask': 0x30,
            'shift': 4,
            'string': 'PTO #3 engagement actuator status - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc0,
            'shift': 6,
            'string': 'PTO #4 engagement actuator status - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x3000,
            'shift': 12,
            'string': 'PTO #3 engagement control switch status - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc000,
            'shift': 14,
            'string': 'PTO #4 engagement control switch status - ',
            'values': onOffErrorNa
        },
    ],
    151: [
        {
            'mask': 0x3,
            'shift': 0,
            'string': 'ATC deep snow/mud function switch - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc,
            'shift': 2,
            'string': 'VDC brake control - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x30,
            'shift': 4,
            'string': 'VDC engine control - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x300,
            'shift': 8,
            'string': 'ATC status lamp - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc00,
            'shift': 10,
            'string': 'ATC brake control - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x3000,
            'shift': 12,
            'string': 'ATC engine control - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc000,
            'shift': 14,
            'string': 'ATC spin-out signal detection - ',
            'values': onOffErrorNa
        },
    ],
    209: [
        {
            'mask': 0x3,
            'shift': 0,
            'string': 'Tractor Mounted Trailer ABS Lamp - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc,
            'shift': 2,
            'string': 'Trailer ABS Control Status - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x30,
            'shift': 4,
            'string': 'ABS warning lamp Trailer #1 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc0,
            'shift': 8,
            'string': 'ABS brake control Status Trailer #1 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x300,
            'shift': 0,
            'string': 'ABS warning Lamp Trailer #2 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc00,
            'shift': 2,
            'string': 'ABS brake control Status Trailer #2 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x3000,
            'shift': 4,
            'string': 'ABS warning Lamp Trailer #3 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc000,
            'shift': 8,
            'string': 'ABS brake control Status Trailer #3 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x30000,
            'shift': 0,
            'string': 'ABS warning Lamp Trailer #4 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc0000,
            'shift': 2,
            'string': 'ABS brake control Status Trailer #4 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0x300000,
            'shift': 4,
            'string': 'ABS warning Lamp Trailer #5 - ',
            'values': onOffErrorNa
        },
        {
            'mask': 0xc00000,
            'shift': 8,
            'string': 'ABS brake control Status Trailer #5 - ',
            'values': onOffErrorNa
        },
    ]
}