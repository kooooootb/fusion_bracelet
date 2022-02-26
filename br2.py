#Author-
#Description-

from asyncio.windows_events import NULL
from contextlib import nullcontext
from warnings import catch_warnings
import adsk.core, adsk.fusion, adsk.cam, traceback, math

_app = None
_ui = None
_design = None
_rowNumber = 0

_handlers = []

##############################################################################

# Inputs
sketch_selInput = None
cylinder_selInput = None
xscale_float_spinnerInput = None
yscale_float_spinnerInput = None
radiusOffset_float_spinnerInput = None
thickenDepth_float_spinnerInput = None
splitFace_boolinput = None

def point3DStr(pt):
    return (str(pt.x) + ',' + str(pt.y) + ',' + str(pt.z))

def getSketchCurvesBoundingBox():
    bbox = None
    if sketch_selInput != None:
        for i in range(sketch_selInput.selectionCount):
            sel = sketch_selInput.selection(i)
            if bbox == None:
                bbox = sel.entity.boundingBox.copy()
            else:
                bbox.combine(sel.entity.boundingBox)

    return bbox

def mapPoint2Curve(x, y, radius, xOrig, yOrig, zOrig):
    x2 = radius * math.cos(x / radius) + xOrig
    y2 = radius * math.sin(x / radius) + yOrig
    z2 = y + zOrig
    return x2, y2, z2

# Hack to test coordinate values
def equal_close(f1,f2,sig_digits):
    return ( f1 == f2 or
             int(f1 * 10 ** sig_digits) == int(f2 * 10 ** sig_digits)
           )
           
