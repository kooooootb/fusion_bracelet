#Author-
#Description-

# from time import time
import adsk.core, adsk.fusion, adsk.cam, traceback, math

import os, sys

_app = None
_ui = None
_design = None
_rowNumber = 0
_maxint = sys.maxsize
_dirpath = os.path.dirname(os.path.realpath(__file__))

# _startTime = time()

def downloadTk():
    installCommand = sys.path[0] +'\Python\python.exe -m pip install tk'
    os.system('cmd /c "' + installCommand + '"')

import importlib
mimp = importlib.util.find_spec("tkinter")
if mimp is None:
    downloadTk()


sys.path.insert(1, _dirpath)
from menuModule import getInputs
from menuModule import inputElement

# _pointsFilename = _dirpath + "imageText.txt"

def getDistancesEdSk(edges:adsk.fusion.BRepEdges, sketchLines:adsk.fusion.SketchLines):
    if edges.count != sketchLines.count:
        return _maxint

    resDistance = 0

    for firstEdge in edges:
        firstPoint:adsk.core.Point3D = firstEdge.startVertex.geometry
        secondPoint:adsk.core.Point3D = None
        distance = _maxint
        for sketchLine in sketchLines:
            tmpSecondPoint = sketchLine.startSketchPoint.geometry
            if firstPoint.distanceTo(tmpSecondPoint) < distance:
                secondPoint = tmpSecondPoint
                distance = firstPoint.distanceTo(tmpSecondPoint)
        
        resDistance += firstPoint.distanceTo(secondPoint)
    return resDistance

def getDistancesEdEd(firstEdges:adsk.fusion.BRepEdges, secondEdges:adsk.fusion.BRepEdges):
    if firstEdges.count != secondEdges.count:
        return _maxint
        
    resDistance = 0

    for firstEdge in firstEdges:
        firstPoint:adsk.core.Point3D = firstEdge.startVertex.geometry
        secondPoint:adsk.core.Point3D = None
        distance = _maxint
        for secondEdge in secondEdges:
            tmpSecondPoint = secondEdge.startVertex.geometry
            if firstPoint.distanceTo(tmpSecondPoint) < distance:
                secondPoint = tmpSecondPoint
                distance = firstPoint.distanceTo(tmpSecondPoint)
        
        resDistance += firstPoint.distanceTo(secondPoint)
    return resDistance

def getMaxPoint(curvesCol:adsk.core.ObjectCollection) -> adsk.core.Point3D:
    resPoint = curvesCol.item(0).boundingBox.maxPoint
    for curve in curvesCol:
        maxPoint:adsk.core.Point3D = curve.boundingBox.maxPoint
        if maxPoint.x > resPoint.x:
            resPoint.x = maxPoint.x
        if maxPoint.x > resPoint.y:
            resPoint.x = maxPoint.y
        if maxPoint.x > resPoint.z:
            resPoint.x = maxPoint.z
    return resPoint

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

##############################################################################

def point3DStr(pt):
    return (str(pt.x) + ',' + str(pt.y) + ',' + str(pt.z))

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
           
