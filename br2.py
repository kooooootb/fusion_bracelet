#Author-
#Description-

from asyncio.windows_events import NULL
from contextlib import nullcontext
from sys import maxsize
from tkinter.tix import INTEGER, MAX
from turtle import Turtle, distance
from warnings import catch_warnings
import adsk.core, adsk.fusion, adsk.cam, traceback, math

_app = None
_ui = None
_design = None
_rowNumber = 0
_maxint = 99999999

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

def getMiddle(edge):
    startPoint = edge.boundingBox.maxPoint
    endPoint = edge.boundingBox.minPoint
    x1 = startPoint.x
    y1 = startPoint.y
    z1 = startPoint.z
    x2 = endPoint.x
    y2 = endPoint.y
    z2 = endPoint.z
    middlePoint = adsk.core.Point3D.create((x1+x2)/2, (y1+y2)/2, (z1+z2)/2)
    return middlePoint

def findNearestEdge(edge:adsk.fusion.BRepEdge, loop:adsk.fusion.BRepLoop):
    middlePoint = getMiddle(edge)
    resEdge:adsk.fusion.BRepEdge = loop.edges.item(0)
    distance = middlePoint.distanceTo(getMiddle(loop.edges.item(0)))
    for pairEdge in loop.edges:
        tmpDistance = middlePoint.distanceTo(getMiddle(pairEdge))
        if tmpDistance < distance:
            distance = tmpDistance
            resEdge = pairEdge
    return resEdge


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
           
def wrapSketch(cylFace, sketchCurves, radius):
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

    radiusOffset = radius
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

            radius = 2.0
            height = 1.0
            thickness = 0.2
            text = 'Sample'
            fontSize = 0.5
            radiusOffset = 0.1
            characterSpacing = 0
            isSingleLined = True

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
                if input.id == 'Font size':
                    fontSize = input.value
                if input.id == 'Radius offset':
                    radiusOffset = input.value
                if input.id == 'Character spacing':
                    characterSpacing = input.value
                if input.id == 'Single line':
                    isSingleLined = input.value

# set initial variables
            rootComp: adsk.fusion.Component = _app.activeProduct.rootComponent
            sketch:adsk.fusion.Sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
            timeline:adsk.fusion.Timeline = _design.timeline

# set features and operations
            extrudes = rootComp.features.extrudeFeatures
            patchFeatures = rootComp.features.patchFeatures
            splitFaceFeatures = rootComp.features.splitFaceFeatures
            loftFeatures = rootComp.features.loftFeatures
            combineFeatures = rootComp.features.combineFeatures
            removeFeatures = rootComp.features.removeFeatures
            unstitchFeatures = rootComp.features.unstitchFeatures
            offsetFeatures = rootComp.features.offsetFeatures
            stitchFeatures = rootComp.features.stitchFeatures
            reverseNormalFeatures = rootComp.features.reverseNormalFeatures
            scaleFeatures = rootComp.features.scaleFeatures
            ruledFeatures = rootComp.features.ruledSurfaceFeatures

            newBodyOperation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
            joinBodyOperation = adsk.fusion.FeatureOperations.JoinFeatureOperation

# create cylinder
            circles = sketch.sketchCurves.sketchCircles
            circle = circles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), radius)
            circleProfile = rootComp.createOpenProfile(circle)

            extInput = extrudes.createInput(circleProfile, newBodyOperation)
            extInput.setThinExtrude(adsk.fusion.ThinExtrudeWallLocation.Center, adsk.core.ValueInput.createByReal(thickness))
            extInput.setSymmetricExtent(adsk.core.ValueInput.createByReal(height / 2), False)
            circleExtrude = extrudes.add(extInput)
            sideFaceIndex = 0
            if circleExtrude.sideFaces.item(1).area > circleExtrude.sideFaces.item(0).area:
                sideFaceIndex = 1
            cylinderSideFace = circleExtrude.sideFaces.item(sideFaceIndex)
            cylinderBody = circleExtrude.bodies.item(0)

