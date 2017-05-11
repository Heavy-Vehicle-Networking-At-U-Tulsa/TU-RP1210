import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from   ctypes import *
from   ctypes.wintypes import HWND
import threading
import queue
import time
import collections
import configparser
import struct


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
            
class setup_RP1210_connections(tk.Toplevel):
    def __init__(self, parent):
        tk.Toplevel.__init__(self, parent)
        self.transient(parent)
        self.title("Select RP1210 Device")
        self.parent = parent
        self.result = None

        self.select_RP1210_frame = tk.Frame(self)
        self.buttonbox()
        self.select_RP1210_frame.pack(padx=5, pady=5)
        
        self.protocol("WM_DELETE_WINDOW", self.cancel)

        self.geometry("+%d+%d" % (parent.winfo_rootx()+150,
                                  parent.winfo_rooty()+150))
       
        self.grab_set()
        self.focus_set()
        self.wait_window(self)

    
    def buttonbox(self):
        self.connect_button = tk.Button(self.select_RP1210_frame, name='connect_button',
                                   text="Connect", width=10, command=self.ok, default=tk.ACTIVE)
        self.connect_button.grid(row=3,column=0, padx=5, pady=5)
        cancel_button = tk.Button(self.select_RP1210_frame, text="Cancel", width=10, command=self.cancel)
        cancel_button.grid(row=3,column=1, padx=5, pady=5)
        
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        self.connect_button.focus()
        
        tk.Label(self.select_RP1210_frame,text="RP1210 DLL").grid(row=0,column=0,columnspan=2)
        self.port_combo_box = ttk.Combobox(self.select_RP1210_frame,text="RP1210 Vendor")
        self.port_combo_box.grid(row=1,column=0,columnspan=2)
        self.populate_combo_box()
        
    
    def populate_combo_box(self):
        RP1210_config = configparser.ConfigParser()
        RP1210_config.read("C:\\Windows\\RP121032.ini")
        
        menubar = tk.Menu(self)
        self.rp1210menu = tk.Menu(menubar, tearoff=0)
        i=0
        self.RP1210_APIs = RP1210_config['RP1210Support']['APIImplementations'].split(',')
        self.port_combo_box_values=[]
        for API in self.RP1210_APIs:
            # create a pulldown menu, and add it to the menu bar
            if API is not '':
                print(API)
                api_config = configparser.ConfigParser()
                api_config.read("C:\\Windows\\"+API+".ini")
                for iniEntry in api_config:
                    print(iniEntry)
                self.port_combo_box_values.append(API)
        
        self.port_combo_box['values']=self.port_combo_box_values
        self.port_combo_box.current(0)
        
    def ok(self, event=None):

        if not self.validate():
            self.focus_set() 
            return

        self.withdraw()
        self.update_idletasks()

        self.apply() #usually this is in the OK function

        
    def cancel(self, event=None):
        
        # put focus back to the parent window
        self.result = (None,None,None)
        self.parent.focus_set()
        self.destroy()
        

    #
    # command hooks

    def validate(self):
        if self.port_combo_box.get() in self.RP1210_APIs:
            return True
        else:
            print("Selection not part of the RP121032.ini file.")
    
    def apply(self):
        dll = self.port_combo_box.get() + ".DLL"
        protocol = "J1939"
        idname = 1
        self.result = (dll,protocol,idname)
        self.parent.focus_set()
        self.destroy()


