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
#
#
#
#
# This is a Python module that allows driving an Omron/Techman robot.
# This Python module can be run directly in console mode to test its functionality.
# This module allows communicating with a robot through the command line.
# The same commands we can input manually are used by RoboDK to drive the robot from the PC.
# RoboDK Drivers are located in /RoboDK/api/Robot/ by default. Drivers can be PY files or EXE files.
#
# Drivers are modular. They are not part of the RoboDK executable but they must be placed in C:/RoboDK/api/robot/, then, linked in the Connection parameters menu:
#   1. right click a robot in RoboDK, then, select "Connect to robot".
#   2. In the "More options" menu it is possible to update the location and name of the driver.
# Driver linking is automatic for currently available drivers.
# More information about robot drivers available here:
#   https://robodk.com/doc/en/Robot-Drivers.html#RobotDrivers
#
# Alternatively to the standard programming methods (where a program is generated, then, transferred to the robot and executed) it is possible to run a program simulation directly on the robot
# The robot movement in the simulator is then synchronized with the real robot.
# Programs generated from RoboDK can be run on the robot by right clicking the program, then selecting "Run on robot".
#   Example:
#   https://www.youtube.com/watch?v=pCD--kokh4s
#
# Example of an online programming project:
#   https://robodk.com/blog/online-programming/
#
# It is possible to control the movement of a robot from the RoboDK API (for example, from a Python or C# program using the RoboDK API).
# The same code is used to simulate and optionally move the real robot.
#   Example:
#   https://robodk.com/offline-programming
#
#   To establish connection from RoboDK API:
#   https://robodk.com/doc/en/PythonAPI/robolink.html#robolink.Item.ConnectSafe
#
# Example of a quick manual test in console mode:
#  User entry: CONNECT 192.168.123.1 7000
#  Response:   SMS:Response from the robot or failure to connect
#  Response:   SMS:Ready 
#  User entry: MOVJ 10 20 30 40 50 60 70
#  Response:   SMS:Working...
#  Response:   SMS:Ready
#  User entry: CJNT
#  Response:   SMS:Working...
#  Response:   JNTS: 10 20 30 40 50 60 70
#
# ---------------------------------------------------------------------------------
import socket
import struct
import sys
import re
from io import BytesIO

# ---------------------------------------------------------------------------------
# ---------------- Constants/settings --------------------
nDOFs_MIN = 6          # Set the minimum number of degrees of freedom that are expected
TM_PORT = 5890         # Default communication port
KEEP_ALIVE = True      # Keep the socket connection alive
TIMEOUT = 1            # in seconds
USE_DEFAULT_ROUNDING = 0 # Use point to point movements
DEBUG_ON = True        # Set to True to see additional debug messages
#SET_BASE_STR = None   
SET_BASE_STR = 'ChangeBase("RobotBase")'  # Reset the base before any other command is sent
DO_DIRECT_MODBUS = True # Use modbus to change digital outputs instead of sending a script to do so

# Set the driver version
DRIVER_VERSION = "RoboDK Driver for Omron-Techman v1.1.0"


# ---------------------------------------------------------------------------------


# Note, a simple print() will flush information to the log window of the robot connection in RoboDK
# Sending a print() might not flush the standard output unless the buffer reaches a certain size

def print_message(message):
    """print_message will display a message in the log window (and the connexion status bar)"""
    print("SMS:" + message)
    sys.stdout.flush()  # very useful to update RoboDK as fast as possible


def show_message(message):
    """show_message will display a message in the status bar of the main window"""
    print("SMS2:" + message)
    sys.stdout.flush()  # very useful to update RoboDK as fast as possible


def Robot_Disconnect():
    global ROBOT
    ROBOT.disconnect()