# create text
            sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
            texts = sketch.sketchTexts
            textInput = texts.createInput2(text, fontSize)
            faceLength = 2 * math.pi * (radiusOffset + radius)
            textDiagonalPoint = adsk.core.Point3D.create(faceLength, -height, 0)
            if isSingleLined:
                sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
                lines = sketch.sketchCurves.sketchLines
                path = lines.addByTwoPoints(adsk.core.Point3D.create(0,0,0), adsk.core.Point3D.create(10,0,0))
                textInput.setAsAlongPath(path, False, adsk.core.HorizontalAlignments.CenterHorizontalAlignment, characterSpacing)
            else:
                textInput.setAsMultiLine(adsk.core.Point3D.create(0, 0, 0), textDiagonalPoint, adsk.core.HorizontalAlignments.CenterHorizontalAlignment, adsk.core.VerticalAlignments.TopVerticalAlignment, characterSpacing)
            text = texts.add(textInput)

            # check if text cant fit on cylinder
            # height
            ratio = abs(text.boundingBox.maxPoint.y - text.boundingBox.minPoint.y) / height
            if ratio > 1:
                text.height = text.height / ratio
                
            # width
            ratio = abs(text.boundingBox.maxPoint.x - text.boundingBox.minPoint.x) / faceLength
            if ratio > 1:
                text.height = text.height / ratio

            curves = text.explode()

# put text on cylinder's face
            wrapSketch(cylinderSideFace, curves, radiusOffset)

# move text(kostyl)
            textSketch = rootComp.sketches.itemByName('WrapSketch')
            textCurves = textSketch.sketchCurves
            transform = textSketch.transform
            dx = 0
            dy = 0
            dLowest = textCurves.item(0).boundingBox.minPoint.z
            dHighest = textCurves.item(0).boundingBox.maxPoint.z
            for curve in textCurves:
                if curve.boundingBox.maxPoint.z > dHighest:
                    dHighest = curve.boundingBox.maxPoint.z
                if curve.boundingBox.minPoint.z < dLowest:
                    dLowest = curve.boundingBox.minPoint.z
            dz = (dHighest + dLowest) / 2
            dz = -dz
            transform.translation = adsk.core.Vector3D.create(dx,dy,dz)
            curvesCol = adsk.core.ObjectCollection.create()
            for sk in textCurves:
                curvesCol.add(sk)
            textSketch.move(curvesCol, transform)

# arrays for created faces
            faces = adsk.core.ObjectCollection.create()
            curvesCollections = []

# creating faces using patches
            while curvesCol.count > 0:
                currentCurvesInput = adsk.core.ObjectCollection.create()#collection for edges on current attempt
                patchInput = None
                index = 0
                # try to create patch, if cant => add next edge to collection and try again
                inputCurvesClosed = False
                while inputCurvesClosed == False:
                    currentCurvesInput.add(curvesCol.item(index))
                    patchInput = patchFeatures.createInput(currentCurvesInput, newBodyOperation)
                    index += 1
                    inputCurvesClosed = patchInput.boundaryCurve.isClosed
                patch = patchFeatures.add(patchInput)
                resFace = patch.faces.item(0)

                # check if surface's direction is wrong and fix it
                facePoint = resFace.pointOnFace
                radiusVector = adsk.core.Vector3D.create(facePoint.x, facePoint.y, facePoint.z)
                (_, normalVector) = resFace.evaluator.getNormalAtPoint(facePoint)
                angle = normalVector.angleTo(radiusVector)
                if angle > (math.pi / 2):
                    resFaceBodyCol = adsk.core.ObjectCollection.create()
                    resFaceBodyCol.add(resFace.body)
                    resFace = reverseNormalFeatures.add(resFaceBodyCol).faces.item(0)

                faces.add(resFace)
                curvesCollections.append(currentCurvesInput)
                # delete used curves from collection
                for curve in currentCurvesInput:
                    curvesCol.removeByItem(curve)

# join surfaces to cylinder using split face (projection)
            faceToSplitCollection = adsk.core.ObjectCollection.create()
            faceToSplitCollection.add(cylinderSideFace)
 
