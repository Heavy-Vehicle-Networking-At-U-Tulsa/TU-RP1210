# Python3
# RP1210 Exercise #2
# Load the RP1210 DLL file
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

prototype = WINFUNCTYPE(c_short, c_char_p, c_char_p, c_char_p, c_char_p)
RP1210_ReadVersion = prototype(("RP1210_ReadVersion", RP1210DLL))

# Determine the DLL Versions
DLLMajorVersion    = (c_char)()
DLLMinorVersion    = (c_char)()
APIMajorVersion    = (c_char)()
APIMinorVersion    = (c_char)()

#There is no return value for RP1210_ReadVersion
RP1210_ReadVersion(byref(DLLMajorVersion),
                   byref(DLLMinorVersion),
                   byref(APIMajorVersion),
                   byref(APIMinorVersion))
print('Successfully Read DLL and API Versions.')
DLLMajor = DLLMajorVersion.value.decode('ascii','ignore')
DLLMinor = DLLMinorVersion.value.decode('ascii','ignore')
APIMajor = APIMajorVersion.value.decode('ascii','ignore')
APIMinor = APIMinorVersion.value.decode('ascii','ignore')
print("DLL Version: {}.{}".format(DLLMajor,DLLMinor))
print("API Version: {}.{}".format(APIMajor,APIMinor))


# Assignnment: 
#  Make a function prototype for RP1210_ClientDisconnect
#  Make a function prototype for RP1210_ReadDetailedVersion
#  Display the RP1210_ReadDetailedVersion information when 
#  connected to an RP1210 device (VDA). The VDA will need
#  12V power.  
