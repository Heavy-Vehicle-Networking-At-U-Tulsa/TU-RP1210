# Python3
# RP1210 Exercise #5
# Send Requests for Component ID
# 
# 

# We need the following to interface with the RP1210 DLL
from ctypes import *
from ctypes.wintypes import HWND
import struct
import time
import random

# The following entry needs to be in RP121032.ini 
dll_in_use = "DGDPA5MA"

delay = 0.5

RP1210DLL = windll.LoadLibrary(dll_in_use + ".dll")

prototype = WINFUNCTYPE(c_short, HWND, c_short, c_char_p, c_long, c_long, c_short)
RP1210_ClientConnect = prototype(("RP1210_ClientConnect", RP1210DLL))

prototype = WINFUNCTYPE(c_short, c_short,  POINTER(c_char*2000), c_short, c_short, c_short)
RP1210_SendMessage = prototype(("RP1210_SendMessage", RP1210DLL))

prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*2000), c_short, c_short)
RP1210_ReadMessage = prototype(("RP1210_ReadMessage", RP1210DLL))

prototype = WINFUNCTYPE(c_short, c_short, c_short, POINTER(c_char*2000), c_short)
RP1210_SendCommand = prototype(("RP1210_SendCommand", RP1210DLL))

# Example Solution:
prototype = WINFUNCTYPE(c_short, c_short)
RP1210_ClientDisconnect = prototype(("RP1210_ClientDisconnect", RP1210DLL))

#Additional functionality
prototype = WINFUNCTYPE(c_short, c_char_p, c_char_p, c_char_p, c_char_p)
RP1210_ReadVersion = prototype(("RP1210_ReadVersion", RP1210DLL))

prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*17), POINTER(c_char*17), POINTER(c_char*17))
RP1210_ReadDetailedVersion = prototype(("RP1210_ReadDetailedVersion", RP1210DLL))

prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*64), c_short, c_short)
RP1210_GetHardwareStatus = prototype(("RP1210_GetHardwareStatus", RP1210DLL))

prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*80))
RP1210_GetErrorMsg = prototype(("RP1210_GetErrorMsg", RP1210DLL))

#Connect to a J1939 Client
deviceID = 1 #This is from the Vendor Specific INI file
protocol_bytes = bytes("J1939",'ascii')
client_id = RP1210_ClientConnect(HWND(None), c_short(deviceID), protocol_bytes, 0, 0, 0)
print("Client Connected with a value of: {}".format(client_id))
if client_id > 127: # Then there is an error code
    fpchDescription = (c_char*80)()
    return_value_1 = RP1210_GetErrorMsg(c_short(client_id), byref(fpchDescription))
    description = fpchDescription.value.decode('ascii','ignore')
    print("RP1210_ClientConnect failed: {}".format(description))
    exit()

# Display the detailed version that pulls the firmware version from the device.
APIVersionInfo    = (c_char*17)()
DLLVersionInfo    = (c_char*17)()
FWVersionInfo     = (c_char*17)()
return_value = RP1210_ReadDetailedVersion(c_short(client_id),
                                        byref(APIVersionInfo),
                                        byref(DLLVersionInfo),
                                        byref(FWVersionInfo))
if return_value == 0:
    message = 'The PC computer has successfully connected to the RP1210 Device.\nThere is no need to check your USB connection.\n'
    DLL = DLLVersionInfo.value
    API = APIVersionInfo.value
    FW  = APIVersionInfo.value
    message += "DLL = {}\n".format(DLL.decode('ascii','ignore'))
    message += "API = {}\n".format(API.decode('ascii','ignore'))
    message += "FW  = {}".format(FW.decode('ascii','ignore'))
else:
    # Set up the description buffer
    fpchDescription = (c_char*80)()
    RP1210_GetErrorMsg(c_short(return_value), byref(fpchDescription))
    description = fpchDescription.value.decode('ascii','ignore')
    message = "RP1210_ReadDetailedVersion failed with\na return value of  {}: {}".format(return_value, description)
print(message)