def wrapSketch(cylFace, sketchCurves):
    # if cylSelInput == None or sketchSelInput == None or _design == None:
        # return

    # if sketchSelInput.selectionCount < 1 or cylSelInput.selectionCount != 1:
        # return

    splitFace_boolinput = False

    xScale = 1.0
    if xscale_float_spinnerInput != None:
        xScale = xscale_float_spinnerInput.value

    yScale = 1.0
    if yscale_float_spinnerInput != None:
        yScale = yscale_float_spinnerInput.value

    radiusOffset = 0.1
    if radiusOffset_float_spinnerInput != None:
        radiusOffset = radiusOffset_float_spinnerInput.value

    thickenDepth = 0.2
    if thickenDepth_float_spinnerInput != None:
        thickenDepth = thickenDepth_float_spinnerInput.value
        
    # Creating a sketch will empty the selection input.  Cache the selected entities
    # so we don't lose access to them when new sketch created.
    # sketchCurves = []
    # for i in range(sketchSelInput.selectionCount):
    #     sketchCurves.append(sketchSelInput.selection(i).entity)

    # cache cylinder face
    # cylFace = cylSelInput.selection(0).entity

    try:
        # Get the root component of the active design.
        rootComp = _design.rootComponent
        # Create a new sketch on the xy plane.
        sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        sketch.name = 'WrapSketch'

        cylGeom = cylFace.geometry

        # Collection of curves to use as splitting tools
        splitToolObjCol = adsk.core.ObjectCollection.create()

        # Iterate over the sketch curves
        for sketchCurve in sketchCurves:
            obj_type = sketchCurve.objectType

            if obj_type == 'adsk::fusion::SketchArc':
                print('SketchArc : unsupported')
            elif obj_type == 'adsk::fusion::SketchCircle':
                print('SketchCircle : unsupported')
            elif obj_type == 'adsk::fusion::SketchEllipse':
                print('SketchEllipse : unsupported')
            elif obj_type == 'adsk::fusion::SketchEllipticalArc':
                print('SketchEllipticalArc : unsupported')
            elif obj_type == 'adsk::fusion::SketchFittedSpline':
                #print('SketchFittedSpline')
                # Get this splines points
                fitPoints = sketchCurve.fitPoints

                # Create an object collection for the points.
                newFitPoints = adsk.core.ObjectCollection.create()

                for ip in range(fitPoints.count):
                    pt = fitPoints.item(ip).geometry
                    # map the old point to cylinder
                    xNew, yNew, zNew = mapPoint2Curve(pt.x * xScale, pt.y * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                    newFitPoints.add(adsk.core.Point3D.create(xNew, yNew, zNew)) #cylGeom.origin.z + zNew))  origin is in middle of cylinder.  Need to find length and offset.

                # Create the spline.
                newFittedSpline = sketch.sketchCurves.sketchFittedSplines.add(newFitPoints)
                if newFittedSpline != None:
                    newFittedSpline.isClosed = sketchCurve.isClosed

                # Split the face with this spline?
                if splitFace_boolinput:
                    splitToolObjCol.add(newFittedSpline)

            elif obj_type == 'adsk::fusion::SketchFixedSpline':
                print('SketchFixedSpline : unsupported')
                # TODO Convert fixed to fitted spline
            elif obj_type == 'adsk::fusion::SketchLine':
                #print('SketchLine')
                # Convert line to arc on cylinder face
                ptStart = sketchCurve.startSketchPoint.geometry
                ptEnd   = sketchCurve.endSketchPoint.geometry
                
                if ptStart != ptEnd:
                    # map the points to cylinder
                    xStart, yStart, zStart = mapPoint2Curve(ptStart.x * xScale, ptStart.y * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                    xEnd, yEnd, zEnd = mapPoint2Curve(ptEnd.x * xScale, ptEnd.y * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                    
                    # Check for a vertical line which will just map to a line
                    # NOTE: Hack for comparison. Needed because small rounding error will cause == to fail and
                    # then creating arc call will fail when given vertical points.  So check for vertical and
                    # almost vertical lines.
                    if equal_close(ptStart.x, ptEnd.x, 6):
                        lines = sketch.sketchCurves.sketchLines
                        lines.addByTwoPoints(adsk.core.Point3D.create(xStart, yStart, zStart), adsk.core.Point3D.create(xEnd, yEnd, zEnd))
                    else:
                        # mapping to a cylinder so create an arc
                        xCtr, yCtr, zCtr = mapPoint2Curve(((ptStart.x + ptEnd.x) / 2.0) * xScale, ((ptStart.y + ptEnd.y) / 2.0) * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                        
                        sketchArcs = sketch.sketchCurves.sketchArcs
                        sketchArcs.addByThreePoints(adsk.core.Point3D.create(xStart, yStart, zStart),
                                                    adsk.core.Point3D.create(xCtr, yCtr, zCtr),
                                                    adsk.core.Point3D.create(xEnd, yEnd, zEnd))
                else:
                    print('Found 0 Length Sketch Line')
                
            elif obj_type == 'adsk::fusion::SketchPoint':
                #print('SketchPoint')
                pt = sketchCurve.geometry
                
                # map the point to cylinder
                xNew, yNew, zNew = mapPoint2Curve(pt.x * xScale, pt.y * yScale, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                
                sketchPoints = sketch.sketchPoints
                sketchPoints.add(adsk.core.Point3D.create(xNew, yNew, zNew))
            else:
                print('Sketch type unsupported: ' + obj_type)

        # Split the face with curves?
        if splitFace_boolinput:

            # TODO : Split API doesn't allow setting Split Type with API.  Use patches for now.
#==============================================================================
#             # Get SplitFaceFeatures
#             splitFaceFeats = rootComp.features.splitFaceFeatures
# 
#             # Set faces to split
#             objCol = adsk.core.ObjectCollection.create()
#             objCol.add(cylFace)
# 
#             # Create SplitFaceFeatureInput
#             splitFaceInput = splitFaceFeats.createInput(objCol, splitToolObjCol, True)
#             #splitFaceInput.splittingTool = splitToolObjCol
# 
#             # Create split face feature
#             splitFaceFeats.add(splitFaceInput)
#==============================================================================

            # Create patches for each of the curves. Then thicken the patches
            # to create new bodies. 
            patches = rootComp.features.patchFeatures
            newPatches = []
            
            for iCurve in range(splitToolObjCol.count):
                curve = splitToolObjCol.item(iCurve)
                patchInput = patches.createInput(curve, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                newPatch = patches.add(patchInput)
                if newPatch != None:
                    newPatches.append(newPatch)
                    
            # Thicken patch features
            thickenFeatures = rootComp.features.thickenFeatures
            for aPatch in newPatches:
                bodies = aPatch.bodies
                inputSurfaces = adsk.core.ObjectCollection.create()
                for body in bodies:
                    inputSurfaces.add(body)

                thickness = adsk.core.ValueInput.createByReal(thickenDepth)
                thickenInput = thickenFeatures.createInput(inputSurfaces, thickness, False,  adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                thickenFeatures.add(thickenInput)
        
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

##############################################################################

def addRowToTable(tableInput):
    global _rowNumber
    #get commandInput associated with command
    cmdInputs = adsk.core.CommandInputs.cast(tableInput.commandInputs)

    valueInput = cmdInputs.addValueInput('TableInput_value{}'.format(_rowNumber), 'Value', 'cm', adsk.core.ValueInput.createByReal(_rowNumber))
    stringInput =  cmdInputs.addStringValueInput('TableInput_string{}'.format(_rowNumber), 'String', str(_rowNumber))
    spinnerInput = cmdInputs.addIntegerSpinnerCommandInput('spinnerInt{}'.format(_rowNumber), 'Integer Spinner', 0 , 100 , 2, int(_rowNumber))
   
    row = tableInput.rowCount
    tableInput.addCommandInput(valueInput, row, 0)
    tableInput.addCommandInput(stringInput, row, 1)
    tableInput.addCommandInput(spinnerInput, row, 2)

    _rowNumber = _rowNumber + 1

def getSelectedEntities(selectionInput):
    entities = []
    for x in range(0, selectionInput.selectionCount):
        mySelection = selectionInput.selection(x)
        selectedObj = mySelection.entity
        if type(selectedObj) is adsk.fusion.BRepBody or type(selectedObj) is adsk.fusion.Component:
            entities.append(selectedObj)
        elif type(selectedObj) is adsk.fusion.Occurrence:
            entities.append(selectedObj.component)
    return entities

def updateSliders(sliderInputs):
    spinner = sliderInputs.itemById("slider_controller")
    value = spinner.value
    #check ranges correctness
    if value > spinner.maximumValue or value < spinner.minimumValue:
        return
    
    #delete all available sliders
    toRemove = []
    for i in range(sliderInputs.count):
        input = sliderInputs.item(i)
        if input.objectType == adsk.core.FloatSliderCommandInput.classType():
            toRemove.append(input)

    for input in toRemove:
        input.deleteMe()

    for i in range(1, value + 1):
        id = str(i)
        sliderInputs.addFloatSlidersCommandInput("slider_configuration_" + id, "slider_" + id, "cm", 0, 10.0 * value)

class MyCommandInputChangedHandler(adsk.core.InputChangedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            eventArgs = adsk.core.InputChangedEventArgs.cast(args)
            inputs = eventArgs.inputs
            cmdInput = eventArgs.input

            #controller for slider otdel'no
            if cmdInput.id == "slider_controller":
                sliderGroup = adsk.core.GroupCommandInput.cast(cmdInput.parentCommandInput)
                sliderInputs = sliderGroup.children
                updateSliders(sliderInputs)
            else:
                tableInput = inputs.itemById('table')
                if cmdInput.id == 'tableAdd':
                    addRowToTable(tableInput)
                elif cmdInput.id == 'tableDelete':
                    if tableInput.selectedRow  == -1:
                        _ui.messageBox('Select one row to delete.')
                    else:
                        tableInput.deleteRow(tableInput.selectedRow)

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class MyCommandDestroyHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()
    
    def notify(self, args):
        try:
            adsk.terminate()
        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class MyCommandExecuteHandler(adsk.core.CommandEventHandler):
    def __init__(self):
        super().__init__()

    def notify(self, args):
        try:
            command = args.firingEvent.sender
            inputs = command.commandInputs

            radius = 0
            height = 0
            thickness = 0
            text = 0

            for input in inputs:
                if input.id == 'Radius':
                    if input.value <= 0:
                        input.value = 1
                    radius = input.value
                if input.id == 'Height':
                    height = input.value
                if input.id == 'Thickness':
                    thickness = input.value
                if input.id == 'Text':
                    text = input.value
# set initial variables
            rootComp = _app.activeProduct.rootComponent
            sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
# create sketch circle
            circles = sketch.sketchCurves.sketchCircles
            circle = circles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), radius)
# create cylinder
            extrudes = rootComp.features.extrudeFeatures
            prof = sketch.profiles.item(circles.count - 1)
            extInput = extrudes.createInput(prof, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            extInput.setThinExtrude(adsk.fusion.ThinExtrudeWallLocation.Center, adsk.core.ValueInput.createByReal(thickness))
            extInput.setSymmetricExtent(adsk.core.ValueInput.createByReal(height), False)
            extrude = extrudes.add(extInput)
# create text
            sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
            texts = sketch.sketchTexts
            textInput = texts.createInput2(text, 0.5)
            textInput.setAsMultiLine(adsk.core.Point3D.create(0, 0, 0), adsk.core.Point3D.create(10, 5, 0), adsk.core.HorizontalAlignments.LeftHorizontalAlignment, adsk.core.VerticalAlignments.TopVerticalAlignment, 0)
            text = texts.add(textInput)
            curves = text.explode()
# put text on cylinder's face
            index = 0
            if extrude.sideFaces.item(1).area > extrude.sideFaces.item(0).area:
                index = 1
            wrapSketch(extrude.sideFaces.item(index), curves)
# move text
            textSketch = rootComp.sketches.itemByName('WrapSketch')
            textCurves = textSketch.sketchCurves
            transform = textSketch.transform
            dx = 0
            dy = 0
            # dz = textSketch.sketchPoints.item(0).geometry.z * (-1)
            dz = textCurves.item(0).boundingBox.minPoint.z * (-1)
            # dz = -5
            transform.translation = adsk.core.Vector3D.create(dx,dy,dz)
            curvesCol = adsk.core.ObjectCollection.create()
            for sk in textCurves:
                curvesCol.add(sk)
            textSketch.move(curvesCol, transform)
# array for created faces
            faces = []
            numberOfFaces = 0
# creating faces using patches
            while curvesCol.count > 0:
                currentCurvesInput = adsk.core.ObjectCollection.create()#collection for edges on current attempt
                patchFeatures = rootComp.features.patchFeatures
                input = None
                index = 0
                success = False
                resFaces = None
                # try to create patch, if cant => add next edge to collection and try again
                while resFaces == None or resFaces.isValid == False:
                    currentCurvesInput.add(curvesCol.item(index))
                    input = patchFeatures.createInput(currentCurvesInput, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                    index += 1
                    try:
                        resFaces = patchFeatures.add(input)
                    except:
                        success = False
                faces.append(resFaces.faces.item(0))
                numberOfFaces += 1
                # _ui.messageBox(str(index))
                # delete used curves from sketch
                for curve in currentCurvesInput:
                    curve.deleteMe()
                # recreate collection without deleted curves
                curvesCol = adsk.core.ObjectCollection.create()
                for sk in textCurves:
                    curvesCol.add(sk)
# extrude created faces
            _ui.messageBox(str(numberOfFaces))
            for face in faces:
                # create collection of all edges in current face
                edges = face.edges
                edgesCol = adsk.core.ObjectCollection.create()
                for edge in edges:
                    edgesCol.add(edge)
                # create profile
                profile = rootComp.createBRepEdgeProfile(edgesCol)
                # set distance
                distance = adsk.fusion.DistanceExtentDefinition.create(adsk.core.ValueInput.createByReal(5)) 
                # extrude
                extInput = extrudes.createInput(profile, adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
                extInput.setOneSideExtent(distance, adsk.fusion.ExtentDirections.NegativeExtentDirection)
                extInput.isSolid = False
                ext = extrudes.add(extInput)




        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

class myCommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def __init__(self):
        super().__init__()
    def notify(self, args):
        try:
            # Get the command that was created.
            cmd = adsk.core.Command.cast(args.command)

            # Connect to the command destroyed event.
            onDestroy = MyCommandDestroyHandler()
            cmd.destroy.add(onDestroy)
            _handlers.append(onDestroy)

            # Connect to the input changed event.           
            onInputChanged = MyCommandInputChangedHandler()
            cmd.inputChanged.add(onInputChanged)
            _handlers.append(onInputChanged)    

            onExecute = MyCommandExecuteHandler()
            cmd.execute.add(onExecute)
            _handlers.append(onExecute)

            # Get the CommandInputs collection associated with the command.
            inputs = cmd.commandInputs

            # Create a tab input.
            tabCmdInput1 = inputs.addTabCommandInput('tab_1', 'Tab 1')
            tab1ChildInputs = tabCmdInput1.children

            # Create value input.
            tab1ChildInputs.addValueInput('Radius', 'Radius', '', adsk.core.ValueInput.createByReal(1.0))

            # Create value input.
            tab1ChildInputs.addValueInput('Height', 'Height', '', adsk.core.ValueInput.createByReal(1.0))

            # Create value input.
            tab1ChildInputs.addValueInput('Thickness', 'Thickness', '', adsk.core.ValueInput.createByReal(0.2))

            # Create value input.
            tab1ChildInputs.addStringValueInput('Text', 'Text', 'Sample')

        except:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))


def run(context):
    try:
        global _app, _ui, _design
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        _design = _app.activeProduct

        cmdDef = _ui.commandDefinitions.itemById('a')
        if not cmdDef:
            cmdDef = _ui.commandDefinitions.addButtonDefinition('a', 'my scale parameters', ' ')

        onCommandCreated = myCommandCreatedHandler()
        cmdDef.commandCreated.add(onCommandCreated)
        _handlers.append(onCommandCreated)

        inputs = adsk.core.NamedValues.create()
        cmdDef.execute(inputs)

        adsk.autoTerminate(False)

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
