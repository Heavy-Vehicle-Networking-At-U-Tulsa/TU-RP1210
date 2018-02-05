from PyQt5.QtWidgets import (QMainWindow,
                             QApplication,
                             QWidget,
                             QComboBox,
                             QLabel,
                             QDialog,
                             QDialogButtonBox,
                             QInputDialog,
                             QGridLayout,
                             QVBoxLayout,
                             QFileDialog,
                             QPushButton,
                             QGroupBox,
                             QPlainTextEdit,
                             QFormLayout,
                             QMessageBox,
                             QLineEdit)
from PyQt5.QtCore import (Qt, QCoreApplication)
from PyQt5.QtGui import QIcon, QFont, QColor, QPalette
import jwt
import pgpy
from pgpy.constants import (PubKeyAlgorithm, 
                            KeyFlags, 
                            HashAlgorithm, 
                            SymmetricKeyAlgorithm, 
                            CompressionAlgorithm, 
                            EllipticCurveOID, 
                            SignatureType)
from passlib.hash import pbkdf2_sha256 as passwd
try:
    from .RP1210Functions import *
except ImportError:
    from RP1210Functions import *
try:
    from .TU_crypt_public import *
except:
    from TU_crypt_public import *
    
import requests
import traceback
import sys
import os
import json
import time
import logging
import logging.config
# with open("logging.config.json",'r') as f:
#     logging_dictionary = json.load(f)
#logging.config.dictConfig(logging_dictionary)
logger = logging.getLogger(__name__)


