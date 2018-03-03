#!/usr/bin/env python3
from PyQt5.QtCore import QCoreApplication
import time
import sys
import struct
import base64
from TURP1210.RP1210.RP1210Functions import *


    
import logging
logger = logging.getLogger(__name__)


ISO_PGN = 0xDA00

SIDNR = 0x7F

service_identifier = { 0x7F: "Negative Response",
                       0x10: "Diagnostic Session Control",
                       0x11: "ECU Reset",
                       0x27: "Security Access",
                       0x22: "Read Data By Identifier",
                       0x28: "Communication Control",
                       0x3E: "Tester Present",
                       0x83: "Access Timing Parameter",
                       0x84: "Secure Data Transmission",
                       0x85: "Control DTC Setting",
                       0x31: "Routine Control"

    }

negative_response_codes = { 0x7F: "Service Not Supported in Active Session",
                            0x12: "Subfunction Not Supported",
                            0x31: "Request Out of Range"
   }


def get_first_nibble(data_byte):
    return (data_byte & 0xF0) >> 4

def get_second_nibble(data_byte):
    return data_byte & 0x0F

# data: data portion of ISO15765 message
# make sure pgn is da00 or the other one
def is_transport(data):
    return get_first_nibble(data[0]) != 0

def is_first_frame(data):
    return get_first_nibble(data[0]) == 1

def is_consecutive_frame(data):
    return get_first_nibble(data[0]) == 2

def is_fc_frame(data):
    return get_first_nibble(data[0]) == 3

def dissect_first_frame(data):
    data_length = (get_second_nibble(data[0]) << 8) | data[1]
    first_data = data[2:]
    return (data_length, first_data)

def dissect_consecutive_frame(data):
    seq_num = get_second_nibble(data[0])
    data_portion = data[1:]

    return (seq_num, data_portion)

def dissect_fc_frame(data):
    flow_status = get_second_nibble(data[0])
    block_size = data[1]
    separation_time = data[2]#in milliseconds, minimum

    return (flow_status, block_size, separation_time)

def dissect_other_frame(data):
    data_length = data[0]
    message_data = data[1:]

    return data_length, message_data

#separate block of data into chunks appropriate for ISO15765 comms
def transport_separate_data(data):
    data_ptr = 0
    length = len(data)
    data_ptr += 6
    yield block[:6]
    while data_ptr < length:
        yield block[data_ptr:data_ptr + 7]
        data_ptr += 7

class ISOTransportQueue:
    def __init__(self, source_address, dest_address, first_frame_message):
        self.dest_address = dest_address
        self.source_address = source_address
        (self.data_length, first_data) = dissect_first_frame(first_frame_message)
        remaining_data = self.data_length - 6
        num_data_messages = remaining_data // 7 if remaining_data % 7 == 0 else remaining_data // 7 + 1
        self.message_queue = [None] * (num_data_messages + 1)
        self.message_queue[0] = first_data

    def add_message(self, consecutive_frame):
        (seq_num, data_portion) = dissect_consecutive_frame(consecutive_frame)
        i = seq_num
        while i < len(self.message_queue):
            if self.message_queue[i] is None:
                self.message_queue[i] = data_portion
                return
            else:
                i += 16

        #raise Exception("ISO15765 message_queue full")

    def is_full(self):
        return None not in self.message_queue

    def get_data(self):
        if self.is_full():
            return b''.join(self.message_queue)[:self.data_length]
        else:
            raise Exception("Called get_data on ISOTransportQueue before full")