# split cylinder's face
            createdProjectionsCollection = adsk.core.ObjectCollection.create()
            createdFacesCollection = adsk.core.ObjectCollection.create()
            previousProjection = None
            previousFace = None
            parentFace = None
            newFace = None
            faceIndex = 0
            arrayOffset = 0
            innerFaces = []
            isWhole = []
            currentInnerFacesCollection = adsk.core.ObjectCollection.create()
            flSuccess = True
            for connectedCurves in curvesCollections:
                parentPoint = faceToSplitCollection.item(0).boundingBox.maxPoint
                
                splitInput = splitFaceFeatures.createInput(faceToSplitCollection, connectedCurves, True)
                splitInput.setClosestPointSplitType()
                
                try:
                    splitting = splitFaceFeatures.add(splitInput)

                    if splitting.faces.item(0).boundingBox.maxPoint.distanceTo(parentPoint) > splitting.faces.item(1).boundingBox.maxPoint.distanceTo(parentPoint):
                        previousProjection = splitting.faces.item(0)
                        parentFace = splitting.faces.item(1)
                    else:
                        previousProjection = splitting.faces.item(1)
                        parentFace = splitting.faces.item(0)

                    faceToSplitCollection = adsk.core.ObjectCollection.create()
                    faceToSplitCollection.add(parentFace)
                    createdProjectionsCollection.add(previousProjection)
                    previousFace = faces.item(faceIndex)
                    createdFacesCollection.add(previousFace)
                    isWhole.append(True)

                    if flSuccess == False:
                        innerFaces.append(currentInnerFacesCollection)
                        flSuccess = True
                except:
                    timeline.moveToPreviousStep()
                    timeline.deleteAllAfterMarker()
                    createdProjectionsCollection.removeByItem(previousProjection)
                    createdFacesCollection.removeByItem(previousFace)
                    isWhole.pop()
                    parentPoint = previousProjection.boundingBox.maxPoint
                    prevProjCollection = adsk.core.ObjectCollection.create()
                    prevProjCollection.add(previousProjection)
                    splitInput = splitFaceFeatures.createInput(prevProjCollection, connectedCurves, True)
                    splitInput.setClosestPointSplitType()
                    splitting = splitFaceFeatures.add(splitInput)
                    if splitting.faces.item(0).boundingBox.maxPoint.distanceTo(parentPoint) > splitting.faces.item(1).boundingBox.maxPoint.distanceTo(parentPoint):
                        newFace = splitting.faces.item(0)
                        previousProjection = splitting.faces.item(1)
                    else:
                        newFace = splitting.faces.item(1)
                        previousProjection = splitting.faces.item(0)
                    createdProjectionsCollection.add(previousProjection)

                    parentPoint = previousFace.boundingBox.maxPoint
                    currentFaceCollection = adsk.core.ObjectCollection.create()
                    currentFaceCollection.add(previousFace)
                    splitInput = splitFaceFeatures.createInput(currentFaceCollection, newFace, True)
                    splitInput.setClosestPointSplitType()
                    splitting = splitFaceFeatures.add(splitInput)

                    unstitchCollection = adsk.core.ObjectCollection.create()
                    unstitchCollection.add(splitting.bodies.item(0))
                    unstitch = unstitchFeatures.add(unstitchCollection)

                    if unstitch.faces.item(0).boundingBox.maxPoint.distanceTo(parentPoint) > unstitch.faces.item(1).boundingBox.maxPoint.distanceTo(parentPoint):
                        newFace = unstitch.faces.item(0)
                        previousFace = unstitch.faces.item(1)
                    else:
                        newFace = unstitch.faces.item(1)
                        previousFace = unstitch.faces.item(0)
                    
                    # newFace.body.deleteMe()
                    # removeFeatures.add(newFace.body)
                    if flSuccess:
                        currentInnerFacesCollection = adsk.core.ObjectCollection.create()
                        flSuccess = False
                    currentInnerFacesCollection.add(newFace)
                    
                    createdFacesCollection.add(previousFace)
                    isWhole.append(False)

                    # faces.item(faceIndex + arrayOffset).body.deleteMe()
                    removeFeatures.add(faces.item(faceIndex).body)
                    arrayOffset += 1

                    
                faceIndex += 1
            if currentInnerFacesCollection.count != 0:
                innerFaces.append(currentInnerFacesCollection)