class UserData(QDialog):
    def __init__(self, path_to_file = "UserData.json"):
        super(UserData, self).__init__()
        self.path_to_file = path_to_file
        self.token = None
        self.attempts = 1
        self.required_user_keys = ["Last Name",
                                  "First Name",
                                  "Title",
                                  "Company",
                                  "Address 1",
                                  "Address 2",
                                  "City",
                                  "State/Province",
                                  "Postal Code",
                                  "Country",
                                  "Phone",
                                  "E-mail",
                                  "Decoder Web Site Address",
                                  "Decoder Public Key",
                                  "Local Private Key File"]
        left_align = ["Decoder Web Site Address",
                      "Decoder Public Key",
                      "Local Private Key File"]
        self.subscription_status = {"Token Expiration":None}
        self.labels = {}
        self.inputs = {}
        self.reset_user_dict()
        for label in self.required_user_keys:
            self.labels[label] = QLabel(label+":")
            if label in left_align:
                self.labels[label].setAlignment(Qt.AlignLeft)
            else:
                self.labels[label].setAlignment(Qt.AlignRight)
            self.inputs[label] = QLineEdit()
        
        self.setup_dialog()
        self.load_file()
        self.load_private_key_contents()
        
        # After everything gets built and loaded. Connect the updater
        for label in self.required_user_keys:
            try:
                self.inputs[label].textChanged.connect(self.update_user_data)
            except AttributeError: #QComboBox is different
                self.inputs[label].currentTextChanged.connect(self.update_user_data)
        
        self.process_web_token()

    def setup_dialog(self):
        """
        Sets up the Graphical User interface for the dialog box. 
        There are 4 main areas
        """

        dialog_box = QWidget()
        dialog_box_layout = QGridLayout()

        user_data_frame = QGroupBox("User Details")
        decoding_service_frame = QGroupBox("Data Decoding Service")
        subscription_status_frame = QGroupBox("Subscription Status")
        pgp_frame = QGroupBox("Pretty Good Privacy (PGP) Setup")

        user_data_frame_layout = QFormLayout()
        user_data_frame.setLayout(user_data_frame_layout)
        
        decoding_service_frame_layout = QGridLayout()
        decoding_service_frame.setLayout(decoding_service_frame_layout)
        
        subscription_status_frame_layout = QGridLayout()
        subscription_status_frame.setLayout(subscription_status_frame_layout)
               
        pgp_frame_layout = QGridLayout()
        pgp_frame.setLayout(pgp_frame_layout)
               

        
        #self.inputs["Country"].setSizeAdjustPolicy(QComboBox.AdjustToContents)
             
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.accepted.connect(self.save_user_data)
        self.rejected.connect(self.close)
        
        # Setup inputs
        for label in ["First Name",
                      "Last Name",
                      "Title",
                      "Company",
                      "Address 1",
                      "Address 2",
                      "City",
                      "State/Province",
                      "Postal Code",
                      "Country",
                      "Phone",
                      "E-mail"]:
            user_data_frame_layout.addRow("{}:".format(label), self.inputs[label])
        user_data_frame_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        self.inputs["Decoder Web Site Address"] = QComboBox()
        sites = ["http://localhost:7774", "https://truckcrypt.synercontechnologies.com"]
        if self.user_data["Decoder Web Site Address"] in sites:
            sites.remove(self.user_data["Decoder Web Site Address"])
        sites.append(self.user_data["Decoder Web Site Address"])
        self.inputs["Decoder Web Site Address"].addItems(reversed(sites))
        self.inputs["Decoder Web Site Address"].setEditable(True)
        self.inputs["Decoder Web Site Address"].setToolTip("Enter the URL pointing to the portal to decrypt, decode, store, and verify your data package files.")
        decoding_service_frame_layout.addWidget(self.labels["Decoder Web Site Address"], 0, 0, 1, 1),
        decoding_service_frame_layout.addWidget(self.inputs["Decoder Web Site Address"], 1, 0, 1, 1)
        

        web_public_key_file_button = QPushButton("Load from File")
        web_public_key_file_button.setToolTip("Browse to the file that was sent to you when you activated your account.")
        web_public_key_file_button.clicked.connect(self.find_web_key)
        decoding_service_frame_layout.addWidget(self.labels["Decoder Public Key"],  2, 0, 1, 1),
        self.inputs["Decoder Public Key"] = QPlainTextEdit(self)
        self.inputs["Decoder Public Key"].setFont(QFont("Lucida Sans Typewriter"))
        #self.inputs["Decoder Public Key"].setFixedHeight(150)
        #self.inputs["Decoder Public Key"].setFixedWidth(480)
        
        decoding_service_frame_layout.addWidget(self.inputs["Decoder Public Key"], 3, 0, 1, 1)
        self.inputs["Decoder Public Key"].setToolTip("This file is needed so you can have encrypted and authenticated communications with the TruckCRYPT Server.")
        decoding_service_frame_layout.addWidget(web_public_key_file_button, 4, 0, 1, 1)
        
        public_key_test_button = QPushButton("Test Public Key")
        public_key_test_button.setToolTip("Encrypts and sends the phrase 'Test Message' to the server to get it decoded.")
        public_key_test_button.clicked.connect(self.send_web_key_test)
        decoding_service_frame_layout.addWidget(public_key_test_button,  5, 0, 1, 1),
        


        pgp_frame_layout.addWidget(self.labels["Local Private Key File"], 0, 0, 1, 2),
        pgp_frame_layout.addWidget(self.inputs["Local Private Key File"], 1, 0, 1, 2)
        
        self.inputs["Local Private Key File"].setToolTip("This private key is your secret. This key is used to digitally sign files that are attributed to you. You must never share this key.")
        self.inputs["Local Private Key"] = QLineEdit(self)
        self.inputs["Local Private Key"].setFont(QFont("Lucida Sans Typewriter"))
        #self.inputs["Local Private Key"].setFixedHeight(150)
        #self.inputs["Local Private Key"].setFixedWidth(480)
        
        user_private_key_file_button = QPushButton("Select Private Key File")
        user_private_key_file_button.clicked.connect(self.find_user_private_key)
        pgp_frame_layout.addWidget(user_private_key_file_button, 2, 0, 1, 1)
        
        show_private_key_contents_button = QPushButton("Show PGP Key Details")
        show_private_key_contents_button.clicked.connect(self.show_private_key_details)
        pgp_frame_layout.addWidget(show_private_key_contents_button, 2, 1, 1, 1)
        
        fingerprint_label = QLabel("\nPrivate Key Fingerprint (the actual key is a secret):")
        pgp_frame_layout.addWidget(fingerprint_label, 3, 0, 1, 2),
        pgp_frame_layout.addWidget(self.inputs["Local Private Key"], 4, 0, 1, 2)
        generate_private_key_button = QPushButton("Create New Private Key")
        generate_private_key_button.setToolTip("Generate a new Private Key file for PGP based on your User Details")
        generate_private_key_button.clicked.connect(self.generate_private_key)
        pgp_frame_layout.addWidget(generate_private_key_button, 5, 0, 1, 1)
        register_key_button = QPushButton("View/Register Public Key")
        register_key_button.setToolTip("Uploads a PGP public Key to a trusted website to establish trust.")
        register_key_button.clicked.connect(self.register_public_key)
        pgp_frame_layout.addWidget(register_key_button, 5, 1, 1, 1)
        pgp_frame_layout.setRowStretch(6,10)

        login_button = QPushButton("Login with Password")
        login_button.setToolTip("Fetches a Web Token to authorize the user application")
        login_button.clicked.connect(self.get_token)
        subscription_status_frame_layout.addWidget(login_button, 0, 0, 1, 1)

        refresh_button = QPushButton("Refresh User Token")
        refresh_button.setToolTip("Refreshes the user token expriration.")
        refresh_button.clicked.connect(self.refresh_token)
        subscription_status_frame_layout.addWidget(refresh_button, 0, 1, 1, 1)

        create_button = QPushButton("Create/Update Account")
        create_button.setToolTip("Requests to create or update an account based on the information entered in this dialog. If the e-mail exists, the information will be updated and the password will be reset.")
        create_button.clicked.connect(self.create_account)
        subscription_status_frame_layout.addWidget(create_button, 1, 0, 1, 1)
        
        reset_pwd_button = QPushButton("Reset Password")
        reset_pwd_button.setToolTip("Send a request to have a password reset link sent to the account on file.")
        reset_pwd_button.clicked.connect(self.create_account)
        subscription_status_frame_layout.addWidget(reset_pwd_button, 1, 1, 1, 1)
        

        subscription_frame = QGroupBox("Subscription Status")
        subscription_status_frame_layout.addWidget(subscription_frame, 2, 0, 1, 2)
        sub_frame_layout = QVBoxLayout()
        subscription_frame.setLayout(sub_frame_layout)

        self.subscription_status_text = QPlainTextEdit()
        self.subscription_status_text.setFixedHeight(60)
        self.subscription_status_text.setReadOnly(True)
        sub_frame_layout.addWidget(self.subscription_status_text)

        subscription_status_frame_layout.setRowStretch(2,10)

        dialog_box_layout.addWidget(user_data_frame,0,0,1,1)
        dialog_box_layout.addWidget(decoding_service_frame, 0,1,1,1)
        dialog_box_layout.addWidget(subscription_status_frame, 1,0,1,1)
        dialog_box_layout.addWidget(pgp_frame, 1,1,1,1)

        dialog_box_layout.addWidget(self.buttons, 2, 1, 1, 1)

        self.setLayout(dialog_box_layout)

        self.setWindowTitle("User and Service Information")
        self.setWindowModality(Qt.ApplicationModal) 
    
    def refresh_token(self):
        """
        Send  arequest to refresh the token
        """
        self.attempts = 1
        header_values = {'Authorization' : self.user_data["Web Token"],
                         'Requested-scope':'user' }
        url = self.user_data["Decoder Web Site Address"] 
        try:
            r = requests.get(url, headers=header_values)
            if r.status_code == 401: #
                self.get_token()
            else:
                self.user_data["Web Token"] = r.headers['new-token']
                self.process_web_token()
                disp_text = ""  
                for k,v in self.subscription_status.items():
                    disp_text += "{}: {}\n".format(k,v)
                QMessageBox.information(self,
                                        "Updated Token",
                                        "The token was updated with the following information:\n\n{}".format(disp_text)
                                        )
        except:
            logger.debug(traceback.format_exc())
            QMessageBox.warning(self,
                                "Token Failed",
                                "There was an issue refreshing the token. The server may be down. Please try again later."
                                )

    def create_account(self):
        """
        Sends a request to create an account or
        """
        if "localhost" in self.user_data["Decoder Web Site Address"]:
            try:
                with open("User Data.json",'r') as f:
                    account_data = json.load(f)
            except (FileNotFoundError,):
                account_data={}
            password, ok = QInputDialog.getText(self, 
                                        "Create Account", 
                                        "User Name:\n{}\n\nPassword:".format(self.user_data["E-mail"]), 
                                        QLineEdit.Password)

            if password and ok:
                url = self.user_data["Decoder Web Site Address"] + "/create"
                data = {"user":base64.b64encode(bytes(self.user_data["E-mail"],'utf-8')),
                        "pass":base64.b64encode(bytes(passwd.hash(password),'utf-8'))}
                try:
                    r = requests.get(url, params=data )
                    logger.debug(r.text)
                    if r.status_code == 200:
                        QMessageBox.information(self,
                                            "Success",
                                        "Stored Username, password, and expiration date to Server".format(os.getcwd())
                                       )
                except:
                    logger.debug(traceback.format_exc())
        else:
            QMessageBox.warning(self,
                                "Not Implemented",
                                "Creating accounts for external servers is not supported at this time."
                                )  
    
    def process_web_token(self):
        """
        tokens are created as follows
        token = {
                "iss":"utulsa.edu",
                "exp": time.time()+30*24*60*60,
                "iat": time.time(),
                "sub": user,
                "auth_time": time.time(),
                "email": user,
                "scope": scope}
        """
        
        p = self.subscription_status_text.palette()
        try: 
            logger.debug("Processing Web Token: {}".format(self.user_data["Web Token"]))
            token_bytes = bytes(self.user_data["Web Token"],'ascii')
            # We don't have the secret on this client. Let's just look at the contents.
            token = jwt.decode(token_bytes, 'secret', verify=False, algorithms=['HS256'])
            logger.debug("token: {}".format(token))
            self.subscription_status["Token Expiration"] = time.strftime("%d %b %Y at %H:%M:%S", time.localtime(token['exp']))
            self.subscription_status["Token Issued At"] = time.strftime("%d %b %Y at %H:%M:%S", time.localtime(token['iat']))
            self.subscription_status["Account Expiration"] = time.strftime("%d %b %Y at %H:%M:%S", time.localtime(token['sub_exp']))
            self.subscription_status["User Permissions"] = ", ".join(token['scope'])
            logger.debug(self.subscription_status)

            disp_text = ""
            for k,v in self.subscription_status.items():
                disp_text += "{}: {}\n".format(k,v)

            self.subscription_status_text.setPlainText(disp_text)
            
            if token['exp'] > time.time() and  token['iat'] < time.time():
                #Valid timeframe (user can't get a valid token by resetting the clock.)
                p.setColor(QPalette.Base, QColor('light green'))
                self.subscription_status_text.setPalette(p)
            else:
                p.setColor(QPalette.Base, QColor('yellow'))
                self.subscription_status_text.setPalette(p)
        except ValueError:
            logger.debug("Not a full token.")
            p.setColor(QPalette.Base, QColor('red'))
            self.subscription_status_text.setPalette(p)
            self.subscription_status_text.setPlainText("There was an error reading the exisiting token.")
        except:
            logger.debug(traceback.format_exc())
            self.subscription_status_text.setPlainText("There was an error reading the exisiting token.")
            p.setColor(QPalette.Base, QColor('orange'))
            self.subscription_status_text.setPalette(p)

    def get_token(self):
        """
        Refresh a token.

        """

        password, ok = QInputDialog.getText(self, 
                                        "Enter Password", 

                                        "Attempt {}\n\nUser Name:\n{}\n\nPassword:".format(self.attempts,self.user_data["E-mail"]), 
                                        QLineEdit.Password)
        if ok and password:
            try:
                user = self.user_data["E-mail"]
                url = self.user_data["Decoder Web Site Address"]
                header = {"Requested-scope":'user'}
                r = requests.get(url, auth=(user, password), headers=header )
                # Log what we get back
                logger.debug(r.status_code)
                for k,v in r.headers.items():
                    logger.debug("{}: {}".format(k,v))
                logger.debug("Response Contents: {}".format(r.text))
                if r.status_code == 401: #
                    self.attempts += 1
                    self.get_token()

            except:
                logger.debug(traceback.format_exc())
                return
            try:
                self.attempts = 1
                self.user_data["Web Token"] = r.headers['new-token']
                self.process_web_token()
                self.save_user_data()
                QMessageBox.information(self,"Updated Web Token",
                    "Successfully updated the user's web token. You do not have to login with a password again until {}".format(self.subscription_status["Token Expiration"]))
            except KeyError:
                logger.debug(traceback.format_exc())

    def get_user_data_list(self):
        return_list = []
        for k in self.required_user_keys:
            try:
                return_list.append(['', k, self.user_data[k]])
            except KeyError:
                pass 
                #return_list=[['', k, self.user_data[k]]]
        return return_list

    def load_file(self):
        try:
            user_file = open(self.path_to_file, 'r')
        except FileNotFoundError:
            logger.debug("User data file could not be found.")
            #self.reset_user_dict()
            return
        
        try:
            self.user_data = json.load(user_file)
        except ValueError:
            logger.warning("User data file could not load.")
            return

        for label in self.required_user_keys:
            try:
                self.inputs[label].setText(self.user_data[label])
                logger.debug("Setting {} to {}".format(label,self.user_data[label]))
            except AttributeError: #Then it is a QCombobox or QPlainTextEdit
                try:
                    self.inputs[label].setPlainText(self.user_data[label])
                    logger.debug("Setting {} to {}".format(label,self.user_data[label]))
                except AttributeError: #Then it is a QCombobox
                    try:
                        idx = self.inputs[label].findText(self.user_data[label])
                    except:
                        idx = 0
                    self.inputs[label].setCurrentIndex(idx)
                    logger.debug("Setting {} to {}".format(label, self.inputs[label].currentText()))

    def reset_user_dict(self):
        self.user_data = {}
        for key in self.required_user_keys:
            self.user_data[key] = ""
        #self.user_data["Web Token"] = "" 
    
    def get_current_data(self):
        return self.user_data

    def send_web_key_test(self,display_dialog=True):
        """
        Encrypt a message with the public key and send it to the server. 
        Wait for a response to get back the test message.
        Uses the TU_crypt functions.
        Returns True if the test passes
        """
        logger.info("Testing the TU_crypt envelope encryption.")
        test_message = b'This is a test: ' + bytes([b for b in range(256)]) #Sent a bytestream with every byte.
        logger.debug(test_message)

        try:
            package = encrypt_bytes(test_message, bytes(self.user_data["Decoder Public Key"],'ascii'))
            result = json.loads(self.upload_data({"Test Message": package}))
            logger.debug("Upload data returned: {}".format(result))
        except:
            logger.debug(traceback.format_exc())
            QMessageBox.warning(self,"Failure","The encryption test on the local client did not work.")
            return False

        try:
            returned_message = base64.b64decode(result["Decrypted Bytes"].encode('ascii'))
            logger.debug("\nReturned Message: {}".format(returned_message))
            if test_message == returned_message:
                if display_dialog:
                    QMessageBox.information(self,"Success","The test message was successfully encrypted with the local public key and decrypted with the server's private key.")
                return True
            else:
                logger.debug("The Returned Message did not match the test message.")
        except:
            logger.debug(traceback.format_exc())
       
        QMessageBox.warning(self,"Failure","The decryption test on the server did not work.")
        return False

    def upload_data(self, data_package):
        """
        Take a message dictionary, converts it to json,  signs it and sends it on the way.
        """
        logger.debug(data_package)
        pgp_message = self.make_pgp_message(data_package)
        header_values = {"Content-type": 'application/text', 
                         "User-pubkey": base64.b64encode(bytes(self.private_key.pubkey)), # used to verify data_package
                         'Api-pubkey': base64.b64encode(bytes(self.user_data["Decoder Public Key"],'ascii')), # shows server what key was used to encrypt data
                         'Authorization' : self.user_data["Web Token"] #used for user authentication
                         }
        url = self.user_data["Decoder Web Site Address"] 
        try:
            r = requests.post(url, data=str(pgp_message), headers=header_values)
            # Log what we get back
            logger.debug(r.status_code)
            for k,v in r.headers.items():
                logger.debug("{}: {}".format(k,v))
            logger.debug("Response Contents: {}".format(r.text))
            if r.status_code == 401: #Unauthorized
                logger.debug("Unauthorized. Need to have a valid token.")
                QMessageBox.warning(self,"Token Invalid", r.text)
                return
            elif r.status_code == 501: #Not Implemented
                logger.debug("Request contents not implemented.")
                QMessageBox.warning(self,"Not Implemented", r.text)
                return
            try:
                #update the token
                self.user_data["Web Token"] = r.headers['new-token']
                self.process_web_token()
                # process the message    
                pgp_message = pgpy.PGPMessage.from_blob(base64.b64decode(r.text))
                logger.debug(str(pgp_message))
                return pgp_message.message

            except:
                logger.debug(traceback.format_exc())
            logger.debug("Finished with requests.")
        except:
            logger.debug(traceback.format_exc())


    def make_pgp_message(self, data_dict):
        """
        Convert a python dictionary to a signed pgp message to be sent across the internet or saved.
        """
        file_contents = json.dumps(data_dict, indent=4, sort_keys=True)
        pgp_message = pgpy.PGPMessage.new(file_contents,
                                 cleartext=False,
                                 sensitive=False,
                                 compression=CompressionAlgorithm.ZIP,
                                 encoding='ascii')
        pgp_message |= self.private_key.sign(pgp_message)
        return pgp_message



    def show_private_key_details(self):
        key_details = "PGP Private Key has the following properties:\n"
        key_details += "  fingerprint:   {}\n".format(self.private_key.fingerprint)
        key_details += "  created:       {}\n".format(self.private_key.created)
        key_details += "  expires_at:    {}\n".format(self.private_key.expires_at)
        key_details += "  is_expired:    {}\n".format(self.private_key.is_expired)
        key_details += "  is_primary:    {}\n".format(self.private_key.is_primary)
        key_details += "  is_protected:  {}\n".format(self.private_key.is_protected)
        key_details += "  is_public:     {}\n".format(self.private_key.is_public)
        key_details += "  is_unlocked:   {}\n".format(self.private_key.is_unlocked)
        key_details += "  key_algorithm: {}\n".format(self.private_key.key_algorithm)
        key_details += "  key_size:      {}\n".format(self.private_key.key_size)
        key_details += "  pubkey:        {}\n".format(self.private_key.pubkey)
        key_details += "  signers:       {}\n".format(self.private_key.signers)
        key_details += "  userid:        {}\n".format(self.private_key.userids[0])
        logger.info(key_details)
        QMessageBox.information(self, "Private Key Details", key_details)

    def load_private_key_contents(self):
        logger.debug("Trying to open the private key file from {}".format(self.user_data["Local Private Key File"]))
        try:
            self.private_key, details = pgpy.PGPKey.from_file(self.user_data["Local Private Key File"])   
            self.public_key = self.private_key.pubkey
            self.public_key |= self.private_key.certify(self.public_key)
            

            logger.debug("Successfully loaded private key and signed the public key.")
        except:
            logger.debug("Private key failed to load.")
            logger.debug(traceback.format_exc())
            #QMessageBox.warning(self, "Private Key Failed",
            #    "Failed to load a private key\n{}".format(traceback.format_exc()))
            self.private_key = None
            #self.private_key = self.generate_private_key() #maybe we can generate the private key here
        
        # self.private_key may be None
        try:
            self.inputs["Local Private Key"].setText(str(self.private_key.fingerprint))
            self.inputs["Local Private Key"].setReadOnly(True)
            p = self.inputs["Local Private Key"].palette()
            p.setColor(QPalette.Base, QColor('light green'))
            self.inputs["Local Private Key"].setPalette(p)
            return True

        except AttributeError:
            self.inputs["Local Private Key"].setText("PGP key is not found.")
            #logger.debug(traceback.format_exc())
            p = self.inputs["Local Private Key"].palette()
            p.setColor(QPalette.Base, QColor("red"))
            self.inputs["Local Private Key"].setPalette(p)
            self.private_key = None
            return False
            

    def register_public_key(self):
        message_contents = str(self.public_key)
        msg = QMessageBox.question(self,
                                   "User's PGP Public Key",
                                   str(self.public_key)+ "\n\n Would you like to register the key with {}?".format(self.user_data["Decoder Web Site Address"]),
                                   )
        
        
        if msg == QMessageBox.Yes:
            logger.debug("Request to upload public key.")

            #used this if yoou want to manually update
            #r = requests.put(url+'/user/provision', headers={})
            #or
            #import swagger client to keep automatic
            # Exepct to get a signed user public key for PGP signing so we don't have to store keys 
            # and confirm that the key should be used for data signing.

    def generate_private_key(self):
        """
        Generate a new PGP private key with the instance user data.
        Saves the file
        Reloads the dialog box with the new private key fingerprint
        """
        fname = QFileDialog.getSaveFileName(self, 
                                            'Select Private Key File',
                                            os.getcwd(),
                                            "Pretty Good Privacy (*.pgp)",
                                            "Pretty Good Privacy (*.pgp)")
        if fname[0]:
            self.user_data["Local Private Key File"] = fname[0]
            self.inputs["Local Private Key File"].setText(fname[0])
        else:
            return
        #save the data first
        
        # Create a new key
        primary_key = pgpy.PGPKey.new(PubKeyAlgorithm.ECDSA, EllipticCurveOID.NIST_P256)
        # Setup a PGP ID, but don't use emails, since those can be scraped off the internet and spammed.

        user_id = pgpy.PGPUID.new('{} {}'.format(self.user_data["First Name"],self.user_data["Last Name"]) , 
                      comment="{}".format(self.user_data["Company"]), 
                      email="{}, {}".format(self.user_data["City"], self.user_data["State/Province"] ))
        logger.debug("Created a PGP User ID")

        # Add the user id to the key
        primary_key.add_uid(user_id, 
                            usage={KeyFlags.Sign, 
                                   KeyFlags.EncryptCommunications, 
                                   KeyFlags.EncryptStorage,
                                   KeyFlags.Authentication},
                            ciphers=[SymmetricKeyAlgorithm.AES128],
                            hashes=[HashAlgorithm.SHA256],
                            compression=[CompressionAlgorithm.ZIP,CompressionAlgorithm.Uncompressed],
                            key_expiration=None,
                            key_server="{}/pgp/".format(self.user_data["Decoder Web Site Address"]),
                            primary=True)
        
        #cert = primary_key.certify(someones_pubkey.userids[0], level=SignatureType.Persona_Cert)
        #someones_pubkey.userids[0] |= cert

        with open(self.user_data["Local Private Key File"],'w') as f:
            f.write(str(primary_key))
        logger.info("Saved PGP key with fingerprint {} to {}".format(primary_key.fingerprint, 
                                                                    self.user_data["Local Private Key File"]))
        
        if self.load_private_key_contents():
            self.save_user_data()    

    def find_user_private_key(self):
        fname = QFileDialog.getOpenFileName(self, 
                                            'Find User Private Key File',
                                            os.getcwd(),
                                            "Pretty Good Privacy (*.pgp);;All Files (*.*)",
                                            "Pretty Good Privacy (*.pgp)")
        if fname[0]:
            self.inputs["Local Private Key File"].setText(fname[0])
            self.user_data["Local Private Key File"] = fname[0]
            if self.load_private_key_contents():
                self.save_user_data()

    # def find_user_public_key(self):

    #     fname = QFileDialog.getOpenFileName(self, 
    #                                         'Find User PGP Public Key File', 
    #                                         os.getcwd(), 
    #                                         "PEM Files (*.pgp)", 
    #                                         "PEM Files (*.pgp)")
    #     if fname[0]:
    #         self.inputs["User Public Key File"].setText(fname[0])


    def find_web_key(self):
        fname = QFileDialog.getOpenFileName(self, 
                                            'Find Decoder Public Key', 
                                            os.getcwd(), 
                                            "PEM Files (*.pem)", 
                                            "PEM Files (*.pem)")
        if fname[0]:
            with open(fname[0],'r') as f:
                self.inputs["Decoder Public Key"].setPlainText(f.read())
            self.inputs["Decoder Public Key"].setReadOnly(True)
    
    def update_web_key(self):
        self.user_data["Decoder Public Key"] = self.inputs["Decoder Public Key"].toPlainText()

    def show_dialog(self):

        
                 
        self.exec_()

    def update_user_data(self):
        """
        Iterate through the dialog box inputs and update the user data dictionary.
        This should be connected to signals that are emitted when the values change. 
        """
        for label in self.required_user_keys:
            try:
                self.user_data[label] = self.inputs[label].text()
            except AttributeError:
                try:
                    self.user_data[label] = self.inputs[label].currentText()
                except AttributeError:
                    self.user_data[label] = self.inputs[label].toPlainText()

    def save_user_data(self):
        self.update_user_data()
        try:
            with open(self.path_to_file,'w') as out_file:
                json.dump(self.user_data, out_file, sort_keys=True, indent=4)
            logger.debug("Wrote User Data file to {}.".format(self.path_to_file))
        except:
            logger.warning("Failure Writing User File.")
            logger.debug(traceback.format_exc())
     