def TM_DecodeResponse(recv_bytes):
    """Convert returned message from TM robot to a readable message"""
    returned = recv_bytes.decode("utf-8").strip()
    print_message("Robot response: " + returned)
    ret_sections = returned.split(',')
    all_good = False
    if len(ret_sections) < 5:
        return all_good, "Unexpected response: " + returned
        
    else:
        status_msg = ""
        if 'OK' in ret_sections[3]:
            all_good = True
            status_msg = "Script is correct"
        else:
            status_msg = "Program Errors: " + returned
        
        warnings = ret_sections[3].split(';')
        if len(warnings) > 2:
            warning_lineid = int(warnings[1]) - 1
            script_lines = script_code.split('\n')
            if warning_lineid >= 0 and warning_lineid < len(script_lines):
                warning_str = script_code[warning_lineid]
            else:
                warning_str = "Unknown error line"
            
            status_msg = "Warning on line " + str(warning_lineid) + ": " + warning_str
            
        return all_good, status_msg

def TM_SendScript(script_code, robot_ip=None, port=5890, robot_socket=None):
    # Send a script to Techman robot
    # TMSCT command
    import sys
    import time
    import struct
    import socket
    
    # Default communication port for Techman scripts:
    #port = TM_PORT
    
    # Script ID (returned when the script is completed)
    script_id = 1
    
    # Build the packet to send based on the script data
    data = (('%i,' % script_id) + script_code)
    data_length = len(data)
    
    # Convert string to bytes
    data_msg = 'TMSCT,' + str(data_length) + ',' + data + ','
    data_msg = data_msg.encode("utf-8")
    
    # Calculate checksum
    csum = 0
    for el in data_msg:
        csum ^= el
    
    # Build byte array to send
    packet = b'$' + data_msg + b'*' + hex(csum)[2:].encode('utf-8').upper() + b'\r\n'
    
    # Connect to the robot
    socket_disconnect = False
    if robot_socket is None:
        socket_disconnect = True
        if DEBUG_ON:
            print_message("Connecting to robot %s:%i ..." % (robot_ip, port))
            UpdateStatus(ROBOTCOM_WORKING)        
            
        robot_socket = socket.create_connection((robot_ip, port))
        robot_socket.settimeout(TIMEOUT)
        if DEBUG_ON:
            print_message("Connected")
            UpdateStatus(ROBOTCOM_WORKING)        
    
    if DEBUG_ON:
        print_message("Sending script...")
        UpdateStatus(ROBOTCOM_WORKING)

    robot_socket.send(packet)    
    #time.sleep(TIMEOUT)
    try:
        received = robot_socket.recv(4096)
    except ConnectionAbortedError as e:
        msg = str(e)
        print(msg)
        return False, msg
        
    if socket_disconnect:
        robot_socket.close()
                
    if received:
        all_good, response = TM_DecodeResponse(received)        
        print_message(response)
        return all_good, response
            
    else:
        msg = "Robot connection problems. Validate the robot connection and the robot IP."
        #print_message(msg)
        return False, msg


def TM_DecodeStatus(recv_bytes):
    """Convert returned message from TM robot to a readable message"""
    returned = recv_bytes.decode("utf-8").strip()
    print_message("Robot response: " + returned)
    ret_sections = returned.split(',')
    listen_active = False
    if len(ret_sections) < 5:
        return listen_active, "Unexpected response: " + returned
        
    else:
        status_msg = ""
        if 'true' in ret_sections[3]:
            listen_active = True
            status_msg = "Flow is in Listen mode: " + ret_sections[4]
        else:
            status_msg = "Program Errors: " + returned
            
        return listen_active, status_msg
        
