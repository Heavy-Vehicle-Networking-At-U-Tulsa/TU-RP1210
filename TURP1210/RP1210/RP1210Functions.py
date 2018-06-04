import time
import traceback
import string
import logging
logger = logging.getLogger(__name__)


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

def hex_string_to_bytes(hex_string):
    try:
        return bytes([int(c,16) for c in hex_string.split()])
    except (TypeError, IndexError):
        # When unable to iterate over byte_string just return an empty string                                                                                                                             
        logger.debug(traceback.format_exc)
        return b''


def get_local_time_string(ts):
    return time.strftime("%A, %d %b %Y at %H:%M:%S %Z", time.localtime(ts))


# A file with constants useful for RP1210 accplications

# RP1210B   RP1210_SendCommand Defines (From RP1210B Document)
RP1210_Reset_Device                          = 0
RP1210_Set_All_Filters_States_to_Pass        = 3
RP1210_Set_Message_Filtering_For_J1939       = 4
RP1210_Set_Message_Filtering_For_CAN         = 5
RP1210_Set_Message_Filtering_For_J1708       = 7
RP1210_Set_Message_Filtering_For_J1850       = 8
RP1210_Set_Message_Filtering_For_ISO15765    = 9
RP1210_Generic_Driver_Command                = 14
RP1210_Set_J1708_Mode                        = 15
RP1210_Echo_Transmitted_Messages             = 16
RP1210_Set_All_Filters_States_to_Discard     = 17
RP1210_Set_Message_Receive                   = 18
RP1210_Protect_J1939_Address                 = 19
RP1210_Set_Broadcast_For_J1708               = 20
RP1210_Set_Broadcast_For_CAN                 = 21
RP1210_Set_Broadcast_For_J1939               = 22
RP1210_Set_Broadcast_For_J1850               = 23
RP1210_Set_J1708_Filter_Type                 = 24
RP1210_Set_J1939_Filter_Type                 = 25
RP1210_Set_CAN_Filter_Type                   = 26
RP1210_Set_J1939_Interpacket_Time            = 27
RP1210_SetMaxErrorMsgSize                    = 28
RP1210_Disallow_Further_Connections          = 29
RP1210_Set_J1850_Filter_Type                 = 30
RP1210_Release_J1939_Address                 = 31
RP1210_Set_ISO15765_Filter_Type              = 32
RP1210_Set_Broadcast_For_ISO15765            = 33
RP1210_Set_ISO15765_Flow_Control             = 34
RP1210_Clear_ISO15765_Flow_Control           = 35
RP1210_Set_ISO15765_Link_Type                = 36
RP1210_Set_J1939_Baud                        = 37
RP1210_Set_ISO15765_Baud                     = 38
RP1210_Set_BlockTimeout                      = 215
RP1210_Set_J1708_Baud                        = 305

# RP1210B Constants - Check RP1210B document for any updates.
CONNECTED                  =                    1  ## Connection state = Connected 
NOT_CONNECTED              =                   -1  ## Connection state = Disconnected

FILTER_PASS_NONE           =                    0  ## Filter state = DISCARD ALL MESSAGES
FILTER_PASS_SOME           =                    1  ## Filter state = PASS SOME (some filters)
FILTER_PASS_ALL            =                    2  ## Filter state = PASS ALL

NULL_WINDOW                =                    0  ## Windows 3.1 is no longer supported.

BLOCKING_IO                =                    1  ## For Blocking calls to send/read.
NON_BLOCKING_IO            =                    0  ## For Non-Blocking calls to send/read.
BLOCK_INFINITE             =                    0  ## For Non-Blocking calls to send/read.

BLOCK_UNTIL_DONE           =                    0  ## J1939 Address claim, wait until done
RETURN_BEFORE_COMPLETION   =                    2  ## J1939 Address claim, don't wait

CONVERTED_MODE             =                    1  ## J1708 RP1210Mode="Converted"
RAW_MODE                   =                    0  ## J1708 RP1210Mode="Raw"

MAX_J1708_MESSAGE_LENGTH   =                  508  ## Maximum size of J1708 message (+1)
MAX_J1939_MESSAGE_LENGTH    =                1796  ## Maximum size of J1939 message (+1)
MAX_ISO15765_MESSAGE_LENGTH =                4108  ## Maximum size of ISO15765 message (+1)

ECHO_OFF                    =                0x00  ## EchoMode
ECHO_ON                     =                0x01  ## EchoMode

RECEIVE_ON                  =                0x01  ## Set Message Receive
RECEIVE_OFF                 =                0x00  ## Set Message Receive

ADD_LIST                    =                0x01  ## Add a message to the list.
VIEW_B_LIST                 =                0x02  ## View an entry in the list.
DESTROY_LIST                =                0x03  ## Remove all entries in the list.
REMOVE_ENTRY                =                0x04  ## Remove a specific entry from the list.
LIST_LENGTH                 =                0x05  ## Returns number of items in list.

FILTER_PGN                  =          0x00000001  ## Setting of J1939 filters
FILTER_PRIORITY             =          0x00000002  ## Setting of J1939 filters
FILTER_SOURCE               =          0x00000004  ## Setting of J1939 filters
FILTER_DESTINATION          =          0x00000008  ## Setting of J1939 filters
FILTER_INCLUSIVE            =                0x00  ## FilterMode
FILTER_EXCLUSIVE            =                0x01  ## FilterMode

