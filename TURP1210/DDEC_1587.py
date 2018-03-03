from PyQt5.QtWidgets import QMessageBox, QInputDialog, QProgressDialog, QTableWidgetItem,  QLabel, QWidget
from PyQt5.QtCore import Qt, QCoreApplication

from TURP1210.RP1210.RP1210Functions import *
from TURP1210.TableModel.TableModel import *
from TURP1210.Graphing.graphing import *
from TURP1210.TU_crypt.TU_crypt_public import *

import json
import base64
import time
import struct
import logging
logger = logging.getLogger(__name__)


class DDEC_J1587(QWidget):
    def __init__(self, parent):
        super(DDEC_J1587, self).__init__()
        self.root = parent
        self.graph_tabs = {}

    def plot_decrypted_data(self):
        try:    
            for key, item in sorted(self.root.data_package["Decrypted Data"].items()):
                try:
                    #print([k for k in item.keys()])
                    logger.debug(key)
                    if 'Hard Brake' in key:
                        logger.debug("{} has Incident data".format(key))
                        num = 1
                        for event in item['hard_brake_data']['values']:
                            self.plot_ddec_hard_brake_data(event, num)
                            num += 1
                    elif 'Last Stop' in key:
                        logger.debug("{} has Incident data".format(key))
                        self.plot_ddec_last_stop_data(item)
                except AttributeError:
                    logger.debug(traceback.format_exc())
        except KeyError:
            #logger.debug(traceback.format_exc())
            logger.debug("There was no decrypted data in the data_package dict.")
    
    def plot_ddec_hard_brake_data(self, data_dict, number):
        logger.debug("Plotting Hard Brake Data")
        title = "Hard Brake Event {}".format(number)
        self.plot_ddec_data(data_dict['Incident Engine Hours'],
                            data_dict['Incident Odometer'],
                            data_dict['Oldest Incident Sample'],
                            data_dict['ECM Time of Incident'],
                            data_dict['Valid Incident Sample Count'],
                            data_dict["Data OT"]["values"],
                            title)
        self.root.pdf_engine.add_event_chart(title + " Graph", self.root.get_plot_bytes(self.graph_tabs[title].figure))
        self.root.pdf_engine.add_event_table(title + " Table", self.graph_tabs[title].data_list)
        
    def plot_ddec_last_stop_data(self, data_dict):
        logger.debug("Plotting Last Stop Data")
        title = "Last Stop Event"
        self.plot_ddec_data(data_dict['Incident Engine Hours'],
                            data_dict['Incident Odometer'],
                            data_dict['Oldest Incident Sample'],
                            data_dict['ECM Time of Incident'],
                            data_dict['Valid Incident Sample Count'],
                            data_dict["Incident values"]["values"],
                            title)
        self.root.pdf_engine.add_event_chart(title + " Graph", self.root.get_plot_bytes(self.graph_tabs[title].figure))
        self.root.pdf_engine.add_event_table(title + " Table", self.graph_tabs[title].data_list)

    def plot_ddec_data(self, hours, odometer, oldest_time, incident_time, valid_count, data_dict, title):
        """
            Expects dictionaries from ecm_parsers
        """
        if title in [k for k in self.graph_tabs.keys()]:
            return #Don't add another tab

        self.graph_tabs[title] = GraphTab(self, self.root.tabs, title)
        self.graph_tabs[title].event_name_label.setText("Name of Event: {}".format(title))
        self.graph_tabs[title].ecm_rtc_label.setText("ECM Real Time Clock at Event: {} UTC".format(incident_time['value']))
        try:
            adjusted_time = incident_time['raw_value'] + self.root.data_package["Time Records"]["Engine #1 from J1587"]["PC Time minus ECM Time"]
        except:
            adjusted_time = incident_time['raw_value']
        self.graph_tabs[title].actual_rtc_label.setText("PC Real Time Clock at Event: {}".format(get_local_time_string(adjusted_time)))
        self.graph_tabs[title].engine_hours_label.setText("Engine Hours at Event: {} {}".format(hours['value'],hours['units']))
        self.graph_tabs[title].odometer_label.setText("Vehicle Distance At Event: {} {}".format(odometer['value'],odometer['units']))
        num_rows = int(valid_count['value'])
        data_dict['Time']={'values':[i for i in range(16-num_rows,16)],'units':"sec"}

        #data_labels = [k for k in data_dict.keys()]
        # We need these to be in the following order:
        data_labels = ["Time",
                       "Road Speed",
                       "Engine Speed",
                       "Brake Switch",
                       "Clutch Switch",
                       "Engine Load",
                       "Throttle",
                       "Cruise Switch",
                       "Coast Switch",
                       "Resume Switch",
                       "Set Switch",
                       "Accelerator Switch",
                       "Diagnostic Code"]
        data_units = [data_dict[k]['units'] for k in data_labels]
        data_headers = ["{}\n({})".format(l,u).replace(' ','\n') for l,u in zip(data_labels,data_units)]
        self.graph_tabs[title].data_list = [[''] + data_labels,[''] + data_units] #Use this for conveniently writing the csv file
        self.graph_tabs[title].data_table.setColumnCount(len(data_labels))
        
        self.graph_tabs[title].data_table.setRowCount(num_rows)
        self.graph_tabs[title].data_table.setHorizontalHeaderLabels(data_headers)
        for row in range(num_rows):
            self.graph_tabs[title].data_list.append([''])
            col_num = 0
            for col_name in data_labels:
                val = data_dict[col_name]['values'][row]
                self.graph_tabs[title].data_list[-1].append(val)
                entry = QTableWidgetItem("{}".format(val))
                entry.setFlags(entry.flags() & ~Qt.ItemIsEditable)
                self.graph_tabs[title].data_table.setItem(row, col_num, entry)
                col_num += 1
        self.graph_tabs[title].data_table.resizeRowToContents(row)
        self.graph_tabs[title].data_table.resizeColumnsToContents()
        self.graph_tabs[title].data_table.scrollToBottom()   

        self.graph_tabs[title].top_axis.plot(data_dict['Time']['values'],
                                             data_dict['Road Speed']['values'],
                                             '-o',
                                             label="Road Speed")
        self.graph_tabs[title].top_axis.grid()
        leg1 = self.graph_tabs[title].top_axis.legend()
        leg1.draggable()

        second_y = self.graph_tabs[title].top_axis.twinx()
        second_y.plot(data_dict['Time']['values'],
                        data_dict['Engine Speed']['values'],
                        '-x',
                        color='green',
                        label="Engine Speed")
        leg2 = second_y.legend()
        leg2.draggable()
        second_y.set_ylabel("Engine Speed (rpm)")

         
        self.graph_tabs[title].middle_axis.plot(data_dict['Time']['values'],
                                                data_dict['Engine Load']['values'],
                                                '-s',
                                                label="Engine Load")
        self.graph_tabs[title].middle_axis.set_ylabel("Engine Load (%)")
        self.graph_tabs[title].middle_axis.grid()
        leg3 = self.graph_tabs[title].middle_axis.legend()
        leg3.draggable()

        second_y = self.graph_tabs[title].middle_axis.twinx()
        second_y.plot(data_dict['Time']['values'],
                        data_dict['Throttle']['values'],
                        '-D',
                        color='green',
                        label="Throttle")
        leg4 =second_y.legend()
        leg4.draggable()
        second_y.set_ylabel("Throttle (%)")

        self.graph_tabs[title].bottom_axis.plot(data_dict['Time']['values'],
                                                data_dict['Brake Switch']['values'],
                                                '-v',
                                                label="Brake")
        self.graph_tabs[title].bottom_axis.plot(data_dict['Time']['values'],
                                                data_dict['Clutch Switch']['values'],
                                                '-*',
                                                label="Clutch")
        self.graph_tabs[title].bottom_axis.plot(data_dict['Time']['values'],
                                                data_dict['Cruise Switch']['values'],
                                                '->',
                                                label="Cruise")
          
        self.graph_tabs[title].bottom_axis.grid()
        leg5 = self.graph_tabs[title].bottom_axis.legend()
        leg5.draggable()

    def generate_ddec_preview(self, raw_data_page):
        '''
        Generate preview(s) from a raw DDEC data page.
        Will always return a list, because one hard brake page will frequently contain two records.

        raw_data_page: the raw page as received from the ECM
        '''
        if raw_data_page is None:
            return []

        raw_data_page = raw_data_page[4:] #Strip off the junk in front
        #get header length so we can strip it too
        (header_req_type, header_total_len, header_bitmask_bytes, header_data_len, header_page_data) = self.preprocess_ddec_page(raw_data_page)
        raw_data_page = raw_data_page[4 + header_total_len:] #Strip off header
        (request_type, total_len, bitmask_bytes, data_len, page_data) = self.preprocess_ddec_page(raw_data_page)
        assert len(page_data) == data_len, "lengths don't match, incomplete data page or implementation error: %s, %d" % (repr(list(page_data)), data_len)
        if request_type == 2:
            return self.ddec_fast_stop_preview(page_data)
        elif request_type == 4:
            return self.ddec_last_stop_preview(page_data)
        else:
            return []

    def ddec_fast_stop_preview(self, page_data):
        '''
        Extract fast stop data records from the fast stop data page.

        Returns list of dictionaries, each in the {'header_lines':[...], 'record_lines':[...] }
        format. There should be two.
        '''
        this_page_data = page_data
        page_previews = []
        while len(this_page_data) > 0:
            record = {'header_lines': [], 'record_lines': []}
            
            engine_hours = struct.unpack('<L', this_page_data[0:4])[0] * .05
            record['header_lines'].append(('Reported Incident Engine Hours', "{:.02f}".format(engine_hours)))
            odometer = struct.unpack('<L', this_page_data[4:8])[0] * 0.1
            record['header_lines'].append(('Reported Incident Odometer', '{:.01f}'.format(odometer)))
            valid_samples = int(this_page_data[8])
            record['header_lines'].append(('Valid Sample Count', '{}'.format(valid_samples)))

            speeds = [struct.unpack('B5x',this_page_data[13+i:19+i])[0] * 0.5 for i in range(0,450,6)]
            for i, speed in enumerate(speeds):
                record['record_lines'].append((str(-60 + i), "{:.02f}".format(speed)))

            page_previews.append(record)
            this_page_data = this_page_data[467:]

        return page_previews

    def ddec_last_stop_preview(self, page_data):
        '''
        Extract fast stop data records from the fast stop data page.

        Returns list of dictionaries, each in the {'header_lines':[...], 'record_lines':[...] }
        format. There should be two.
        '''
        this_page_data = page_data
        page_previews = []
        while len(this_page_data) > 0:
            record = {'header_lines': [], 'record_lines': []}
        
            engine_hours = struct.unpack('<L', this_page_data[0:4])[0] * .05
            record['header_lines'].append(('Reported Incident Engine Hours', "{:.02f}".format(engine_hours)))
            odometer = struct.unpack('<L', this_page_data[4:8])[0] * 0.1
            record['header_lines'].append(('Reported Incident Odometer', '{:.01f}'.format(odometer)))
            
            speeds = [struct.unpack('B5x', this_page_data[8+i:14+i])[0] * 0.5 for i in range(0, 720, 6)]
            for i, speed in enumerate(speeds):
                record['record_lines'].append((str(-105 + i), "{:.02f}".format(speed)))

            valid_samples = int(this_page_data[728])
            record['header_lines'].append(('Valid Sample Count', '{}'.format(valid_samples)))
            page_previews.append(record)
            this_page_data = this_page_data[737:]

        return page_previews

    def preprocess_ddec_page(self, raw_data_page):
        '''
        Extract request type, total length, bitmask bytes, data length and page data
        Returns tuple of that information
        '''
        request_type = int(raw_data_page[0])
        total_len = struct.unpack('<H', raw_data_page[2:4])[0]
        bitmask_len = int(raw_data_page[4])
        bitmask_bytes = raw_data_page[5:5+bitmask_len]
        data_len = total_len - (1 + bitmask_len)
        page_data = raw_data_page[5+bitmask_len:5+bitmask_len+data_len]

        return (request_type, total_len, bitmask_bytes, data_len, page_data)

    def start_ddec_J1587(self):
        self.ddec_progress = QProgressDialog(self)
        self.ddec_progress.setMinimumWidth(600)
        self.ddec_progress.setWindowTitle("Downloading DDEC Data Pages")
        self.ddec_progress.setMinimumDuration(0)
        self.ddec_progress.setWindowModality(Qt.ApplicationModal)
        self.ddec_progress.setMaximum(10)
        self.ddec_progress_label = QLabel("")
        self.ddec_progress.setLabel(self.ddec_progress_label)
        self.ddec_progress.setValue(0)
        

        self.root.ok_to_send_j1587_requests = False

        page_names = ["Configuration Data", "Trip Data", "Monthly Activity", "Diagnostic Records",
                      "Daily Engine Usage", "Trip Tables", "Life to Date", "Hard Brake Data",
                      "Last Stop Data"]
        requests = [b'\x00\xc8\x07\x04\x06\x00\x46\x41\x41\x5a\x05\x48',
                    b'\x00\xc8\x07\x04\x01\x00\x46\x41\x41\x5a\xcd\x09',
                    b'\x00\xc8\x07\x04\x0e\x00\x46\x41\x41\x5a\x08\x0a',
                    b'\x00\xc8\x07\x04\x0f\x00\x46\x41\x41\x5a\x4d\xaa',
                    b'\x00\xc8\x07\x04\x10\x00\x46\x41\x41\x5a\x92\x2d',
                    b'\x00\xc8\x07\x04\x0c\x00\x46\x41\x41\x5a\x83\x4a',
                    b'\x00\xc8\x07\x04\x14\x00\x46\x41\x41\x5a\x94\x8c',
                    b'\x00\xc8\x07\x04\x02\x00\x46\x41\x41\x5a\x03\xe9',
                    b'\x00\xc8\x07\x04\x04\x00\x46\x41\x41\x5a\x8e\x08']
        
        # Empty the queue
        while self.root.extra_queues["J1708"].qsize():
            message = self.root.extra_queues["J1708"].get_nowait()
        
        encoded_pages = {}
        raw_pages = {}
        
        for data_page_name, request, prog_count in zip(page_names, requests, range(1,10)):
            logger.info("Starting DDEC Data Page Extration on J1708 for {}.".format(data_page_name))
            # Bytes are priority, tool MID, PID, N, desitination MID, Command
            # Send an connection manager abort command 3 times.
            for i in range(3):
                self.root.RP1210.send_message(self.root.client_ids["J1708"], b'\x05\xb6\xc5\x02\x80\xff') 
                time.sleep(.05)
                QCoreApplication.processEvents()
            # Let the ECU know we are going to start a DDEC Data Pages download.
            self.root.RP1210.send_message(self.root.client_ids["J1708"], b'\x05\xb6\xfe\x80\x00\xdb')
            time.sleep(.1)
            
            request_length = len(request)
            # Send a Request to Send message
            self.root.RP1210.send_message(self.root.client_ids["J1708"], 
                b'\x05\xb6\xc5\x05\x80\x01\x01' + request_length.to_bytes(2,'little'))
            
            # Wait for a clear to send message from the ECU
            CTS = False
            start_time = time.time()
            while not CTS:
                # Keep the application responsive
                QCoreApplication.processEvents()
                # Check to see if anything has come into the queue
                while self.root.extra_queues["J1708"].qsize():
                    message = self.root.extra_queues["J1708"].get()
                    try:
                        MID = message[0]
                        PID = message[1]
                        if MID == 0x80 and PID == 197:
                            LEN = message[2] # Message Length
                            DST = message[3] # Desitnation MID
                            CTL = message[4] # PID 197 Control code
                            if CTL == 2: # CTS (Clear to Send)
                                segments_cleared_for = message[5]
                                start_segment = message[6]
                                if segments_cleared_for > 0: # Only proceed if the ECU says it's ok
                                    CTS = True
                                logger.debug('Engine says it is cleared to send {} segments.'.format(segments_cleared_for))
                                break
                    except IndexError:
                        pass
                if time.time() - start_time > 5:
                    err_msg = "Operation timed out in J1708 when looking for Clear To Send messsage from the Engine."
                    QMessageBox.warning(self, "DDEC Extration Error", err_msg)
                    logger.warning(err_msg)
                    break
                elif self.ddec_progress.wasCanceled():
                    logger.info("DDEC Data Page Extraction Canceled by user.")
                    return
            if CTS:
                # Send the data page request message using the connection management protocol.
                send_buffer = b'\x05\xb6\xc6' # Priority, MID, Transport PID
                send_buffer += (2 + request_length).to_bytes(1, 'little') # Data length including MID and Start Byte
                send_buffer += b'\x80' #Destination MID
                send_buffer += start_segment.to_bytes(1, 'little') #N
                send_buffer += request # Different Data Page Requests
                self.root.RP1210.send_message(self.root.client_ids["J1708"], send_buffer)
                
                # Wait from ECM to hear that the message was sent.
                ACK = False
                start_time = time.time()
                while not ACK:
                    # Keep the application responsive
                    QCoreApplication.processEvents()
                    # Check to see if anything has come into the queue
                    while self.root.extra_queues["J1708"].qsize():
                        message = self.root.extra_queues["J1708"].get()
                        try:
                            MID = message[0]
                            PID = message[1]
                            if MID == 0x80 and PID == 197:
                                #LEN = message[2]
                                #DST = message[3]
                                CTL = message[4]
                                if CTL == 3: # EOM
                                    ACK = True
                                    break
                        except IndexError:
                            pass
                    if time.time() - start_time > 5:
                        err_msg = "Operation timed out when looking for an Acknowledgment Messsage from the Engine."
                        QMessageBox.warning(self, "DDEC Extration Error", err_msg)
                        logger.warning(err_msg)
                        break
                    elif self.ddec_progress.wasCanceled():
                        logger.info("DDEC Data Page Extraction Canceled by user.")
                        self.ddec_progress.deleteLater()
                        return
            else:
                err_msg = "No Clear To Send Message was found from the ECU. ECU may not be online or support DDEC Extractions over J1587."                        
                QMessageBox.warning(self, "DDEC Extration Error", err_msg)
                logger.warning(err_msg)
                self.ddec_progress.deleteLater()
                return

            if ACK: # Listen for RTS
                looking_for_rts = True
                start_time = time.time()
                while looking_for_rts:
                    QCoreApplication.processEvents()
                    while self.root.extra_queues["J1708"].qsize():
                        message = self.root.extra_queues["J1708"].get()
                        try:
                            MID = message[0]
                            PID = message[1]
                            if MID == 0x80 and PID == 197:
                                LEN = message[2]
                                DST = message[3]
                                CTL = message[4]
                                if CTL == 1: # RTS
                                    # Once a Request to send message is found, then we can send a clear to send
                                    # message from the tool to let the ECU know we are ready.
                                    looking_for_rts = False
                                    segments_to_get = message[5]
                                    total_bytes_to_get = struct.unpack("<H", message[6:8])[0]
                                    send_buffer = b'\x05\xb6\xc5\x04\x80\x02' # Start a CTS message
                                    send_buffer += segments_to_get.to_bytes(1,'little') # Message size
                                    send_buffer += b'\x01' # Starting with the first segment
                                    self.root.RP1210.send_message(self.root.client_ids["J1708"], send_buffer)
                        except IndexError:
                            pass
                    if time.time() - start_time > 5:
                        err_msg = "Operation timed out when looking for a Request to Send Messsage from the Engine."
                        QMessageBox.warning(self, "DDEC Extration Error", err_msg)
                        logger.warning(err_msg)
                        break
                    elif self.ddec_progress.wasCanceled():
                        logger.info("DDEC Data Page Extraction Canceled by user")
                        self.ddec_progress.deleteLater()
                        return
                
                # Setup the listener for DDEC Data Pages
                RXSegments = {} # Use a dictionary if one of the segments is out of order.
                start_time = time.time()
                bytes_received = 0
                while len(RXSegments) < segments_to_get:
                    QCoreApplication.processEvents()
                    while self.root.extra_queues["J1708"].qsize():
                        message = self.root.extra_queues["J1708"].get()
                        try:
                            MID = message[0]
                            PID = message[1]
                            if MID == 0x80 and PID == 198: # Data Transfer message
                            # LEN = message[2]
                            # DST = message[3]
                                segment = message[4]
                                data = message[5:]
                                RXSegments[segment] = data
                                bytes_received += len(data)
                                self.ddec_progress_label.setText("Getting Data Page {} - {}: {}".format(prog_count, data_page_name, bytes_to_hex_string(message[4:])))
                            #logger.debug('Received Segment %d of %d bytes' %(segment, len(data)))
                        except IndexError:
                            pass
                    if time.time() - start_time > 30:
                        err_msg = "Operation timed out when looking for DDEC Data Pages segments."
                        QMessageBox.warning(self, "DDEC Extration Error", err_msg)
                        logger.warning(err_msg)
                        break
                    elif self.ddec_progress.wasCanceled():
                        logger.info("DDEC Data Page Extraction Canceled by user")
                        self.ddec_progress.deleteLater()
                        return
                logger.info("Received the following bytes for {}:".format(data_page_name))
                response = b'\x80' # Start with a byte to make the parsers happy.
                for key, item in sorted(RXSegments.items()):
                    response += item
                logger.info(response)
                logger.info("Received {} bytes of the {} bytes promised.".format(bytes_received, total_bytes_to_get))
                if bytes_received == total_bytes_to_get:
                    logger.debug("Sending Acknowledgment")                
                    for i in range(3):
                        self.root.RP1210.send_message(self.root.client_ids["J1708"], b'\x05\xb6\xc5\x02\x80\x03') # ACK/EOM
                else:
                    warn = "The number of bytes received was different than the number promised for {}\n Please try again.".format(data_page_name)
                    logger.warning(warn)                
                    for i in range(3):
                        self.root.RP1210.send_message(self.root.client_ids["J1708"], b'\x05\xb6\xc5\x02\x80\xFF') # Abort   
                    self.ddec_progress.deleteLater()
                    QMessageBox.warning(self.root,"Download issue", warn )
                    return
                # Store the raw bytes to use later.
                raw_pages[data_page_name] = response
                encoded_pages[data_page_name] = str(base64.b64encode(response), "ascii")
                
                self.ddec_progress.setValue(prog_count)
            else:
                logger.warning("This shouldn't display. Something went wrong when trying to extract {}".format(data_page_name))
        
        # Data pages are complete. Let's get some DDEC Parameters
        prog_count += 1 
        pids = [0xed for i in range(3)]
        for pid in pids:
            looking_for_pid = True
            req_msg = b'\xb6\xfe\x80\x00'+bytes([pid])
            self.root.RP1210.send_message(self.root.client_ids["J1708"], req_msg)
            self.ddec_progress_label.setText("Getting DDEC Specific Parameters: {}".format(bytes_to_hex_string(req_msg)))       
            while looking_for_pid:
                QCoreApplication.processEvents()
                while self.root.extra_queues["J1708"].qsize():
                    message = self.root.extra_queues["J1708"].get()
                    MID = message[0]
                    PID = message[1]
                    if MID == 0x80 and PID == 254:
                        LEN = message[2]
                        DST = message[3]
                        CTL = message[4]
                        if CTL == 1: # RTS
                            # Once a Request to send message is found, then we can send a clear to send
                            # message from the tool to let the ECU know we are ready.
                            looking_for_pid = False
                            segments_to_get = message[5]
                            total_bytes_to_get = struct.unpack("<H", message[6:8])[0]
                            send_buffer = b'\x05\xb6\xc5\x04\x80\x02' # Start a CTS message
                            send_buffer += segments_to_get.to_bytes(1,'little') # Message size
                            send_buffer += b'\x01' # Starting with the first segment
                            self.root.RP1210.send_message(self.root.client_ids["J1708"], send_buffer)

                if time.time() - start_time > 5:
                    logger.warning("Operation timed out when looking for DDEC PID {}.".format(req_msg[-1]))
                    break
                elif self.ddec_progress.wasCanceled():
                    logger.info("DDEC Data Page Extraction Canceled by user")
                    self.ddec_progress.deleteLater()
                    return
                    
        self.ddec_progress.setValue(prog_count)         

        # Look at the data before to see the result.
        self.ddec_preview_graph = GraphDialog(self, title="DDEC Preview Data")
        self.ddec_preview_graph.set_xlabel("Event Time (sec)")
        self.ddec_preview_graph.set_ylabel("Speed (mph)")
        self.ddec_preview_graph.set_title("Preview of DDEC Hard Brake and Last Stop Data")
        
        
        i = 0
        for hb_data in self.generate_ddec_preview(raw_pages["Hard Brake Data"]):
            i += 1
            logger.debug("Hard Brake {} record lines:".format(i))
            logger.debug(hb_data['record_lines'])
            self.ddec_preview_graph.add_xy_data(hb_data['record_lines'],
                        marker=markers[i] + '-',
                        label="Hard Brake #{}".format(i)
                        )
        for ls_data in self.generate_ddec_preview(raw_pages["Last Stop Data"]):
            logger.debug("Last Stop record lines:")
            logger.debug(ls_data['record_lines'])
            self.ddec_preview_graph.add_xy_data(ls_data['record_lines'],
                        marker=markers[i] + '-',
                        label="Last Stop"
                        )
        self.ddec_preview_graph.plot_xy()
        self.root.ok_to_send_j1587_requests = True

        self.ddec_progress.deleteLater()

        # Encrypt the data
        raw_report = json.dumps(encoded_pages)
        encryption_file = self.root.user_data.user_data["Decoder Public Key"]
        logger.debug("Decoder Public Key: {}".format(encryption_file))
        try:
            self.root.data_package["DDEC J1587 Encrypted"] = encrypt_bytes(raw_report.encode(), encryption_file)
        except:
            logger.debug(traceback.format_exc())

        

        