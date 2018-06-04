from reportlab.pdfgen import canvas as main_canvas
from reportlab.platypus import PageBreak
from reportlab.platypus.frames import Frame
from reportlab.platypus import PageTemplate, Flowable, FrameBreak, KeepTogether, PageBreak
from reportlab.platypus import Paragraph, Preformatted, Spacer, Image
from reportlab.platypus import BaseDocTemplate, SimpleDocTemplate
from reportlab.platypus import Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.lib.units import inch
from reportlab.lib.styles import PropertySet, getSampleStyleSheet
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.rl_config import defaultPageSize
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from io import BytesIO
from pdfrw import PdfReader, PdfDict
from pdfrw.buildxobj import pagexobj
from pdfrw.toreportlab import makerl
import string
import os
import traceback
import sys
import time
import json
import pgpy
from pgpy.constants import (PubKeyAlgorithm, 
                            KeyFlags, 
                            HashAlgorithm, 
                            SymmetricKeyAlgorithm, 
                            CompressionAlgorithm, 
                            EllipticCurveOID, 
                            SignatureType)

import logging
logger = logging.getLogger(__name__)

#Simple table style that makes a table with an inner grid, with a thick line below the header.
FLAReportTableStyle = TableStyle([('BOX', (0,0), (-1,-1), 0.25, colors.black),
                                  ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                                  ('LINEABOVE', (0,1), (-1,1), 0.75, colors.black),
                                  ('LINEABOVE', (0, 'splitfirst'), (-1, 'splitfirst'), 0.75, colors.black),
                              ])

FLAReportHeaderlessTableStyle = TableStyle([('BOX', (0,0), (-1,-1), 0.25, colors.black),
                                            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                                        ])

J1939PGNTableStyle = TableStyle([('BOX', (0,0), (-1, -1), 0.25, colors.black),#Border box
                                 ('LINEBELOW', (0, 'splitlast'), (-1, 'splitlast'), 0.25, colors.black)],#draw bottom line if table splits
                            )

def time_string(timestamp):
    try:
        return time.strftime("%a, %d %b %Y %H:%M:%S %z",time.localtime(timestamp))
    except TypeError:
        return "time not given"

def clean_string(value):
    try:
        return ''.join(s for s in value if s in string.printable)
    except:
        return repr(value)

