# Copyright 2015-2020 - RoboDK Inc. - https://robodk.com/
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# ----------------------------------------------------
# This file is a POST PROCESSOR for Robot Offline Programming to generate programs 
# for an Omron TM - Techman robot with RoboDK
#
# To edit/test this POST PROCESSOR script file:
# Select "Program"->"Add/Edit Post Processor", then select your post or create a new one.
# You can edit this file using any text editor or Python editor. Using a Python editor allows to quickly evaluate a sample program at the end of this file.
# Python should be automatically installed with RoboDK
#
# You can also edit the POST PROCESSOR manually:
#    1- Open the *.py file with Python IDLE (right click -> Edit with IDLE)
#    2- Make the necessary changes
#    3- Run the file to open Python Shell: Run -> Run module (F5 by default)
#    4- The "test_post()" function is called automatically
# Alternatively, you can edit this file using a text editor and run it with Python
#
# To use a POST PROCESSOR file you must place the *.py file in "C:/RoboDK/Posts/"
# To select one POST PROCESSOR for your robot in RoboDK you must follow these steps:
#    1- Open the robot panel (double click a robot)
#    2- Select "Parameters"
#    3- Select "Unlock advanced options"
#    4- Select your post as the file name in the "Robot brand" box
#
# To delete an existing POST PROCESSOR script, simply delete this file (.py file)
#
# ----------------------------------------------------
# More information about RoboDK Post Processors and Offline Programming here:
#     https://robodk.com/help#PostProcessor
#     https://robodk.com/doc/en/PythonAPI/postprocessor.html
# ----------------------------------------------------

### Important! Comments and/or empty lines are not supported: the whole program is not taken into account
#DEFAULT_HEADER_SCRIPT = """
#//--------------------------
#// Add your header or subprograms here
#
#//--------------------------
#"""

DEFAULT_HEADER_SCRIPT = ""

def TM_SendScript(script_code, robot_ip):
    # Send a script to Techman robot
    # TMSCT command
    import sys
    import time
    import struct
    import socket
    
    # Default communication port for Techman scripts:
    port = 5890
    
    # Script ID (returned when the script is completed)
    script_id = 1
    
    def DecodeResponse(rec_bytes):
        # Convert returned message from TM robot to a readable message
        returned = rec_bytes.decode("utf-8").strip()
        print("Robot response: " + returned)
        ret_sections = returned.split(',')
        all_good = False
        if len(ret_sections) < 5:
            return all_good, "Unexpected response: " + returned
            
        else:
            status_msg = ""
            if 'OK' in ret_sections[3]:
                status_msg = "Program is correct"
                all_good = True
            else:
                status_msg = "Program Errors!"
            
            warnings = ret_sections[3].split(';')
            if len(warnings) > 2:
                warning_lineid = int(warnings[1]) - 1
                script_lines = script_code.split('\n')
                if warning_lineid >= 0 and warning_lineid < len(script_lines):
                    warning_str = script_code[warning_lineid]
                else:
                    warning_str = "Unknown error line"
                
                status_msg = "<br>Warning on line " + str(warning_lineid) + ": " + warning_str
                
            return all_good, status_msg
    
    # Build the packet to send based on the script data
    data = (('%i,' % script_id) + script_code)
    data_length = len(data)
    
    # convert string to bytes
    data_msg = 'TMSCT,' + str(data_length) + ',' + data + ','
    data_msg = data_msg.encode("utf-8")
    
    # Calculate checksum
    csum = 0
    for el in data_msg:
        csum ^= el
    
    packet = b'$' + data_msg + b'*' + hex(csum)[2:].encode('utf-8').upper() + b'\r\n'
    
    print("Ready to load RoboDK program generated for Omron/Techman robots.")
    print("Make sure to check the following:")
    print(" -> Make sure the robot is in a Listen node")
    print(" -> The Listen Port is set to:   %i" % port)
    print(" -> The robot IP is set to:      %s" % robot_ip)
    print(" -> Activate the following setting if your simulation calls any subprograms: Tools-Options-Program-Inline subprograms")
    print("")
    print("You can change these settings in 'Connect-Connect to Robot' from RoboDK's main menu.")
    
    # Infinite loop to run the program
    while True:        
        print("")
        print("")
        print("******************************************************************************")
        print("Press enter to start the program on the real robot")
        print("(close this window to stop)")
        input()
        
        print("Connecting to robot %s:%i ..." % (robot_ip, port))
        sys.stdout.flush()
        robot_socket = socket.create_connection((robot_ip, port))
        print("Connected")
        sys.stdout.flush()
        
        print("Sending program...")
        sys.stdout.flush()         
        robot_socket.send(packet)
        time.sleep(0.5)
        
        try:
            received = robot_socket.recv(4096)
            
        except ConnectionAbortedError as e:
            msg = str(e)
            print(msg)
            return
            
        robot_socket.close()
                        
        if received:
            sys.stdout.flush()
            all_good, response = DecodeResponse(received)        
            print(response)
            sys.stdout.flush()
                
        else:
            print("Robot connection problems. Validate the robot connection and IP.")
            sys.stdout.flush()
            #time.sleep(2)
            #return 0 

