#!/usr/bin/env python3
from PyQt5.QtCore import QCoreApplication
import time
import sys
import struct
import base64

from TU_RP1210functions import *

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("{timestamp: '%(asctime)s', level: '%(levelname)s', function: '%(funcName)s', message: '%(message)s'}",
    datefmt='%Y-%m-%d %H:%M:%S')
#file_handler = logging.FileHandler('RP1210 ' + start_time + '.log',mode='w')
file_handler = logging.FileHandler('TruckCRYPT.log', mode='w')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)


ISO_PGN = 0xDA00

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

    def send_message(self, data_bytes, dst=0x00):
        #logger.debug("Sending ISO Message Data: {}".format(data_bytes))
        self.root.send_j1939_message(ISO_PGN, data_bytes, DA=dst, SA=0xf9, priority=6)
    
    def look_up_source(self, sa):
        try:
            return  self.root.j1939db["J1939SATabledb"]["{}".format(sa)]
        except KeyError:
            return "Unknown"

    def read_message(self):
        # The queue is fed by RP1210ReadMessageThread 
        while self.read_queue.qsize():
            (pgn, priority, src_addr, dst_addr, message_data) = self.read_queue.get()
            #logger.debug("Received ISO message: {}".format((pgn, priority, src_addr, dst_addr, message_data)))
            if is_first_frame(message_data):
                #don't do anything if we already see a session from this source
                #logger.debug("This was the First Frame of an ISO message.")
                if not self.transport_queues.get(src_addr):
                    self.transport_queues[src_addr] = ISOTransportQueue(src_addr,
                                                                            dst_addr,
                                                                            message_data)
                    fc_data = bytes([(0x3 << 4), 0, 0, 0, 0, 0, 0, 0])
                    self.send_message(fc_data, dst=src_addr)


            elif is_consecutive_frame(message_data):
                #logger.debug("This was a consecutive frame of an ISO message.")
                this_queue = self.transport_queues.get(src_addr)
                if this_queue:
                    this_queue.add_message(message_data)
                    if this_queue.is_full():
                        completed_data = this_queue.get_data()
                        del(self.transport_queues[src_addr])
                        self.uds_count += 1
                        self.root.J1939.uds_messages[self.uds_count]={"SA": this_queue.source_address,
                                                              "Source": self.look_up_source(this_queue.source_address),
                                                              "DA": this_queue.dest_address,
                                                              "Desination": self.look_up_source(this_queue.dest_address),
                                                              "Raw Bytes": repr(completed_data), 
                                                              "Encoded Bytes" : str(base64.b64encode(completed_data), "ascii"),
                                                              "Raw Hexadecimal": bytes_to_hex_string(completed_data)}
                        self.root.J1939.fill_uds_table()
                        return (0xda00, 6, this_queue.source_address,
                                this_queue.dest_address, completed_data)
            elif is_fc_frame(message_data):
                pass
            else:
                data_length, message_data = dissect_other_frame(message_data)
                self.uds_count += 1
                self.root.J1939.uds_messages[self.uds_count]={"SA": src_addr,
                                                              "Source": self.look_up_source(src_addr),
                                                              "DA": dst_addr,
                                                              "Desination": self.look_up_source(dst_addr),
                                                              "Raw Bytes": repr(message_data[:data_length]),
                                                              "Encoded Bytes" : str(base64.b64encode(message_data[:data_length]), "ascii"),
                                                              "Raw Hexadecimal": bytes_to_hex_string(message_data[:data_length])}
                self.root.J1939.fill_uds_table()
                return (pgn, priority, src_addr, dst_addr, message_data)
        
        return (None, None, None, None, None)

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
                    if data[0:3] == bytes([0x62, 0xF1, 0x90]):    
                        self.root.data_package["Component Information"][source_key].update({"VIN from ISO": get_printable_chars(data[3:])})
                    elif data[0:3] == bytes([0x62, 0xF1, 0x8C]):    
                        self.root.data_package["Component Information"][source_key].update({"ECU Serial Number from ISO": get_printable_chars(data[3:])})
                    elif data[0:3] == bytes([0x62, 0xF1, 0x95]):    
                        self.root.data_package["Component Information"][source_key].update({"ECU Software Version from ISO": ' '.join(['{}'.format(b) for b in data[3:]])})
                    elif data[0:3] == bytes([0x62, 0xF1, 0x93]):    
                        self.root.data_package["Component Information"][source_key].update({"ECU Hardware Version from ISO": ' '.join(['{}'.format(b) for b in data[3:]])})
                    
                QCoreApplication.processEvents()
            if done:
                break
        

        return returned_data

def init_session(isodriver):
    message_bytes = bytes([0x2, 0x10, 0x81, 0, 0, 0, 0, 0])
    isodriver.send_message(message_bytes, 0)