class RP1210(tk.Frame):
    """The RP1210 gui and functions."""
    def __init__(self, parent):
        self.main_frame = tk.Frame.__init__(self, parent)
        self.root = parent
        self.root.geometry('+100+100')
        self.root.title('RP1210 Interface')
        self.grid( column=0, row=0, sticky='NSEW') #needed to display

        self.rx_message_list = []
        self.dllName = None#"DPA4PMA.DLL"
        self.protocol = "J1939:Channel=1"
        self.deviceID = 1
        self.init_gui()
        self.setupRP1210()
        
        
    
    def select_RP1210_dialog(self):
        connection_dialog = setup_RP1210_connections(self)
        (self.dllName, self.protocol, self.deviceID) = connection_dialog.result
        print("Connecting with {} using protocol: {} and a deviceID of {}.".format(self.dllName,
                                                                                    self.protocol,
                                                                                    self.deviceID))
        if self.dllName is not None: #avoid loop
            self.setupRP1210()
            self.run_program()
            
        
    def setupRP1210(self):

        if self.dllName is None:
            self.select_RP1210_dialog()
        else:
            #Load the Windows Device Library
            RP1210DLL = windll.LoadLibrary( self.dllName )
                    
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

            print( "Attempting connect to DLL [%s], DeviceID [%d]" %( self.dllName, self.deviceID ) )

            self.szProtocolName = bytes(self.protocol,'ascii')
            self.nClientID = self.ClientConnect( HWND(None), c_short( self.deviceID ), self.szProtocolName, 0, 0, 0  )

            # Set all filters to pass.  This allows messages to be read.
            RP1210_Set_All_Filters_States_to_Pass = 3 
            nRetVal = self.SendCommand( c_short( RP1210_Set_All_Filters_States_to_Pass ), c_short( self.nClientID ), None, 0 )

            if nRetVal == 0 :
               print("RP1210_Set_All_Filters_States_to_Pass - SUCCESS" )
            else :
               print('RP1210_Set_All_Filters_States_to_Pass returns %i' %nRetVal )

            
       
    def init_gui(self):
        """Builds GUI."""

        #Add a menu to select RP1210 device
        self.root.option_add('*tearOff', 'FALSE')
        self.menubar = tk.Menu(self.root,name='main_menus')
 
        self.menu_connection = tk.Menu(self.menubar)
        self.menu_connection.add_command(label='Select RP1210 Device',
                                         command=self.select_RP1210_dialog)

        self.menubar.add_cascade(menu=self.menu_connection, label='RP1210')
        self.root.config(menu=self.menubar)

        #Set up a button. Some documentation is http://effbot.org/tkinterbook/button.htm
        version_button = tk.Button(self, text="Save Log", command=self.save_log_file)
        version_button.grid(row=0,column=0,padx=10,pady=2, sticky=tk.W+tk.E) #The sticky parameters fill the column.

        detailed_version_button = tk.Button(self, text="Get Detailed Version", command=self.display_detailed_version)
        detailed_version_button.grid(row=1,column=0,padx=10,pady=2, sticky=tk.W+tk.E)

        rp1210_button = tk.Button(self, text="Select RP1210 Adapter", command=self.select_RP1210_dialog)
        rp1210_button.grid(row=2,column=0,padx=10,pady=2, sticky=tk.W+tk.E)

        rp1210_button = tk.Button(self, text="Destroy and Terminate", command=self.on_closing)
        rp1210_button.grid(row=3,column=0,padx=10,pady=2, sticky=tk.W+tk.E)

        #Add a Text Box to display the data. See http://www.tkdocs.com/tutorial/tree.html
        #also https://docs.python.org/3/library/tkinter.ttk.html
        self.tree_columns = ["period", "DA", "SA", "Pri", "Data"]
        self.tree_column_widths = [50, 50, 50, 50, 300]
        
        self.recieved_j1939_message_tree = ttk.Treeview(self.main_frame, height=20, columns=self.tree_columns)
        self.recieved_j1939_message_tree.grid(row=0,column=1,rowspan=2,sticky=tk.W+tk.E+tk.N+tk.S)
        self.recieved_j1939_message_tree.column("#0",stretch=True, minwidth=50,width=150, anchor='w') 
        self.recieved_j1939_message_tree.heading("#0",text="PGN Hex",anchor='w')
        for col,col_width in zip(self.tree_columns,self.tree_column_widths):
            self.recieved_j1939_message_tree.column(col,stretch=True, minwidth=50, width=col_width, anchor='w') 
            self.recieved_j1939_message_tree.heading(col,text=col,anchor='w')
            

        #Assignment: Add the followng columns to the tree view: 'Timestamp','PGN','HOW/Priority', 'SA','DA','data'
        #self.recieved_j1939_message_tree.column('Timestamp', width=130, anchor='w')
        #self.recieved_j1939_message_tree.heading('Timestamp', text='Timestamp')

        #Add a checkbutton to start and stop scrolling
        #See http://effbot.org/tkinterbook/checkbutton.htm
        self.scroll_j1939_message_button =  ttk.Checkbutton(self.main_frame, text="Auto Scroll Message Window")
        self.scroll_j1939_message_button.grid(row=3,column=1,sticky='NW')
        self.scroll_j1939_message_button.state(['!alternate']) #Clears Check Box
        self.scroll_j1939_message_button.state(['selected']) #selects Check Box

    def run_program(self):
        #Add a thread to listen to messages
        self.rx_queue = queue.Queue()
        self.read_message_thread = RP1210ReadMessageThread(self,self.rx_queue,self.ReadMessage,self.nClientID)
        self.read_message_thread.daemon = True
        self.read_message_thread.start()
        print("Started RP1210ReadMessage Thread.")

        # Set up a deque to hold messages
        #https://docs.python.org/3/library/collections.html#collections.deque
        self.max_rx_messages = 10000
        self.rx_message_buffer = collections.deque(maxlen=self.max_rx_messages)
        self.max_message_tree = 10000
        self.message_tree_ids=collections.deque(maxlen=self.max_message_tree)
        self.fill_tree()

        #Assignment: Create widgets that can set the maxlen of the deque buffers
    

    def fill_tree(self):
        
        while self.rx_queue.qsize():
            
            
            rxmessage = self.rx_queue.get()
            timestamp = struct.unpack('>L',rxmessage[0:4])[0]/1000
            #print("{}".format(timestamp))
            
            timestamp_text = "{:0.3f}".format(timestamp)
            #print(rxmessage)
            pgn = rxmessage[4] + (rxmessage[5] << 8) + (rxmessage[6] << 16)
            pgn_text = "{:06X}".format(pgn)

            SA = rxmessage[8]
            #self.recieved_j1939_message_tree.insert("SA",'end',text="{}".format(SA))
            DA = rxmessage[9]
            priority = rxmessage[7]
            data_field = rxmessage[8:]
            data_text=[]
            for d in data_field:
                data_text.append("{:02X}".format(d))

            rxmessage_text = ",".join([timestamp_text,pgn_text,"{}".format(SA),"{}".format(DA),"{}".format(priority)] + data_text)
            self.rx_message_list.append(rxmessage_text+"\n")
            #print(rxmessage_text)

            selection = self.recieved_j1939_message_tree.insert('',
                                                                'end',
                                                                text=pgn_text,
                                                                values=[0,DA,SA,priority,data_field])

            self.message_tree_ids.append(selection)
            if len(self.message_tree_ids) >= self.max_message_tree: #Change this to a tkInt that updates based
                self.recieved_j1939_message_tree.delete(self.message_tree_ids.popleft())

            
        if self.scroll_j1939_message_button.instate(['selected']):
               if len(self.message_tree_ids) > 1:
                   self.recieved_j1939_message_tree.see(self.message_tree_ids[-1])
           
        self.after(20, self.fill_tree)

        #Assignment: Add a widget that will clear the tree view
        
    def save_log_file(self):
        with open("dataFile.csv","w") as data_file:
            for line in self.rx_message_list:
                data_file.write(line)

    
        

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
    def on_closing(self):
        print("Exiting program. Disconnect RP1210 Device with return value of ", end='')
        print(self.ClientDisconnect(self.nClientID))
        root.destroy()

if __name__ == '__main__':

    root = tk.Tk()
    rp1210 = RP1210(root)
    root.protocol("WM_DELETE_WINDOW", rp1210.on_closing)
    root.mainloop()
    print("Bye.")
        
