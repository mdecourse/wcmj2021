# Type help("robolink") or help("robodk") for more information
# Press F5 to run the script
# Documentation: https://robodk.com/doc/en/RoboDK-API.html
# Reference:     https://robodk.com/doc/en/PythonAPI/index.html
# Note: It is not required to keep a copy of this file, your python script is saved with the station
from robolink import *    # RoboDK API
from robodk import *      # Robot toolbox

#import extras
import sys 
import os
import re
from math import cos, sin, pi, atan, atan2
import collections
#temp add directory of scandata.py to the path. windows environment variables
#are not available in the rdk python shell.
sys.path.append(os.path.abspath('C:/Users/matt/Dropbox/Git/wear-rebuild/python')) # temporary add wear-rebuild path
import scandata

# import gui tools
from tkinter import *
import tkinter.font as font

#--------------------------------------------
# constants

#project specific
CLOUD_FILE = 'rep.csv'
COORD_SYS = 'cylindrical' # cylindrical or cartesian
NOMINAL_R = 87
LAYER_HEIGHT_MM = 1.27
PASS_OVERLAP_MM = 9.525
RETRACT_DISTANCE = 20
TRANSITION_SPEED = 50
RAIL_START = 8600
POSITIONER_START = -80

#work cell specific
ROBOT_NAME = 'Fanuc R-1000iA/80F'
REF_NAME = 'Headstock Leader' # frame name
TOOL_NAME = 'tool' #tool name
PART_NAME = 'Clad_Path' # frame name
MACHINING_NAME = 'rep_path'
APPROACH_TRGT = 'HS Inter'
START_POS = [37.83,-36.95,-5.87,-62.43,43.06,20.09,8600, 0]
#TOOL_ORIENT = rotz(pi)
TOOL_ORIENT = rotz(0) #machining orientation
TOOL_ORIENT = roty(pi/2)*rotz(pi/2) #machining orientation

DISPLAY_PLOTS = True
REMEMBER_LAST_VALUES = True

#--------------------------------------------
# List the variables that will be remembered by the station and provided through the GUI
PARAM_VARS = []
PARAM_LABELS = []

PARAM_VARS += ["NOMINAL_R", "LAYER_HEIGHT_MM", "PASS_OVERLAP_MM"]
PARAM_LABELS += ["Build Up Radius (mm)", "Layer Height(mm)", "Pass Overlap (mm)"]

PARAM_VARS += ["TRANSITION_SPEED", "RETRACT_DISTANCE"]
PARAM_LABELS +=  ["Interpass Speed (mm/s)", "Retract Distance (mm)"]

BOOL_VARS = []
BOOL_LABELS = []

BOOL_VARS += ["DISPLAY_PLOTS"]
BOOL_LABELS +=  ["Display Plots"]

STR_VARS = []
STR_LABELS = []

STR_VARS += ["CLOUD_FILE"]
STR_LABELS += ["Cloud Filename"]

#--------------------------------------------
#data sructures

poseData = collections.namedtuple('poseData',
    'polCoords '
    'pose '
    'interPose'
)

#--------------------------------------------------------------------------------
# function definitions:

# Show message through RoboDK and the console
def ShowMsg(msg):
    print(msg)
    NotifyGUI.set(msg)
    root.update_idletasks()
    RDK.ShowMessage(msg, False)

def show_scan(pcloud):
    scn = scandata.scanObject(pcloud, COORD_SYS)
    scn_plot = scn.plot()
    scn_plot.show(block=False)

def show_ppath(toolpath):
    pltPath = toolpath.plot()
    pltPath.show(block=False)