def TM_Status(subcmd=0, robot_ip=None, port=5890, robot_socket=None):
    # Send a script to Techman robot
    # TMSCT command
    import sys
    import time
    import struct
    import socket
        
    # Build the packet to send based on the script data
    data = ('%02i,' % subcmd)
    data_length = len(data)
    
    # Convert string to bytes
    data_msg = 'TMSTA,' + str(data_length) + ',' + data + ','
    data_msg = data_msg.encode("utf-8")
    
    # Calculate checksum
    csum = 0
    for el in data_msg:
        csum ^= el
    
    # Build byte array to send
    packet = b'$' + data_msg + b'*' + hex(csum)[2:].encode('utf-8').upper() + b'\r\n'
    
    # Connect to the robot
    socket_disconnect = False
    if robot_socket is None:
        socket_disconnect = True
        if DEBUG_ON:
            print_message("Connecting to robot %s:%i ..." % (robot_ip, port))
            UpdateStatus(ROBOTCOM_WORKING)

        robot_socket = socket.create_connection((robot_ip, port))      
        robot_socket.settimeout(TIMEOUT)
        if DEBUG_ON:
            print_message("Connected")
            UpdateStatus(ROBOTCOM_WORKING)
                
    if DEBUG_ON:
        print_message("Sending script...")
        UpdateStatus(ROBOTCOM_WORKING)

    robot_socket.send(packet)    
    #time.sleep(TIMEOUT)
    received = robot_socket.recv(4096)
    if socket_disconnect:
        robot_socket.close()
                
    if received:
        listen_mode, response = TM_DecodeStatus(received)
        print_message(response)
        return listen_mode, response
            
    else:
        msg = "Robot connection problems. Validate the robot connection and the robot IP."
        #print_message(msg)
        return False, msg
    
    
# ----------- communication class for Omron-Techman robots -------------
# This class handles communication between this driver (PC) and the robot
class ComRobot:
    """Robot class for programming Omron-Techman robots"""
    LAST_MSG = None  # Keep a copy of the last message received
    CONNECTED = False  # Connection status is known at all times
    SPEED_MMS = 100 # default speed in mm/s
    ROUNDING = USE_DEFAULT_ROUNDING
    SPEED_PERCENT = 10 # default speed in percentage
    RobotIP = None
    RobotPort = TM_PORT
    sock = None # communication socket (None if we don't want the connection to remain alive)
    UPDATE_BASE = SET_BASE_STR

    # This is executed when the object is created
    def __init__(self):
        self.BUFFER_SIZE = 512  # bytes
        self.TIMEOUT = 5 * 60  # seconds: it must be enough time for a movement to complete
        # destructor

    def __del__(self):
        self.disconnect()

    # Disconnect from robot
    def disconnect(self):
        if not KEEP_ALIVE:
            return True
            
        self.CONNECTED = False
        if self.sock:
            try:
                self.sock.close()
                self.sock = None
            except OSError:
                self.sock = None
                return False
                
        return True

    # Connect to robot
    def connect(self, ip, port=30000):
        if not KEEP_ALIVE:
            self.CONNECTED = True
            return True

        global ROBOT_MOVING
        self.disconnect()
        print_message('Connecting to robot %s:%i' % (ip, port))
        UpdateStatus(ROBOTCOM_WORKING)
        # Create new socket connection
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(TIMEOUT)
        UpdateStatus(ROBOTCOM_WORKING)
        try:
            self.sock.connect((ip, port))
        except ConnectionRefusedError as e:
            print_message(str(e))
            return False
        except socket.timeout as e:
            #print_message(str(e))
            print_message("Connection timed out")
            return False

        self.CONNECTED = True
        ROBOT_MOVING = False
        #self.send_line(DRIVER_VERSION)
        print_message('Waiting for welcome message...')

        #robot_response = self.recv_line()
        #print(robot_response)
        #sys.stdout.flush()
        return True

    def SendCmd(self, script_code):
        """Send a command. Returns True if success, False otherwise."""
        # print('SendCmd(cmd=' + str(cmd) + ', values=' + str(values) if values else '' + ')')
        # Skip the command if the robot is not connected
        if KEEP_ALIVE and not self.CONNECTED:
            UpdateStatus(ROBOTCOM_NOT_CONNECTED)
            return False
            
        if self.UPDATE_BASE is not None:
            # Important: Set the base to the robot base
            script_code = self.UPDATE_BASE + '\n' + script_code
            self.UPDATE_BASE = None

        all_good, self.LAST_MSG = TM_SendScript(script_code, self.RobotIP, self.RobotPort, self.sock)
        return all_good
        
    def WaitReady(self):
        """Wait for the robot to be in Listen mode"""
        listen_active = False
        while not listen_active:
            listen_active, msg = TM_Status(0, self.RobotIP, self.RobotPort, self.sock)
            print_message(msg)
            
        return True


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Generic RoboDK driver for a specific Robot class
ROBOT = ComRobot()
#ROBOT_IP = "172.31.1.147"  # IP of the robot
ROBOT_PORT = TM_PORT  # Communication port of the robot
ROBOT_MOVING = False


