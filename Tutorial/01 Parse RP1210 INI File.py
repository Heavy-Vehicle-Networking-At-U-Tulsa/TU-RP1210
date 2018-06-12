# python
# 
try:
    with open("C:/windows/RP121032.ini") as ini:
        rp1210ini_lines = ini.readlines()
except FileNotFoundError:
    print("RP1210 file not found. Be sure RP1210 device drivers are installed.")
    exit()

#displays each line without the whitespace or newlines
for line in rp1210ini_lines:
    print(line.strip()) 

#Pick the second line and split it at the = sign    
APIImplementations = rp1210ini_lines[1].split("=")
print(APIImplementations)

#create a list of all the available DLLs
rp1210_vendors = APIImplementations[1].strip().split(',')
print("Pick from one of the following DLLs for your RP1210 adapter:")
i=0
for dll_name in rp1210_vendors:
    print("{:2d}: {}".format(i,dll_name))
    i+=1

# Assignment: Select the correct DLL to use with your device and
# store it as a variable. For example:
#    dll_in_use = rp1210_vendors[XX] 
# where XX is the appropriate index in the list