def get_toolpath(scn):
    ShowMsg("Solving toolpath for %s" % REF_NAME)
    pth = scandata.toolpath(scn, LAYER_HEIGHT_MM, PASS_OVERLAP_MM)
    pth.slicer('depth')
    pth.generatePath()

    if DISPLAY_PLOTS:
        show_ppath(pth)

    #store cylindrical coords for each point
    pol_lines = []
    for plane in pth.path:
        for line in plane:
            pt_list = []
            for pnt in line:
                point_i = [pnt[0],pnt[1],pnt[2]]
                pt_list.append(point_i)
            pol_lines.append(pt_list)

    #store xyzijk coords for each point
    #store interpass path points
    pose_lines = []
    inter_lines = []
    for i in range(len(pth.pathCart)):
        #create welding path
        pt_list = []
        for j in range(len(pth.pathCart[i])):
            pnt = pth.pathCart[i][j]
            point_i = [pnt[0],pnt[1],pnt[2],pnt[3],pnt[4],pnt[5]] # create a point
            pt_list.append(point_i) #append the point to the list
        pose_lines.append(pt_list)

        #create transition path
        pt_trans = []
        if i < len(pth.pathCart)-1:
            for j in range(len(pth.pathInter[i])):
                pnt = pth.pathInter[i][j]
                point_i = [pnt[0],pnt[1],pnt[2],pnt[3],pnt[4],pnt[5]] # create a point
                pt_trans.append(point_i) #append the point to the list
            inter_lines.append(pt_trans)

    #store into poseData struct
    poses = poseData(polCoords=pol_lines, pose=pose_lines, interPose=inter_lines)
        
    return poses

def draw_path(rbt, uframe, utool, poses):
    """
    """
    # Create a new program
    RDK.Render(False)
    prog = RDK.AddProgram(MACHINING_NAME)
    prog.ShowInstructions(False)

    #set frames
    prog.setPoseFrame(rbt.PoseFrame())
    prog.setPoseTool(rbt.PoseTool())

    #set tool orientation to part
    orient_frame2tool = TOOL_ORIENT

    #delete last target
    target = RDK.Item('TApp', ITEM_TYPE_TARGET)
    if target.Valid():
        target.Delete()
    
    # Retrieve the current robot position:
    pose_ref = robot.Pose()

    #Start position of external axis
    rail_pos = RAIL_START
    hs_pos = POSITIONER_START

    # Specify the position of the external axes:
    external_axes = [rail_pos, hs_pos]

    #goto initial point
    approachpos = RDK.Item(APPROACH_TRGT, ITEM_TYPE_TARGET)
    #get robot joints
    appr_joints = approachpos.Joints().tolist()[0:6]

    #add target
    target = RDK.AddTarget("TApp", uframe)
    target.setAsJointTarget()
    target.setJoints(appr_joints + external_axes)
    
    prog.MoveL(target)

    #initialize object
    points_object = None
    new_obj = True
    
    
    t_i = 1
    #go through each line
    for i in range(len(poses.pose)):
        # add curve
        if i == 0:
            points_object = RDK.AddCurve(poses.pose[i])
            points_object.setParent(uframe)
            points_object.setName(PART_NAME)
        else:
            RDK.AddCurve(poses.pose[i],points_object, True)

        # get transition path
        trans_path = []
        if i < len(poses.pose)-1:
            trans_path = poses.interPose[i]

        #get pass z difference for rail offset
        if i > 0:
            rail_pos = RAIL_START - (poses.pose[i][0][2] - poses.pose[0][0][2])
        # *****
        # ** pat might be mirrored or backwards
        for j in reversed(range(len(poses.pose[i]))):
            # get pose
            p_i = xyzrpw_2_pose(poses.pose[i][j])
            #create target
            prog.ShowTargets(False)
            target = RDK.AddTarget('T%i' % (t_i), uframe)
            target.setAsCartesianTarget()
            #get theta for headstock
            hs_pos = atan2(poses.pose[i][j][0], poses.pose[i][j][1])* 180 / pi
            external_axes = [rail_pos, hs_pos]
            target.setJoints([0,0,0,0,0,0] + external_axes)
            target.setPose(p_i*orient_frame2tool)
            #move to target
            prog.MoveL(target)
            #increment target index
            t_i += 1

        #make transition path
        if trans_path:
            for j in reversed(range(len(trans_path))):
                # get pose
                p_i = xyzrpw_2_pose(trans_path[j])
                #create target
                prog.ShowTargets(False)
                target = RDK.AddTarget('T%i' % (t_i), uframe)
                target.setAsCartesianTarget()
                #get theta for headstock
                hs_pos = atan2(trans_path[j][0], trans_path[j][1])* 180 / pi
                external_axes = [rail_pos, hs_pos]
                target.setJoints([0,0,0,0,0,0] + external_axes)
                target.setPose(p_i*orient_frame2tool)
                #move to target
                prog.MoveL(target)
                #increment target index
                t_i += 1

    # hide targets from tree
    prog.ShowTargets(False)
    
    RDK.Render(True)
    
    return prog