# ------------ robot connection -----------------
# Establish connection with the robot
def RobotConnect():
    global ROBOT
    return ROBOT.connect(ROBOT.RobotIP, ROBOT.RobotPort)


# Disconnect from the robot
def RobotDisconnect():
    global ROBOT
    ROBOT.disconnect()
    return True


# -----------------------------------------------------------------------------
# Generic RoboDK driver tools

def print_joints(joints, is_moving=False):
    # if len(joints) > 6:
    #    joints = joints[0:6]
    if is_moving:
        # Display the feedback of the joints when the robot is moving
        if ROBOT_MOVING:
            print("JNTS_MOVING " + " ".join(format(x, ".5f") for x in joints))  # if joints is a list of float
            # print("JNTS_MOVING " + joints)
    else:
        print("JNTS " + " ".join(format(x, ".5f") for x in joints))  # if joints is a list of float
        # print("JNTS " + joints)
    sys.stdout.flush()  # very useful to update RoboDK as fast as possible


# ---------------------------------------------------------------------------------
# Constant values to display status using UpdateStatus()
ROBOTCOM_UNKNOWN = -1000
ROBOTCOM_CONNECTION_PROBLEMS = -3
ROBOTCOM_DISCONNECTED = -2
ROBOTCOM_NOT_CONNECTED = -1
ROBOTCOM_READY = 0
ROBOTCOM_WORKING = 1
ROBOTCOM_WAITING = 2

# Last robot status is saved
STATUS = ROBOTCOM_DISCONNECTED


# UpdateStatus will send an appropriate message to RoboDK which will result in a specific coloring
# for example, Ready will be displayed in green, Waiting... will be displayed in Yellow and other messages
# will be displayed in red
def UpdateStatus(set_status=None):
    global STATUS
    if set_status is not None:
        STATUS = set_status

    if STATUS == ROBOTCOM_CONNECTION_PROBLEMS:
        print_message("Connection problems")
    elif STATUS == ROBOTCOM_DISCONNECTED:
        print_message("Disconnected")
    elif STATUS == ROBOTCOM_NOT_CONNECTED:
        print_message("Not connected")
    elif STATUS == ROBOTCOM_READY:
        print_message("Ready")
    elif STATUS == ROBOTCOM_WORKING:
        print_message("Working...")
    elif STATUS == ROBOTCOM_WAITING:
        print_message("Waiting...")
    else:
        print_message("Unknown status")


# Sample set of commands that can be provided by RoboDK of through the command line
def TestDriver():
    # try:
    # rob_ip = input("Enter the robot IP: ")
    # rob_port = input("Enter the robot Port (default=1101): ")
    # rob_port = int(rob_port)

    # RunCommand("CONNECT 192.168.0.100 10000")
    RunCommand("CONNECT 192.168.0.101 5890")
    RunCommand("SETDO 6 0")
    RunCommand("SETDO 6 1")
    RunCommand("SETDO 6 0")

    #print("Changing base:")
    #RunCommand("SETTOOL 0 0 0 0 0 0")
    #RunCommand('c ChangeTCP("USER_TCP_TM")')
    #print("moving robot:")
    #RunCommand("MOVJ -49.02582 3.23587 75.50025 11.26389 90.00000 -49.0258")
    #RunCommand("MOVJ -51.02582 3.23587 75.50025 11.26389 90.00000 -49.0258")
    #RunCommand("RUNPROG -1 SetForceConditionOnce(12)")
    #RunCommand("DISCONNECT")
    # print("Tip: Type 'CJNT' to retrieve")
    # print("Tip: Type 'MOVJ j1 j2 j3 j4 j5 j6 j7' to move the robot (provide joints as angles)")
    # except Exception as e:
    #    print(e)

    # input("Test commands finished. Press enter to continue")

    # RunCommand("SETTOOL -0.025 -41.046 50.920 60.000 -0.000 90.000")
    # RunCommand("MOVJ -5.362010 46.323420 20.746290 74.878840 -50.101680 61.958500")
    # RunCommand("SPEED 250")
    # RunCommand("MOVEL 0 0 0 0 0 0 -5.362010 50.323420 20.746290 74.878840 -50.101680 61.958500")
    # RunCommand("PAUSE 2000") # Pause 2 seconds


