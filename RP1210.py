from PyQt5.QtWidgets import (QMessageBox,
                             QInputDialog)

# Use ctypes to import the RP1210 DLL
from ctypes import *
from ctypes.wintypes import HWND

from PyQt5.QtCore import Qt, QCoreApplication

import json
from TU_RP1210functions import *

import traceback
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s, %(levelname)s, in %(funcName)s, %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S.')
#file_handler = logging.FileHandler('RP1210 ' + start_time + '.log',mode='w')
file_handler = logging.FileHandler('TruckCRYPT.log',mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler()
logger.addHandler(stream_handler)

class RP1210Class():
    """A class to access RP1210 libraries for different devices."""
    def __init__(self,dll_name):
        #Load the Windows Device Library
        self.nClientID = None
        self.ucTxRxBuffer = (c_char*2000)()
        self.create_RP1210_functions(dll_name)

    def create_RP1210_functions(self,dll_name):
        self.ClientConnect = None
        self.ClientDisconnect = None
        self.SendMessage = None
        self.ReadMessage = None
        self.SendCommand = None
        self.ReadVersion = None
        self.ReadDetailedVersion = None
        self.GetHardwareStatus = None
        self.GetErrorMsg = None
        self.GetHardwareStatusEx = None
        self.GetLastErrorMsg = None
        
        self.dll_name = dll_name

        if dll_name is not None:
            logger.debug("Loading the {} file.".format(dll_name + ".dll"))
            try:
                RP1210DLL = windll.LoadLibrary(dll_name + ".dll")
            except Exception as e:
                logger.debug(traceback.format_exc())
                logger.info("\nIf RP1210 DLL fails to load, please check to be sure you are using"
                    + "a 32-bit version of Python and you have the correct drivers for the VDA installed.")
                return None

            # Define windows prototype functions:
            try:
                prototype = WINFUNCTYPE(c_short, HWND, c_short, c_char_p, c_long, c_long, c_short)
                self.ClientConnect = prototype(("RP1210_ClientConnect", RP1210DLL))

                prototype = WINFUNCTYPE(c_short, c_short)
                self.ClientDisconnect = prototype(("RP1210_ClientDisconnect", RP1210DLL))

                prototype = WINFUNCTYPE(c_short, c_short,  POINTER(c_char*2000), c_short, c_short, c_short)
                self.SendMessage = prototype(("RP1210_SendMessage", RP1210DLL))

                prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*2000), c_short, c_short)
                self.ReadMessage = prototype(("RP1210_ReadMessage", RP1210DLL))

                prototype = WINFUNCTYPE(c_short, c_short, c_short, POINTER(c_char*2000), c_short)
                self.SendCommand = prototype(("RP1210_SendCommand", RP1210DLL))
            except Exception as e:
                logger.debug(traceback.format_exc())
                logger.debug("\n Critical RP1210 functions were not able to be loaded. There is something wrong with the DLL file.")
                return None

            try:
                prototype = WINFUNCTYPE(c_short, c_char_p, c_char_p, c_char_p, c_char_p)
                self.ReadVersion = prototype(("RP1210_ReadVersion", RP1210DLL))
            except Exception as e:
                logger.exception(e)

            try:
                prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*17), POINTER(c_char*17), POINTER(c_char*17))
                self.ReadDetailedVersion = prototype(("RP1210_ReadDetailedVersion", RP1210DLL))
            except Exception as e:
                logger.debug(traceback.format_exc())
                self.ReadDetailedVersion = None

            try:
                prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*64), c_short, c_short)
                self.GetHardwareStatus = prototype(("RP1210_GetHardwareStatus", RP1210DLL))
            except Exception as e:
                logger.debug(traceback.format_exc())

            try:
                prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*256))
                self.GetHardwareStatusEx = prototype(("RP1210_GetHardwareStatusEx", RP1210DLL))
            except Exception as e:
                logger.debug(traceback.format_exc())
                
            try:
                prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_char*80))
                self.GetErrorMsg = prototype(("RP1210_GetErrorMsg", RP1210DLL))
            except Exception as e:
                logger.debug(traceback.format_exc())

            try:
                prototype = WINFUNCTYPE(c_short, c_short, POINTER(c_int), POINTER(c_char*80), c_short)
                self.GetLastErrorMsg = prototype(("RP1210_GetLastErrorMsg", RP1210DLL))
            except Exception as e:
                logger.debug(traceback.format_exc())
        else:
            logger.warning("DLL file was None.")

    def get_client_id(self, protocol, deviceID, speed):
        QCoreApplication.processEvents()
        nClientID = None
        if len(speed) > 0 and (protocol == "J1939"  or protocol == "CAN" or protocol == "ISO15765"):
            protocol_bytes = bytes(protocol + ":Baud={}".format(speed),'ascii')
        else:
            protocol_bytes = bytes(protocol,'ascii')
        logger.debug("Connecting with ClientConnect using " + repr(protocol_bytes))
        try:
            nClientID = self.ClientConnect(HWND(None), c_short(deviceID), protocol_bytes, 0, 0, 0)
            logger.debug("The Client ID is: {}, which means {}".format(nClientID, self.get_error_code(nClientID)))
            
        except Exception as e:
            logger.warning("Client Connect did not work.")
            logger.debug(traceback.format_exc())
        
        if nClientID is None:
            logger.debug("An RP1210 device is not connected properly.")
            return None
        elif nClientID < 128:
            file_contents = {nClientID:{"dll_name":self.dll_name,
                                             "protocol":protocol,
                                             "deviceID":deviceID,
                                             "speed":speed}
                                            }
            with open("Last_RP1210_Connection.json","w") as rp1210_file:
                json.dump(file_contents, rp1210_file, sort_keys=True, indent = 4)


            return nClientID
        else:
            return None

    def display_version(self):

        message_window = QMessageBox()
        message_window.setIcon(QMessageBox.Information)
        message_window.setWindowTitle('RP1210 Version Information')
        message_window.setStandardButtons(QMessageBox.Ok)

        if self.ReadVersion is None:
            message_window.setText("RP1210_ReadVersion() function is not available.")
            logger.debug("RP1210_ReadVersion() is not supported.")
        else:
            chDLLMajorVersion    = (c_char)()
            chDLLMinorVersion    = (c_char)()
            chAPIMajorVersion    = (c_char)()
            chAPIMinorVersion    = (c_char)()

            #There is no return value for RP1210_ReadVersion
            self.ReadVersion(byref(chDLLMajorVersion),
                                    byref(chDLLMinorVersion),
                                    byref(chAPIMajorVersion),
                                    byref(chAPIMinorVersion))
            logger.debug('Successfully Read DLL and API Versions.')
            DLLMajor = chDLLMajorVersion.value.decode('ascii','ignore')
            DLLMinor = chDLLMinorVersion.value.decode('ascii','ignore')
            APIMajor = chAPIMajorVersion.value.decode('ascii','ignore')
            APIMinor = chAPIMinorVersion.value.decode('ascii','ignore')
            logger.debug("DLL Major Version: {}".format(DLLMajor))
            logger.debug("DLL Minor Version: {}".format(DLLMinor))
            logger.debug("API Major Version: {}".format(APIMajor))
            logger.debug("API Minor Version: {}".format(APIMinor))
            message_window.setText("Driver software versions are as follows:\nDLL Major Version: {}\nDLL Minor Version: {}\nAPI Major Version: {}\nAPI Minor Version: {}".format(DLLMajor,DLLMinor,APIMajor,APIMinor))
        message_window.exec_()
    
    def get_hardware_status_ex(self,nClientID=1):
        message_window = QMessageBox()
        message_window.setIcon(QMessageBox.Information)
        message_window.setWindowTitle('RP1210 Extended Hardware Status')
        message_window.setStandardButtons(QMessageBox.Ok)

        if self.GetHardwareStatusEx is None:
            message = "RP1210_GetHardwareStatusEx() function is not available."
        else:
            fpchClientInfo = (c_char*256)()
            return_value = self.GetHardwareStatusEx(c_short(nClientID),
                                                         byref(fpchClientInfo))
            if return_value == 0:
                message = ""
                status_bytes = fpchClientInfo.raw
                logger.debug(status_bytes)

                hw_device_located = (status_bytes[0] & 0x01) >> 0
                if hw_device_located:
                    message += "The hardware device was located and it is ready.\n"
                else:
                    message += "The hardware device was not located.\n"

                hw_device_internal = (status_bytes[0] & 0x02) >> 1
                if hw_device_internal:
                    message += "The hardware device is an internal device, non-wireless.\n"
                else:
                    message += "The hardware device is not an internal device, non-wireless.\n"

                hw_device_external = (status_bytes[0] & 0x04) >> 2
                if hw_device_external:
                    message += "The hardware device is an external device, non-wireless.\n"
                else:
                    message += "The hardware device is not an external device, non-wireless.\n"

                hw_device_internal = (status_bytes[0] & 0x08) >> 3
                if hw_device_internal:
                    message += "The hardware device is an internal device, wireless.\n"
                else:
                    message += "The hardware device is not an internal device, wireless.\n"

                hw_device_external = (status_bytes[0] & 0x10) >> 4
                if hw_device_external:
                    message += "The hardware device is an external device, wireless.\n"
                else:
                    message += "The hardware device is not an external device, wireless.\n"

                auto_baud = (status_bytes[0] & 0x20) >> 5
                if auto_baud:
                    message += "The hardware device CAN auto-baud capable.\n"
                else:
                    message += "The hardware device is not CAN auto-baud capable.\n"

                number_of_clients = status_bytes[1]
                message += "The number of connected clients is {}.\n\n".format(number_of_clients)

                number_of_can = status_bytes[1]
                message += "The number of simultaneous CAN channels is {}.\n\n".format(number_of_can)

                message += "There may be more information available than what is currently shown."
            else:
                message = "RP1210_GetHardwareStatusEx failed with a return value of  {}: {}".format(return_value,self.get_error_code(return_value))

        logger.debug(message)
        message_window.setText(message)
        message_window.exec_()

    def get_hardware_status(self,nClientID=1):
        message_window = QMessageBox()
        message_window.setIcon(QMessageBox.Information)
        message_window.setWindowTitle('RP1210 Hardware Status')
        message_window.setStandardButtons(QMessageBox.Ok)

        if self.GetHardwareStatus is None:
            message = "RP1210_GetHardwareStatus() function is not available."
        else:
            fpchClientInfo = (c_char*64)()
            nInfoSize = 64
            return_value = self.GetHardwareStatus(c_short(nClientID),
                                                         byref(fpchClientInfo),
                                                         c_short(nInfoSize),
                                                         c_short(0))
            if return_value == 0 :
                message = ""
                status_bytes = fpchClientInfo.raw
                logger.debug(status_bytes)


                hw_device_located = (status_bytes[0] & 0x01) >> 0
                if hw_device_located:
                    message += "The hardware device was located.\n"
                else:
                    message += "The hardware device was not located.\n"

                hw_device_internal = (status_bytes[0] & 0x02) >> 1
                if hw_device_internal:
                    message += "The hardware device is an internal device.\n"
                else:
                    message += "The hardware device is not an internal device.\n"

                hw_device_external = (status_bytes[0] & 0x04) >> 2
                if hw_device_external:
                    message += "The hardware device is an external device.\n"
                else:
                    message += "The hardware device is not an external device.\n"

                number_of_clients = status_bytes[1]
                message += "The number of connected clients is {}.\n\n".format(number_of_clients)

                j1939_active = (status_bytes[2] & 0x01) >> 0
                if j1939_active:
                    message += "The J1939 link is activated.\n"
                else:
                    message += "The J1939 link is not activated.\n"

                traffic_detected = (status_bytes[2] & 0x02) >> 1
                if traffic_detected:
                    message += "J1939 network traffic was detected in the last second.\n"
                else:
                    message += "J1939 network traffic was not detected in the last second.\n"

                bus_off = (status_bytes[2] & 0x04) >> 2
                if bus_off:
                    message += "The CAN controller reports a BUS_OFF status.\n"
                else:
                    message += "The CAN controller does not report a BUS_OFF status.\n"
                number_of_clients = status_bytes[3]
                message += "The number of clients connected to J1939 is {}.\n\n".format(number_of_clients)


                j1708_active = (status_bytes[4] & 0x01) >> 0
                if j1708_active:
                    message += "The J1708 link is activated.\n"
                else:
                    message += "The J1708 link is not activated.\n"

                traffic_detected = (status_bytes[4] & 0x02) >> 1
                if traffic_detected:
                    message += "J1708 network traffic was detected in the last second.\n"
                else:
                    message += "J1708 network traffic was not detected in the last second.\n"

                number_of_clients = status_bytes[5]
                message += "The number of clients connected to J1708 is {}.\n\n".format(number_of_clients)

                can_active = (status_bytes[6] & 0x01) >> 0
                if can_active:
                    message += "The CAN link is activated.\n"
                else:
                    message += "The CAN link is not activated.\n"

                traffic_detected = (status_bytes[6] & 0x02) >> 1
                if traffic_detected:
                    message += "CAN network traffic was detected in the last second.\n"
                else:
                    message += "CAN network traffic was not detected in the last second.\n"

                bus_off = (status_bytes[6] & 0x04) >> 2
                if bus_off:
                    message += "The CAN controller reports a BUS_OFF status.\n"
                else:
                    message += "The CAN controller does not report a BUS_OFF status.\n"
                number_of_clients = status_bytes[7]
                message += "The number of clients connected to CAN is {}.\n\n".format(number_of_clients)

                j1850_active = (status_bytes[8] & 0x01) >> 0
                if j1850_active:
                    message += "The J1850 link is activated.\n"
                else:
                    message += "The J1850 link is not activated.\n"

                traffic_detected = (status_bytes[8] & 0x02) >> 1
                if traffic_detected:
                    message += "J1850 network traffic was detected in the last second.\n"
                else:
                    message += "J1850 network traffic was not detected in the last second.\n"

                number_of_clients = status_bytes[9]
                message += "The number of clients connected to J1850 is {}.\n\n".format(number_of_clients)

                iso_active = (status_bytes[16] & 0x01) >> 0
                if iso_active:
                    message += "The ISO15765 link is activated.\n"
                else:
                    message += "The ISO15765 link is not activated.\n"

                traffic_detected = (status_bytes[16] & 0x02) >> 1
                if traffic_detected:
                    message += "ISO15765 network traffic was detected in the last second.\n"
                else:
                    message += "ISO15765 network traffic was not detected in the last second.\n"

                bus_off = (status_bytes[16] & 0x04) >> 2
                if bus_off:
                    message += "The CAN controller reports a BUS_OFF status.\n"
                else:
                    message += "The CAN controller does not report a BUS_OFF status.\n"
                number_of_clients = status_bytes[17]
                message += "The number of clients connected to ISO15765 is {}.\n\n".format(number_of_clients)

            else:
                message = "RP1210_GetHardwareStatus failed with a return value of  {}: {}".format(return_value,self.get_error_code(return_value))
        logger.debug(message)
        message_window.setText(message)
        message_window.exec_()
    
    def get_hardware_status_data(self,nClientID):
        vda = False
        can = False
        j1939 = False
        j1708 = False
        iso = False

        if self.GetHardwareStatus is not None:
            fpchClientInfo = (c_char*64)()
            nInfoSize = 16
            logger.debug("calling GetHardwareStatus")
            return_value = self.GetHardwareStatus(c_short(nClientID),
                                                         byref(fpchClientInfo),
                                                         c_short(nInfoSize),
                                                         c_short(0))
            if return_value == 0:
                vda = True
                status_bytes = fpchClientInfo.raw
                
                traffic_detected = (status_bytes[2] & 0x02) >> 1 #J1708
                if traffic_detected:
                    j1939 = True
                else:
                    j1939 = False

                traffic_detected = (status_bytes[4] & 0x02) >> 1 #J1708
                if traffic_detected:
                    j1708 = True
                else:
                    j1708 = False

                traffic_detected = (status_bytes[6] & 0x02) >> 1 #CAN
                if traffic_detected:
                    can = True
                else:
                    can = False

                traffic_detected = (status_bytes[16] & 0x02) >> 1 #ISO
                if traffic_detected:
                    iso = True
                else:
                    iso = False

        return vda,can,j1939,j1708,iso



    def get_error_code(self,code):
        # Make sure the function prototype is available:
        if self.GetErrorMsg is not None:
            #make sure the error code is an integer
            try:
                code = int(code)
            except Exception as e:
                logger.warning(e)
                code = -1
            # Set up the decription buffer
            fpchDescription = (c_char*80)()
            return_value = self.GetErrorMsg(c_short(code), byref(fpchDescription))
            description = fpchDescription.value.decode('ascii','ignore')

            if return_value == 0:
               return description
        return "Error code interpretation not available."

    def display_detailed_version(self,nClientID):
        message_window = QMessageBox()
        message_window.setIcon(QMessageBox.Information)
        message_window.setWindowTitle('RP1210 Detailed Version')
        message_window.setStandardButtons(QMessageBox.Ok)

        if self.ReadDetailedVersion is None:
            message = "RP1210_ReadDetailedVersion() function is not available."
        else:
            chAPIVersionInfo    = (c_char*17)()
            chDLLVersionInfo    = (c_char*17)()
            chFWVersionInfo     = (c_char*17)()
            return_value = self.ReadDetailedVersion(c_short(nClientID),
                                                        byref(chAPIVersionInfo),
                                                        byref(chDLLVersionInfo),
                                                        byref(chFWVersionInfo))
            if return_value == 0 :
                message = 'The PC computer has successfully connected to the RP1210 Device.\nThere is no need to check your USB connection.\n'
                DLL = chDLLVersionInfo.value
                API = chAPIVersionInfo.value
                FW = chAPIVersionInfo.value
                message += "DLL = {}\n".format(DLL.decode('ascii','ignore'))
                message += "API = {}\n".format(API.decode('ascii','ignore'))
                message += "FW  = {}".format(FW.decode('ascii','ignore'))
            else:
                message = "RP1210_ReadDetailedVersion failed with\na return value of  {}: {}".format(return_value,self.get_error_code(return_value))
        message_window.setText(message)
        message_window.exec_()

    def send_message(self, client_id, message_bytes):
        msg_len = len(message_bytes)
        #logger.debug("Sending the following bytes on Client {}: ".format(client_id) 
        #    + bytes_to_hex_string(message_bytes))
        for i in range(msg_len):
            self.ucTxRxBuffer[i] = message_bytes[i]

        try:
            return_value = self.SendMessage(c_short(client_id),
                                        byref(self.ucTxRxBuffer),
                                        c_short(msg_len), 0, 0)
            if return_value != 0:
                    message = "RP1210_SendMessage failed with a return value of  {}: {}".format(return_value,self.RP1210.get_error_code(return_value))
                    logger.warning(message)
        except Exception as e:
            logger.debug(repr(e))


    def send_command(self,command_num,client_id,message_bytes):
        msg_len = len(message_bytes)
        fpchClientCommand = (c_char*2000)()
        for i in range(msg_len):
            fpchClientCommand[i] = message_bytes[i]

        return_value = self.SendCommand(c_short(command_num),
                                        c_short(client_id),
                                        byref(fpchClientCommand),
                                        c_short(msg_len))
        if return_value != 0:
                message = "RP1210_SendCommand {} failed with a return value of  {}: {}".format(command_num,return_value,self.get_error_code(return_value))
                logger.warning(message)
        return return_value
        
    def get_last_error_msg(self,nClientID):

        nErrorCode, ok = QInputDialog.getInt(self, 'Last Error Code','Enter Error Code:',value = -1,min = 0,max=255)

        message_window = QMessageBox()
        message_window.setIcon(QMessageBox.Information)
        message_window.setWindowTitle('RP1210 Get Last Error Message')
        message_window.setStandardButtons(QMessageBox.Ok)
        # Make sure the function prototype is available:
        if self.GetLastErrorMsg is not None and nClientID is not None:
            fpchDescription = (c_char*80)()
            nSubErrorCode = (c_int)()
            return_value = self.GetLastErrorMsg(c_short(nErrorCode),
                                                       byref(nSubErrorCode),
                                                       byref(fpchDescription),
                                                       c_short(nclientID))
            description = fpchDescription.value.decode('ascii','ignore')
            sub_error = nSubErrorCode.value
            if return_value == 0 :
                message = "Client ID is {}.\nError Code {} means {}".format(clientID, nErrorCode, description)
                if sub_error < 0:
                    message_window.setInformativeText("No subordinate error code is available.")
                else:
                    message_window.setInformativeText("Additional Code: {}".format(sub_error))
            else:
                message = "RP1210_GetLastErrorMsg failed with\na return value of  {}: {}".format(return_value,self.get_error_code(return_value))
        else:
            message = "RP1210_GetLastErrorMsg() function is not available."

        logger.debug(message)
        message_window.setText(message)
        message_window.exec_()