def get_paccar_hard_brakes():
#    data_page_num = int(sys.argv[1])
    data_pages = [None]*6
    snapshotter = TrafficSnapshotter.TrafficSnapshotter()
    __isodriver = ISO15765Driver(snapshotter)
    
    message_bytes = bytes([0x2, 0x10, 0x81, 0, 0, 0, 0,0])
    
    for data_page_num in [0,1,2,3,4,5]:

        '''        print("initializing session for datapage %d" % data_page_num)
        init_session(__isodriver)
        done = False
        while not done:
            (pgn, priority, src_addr, dst_addr, data) = __isodriver.read_message()
            #        print( repr( (hex(pgn), priority, src_addr, dst_addr, data) ) )
            if pgn == 0xDA00:
                print( repr( (hex(pgn), priority, src_addr, dst_addr, data) ) )
                done = True'''

        print("requesting PACCAR data page %d" % data_page_num)

        message_bytes = bytes([0x2, 0x33, 0x60 | data_page_num, 0, 0, 0, 0, 0])
        __isodriver.send_message(message_bytes, 0)
        time.sleep(2)
        done = False
        while not done:
            (pgn, priority, src_addr, dst_addr, data) = __isodriver.read_message()
            #           print( repr( (hex(pgn), priority, src_addr, dst_addr, data) ) )
            if pgn == 0xDA00:
                data_pages[data_page_num] = data
                done = True
        saved_snapshot = snapshotter.snapshot
        del(snapshotter)
        del(__isodriver)
        snapshotter = TrafficSnapshotter.TrafficSnapshotter(saved_snapshot)
        __isodriver = ISO15765Driver(snapshotter)
        
    datas = []
    for i in range(0, 5, 2):
        datas.append(data_pages[i][2:]+data_pages[i+1][2:])
    

def get_paccar_snapshot_recorder():
#    data_page_num = int(sys.argv[1])
    data_pages = [None] * 33
    total_pages = 0
    page_lengths = []
    snapshotter = TrafficSnapshotter.TrafficSnapshotter()
    __isodriver = ISO15765Driver(snapshotter)
    
    message_bytes = bytes([0x2, 0x10, 0x81, 0, 0, 0, 0,0])
    
    for data_page_num in range(0x31, 0x52):

        '''        print("initializing session for datapage %d" % data_page_num)
        init_session(__isodriver)
        done = False
        while not done:
            (pgn, priority, src_addr, dst_addr, data) = __isodriver.read_message()
            #        print( repr( (hex(pgn), priority, src_addr, dst_addr, data) ) )
            if pgn == 0xDA00:
                print( repr( (hex(pgn), priority, src_addr, dst_addr, data) ) )
                done = True'''

        print("requesting PACCAR data page %s" % hex(data_page_num))

        message_bytes = bytes([0x2, 0x33, data_page_num, 0, 0, 0, 0, 0])
        __isodriver.send_message(message_bytes, 0)
        done = False
        while not done:
            (pgn, priority, src_addr, dst_addr, data) = __isodriver.read_message()
            #           print( repr( (hex(pgn), priority, src_addr, dst_addr, data) ) )
            if pgn == 0xDA00:
      #          data_pages[data_page_num] = data
                print(data)
                page_lengths.append(len(data))
                data_pages[data_page_num - 0x31] = data
                done = True
        snapshotter.cleanup()
        del(snapshotter)
        del(__isodriver)
        snapshotter = TrafficSnapshotter.TrafficSnapshotter()
        __isodriver = ISO15765Driver(snapshotter)
        total_pages +=1


    print("Total pages: %d" % total_pages)
    print("Page lengths: %s" % str(page_lengths))
    return data_pages

def get_unknown_parameter(filename):
#    data_page_num = int(sys.argv[1])
    data_pages = [None]
    total_pages = 0
    page_lengths = []
    snapshotter = TrafficSnapshotter.TrafficSnapshotter()
    __isodriver = ISO15765Driver(snapshotter)
 
    message_bytes0 = bytes([0x02, 0x10, 0x03] + [0x00] * 5)
    message_bytes1 = bytes([0x03, 0x22, 0xf1, 0x57] + [0x00] * 4)

    
    

    __isodriver.send_message(message_bytes1, 0)
    done = False
    start_time = time.time()
    while not done and time.time() - start_time < 30:
        (pgn, priority, src_addr, dst_addr, data) = __isodriver.read_message()
        if pgn == 0xDA00:
            print(data)
            page_lengths.append(len(data))
            data_pages[0] = data
            done = True
    snapshotter.cleanup()
    snapshotter.snapshot.dump_to_log(filename)
    return data_pages


    