# -------------------------- Main driver loop -----------------------------
# Read STDIN and process each command (infinite loop)
# IMPORTANT: This must be run from RoboDK so that RoboDK can properly feed commands through STDIN
# This driver can also be run in console mode providing the commands through the console input
def RunDriver():
    for line in sys.stdin:
        RunCommand(line.strip())


# Each line provided through command line or STDIN will be processed by RunCommand
def RunCommand(cmd_line):
    global ROBOT
    global ROBOT_MOVING

    # strip a line of words into a list of numbers
    def line_2_values(line):
        values = []
        for word in line:
            try:
                number = float(word)
                values.append(number)
            except ValueError:
                pass
        return values

    cmd_words = cmd_line.split(' ')  # [''] if len == 0
    cmd = cmd_words[0]
    cmd_values = line_2_values(cmd_words[1:])  # [] if len <= 1
    n_cmd_values = len(cmd_values)
    n_cmd_words = len(cmd_words)
    received = None

    if cmd_line == "":
        # Skip if no command is provided
        return

    elif cmd_line.startswith("CONNECT"):
        # Connect to robot provided the IP and the port
        if n_cmd_words >= 2:
            ROBOT.RobotIP = cmd_words[1]
        if n_cmd_words >= 3:
            ROBOT.RobotPort = int(cmd_words[2])
        received = RobotConnect()   

    #elif not ROBOT.CONNECTED:
    #    print_message("Robot not connected. Connect first!")
    #    UpdateStatus(ROBOTCOM_NOT_CONNECTED)
        
    elif n_cmd_values >= nDOFs_MIN and cmd_line.startswith("MOVJ"):
        UpdateStatus(ROBOTCOM_WORKING)
        # Activate the monitor feedback
        ROBOT_MOVING = True
        
        # Execute a joint move. RoboDK provides j1,j2,...,j6,j7,x,y,z,w,p,r
        jnts = ''    
        for i in range(max(nDOFs_MIN, len(cmd_values) - 6)):
            jnts = jnts + ('%.5f,' % (cmd_values[i]))
        jnts = jnts[:-2]        
        
        # script code for a joint move:
        script_code = 'PTP("JPP",%s,%i,%i,%i,%s)' % (jnts, ROBOT.SPEED_PERCENT, 0, ROBOT.ROUNDING, ("true" if ROBOT.ROUNDING > 0 else "false"))
        if ROBOT.SendCmd(script_code):
            # Wait for command to be executed
            if ROBOT.WaitReady():
                # Notify that we are done with this command
                UpdateStatus(ROBOTCOM_READY)

    elif n_cmd_values >= nDOFs_MIN and cmd_line.startswith("MOVL"):
        UpdateStatus(ROBOTCOM_WORKING)
        # Activate the monitor feedback
        ROBOT_MOVING = True
        
        xyzwpr = '%.3f,%.3f,%.3f,%.4f,%.4f,%.4f' % tuple(cmd_values[-6:])
        script_code = 'Line("CAP",%s,%i,%i,%i,%s)' % (xyzwpr, ROBOT.SPEED_MMS, 0, ROBOT.ROUNDING, ("true" if ROBOT.ROUNDING > 0 else "false"))
        
        # Execute a linear move. RoboDK provides j1,j2,...,j6,j7,x,y,z,w,p,r
        if ROBOT.SendCmd(script_code):
            # Wait for command to be executed
            if ROBOT.WaitReady():
                # Notify that we are done with this command
                UpdateStatus(ROBOTCOM_READY)

    elif n_cmd_values >= nDOFs_MIN and cmd_line.startswith("MOVLSEARCH"):
        UpdateStatus(ROBOTCOM_WORKING)
        # Activate the monitor feedback
        ROBOT_MOVING = True
        # Execute a linear move. RoboDK provides j1,j2,...,j6,x,y,z,w,p,r
        if ROBOT.SendCmd(MSG_MOVEL_SEARCH, cmd_values[0:n_cmd_values]):
            # Wait for command to be executed
            if ROBOT.WaitReady():
                # Retrieve contact joints
                jnts_contact = ROBOT.recv_array()
                print_joints(jnts_contact)

    elif n_cmd_values >= 2 * (nDOFs_MIN + 6) and cmd_line.startswith("MOVC"):
        msg = "Circular movement not supported"
        print_message(msg)
        raise Exception(msg)

    elif cmd_line.startswith("CJNT"):
        UpdateStatus(ROBOTCOM_WORKING)
        # Retrieve the current position of the robot
        if ROBOT.SendCmd(MSG_CJNT):
            received = ROBOT.recv_array()
            print_joints(received)

    elif n_cmd_values >= 1 and cmd_line.startswith("SPEED"):
        #UpdateStatus(ROBOTCOM_WORKING)
        # First value is linear speed in mm/s
        # IMPORTANT! We should only send one "Ready" per instruction
        speed_values = [-1, -1, -1, -1]
        for i in range(min(4, len(cmd_values))):
            speed_values[i] = cmd_values[i]

        # speed_values[0] = speed_values[0] # linear speed in mm/s
        # speed_values[1] = speed_values[1] # joint speed in mm/s
        # speed_values[2] = speed_values[2] # linear acceleration in mm/s2
        # speed_values[3] = speed_values[3] # joint acceleration in deg/s2

        if speed_values[0] > 0:
            ROBOT.SPEED_MMS = speed_values[0]
            
        if speed_values[1] > 0:
            ROBOT.SPEED_PERCENT = min(100, 100*speed_values[1]/2000)
            
        UpdateStatus(ROBOTCOM_READY)

    elif n_cmd_values >= 6 and cmd_line.startswith("SETTOOL"):
        UpdateStatus(ROBOTCOM_WORKING)
        # Set the Tool frame provided the 6 XYZWPR cmd_values by RoboDK        
        script_code = 'ChangeTCP(%.3f,%.3f,%.3f,%.4f,%.4f,%.4f)' % tuple(cmd_values)
        if ROBOT.SendCmd(script_code):
            UpdateStatus(ROBOTCOM_READY)
        else:
            UpdateStatus(ROBOTCOM_CONNECTION_PROBLEMS)            

    elif n_cmd_values >= 1 and cmd_line.startswith("PAUSE"):
        UpdateStatus(ROBOTCOM_WAITING)
        # Run a pause
        time.sleep(0.001*cmd_values[0])
        UpdateStatus(ROBOTCOM_READY)

    elif n_cmd_values >= 1 and cmd_line.startswith("SETROUNDING"):
        # Set the rounding/smoothing value. Also known as ZoneData in ABB or CNT for Fanuc
        ROBOT.ROUNDING = cmd_values[0]
        UpdateStatus(ROBOTCOM_READY)

    elif n_cmd_values >= 2 and cmd_line.startswith("SETDO"):
        UpdateStatus(ROBOTCOM_WORKING)
        dIO_id = cmd_values[0]
        dIO_value = cmd_values[1]
        if DO_DIRECT_MODBUS:
            from pymodbus.client.sync import ModbusTcpClient
            
            # Phillip to implement modbus signal here given DO id and value
            if (dIO_id > 255):
                msg = "Modbus IO only allows 255 unique IO ports"
                print_message(msg)
                raise Exception(msg)
            client = ModbusTcpClient(ROBOT.RobotIP)
            client.write_coil(int(dIO_id),bool(dIO_value),unit = 1) #So usually it's unit 0 but wireshark showed the unit went by id 1
            client.close()
        else:
            # Execute script to trigger modbus
            script_code = 'modbus_write("TCP_1",0,"DO",%i,%s)' % (int(dIO_id)+800, dIO_value)
            
            if ROBOT.SendCmd(script_code):
                # Wait for command to be executed
                if ROBOT.WaitReady():
                    # Notify that we are done with this command
                    UpdateStatus(ROBOTCOM_READY)

    elif n_cmd_values >= 2 and cmd_line.startswith("WAITDI"):
        msg = "Wait Digital Input not supported"
        print_message(msg)
        raise Exception(msg)

    elif n_cmd_values >= 1 and n_cmd_words >= 3 and cmd_line.startswith("RUNPROG"):
        UpdateStatus(ROBOTCOM_WORKING)
        program_id = cmd_values[0]  # Program ID is extracted automatically if the program name is Program ID
        code = cmd_words[2]  # "Program%i" % program_id
        m = re.search(r'^(?P<program_name>.*)\((?P<args>.*)\)', code)
        code_dict = m.groupdict()
        program_name = code_dict['program_name']
        args = code_dict['args'].replace(' ', '').split(',')
        print('program_name: ' + program_name)
        print('args: ' + str(args))
    
        if ROBOT.SendCmd(code):
            # Wait for the program call to complete
            if ROBOT.WaitReady():
                # Notify that we are done with this command
                UpdateStatus(ROBOTCOM_READY)
                
    elif cmd_line.startswith("c "):
        UpdateStatus(ROBOTCOM_WORKING)
        code = cmd_line[2:]
        if ROBOT.SendCmd(code):
            # Wait for the program call to complete
            if ROBOT.WaitReady():
                # Notify that we are done with this command
                UpdateStatus(ROBOTCOM_READY)

    elif n_cmd_words >= 2 and cmd_line.startswith("POPUP "):
        UpdateStatus(ROBOTCOM_WORKING)
        message = cmd_line[6:]
        #ROBOT.send_line(message)
        # Wait for command to be executed
        if ROBOT.WaitReady():
            # Notify that we are done with this command
            UpdateStatus(ROBOTCOM_READY)

    elif cmd_line.startswith("DISCONNECT"):
        # Disconnect from robot
        UpdateStatus(ROBOTCOM_DISCONNECTED)
        ROBOT.disconnect()        

    elif cmd_line.startswith("STOP") or cmd_line.startswith("QUIT"):
        # Stop the driver
        ROBOT.disconnect()
        UpdateStatus(ROBOTCOM_DISCONNECTED)
        quit(0)  # Stop the driver

    elif cmd_line.startswith("t"):
        # Call custom procedure for quick testing
        TestDriver()

    else:
        print("Unknown command: " + str(cmd_line))

    if received is not None:
        UpdateStatus(ROBOTCOM_READY)
    # Stop monitoring feedback
    ROBOT_MOVING = False


