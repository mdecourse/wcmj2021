    #type help("robolink") or help("robodk") for more information
    #(note: you do not need to keep a copy of this file, your python script is saved with the station)
    from robolink import *    # API to communicate with robodk
    from robodk import *      # basic matrix operations
     
     
    # Setup global parameters
    BALL_DIAMETER = 100 # diameter of one ball
    APPROACH = 100      # approach distance with the robot, in mm
    nTCPs = 6           # number of TCP's in the tool
     
     
    def box_calc(BALLS_SIDE=4, BALLS_MAX=None):
        """Calculates a list of points (ball center) as if the balls were stored in a box"""
        if BALLS_MAX is None: BALLS_MAX = BALLS_SIDE**3
        xyz_list = []
        for h in range(BALLS_SIDE):
            for i in range(BALLS_SIDE):
                for j in range(BALLS_SIDE):
                    xyz_list = xyz_list + [[(i+0.5)*BALL_DIAMETER, (j+0.5)*BALL_DIAMETER, (h+0.5)*BALL_DIAMETER]]
                    if len(xyz_list) >= BALLS_MAX:
                        return xyz_list
        return xyz_list
     
    def pyramid_calc(BALLS_SIDE=4):
        """Calculates a list of points (ball center) as if the balls were place in a pyramid"""
        #the number of balls can be calculated as: int(BALLS_SIDE*(BALLS_SIDE+1)*(2*BALLS_SIDE+1)/6)
        BALL_DIAMETER = 100
        xyz_list = []
        sqrt2 = 2**(0.5)
        for h in range(BALLS_SIDE):
            for i in range(BALLS_SIDE-h):
                for j in range(BALLS_SIDE-h):
                    height = h*BALL_DIAMETER/sqrt2 + BALL_DIAMETER/2
                    xyz_list = xyz_list + [[i*BALL_DIAMETER + (h+1)*BALL_DIAMETER*0.5, j*BALL_DIAMETER + (h+1)*BALL_DIAMETER*0.5, height]]
        return xyz_list
     
    def balls_setup(frame, positions):
        """Place a list of balls in a reference frame. The reference object (ball) must have been previously copied to the clipboard."""
        nballs = len(positions)
        step = 1/(nballs - 1)
        for i in range(nballs):
            newball = frame.Paste()
            newball.setName('ball ' + str(i)) #set item name
            newball.setPose(transl(positions[i])) #set item position with respect to parent
            newball.setVisible(True, False) #make item visible but hide the reference frame
            newball.Recolor([1-step*i, step*i, 0.2, 1]) #set RGBA color
     
    def cleanup_balls(parentnodes):
        """Deletes all child items whose name starts with \"ball\", from the provided list of parent items."""
        todelete = []
        for item in parentnodes:
            todelete.append(item.Childs())
        todelete = robottool.Childs() + frame1.Childs() + frame2.Childs()
        for item in todelete:
            if item.Name().startswith('ball'):
                item.Delete()
     
    def TCP_On(toolitem, tcp_id):
        """Attaches the closest object to the toolitem Htool pose,
        furthermore, it will output appropriate function calls on the generated robot program (call to TCP_On)"""
        toolitem.AttachClosest()
        toolitem.RL().RunMessage('Set air valve %i on' % (tcp_id+1))
        toolitem.RL().RunProgram('TCP_On(%i)' % (tcp_id+1));
            
    def TCP_Off(toolitem, tcp_id, itemleave=0):
        """Detaches the closest object attached to the toolitem Htool pose,
        furthermore, it will output appropriate function calls on the generated robot program (call to TCP_Off)"""
        toolitem.DetachClosest(itemleave)
        toolitem.RL().RunMessage('Set air valve %i off' % (tcp_id+1))
        toolitem.RL().RunProgram('TCP_Off(%i)' % (tcp_id+1));
     
     
    #----------------------------------------------------------
    # the program starts here:
     
    # Start the API with RoboDK
    RL = Robolink()
     
    # Turn off automatic rendering (faster)
    RL.Render(False)
    #RL.Set_Simulation_Speed(500); # controls the simulation speed
     
    # Gather required items from the station tree
    robot = RL.Item('Fanuc M-710iC/50')
    robottool = RL.Item('Tool')
    frame1 = RL.Item('Table 1')
    frame2 = RL.Item('Table 2')
     
    # Copy a ball
    ballref = RL.Item('reference ball')
    ballref.Copy()
     
    # Run a station program to replace the two tables
    prog_reset = RL.Item('Replace objects')
    prog_reset.RunProgram()
     
    # Call custom procedure to remove old objects
    cleanup_balls([robottool, frame1, frame2])
     
    # Make a list of positions to place the objects
    frame1_list = pyramid_calc(4)
    frame2_list = pyramid_calc(4)
     
    # Programmatically place the objects with a custom-made procedure
    balls_setup(frame1, frame1_list)
     
    # Turn on automatic rendering
    RL.Render(True)
     
    # Calculate tool frames for the suction cup tool of 6 suction cups
    TCPs = []
    for i in range(nTCPs):
        TCPs = TCPs + [transl(0,0,100)*rotz((360/nTCPs)*i*pi/180)*transl(125,0,0)*roty(pi/2)]
     
    # Move balls    
    robot.setTool(robottool) # this is automatic if there is only one tool
    nballs_frame1 = len(frame1_list)
    nballs_frame2 = len(frame2_list)
    idTake = nballs_frame1 - 1
    idLeave = 0
    idTCP = 0
    target_app_frame = transl(2*BALL_DIAMETER, 2*BALL_DIAMETER, 4*BALL_DIAMETER)*roty(pi)*transl(0,0,-APPROACH)
     
    while idTake >= 0:
        # ------------------------------------------------------------------
        # first priority: grab as many balls as possible
        # the tool is empty at this point, so take as many balls as possible (up to a maximum of 6 -> nTCPs)
        ntake = min(nTCPs, idTake + 1)
     
        # approach to frame 1
        robot.setFrame(frame1)
        robottool.setHtool(TCPs[0])
        robot.MoveJ([0,0,0,0,10,-200])
        robot.MoveJ(target_app_frame)
     
        # grab ntake balls from frame 1
        for i in range(ntake):
            Htool = TCPs[i]
            robottool.setHtool(Htool)
            # calculate target wrt frame1: rotation about Y is needed since Z and X axis are inverted
            target = transl(frame1_list[idTake])*roty(pi)*rotx(30*pi/180)
            target_app = target*transl(0,0,-APPROACH)
            idTake = idTake - 1        
            robot.MoveL(target_app)
            robot.MoveL(target)
            TCP_On(robottool, i)
            robot.MoveL(target_app)
     
        # ------------------------------------------------------------------
        # second priority: unload the tool     
        # approach to frame 2 and place the tool balls into table 2
        robottool.setHtool(TCPs[0])
        robot.MoveJ(target_app_frame)
        robot.MoveJ([0,0,0,0,10,-200])
        robot.setFrame(frame2)    
        robot.MoveJ(target_app_frame)
        for i in range(ntake):
            Htool = TCPs[i]
            robottool.setHtool(Htool)
            if idLeave > nballs_frame2-1:
                raise Exception("No room left to place objects in Frame 2")
            
            # calculate target wrt frame1: rotation of 180 about Y is needed since Z and X axis are inverted
            target = transl(frame2_list[idLeave])*roty(pi)*rotx(30*pi/180)
            target_app = target*transl(0,0,-APPROACH)
            idLeave = idLeave + 1        
            robot.MoveL(target_app)
            robot.MoveL(target)
            TCP_Off(robottool, i, frame2)
            robot.MoveL(target_app)
     
        robot.MoveJ(target_app_frame)
     
    # Move home when the robot finishes
    robot.MoveJ([0,0,0,0,10,-200])