# create solid body using lofts
            faceIndex = 0
            innerFaceIndex = 0

            zeroAngle = adsk.core.ValueInput.createByReal(0)
            normalRuledSurfaceType = adsk.fusion.RuledSurfaceTypes.NormalRuledSurfaceType

            for face in createdFacesCollection:
                # # connect face with projection
                # loftInput = loftFeatures.createInput(joinBodyOperation)
                # loftSections = loftInput.loftSections
                
                currentFace:adsk.fusion.BRepFace = createdFacesCollection.item(faceIndex)
                currentProj:adsk.fusion.BRepFace = createdProjectionsCollection.item(faceIndex)

                # loftSections.add(currentProj)
                # loftSections.add(currentFace)
                # loftInput.isSolid = True
                if isWhole[faceIndex]:
                    # create body from projection
                    projCurvesCollection = adsk.core.ObjectCollection.create()
                    for curve in currentProj.edges:
                        projCurvesCollection.add(curve)
                    patchInput = patchFeatures.createInput(projCurvesCollection, newBodyOperation)
                    patch = patchFeatures.add(patchInput)
                    currentProj = patch.faces.item(0)

                    # check if surface's direction is wrong and fix it
                    facePoint = currentProj.pointOnFace
                    radiusVector = adsk.core.Vector3D.create(facePoint.x, facePoint.y, facePoint.z)
                    (_, normalVector) = currentProj.evaluator.getNormalAtPoint(facePoint)
                    angle = normalVector.angleTo(radiusVector)
                    if angle > (math.pi / 2):
                        currentProjBodyCol = adsk.core.ObjectCollection.create()
                        currentProjBodyCol.add(currentProj.body)
                        currentProj = reverseNormalFeatures.add(currentProjBodyCol).faces.item(0)

                    facesToStitchCollection = adsk.core.ObjectCollection.create()
                    facesToStitchCollection.add(currentProj.body)
                    facesToStitchCollection.add(currentFace.body)

                    # create walls(loft)
                    for edgeProj in currentProj.edges:
                        loftInput = loftFeatures.createInput(newBodyOperation)
                        loftSections = loftInput.loftSections

                        edgeFace = findNearestEdge(edgeProj, currentFace.loops.item(0))
                        pathCol1 = adsk.core.ObjectCollection.create()
                        pathCol2 = adsk.core.ObjectCollection.create()
                        pathCol1.add(edgeFace)
                        pathCol2.add(edgeProj)

                        path1 = adsk.fusion.Path.create(pathCol1, False)
                        path2 = adsk.fusion.Path.create(pathCol2, False)

                        loftSections.add(path1)
                        loftSections.add(path2)
                        loftInput.isSolid = False
                        loftFeature = loftFeatures.add(loftInput)

                        facesToStitchCollection.add(loftFeature.faces.item(0).body)

                    tolerance = adsk.core.ValueInput.createByReal(0.01)
                    stitchInput = stitchFeatures.createInput(facesToStitchCollection, tolerance, joinBodyOperation)
                    stitchFeature = stitchFeatures.add(stitchInput)

                else:
                    # timeline.moveToPreviousStep()
                    # timeline.deleteAllAfterMarker()

                    startPoint = currentProj.boundingBox.maxPoint
                    loopIndex = 0

                    # creating patch
                    projLoop = currentProj.loops.item(loopIndex)
                    loopIndex += 1
                    projCurvesCollection = adsk.core.ObjectCollection.create()
                    for curve in projLoop.edges:
                        projCurvesCollection.add(curve)
                    patchInput = patchFeatures.createInput(projCurvesCollection, newBodyOperation)
                    patch = patchFeatures.add(patchInput)
                    while patch.faces.item(0).boundingBox.maxPoint.distanceTo(startPoint) > 0.00001:
                        timeline.moveToPreviousStep()
                        timeline.deleteAllAfterMarker()
                        projLoop = currentProj.loops.item(loopIndex)
                        loopIndex += 1
                        projCurvesCollection = adsk.core.ObjectCollection.create()
                        for curve in projLoop.edges:
                            projCurvesCollection.add(curve)
                        patchInput = patchFeatures.createInput(projCurvesCollection, newBodyOperation)
                        patch = patchFeatures.add(patchInput)
                    patchFace = patch.faces.item(0)
                    
                    # check if surface's direction is wrong and fix it
                    facePoint = patchFace.pointOnFace
                    radiusVector = adsk.core.Vector3D.create(facePoint.x, facePoint.y, facePoint.z)
                    (_, normalVector) = patchFace.evaluator.getNormalAtPoint(facePoint)
                    angle = normalVector.angleTo(radiusVector)
                    if angle > (math.pi / 2):
                        patchFaceBodyCol = adsk.core.ObjectCollection.create()
                        patchFaceBodyCol.add(patchFace.body)
                        patchFace = reverseNormalFeatures.add(patchFaceBodyCol).faces.item(0)

                    # separating patch
                    patchFaceCollection = adsk.core.ObjectCollection.create()
                    startPoint = patchFace.boundingBox.maxPoint
                    patchFaceCollection.add(patchFace)
                    splitInput = splitFaceFeatures.createInput(patchFaceCollection, innerFaces[innerFaceIndex], True)
                    splitInput.setClosestPointSplitType()
                    splitting = splitFaceFeatures.add(splitInput)
                    for splFace in innerFaces[innerFaceIndex]:
                        removeFeatures.add(splFace.body)
                    # splitFaces = splitting.faces
                    # splitFaces = patchFace.body.faces
                    innerFaceIndex += 1

                    startPoint = patchFace.boundingBox.maxPoint
                    unstitchCollection = adsk.core.ObjectCollection.create()
                    unstitchCollection.add(patchFace)
                    unstitch = unstitchFeatures.add(unstitchCollection)
                    distance = _maxint
                    currentProj:adsk.fusion.BRepFace = None
                    for splFace in unstitch.faces:
                        if splFace.boundingBox.maxPoint.distanceTo(startPoint) < distance:
                            if currentProj != None:
                                removeFeatures.add(currentProj.body)
                            currentProj = splFace
                            distance = splFace.boundingBox.maxPoint.distanceTo(startPoint)
                        else:
                            if currentProj != None:
                                removeFeatures.add(splFace.body)
                    
                    # offset projection into the cylinder to make them overlap
                    currentProjCollection = adsk.core.ObjectCollection.create()
                    currentProjCollection.add(currentProj)
                    offsetDistance = adsk.core.ValueInput.createByReal(-0.01)
                    offsetInput = offsetFeatures.createInput(currentProjCollection, offsetDistance, newBodyOperation)
                    offset = offsetFeatures.add(offsetInput)
                    removeFeatures.add(currentProj.body)
                    currentProj = offset.faces.item(0)

                    # currentProj currentFace
                    facesToStitchCollection = adsk.core.ObjectCollection.create()
                    facesToStitchCollection.add(currentFace.body)
                    facesToStitchCollection.add(currentProj.body)
                    for loop in currentFace.loops:
                        distance = _maxint
                        pairLoop:adsk.fusion.BRepLoop = None
                        for tmpLoop in currentProj.loops:
                            if tmpLoop.edges.count != loop.edges.count:
                                continue
                            if tmpLoop.boundingBox.maxPoint.distanceTo(loop.boundingBox.maxPoint) < distance:
                                pairLoop = tmpLoop
                                distance = tmpLoop.boundingBox.maxPoint.distanceTo(loop.boundingBox.maxPoint)

                        for edgeProj in pairLoop.edges:
                            loftInput = loftFeatures.createInput(newBodyOperation)
                            loftSections = loftInput.loftSections

                            edgeFace = findNearestEdge(edgeProj, loop)
                            pathCol1 = adsk.core.ObjectCollection.create()
                            pathCol2 = adsk.core.ObjectCollection.create()
                            pathCol1.add(edgeFace)
                            pathCol2.add(edgeProj)

                            path1 = adsk.fusion.Path.create(pathCol1, False)
                            path2 = adsk.fusion.Path.create(pathCol2, False)

                            loftSections.add(path1)
                            loftSections.add(path2)
                            loftInput.isSolid = False
                            loftFeature = loftFeatures.add(loftInput)

                            facesToStitchCollection.add(loftFeature.faces.item(0).body)
                    
                    tolerance = adsk.core.ValueInput.createByReal(0.01)
                    stitchInput = stitchFeatures.createInput(facesToStitchCollection, tolerance, joinBodyOperation)
                    stitchFeature = stitchFeatures.add(stitchInput)
                

                removeFeatures.add(currentFace.body)
                faceIndex += 1

            
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
            tabCmdInput1:adsk.core.TabCommandInput = inputs.addTabCommandInput('tab_1', 'Tab 1')
            tab1ChildInputs = tabCmdInput1.children

            # Create value inputs.
            tab1ChildInputs.addValueInput('Radius', 'Radius (cm)', '', adsk.core.ValueInput.createByReal(1.0))

            tab1ChildInputs.addValueInput('Height', 'Height (cm)', '', adsk.core.ValueInput.createByReal(0.4))

            tab1ChildInputs.addValueInput('Thickness', 'Thickness (cm)', '', adsk.core.ValueInput.createByReal(0.02))

            tab1ChildInputs.addStringValueInput('Text', 'Text', 'text')

            tab1ChildInputs.addValueInput('Font size', 'Font size (cm)', '', adsk.core.ValueInput.createByReal(0.5))

            tab1ChildInputs.addValueInput('Radius offset', 'Radius offset (cm)', '', adsk.core.ValueInput.createByReal(0.02))
            
            tab1ChildInputs.addValueInput('Character spacing', 'Character spacing (cm)', '', adsk.core.ValueInput.createByReal(0))

            tab1ChildInputs.addBoolValueInput('Single line', 'Single line?', True, '', True)

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