class ISO15765Driver():
    def __init__(self, parent, iso_read_queue,):
        self.read_queue = iso_read_queue
        self.root = parent
        self.transport_queues = {}
        self.uds_count = 0
        self.uds_messages = {}

    def send_message(self, data_bytes, dst=0x00):
        #logger.debug("Sending ISO Message Data: {}".format(data_bytes))
        self.root.send_j1939_message(ISO_PGN, data_bytes, DA=dst, SA=0xf9, priority=6)
    
    def look_up_source(self, sa):
        try:
            return  self.root.j1939db["J1939SATabledb"]["{}".format(sa)]
        except KeyError:
            return "Unknown"

    def read_message(self, display=False):
        # The queue is fed by RP1210ReadMessageThread 
        while self.read_queue.qsize():
            (pgn, priority, src_addr, dst_addr, message_data) = self.read_queue.get()
            #if display:
            #    logger.debug("Received ISO message: {}".format((pgn, priority, src_addr, dst_addr, message_data)))
            if is_first_frame(message_data):
                #don't do anything if we already see a session from this source
                #logger.debug("This was the First Frame of an ISO message.")
                if not self.transport_queues.get(src_addr):
                    self.transport_queues[src_addr] = ISOTransportQueue(src_addr,
                                                                            dst_addr,
                                                                            message_data)
                    fc_data = bytes([(0x3 << 4), 0, 0, 0, 0, 0, 0, 0])
                    if not display: # Only respond if not displaying. Display is a different object
                        self.send_message(fc_data, dst=src_addr)

            elif is_consecutive_frame(message_data):
                #logger.debug("This was a consecutive frame of an ISO message.")
                this_queue = self.transport_queues.get(src_addr)
                if this_queue:
                    this_queue.add_message(message_data)
                    if this_queue.is_full():
                        completed_data = this_queue.get_data()
                        del(self.transport_queues[src_addr])
                        if display:
                            self.display_values(completed_data,
                                                this_queue.source_address,
                                                this_queue.dest_address)
                        return (0xda00, 6, this_queue.source_address,
                                this_queue.dest_address, completed_data)
            elif is_fc_frame(message_data):
                pass
            else:
                data_length, message_data = dissect_other_frame(message_data)
                if display:
                    self.display_values(message_data[:data_length], src_addr, dst_addr)
                return (pgn, priority, src_addr, dst_addr, message_data)
        
        return (None, None, None, None, None)

    def display_values(self, A_data, sa, da):
        """
        Provide a common function to display UDS values in the UDS table
        """
        self.uds_count += 1
        meaning, value, units = self.get_meaning(A_data[0], A_data[1:])
        #["SA","Source","DA","SID","Service Name","Raw Hexadecimal","Meaning","Value","Units","Raw Bytes"]
        self.uds_messages[self.uds_count] = {"SA": sa,
                                          "Source": self.look_up_source(sa),
                                          "DA": da,
                                          "SID": "{:02X}".format(A_data[0]),
                                          "Service Name": self.get_service_identifier(A_data[0]),
                                          "Meaning": meaning,
                                          "Value": value,
                                          "Units": units,
                                          "Raw Bytes": repr(A_data[1:]),
                                          "Encoded Bytes" : str(base64.b64encode(A_data[1:]), "ascii"),
                                          "Raw Hexadecimal": bytes_to_hex_string(A_data[1:])}
        
        #logger.debug(self.uds_messages[self.uds_count])
        
    def get_service_identifier(self, sid):
        """
        Pass in a UDS Service Identifier number and look up what it means. 
        A positive response code has 0x40 added to the SID, so we mask it off to look up 
        the requesting sid. 
        Look up data according to ISO 14229-1:2013 Table 23
        """
        try:
            return service_identifier[sid]
        except KeyError:
            try:
                return "Res. " + service_identifier[sid & 0b10111111]    
            except KeyError:
                return "Unknown SID"
    
    def get_meaning(self, sid, data):
        """
        Using the service identifier, determine which type of data we need. For example, a 0x62 
        is a positive response to the request data by parameter sid. Ues ISO 14229-1 Table C.1 to 
        determine the values. 

        Use the ISO Standard
        """

        meaning = ""
        value = ""
        units = ""
        if sid == 0x62: #positive response to read data by identifier
            code = struct.unpack(">H",data[0:2])[0]
            #look up codes according to ISO 14229-1 Table C1
            if code == 0xF195:
                meaning = "System Supplier ECU Software Version Number"
            elif code ==  0xF190:
                meaning = "Vehicle Identfication Number"
                value = data[2:].decode('ascii','ignore')
                units = "ASCII"
            elif code == 0xF193:
                meaning = "System Supplier ECU Hardware Version Number"   
            elif code == 0xF18C:
                meaning = "ECU Serial Number"
                value = data[2:].decode('ascii','ignore')
                units = "ASCII"
            elif code == 0xF180:
                meaning = "Boot Software Identfication"
            elif code == 0xF181:
                meaning = "Application Software Identfication"
            elif code == 0xF186:
                meaning = "Active Diagnostic Session"
            elif code == 0xF192:
                meaning = "System Supplier ECU Hardware Number"
            elif code == 0xF197:
                meaning = "System Name or Engine Type"

        elif sid == 0x7F: #NACK
            nrc_code = data[1] #negative response code
            #Look up data according to ISO 14229-1:2013 Table A.1
            try:
                meaning = negative_response_codes[nrc_code]
            except KeyError:
                meaning = "Unknown Response Code"
        else:
            try:
                meaning = "{}".format(struct.unpack(">L",data[1:5])[0])
            except struct.error:
                try:
                    meaning = "{}".format(struct.unpack(">H",data[1:3])[0])
                except struct.error:
                    pass
                except:
                    logger.debug(traceback.format_exc())
            except:
                logger.debug(traceback.format_exc())
        return meaning, value, units


    def uds_read_data_by_id(self, param_bytes, dst=0, timeout=.5):
        '''UDS "read data by identifier" message. param_bytes is everything following
           0x22. The message is filled with zeros at the end.
        '''
        message_bytes = bytes([len(param_bytes)+1, 0x22] + list(param_bytes) + [0x00]*(8 - len(param_bytes) - 2))
        return self.get_iso_param(message_bytes, da=0, timeout=timeout, retries=3)
    
    def get_iso_param(self, message_bytes, da=0, timeout=None, retries=3):
        self.send_message(message_bytes, dst=da)
        done = False
        returned_data = None
        start_time = time.time()
        for tries in range(retries):
            while not done and timeout is not None and time.time() - start_time < timeout:
                (pgn, priority, src_addr, dst_addr, data) = self.read_message()
                
                if pgn == 0xDA00 and data[0] ^ message_bytes[1] == 0x40:
                    returned_data = data
                    done = True

                    source_key = "{} on J1939".format(self.root.J1939.get_sa_name(src_addr))
                    try:
                        if data[0:3] == bytes([0x62, 0xF1, 0x90]):    
                            self.root.data_package["Component Information"][source_key].update({"VIN from ISO": get_printable_chars(data[3:])})
                        elif data[0:3] == bytes([0x62, 0xF1, 0x8C]):    
                            self.root.data_package["Component Information"][source_key].update({"ECU Serial Number from ISO": get_printable_chars(data[3:])})
                        elif data[0:3] == bytes([0x62, 0xF1, 0x95]):    
                            self.root.data_package["Component Information"][source_key].update({"ECU Software Version from ISO": ' '.join(['{}'.format(b) for b in data[3:]])})
                        elif data[0:3] == bytes([0x62, 0xF1, 0x93]):    
                            self.root.data_package["Component Information"][source_key].update({"ECU Hardware Version from ISO": ' '.join(['{}'.format(b) for b in data[3:]])})
                    except KeyError:
                        pass
                QCoreApplication.processEvents()
            if done:
                break
        

        return returned_data

def init_session(isodriver):
    message_bytes = bytes([0x2, 0x10, 0x81, 0, 0, 0, 0, 0])
    isodriver.send_message(message_bytes, 0)