def machining(points_object, ref_frame):
    """
    """
    curve_follow = RDK.Item(MACHINING_NAME, ITEM_TYPE_MACHINING)
    if not curve_follow.Valid():
        curve_follow = RDK.AddMachiningProject(MACHINING_NAME)

    # Use the current reference frame:
    curve_follow.setPoseFrame(ref_frame)

    #set transition speed
    curve_follow.setSpeed(TRANSITION_SPEED)
    #set tool orientation
    curve_follow.setPose(TOOL_ORIENT)
    #set preferred start joints
    curve_follow.setJoints(START_POS)

    #set curve
    prog, status = curve_follow.setMachiningParameters(part=points_object)
    print(status)
    if status == 0:
        ShowMsg("Program %s generated successfully" % REF_NAME)
    else:
        ShowMsg("Issues found generating program %s!" % REF_NAME)
    
    # get the program name
    prog.RunProgram()

def make_machining_curve(poses, ref_frame):
    """
    """
    #robodk points
    points_object = None

    for i in range(len(poses.pose)):
        #store interpass lines
        trans_path = []
        #if i < len(poses.pose)-1:
        #    trans_path = poses.interPose[i]

        #create welding path
        if points_object is None:
            # Add the points as an object in the RoboDK station tree
            points_object = RDK.AddCurve(poses.pose[i])
            # Add the points to the reference and set the reference name
            points_object.setParent(ref_frame)
            points_object.setName(PART_NAME)
            if trans_path:
                RDK.AddCurve(trans_path,points_object, True)
        else:
            # Add curve to existing object
            RDK.AddCurve(poses.pose[i],points_object, True)
            if trans_path:
                RDK.AddCurve(trans_path,points_object, True)

    #create follow points project, and add points
    machining(points_object, ref_frame)

    #run output machinging program
    prog_main = RDK.Item(MACHINING_NAME, ITEM_TYPE_PROGRAM)

    return prog_main


def Main(robot, user_frame, tool_frame):
    """
    """
    
    # Remove curve objects
    obj_delete = RDK.Item(PART_NAME, ITEM_TYPE_OBJECT)
    if obj_delete.Valid():
        obj_delete.Delete()
    # Remove previous toolpath
    obj_delete = RDK.Item(MACHINING_NAME, ITEM_TYPE_PROGRAM)
    if obj_delete.Valid():
        obj_delete.Delete()

    #get path of rdk file. Use to retrieve project files
    #in same directory as rdk file.
    path_stationfile = RDK.getParam('PATH_OPENSTATION')
    #get path for cloud file and load it
    pcdpath = path_stationfile + '/' + CLOUD_FILE
    pcdfile = scandata.PointCloud(pcdpath)

    if DISPLAY_PLOTS:
        show_scan(pcdfile)

    #modify cloud data into a cylindrical numpy array and normalized to  a diameter 
    scan = scandata.scanObject(pcdfile, COORD_SYS)
    scan.normalize_zaxis(NOMINAL_R)

    #retrieve toolpath
    #store line pose data in poseData structure
    poses = get_toolpath(scan)

    #manually draw path
    prog_main = draw_path(robot, user_frame, tool_frame, poses)
    
    #make curve follow project from paths
    #prog_main = make_machining_curve(poses, user_frame)

    # Start the program simulation:    
    prog_main.RunProgram()
    ShowMsg("Done!!")
    

