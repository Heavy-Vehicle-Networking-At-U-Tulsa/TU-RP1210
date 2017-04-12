import tkinter as tk
from tkinter import messagebox
from   ctypes import *
from   ctypes.wintypes import HWND

class RP1210(tk.Frame):
    """The SSS2 gui and functions."""
    def __init__(self, parent):
        tk.Frame.__init__(self, parent)
        self.root = parent
        self.root.geometry('640x480+100+100')
        self.root.title('RP1210 Interface')
        self.grid( column=0, row=0, sticky='NSEW') #needed to display

        #See the entries in C:\Windows\RP121032.ini for options to use in the dllName (we'll parse this ini file later)  
        self.setupRP1210("DPA4PMA.DLL" )
        self.init_gui()

    def setupRP1210(self,dllName,protocol = "J1939:Channel=1",deviceID = 1):

        #Load the Windows Device Library
        RP1210DLL = windll.LoadLibrary( dllName )
                
        # Define windows prototype functions:
        # typedef short (WINAPI *fxRP1210_ClientConnect)       ( HWND, short, char *, long, long, short );
        prototype                   = WINFUNCTYPE( c_short, HWND, c_short, c_char_p, c_long, c_long, c_short)
        self.ClientConnect        = prototype( ( "RP1210_ClientConnect", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_ClientDisconnect)    ( short                                  );
        prototype                   = WINFUNCTYPE( c_short, c_short )
        self.ClientDisconnect     = prototype( ( "RP1210_ClientDisconnect", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_SendMessage)         ( short, char*, short, short, short      );
        prototype                   = WINFUNCTYPE( c_short, c_short,  POINTER( c_char*2000 ), c_short, c_short, c_short      )
        self.SendMessage          = prototype( ("RP1210_SendMessage", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_ReadMessage)         ( short, char*, short, short             );
        prototype                   = WINFUNCTYPE( c_short, c_short, POINTER( c_char*2000 ), c_short, c_short             )
        self.ReadMessage          = prototype( ("RP1210_ReadMessage", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_SendCommand)         ( short, short, char*, short             );
        prototype                   = WINFUNCTYPE( c_short, c_short, c_short, POINTER( c_char*2000 ), c_short             )
        self.SendCommand          = prototype( ("RP1210_SendCommand", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_ReadVersion)         ( char*, char*, char*, char*             );
        prototype                   = WINFUNCTYPE( c_short, c_char_p, c_char_p, c_char_p, c_char_p             )
        self.ReadVersion          = prototype( ("RP1210_ReadVersion", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_ReadDetailedVersion) ( short, char*, char*, char*             );
        prototype                   = WINFUNCTYPE( c_short, c_short, POINTER(c_char*17), POINTER(c_char*17), POINTER(c_char*17) )
        self.ReadDetailedVersion  = prototype( ("RP1210_ReadDetailedVersion", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_GetHardwareStatus)   ( short, char*, short, short             );
        prototype                   = WINFUNCTYPE( c_short, c_short, c_char_p, c_short, c_short             )
        self.GetHardwareStatus    = prototype( ("RP1210_GetHardwareStatus", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_GetErrorMsg)         ( short, char*                           );
        prototype                   = WINFUNCTYPE( c_short, c_short, c_char_p                           )
        self.GetErrorMsg          = prototype( ("RP1210_GetErrorMsg", RP1210DLL ) )

        # typedef short (WINAPI *fxRP1210_GetLastErrorMsg)     ( short, int *, char*, short             );
        prototype                   = WINFUNCTYPE( c_short, c_void_p, c_char_p, c_short             )
        self.GetLastErrorMsg      = prototype( ("RP1210_GetLastErrorMsg", RP1210DLL ) )

        print( "Attempting connect to DLL [%s], DeviceID [%d]" %( dllName, deviceID ) )

        self.szProtocolName = bytes(protocol,'ascii')
        self.nClientID = self.ClientConnect( HWND(None), c_short( deviceID ), self.szProtocolName, 0, 0, 0  )

        print('The Client ID is: %i' %self.nClientID )
   
    def init_gui(self):
        """Builds GUI."""
        #Set up a button. Some documentation is http://effbot.org/tkinterbook/button.htm
        version_button = tk.Button(self, text="Display Version", command=self.display_version)
        version_button.grid(row=0,column=0,padx=10,pady=2, sticky=tk.W+tk.E) #The sticky parameters fill the column.

        detailed_version_button = tk.Button(self, text="Get Detailed Version", command=self.display_detailed_version)
        detailed_version_button.grid(row=1,column=0,padx=10,pady=2, sticky=tk.W+tk.E)
        
        
    def display_version(self):
        """Brings up a dialog box that shows the version of the RP1210 device and driver. This is not a recommended function to use in RP1210D"""
        
        chDLLMajorVersion    = (c_char)()
        chDLLMinorVersion    = (c_char)()
        chAPIMajorVersion    = (c_char)()
        chAPIMinorVersion    = (c_char)()

        self.ReadVersion( byref( chDLLMajorVersion ), byref( chDLLMinorVersion ), byref( chAPIMajorVersion ), byref( chAPIMinorVersion  ) )

        print('Successfully Read DLL and API Versions.')
        DLLMajor = chDLLMajorVersion.value
        DLLMinor = chDLLMinorVersion.value
        APIMajor = chAPIMajorVersion.value
        APIMinor = chAPIMinorVersion.value
        print("DLL Major Version: {}".format(DLLMajor))
        print("DLL Minor Version: {}".format(DLLMinor))
        print("API Major Version: {}".format(APIMajor))
        print("API Minor Version: {}".format(DLLMinor))
        
        message_box_text = "".join(["Driver software versions are as follows:\n",
             "DLL Major Version: {}\n".format(DLLMajor.decode('ascii')),
             "DLL Minor Version: {}\n".format(DLLMinor.decode('ascii')),
             "API Major Version: {}\n".format(APIMajor.decode('ascii')),
             "API Minor Version: {}\n".format(DLLMinor.decode('ascii'))])
        messagebox.showinfo("RP1210 Version Information",message_box_text)
        

    def display_detailed_version(self):
        """Brings up a dialog box that shows the version of the RP1210 driver"""
        
        chAPIVersionInfo    = (c_char*17)()
        chDLLVersionInfo    = (c_char*17)()
        chFWVersionInfo     = (c_char*17)()
        nRetVal = self.ReadDetailedVersion( c_short( self.nClientID ), byref( chAPIVersionInfo ), byref( chDLLVersionInfo ), byref( chFWVersionInfo ) )

        if nRetVal == 0 :
           print('Congratulations! You have connected to a VDA! No need to check your USB connection.')
           DLL = chDLLVersionInfo.value
           API = chAPIVersionInfo.value
           FW = chAPIVersionInfo.value
           message_box_text = "".join(["Congratulations!\n",
                 "You have connected to a vehicle diagnostic adapter (VDA)!\n",
                 "No need to check your USB connection.\n", 
                 "DLL = {}\nAPI = {}\nFW  = {}".format(DLL.decode('ascii'),API.decode('ascii'),FW.decode('ascii'))])
           messagebox.showinfo("RP1210 Detailed Version Information",message_box_text)
        
        else :   
           print("ReadDetailedVersion fails with a return value of  %i" %nRetVal )
           messagebox.showerror("RP1210 Detailed Version Information","ERROR {}".format(nRetVal))
                               
           


if __name__ == '__main__':

    root = tk.Tk()
    RP1210(root)
    root.mainloop()
    try:
        root.destroy() # if mainloop quits, destroy window
    except:
        print("Bye.")
        