def ReadFile(script_path):
    """Read a file from disk (place the file in the same directory)"""
    with open(script_path, 'r') as fid:
        data_file = fid.read()
        # Update new lines as expected by Techman
        data_file = data_file.replace('\n','\r\n')
        
    return data_file
    
def RunScript(script_name):
    """Read and send a file from disk to the robot"""    
    import os
    script_folder = os.path.dirname(os.path.realpath(__file__))
    script_folder = script_folder.replace("\\", "/")
    script_path = script_folder + "/" + script_name + ".script"        
    print("Loading program: " + script_name)
    print("Located in: " + script_path)
    print("")
    script_data = ReadFile(script_path)
    TM_SendScript(script_data, ROBOT_IP)
    
    
SCRIPT_LOADER_HEADER = """# This is a Python program that will load a program for a Techman robot.
# This file is generated automatically using RoboDK Software.
# For more information, visit: https://robodk.com/

# ------------------------------------------------------
# Set the Robot IP or change as required
# You can also set the robot IP in RoboDK to generate and execute the program automatically:
#  1- Select "Connect" from the main menu
#  2- Select "Connect to Robot"
#  3- Enter the robot IP
ROBOT_IP = "%s"


def MainProgram():
    # Run the program file (script file must be placed in the same folder)
    # The program file was originally saved here:
    # %s

    RunScript("%s")

    print("Main program completed")
    
    
"""

SCRIPT_LOADER_FOOTER = """

# To execute when this file is run as a single module
if __name__ == "__main__":
    
    # Run the main program
    MainProgram()
    
    print("Program Done")
    input("Press any key to close")    
"""



# ----------------------------------------------------
# Import RoboDK tools
from robodk import *

# ----------------------------------------------------

def pose_2_str(pose):
    """Prints a pose target"""
    [x,y,z,r,p,w] = pose_2_xyzrpw(pose)
    return ('%.3f,%.3f,%.3f,%.4f,%.4f,%.4f' % (x,y,z,r,p,w))
    
def joints_2_str(jnts):
    """Prints a joint target for Staubli VAL3 XML"""
    str = ''    
    for i in range(len(jnts)):
        str = str + ('%.5f,' % (jnts[i]))
    str = str[:-2]
    return str
    
#def distance_p1_p02(p0,p1,p2):
#    v01 = subs3(p1, p0)
#    v02 = subs3(p2, p0)
#    return dot(v02,v01)/dot(v02,v02)
        