#--------------------------------------------------------------------------------
# Program start

#start rdk api
RDK = Robolink()

# Prompt the user to select a robot (if only one robot is available it will select that robot automatically)
robot = RDK.Item(ROBOT_NAME, ITEM_TYPE_ROBOT)
#get userframe
user_frame = RDK.Item(REF_NAME, ITEM_TYPE_FRAME)
#get toolframe
tool_frame = RDK.Item(TOOL_NAME, ITEM_TYPE_TOOL)

#set active frame
robot.setPoseFrame(user_frame)
#set active tool
robot.setPoseTool(tool_frame)

# Retrieve Global parameters or set defaults as found in RoboDK
if REMEMBER_LAST_VALUES:
    for strvar in PARAM_VARS:
        var_value = RDK.getParam(strvar)
        if var_value is not None:
            exec(strvar + " = " + str(var_value))

# Generate the main window
root = Tk()
root.title("Toolpath parameters")

# define a label to notify the user
NotifyGUI = StringVar()


#-----------------------------------------
# Create a GUI menu using tkinter

for strvar, hint in zip(STR_VARS, STR_LABELS):
    var = eval(strvar)
    print(var)
    txtvar = "txt" + strvar
    exec(txtvar + " = StringVar()")
    exec(txtvar + ".set('" + var + "')")
    exec("Label(root, text='" + hint + "').pack()")
    exec("Entry(root, textvariable=" + txtvar + ").pack()")

for strvar, hint in zip(PARAM_VARS, PARAM_LABELS):
    var = eval(strvar)
    txtvar = "txt" + strvar
    exec(txtvar + " = StringVar()")
    exec(txtvar + ".set(str(" + str(var) + "))")
    exec("Label(root, text='" + hint + "').pack()")
    exec("Entry(root, textvariable=" + txtvar + ").pack()")

for boolvar, hint in zip(BOOL_VARS, BOOL_LABELS):
    var = eval(boolvar)
    txtvar = "bool" + boolvar
    boxvar = 'c_' + boolvar 
    exec(txtvar + " = IntVar()")
    exec(boxvar + "=Checkbutton(root, text='" + hint + "', variable="+txtvar+")")
    exec(boxvar +".pack()")
    if var:
        exec(boxvar + ".select()")

# Add a button and default action to execute the current choice of the user
def btnUpdate():
    # List the global variables so that we can read or modify the latest values
    #exec(PARAM_GLOBALS)

    try:        
        for strvar in PARAM_VARS:
            # Update global variable
            exec("%s = float(txt%s.get())" % (strvar, strvar), globals())

        for strvar in STR_VARS:
            # Update global variable
            exec("%s = txt%s.get()" % (strvar, strvar), globals())
            
        for boolvar in BOOL_VARS:
            # Update global variable
            exec("%s = bool(bool%s.get())" % (boolvar, boolvar), globals())
            
    except Exception as e:
        RDK.ShowMessage("Invalid input!! " + str(e), False)
        return

    # Remember the last settings in the RoboDK station
    for strvar in PARAM_VARS:
        value = eval(strvar)
        RDK.setParam(strvar, value)
        
    for boolvar in BOOL_VARS:
        value = eval(boolvar)
        RDK.setParam(boolvar, value)

    # Run the main program once all the global variables have been set
    Main(robot, user_frame, tool_frame)


# Add an update button that calls btnUpdate()
font_large = font.Font(family='Helvetica', size=18, weight=font.BOLD)
Label(root, text=" ").pack() # Just a spacer
Label(root, textvariable=NotifyGUI).pack() # information variable
Button(root, text='Update', font=font_large, width=20, height=4, command=btnUpdate, bg='green').pack()

# Important to display the graphical user interface
root.mainloop()



