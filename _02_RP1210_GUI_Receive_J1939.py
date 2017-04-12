import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from   ctypes import *
from   ctypes.wintypes import HWND
import threading
import queue
import time


class RP1210ReadMessageThread(threading.Thread):
    def __init__(self, parent, rx_queue, RP1210_ReadMessage,nClientID ):
        self.root = parent
        threading.Thread.__init__(self)
        self.rx_queue = rx_queue
        self.ReadMessage = RP1210_ReadMessage
        
        self.nClientID = nClientID
        
    def run(self):
        ucTxRxBuffer = (c_char*2000)()
        NON_BLOCKING_IO = 0
        print(self.ReadMessage)
        print(self.nClientID)
        
        while True:
            nRetVal = self.ReadMessage( c_short( self.nClientID ), byref( ucTxRxBuffer ), c_short( 2000 ), c_short( NON_BLOCKING_IO ) )
            if nRetVal > 0:
                #print(ucTxRxBuffer[:nRetVal])
                self.rx_queue.put(ucTxRxBuffer[:nRetVal])
            time.sleep(.001)
            

class RP1210(tk.Frame):
    """The SSS2 gui and functions."""
    def __init__(self, parent):
        self.main_frame = tk.Frame.__init__(self, parent)
        self.root = parent
        self.root.geometry('+100+100')
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

        # Set all filters to pass.  This allows messages to be read.
        RP1210_Set_All_Filters_States_to_Pass = 3 
        nRetVal = self.SendCommand( c_short( RP1210_Set_All_Filters_States_to_Pass ), c_short( self.nClientID ), None, 0 )

        if nRetVal == 0 :
           print("RP1210_Set_All_Filters_States_to_Pass - SUCCESS" )
        else :
           print('RP1210_Set_All_Filters_States_to_Pass returns %i' %nRetVal )
   
    def init_gui(self):
        """Builds GUI."""
        #Set up a button. Some documentation is http://effbot.org/tkinterbook/button.htm
        version_button = tk.Button(self, text="Display Version", command=self.display_version)
        version_button.grid(row=0,column=0,padx=10,pady=2, sticky=tk.W+tk.E) #The sticky parameters fill the column.

        detailed_version_button = tk.Button(self, text="Get Detailed Version", command=self.display_detailed_version)
        detailed_version_button.grid(row=1,column=0,padx=10,pady=2, sticky=tk.W+tk.E)


        #Add a thread to listen to messages
        self.rx_queue = queue.Queue()
        self.read_message_thread = RP1210ReadMessageThread(self,self.rx_queue,self.ReadMessage,self.nClientID)
        self.read_message_thread.start()
        print("Started RP1210ReadMessage Thread.")

        #Add a Text Box to display the data. See http://www.tkdocs.com/tutorial/tree.html
        #also https://docs.python.org/3/library/tkinter.ttk.html
        self.recieved_j1939_message_tree = ttk.Treeview(self.main_frame, height=20)
        self.recieved_j1939_message_tree.grid(row=0,column=1,rowspan=2,sticky=tk.W+tk.E+tk.N+tk.S)
        self.recieved_j1939_message_tree.column("#0",stretch=True, minwidth=500,width=500, anchor='w') 
        self.recieved_j1939_message_tree.heading("#0",text="Hex Values",anchor='w') 

        #Assignment: Add the followng columns to the tree view: 'Timestamp','PGN','HOW/Priority', 'SA','DA','data'
        #self.recieved_j1939_message_tree.column('Timestamp', width=130, anchor='w')
        #self.recieved_j1939_message_tree.heading('Timestamp', text='Timestamp')

        #Add a checkbutton to start and stop scrolling
        #See http://effbot.org/tkinterbook/checkbutton.htm
        self.scroll_j1939_message_button =  ttk.Checkbutton(self.main_frame, text="Auto Scroll Message Window")
        self.scroll_j1939_message_button.grid(row=3,column=1,sticky='NW')
        self.scroll_j1939_message_button.state(['!alternate']) #Clears Check Box
        self.scroll_j1939_message_button.state(['selected']) #selects Check Box
        
        self.rx_index = 0
        self.message_tree_ids=[]
        self.fill_tree()
        
    def fill_tree(self):
        while self.rx_queue.qsize():
            
            
            message_text = ""
            rxmessage = self.rx_queue.get()

            for b in rxmessage:
                message_text+="{:02X} ".format(b)
            self.message_tree_ids.insert(self.rx_index, self.recieved_j1939_message_tree.insert('','end',text=message_text))

            
                
            if self.rx_index > 10:
                self.recieved_j1939_message_tree.delete(self.message_tree_ids[self.rx_index-10])
                self.rx_index = 0
            
            if self.scroll_j1939_message_button.instate(['selected']):
               self.recieved_j1939_message_tree.see(self.message_tree_ids[self.rx_index])

            self.rx_index+=1
           

           
        self.after(10, self.fill_tree)

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
        