# ----------------------------------------------------    
# Object class that handles the robot instructions/syntax
class RobotPost(object):
    """Robot post object"""
    # Robot IP (should be provided by RoboDK when the program is generated)
    ROBOT_IP = '192.168.1.100'
    
    MAX_LINES_X_PROG = 1e9 #250    # Maximum number of lines per program. If the number of lines is exceeded, the program will be executed step by step by RoboDK
    PROG_EXT = 'script'        # set the program extension
    SPEED_MMS       = 50    # default speed for linear moves in m/s
    SPEED_PERCENT   = 10    # default speed for joint moves in percentage
    SPEED_DEGS      = 30    # default speed for joint moves in deg/s
    ACCEL_MMSS      = 100   # default acceleration for lineaer moves in mm/ss
    ACCEL_DEGSS    =  200   # default acceleration for joint moves in deg/ss
    ROUNDING       =    1   # default blend radius as a percentage
    USE_MOVEP = False
    TAB_CHAR = ''
    #--------------------------------
    REF_FRAME      = eye(4) # default reference frame (the robot reference frame)
    LAST_POS_ABS = None # last XYZ position
    
    
    
    
    # other variables
    ROBOT_POST = 'unset'
    ROBOT_NAME = 'generic'
    PROG_FILES = []
    MAIN_PROGNAME = 'unknown'
    
    nPROGS = 0
    PROG = []
    PROG_LIST = []
    VARS = []
    VARS_LIST = []
    SUBPROG = []
    TAB = ''
    LOG = ''   
    FOLDER = ''
    SCRIPT_LOADER = 'TM_Loader.py'
    
    def __init__(self, robotpost=None, robotname=None, robot_axes = 6, **kwargs):
        self.ROBOT_POST = robotpost
        self.ROBOT_NAME = robotname
        for k,v in kwargs.items():
            if k == 'lines_x_prog':
                self.MAX_LINES_X_PROG = v    
            elif k == 'ip_com':
                self.ROBOT_IP = v
        
    def ProgStart(self, progname):
        progname = FilterName(progname)
        self.nPROGS = self.nPROGS + 1
        if self.nPROGS <= 1:
            self.TAB = ''
            # Create global variables:
            #self.addline('// Program %s' % progname)
            self.vars_update()
            self.MAIN_PROGNAME = progname    
        else:
            #self.addline('// Subprogram %s' % progname)
            #self.addline('void %s(){' % progname)
            self.TAB = self.TAB_CHAR      
        
    def ProgFinish(self, progname):
        progname = FilterName(progname)
        self.TAB = ''
        # Important!! The script language does not support comments or empty lines
        #if self.nPROGS <= 1:
        #    self.addline('// End of main program ' + progname)
        #else:
        #    self.addline('// End of subprogram ' + progname)
        #    self.addline('')       
                
    def ProgSave(self, folder, progname, ask_user = False, show_result = False):
        progname = FilterName(progname)
        if ask_user or not DirExists(folder):
            folder = getSaveFolder(folder,'Select a directory to save your program')
            if folder is None:
                # The user selected the Cancel button
                return
                
        self.FOLDER = folder
        
        filesave = folder + '/' + progname + '.' + self.PROG_EXT

        self.prog_2_list()        

        with open(filesave, "w") as fid:
            # Create main program call:
            #fid.write('void %s(){\n' % self.MAIN_PROGNAME)

            # Add global parameters:
            #fid.write(self.TAB_CHAR + '// Global parameters:\n')
            #for line in self.VARS_LIST[0]:
            #    fid.write(self.TAB_CHAR + line + '\n')            
            #fid.write(self.TAB_CHAR + '\n')
            #fid.write(self.TAB_CHAR)

            # Add a custom header if desired:
            fid.write(DEFAULT_HEADER_SCRIPT)        
            #fid.write(self.TAB_CHAR + '\n')

            # Add the suprograms that are being used in RoboDK
            #for line in self.SUBPROG:
            #    fid.write("// " + self.TAB_CHAR + line + '\n')
                
            #fid.write("// " + self.TAB_CHAR + '\n')

            # Add the main code:
            #fid.write(self.TAB_CHAR + '// Main program:\n')
            for prog in self.PROG_LIST:
                for line in prog:
                    fid.write(self.TAB_CHAR + line + '\n')

            #fid.write('\n\n')
            #fid.write('%s()\n' % self.MAIN_PROGNAME)
    
        print('SAVED: %s\n' % filesave) # tell RoboDK the path of the saved file
        self.PROG_FILES = filesave
        
        
        self.SCRIPT_LOADER = folder + '/' + progname + '.py'
        with open(self.SCRIPT_LOADER, "w") as fid:
            fid.write(SCRIPT_LOADER_HEADER % (self.ROBOT_IP, filesave, progname))
            import inspect
            fid.write(inspect.getsource(RunScript))
            fid.write("\r\n")
            fid.write(inspect.getsource(ReadFile))
            fid.write("\r\n")
            fid.write(inspect.getsource(TM_SendScript))
            fid.write("\r\n")
            fid.write(SCRIPT_LOADER_FOOTER)
        
        # open file with default application
        if show_result:
            if type(show_result) is str:
                # Open file with provided application
                import subprocess
                p = subprocess.Popen([show_result, filesave])
            elif type(show_result) is list:
                import subprocess
                p = subprocess.Popen(show_result + [filesave])   
            else:
                # open file with default application
                os.startfile(filesave)
            if len(self.LOG) > 0:
                mbox('Program generation LOG:\n\n' + self.LOG)
    
        #if len(self.PROG_LIST) > 1:
        #    mbox("Warning! The program " + progname + " is too long and directly running it on the robot controller might be slow. It is better to run it form RoboDK.")


    #Function to generate
    def TriggerScript(self):
        import subprocess
        import sys
        
        print("POPUP: Running script file")
        sys.stdout.flush()
        
        #subprocess.call([sys.executable, filenameToOpen], shell = False)
        command = 'start "" "' + sys.executable + '" "' + self.SCRIPT_LOADER + '"'
        print("Running command: " + command)
        sys.stdout.flush()
        os.system(command)        
        
    def ProgSendRobot(self, robot_ip, remote_path, ftp_user, ftp_pass):
        """Send a program to the robot using the provided parameters. This method is executed right after ProgSave if we selected the option "Send Program to Robot".
        The connection parameters must be provided in the robot connection menu of RoboDK"""
        #UploadFTP(self.PROG_FILES, robot_ip, remote_path, ftp_user, ftp_pass)
        status = self.TriggerScript()
        
    def MoveJ(self, pose, joints, conf_RLF=None):
        """Add a joint movement"""        
        self.addline('PTP("JPP",%s,%i,%i,%i,%s)' % (joints_2_str(joints), self.SPEED_PERCENT, 0, self.ROUNDING, ("true" if self.ROUNDING > 0 else "false")))        
        
    def MoveL(self, pose, joints, conf_RLF=None):
        """Add a linear movement"""
        # Movement in joint space or Cartesian space should give the same result:
        # pose_wrt_base = self.REF_FRAME*pose

        if pose is None:
            raise Exception("Linear movements using joint targets is not accepted")
            return

        self.addline('Line("CAP",%s,%i,%i,%i,%s)' %(pose_2_str(pose), self.SPEED_MMS, 0, self.ROUNDING, ("true" if self.ROUNDING > 0 else "false")))
        
    def MoveC(self, pose1, joints1, pose2, joints2, conf_RLF_1=None, conf_RLF_2=None):
        """Add a circular movement"""            
        #pose1_abs = self.REF_FRAME*pose1
        #pose2_abs = self.REF_FRAME*pose2        
        if pose1 is None or pose2 is None:
            raise Exception("Circular movements must be done using Cartesian targets")
            return

        self.addline('Circle("CAP",%s,%s,%i,%i,%i,%s)' % (pose_2_str(pose1), pose_2_str(pose2), self.SPEED_MMS, 0, self.ROUNDING, "true" if self.ROUNDING > 0 else "false"))
        
    def setFrame(self, pose, frame_id=None, frame_name=None):
        """Change the robot reference frame"""
        # the reference frame is not needed if we use joint space for joint and linear movements
        # the reference frame is also not needed if we use cartesian moves with respect to the robot base frame
        # the cartesian targets must be pre-multiplied by the active reference frame
        self.REF_FRAME = pose    
        self.addline('ChangeBase(%s)' % pose_2_str(pose))
        ## Optional: Set the reference by name (same name as defined in RoboDK tree)
        #self.addline('ChangeBase(%s)' % frame_name)
        
    def setTool(self, pose, tool_id=None, tool_name=None):
        """Change the robot TCP"""
        self.addline('ChangeTCP(%s)' % pose_2_str(pose))
        ## Optional: Set the tool by name (same name as defined in RoboDK tree)
        # self.addline('ChangeTCP(%s)' % tool_name)
        
    def Pause(self, time_ms):
        """Pause the robot program"""
        #This is just a stop to the program that require a Resume afterwards, we need a Delay here
        if time_ms <= 0:
            #self.addline('// Pause program')
            self.addline('Pause()')
        else:
            #self.addline('// delay of %i ms not implemented' % time_ms)
            self.addline('Pause()')
        
    def setSpeed(self, speed_mms):
        """Changes the robot speed (in mm/s)"""
        #if speed_mms < 999.9:
        #    self.USE_MOVEP = True
        #else:
        #    self.USE_MOVEP = False
        self.SPEED_MSS = max(1,speed_mms)
        
        # Assume that 5000 mm/s is 100% of the speed
        self.SPEED_PERCENT = self.SPEED_MSS / 5000
        
    def setAcceleration(self, accel_mmss):
        """Changes the robot acceleration (in mm/s2)"""    
        self.ACCEL_MMSS = accel_mmss
        
    def setSpeedJoints(self, speed_degs):
        """Changes the robot joint speed (in deg/s)"""
        self.SPEED_DEGS = speed_degs
        
        # Assume that 5000 deg/s is 100% of the speed
        self.SPEED_PERCENT = self.SPEED_DEGS / 5000
    
    def setAccelerationJoints(self, accel_degss):
        """Changes the robot joint acceleration (in deg/s2)"""
        self.ACCEL_DEGSS = accel_degss
        
    def setZoneData(self, zone_mm):
        """Changes the zone data approach (makes the movement more smooth)"""
        if zone_mm < 0:
            zone_mm = 0
            
        self.ROUNDING = zone_mm
        
    def setDO(self, io_var, io_value):
        """Set a Digital Output"""
        if type(io_value) != str: # set default variable value if io_value is a number            
            if io_value > 0:
                io_value = 'true'
            else:
                io_value = 'false'
        
        if type(io_var) != str:  # set default variable name if io_var is a number
            newline = 'modbus_write("TCP_1",0,"DO",%i,%s)' % (int(io_var)+800, io_value)
        else:
            newline = 'modbus_write("TCP_1",0,"DO",%s,%s)' % (io_var, io_value)
            
        self.addline(newline)
        
    def setAO(self, io_var, io_value):
        """Set an Analog Output"""
        if type(io_value) != str: # set default variable value if io_value is a number            
            io_value = str(io_value)
        
        if type(io_var) != str:  # set default variable name if io_var is a number
            newline = 'modbus_read("TCP_1",0,"RO",%i,%s)' % (int(io_var)+9000, io_value)
        else:
            newline = 'modbus_read("TCP_1",0,"RO",%s,%s)' % (io_var, io_value)
            
        self.addline(newline)
        
    def waitDI(self, io_var, io_value, timeout_ms=-1):
        """Waits for an input io_var to attain a given value io_value. Optionally, a timeout can be provided."""
        if type(io_var) != str:  # set default variable name if io_var is a number
            io_var = str(int(io_var)+7202)
            
        if type(io_value) != str: # set default variable value if io_value is a number            
            if io_value > 0:
                io_value = 'true'
            else:
                io_value = 'false'
        
        newline = 'modbus_read("TCP_1",0,"DI",%s,%s)' % (io_var, io_value)
        
        # Important! This is not correct
        self.addline(newline)
        
    def RunCode(self, code, is_function_call = False):
        """Adds code or a function call"""
        if is_function_call:
            code = FilterName(code)
            if code.lower() == "usemovel":
                self.USE_MOVEP = False
                return
            elif code.lower() == "usemovep":
                self.USE_MOVEP = True
                return
            
            if not code.endswith(')'):
                code = code + '()'
            self.addline(code)
        else:
            if not '\n' in code:
                self.addline(code)
            else:
                for line in code.split('\n'):
                    self.addline(line)
            
            #self.addline('# ' + code) #generate custom code as a comment
        
    def RunMessage(self, message, iscomment = False):
        """Show a message on the controller screen"""
        # COMMENT LINES ARE NOT ALLOWED when sending a script!!!
        return
        
        
        if iscomment:
            self.addline('// ' + message)
        else:
            self.addline('// Popup: %s' % message)
        