SILENT_J1939_CLAIM          =                0x00  ## Claim J1939 Address
PASS_J1939_CLAIM_MESSAGES   =                0x01  ## Claim J1939 Address

CHANGE_BAUD_NOW             =                0x00  ## Change Baud
MSG_FIRST_CHANGE_BAUD       =                0x01  ## Change Baud
RP1210_BAUD_9600            =                0x00  ## Change Baud
RP1210_BAUD_19200           =                0x01  ## Change Baud
RP1210_BAUD_38400           =                0x02  ## Change Baud
RP1210_BAUD_57600           =                0x03  ## Change Baud
RP1210_BAUD_125k            =                0x04  ## Change Baud
RP1210_BAUD_250k            =                0x05  ## Change Baud
RP1210_BAUD_500k            =                0x06  ## Change Baud
RP1210_BAUD_1000k           =                0x07  ## Change Baud

STANDARD_CAN                =                0x00  ## Filters
EXTENDED_CAN                =                0x01  ## Filters
STANDARD_CAN_ISO15765_EXTENDED =             0x02  ## 11-bit with ISO15765 extended address
EXTENDED_CAN_ISO15765_EXTENDED =             0x03  ## 29-bit with ISO15765 extended address
STANDARD_MIXED_CAN_ISO15765    =             0x04  ## 11-bit identifier with mixed addressing
ISO15765_ACTUAL_MESSAGE        =             0x00  ## ISO15765 ReadMessage - type of data
ISO15765_CONFIRM               =             0x01  ## ISO15765 ReadMessage - type of data
ISO15765_FF_INDICATION         =             0x02  ## ISO15765 ReadMessage - type of data

LINKTYPE_GENERIC_CAN               =         0x00  ## Set_ISO15765_Link_Type argument
LINKTYPE_J1939_ISO15765_2_ANNEX_A  =         0x01  ## Set_ISO15765_Link_Type argument
LINKTYPE_J1939_ISO15765_3          =         0x02  ## Set_ISO15765_Link_Type argument

# Local Definitions
J1939_GLOBAL_ADDRESS                   =      255
J1939_OFFBOARD_DIAGNOSTICS_TOOL_1      =      249
J1587_OFFBOARD_DIAGNOSTICS_TOOL_1      =      172

# PrintRP1210Error Dictionary data Structure
RP1210Errors = {
    0: "NO ERRORS",
    128: "ERR DLL NOT INITIALIZED",
    129: "ERR INVALID CLIENT ID",
    130: "ERR CLIENT ALREADY CONNECTED",
    131: "ERR CLIENT AREA FULL",
    132: "ERR FREE MEMORY",
    133: "ERR NOT ENOUGH MEMORY",
    134: "ERR INVALID DEVICE",
    135: "ERR DEVICE IN USE",
    136: "ERR INVALID PROTOCOL",
    137: "ERR TX QUEUE FULL",
    138: "ERR TX QUEUE CORRUPT",
    139: "ERR RX QUEUE FULL",
    140: "ERR RX QUEUE CORRUPT",
    141: "ERR MESSAGE TOO LONG",
    142: "ERR HARDWARE NOT RESPONDING",
    143: "ERR COMMAND NOT SUPPORTED",
    144: "ERR INVALID COMMAND",
    145: "ERR TXMESSAGE STATUS",
    146: "ERR ADDRESS CLAIM FAILED",
    147: "ERR CANNOT SET PRIORITY",
    148: "ERR CLIENT DISCONNECTED",
    149: "ERR CONNECT NOT ALLOWED",
    150: "ERR CHANGE MODE FAILED",
    151: "ERR BUS OFF",
    152: "ERR COULD NOT TX ADDRESS CLAIMED",
    153: "ERR ADDRESS LOST",
    154: "ERR CODE NOT FOUND",
    155: "ERR BLOCK NOT ALLOWED",
    156: "ERR MULTIPLE CLIENTS CONNECTED",
    157: "ERR ADDRESS NEVER CLAIMED",
    158: "ERR WINDOW HANDLE REQUIRED",
    159: "ERR MESSAGE NOT SENT",
    160: "ERR MAX NOTIFY EXCEEDED",
    161: "ERR MAX FILTERS EXCEEDED",
    162: "ERR HARDWARE STATUS CHANGE",
    202: "ERR INI FILE NOT IN WIN DIR",
    204: "ERR INI SECTION NOT FOUND",
    205: "ERR INI KEY NOT FOUND",
    206: "ERR INVALID KEY STRING",
    207: "ERR DEVICE NOT SUPPORTED",
    208: "ERR INVALID PORT PARAM",
    213: "ERR COMMAND TIMED OUT",
    220: "ERR OS NOT SUPPORTED",
    222: "ERR COMMAND QUEUE IS FULL",
    224: "ERR CANNOT SET CAN BAUDRATE",
    225: "ERR CANNOT CLAIM BROADCAST ADDRESS",
    226: "ERR OUT OF ADDRESS RESOURCES",
    227: "ERR ADDRESS RELEASE FAILED",
    230: "ERR COMM DEVICE IN USE",
    441: "ERR DATA LINK CONFLICT",
    453: "ERR ADAPTER NOT RESPONDING",
    454: "ERR CAN BAUD SET NONSTANDARD",
    455: "ERR MULTIPLE CONNECTIONS NOT ALLOWED NOW",
    456: "ERR J1708 BAUD SET NONSTANDARD",
    457: "ERR J1939 BAUD SET NONSTANDARD",
    458: "ERR ISO15765 BAUD SET NONSTANDARD"}