if __name__ == "__main__":
    """Call Main procedure"""

    # It is important to disconnect the robot if we force to stop the process
    import atexit

    atexit.register(RobotDisconnect)
    
    cmdlist = ''
    cmdlist +='c ChangeTCP("TCP_1")|Set TCP_1|'
    cmdlist +='c ChangeBase("RobotBase")|Set Robot base|'
    cmdlist +='SETDO 6 1|Set DO6 On|'
    cmdlist +='SETDO 6 0|Set DO6 Off|'
    cmdlist +='c modbus_write("TCP_1",0,"DO",806,1)|Set DO6 On|'
    cmdlist +='c modbus_write("TCP_1",0,"DO",806,0)|Set DO6 Off|'
    
    print("CMDLIST:" + cmdlist)
    sys.stdout.flush()

    # Flush Disconnected message
    print_message(DRIVER_VERSION)
    
    # Install required packages
    if DO_DIRECT_MODBUS:
        UpdateStatus(ROBOTCOM_WORKING)    
        from robolink import import_install
        UpdateStatus(ROBOTCOM_WORKING)
        import_install("pymodbus")    
    
    UpdateStatus(ROBOTCOM_DISCONNECTED)

    # Run the driver from STDIN
    RunDriver()

    # Test the driver with a sample set of commands
    #TestDriver()
