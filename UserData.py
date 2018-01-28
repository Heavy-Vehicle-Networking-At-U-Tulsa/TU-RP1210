from PyQt5.QtWidgets import (QMainWindow,
                             QWidget,
                             QComboBox,
                             QLabel,
                             QDialog,
                             QDialogButtonBox,
                             QGridLayout,
                             QFileDialog,
                             QPushButton,
                             QLineEdit)
from PyQt5.QtCore import (Qt, QCoreApplication)
import traceback
import os
import json
import logging
logger = logging.getLogger(__name__)


class UserData(QDialog):
    def __init__(self, path_to_file = "TruckCRYPT User Data.txt"):
        super(UserData, self).__init__()
        self.path_to_file = path_to_file
        
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
                                  "TruckCRYPT Web Site",
                                  "TruckCRYPT Web Public Key File",
                                  "User Private Key File",
                                  "User Public Key File"]
        left_align = ["TruckCRYPT Web Site",
                      "TruckCRYPT Web Public Key File",
                      "User Private Key File",
                      #"TruckCRYPT API Key File",
                      "User Public Key File"]
        
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
            self.reset_user_dict()
        else:
            try:
                self.user_data = json.load(user_file)
            except ValueError:
                logger.warning("User data file could not load.")
                self.reset_user_dict()
        
        # Check all entries
        if self.check_entries():
            self.reset_user_dict()
            #QCoreApplication.processEvents()
        
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
        self.grid_layout = QGridLayout()
        
        self.inputs["State/Province"] = QComboBox()
        self.inputs["State/Province"].addItems(state_names.values())
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

        # ["Last Name",
        #  "First Name",
        #  "Title",
        #  "Company",
        #  "Address 1",
        #  "Address 2",
        #  "City",
        #  "State",
        #  "Zip",
        #  "Country",
        #  "Phone",
        #  "TruckCRYPT Web Site",
        #  "TruckCRYPT Web Public Key File",
        #  "User Private Key File",
        #  "User Public Key File"]

        self.grid_layout.addWidget(self.labels["First Name"],       0, 0, 1, 1)
        self.grid_layout.addWidget(self.inputs["First Name"],       0, 1, 1, 1)
            
        self.grid_layout.addWidget(self.labels["Last Name"],        0, 2, 1, 1)
        self.grid_layout.addWidget(self.inputs["Last Name"],        0, 3, 1, 3)
            
        self.grid_layout.addWidget(self.labels["Title"],            1, 0, 1, 1)
        self.grid_layout.addWidget(self.inputs["Title"],            1, 1, 1, 1)
            
        self.grid_layout.addWidget(self.labels["E-mail"],           1, 2, 1, 1)
        self.grid_layout.addWidget(self.inputs["E-mail"],           1, 3, 1, 3)
              
        self.grid_layout.addWidget(self.labels["Company"],          2, 0, 1, 1)
        self.grid_layout.addWidget(self.inputs["Company"],          2, 1, 1, 5)
            
        self.grid_layout.addWidget(self.labels["Address 1"],        3, 0, 1, 1)
        self.grid_layout.addWidget(self.inputs["Address 1"],        3, 1, 1, 5)
            
        self.grid_layout.addWidget(self.labels["Address 2"],        4, 0, 1, 1)
        self.grid_layout.addWidget(self.inputs["Address 2"],        4, 1, 1, 5)
            
        self.grid_layout.addWidget(self.labels["City"],             5, 0, 1, 1)
        self.grid_layout.addWidget(self.inputs["City"],             5, 1, 1, 1)
            
        self.grid_layout.addWidget(self.labels["State/Province"],   5, 2, 1, 1)
        self.grid_layout.addWidget(self.inputs["State/Province"],   5, 3, 1, 1)
        
        self.grid_layout.addWidget(self.labels["Postal Code"],      5, 4, 1, 1)
        self.grid_layout.addWidget(self.inputs["Postal Code"],      5, 5, 1, 1)
            
        self.grid_layout.addWidget(self.labels["Country"],          6, 0, 1, 1)
        self.grid_layout.addWidget(self.inputs["Country"],          6, 1, 1, 1)
        
        self.grid_layout.addWidget(self.labels["Phone"],            6, 2, 1, 1)
        self.grid_layout.addWidget(self.inputs["Phone"],            6, 3, 1, 1)
        
        self.inputs["TruckCRYPT Web Site"].setToolTip("Enter the URL for the TruckCRYPT web portal to decrypt, decode, store, and verify your data package files.")
        self.grid_layout.addWidget(self.labels["TruckCRYPT Web Site"], 7, 0, 1, 3),
        self.grid_layout.addWidget(self.inputs["TruckCRYPT Web Site"], 8, 0, 1, 5)

        web_public_key_file_button = QPushButton("Select File")
        web_public_key_file_button.setToolTip("Browse to the file that was sent to you when you activated your account.")
        web_public_key_file_button.clicked.connect(self.find_web_key)
        self.grid_layout.addWidget(web_public_key_file_button,                    10, 5, 1, 1)
        self.grid_layout.addWidget(self.labels["TruckCRYPT Web Public Key File"],  9, 0, 1, 3),
        self.grid_layout.addWidget(self.inputs["TruckCRYPT Web Public Key File"], 10, 0, 1, 5)
        self.inputs["TruckCRYPT Web Public Key File"].setToolTip("This file is needed so you can have encrypted and authenticated communications with the TruckCRYPT Server.")

        user_private_key_file_button = QPushButton("Select File")
        user_private_key_file_button.clicked.connect(self.find_user_private_key)
        self.grid_layout.addWidget(user_private_key_file_button,         12, 5, 1, 1)
        self.grid_layout.addWidget(self.labels["User Private Key File"], 11, 0, 1, 3),
        self.grid_layout.addWidget(self.inputs["User Private Key File"], 12, 0, 1, 5)
        self.inputs["User Private Key File"].setToolTip("This private key is your secret. TruckCRYPT uses this key to digitally sign files that are attributed to you. Therefore, you must never share this key.")

        user_public_key_file_button = QPushButton("Select File")
        user_public_key_file_button.clicked.connect(self.find_user_public_key)
        self.grid_layout.addWidget(user_public_key_file_button,         14, 5, 1, 1)
        self.grid_layout.addWidget(self.labels["User Public Key File"], 13, 0, 1, 3)
        self.grid_layout.addWidget(self.inputs["User Public Key File"], 14, 0, 1, 5)
        self.inputs["User Public Key File"].setToolTip("TruckCRYPT uses this key to verify digitally signed files that you signed with the private key. Therefore, you should share this key so others can verify your signature.")

        self.grid_layout.addWidget(self.buttons, 15, 2, 1, 3)

        self.setLayout(self.grid_layout)

        self.setWindowTitle("Enter User Information")
        self.setWindowModality(Qt.ApplicationModal)      

    def find_user_private_key(self):
        fname = QFileDialog.getOpenFileName(self, 
                                            'Find User Private Key File',
                                            os.getcwd(),
                                            "PEM Files (*.pem)",
                                            "PEM Files (*.pem)")
        if fname[0]:
            self.inputs["User Private Key File"].setText(fname[0])
    
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
                                            'Find TruckCRYPT Web Public Key File', 
                                            os.getcwd(), 
                                            "PEM Files (*.pem)", 
                                            "PEM Files (*.pem)")
        if fname[0]:
            self.inputs["TruckCRYPT Web Public Key File"].setText(fname[0])

    def show_dialog(self):

        for label in self.required_user_keys:
            
            try:
                self.inputs[label].setText(self.user_data[label])
            except AttributeError: #Then it is a QCombobox
                try:
                    idx = self.inputs[label].findText(self.user_data[label])
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
                self.user_data[label] = self.inputs[label].currentText()
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