#Set all filters to pass
# Setup a message buffer for RP1210 traffic
TxRxBuffer = (c_char*2000)()

#From RP1210 API 
RP1210_Set_All_Filters_States_to_Pass = 3
return_value = RP1210_SendCommand(c_short(RP1210_Set_All_Filters_States_to_Pass),
                                  c_short(client_id),
                                  byref(TxRxBuffer),
                                  c_short(0))
if return_value != 0:
    fpchDescription = (c_char*80)()
    RP1210_GetErrorMsg(c_short(return_value), byref(fpchDescription))
    description = fpchDescription.value.decode('ascii','ignore')
    print("RP1210_Set_All_Filters_States_to_Pass failed with a return value of {}: {}".format(return_value,description))
else:
    print("RP1210_Set_All_Filters_States_to_Pass succeeded.")

# Set some constants
BLOCKING_IO = 1
NON_BLOCKING_IO = 0

#Read some messages:
message_count = 0
start_time = time.time()
try: 
    while message_count < 10000:
        if time.time() - start_time > delay:
            start_time = time.time()
            delay = 1+random.random()

            #send a request message for Component ID per J1939-21
            # Populate the send buffer per RP1210 Send_Message for J1939
            TxRxBuffer[0] = 0x00 # PGN for Request LSB
            TxRxBuffer[1] = 0xEA # PGN for Request 
            TxRxBuffer[2] = 0x00 # PGN for Request MSB
            TxRxBuffer[3] = 0x06 # Priority
            TxRxBuffer[4] = 0xF9 # Source Address (Diagnostics Tool)
            TxRxBuffer[5] = 0xFF # Destination Send it to everyone (Try ECU Source too)
            TxRxBuffer[6] = 0xEB # LSB of Component ID PGN
            TxRxBuffer[7] = 0xFE # Component ID PGN
            TxRxBuffer[8] = 0x00 # MSB of Component ID PGN
            
            msg_len = 9
            print("Sending Request "+" ".join("{:02X}".format(c) for c in TxRxBuffer[0:msg_len]))
            #call the command
            return_value = RP1210_SendMessage(c_short(client_id),
                                              byref(TxRxBuffer),
                                              c_short(msg_len), 0, 0)
            if return_value != 0:
                fpchDescription = (c_char*80)()
                RP1210_GetErrorMsg(c_short(return_value), byref(fpchDescription))
                description = fpchDescription.value.decode('ascii','ignore')
                print("RP1210_SendMessage failed with a return value of {}: {}".format(return_value,description))
                break
            else:
                print("Request for Component ID was sent.")
        else:
            # Sleep for a millisecond
            time.sleep(0.001)    

        return_value = RP1210_ReadMessage(c_short(client_id),
                                          byref(TxRxBuffer),
                                          c_short(2000),
                                          c_short(NON_BLOCKING_IO))
        if return_value > 0:
            message_count +=1
           
            # RP1210: The J1939 Message from RP1210_ReadMessage
            # Assume Echo is off
            vda_timestamp = struct.unpack(">L",TxRxBuffer[0:4])[0]
            pgn = struct.unpack("<L", TxRxBuffer[4:7] + b'\x00')[0]
            how = struct.unpack("B",TxRxBuffer[7])[0] 
            sa = struct.unpack("B",TxRxBuffer[8])[0]
            da = struct.unpack("B",TxRxBuffer[9])[0]
            message = TxRxBuffer[10:return_value]
            # Use a list comprehension to make a hex representation of the message.
            msg_str = " ".join(["{:02X}".format(c) for c in message])                              
            #print("{:12d} ({},{},{},{}) {}".format(vda_timestamp,pgn,sa,da,how,msg_str))

            if pgn == 0xFEEB: #PGN is 65269
                print("Found Component ID:")
                print(message)
                
except KeyboardInterrupt:
    print("\nCtrl - C pressed.")
ret_val = RP1210_ClientDisconnect(client_id)
print("Client Disconnected with return value of: {}".format(ret_val))

# Assignment: 
#  Request VIN