# ------------------ private ----------------------
    def vars_update(self):
        # Generate global variables for this program
        self.VARS = []            
        #self.VARS.append('global speed_ms    = %.3f' % self.SPEED_MS)
        #self.VARS.append('global speed_rads  = %.3f' % self.SPEED_RADS)
        #self.VARS.append('global accel_mss   = %.3f' % self.ACCEL_MSS)
        #self.VARS.append('global accel_radss = %.3f' % self.ACCEL_RADSS)
        #self.VARS.append('global blend_radius_m = %.3f' % self.BLEND_RADIUS_M)
            
    def prog_2_list(self):
        if len(self.PROG) > 1:
            self.PROG_LIST.append(self.PROG)
            self.PROG = []
            self.VARS_LIST.append(self.VARS)
            self.VARS = []
            self.vars_update()
        
    def addline(self, newline):
        """Add a program line"""
        if self.nPROGS <= 1:
            if len(self.PROG) > self.MAX_LINES_X_PROG:
                self.prog_2_list()
                
            self.PROG.append(self.TAB + newline)
        else:
            self.SUBPROG.append(self.TAB + newline)
        
    def addlog(self, newline):
        """Add a log message"""
        self.LOG = self.LOG + newline + '\n'

# -------------------------------------------------
# ------------ For testing purposes ---------------   
def Pose(xyzrpw):
    [x,y,z,r,p,w] = xyzrpw
    a = r*math.pi/180
    b = p*math.pi/180
    c = w*math.pi/180
    ca = math.cos(a)
    sa = math.sin(a)
    cb = math.cos(b)
    sb = math.sin(b)
    cc = math.cos(c)
    sc = math.sin(c)
    return Mat([[cb*ca, ca*sc*sb - cc*sa, sc*sa + cc*ca*sb, x],[cb*sa, cc*ca + sc*sb*sa, cc*sb*sa - ca*sc, y],[-sb, cb*sc, cc*cb, z],[0,0,0,1]])