def wrapSketch(cylFace, sketchCurves, radiusOffset):
    try:
        # Get the root component of the active design.
        rootComp = _design.rootComponent
        # Create a new sketch on the xy plane.
        sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)

        cylGeom = cylFace.geometry

        # Iterate over the sketch curves
        for sketchCurve in sketchCurves:
            obj_type = sketchCurve.objectType

            if obj_type == 'adsk::fusion::SketchFittedSpline':
                # Get this splines points
                fitPoints = sketchCurve.fitPoints

                # Create an object collection for the points.
                newFitPoints = adsk.core.ObjectCollection.create()

                for ip in range(fitPoints.count):
                    pt = fitPoints.item(ip).geometry
                    # map the old point to cylinder
                    xNew, yNew, zNew = mapPoint2Curve(pt.x, pt.y, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                    newFitPoints.add(adsk.core.Point3D.create(xNew, yNew, zNew)) #cylGeom.origin.z + zNew))  origin is in middle of cylinder.  Need to find length and offset.

                # Create the spline.
                newFittedSpline = sketch.sketchCurves.sketchFittedSplines.add(newFitPoints)
                if newFittedSpline != None:
                    newFittedSpline.isClosed = sketchCurve.isClosed

            elif obj_type == 'adsk::fusion::SketchLine':
                # Convert line to arc on cylinder face
                ptStart = sketchCurve.startSketchPoint.geometry
                ptEnd   = sketchCurve.endSketchPoint.geometry
                
                if ptStart != ptEnd:
                    # map the points to cylinder
                    xStart, yStart, zStart = mapPoint2Curve(ptStart.x, ptStart.y, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                    xEnd, yEnd, zEnd = mapPoint2Curve(ptEnd.x, ptEnd.y, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                    
                    # Check for a vertical line which will just map to a line
                    if equal_close(ptStart.x, ptEnd.x, 6):
                        lines = sketch.sketchCurves.sketchLines
                        lines.addByTwoPoints(adsk.core.Point3D.create(xStart, yStart, zStart), adsk.core.Point3D.create(xEnd, yEnd, zEnd))
                    else:
                        # mapping to a cylinder so create an arc
                        xCtr, yCtr, zCtr = mapPoint2Curve(((ptStart.x + ptEnd.x) / 2.0), ((ptStart.y + ptEnd.y) / 2.0), cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                        
                        sketchArcs = sketch.sketchCurves.sketchArcs
                        sketchArcs.addByThreePoints(adsk.core.Point3D.create(xStart, yStart, zStart),
                                                    adsk.core.Point3D.create(xCtr, yCtr, zCtr),
                                                    adsk.core.Point3D.create(xEnd, yEnd, zEnd))
                else:
                    print('Found 0 Length Sketch Line')
                
            elif obj_type == 'adsk::fusion::SketchPoint':
                pt = sketchCurve.geometry
                
                # map the point to cylinder
                xNew, yNew, zNew = mapPoint2Curve(pt.x, pt.y, cylGeom.radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
                
                sketchPoints = sketch.sketchPoints
                sketchPoints.add(adsk.core.Point3D.create(xNew, yNew, zNew))
            else:
                print('Sketch type unsupported: ' + obj_type)
        
        return sketch
        
    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

##############################################################################

def addRowToTable(tableInput):
    global _rowNumber
    # get commandInput associated with command
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


def task():
    try:
        # inputs = command.commandInputs
        inputs = getInputs(_dirpath)

        radius = 2.0
        height = 1.0
        thickness = 0.2
        text = ''
        fontSize = 0.5
        radiusOffset = 0.1
        characterSpacing = 0
        makeSlot = True
        slotWidth = 0.02
        usePicture = False
        imageScaling = 0.95

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
            if input.id == 'Font_size':
                fontSize = input.value
            if input.id == 'Radius_offset':
                radiusOffset = input.value
            if input.id == 'Character_spacing':
                characterSpacing = input.value
            if input.id == 'Slot':
                makeSlot = input.value
            if input.id == 'Slot_width':
                slotWidth = input.value
            if input.id == 'Use_picture':
                usePicture = input.value
            if input.id == 'Image_scaling':
                imageScaling = input.value
        
# check if text is empty
        if text == "":
            return 

# set initial variables
        rootComp: adsk.fusion.Component = _app.activeProduct.rootComponent
        sketch:adsk.fusion.Sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
        timeline:adsk.fusion.Timeline = _design.timeline

        offsetDistance:adsk.core.ValueInput = None
        if thickness < 0.1:
            offsetDistance = adsk.core.ValueInput.createByReal((-1) * thickness / 10)
        else:
            offsetDistance = adsk.core.ValueInput.createByReal(-0.01)

# set features and operations
        extrudeFeatures:adsk.fusion.ExtrudeFeatures = rootComp.features.extrudeFeatures
        patchFeatures:adsk.fusion.PatchFeatures = rootComp.features.patchFeatures
        splitFaceFeatures:adsk.fusion.SplitFaceFeatures = rootComp.features.splitFaceFeatures
        loftFeatures:adsk.fusion.LoftFeatures = rootComp.features.loftFeatures
        removeFeatures:adsk.fusion.RemoveFeatures = rootComp.features.removeFeatures
        unstitchFeatures:adsk.fusion.UnstitchFeatures = rootComp.features.unstitchFeatures
        offsetFeatures:adsk.fusion.OffsetFeatures = rootComp.features.offsetFeatures
        stitchFeatures:adsk.fusion.StitchFeatures = rootComp.features.stitchFeatures
        reverseNormalFeatures:adsk.fusion.ReverseNormalFeatures = rootComp.features.reverseNormalFeatures

        newBodyOperation = adsk.fusion.FeatureOperations.NewBodyFeatureOperation
        joinBodyOperation = adsk.fusion.FeatureOperations.JoinFeatureOperation
        cutBodyOperation = adsk.fusion.FeatureOperations.CutFeatureOperation

# create cylinder
        circles = sketch.sketchCurves.sketchCircles
        circle = circles.addByCenterRadius(adsk.core.Point3D.create(0,0,0), radius)
        circleProfile = rootComp.createOpenProfile(circle)

        extInput = extrudeFeatures.createInput(circleProfile, newBodyOperation)
        extInput.setThinExtrude(adsk.fusion.ThinExtrudeWallLocation.Center, adsk.core.ValueInput.createByReal(thickness))
        extInput.setSymmetricExtent(adsk.core.ValueInput.createByReal(height / 2), False)
        circleExtrude = extrudeFeatures.add(extInput)
        sideFaceIndex = 0
        if circleExtrude.sideFaces.item(1).area > circleExtrude.sideFaces.item(0).area:
            sideFaceIndex = 1
        cylinderSideFace = circleExtrude.sideFaces.item(sideFaceIndex)
        cylinderBody = circleExtrude.bodies.item(0)
        faceLength = 2 * math.pi * (radiusOffset + radius)

        textCurves = []

        if usePicture:
            print('currently unsupported')
            # fs = open(_pointsFilename, "rb")
            # pointsCol = adsk.core.ObjectCollection.create()
            
            # x = 0
            # y = 0
            # isY = False
            # count = 0
            # xMax = 0
            # yMax = 0
            # xMin = _maxint
            # yMin = _maxint
            # sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
            # lines = sketch.sketchCurves.sketchLines

            # for num in fs:
            #     if count > 0:
            #         if isY:
            #             y = float(num)
            #             if x > xMax:
            #                 xMax = x
            #             if y > yMax:
            #                 yMax = y
            #             if x < xMin:
            #                 xMin = x
            #             if y < yMin:
            #                 yMin = y
            #             point = adsk.core.Point3D.create(x,y,0)
            #             pointsCol.add(point)
            #             isY = False
            #         else:
            #             x = float(num)
            #             isY = True
            #         count -= 1
            #     else:
            #         count = float(num)
            #         count *= 2

            #         if pointsCol.count > 1:
            #             firstPoint = adsk.core.Point3D.create(0,0,0)
            #             secondPoint = adsk.core.Point3D.create(0,0,0)

            #             firstPoint = pointsCol[pointsCol.count - 1]

            #             for point in pointsCol:
            #                 secondPoint = point

            #                 curve = lines.addByTwoPoints(firstPoint, secondPoint)
            #                 textCurves.append(curve)

            #                 firstPoint = point
                        
            #             pointsCol = adsk.core.ObjectCollection.create()
                    
            # realHeight = height
            # realLength = (radius + (thickness / 2) + radiusOffset) * 2 * math.pi

            # heightRatio = realHeight / (yMax - yMin)
            # lengthRatio = realLength / (xMax - xMin)
            # ratio = 0

            # if heightRatio < lengthRatio:
            #     ratio = heightRatio
            # else:
            #     ratio = lengthRatio

            # ratio *= imageScaling
            
            # sketchCol = adsk.core.ObjectCollection.create()
            # sketchCol.add(sketch)
            # refPoint = sketch.sketchPoints.item(0)
            # scaleInput = scaleFeatures.createInput(sketchCol, refPoint, adsk.core.ValueInput.createByReal(ratio))
            # scaleFeatures.add(scaleInput)
        else:
            # create text
            sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
            texts = sketch.sketchTexts
            textInput = texts.createInput2(text, fontSize)
            
            sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
            lines = sketch.sketchCurves.sketchLines
            path = lines.addByTwoPoints(adsk.core.Point3D.create(0,0,0), adsk.core.Point3D.create(10,0,0))
            textInput.setAsAlongPath(path, False, adsk.core.HorizontalAlignments.CenterHorizontalAlignment, characterSpacing)
            
            text = texts.add(textInput)

            # check if text cant fit on cylinder
            # height
            ratio = 1.05 * abs(text.boundingBox.maxPoint.y - text.boundingBox.minPoint.y) / height
            if ratio > 1:
                text.height = text.height / ratio
                
            # width
            ratio = 1.05 * abs(text.boundingBox.maxPoint.x - text.boundingBox.minPoint.x) / faceLength
            if ratio > 1:
                text.height = text.height / ratio

            textLeft = text.boundingBox.maxPoint.x
            textRight = text.boundingBox.minPoint.x

            textCurves = text.explode()
        
# make slot
        if makeSlot:
            slotWidth /= 2

            # create sketch rectangle
            sketch = rootComp.sketches.add(rootComp.xYConstructionPlane)
            lines = sketch.sketchCurves.sketchLines

            if textLeft > textRight: textLeft, textRight = textRight, textLeft
            textWidth = abs(textRight - textLeft)
            textMiddle = textLeft + textWidth/2
            textLeft = textMiddle - faceLength/2 + slotWidth

            cylGeom = cylinderSideFace.geometry
            k = (radius - thickness - radiusOffset) / (radiusOffset + radius)

            x1, y1, _ = mapPoint2Curve(textLeft, 0, radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
            p11 = adsk.core.Point3D.create(x1 / k, y1 / k, 0)
            x2, y2, _ = mapPoint2Curve(textLeft - 2 * slotWidth, 0, radius + radiusOffset, cylGeom.origin.x, cylGeom.origin.y, cylGeom.origin.z)
            p21 = adsk.core.Point3D.create(x2 / k, y2 / k, 0)

            p12 = adsk.core.Point3D.create(x1 * k, y1 * k, 0)
            p22 = adsk.core.Point3D.create(x2 * k, y2 * k, 0)

            linesCol = adsk.core.ObjectCollection.create()
            linesCol.add(lines.addByTwoPoints(p11, p12))
            linesCol.add(lines.addByTwoPoints(p12, p22))
            linesCol.add(lines.addByTwoPoints(p22, p21))
            linesCol.add(lines.addByTwoPoints(p21, p11))

            # cut with extrude
            extrudeInput = extrudeFeatures.createInput(sketch.profiles.item(0), cutBodyOperation)
            extrudeInput.setSymmetricExtent(adsk.core.ValueInput.createByReal(height), True)
            extrudeInput.participantBodies = [cylinderBody]
            extrudeInput.isSolid = True
            extrude = extrudeFeatures.add(extrudeInput)

            if extrude.bodies.count == 2:
                if extrude.bodies.item(0).faces.count > extrude.bodies.item(1).faces.count:
                    cylinderBody = extrude.bodies.item(0)
                    extrude.bodies.item(1).deleteMe()
                else:
                    cylinderBody = extrude.bodies.item(1)
                    extrude.bodies.item(0).deleteMe()

# put text on cylinder's face
        textSketch = wrapSketch(cylinderSideFace, textCurves, radiusOffset)

        for curve in textCurves:
            curve.deleteMe()

# move text
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

# project faces on cylinder using split face
        facesToSplitCollection = adsk.core.ObjectCollection.create()
        facesToSplitCollection.add(cylinderSideFace)

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
            splitInput = splitFaceFeatures.createInput(facesToSplitCollection, connectedCurves, True)
            splitInput.setClosestPointSplitType()
            
            try:
                splitting = splitFaceFeatures.add(splitInput)

                distance = _maxint
                previousProjection = None

                for face in splitting.faces:
                    facesToSplitCollection.removeByItem(face)
                    sumDistance = getDistancesEdSk(face.edges, connectedCurves)
                    if sumDistance < distance:
                        distance = sumDistance
                        if previousProjection != None:
                            facesToSplitCollection.add(previousProjection)
                        previousProjection = face
                    else:
                        facesToSplitCollection.add(face)

                createdProjectionsCollection.add(previousProjection)
                previousFace = faces.item(faceIndex)
                createdFacesCollection.add(previousFace)
                isWhole.append(True)

                if flSuccess == False:
                    innerFaces.append(currentInnerFacesCollection)
                    flSuccess = True
            except:
                # rollback
                timeline.moveToPreviousStep()
                timeline.deleteAllAfterMarker()

                # remove last elements
                createdFacesCollection.removeByItem(previousFace)
                isWhole.pop()

                # set and make split on projection
                prevProjCollection = adsk.core.ObjectCollection.create()
                prevProjCollection.add(previousProjection)
                # splitInput = splitFaceFeatures.createInput(prevProjCollection, connectedCurves, True)
                splitInput = splitFaceFeatures.createInput(createdProjectionsCollection, connectedCurves, True)
                splitInput.setClosestPointSplitType()
                splitting = splitFaceFeatures.add(splitInput)

                # choose which face is in use
                distance = _maxint
                newFace = None
                previousProjection = None

                for face in splitting.faces:
                    createdProjectionsCollection.removeByItem(face)
                    tmpDist = getDistancesEdSk(face.edges, connectedCurves)
                    if tmpDist < distance:
                        distance = tmpDist
                        if newFace != None:
                            createdProjectionsCollection.add(newFace)
                        newFace = face
                    else:
                        createdProjectionsCollection.add(face)
                facesToSplitCollection.add(newFace)

                # split face
                currentFaceCollection = adsk.core.ObjectCollection.create()
                currentFaceCollection.add(previousFace)
                splitInput = splitFaceFeatures.createInput(currentFaceCollection, newFace, True)
                splitInput.setClosestPointSplitType()
                splitting = splitFaceFeatures.add(splitInput)

                # unstitch splitted body
                unstitchCollection = adsk.core.ObjectCollection.create()
                unstitchCollection.add(splitting.bodies.item(0))
                unstitch = unstitchFeatures.add(unstitchCollection)

                distance = _maxint
                if getDistancesEdEd(unstitch.faces.item(0).edges, newFace.edges) > getDistancesEdEd(unstitch.faces.item(1).edges, newFace.edges):
                    newFace = unstitch.faces.item(1)
                    previousFace = unstitch.faces.item(0)
                else:
                    newFace = unstitch.faces.item(0)
                    previousFace = unstitch.faces.item(1)
                
                if flSuccess:
                    currentInnerFacesCollection = adsk.core.ObjectCollection.create()
                    flSuccess = False
                currentInnerFacesCollection.add(newFace)
                
                createdFacesCollection.add(previousFace)
                isWhole.append(False)

                removeFeatures.add(faces.item(faceIndex).body)
                arrayOffset += 1

            faceIndex += 1
        if currentInnerFacesCollection.count != 0:
            innerFaces.append(currentInnerFacesCollection)

# create solid body using lofts
        faceIndex = 0
        innerFaceIndex = 0
        resultBody:adsk.fusion.BRepBody = None

        for face in createdFacesCollection:
            currentFace:adsk.fusion.BRepFace = createdFacesCollection.item(faceIndex)
            currentProj:adsk.fusion.BRepFace = None
            # currentProj:adsk.fusion.BRepFace = createdProjectionsCollection.item(faceIndex)
            distance = _maxint
            for splFace in createdProjectionsCollection:
                tmpDist = getDistancesEdEd(splFace.edges, currentFace.edges)
                if tmpDist < distance:
                    distance = tmpDist
                    currentProj = splFace
            createdProjectionsCollection.removeByItem(currentProj)

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
                    
                # offset projection into the cylinder to make them overlap
                currentProjCollection = adsk.core.ObjectCollection.create()
                currentProjCollection.add(currentProj)
                offsetInput = offsetFeatures.createInput(currentProjCollection, offsetDistance, newBodyOperation)
                offset = offsetFeatures.add(offsetInput)
                removeFeatures.add(currentProj.body)
                currentProj = offset.faces.item(0)

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
                resultBody = stitchFeature.bodies.item(0)

            else:
                edgesCount = 0

                # creating patch(for each loop and find the biggest one)
                patchFaceCollection = adsk.core.ObjectCollection.create()
                areaPatch = 0
                for loop in currentProj.loops:
                    projCurvesCollection = adsk.core.ObjectCollection.create()
                    for curve in loop.edges:
                        projCurvesCollection.add(curve)
                    patchInput = patchFeatures.createInput(projCurvesCollection, newBodyOperation)
                    patch = patchFeatures.add(patchInput)
                    patchFaceCollection.add(patch.faces.item(0))
                    if patch.faces.item(0).area > areaPatch:
                        patchFace = patch.faces.item(0)
                        edgesCount = loop.edges.count
                
                # remove odd patches
                patchFaceCollection.removeByItem(patchFace)
                for tmpFace in patchFaceCollection:
                    removeFeatures.add(tmpFace.body)
                
                # check if surface's direction is wrong and fix it
                facePoint = patchFace.pointOnFace
                radiusVector = adsk.core.Vector3D.create(facePoint.x, facePoint.y, facePoint.z)
                (_, normalVector) = patchFace.evaluator.getNormalAtPoint(facePoint)
                angle = normalVector.angleTo(radiusVector)
                if angle > (math.pi / 2):
                    patchFaceBodyCol = adsk.core.ObjectCollection.create()
                    patchFaceBodyCol.add(patchFace.body)
                    patchFace = reverseNormalFeatures.add(patchFaceBodyCol).faces.item(0)

                # separating patch(using premade inner faces collection)
                patchFaceCollection = adsk.core.ObjectCollection.create()
                patchFaceCollection.add(patchFace)
                splitInput = splitFaceFeatures.createInput(patchFaceCollection, innerFaces[innerFaceIndex], True)
                splitInput.setClosestPointSplitType()
                splitting = splitFaceFeatures.add(splitInput)
                for splFace in innerFaces[innerFaceIndex]:
                    removeFeatures.add(splFace.body)
                innerFaceIndex += 1

                unstitchCollection = adsk.core.ObjectCollection.create()
                unstitchCollection.add(patchFace)
                unstitch = unstitchFeatures.add(unstitchCollection)

                currentProj:adsk.fusion.BRepFace = None
                facesToRemove = adsk.core.ObjectCollection.create()
                flag = False
                for splFace in unstitch.faces:
                    if flag:
                        facesToRemove.add(splFace)
                        continue

                    totalEdges = 0
                    for tmpFace in unstitch.faces:
                        if splFace != tmpFace:
                            totalEdges += tmpFace.edges.count
                    
                    if splFace.edges.count - totalEdges == edgesCount:
                        currentProj = splFace
                        flag = True
                    else:
                        facesToRemove.add(splFace)

                for splFace in facesToRemove:
                    removeFeatures.add(splFace.body)
                
                # offset projection into the cylinder to make them overlap
                currentProjCollection = adsk.core.ObjectCollection.create()
                currentProjCollection.add(currentProj)
                offsetInput = offsetFeatures.createInput(currentProjCollection, offsetDistance, newBodyOperation)
                offset = offsetFeatures.add(offsetInput)
                removeFeatures.add(currentProj.body)
                currentProj = offset.faces.item(0)

                # stitch currentProj currentFace and walls
                facesToStitchCollection = adsk.core.ObjectCollection.create()
                facesToStitchCollection.add(currentFace.body)
                facesToStitchCollection.add(currentProj.body)
                for loop in currentFace.loops:
                    distance = _maxint
                    pairLoop:adsk.fusion.BRepLoop = None
                    for tmpLoop in currentProj.loops:
                        tmpDist = getDistancesEdEd(tmpLoop.edges, loop.edges)
                        if tmpDist < distance:
                            distance = tmpDist
                            pairLoop = tmpLoop

                        # if tmpLoop.edges.count != loop.edges.count:
                        #     continue
                        # if tmpLoop.boundingBox.maxPoint.distanceTo(loop.boundingBox.maxPoint) < distance:
                        #     pairLoop = tmpLoop
                        #     distance = tmpLoop.boundingBox.maxPoint.distanceTo(loop.boundingBox.maxPoint)

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
                resultBody = stitchFeature.bodies.item(0)

            removeFeatures.add(currentFace.body)
            faceIndex += 1

        # _ui.messageBox(f"Time elaplsed: {time() - _startTime}")
        
    except:
        _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))

def run(context):
    try:
        global _app, _ui, _design
        _app = adsk.core.Application.get()
        _ui  = _app.userInterface

        _design = _app.activeProduct

        task()

    except:
        if _ui:
            _ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))