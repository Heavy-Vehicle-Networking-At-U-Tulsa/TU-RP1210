# Python3
# RP1210 Exercise #3
# Connect the RP1210 Client
# 
# 

# We need the following to interface with the RP1210 DLL
from ctypes import *
from ctypes.wintypes import HWND

# The following entry needs to be in RP121032.ini 
dll_in_use = "DGDPA5MA"

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
print("Client Connected with a value of {}".format(client_id))
if client_id > 127: # Then there is an error code
    fpchDescription = (c_char*80)()
    return_value_1 = RP1210_GetErrorMsg(c_short(client_id), byref(fpchDescription))
    description = fpchDescription.value.decode('ascii','ignore')
    print("RP1210_ClientConnect failed: {}".format(description))
else:
    print("Success!")

# Example Solution:
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
    return_value_1 = RP1210_GetErrorMsg(c_short(return_value), byref(fpchDescription))
    description = fpchDescription.value.decode('ascii','ignore')
    message = "RP1210_ReadDetailedVersion failed with\na return value of  {}: {}".format(return_value, description)
print(message)

ret_val = RP1210_ClientDisconnect(client_id)
print("Client Disconnected with return value of: {}".format(ret_val))
