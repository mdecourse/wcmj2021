from robolink import *               # import the robolink library (bridge with RoboDK)
from robodk import *
RDK = Robolink()                    # establish a link with the simulator
robot1 = RDK.Item('Fan1')      # retrieve the robot by name
#robot1.setJoints([0,0,0,0,0,0])      # set all robot axes to zero
robot2 = RDK.Item('Fan2')
#robot2.setJoints([0,0,0,0,0,0])
FrameA = RDK.Item('FrameA')
#
if RDK.Item('r2mv2').Valid():
    RDK.Item('r2mv2').Delete()
else:
    print("none")
r2mv2 = RDK.AddFrame('r2mv2', FrameA)
tool1 =RDK.Item('Fan1 Tool 1')

temp = tool1.Pose()
temp   = xyzrpw_2_pose([0, 0, 100, 0, 180, 0])
r2mv2.setPose(temp)

tref = RDK.Item('r2mv2')



#set target with respect to ref frame robo1
#?does point need to convert to world coord or joint coord?


# First: create a new target
target = RDK.AddTarget("T1", tref)
#target = Offset(0,0,0,rx=0,ry=180,rz=0)
#target.setAsCartesianTarget()       # Set the target as Cartesian (default)
#robot2.setSpeed(500)
robot2.MoveL(target)               # linear move to the approach position
# delete temp frame and target
r2mv2.Delete()


#cacl the time and distance betweent current and target

#Move in sync with robo1

#run loop again