def test_post():
    """Test the post with a basic program"""

    robot = RobotPost('Universal Robotics', 'Generic UR robot')

    robot.ProgStart("Program")
    robot.RunMessage("Program generated by RoboDK", True)
    robot.setFrame(Pose([807.766544, -963.699898, 41.478944, 0, 0, 0]))
    robot.setTool(Pose([62.5, -108.253175, 100, -60, 90, 0]))
    robot.setSpeed(100) # set speed to 100 mm/s
    robot.setAcceleration(3000) # set speed to 3000 mm/ss    
    robot.MoveJ(Pose([200, 200, 500, 180, 0, 180]), [-46.18419, -6.77518, -20.54925, 71.38674, 49.58727, -302.54752] )
    robot.MoveL(Pose([200, 250, 348.734575, 180, 0, -150]), [-41.62707, -8.89064, -30.01809, 60.62329, 49.66749, -258.98418] )
    robot.MoveL(Pose([200, 200, 262.132034, 180, 0, -150]), [-43.73892, -3.91728, -35.77935, 58.57566, 54.11615, -253.81122] )
    robot.RunMessage("Setting air valve 1 on")
    robot.RunCode("TCP_On", True)
    robot.Pause(1000)
    robot.MoveL(Pose([200, 250, 348.734575, 180, 0, -150]), [-41.62707, -8.89064, -30.01809, 60.62329, 49.66749, -258.98418] )
    robot.MoveL(Pose([250, 300, 278.023897, 180, 0, -150]), [-37.52588, -6.32628, -34.59693, 53.52525, 49.24426, -251.44677] )
    robot.MoveL(Pose([250, 250, 191.421356, 180, 0, -150]), [-39.75778, -1.04537, -40.37883, 52.09118, 54.15317, -246.94403] )
    robot.RunMessage("Setting air valve off")
    robot.RunCode("TCP_Off", True)
    robot.Pause(1000)
    robot.MoveL(Pose([250, 300, 278.023897, 180, 0, -150]), [-37.52588, -6.32628, -34.59693, 53.52525, 49.24426, -251.44677] )
    robot.MoveL(Pose([250, 200, 278.023897, 180, 0, -150]), [-41.85389, -1.95619, -34.89154, 57.43912, 52.34162, -253.73403] )
    robot.MoveL(Pose([250, 150, 191.421356, 180, 0, -150]), [-43.82111, 3.29703, -40.29493, 56.02402, 56.61169, -249.23532] )
    robot.ProgFinish("Program")
    # robot.ProgSave(".","Program",True)
    for line in robot.PROG:
        print(line)
    if len(robot.LOG) > 0:
        mbox('Program generation LOG:\n\n' + robot.LOG)

    input("Press Enter to close...")

if __name__ == "__main__":
    """Function to call when the module is executed by itself: test"""
    test_post()