import time
import traceback
import string
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s, %(levelname)s, in %(funcName)s, %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S.')
#file_handler = logging.FileHandler('RP1210 ' + start_time + '.log',mode='w')
file_handler = logging.FileHandler('TruckCRYPT.log', mode='w')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)

def get_printable_chars(data_bytes):
    return ''.join([x if x in string.printable else '' for x in data_bytes.decode('ascii','ignore')])

def get_list_from_dict(data_dict):
    return_list=[]
    for k1,v1 in data_dict.items():
        try:
            if len(v1.items()) > 0:
                return_list.append(['',k1])
            for k2,v2 in v1.items():
                return_list.append(['','',k2,v2])
        except (TypeError, AttributeError):
            pass
    return return_list

def bytes_to_hex_string(byte_string):
    try:
        return " ".join("{:02X}".format(c) for c in byte_string)
    except (TypeError, IndexError):
        # When unable to iterate over byte_string just return an empty string                                                                                                                             
        logger.debug(traceback.format_exc)
        return ""

def get_local_time_string(ts):
    return time.strftime("%A, %d %b %Y at %H:%M:%S %Z", time.localtime(ts))

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