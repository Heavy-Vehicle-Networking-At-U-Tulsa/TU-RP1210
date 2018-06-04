#!/usr/bin/env python3
from PyQt5.QtCore import QCoreApplication
import time
import sys
import struct
import threading
import json
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
        #["Line","SA","Source","DA","SID","Service Name","Raw Hexadecimal","Meaning","Value","Units","Raw Bytes"]
        self.uds_messages["{}".format(self.uds_count)] = {"Line": "{:7d}".format(self.uds_count),
            "SA": sa,
            "Source": self.look_up_source(sa),
            "DA": da,
            "SID": "{:02X}".format(A_data[0]),
            "Service Name": self.get_service_identifier(A_data[0]),
            "Meaning": meaning,
            "Value": value,
            "Units": units,
            "Raw Bytes": repr(A_data[1:]),
            "Encoded Bytes" : str(base64.b64encode(A_data), "ascii"),
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


class UDSResponder(threading.Thread):
    def __init__(self, parent, recording, rxqueue):
        threading.Thread.__init__(self)
        self.root = parent
        self.recording = recording #self.data_package["UDS Messages"]
        self.rxqueue = rxqueue
        self.response_dict = {}
        self.rx_count = 0
        self.runSignal = True
        self.max_count = 500 #For the progress bar
        self.create_responses()
        
    def run(self):
        
        #clear queue
        while self.rxqueue.qsize():
            rxmessage = self.rxqueue.get()

        while self.runSignal:
            time.sleep(0.005)
            while self.rxqueue.qsize():

                rxmessage = self.rxqueue.get()
                #logger.debug("RX: " + bytes_to_hex_string(rxmessage))
                if rxmessage[4] == 0 and rxmessage[7] == 0xDA: #Echo is on. See The CAN Message from RP1210_ReadMessage
                    logger.debug("RX: " + bytes_to_hex_string(rxmessage[6:]))
                    self.rx_count+=1
                    if self.rx_count == self.max_count:
                        self.rx_count = 1
                    da = rxmessage[8]
                    sa = rxmessage[9]
                    length = rxmessage[10]
                    sid = rxmessage[11]
                    req_bytes=rxmessage[11:11+length]
                    response_key = (sa, bytes_to_hex_string(req_bytes))
                    logger.debug("Looking for {}".format(response_key))
                    try:
                        tx_msg_list = self.response_dict[response_key]
                    except KeyError:
                        logger.debug("No Response.")
                        #logger.debug(traceback.format_exc())
                    else:
                        #TODO: Write a routine to transport 
                        
                        for msg_segment in tx_msg_list:
                            logger.debug("TX: " + bytes_to_hex_string(msg_segment))
                            bytes_to_send = bytes([0x01, 0x18, 0xDA, sa, da]) + msg_segment
                            self.root.RP1210.send_message(self.root.client_ids["CAN"], bytes_to_send)
                            time.sleep(0.001)
                            if msg_segment[0] == (0x10 & 0xF0):
                                time.sleep(0.005)
                                self.wait_for_ack()
                
                elif rxmessage[10:13] == b'\x00\xEE\x00':
                        logger.debug("REQ: " + bytes_to_hex_string(rxmessage[10:]))
                        for i in range(10):
                            bytes_to_send = bytes([0x01, 0x18, 0xEE, 0xFF, 0x00, 0xF7, 0x02, 0xA1, 0x01, 0x00, 0x00, 0x00, 0x10])
                            self.root.RP1210.send_message(self.root.client_ids["CAN"], bytes_to_send)
                            logger.debug("TX: " + bytes_to_hex_string(bytes_to_send))
                            time.sleep(0.010)           

    def wait_for_ack(self):
        start_time = time.time()
        while time.time() - start_time < .2:
            while self.rxqueue.qsize():
                rxmessage = self.rxqueue.get()
                #Check the following: 1) Not an echo message, 2) it's an ISO message, and 3) its a response
                if rxmessage[4] == 0 and rxmessage[7] == 0xDA and rxmessage[10] == 0x30: 
                    logger.debug("RX: " + bytes_to_hex_string(rxmessage[10:]))
                    return
            time.sleep(0.001)
        logger.debug("UDS Responder Timed Out looking for ack message.")
    
    def create_responses(self):
        length = len(self.recording)
        logger.debug("Length of ISO Traffic Record: {}".format(length))
        response_dict = {}
        response_dict[(249, bytes_to_hex_string(b'\x10\x01'))] = [b'\x50\x01']
        message_index = 1
        #logger.debug(self.data_package["UDS Messages"])
        while message_index < length:
            message = self.recording["{}".format(message_index)]
            message_index += 1
            if message["SA"] == 249: #Source from VDA
                #search through the messages for a response
                da = int(message["DA"])
                sid = int(message["SID"],16)
                if sid == 0x3E: #tester present (these sometimes don't have responses.)
                    continue
                len_req_bytes = len(base64.b64decode(message["Encoded Bytes"]))
                req_bytes = base64.b64decode(message["Encoded Bytes"])[:min(len_req_bytes,4)]
                response_message_index = message_index
                

                #Don't redo lookups
                # if response_key in self.response_dict.keys():
                #     logger.debug("Already found Item.")
                #     continue

                while response_message_index < min(response_message_index + 100, length):
                    response_message = self.recording["{}".format(response_message_index)]
                    response_message_index += 1
                    response_sid = int(response_message["SID"],16)
                    response_sa = int(response_message["SA"])
                    response = base64.b64decode(response_message["Encoded Bytes"])[1:]

                    if response_sa == da and response_sid != 0x7E :
                    #tests
                    #logger.debug("response_sa: {} == da: {}".format(response_sa,da))
                    #logger.debug("response_sid - 0x40: {} == sid: {}".format(response_sid - 0x40,sid))
                        logger.debug("response: {} == req_bytes: {}".format(bytes_to_hex_string(response[:min(len_req_bytes,4)-1]), bytes_to_hex_string(req_bytes[1:])))
                        response_len = len(response)
                        if (response_sid - 0x40) == sid and response[:min(len_req_bytes,4)-1] == req_bytes[1:]:
                            if response_len < 6:
                                response_bytes = [bytes([response_len+1]) + bytes([response_sid]) + response]
                            else:
                                first_two_bytes = struct.pack(">H", 0x1000 | (0x0FFF & response_len+1)) #first frame plus 12 bits for length 
                                response_bytes = [ first_two_bytes + bytes([response_sid]) + response[:5] ]
                                frame = 1
                                for i in range(5,response_len,7):
                                    first_byte = struct.pack("B", 0x20 | (0x0F & frame))
                                    frame += 1
                                    response_bytes.append( first_byte + response[i:i+7] )
                                    while len(response_bytes[-1]) < 8:
                                        response_bytes[-1] += b'\xFF'
                        elif response_sid == 0x7F and response[0] == sid:
                            response_bytes = [bytes([response_len+1]) + bytes([response_sid]) + response]
                        else:
                            continue
                        #logger.debug(response_bytes)
                        response_key = (249, bytes_to_hex_string(req_bytes))
                        logger.debug("Found {}".format(response_key))
                        self.response_dict[response_key] = response_bytes
                        break
                    

        #Tester present response.
        self.response_dict[(249, bytes_to_hex_string(b'\x3E\x00'))] = [b'\x02\x7E\x00']
        
        # Add special codes and Negative responses. 
        # TODO: Make this a GUI widget.
        #self.response_dict[(249, bytes_to_hex_string(b'\x10\x01'))] = [b'\x02\x50\x01']
        self.response_dict[(249, bytes_to_hex_string(b'\x10\x60'))] = [b'\x03\x7F\x10\x12']

        logger.info("Created UDS Response Dictionary")
        for k,v in sorted(self.response_dict.items()):
            logger.debug("{}: {}".format(k,v))