state_names = {
    'AK': 'Alaska',
    'AL': 'Alabama',
    'AR': 'Arkansas',
    'AS': 'American Samoa',
    'AZ': 'Arizona',
    'CA': 'California',
    'CO': 'Colorado',
    'CT': 'Connecticut',
    'DC': 'Dist. of Columbia',
    'DE': 'Delaware',
    'FL': 'Florida',
    'GA': 'Georgia',
    'GU': 'Guam',
    'HI': 'Hawaii',
    'IA': 'Iowa',
    'ID': 'Idaho',
    'IL': 'Illinois',
    'IN': 'Indiana',
    'KS': 'Kansas',
    'KY': 'Kentucky',
    'LA': 'Louisiana',
    'MA': 'Massachusetts',
    'MD': 'Maryland',
    'ME': 'Maine',
    'MI': 'Michigan',
    'MN': 'Minnesota',
    'MO': 'Missouri',
    'MS': 'Mississippi',
    'MT': 'Montana',
    'NA': 'National',
    'NC': 'North Carolina',
    'ND': 'North Dakota',
    'NE': 'Nebraska',
    'NH': 'New Hampshire',
    'NJ': 'New Jersey',
    'NM': 'New Mexico',
    'NV': 'Nevada',
    'NY': 'New York',
    'OH': 'Ohio',
    'OK': 'Oklahoma',
    'OR': 'Oregon',
    'PA': 'Pennsylvania',
    'PR': 'Puerto Rico',
    'RI': 'Rhode Island',
    'SC': 'South Carolina',
    'SD': 'South Dakota',
    'TN': 'Tennessee',
    'TX': 'Texas',
    'UT': 'Utah',
    'VA': 'Virginia',
    'VI': 'Virgin Islands',
    'VT': 'Vermont',
    'WA': 'Washington',
    'WI': 'Wisconsin',
    'WV': 'West Virginia',
    'WY': 'Wyoming',
    'AB': 'Alberta',
    'BC': 'British Columbia',
    'MB': 'Manitoba',
    'NB': 'New Brunswick',
    'NL': 'Newfoundland',
    'NT': 'Northwest Terr.',
    'NS': 'Nova Scotia',
    'NU': 'Nunavut',
    'ON': 'Ontario',
    'QC': 'Quebec',
    'SK': 'Saskatchewan',
    'YT': 'Yukon'
}

