from PyQt5.QtWidgets import (QMainWindow,
                             QApplication,
                             QWidget,
                             QComboBox,
                             QLabel,
                             QDialog,
                             QDialogButtonBox,
                             QGridLayout,
                             QVBoxLayout,
                             QFileDialog,
                             QPushButton,
                             QGroupBox,
                             QPlainTextEdit,
                             QLineEdit)
from PyQt5.QtCore import (Qt, QCoreApplication)
from PyQt5.QtGui import QIcon, QFont
#import bcrypt #use this for passwords
import jwt
import pgpy
from pgpy.constants import (PubKeyAlgorithm, 
                            KeyFlags, 
                            HashAlgorithm, 
                            SymmetricKeyAlgorithm, 
                            CompressionAlgorithm, 
                            EllipticCurveOID, 
                            SignatureType)
import traceback
import sys
import os
import json
import logging
import logging.config
with open("logging.config.json",'r') as f:
    logging_dictionary = json.load(f)

logging.config.dictConfig(logging_dictionary)
logger = logging.getLogger(__name__)



class UserData(QDialog):
    def __init__(self, path_to_file = "User Data.json"):
        super(UserData, self).__init__()
        self.path_to_file = path_to_file
        self.token = None
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
                #self.reset_user_dict()


        # Check all entries
        # if self.check_entries():
        #     self.reset_user_dict()
        #     #QCoreApplication.processEvents()
        
    def check_entries(self):
        for key, value in self.user_data.items():
            if key not in self.required_user_keys or type(value) is not str:
                logger.warning("User data for {} is not formatted correctly.".format(key))    
                return True
        data_keys = [k for k in self.user_data.keys()]
        for key in self.required_user_keys:
            if key not in data_keys:
                return True
        return False    

    def reset_user_dict(self):
        self.user_data = {}
        for key in self.required_user_keys:
            self.user_data[key] = ""
        #self.show_dialog()
    
    def get_current_data(self):
        return self.user_data

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

        user_data_frame_layout = QGridLayout()
        user_data_frame.setLayout(user_data_frame_layout)
        
        decoding_service_frame_layout = QGridLayout()
        decoding_service_frame.setLayout(decoding_service_frame_layout)
        
        subscription_status_frame_layout = QGridLayout()
        subscription_status_frame.setLayout(subscription_status_frame_layout)
               
        pgp_frame_layout = QGridLayout()
        pgp_frame.setLayout(pgp_frame_layout)
               

        self.inputs["State/Province"] = QComboBox()
        self.inputs["State/Province"].addItems(state_names.values())
        self.inputs["State/Province"].setEditable(True)
        #self.inputs["State/Province"].setSizeAdjustPolicy(QComboBox.AdjustToContents)
        
        self.inputs["Country"] = QComboBox()
        self.inputs["Country"].addItems(country_names.values())
        #self.inputs["Country"].setSizeAdjustPolicy(QComboBox.AdjustToContents)
             
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            Qt.Horizontal, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.accepted.connect(self.save_user_data)
        self.rejected.connect(self.close)
        
        # Setup grids 

        user_data_frame_layout.addWidget(self.labels["First Name"],       0, 0, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["First Name"],       0, 1, 1, 1)
            
        user_data_frame_layout.addWidget(self.labels["Last Name"],        0, 2, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["Last Name"],        0, 3, 1, 3)
            
        user_data_frame_layout.addWidget(self.labels["Title"],            1, 0, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["Title"],            1, 1, 1, 1)
            
        user_data_frame_layout.addWidget(self.labels["E-mail"],           1, 2, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["E-mail"],           1, 3, 1, 3)
              
        user_data_frame_layout.addWidget(self.labels["Company"],          2, 0, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["Company"],          2, 1, 1, 5)
            
        user_data_frame_layout.addWidget(self.labels["Address 1"],        3, 0, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["Address 1"],        3, 1, 1, 5)
            
        user_data_frame_layout.addWidget(self.labels["Address 2"],        4, 0, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["Address 2"],        4, 1, 1, 5)
            
        user_data_frame_layout.addWidget(self.labels["City"],             5, 0, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["City"],             5, 1, 1, 1)
            
        user_data_frame_layout.addWidget(self.labels["State/Province"],   5, 2, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["State/Province"],   5, 3, 1, 1)
        
        user_data_frame_layout.addWidget(self.labels["Postal Code"],      5, 4, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["Postal Code"],      5, 5, 1, 1)
            
        user_data_frame_layout.addWidget(self.labels["Country"],          6, 0, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["Country"],          6, 1, 1, 1)
        
        user_data_frame_layout.addWidget(self.labels["Phone"],            6, 2, 1, 1)
        user_data_frame_layout.addWidget(self.inputs["Phone"],            6, 3, 1, 1)
        
        
        self.inputs["Decoder Web Site Address"] = QComboBox()
        self.inputs["Decoder Web Site Address"].addItems(["https://localhost:7774",
                                                          "https://truckcrypt.synercontechnologies.com"])
        self.inputs["Decoder Web Site Address"].setEditable(True)
        self.inputs["Decoder Web Site Address"].setToolTip("Enter the URL for the URL pointing to the portal to decrypt, decode, store, and verify your data package files.")
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
        


        pgp_frame_layout.addWidget(self.labels["Local Private Key File"], 0, 0, 1, 2),
        pgp_frame_layout.addWidget(self.inputs["Local Private Key File"], 1, 0, 1, 2)
        self.inputs["Local Private Key File"].setToolTip("This private key is your secret. This key is used to digitally sign files that are attributed to you. You must never share this key.")
        self.inputs["Local Private Key"] = QPlainTextEdit(self)
        self.inputs["Local Private Key"].setFont(QFont("Lucida Sans Typewriter"))
        #self.inputs["Local Private Key"].setFixedHeight(150)
        #self.inputs["Local Private Key"].setFixedWidth(480)
        
        user_private_key_file_button = QPushButton("Select Private Key File")
        user_private_key_file_button.clicked.connect(self.find_user_private_key)
        pgp_frame_layout.addWidget(user_private_key_file_button, 2, 0, 1, 1)
        
        show_private_key_contents_button = QPushButton("Show PGP Key Details")
        show_private_key_contents_button.clicked.connect(self.show_private_key_details)
        pgp_frame_layout.addWidget(show_private_key_contents_button, 2, 1, 1, 1)
        
        pgp_frame_layout.addWidget(self.inputs["Local Private Key"], 3, 0, 1, 2)
        generate_private_key_button = QPushButton("Create New Private Key")
        generate_private_key_button.setToolTip("Generate a new Private Key file for PGP based on your User Details")
        generate_private_key_button.clicked.connect(self.generate_private_key)
        pgp_frame_layout.addWidget(generate_private_key_button, 4, 0, 1, 1)
        register_key_button = QPushButton("Register PGP Public Key")
        register_key_button.setToolTip("Uploads a PGP public Key to a trusted website to establish trust.")
        register_key_button.clicked.connect(self.register_public_key)
        pgp_frame_layout.addWidget(register_key_button, 4, 1, 1, 1)
        
        # user_public_key_file_button = QPushButton("Select File")
        # user_public_key_file_button.clicked.connect(self.find_user_public_key)
        # user_data_frame_layout.addWidget(user_public_key_file_button,         14, 5, 1, 1)
        # user_data_frame_layout.addWidget(self.labels["User Public Key File"], 13, 0, 1, 3)
        # user_data_frame_layout.addWidget(self.inputs["User Public Key File"], 14, 0, 1, 5)
        # self.inputs["User Public Key File"].setToolTip("TruckCRYPT uses this key to verify digitally signed files that you signed with the private key. Therefore, you should share this key so others can verify your signature.")

        dialog_box_layout.addWidget(user_data_frame,0,0,1,3)
        dialog_box_layout.addWidget(decoding_service_frame, 1,0,1,1)
        dialog_box_layout.addWidget(subscription_status_frame, 1,1,1,1)
        dialog_box_layout.addWidget(pgp_frame, 1,2,1,1)

        dialog_box_layout.addWidget(self.buttons, 2, 2, 1, 1)

        self.setLayout(dialog_box_layout)

        self.setWindowTitle("User and Service Information")
        self.setWindowModality(Qt.ApplicationModal) 
    
    def show_private_key_details(self):
        pass
    
    def load_private_key_contents(self):
        logger.debug("Trying to open the private key file from {}".format(self.user_data["Local Private Key File"]))
        try:
            with open(self.user_data["Local Private Key File"],'r') as f:
                self.inputs["Local Private Key"].setPlainText(f.read())

        except FileNotFoundError:
            logger.debug("Local Private Key File not Found")
            return
        try:
            self.private_key = pgpy.PGPKey.from_file(self.user_data["Local Private Key File"])
        except:
            logger.debug("Private key failed to load.")
            logger.debug(traceback.format_exc())
            self.private_key = None #maybe we can generate the private key here

    def register_public_key(self):
        pass
    def generate_private_key(self):
        pass

    def find_user_private_key(self):
        fname = QFileDialog.getOpenFileName(self, 
                                            'Find User Private Key File',
                                            os.getcwd(),
                                            "PEM Files (*.pem)",
                                            "PEM Files (*.pem)")
        if fname[0]:
            self.inputs["Local Private Key File"].setText(fname[0])
            self.load_private_key_contents()

    def find_user_public_key(self):

        fname = QFileDialog.getOpenFileName(self, 
                                            'Find User Public Key File', 
                                            os.getcwd(), 
                                            "PEM Files (*.pem)", 
                                            "PEM Files (*.pem)")
        if fname[0]:
            self.inputs["User Public Key File"].setText(fname[0])

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

    def show_dialog(self):

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
                        logger.debug("Setting {} to {}".format(label,self.user_data[label]))
                    except:
                        idx = 0
                    self.inputs[label].setCurrentIndex(idx)
                 
        self.exec_()

    def save_user_data(self):
        logger.debug("Accepted Dialog OK")
        for label in self.required_user_keys:
            try:
                self.user_data[label] = self.inputs[label].text()
            except AttributeError:
                try:
                    self.user_data[label] = self.inputs[label].currentText()
                except AttributeError:
                    self.user_data[label] = self.inputs[label].toPlainText()
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
    'DC': 'District of Columbia',
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
    'MP': 'Northern Mariana Islands',
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
    'NL': 'Newfoundland and Labrador',
    'NT': 'Northwest Territories',
    'NS': 'Nova Scotia',
    'NU': 'Nunavut',
    'ON': 'Ontario',
    'PE': 'Prince Edward Island',
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
    "BO":"BOLIVIA, PLURINATIONAL STATE OF",
    "BA":"BOSNIA AND HERZEGOVINA",
    "BW":"BOTSWANA",
    "BV":"BOUVET ISLAND",
    "BR":"BRAZIL",
    "IO":"BRITISH INDIAN OCEAN TERRITORY",
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
    "CC":"COCOS (KEELING) ISLANDS",
    "CO":"COLOMBIA",
    "KM":"COMOROS",
    "CG":"CONGO",
    "CD":"CONGO, THE DEMOCRATIC REPUBLIC OF THE",
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
    "FK":"FALKLAND ISLANDS (MALVINAS)",
    "FO":"FAROE ISLANDS",
    "FJ":"FIJI",
    "FI":"FINLAND",
    "FR":"FRANCE",
    "GF":"FRENCH GUIANA",
    "PF":"FRENCH POLYNESIA",
    "TF":"FRENCH SOUTHERN TERRITORIES",
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
    "HM":"HEARD ISLAND AND MCDONALD ISLANDS",
    "VA":"HOLY SEE (VATICAN CITY STATE)",
    "HN":"HONDURAS",
    "HK":"HONG KONG",
    "HU":"HUNGARY",
    "IS":"ICELAND",
    "IN":"INDIA",
    "ID":"INDONESIA",
    "IR":"IRAN, ISLAMIC REPUBLIC OF",
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
    "KP":"KOREA, DEMOCRATIC PEOPLE'S REPUBLIC OF",
    "KR":"KOREA, REPUBLIC OF",
    "KW":"KUWAIT",
    "KG":"KYRGYZSTAN",
    "LA":"LAO PEOPLE'S DEMOCRATIC REPUBLIC",
    "LV":"LATVIA",
    "LB":"LEBANON",
    "LS":"LESOTHO",
    "LR":"LIBERIA",
    "LY":"LIBYAN ARAB JAMAHIRIYA",
    "LI":"LIECHTENSTEIN",
    "LT":"LITHUANIA",
    "LU":"LUXEMBOURG",
    "MO":"MACAO",
    "MK":"MACEDONIA, THE FORMER YUGOSLAV REPUBLIC OF",
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
    "FM":"MICRONESIA, FEDERATED STATES OF",
    "MD":"MOLDOVA, REPUBLIC OF",
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
    "PS":"PALESTINIAN TERRITORY, OCCUPIED",
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
    "SH":"SAINT HELENA, ASCENSION AND TRISTAN DA CUNHA",
    "KN":"SAINT KITTS AND NEVIS",
    "LC":"SAINT LUCIA",
    "MF":"SAINT MARTIN",
    "PM":"SAINT PIERRE AND MIQUELON",
    "VC":"SAINT VINCENT AND THE GRENADINES",
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
    "GS":"SOUTH GEORGIA AND THE SOUTH SANDWICH ISLANDS",
    "ES":"SPAIN",
    "LK":"SRI LANKA",
    "SD":"SUDAN",
    "SR":"SURINAME",
    "SJ":"SVALBARD AND JAN MAYEN",
    "SZ":"SWAZILAND",
    "SE":"SWEDEN",
    "CH":"SWITZERLAND",
    "SY":"SYRIAN ARAB REPUBLIC",
    "TW":"TAIWAN, PROVINCE OF CHINA",
    "TJ":"TAJIKISTAN",
    "TZ":"TANZANIA, UNITED REPUBLIC OF",
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
    "UM":"UNITED STATES MINOR OUTLYING ISLANDS",
    "UY":"URUGUAY",
    "UZ":"UZBEKISTAN",
    "VU":"VANUATU",
    "VE":"VENEZUELA, BOLIVARIAN REPUBLIC OF",
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