# Type help("robolink") or help("robodk") for more information
# Press F5 to run the script
# Documentation: https://robodk.com/doc/en/RoboDK-API.html
# Reference:     https://robodk.com/doc/en/PythonAPI/index.html
# Note: It is not required to keep a copy of this file, your python script is saved with the station
from robolink import *    # RoboDK API
from robodk import *      # Robot toolbox
import math
RDK = Robolink()

# Enter the distance, in mm, to filter points min and max distance.
# For example, if we want one point each 2 mm at most, we should enter MinFilterPointDistance = 2.
# Set to -1 to not filter the points distance.
MinFilterPointDistance = -1 # in mm
MaxFilterPointDistance = -1 # in mm


# Ask the user to select the object
obj = RDK.ItemUserPick("Select the object to modify curves") # we can optionally filter by ITEM_TYPE_OBJECT or ITEM_TYPE_TOOL (not both)
# Exit if the user selects cancel
if not obj.Valid():
    quit()

# Ask the user to enter min and max distance between points
if MinFilterPointDistance <= 0:
    str_min_filter = mbox("Enter the minimum distance between points (mm).\nUse -1 to disable minimum distance filter.", entry="10")
    if not str_min_filter:
        # The user selected cancel
        quit()
    # Convert the user input to an integer
    MinFilterPointDistance = float(str_min_filter)
    if MinFilterPointDistance == 0 or MinFilterPointDistance < -1:
        RDK.ShowMessage("Invalid Filter value. Enter a value >= 1 mm or -1", False)
        raise Exception(msg)
if MaxFilterPointDistance <= 0:
    str_max_filter = mbox("Enter the maximum distance between points (mm).\nUse -1 to disable maximum distance filter.", entry="10")
    if not str_max_filter:
        # The user selected cancel
        quit()
    # Convert the user input to an integer
    MaxFilterPointDistance = float(str_max_filter)
    if MaxFilterPointDistance == 0 or MaxFilterPointDistance < -1:
        RDK.ShowMessage("Invalid Filter value. Enter a value >= 1 mm or -1", False)
        raise Exception(msg)
if MinFilterPointDistance < 0 and MaxFilterPointDistance < 0:
    quit()

# Iterate through all object curves, extract the curve points and modify point density
curve_id = 0
obj_filtered = None
stupid_flag = False

while True:
    points, name_feature = obj.GetPoints(FEATURE_CURVE, curve_id)
    # points is a double array of float with np points and xyzijk data for each point
    # point[np] = [x,y,z,i,j,k] # where xyz is the position and ijk is the tool orientation (Z axis, usually the normal to the surface)
    np = len(points)
    # when curve_id is out of bounds, an empty double array is returned
    if np == 0 or len(points[0]) < 6:
        break
        
    msg = "Modifying: " + name_feature
    print(msg)
    RDK.ShowMessage(msg, False)
    curve_id = curve_id + 1

    lastp = None
    points_filtered = []
    points_filtered.append(points[0])
    lastp = points[0]

    for i in range(1,np):
        # If distance is between bundaries
        print(distance(lastp, points[i]))
        if (distance(lastp, points[i]) > MinFilterPointDistance and distance(lastp, points[i]) < MaxFilterPointDistance):
            points_filtered.append(points[i])
            lastp = points[i]  
        # If distance is too long   
        elif distance(lastp, points[i]) > MaxFilterPointDistance:
            filter_iteration = math.ceil(distance(lastp, points[i])/MaxFilterPointDistance)
            new_point = [0,0,0,0,0,0]
            for j in range(1,filter_iteration):
                for k in range(6):
                    new_point[k] = (points[i][k] - lastp[k])/filter_iteration * j + lastp[k]
                if distance(lastp, new_point) < MinFilterPointDistance:
                    pourcentage_distance = MinFilterPointDistance/distance(lastp, points[i])
                    for k in range(6):
                        new_point[k] = (points[i][k] - lastp[k])*pourcentage_distance + lastp[k]    
                    points_filtered.append(new_point)
                    lastp = new_point      
                    i = i-1    
                    stupid_flag = True    
                    break            
                points_filtered.append(new_point)
                new_point = [0,0,0,0,0,0]
            # Stupid way of skipping the last point... Need to rethink that whole part before it bits me
            if stupid_flag == False:
                points_filtered.append(points[i])
                lastp = points[i]
            else: 
                stupid_flag = False
        # If distance is too short
        elif distance(lastp, points[i]) < MinFilterPointDistance and i == np-1:
            points_filtered.append(points[i])


    points = points_filtered


    # For the first curve: create a new object, rename it and place it in the same location of the original object
    if obj_filtered is None:
        obj_filtered = RDK.AddCurve(points, 0, False, PROJECTION_NONE)
        obj_filtered.setName(obj.Name() + " Filtered")
        obj_filtered.setParent(obj.Parent())
        obj_filtered.setGeometryPose(obj_filtered.GeometryPose())

    else:
        # After the first curve has been added, add following curves to the same object
        RDK.AddCurve(points, obj_filtered, True, PROJECTION_NONE)

# Set the curve display width
obj_filtered.setValue('DISPLAY','LINEW=2')
# Set the curve color as RGBA values [0-1.0]
obj_filtered.setColorCurve([0.0,0.5,1.0, 0.8])