country_names = {
    "US":"UNITED STATES",
    "CA":"CANADA",
    "AF":"AFGHANISTAN",
    "AX":"ALAND ISLANDS",
    "AL":"ALBANIA",
    "DZ":"ALGERIA",
    "AS":"AMERICAN SAMOA",
    "AD":"ANDORRA",
    "AO":"ANGOLA",
    "AI":"ANGUILLA",
    "AQ":"ANTARCTICA",
    "AG":"ANTIGUA AND BARBUDA",
    "AR":"ARGENTINA",
    "AM":"ARMENIA",
    "AW":"ARUBA",
    "AU":"AUSTRALIA",
    "AT":"AUSTRIA",
    "AZ":"AZERBAIJAN",
    "BS":"BAHAMAS",
    "BH":"BAHRAIN",
    "BD":"BANGLADESH",
    "BB":"BARBADOS",
    "BY":"BELARUS",
    "BE":"BELGIUM",
    "BZ":"BELIZE",
    "BJ":"BENIN",
    "BM":"BERMUDA",
    "BT":"BHUTAN",
    "BO":"BOLIVIA",
    "BA":"BOSNIA ",
    "BW":"BOTSWANA",
    "BV":"BOUVET ISLAND",
    "BR":"BRAZIL",
    "IO":"BRITISH ",
    "BN":"BRUNEI DARUSSALAM",
    "BG":"BULGARIA",
    "BF":"BURKINA FASO",
    "BI":"BURUNDI",
    "KH":"CAMBODIA",
    "CM":"CAMEROON",
    "CV":"CAPE VERDE",
    "KY":"CAYMAN ISLANDS",
    "CF":"CENTRAL AFRICAN REPUBLIC",
    "TD":"CHAD",
    "CL":"CHILE",
    "CN":"CHINA",
    "CX":"CHRISTMAS ISLAND",
    "CC":"COCOS ISLANDS",
    "CO":"COLOMBIA",
    "KM":"COMOROS",
    "CG":"CONGO",
    "CD":"CONGO",
    "CK":"COOK ISLANDS",
    "CR":"COSTA RICA",
    "CI":"COTE D'IVOIRE",
    "HR":"CROATIA",
    "CU":"CUBA",
    "CY":"CYPRUS",
    "CZ":"CZECH REPUBLIC",
    "DK":"DENMARK",
    "DJ":"DJIBOUTI",
    "DM":"DOMINICA",
    "DO":"DOMINICAN REPUBLIC",
    "EC":"ECUADOR",
    "EG":"EGYPT",
    "SV":"EL SALVADOR",
    "GQ":"EQUATORIAL GUINEA",
    "ER":"ERITREA",
    "EE":"ESTONIA",
    "ET":"ETHIOPIA",
    "FK":"FALKLAND ISLANDS",
    "FO":"FAROE ISLANDS",
    "FJ":"FIJI",
    "FI":"FINLAND",
    "FR":"FRANCE",
    "GF":"FRENCH GUIANA",
    "PF":"FRENCH POLYNESIA",
    "GA":"GABON",
    "GM":"GAMBIA",
    "GE":"GEORGIA",
    "DE":"GERMANY",
    "GH":"GHANA",
    "GI":"GIBRALTAR",
    "GR":"GREECE",
    "GL":"GREENLAND",
    "GD":"GRENADA",
    "GP":"GUADELOUPE",
    "GU":"GUAM",
    "GT":"GUATEMALA",
    "GG":"GUERNSEY",
    "GN":"GUINEA",
    "GW":"GUINEA-BISSAU",
    "GY":"GUYANA",
    "HT":"HAITI",
    "HM":"HEARD ISLAND",
    "VA":"VATICAN CITY",
    "HN":"HONDURAS",
    "HK":"HONG KONG",
    "HU":"HUNGARY",
    "IS":"ICELAND",
    "IN":"INDIA",
    "ID":"INDONESIA",
    "IR":"IRAN",
    "IQ":"IRAQ",
    "IE":"IRELAND",
    "IM":"ISLE OF MAN",
    "IL":"ISRAEL",
    "IT":"ITALY",
    "JM":"JAMAICA",
    "JP":"JAPAN",
    "JE":"JERSEY",
    "JO":"JORDAN",
    "KZ":"KAZAKHSTAN",
    "KE":"KENYA",
    "KI":"KIRIBATI",
    "KP":"NORTH KOREA",
    "KR":"KOREA",
    "KW":"KUWAIT",
    "KG":"KYRGYZSTAN",
    "LA":"LAO",
    "LV":"LATVIA",
    "LB":"LEBANON",
    "LS":"LESOTHO",
    "LR":"LIBERIA",
    "LY":"LIBYAN ARAB JAMAHIRIYA",
    "LI":"LIECHTENSTEIN",
    "LT":"LITHUANIA",
    "LU":"LUXEMBOURG",
    "MO":"MACAO",
    "MK":"MACEDONIA",
    "MG":"MADAGASCAR",
    "MW":"MALAWI",
    "MY":"MALAYSIA",
    "MV":"MALDIVES",
    "ML":"MALI",
    "MT":"MALTA",
    "MH":"MARSHALL ISLANDS",
    "MQ":"MARTINIQUE",
    "MR":"MAURITANIA",
    "MU":"MAURITIUS",
    "YT":"MAYOTTE",
    "MX":"MEXICO",
    "FM":"MICRONESIA",
    "MD":"MOLDOVA",
    "MC":"MONACO",
    "MN":"MONGOLIA",
    "ME":"MONTENEGRO",
    "MS":"MONTSERRAT",
    "MA":"MOROCCO",
    "MZ":"MOZAMBIQUE",
    "MM":"MYANMAR",
    "NA":"NAMIBIA",
    "NR":"NAURU",
    "NP":"NEPAL",
    "NL":"NETHERLANDS",
    "AN":"NETHERLANDS ANTILLES",
    "NC":"NEW CALEDONIA",
    "NZ":"NEW ZEALAND",
    "NI":"NICARAGUA",
    "NE":"NIGER",
    "NG":"NIGERIA",
    "NU":"NIUE",
    "NF":"NORFOLK ISLAND",
    "MP":"NORTHERN MARIANA ISLANDS",
    "NO":"NORWAY",
    "OM":"OMAN",
    "PK":"PAKISTAN",
    "PW":"PALAU",
    "PS":"PALESTINIAN TERRITORY",
    "PA":"PANAMA",
    "PG":"PAPUA NEW GUINEA",
    "PY":"PARAGUAY",
    "PE":"PERU",
    "PH":"PHILIPPINES",
    "PN":"PITCAIRN",
    "PL":"POLAND",
    "PT":"PORTUGAL",
    "PR":"PUERTO RICO",
    "QA":"QATAR",
    "RE":"REUNION",
    "RO":"ROMANIA",
    "RU":"RUSSIAN FEDERATION",
    "RW":"RWANDA",
    "BL":"SAINT BARTHELEMY",
    "SH":"SAINT HELENA",
    "KN":"SAINT KITTS AND NEVIS",
    "LC":"SAINT LUCIA",
    "MF":"SAINT MARTIN",
    "PM":"SAINT PIERRE",
    "VC":"SAINT VINCENT",
    "WS":"SAMOA",
    "SM":"SAN MARINO",
    "ST":"SAO TOME AND PRINCIPE",
    "SA":"SAUDI ARABIA",
    "SN":"SENEGAL",
    "RS":"SERBIA",
    "SC":"SEYCHELLES",
    "SL":"SIERRA LEONE",
    "SG":"SINGAPORE",
    "SK":"SLOVAKIA",
    "SI":"SLOVENIA",
    "SB":"SOLOMON ISLANDS",
    "SO":"SOMALIA",
    "ZA":"SOUTH AFRICA",
    "GS":"SOUTH GEORGIA AND TH",
    "ES":"SPAIN",
    "LK":"SRI LANKA",
    "SD":"SUDAN",
    "SR":"SURINAME",
    "SJ":"SVALBARD AND JAN MAYEN",
    "SZ":"SWAZILAND",
    "SE":"SWEDEN",
    "CH":"SWITZERLAND",
    "SY":"SYRIAN ARAB REPUBLIC",
    "TW":"TAIWAN",
    "TJ":"TAJIKISTAN",
    "TZ":"TANZANIA",
    "TH":"THAILAND",
    "TL":"TIMOR-LESTE",
    "TG":"TOGO",
    "TK":"TOKELAU",
    "TO":"TONGA",
    "TT":"TRINIDAD AND TOBAGO",
    "TN":"TUNISIA",
    "TR":"TURKEY",
    "TM":"TURKMENISTAN",
    "TC":"TURKS AND CAICOS ISLANDS",
    "TV":"TUVALU",
    "UG":"UGANDA",
    "UA":"UKRAINE",
    "AE":"UNITED ARAB EMIRATES",
    "GB":"UNITED KINGDOM",
    "UM":"UNITED STATE",
    "UY":"URUGUAY",
    "UZ":"UZBEKISTAN",
    "VU":"VANUATU",
    "VE":"VENEZUELA",
    "VN":"VIET NAM",
    "VG":"VIRGIN ISLANDS, BRITISH",
    "VI":"VIRGIN ISLANDS, U.S.",
    "WF":"WALLIS AND FUTUNA",
    "EH":"WESTERN SAHARA",
    "YE":"YEMEN",
    "ZM":"ZAMBIA",
    "ZW ":"ZIMBABWE"
}

def user_data_standalone():
    """
    Use this function to test the basic functionality.
    """
    print(os.terminal_size.lines)
    print(os.terminal_size.columns)
    app = QCoreApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    else:
        app.close()
    execute = Standalone()
    sys.exit(app.exec_())

class Standalone(QMainWindow):
    def __init__(self):
        super(Standalone, self).__init__()
        self.init_ui()
        user_data = UserData()
        user_data.show_dialog()  
    
    def init_ui(self):
        self.statusBar().showMessage("Testing UserData Module")
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.setWindowTitle('UserData Test')
        self.show()

if __name__ == '__main__':
    user_data_standalone()