def hours_min_sec(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return "%d:%02d:%02d" % (h, m, s)

component_information_description = '''The TruckCRYPT Software performs a so-called role-call when it is connected to a vehicle. The role-call process sends out request messages on the different vehicle networks and asks all modules for identifying information like make, model, serial number, software identification, and vehicle indentification number. These data are requested from each module on the networks. Not every module will respond to the requests. Modules are identified by their source address (SA) on J1939 networks and by their message identifier (MID) on J1587 networks. The interpretation of these identifiers is based on the J1939 and J1587 standards. Often the engine retarder controlling application runs in the engine control module and will share some of the same component information. The data shown in this section is a direct rendering of the byte stream from the network and no interpretation is given.
'''

component_information_reference = '''For more information regarding the parameters in this section, please look up the meanings associated with the following J1939 PGNs: <b>65242</b>, <b>65259</b>, and <b>65260</b> and the following J1587 PIDs: <b>233</b>, <b>234</b>, <b>237</b>, <b>243</b>. Additinally, the VIN can be sourced from the unified diagnostic services (UDS), which is described in Table C.1 of ISO 14229-1.'''

time_records_description = ['''Time is tracked by computers and electronic control units by counting the number of seconds from a defined epoch. There are two common epochs used with heavy vehicles: 1) the UNIX epoch of January 1, 1970 at midnight UTC, and 2) the J1587 epoch of January 1, 1985 at midnight UTC. Local times are expressed and displayed in terms of a timezone; however, most computers keep track of time using Universal Coordinated Time (UTC). The TruckCRYPT software treats all ECU times as UTC. All math related to times is done using UTC and results may be displayed in local time (i.e. with timezone information.''', '''Many electronic control units use a small battery to keep time when the power to the ECU is turned off. However, this battery may eventually run out, which means the real time clock (RTC) on the ECU is not able to keep accurate time. This symptom manifests itself as a date that seems unreasonable. Typical RTCs will have drift and not reflect accurate time. This is accounted for by recording the PC time (which is assumed accurate) at the same time the vehicle network message containing real time information reaches the TruckCRYPT software. A GPS system, if available, can provide external time references that are not subject to change.''']

ecu_time_records_description = '''Many electronic control units will keep track of the time it is operating. This is often an internal counter that increments one count per second. There are two common counters: one for the number of seconds that pass with the ingition key switch in the on position, and the other is for the number of seconds that the engine speed is greater than zero. Some of these times can be reset based on a trip reset event.'''

distance_records_description = '''Distance information is kept using a counter that increments with pulses from a pickup sensor. Usually a magnetic pickup sensor, called the Vehicle Speed Sensor (VSS), is located on the tail-shaft near the rear of the transmission. Additionally, discrete wheel speed sensors are used by the electronic brake controller to determine individual wheel speeds. These sensors detect pulses from the changing magnetic flux associated with the gaps in a rotating tone ring. Using a parameter based on tire size, these pulses can be converted to a distance. Speed is determined by counting the number of pulses in a given amount of time and converting that rate to engineerinig units. The distance calculated is tracked with different resolutions based on J1939 parameters. The information in this section is based on J1939 PGN 65217 and 65248 as well as J1587 PID 244 and 245. After a while, the different sources for distance information may not report the same value due to rounding and truncation errors.'''

gps_records_description = '''GPS Description.'''

pgn_records_description = '''This section contains the raw hexadecmial representation of the network traffic from the J1939 network. Different control applications (CAs) can use the same parameter group number (PGN) but each CA has its own source address (SA). The table below displays all the J1939 parameters that were seen on the network. Most of the J1939 values do not change with time during a typical download; however, some paramters, like time update during the session. The table below lists the message traffic for the messages that were last seen. Messages that are more than 8 bytes are shown as the result of assembling the transport layer CAN frames into defined J1939 messages. The human readable values from the raw hexadecimal are displayed in the Suspect Parameter Number Table.'''

spn_records_description = '''SPN Description'''

j1587_records_description = '''J1587 Message description'''

j1587_faults_description = '''A = Active, I = Inactive'''

network_log_description = '''Network logs are files that containing all of the vehicle network traffic. For heavy vehicles there are two networks that are commonly used: 1) Controller Area Network (CAN) and 2) J1708, which is an older protocol based on RS485. The RP1210 compliant Vehicle Diagnostic Adapter is set up to receive all CAN and J1708 messages. These messages are stored in separate files. The J1708 log file is text based and the CAN file is a binary file. The hash digest values are calculated based on the SHA-256 algorithm.'''

signature_description = '''The file contents are signed and verified.'''

module_directory = os.path.split(__file__)[0]

class FLAReportTemplate(SimpleDocTemplate):
    '''
    Root class for Forensic Link Adapter ReportLab report. Gathers sections and renders them into a pdf file.
    '''

    def __init__(self, parent, icon_file="logo.pdf", **kwargs):
        if kwargs.get('pagesize', None) is not None:
            self.pagesize = kwargs.pop('pagesize')
        else:
            self.pagesize = letter

        self.root = parent

        self.descriptor = "Heavy Vehicle"
        self.author = "Student CyberTruck Experience {}".format(time.strftime("%Y"))
        
        
        self.total_pages = 0

        self.logo_file = icon_file
        logger.debug("Using logo file in PDF: {}".format(self.logo_file))

        # Set Up styles for the Document
        self.styles = getSampleStyleSheet()
        
        
        self.toc = TableOfContents()
        self.toc.levelStyles = [
            PS(fontSize=14, name='TOCHeading1',
                leftIndent=20, firstLineIndent=-20, spaceBefore=5, leading=16),
            PS(fontSize=12, name='TOCHeading2',
                leftIndent=40, firstLineIndent=-20, spaceBefore=0, leading=12),
            PS(fontSize=10, name='TOCHeading3',
                leftIndent=60, firstLineIndent=-20, spaceBefore=0, leading=12),
            PS(fontSize=10, name='TOCHeading4',
                leftIndent=100, firstLineIndent=-20, spaceBefore=0, leading=12),
            ]
        self.table_options = [('GRID',(0,0), (-1,-1), 0.5, colors.black),
                              ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                              ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]
        self.event_groups={}

    def afterFlowable(self, flowable):
        "Registers TOC entries."
        if flowable.__class__.__name__ == 'Paragraph':
            text = flowable.getPlainText()
            style = flowable.style.name
            if style == 'Heading1':
                self.notify('TOCEntry', (0, text, self.page))
            elif style == 'Heading2':
                self.notify('TOCEntry', (1, text, self.page))
            elif style == 'Heading3':
                self.notify('TOCEntry', (2, text, self.page))

    def go(self, pgp_message, outputfilename):
        '''
        Loads a data package and parses it.
        This function builds and the story and produces it.
        It follows along in order of the PDF.
        '''
        SimpleDocTemplate.__init__(self, outputfilename,
                                   pagesize=self.pagesize,
                                   showBoundary=0,
                                   leftMargin=0.5*inch,
                                   rightMargin= 0.5*inch,
                                   topMargin=1.1*inch,
                                   bottomMargin=0.6*inch,
                                   allowSplitting=1,
                                   title="{} Data Report".format(self.descriptor),
                                   author=self.author,
                                   _pageBreakQuick=1,
                                   encrypt=None)
        
        table_options = self.table_options
        
        self.data_package = json.loads(pgp_message.message)
        self.datafilename = self.data_package["File Name"]

         #Extract header and footer data for each page.
        try:
            self.VIN = self.data_package["Component Information"]["Engine #1 on J1587"]["VIN"].strip('*')
        except:
            self.VIN = "Not Provided"
            try:
                self.VIN = self.data_package["Component Information"]["Engine #1 on J1939"]["VIN"].strip('*')
            except:
                self.VIN = "Not Provided"

        try:
            self.make = self.data_package["Component Information"]["Engine #1 on J1587"]["Make"].strip('*')
        except:
            self.make = "Not Provided"
            try:
                self.make = self.data_package["Component Information"]["Engine #1 on J1939"]["Make"].strip('*')
            except:
                self.make = "Not Provided"

        try:
            self.model = self.data_package["Component Information"]["Engine #1 on J1587"]["Model"].strip('*')
        except:
            self.model = "Not Provided"
            try:
                self.model = self.data_package["Component Information"]["Engine #1 on J1939"]["Model"].strip('*')
            except:
                self.model = "Not Provided"
        
        try:
            self.serial = self.data_package["Component Information"]["Engine #1 on J1587"]["Serial"].strip('*')
        except:
            self.serial = "Not Provided"
            try:
                self.serial = self.data_package["Component Information"]["Engine #1 on J1939"]["Serial"].strip('*')
            except:   
                self.serial = "Not Provided"
        try: 
            self.download_date = time_string(self.data_package["Time Records"]["Permission Time"])
        except KeyError:
            #print(traceback.format_exc())
            self.download_date = "Not Provided"
        
        # Build the story 
        self.story = []
        self.story.append(Paragraph("{} Data Report".format(self.descriptor), self.styles['title']))
        
        centered_normal_style = PS(name='centered', alignment=TA_CENTER)
        self.story.append(Paragraph("Report Creation Date: {}".format(time.strftime("%A, %B %d, %Y")), centered_normal_style))

        user_style = PS(name='user', fontName="Helvetica-Bold", fontSize=14, spaceAfter=12)
        self.story.append(Paragraph("User Information", user_style))
        if len(self.data_package["User Data"]["Company"]) > 0:
            company = self.data_package["User Data"]["Company"]
        else:
            company = "No organization information provided."
        self.story.append(Paragraph(company, self.styles['Normal']))
        
        name = "{} {}".format(self.data_package["User Data"]["First Name"],
                              self.data_package["User Data"]["Last Name"])
        if len(self.data_package["User Data"]["Title"]) > 0:
            name += ", {}".format(self.data_package["User Data"]["Title"])
        if name == " ":
            name = "No name information provided."
        self.story.append(Paragraph(name, self.styles['Normal']))

        if len(self.data_package["User Data"]["Address 1"]) > 0:
            self.story.append(Paragraph(self.data_package["User Data"]["Address 1"], self.styles['Normal']))
        else: 
            self.story.append(Paragraph("No address information available.", self.styles['Normal']))
        if len(self.data_package["User Data"]["Address 2"]) > 0:
            self.story.append(Paragraph(self.data_package["User Data"]["Address 2"], self.styles['Normal']))
        city = "{}, {}  {}".format(self.data_package["User Data"]["City"],
                                   self.data_package["User Data"]["State/Province"],
                                   self.data_package["User Data"]["Postal Code"])
        self.story.append(Paragraph(city, self.styles['Normal']))
        self.story.append(Paragraph("Phone: " + self.data_package["User Data"]["Phone"], self.styles['Normal']))
        try:
            self.story.append(Paragraph("E-mail: " + self.data_package["User Data"]["E-mail"], self.styles['Normal']))
        except:
            self.story.append(Paragraph("E-mail missing", self.styles['Normal']))
        # Insert the table of contents.
        h1_no_toc_style = PS(name='h1', fontSize=14, spaceBefore=12, fontName='Helvetica-Bold')
        self.story.append(Paragraph("Table Of Contents", h1_no_toc_style))
        self.story.append(self.toc)
        #self.story.append(PageBreak())

        
        main_key = "Component Information"
        section_title = main_key
        self.add_information_section(main_key, section_title, component_information_description)
        
        #Event Data
        self.story.append(Spacer(0.2,0.4*inch))
        self.story.append(Paragraph("Event Data", self.styles["Heading1"]))
        self.story.append(Paragraph("This is an event data description", self.styles["Normal"]))
        #print("self.event_groups =")
        #print(self.event_groups)
        if len(self.event_groups) > 0:
            for key, value in self.event_groups.items():
                self.story.append(PageBreak())
                self.story.append(Paragraph(key, self.styles["Heading2"]))
                self.story.append(value)
        else:
            self.story.append(Spacer(0.2,0.4*inch))
            self.story.append(Paragraph("No Event Data is available for this report.", self.styles["Normal"]))




        # Time Records for Realtime Clocks
        self.story.append(PageBreak())
        self.story.append(Paragraph("Real Time Records", self.styles["Heading1"]))
        for p in time_records_description:
            self.story.append(Paragraph(p, self.styles["Normal"]))
            self.story.append(Spacer(0.2,0.2*inch))
        pc_time_keys = ["Permission Time", 
                        "Last GPS Time",  
                        "PC Time at Last GPS Reading", 
                        "Last PC Time"]
        bold_style = PS(fontName="Helvetica-Bold", name='normal_bold')
        time_data = [[Paragraph("Description",bold_style),
                      Paragraph("UNIX Timestamp",bold_style),
                      Paragraph("Local Time Value",bold_style)]]
        for key in pc_time_keys:
            try:
                timestamp = int(self.data_package["Time Records"][key])
            except (TypeError, KeyError):
                timestamp = "Data Not Obtained."
            if 'minus' in key:
                time_data.append([key,
                              "{}".format(timestamp),
                              hours_min_sec(timestamp)])
            else:
                time_data.append([key,
                              "{}".format(timestamp),
                              time_string(timestamp)
                              ])
       
        self.story.append(Paragraph("System Reference Times", self.styles["Heading2"]))
        self.story.append(Paragraph("The following values were obtained through the computer running the software.", self.styles['Normal']))
        time_table = Table(time_data, repeatRows=1, colWidths='*')
        self.story.append(time_table)

        self.story.append(Spacer(0.2,0.2*inch))
        self.story.append(Paragraph("The following values are calculated based on the data in the previous table.", self.styles['Normal']))
        
        time_data = [[Paragraph("Description", bold_style),
                      Paragraph("Total Seconds", bold_style),
                      Paragraph("Hours:Minutes:Seconds", bold_style)]]
        key="PC Time minus GPS Time"
        try:
            diff = int(self.data_package["Time Records"][key])
            time_data.append([key,
                          "{}".format(diff),
                          hours_min_sec(diff)
                          ])
        except (TypeError, KeyError):
            diff = "GPS Time Data Not Available."
        try:
            duration = int(self.data_package["Time Records"]["Last PC Time"] - 
                        self.data_package["Time Records"]["Permission Time"])
        except (TypeError, KeyError):
            duration = int(self.data_package["Time Records"]["Last PC Time"] - 
                        self.data_package["Time Records"]["PC Start Time"])  
        time_data.append(["Download Duration",
                          "{:d}".format(duration),
                          hours_min_sec(duration)
                          ])
        time_table = Table(time_data, repeatRows=1, colWidths='*')
        self.story.append(time_table)
        
        self.story.append(Paragraph("Electronic Control Unit Times", self.styles["Heading2"]))
        self.story.append(Paragraph("The information in this section is based on the real-time clock data from the different vehicle networks. For J1939, PGN 65254 is used to interpret real time values. Parameter Identfiers 251 and 252 are used to interpret times from the J1587 network.", self.styles['Normal']))
        for key, value in sorted(self.data_package["Time Records"].items()):
            if "J1939" in key or "J1587" in key:
                try:
                    if len(value) > 0:
                        self.story.append(Paragraph(key, self.styles["Heading3"]))
                        for key1, value1 in sorted(value.items()):
                            if 'minus' in key1:
                                self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {:d} seconds ({})</para>".format(key1,int(value1),hours_min_sec(int(value1))), self.styles["Normal"]))
                            elif 'Last ECM Time' in key1:
                                self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {:d} seconds from epoch, or {}</para>".format(key1, int(value1), time_string(value1)), self.styles["Normal"]))
                            else:
                                self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {}</para>".format(key1,value1), self.styles["Normal"]))
                except TypeError:
                    pass

        main_key = "ECU Time Information"
        section_title = main_key
        self.add_information_section(main_key, section_title, ecu_time_records_description)

        main_key = "Distance Information"
        section_title = main_key
        self.add_information_section(main_key, section_title, distance_records_description)

        main_key = "GPS Data"
        self.story.append(PageBreak())
        self.story.append(Paragraph("External Reference GPS Data", self.styles["Heading1"]))
        self.story.append(Paragraph(gps_records_description, self.styles["Normal"]))
        self.story.append(Spacer(0.2,0.2*inch))
        for key,value in self.data_package[main_key].items():
            if 'Time' in key:
                try:
                    timestamp = int(value)
                    value_string = "{:d} seconds from the epoch, or {}".format(timestamp,time_string(timestamp))
                except (TypeError, KeyError):
                    value_string = "Not Available"
                self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {}</para>".format(key,value_string), self.styles["Normal"]))
            else:
                self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {}</para>".format(key,value), self.styles["Normal"]))

        #self.story.append(Spacer(0.2,0.2*inch))       
        self.story.append(PageBreak())
        self.story.append(Paragraph("J1939 Messages by Parameter Group Number", self.styles["Heading1"]))
        self.story.append(Paragraph(pgn_records_description, self.styles["Normal"]))
        self.story.append(Spacer(0.2,0.2*inch))       
        page_width = 7.5 * inch
        col_widths = [.08*page_width,.12*page_width, .30*page_width, .05*page_width, .20*page_width, .25*page_width]
        j1939pgn_data=[[Paragraph("<b>PGN</b>", self.styles["Normal"]),
                        Paragraph("<b>Acronym</b>", self.styles["Normal"]),
                        Paragraph("<b>Parameter Group Name</b>", self.styles["Normal"]),
                        Paragraph("<b>SA</b>", self.styles["Normal"]),
                        Paragraph("<b>Source</b>", self.styles["Normal"]),
                        Paragraph("<b>Message Hexadecimal</b>", self.styles["Normal"])]]

        for key,value in self.data_package["J1939 Parameter Group Numbers"].items():
            pgn = Paragraph(value["PGN"], self.styles["Normal"])
            acronym = Paragraph(value["Acronym"], self.styles["Normal"])
            name = Paragraph(value["Parameter Group Label"], self.styles["Normal"])
            sa = Paragraph(value["SA"], self.styles["Normal"])
            Source = Paragraph(value["Source"], self.styles["Normal"])
            raw = Paragraph(value["Raw Hexadecimal"], self.styles["Normal"])
            j1939pgn_data.append([pgn,acronym,name,sa,Source,raw])
        


        table_style = TableStyle(self.table_options)
        

        j1939pgn_table = Table(j1939pgn_data, repeatRows=1, colWidths=col_widths)
        j1939pgn_table.setStyle(table_style)
        self.story.append(j1939pgn_table)

        self.story.append(Paragraph("Parameter Group Numbers Not Included", self.styles["Heading3"]))
        self.story.append(Spacer(0.1,0.1*inch))
        page_width = 6.5 * inch
        col_widths = [.1*page_width,.90*page_width]
        j1939pgn_exclude=[[Paragraph("<b>PGN</b>", self.styles["Normal"]),
                           Paragraph("<b>Parameter Group Name</b>", self.styles["Normal"])]]
        try:
            for pgn in sorted(self.root.J1939.pgns_to_not_decode):
                pgn_entry = Paragraph(str(pgn), self.styles["Normal"])
                name_entry = Paragraph(self.root.J1939.get_pgn_label(pgn), self.styles["Normal"])
                j1939pgn_exclude.append([pgn_entry, name_entry])
            j1939exclude_table = Table(j1939pgn_exclude, repeatRows=1, colWidths=col_widths)
            j1939exclude_table.setStyle(table_style)
            self.story.append(j1939exclude_table)
        except AttributeError:
            logger.debug(traceback.format_exc())
        # SPNs
        #self.story.append(Spacer(0.2,0.2*inch))       
        self.story.append(PageBreak())
        self.story.append(Paragraph("J1939 Suspect Parameter Number Values", self.styles["Heading1"]))
        self.story.append(Paragraph(spn_records_description, self.styles["Normal"]))
        self.story.append(Spacer(0.2,0.2*inch))       
        page_width = 7.5 * inch
        col_widths = [.065*page_width,.26*page_width, .075*page_width, .20*page_width, .15*page_width, .1*page_width, .15*page_width]
        j1939spn_data=[[Paragraph("<b>SPN</b>", self.styles["Normal"]),
                        Paragraph("<b>SPN Name</b>", self.styles["Normal"]),
                        Paragraph("<b>PGN</b>", self.styles["Normal"]),
                        Paragraph("<b>Source</b>", self.styles["Normal"]),
                        Paragraph("<b>Value</b>", self.styles["Normal"]),
                        Paragraph("<b>Units</b>", self.styles["Normal"]),\
                        Paragraph("<b>Meaning</b>", self.styles["Normal"])]]
        dict1=self.data_package["J1939 Suspect Parameter Numbers"]
        for value in sorted(dict1.values(), key=lambda x: x["Suspect Parameter Number Label"]):
            meaning = value["Meaning"]
            if 'Out' not in meaning:
                pgn = Paragraph(value["PGN"], self.styles["Normal"])
                name = Paragraph(value["Suspect Parameter Number Label"], self.styles["Normal"])
                spn = Paragraph(value["SPN"], self.styles["Normal"])
                Source = Paragraph(value["Source"], self.styles["Normal"])
                units = Paragraph(value["Units"], self.styles["Normal"])
                val = Paragraph(value["Value"], self.styles["Normal"])
                mean_par = Paragraph(value["Meaning"], self.styles["Normal"])
                j1939spn_data.append([spn,name,pgn,Source,val,units, mean_par])
        j1939spn_table = Table(j1939spn_data, repeatRows=1, colWidths=col_widths)
        j1939spn_table.setStyle(table_style)
        self.story.append(j1939spn_table)

        self.story.append(PageBreak())
        self.story.append(Paragraph("J1587 Network Message Values", self.styles["Heading1"]))
        self.story.append(Paragraph(j1587_records_description, self.styles["Normal"]))
        self.story.append(Spacer(0.2,0.2*inch))   

        
        col_widths = [.06*page_width,.06*page_width, .24*page_width, .20*page_width, .10*page_width, .34*page_width]
        j1587_data=[[Paragraph("<b>MID</b>", self.styles["Normal"]),
                     Paragraph("<b>PID</b>", self.styles["Normal"]),
                     Paragraph("<b>Parameter Name</b>", self.styles["Normal"]),
                     Paragraph("<b>Value</b>", self.styles["Normal"]),
                     Paragraph("<b>Units</b>", self.styles["Normal"]),
                     Paragraph("<b>Meaning</b>", self.styles["Normal"])]]
        dict1=self.data_package["J1587 Message and Parameter IDs"]
        mids ={}
        diag_code = {}
        row_count = 1
        for value in sorted(dict1.values(), key=lambda x: x["Parameter Identification"]):
            mids[value["MID"]] = value["Message Identification"]
            mid = Paragraph(value["MID"], self.styles["Normal"])
            pid = Paragraph(value["PID"], self.styles["Normal"])
            name = Paragraph(value["Parameter Identification"], self.styles["Normal"])
            units = Paragraph(value["Units"], self.styles["Normal"])
            val = Paragraph(value["Value"], self.styles["Normal"])
            if '194' in value["PID"]:
                diag_code[value["MID"]]={'meaning': value["Meaning"].split('\n'), 'name':value["Message Identification"]}
                mean_par = Paragraph("See Below", self.styles["Normal"])
            else:
                meaning_table = []
                meaning_vals = value["Meaning"].split('\n')
                for m in meaning_vals:
                    meaning_table.append([Paragraph(m, self.styles["Normal"])])
                mean_par = Table(meaning_table, colWidths=[col_widths[-1] - 0.1*inch])
            if len(value['Units']) == 0 and len(value["Meaning"]) == 0:
               table_options = self.table_options
               table_options.append(('SPAN', (3,row_count), (5,row_count))) 
            j1587_data.append([mid,pid,name,val,units, mean_par])
            row_count+=1
        table_style = TableStyle(table_options)
        j1587_table = Table(j1587_data, repeatRows=1, colWidths=col_widths)
        j1587_table.setStyle(table_style)
        self.story.append(j1587_table)
        legend_text = "Message Identifier (MID) Legend:"
        for key,val in sorted(mids.items()):
            legend_text += "  {} = {};".format(key,val)
        self.story.append(Paragraph(legend_text[:-1], self.styles["Normal"] ))
        self.story.append(Spacer(0.2,0.2*inch))       
        self.story.append(Paragraph("J1587 Fault Code Data (PID 194)", self.styles["Heading2"]))
        self.story.append(Paragraph(j1587_faults_description, self.styles["Normal"]))
        
        for key,val in diag_code.items():
            self.story.append(Paragraph("Diagnostic Codes for {} (MID {})".format(val['name'],key), self.styles["Heading3"]))
            diag_table = []
            meaning_vals = val["meaning"]
            for m in meaning_vals:
                diag_table.append([Paragraph(m, self.styles["Normal"])])
            self.story.append(Table(diag_table, colWidths=None))

        
        self.story.append(PageBreak())
        self.story.append(Paragraph("Forensic Context Information", self.styles["Heading2"]))
        
        main_key = "Network Logs"
        self.story.append(Spacer(0.2,0.3*inch))
        self.story.append(Paragraph(main_key, self.styles["Heading2"]))
        self.story.append(Paragraph(network_log_description, self.styles["Normal"]))
        self.story.append(Spacer(0.2,0.2*inch))
        try:
            for key,value in self.data_package[main_key].items():
                self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {}</para>".format(key,value), self.styles["Normal"]))
        except KeyError:
            self.story.append(Paragraph("{} is not available.".format(main_key), self.styles["Normal"]))
        self.story.append(Paragraph("{} Data File Information".format(self.descriptor), self.styles["Heading2"]))
        key = "File Name"
        value = self.data_package[key]
        self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {}</para>".format(key,value), self.styles["Normal"]))
        
        key = "File Format"
        value = self.data_package[key]
        try:
            self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {}.{}</para>".format(key,value['major'],value['minor']), self.styles["Normal"]))
        except TypeError:
            self.story.append(Paragraph("{} is not available.".format(key), self.styles["Normal"]))

        key = "Machine UUID"
        value = self.data_package[key]
        self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {}</para>".format(key,value), self.styles["Normal"]))
        
        key = "Harddrive UUID"
        value = self.data_package[key]
        self.story.append(Paragraph("<para leftIndent=20><b>{}:</b> {}</para>".format(key,value), self.styles["Normal"]))

        key = "Signatures"
        self.story.append(Paragraph("<para leftIndent=20><b>{}:</b></para>".format(key), self.styles["Normal"]))
        for sig in pgp_message.signatures:
            for value in str(sig).split('\n'):
                self.story.append(Paragraph("<para leftIndent=30>{}</para>".format(value), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>cipherprefs:    {}</para>".format(sig.cipherprefs), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>compprefs:      {}</para>".format(sig.compprefs), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>created:        {}</para>".format(sig.created), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>expires_at:     {}</para>".format(sig.expires_at), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>exportable:     {}</para>".format(sig.exportable), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>features:       {}</para>".format(sig.features), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>hashprefs:      {}</para>".format(sig.hashprefs), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>hash_algorithm: {}</para>".format(str(pgpy.constants.HashAlgorithm(sig.hash_algorithm))), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>is_expired:     {}</para>".format(sig.is_expired), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>key_algorithm:  {}</para>".format(str(pgpy.constants.PubKeyAlgorithm(sig.key_algorithm))), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>key_flags:      {}</para>".format(sig.key_flags), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>keyserver:      {}</para>".format(sig.keyserver), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>keyserverprefs: {}</para>".format(sig.keyserverprefs), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>notation:       {}</para>".format(sig.notation), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>policy_uri:     {}</para>".format(sig.policy_uri), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>revocable:      {}</para>".format(sig.revocable), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>signer:         {}</para>".format(sig.signer), self.styles["Normal"]))
            self.story.append(Paragraph("<para leftIndent=50>type:           {}</para>".format(str(pgpy.constants.SignatureType(sig.type))), self.styles["Normal"]))

        # User Data

        # Build the PDF file with calls to functions for each page. Use multibuild for the Table of Contents    
        try:
            self.multiBuild(self.story, onFirstPage=self._on_first_page, onLaterPages=self._on_other_page)
            return "Success"
        except PermissionError:
            return "Permission Error. The PDF file may be open in another application. Please close it and try again."
    
    def chopLine(self, old_line, maxline):
        """
        Make sure lines don't go too long
        """
        try:
            new_line = old_line[0]
            for i in range(1,len(old_line)):
                new_line += old_line[i]
                if (i % maxline) == 0:
                    new_line+='\n'
            return new_line  
        except IndexError:
            return old_line
            
    def add_information_section(self, main_key, section_title, description):
        '''
        When the data_package dictionary has a section of dictionaries from different sources, we can
        use this function to add to the story line. 
        The main_key is the key in the dictionary. This may be the section_title too, but not necessary.
        The decription is a text blurb that is inserted just below the section heading.
        This function should work on displaying the following:
            Component Information
            ECU Times
            Distance Information
        '''
        self.story.append(PageBreak())
        self.story.append(Paragraph(main_key, self.styles["Heading1"]))
        self.story.append(Paragraph(description, self.styles["Normal"]))

        for key, value in sorted(self.data_package[main_key].items()):
            #logger.debug("{}: {}".format(key,value))
            if len(value) > 0:
                self.story.append(Paragraph(key, self.styles["Heading2"]))
                for key1, value1 in sorted(value.items()):
                    try:
                        if len(value1) > 0:
                            #logger.debug("{}: {}".format(key1,value1))
                            safe_val = self.chopLine("<para leftIndent=20><b>{}:</b> {}</para>".format(key1,clean_string(value1)),180)
                            #logger.debug("safe_val = {}".format(safe_val))
                            self.story.append(Paragraph(safe_val, self.styles["Normal"]))
                    except TypeError:
                        pass #none type doesn't need printed.

    def _on_first_page(self, canvas, doc):
        scale = 2
        img = PdfImage(self.logo_file,
                        width=scale*inch,
                        height=scale * 394/905 * inch)
        img.drawOn(canvas,
                   3 * inch, 
                   10 * inch)
        
        self._on_page(canvas, doc)            

    def _on_other_page(self, canvas, doc):
        scale = 1.5
        img = PdfImage(self.logo_file,
                        width=scale*inch,
                        height=scale * 394/905 * inch)
        img.drawOn(canvas,
                   6.5 * inch, 
                   10.0 * inch)
        canvas.setFont("Helvetica", 14)
        canvas.drawString(0.5 * inch, 
                          10.5 * inch, 
                          "{} Data Report".format(self.descriptor),
                          )
        canvas.setFont("Helvetica", 10)
        canvas.drawString(0.5 * inch, 
                          10.30 * inch, 
                          "VIN: {}".format(self.VIN)
                          )
        canvas.drawString(0.5 * inch, 
                          10.1 * inch, 
                          "Make: {}, Model: {}, S/N: {}".format(clean_string(self.make),
                                                                clean_string(self.model), 
                                                                clean_string(self.serial))
                          )
        self._on_page(canvas, doc)            

    def _on_page(self, canvas, doc):
    # ... do any additional page formatting here for each page
        
        if doc.page > self.total_pages:
            self.total_pages = doc.page
        else:
            canvas.setFont("Helvetica", 10)
            canvas.drawRightString(8 * inch, 
                              0.25 * inch, 
                              "Page {} of {}".format(doc.page, self.total_pages)
                              )
            canvas.drawString(0.5 * inch, 
                            0.45 * inch, 
                            "File: {}".format(self.datafilename)
                            )
            canvas.drawString(0.5 * inch, 
                            0.25 * inch, 
                            "Download Date: {}".format(self.download_date)
                            )

    def add_ddec_event_table(self, title, table_list):
        """
        A utility to accumulate chart data for events. Often these charts will be in chunks.
        """
        styles = getSampleStyleSheet()
        styleN = styles["BodyText"]
        #used alignment if required
        styleN.alignment = TA_LEFT

        logger.debug("Adding Table Data for {} to PDF.".format(title))
        #logger.debug(table_list)
        page_width = 7.5 * inch
        col_widths = [.065*page_width, 
                      .078*page_width, 
                      .08*page_width, 
                      .08*page_width, 
                      .08*page_width, 
                      .08*page_width, 
                      .085*page_width, 
                      .08*page_width, 
                      .08*page_width, 
                      .092*page_width, 
                      .08*page_width, 
                      .08*page_width, 
                      .08*page_width]
        formatted_table_list=[]
        for row in table_list:
            formatted_table_list.append([])
            for col_num in range(1,len(row)):
                try:
                    if "Accelerator Switch" in row[col_num]:
                        row[col_num] = "Accel. Switch"
                    elif "Diagnostic Code" in row[col_num]:
                        row[col_num] = "Diag. Code"
                except TypeError:
                    pass
                formatted_table_list[-1].append(Paragraph("{}".format(row[col_num]), styleN))

        try:
            table_object = Table(formatted_table_list, repeatRows=2, repeatCols=1, colWidths=col_widths )
            table_object.setStyle(TableStyle(self.table_options))
            self.event_groups[title] = table_object
        except ValueError:
            self.event_groups[title] = Paragraph("There was an error in generating a table. The data to build the table is as follows: {}".format(table_list), 
                                        self.styles['Normal'])

    def add_event_chart(self, title, img):      
        logger.debug("Adding Charts Data for {} to PDF.".format(title))
        self.event_groups[title] = PdfImage(img,width=7.5*inch, height=8.5*inch,)
        
        
        
class PdfImage(Flowable):
    """
    PdfImage wraps the first page from a PDF file as a Flowable
    which can be included into a ReportLab Platypus document.
    Based on the vectorpdf extension in rst2pdf (http://code.google.com/p/rst2pdf/)

    This can be used from the place where you want to return your matplotlib image
    as a Flowable:

        img = BytesIO()

        fig, ax = plt.subplots(figsize=(canvaswidth,canvaswidth))

        ax.plot([1,2,3],[6,5,4],antialiased=True,linewidth=2,color='red',label='a curve')

        fig.savefig(img,format='PDF')

        return(PdfImage(img))

    """

    def __init__(self, filename_or_object, width=None, height=None, kind='direct'):
        # If using StringIO buffer, set pointer to begining
        if hasattr(filename_or_object, 'read'):
            filename_or_object.seek(0)
        self.page = PdfReader(filename_or_object, decompress=False).pages[0]
        self.xobj = pagexobj(self.page)

        self.imageWidth = width
        self.imageHeight = height
        x1, y1, x2, y2 = self.xobj.BBox

        self._w, self._h = x2 - x1, y2 - y1
        if not self.imageWidth:
            self.imageWidth = self._w
        if not self.imageHeight:
            self.imageHeight = self._h
        self.__ratio = float(self.imageWidth)/self.imageHeight
        if kind in ['direct','absolute'] or width==None or height==None:
            self.drawWidth = width or self.imageWidth
            self.drawHeight = height or self.imageHeight
        elif kind in ['bound','proportional']:
            factor = min(float(width)/self._w,float(height)/self._h)
            self.drawWidth = self._w*factor
            self.drawHeight = self._h*factor

    def wrap(self, availableWidth, availableHeight):
        """
        returns draw- width and height

        convenience function to adapt your image 
        to the available Space that is available
        """
        return self.drawWidth, self.drawHeight

    def drawOn(self, canv, x, y, _sW=0):
        """
        translates Bounding Box and scales the given canvas
        """
        if _sW > 0 and hasattr(self, 'hAlign'):
            a = self.hAlign
            if a in ('CENTER', 'CENTRE', TA_CENTER):
                x += 0.5*_sW
            elif a in ('RIGHT', TA_RIGHT):
                x += _sW
            elif a not in ('LEFT', TA_LEFT):
                raise ValueError("Bad hAlign value " + str(a))

        xobj_name = makerl(canv, self.xobj)

        xscale = self.drawWidth/self._w
        yscale = self.drawHeight/self._h

        x -= self.xobj.BBox[0] * xscale
        y -= self.xobj.BBox[1] * yscale

        canv.saveState()
        canv.translate(x, y)
        canv.scale(xscale, yscale)
        canv.doForm(xobj_name)
        canv.restoreState()

def get_user_data(user_data):
    """
        Returns a Reportlab Flowable based on user data 
    """
    styles = getSampleStyleSheet()
    story = []
    
    if len(user_data["Company"]) > 0:
        company = user_data["Company"]
    else:
        company = "No organization information provided."
    story.append(Paragraph(company, styles['Normal']))
    
    name = "{} {}".format(user_data["First Name"],
                          user_data["Last Name"])
    if len(user_data["Title"]) > 0:
        name += ", {}".format(user_data["Title"])
    if name == " ":
        name = "No name information provided."
    story.append(Paragraph(name, styles['Normal']))

    if len(user_data["Address 1"]) > 0:
        story.append(Paragraph(user_data["Address 1"], styles['Normal']))
    else: 
        story.append(Paragraph("No address information available.", styles['Normal']))
    if len(user_data["Address 2"]) > 0:
        story.append(Paragraph(user_data["Address 2"], styles['Normal']))
    city = "{}, {}  {}".format(user_data["City"],
                               user_data["State/Province"],
                               user_data["Postal Code"])
    story.append(Paragraph(city, styles['Normal']))
    story.append(Paragraph("Phone: " + user_data["Phone"], styles['Normal']))
    try:
        story.append(Paragraph("E-mail: " + user_data["E-mail"], styles['Normal']))
    except:
        story.append(Paragraph("E-mail missing", styles['Normal']))
    return story

class SignatureVerificationReport(SimpleDocTemplate):
    '''
    Root class for a report. Gathers sections and renders them into a pdf file.
    The data dict needs to have the following keys:
     "Signer"
     "First File Bytes"
     "Last File Bytes"
     "Filename"
     "Signature File Name"
     "Signature"
     "Public Key"
     "Current Hash"

    '''

    def __init__(self, outputfilename, data_dict, **kwargs):
        if kwargs.get('pagesize', None) is not None:
            self.pagesize = kwargs.pop('pagesize')
        else:
            self.pagesize = letter

        if outputfilename[-4:].lower() == '.pdf':
            self.outputfilename = outputfilename
        else:
            self.outputfilename = outputfilename + '.pdf'

        SimpleDocTemplate.__init__(self, self.outputfilename,
                                   pagesize=self.pagesize,
                                   showBoundary=0,
                                   leftMargin=0.5*inch,
                                   rightMargin= 0.5*inch,
                                   topMargin=1.1*inch,
                                   bottomMargin=0.6*inch,
                                   allowSplitting=1,
                                   title="TruckCRYPT File Verification Report",
                                   author="Copyright {} Synercon Technologies, LLC".format(time.strftime("%Y")),
                                   _pageBreakQuick=1,
                                   encrypt=None)
        
        self.total_pages = 0

        # Set Up styles for the Document
        self.styles = getSampleStyleSheet()

        
        # Build the story 
        self.story = []
        self.story.append(Paragraph("Forensic File Verification Report", self.styles['title']))

        centered_normal_style = PS(name='centered', alignment=TA_CENTER)
        self.story.append(Paragraph("Report Creation Date: {}".format(time.strftime("%A, %B %d, %Y")), centered_normal_style))
        
        user_style = PS(name='user', fontName="Helvetica-Bold", fontSize=14, spaceAfter=12)
        self.story.append(Paragraph("File Signer Information", user_style))

        for flowable in get_user_data(data_dict["Signer"]):
            self.story.append(flowable)

        self.story.append(Paragraph("File Verification Procedure", self.styles["Heading3"]))
        self.story.append(Paragraph("A signature is an encrypted hash value of the bytes of the original file. The encryption is asymmetric, which means the signer can encrypt the hash value with their private key. This encrypted hash value is a signature and it can be decrypted with the matching public key. The file to be verified is loaded into memory as a byte stream and hashed using the same algorithm (SHA-256). The Digital Signature Service (DSS) based on the FIPS 186-3 uses elliptic curve cryptography (ECC) to verify the hash performed on the original file is the same as the current file.  If even one byte is altered the hash digest will be dramatically different, indicating the file was altered. The DSS ensures the signtature cannot be alterd to match an altered file. This guarantees the data is authentic.", self.styles["Normal"]))
        self.story.append(Spacer(0.2,0.2*inch))
        
        self.story.append(Paragraph("File to Verify", self.styles["Heading4"]))
        self.story.append(Paragraph("{}".format(data_dict["File Name"]), self.styles["Normal"]))
        self.story.append(Paragraph("File Contents (Raw Bytes)", self.styles["Heading4"]))
        self.story.append(Paragraph("{} ... ".format(data_dict["First File Bytes"]), self.styles["Normal"]))
        self.story.append(Paragraph("Signature File Name", self.styles["Heading4"]))
        self.story.append(Paragraph("{}".format(data_dict["Signature File Name"]), self.styles["Normal"]))
        self.story.append(Paragraph("Signature Byte String", self.styles["Heading4"]))
        self.story.append(Paragraph("{}".format(data_dict["Signature"]), self.styles["Normal"]))
        self.story.append(Paragraph("Signature Public Key", self.styles["Heading4"]))
        self.story.append(Paragraph("{}".format(data_dict["Public Key"]), self.styles["Normal"]))
        self.story.append(Paragraph("Original SHA-256 Hash Digest (Informational only)", self.styles["Heading4"]))
        self.story.append(Paragraph("The file is verified against its signature. The original content has not been altered.", self.styles["Heading3"]))

    def go(self):
        # Build the PDF file with calls to functions for each page. Use multibuild for the Table of Contents    
        try:
            self.build(self.story)
            return "Success"
        except PermissionError:
            return "Permission Error. Perhaps the PDF file is already open somewhere else. If so, please close it and try again."

if __name__ == '__main__':
    logger.debug("Running tests for generating PDFs for TruckCRYPT.")
    output = FLAReportTemplate(None)
    pgp_file_contents = pgpy.PGPMessage.from_file("Example Data.cpt")
    code = output.go(pgp_file_contents, "TestReport.pdf")
    print(code)
        