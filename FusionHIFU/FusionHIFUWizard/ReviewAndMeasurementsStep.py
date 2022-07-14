#! /usr/bin/env python
# -*- coding:utf8 -*-

from __main__ import qt, ctk, vtk, slicer

import PythonQt
import string
import math
import os
import numpy as np

from .FusionHIFUStep import *
from .Helper import *

class ReviewAndMeasurementStep( FusionHIFUStep ):
    '''
    Show volume rendering image and do some measurements. 1. measurement(line, angle); 2. change layout; 3.Pseudo-color map for MPR and VR; 4.Data probe; 5.Clipping
    '''
    def __init__( self, stepid ):
        self.initialize( stepid )
        self.setName( '2. 体绘制及测量' )
        self.setDescription( """步骤:\n  1. 选择合适的体绘制参数，测量感兴趣区域\n """ )

        self.__parent = super( ReviewAndMeasurementStep, self )
        self.reset()
        qt.QTimer.singleShot(0, self.killButton)


    def reset(self):
        self.__vrDisplayNode = None
        self.__roiTransformNode = None
        self.__baselineVolume = None

        self.__roi = None
        self.__roiObserverTag = None
        
    def killButton(self):
        # hide useless button
        bl = slicer.util.findChildren(text='Final')
        if len(bl):
            bl[0].hide()


    def createUserInterface( self ):
        try:
            self.__layout = self.__parent.createUserInterface()

            # Hide ROI Details
            roiCollapsibleButton = ctk.ctkCollapsibleButton()
            #roiCollapsibleButton.setMaximumWidth(320)
            roiCollapsibleButton.text = "ROI 设置"
            self.__layout.addWidget(roiCollapsibleButton)
            roiCollapsibleButton.collapsed = True

            # Layout
            roiLayout = qt.QFormLayout(roiCollapsibleButton)

            #label for ROI selector
            roiLabel = qt.QLabel( '选择 ROI:' )
            font = roiLabel.font
            font.setBold(True)
            roiLabel.setFont(font)
            
            #creates combobox and populates it with all vtkMRMLAnnotationROINodes in the scene
            self.__roiSelector = slicer.qMRMLNodeComboBox()
            self.__roiSelector.nodeTypes = ['vtkMRMLAnnotationROINode']
            self.__roiSelector.toolTip = "ROI defining the structure of interest"
            self.__roiSelector.setMRMLScene(slicer.mrmlScene)
            self.__roiSelector.addEnabled = 1
            
            #add label + combobox
            roiLayout.addRow( roiLabel, self.__roiSelector )

            self.__roiSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onROIChanged)

            # the ROI parameters
            # GroupBox to hold ROI Widget
            voiGroupBox = qt.QGroupBox()
            voiGroupBox.setTitle( 'Define VOI' )
            roiLayout.addRow( voiGroupBox )
            
            # create form layout for GroupBox
            voiGroupBoxLayout = qt.QFormLayout( voiGroupBox )
            
            # create ROI Widget and add it to the form layout of the GroupBox
            self.__roiWidget = PythonQt.qSlicerAnnotationsModuleWidgets.qMRMLAnnotationROIWidget()
            voiGroupBoxLayout.addRow( self.__roiWidget )
            
            # Hide VR Details
            vrCollapsibleButton = ctk.ctkCollapsibleButton()
            #roiCollapsibleButton.setMaximumWidth(320)
            vrCollapsibleButton.text = "Rendering Details"
            self.__layout.addWidget(vrCollapsibleButton)
            vrCollapsibleButton.collapsed = True

            # Layout
            vrLayout = qt.QFormLayout(vrCollapsibleButton)
            
            # the ROI parameters
            # GroupBox to hold ROI Widget
            vrGroupBox = qt.QGroupBox()
            vrGroupBox.setTitle( '绘制参数设置' )
            vrLayout.addRow( vrGroupBox )
            
            # create form layout for GroupBox
            vrGroupBoxLayout = qt.QFormLayout( vrGroupBox )
            
            # initialize VR
            self.__vrLogic = slicer.modules.volumerendering.logic()
            # create ROI Widget and add it to the form layout of the GroupBox
            self.__vrWidget = PythonQt.qSlicerVolumeRenderingModuleWidgets.qSlicerVolumeRenderingPresetComboBox()
            self.__vrWidget.setMRMLScene(self.__vrLogic.GetPresetsScene())
            self.__vrWidget.connect(PythonQt.QtCore.SIGNAL('currentNodeChanged(vtkMRMLNode*)'), self.presetChanged)
            self.__vrWidget.connect("presetOffsetChanged(double, double, bool)", self.presetOffsetChanged)
            vrGroupBoxLayout.addRow( self.__vrWidget )
            
            # Hide Ultrasonic Probe Details
            ultraSonicProbeCollapsibleButton = ctk.ctkCollapsibleButton()
            #ultraSonicProbeCollapsibleButton.setMaximumWidth(320)
            ultraSonicProbeCollapsibleButton.text = "超声探头设置"
            self.__layout.addWidget(ultraSonicProbeCollapsibleButton)
            ultraSonicProbeCollapsibleButton.collapsed = True

            # Layout
            ultraSonicProbeLayout = qt.QFormLayout(ultraSonicProbeCollapsibleButton)

            #label for Ultrasonic Probe selector
            ultraSonicProbeLabel = qt.QLabel( '选择探头:' )
            font = ultraSonicProbeLabel.font
            font.setBold(True)
            ultraSonicProbeLabel.setFont(font)
            
            #creates combobox and populates it with all vtkMRMLAnnotationROINodes in the scene
            self.__ultraSonicProbeSelector = qt.QComboBox()
            self.__probetype = ("小凸探头1", "小凸探头2")  # add more probe types later
            self.__ultraSonicProbeSelector.toolTip = "select an ultrasonic probe and display in the VR view"
            self.__ultraSonicProbeSelector.addItems(self.__probetype)
            
            #add label
            ultraSonicProbeLayout.addRow( ultraSonicProbeLabel, self.__ultraSonicProbeSelector )

            #label for Ultrasonic Probe selector
            ultraSonicProbeSettingLabel = qt.QLabel( '探头参数设置:' )
            font = ultraSonicProbeSettingLabel.font
            font.setBold(True)
            ultraSonicProbeSettingLabel.setFont(font)
            ultraSonicProbeLayout.addRow(ultraSonicProbeSettingLabel)

            angleText1 = qt.QLabel("角度:")
            self.probeAngle = qt.QLineEdit()
            self.probeAngle.setMaximumWidth(50)
            nearRadiusText1 = qt.QLabel("内径:")
            self.nearRadius = qt.QLineEdit()
            self.nearRadius.setMaximumWidth(50)
            farRadiusText1 = qt.QLabel("外径:")
            self.farRadius = qt.QLineEdit()
            self.farRadius.setMaximumWidth(50)

            self.QHBox1 = qt.QHBoxLayout()
            self.QHBox1.addWidget(angleText1)
            self.QHBox1.addWidget(self.probeAngle)
            self.QHBox1.addWidget(nearRadiusText1)
            self.QHBox1.addWidget(self.nearRadius)
            self.QHBox1.addWidget(farRadiusText1)
            self.QHBox1.addWidget(self.farRadius)
            ultraSonicProbeLayout.addRow(self.QHBox1)

            # Apply the probe settings button
            self.__applyProbeSettingButton = qt.QPushButton("应用")
            self.__applyProbeSettingButton.enabled = True
            self.__applyProbeSettingButton.connect('clicked(bool)', self.applyProbeSetting)
            self.QHBox2 = qt.QHBoxLayout()
            self.QHBox2.addWidget(self.__applyProbeSettingButton)
            ultraSonicProbeLayout.addRow(self.QHBox2)

            self.transformWidget = slicer.modules.transforms.widgetRepresentation()
            transformEditWidget = slicer.util.findChild(self.transformWidget, "DisplayEditCollapsibleWidget")
            transformEditWidget.text = "Edit Probe Transform"
            ultraSonicProbeLayout.addRow(transformEditWidget)

            #self.__ultraSonicProbeSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.loadUltrasonicProbe)

            # self.updateWidgetFromParameters(self.parameterNode())
            qt.QTimer.singleShot(0, self.killButton)
            Helper.Logger().info("ReviewAndMeasurementStep.createUserInterface ends.")
        except Exception as err:
            Helper.Logger().exception(err)

        
    #called when ROI bounding box is altered
    def onROIChanged(self):
        #read ROI node from combobox
        roi = self.__roiSelector.currentNode()

        if roi != None:
            self.__roi = roi
        
        # create VR node first time a valid ROI is selected
        self.InitVRDisplayNode()

        # update VR settings each time ROI changes
        pNode = self.parameterNode()
        # get scalar volume node loaded in previous step
        #v = pNode.GetNodeReference('baselineVolume')
        
        #set parameters for VR display node
        self.__vrDisplayNode.SetAndObserveROINodeID(roi.GetID())
        self.__vrDisplayNode.SetCroppingEnabled(1)
        self.__vrDisplayNode.VisibilityOn()
        
        #transform ROI
        roi.SetAndObserveTransformNodeID(self.__roiTransformNode.GetID())


        if self.__roiObserverTag != None:
            self.__roi.RemoveObserver(self.__roiObserverTag)
            
        #add observer to ROI. call self.processROIEvents if ROI is altered
        self.__roiObserverTag = self.__roi.AddObserver('ModifiedEvent', self.processROIEvents)
        
        #enable click and drag functions on ROI
        roi.SetInteractiveMode(1)
        
        #connect ROI widget to ROI
        self.__roiWidget.setMRMLAnnotationROINode(roi)
        self.__roi.SetDisplayVisibility(1)
        
    def processROIEvents(self,node = None, event = None):
        # get the range of intensities inside the ROI
        # Make updates faster and prevent flickering (due to transfer function editing)
        slicer.app.pauseRender()

        # get the IJK bounding box of the voxels inside ROI
        roiCenter = [0,0,0]
        roiRadius = [0,0,0]
        
        #get center coordinate
        self.__roi.GetXYZ(roiCenter)
        print(roiCenter) 
        
        #change slices to center of ROI
        lm = slicer.app.layoutManager()
        redWidget = lm.sliceWidget('Red')
        redController = redWidget.sliceController()
            
        yellowWidget = lm.sliceWidget('Yellow')
        yellowController = yellowWidget.sliceController()
            
        greenWidget = lm.sliceWidget('Green')
        greenController = greenWidget.sliceController()
            
        yellowController.setSliceOffsetValue(roiCenter[0])
        greenController.setSliceOffsetValue(roiCenter[1])
        redController.setSliceOffsetValue(roiCenter[2])
        
        #get radius
        self.__roi.GetRadiusXYZ(roiRadius)
        
        #get IJK coordinates of 8 corners of ROI
        roiCorner1 = [roiCenter[0]+roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]+roiRadius[2],1]
        roiCorner2 = [roiCenter[0]+roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]-roiRadius[2],1]
        roiCorner3 = [roiCenter[0]+roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]+roiRadius[2],1]
        roiCorner4 = [roiCenter[0]+roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]-roiRadius[2],1]
        roiCorner5 = [roiCenter[0]-roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]+roiRadius[2],1]
        roiCorner6 = [roiCenter[0]-roiRadius[0],roiCenter[1]+roiRadius[1],roiCenter[2]-roiRadius[2],1]
        roiCorner7 = [roiCenter[0]-roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]+roiRadius[2],1]
        roiCorner8 = [roiCenter[0]-roiRadius[0],roiCenter[1]-roiRadius[1],roiCenter[2]-roiRadius[2],1]
        
        #get RAS transformation matrix of scalar volume and convert it to IJK matrix
        ras2ijk = vtk.vtkMatrix4x4()
        self.__baselineVolume.GetRASToIJKMatrix(ras2ijk)
        
        roiCorner1ijk = ras2ijk.MultiplyPoint(roiCorner1)
        roiCorner2ijk = ras2ijk.MultiplyPoint(roiCorner2)
        roiCorner3ijk = ras2ijk.MultiplyPoint(roiCorner3)
        roiCorner4ijk = ras2ijk.MultiplyPoint(roiCorner4)
        roiCorner5ijk = ras2ijk.MultiplyPoint(roiCorner5)
        roiCorner6ijk = ras2ijk.MultiplyPoint(roiCorner6)
        roiCorner7ijk = ras2ijk.MultiplyPoint(roiCorner7)
        roiCorner8ijk = ras2ijk.MultiplyPoint(roiCorner8)

        lowerIJK = [0, 0, 0]
        upperIJK = [0, 0, 0]

        lowerIJK[0] = min(roiCorner1ijk[0],roiCorner2ijk[0],roiCorner3ijk[0],roiCorner4ijk[0],roiCorner5ijk[0],roiCorner6ijk[0],roiCorner7ijk[0],roiCorner8ijk[0])
        lowerIJK[1] = min(roiCorner1ijk[1],roiCorner2ijk[1],roiCorner3ijk[1],roiCorner4ijk[1],roiCorner5ijk[1],roiCorner6ijk[1],roiCorner7ijk[1],roiCorner8ijk[1])
        lowerIJK[2] = min(roiCorner1ijk[2],roiCorner2ijk[2],roiCorner3ijk[2],roiCorner4ijk[2],roiCorner5ijk[2],roiCorner6ijk[2],roiCorner7ijk[2],roiCorner8ijk[2])

        upperIJK[0] = max(roiCorner1ijk[0],roiCorner2ijk[0],roiCorner3ijk[0],roiCorner4ijk[0],roiCorner5ijk[0],roiCorner6ijk[0],roiCorner7ijk[0],roiCorner8ijk[0])
        upperIJK[1] = max(roiCorner1ijk[1],roiCorner2ijk[1],roiCorner3ijk[1],roiCorner4ijk[1],roiCorner5ijk[1],roiCorner6ijk[1],roiCorner7ijk[1],roiCorner8ijk[1])
        upperIJK[2] = max(roiCorner1ijk[2],roiCorner2ijk[2],roiCorner3ijk[2],roiCorner4ijk[2],roiCorner5ijk[2],roiCorner6ijk[2],roiCorner7ijk[2],roiCorner8ijk[2])
        
        #get image data of scalar volume
        image = self.__baselineVolume.GetImageData()
        
        #create image clipper
        clipper = vtk.vtkImageClip()
        clipper.ClipDataOn()
        clipper.SetOutputWholeExtent(int(lowerIJK[0]),int(upperIJK[0]),int(lowerIJK[1]),int(upperIJK[1]),int(lowerIJK[2]),int(upperIJK[2]))
        clipper.SetInputData(image)
        clipper.Update()
        
        #read upper and lower threshold values from clipped volume
        roiImageRegion = clipper.GetOutput()
        intRange = roiImageRegion.GetScalarRange()
        lThresh = 0.4*(intRange[0]+intRange[1])
        uThresh = intRange[1]
        
        #create new opacity map with voxels falling between upper and lower threshold values at 100% opacity. All others at 0%
        self.__vrOpacityMap.RemoveAllPoints()
        self.__vrOpacityMap.AddPoint(0,0)
        self.__vrOpacityMap.AddPoint(lThresh-1,0)
        self.__vrOpacityMap.AddPoint(lThresh,1)
        self.__vrOpacityMap.AddPoint(uThresh,1)
        self.__vrOpacityMap.AddPoint(uThresh+1,0)

        # finally, update the focal point to be the center of ROI
        camera = slicer.mrmlScene.GetNodeByID('vtkMRMLCameraNode1')
        camera.SetFocalPoint(roiCenter)
        camera.SetPosition(roiCenter[0],-600,roiCenter[2])
        camera.SetViewUp([0,0,1])

        slicer.app.resumeRender()

    #set up VR
    def InitVRDisplayNode(self):
        #If VR node exists, load it from saved ID
        if self.__vrDisplayNode == None:
            pNode = self.parameterNode()
            self.__vrDisplayNode = pNode.GetNodeReference('vrDisplayNode')
            if not self.__vrDisplayNode:
                v = pNode.GetNodeReference('baselineVolume')
                Helper.Logger().debug('HIFusion VR: will observe ID '+ v.GetID())
                vrLogic = slicer.modules.volumerendering.logic()
                self.__vrDisplayNode = vrLogic.CreateDefaultVolumeRenderingNodes(v)

                propNode = self.__vrDisplayNode.GetVolumePropertyNode()
                Helper.Logger().debug('Property node: '+ propNode.GetID())

                defaultRoiNode = self.__vrDisplayNode.GetROINode()
                if defaultRoiNode != self.__roi:
                    self.__vrDisplayNode.SetAndObserveROINodeID(self.__roi.GetID())
                    slicer.mrmlScene.RemoveNode(defaultRoiNode)

                vrLogic.CopyDisplayToVolumeRenderingDisplayNode(self.__vrDisplayNode)

                # Workaround: depth peeling must be disabled for volume rendering to appear properly
                viewNode = slicer.mrmlScene.GetNodeByID('vtkMRMLViewNode1')
                viewNode.SetUseDepthPeeling(False)

        viewNode = slicer.mrmlScene.GetNodeByID('vtkMRMLViewNode1')
        self.__vrDisplayNode.AddViewNodeID(viewNode.GetID())

        slicer.modules.volumerendering.logic().CopyDisplayToVolumeRenderingDisplayNode(self.__vrDisplayNode)

        #update opacity and color map
        self.__vrOpacityMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetScalarOpacity()
        self.__vrColorMap = self.__vrDisplayNode.GetVolumePropertyNode().GetVolumeProperty().GetRGBTransferFunction()

        self.__vrWidget.setMRMLVolumePropertyNode(self.__vrDisplayNode.GetVolumePropertyNode())

        # setup color transfer function once
        # two points at 0 and 500 force all voxels to be same color (any two points will work)
        self.__vrColorMap.RemoveAllPoints()
        self.__vrColorMap.AddRGBPoint(0, 0.95,0.84,0.57)
        self.__vrColorMap.AddRGBPoint(500, 0.95,0.84,0.57)

        # Update transfer function based on ROI
        self.processROIEvents()
    
    def applyProbeSetting(self):
        # load the probe model
        self.probeModelPath = os.path.join(os.path.dirname(slicer.modules.fusionhifu.path), 'Resources/ProbeModels/' + '5P1.stl')
        self.probeModelPath = self.probeModelPath.replace("\\","/")
        probeStlReader = vtk.vtkSTLReader()
        probeStlReader.SetFileName(self.probeModelPath)
        probeStlReader.Update()
        
        # flag
        self.stlTransform = vtk.vtkTransform()
        self.stlTransform.Translate(0, -200, 0)
        
        
        stlTransformPolyDataFilter = vtk.vtkTransformPolyDataFilter()
        stlTransformPolyDataFilter.SetInputData(probeStlReader.GetOutput())
        stlTransformPolyDataFilter.SetTransform(self.stlTransform)
        stlTransformPolyDataFilter.Update()
        
        model1 = slicer.modules.models.logic().AddModel(stlTransformPolyDataFilter.GetOutputPort())
        
        # load the detection area model
        r1 = float(self.nearRadius.text)
        r2 = float(self.farRadius.text)

        self.points = vtk.vtkPoints()
        # alpha = float(self.probeAngle.text)
        # 输入角度值 不是 弧度值
        alpha = (float(self.probeAngle.text) / 180) * vtk.vtkMath.Pi()
        theta = - alpha
       
        index = 0
        
        while theta <= alpha:
            self.points.InsertPoint(index, r1*math.sin(theta), 0.0, r1*math.cos(theta))
            theta += vtk.vtkMath.Pi() / 200.0 
            index += 1
        
        theta -= vtk.vtkMath.Pi() / 200.0 
        while theta >= -alpha:
            self.points.InsertPoint(index, r2*math.sin(theta), 0.0, r2*math.cos(theta))
            theta -= vtk.vtkMath.Pi() / 200.0
            index += 1

        theta += vtk.vtkMath.Pi() / 200.0 
        self.points.InsertPoint(index, r1*math.sin(theta), 0.0, r1*math.cos(theta))
        index += 1

        self.lines = vtk.vtkCellArray()
        self.lines.InsertNextCell(index)
        for i in range(0,index):
            self.lines.InsertCellPoint(i)
        
        self.detectionArea = vtk.vtkPolyData()
        self.detectionArea.SetPoints(self.points)
        self.detectionArea.SetLines(self.lines)

        # adjust initial position
        self.myTransform = vtk.vtkTransform()
 
        self.myTransform.RotateX(-90)
        self.myTransform.RotateY(0)
        self.myTransform.RotateZ(90)
        self.myTransform.Translate(0, 0, -100)

        myTransformPolyDataFilter = vtk.vtkTransformPolyDataFilter()
        myTransformPolyDataFilter.SetInputData(self.detectionArea)
        myTransformPolyDataFilter.SetTransform(self.myTransform)
        myTransformPolyDataFilter.Update()

        model2 = slicer.modules.models.logic().AddModel(myTransformPolyDataFilter.GetOutputPort())

        #transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTransformNode")
        transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode")
        matrix = vtk.vtkMatrix4x4()
        transformNode.SetMatrixTransformToParent(matrix)
        model1.SetAndObserveTransformNodeID(transformNode.GetID())
        model2.SetAndObserveTransformNodeID(transformNode.GetID())
        self.transformWidget.setEditedNode(transformNode)

        transformNode.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.onTransformNodeModified)

    def onTransformNodeModified(self, transformNode, unusedArg2=None, unusedArg3=None):
        transformMatrix = vtk.vtkMatrix4x4()
        transformNode.GetMatrixTransformToWorld(transformMatrix)
        print("原本的变换transformMatrix")
        print(transformMatrix)

        # 得到transformMatrix中的矩阵
        print("变换transformMatrix中提取它的矩阵")
        Matrix = np.array([[0,0,0,0], [0,0,0,0], [0,0,0,0], [0,0,0,0]], np.float64)

        for i in range(0,4):
            for j in range(0,4):
                Matrix[i,j] = transformMatrix.GetElement(i,j)
        # Matrix[0] = [transformMatrix.GetElement(0,0), transformMatrix.GetElement(0,1), transformMatrix.GetElement(0,2), transformMatrix.GetElement(0,3)]
        print(Matrix)
        # print("Position: [{0}, {1}, {2}]".format(transformMatrix.GetElement(0,3), transformMatrix.GetElement(1,3), transformMatrix.GetElement(2,3)))

        self.getNoramalVector(Matrix)

    ## change the preset transfer function
    def getNoramalVector(self, Matrix):
        # 得到points点数
        self.pointsNumbers = self.points.GetNumberOfPoints()
        print("总的points点数")
        print (self.pointsNumbers)
        
        # 得到要计算的三个点 第一个 中间一个 最后一个
        self.point1 = self.points.GetPoint(0)
        self.point2 = self.points.GetPoint(int(self.pointsNumbers / 2))
        self.point3 = self.points.GetPoint(self.pointsNumbers - 2)
        print("所提取的三个点的坐标")
        print (self.point1)
        print (self.point2)
        print (self.point3)

        point1_vtk_array = np.zeros(3)
        point1_vtk_array[0] = self.point1[0]
        point1_vtk_array[1] = self.point1[1]
        point1_vtk_array[2] = self.point1[2]

        point2_vtk_array = np.zeros(3)
        point2_vtk_array[0] = self.point2[0]
        point2_vtk_array[1] = self.point2[1]
        point2_vtk_array[2] = self.point2[2]
        
        point3_vtk_array = np.zeros(3)
        point3_vtk_array[0] = self.point3[0]
        point3_vtk_array[1] = self.point3[1]
        point3_vtk_array[2] = self.point3[2]
        
        # vtk变换后的坐标矩阵 
        
        self.myTransform.TransformPoint(point1_vtk_array, point1_vtk_array)
        self.myTransform.TransformPoint(point2_vtk_array, point2_vtk_array)
        self.myTransform.TransformPoint(point3_vtk_array, point3_vtk_array)
               
        print("after vtk transform")
        print (point1_vtk_array)
        print (point2_vtk_array)
        print (point3_vtk_array)
        
        # 变换前 装到数组中 最后还要推入1
        point1_array = np.zeros(4)
        point1_array[0] = point1_vtk_array[0]
        point1_array[1] = point1_vtk_array[1]
        point1_array[2] = point1_vtk_array[2]
        point1_array[3] = 1

        point2_array = np.zeros(4)
        point2_array[0] = point2_vtk_array[0]
        point2_array[1] = point2_vtk_array[1]
        point2_array[2] = point2_vtk_array[2]
        point2_array[3] = 1

        point3_array = np.zeros(4)
        point3_array[0] = point3_vtk_array[0]
        point3_array[1] = point3_vtk_array[1]
        point3_array[2] = point3_vtk_array[2]
        point3_array[3] = 1

        print("将三个点的坐标转换为可运算的矩阵")
        print (point1_array)
        print (point2_array)
        print (point3_array)
        
        # 变换后的坐标矩阵       
        point1_array_trans = np.dot(Matrix, point1_array)
        point2_array_trans = np.dot(Matrix, point2_array)
        point3_array_trans = np.dot(Matrix, point3_array)

        # 降低维度
        # point1_array_trans = np.squeeze(point1_array_trans)
        print("经过变换后的三个点的坐标矩阵")
        print("after transforming")
        print(point1_array_trans)
        print(point2_array_trans)
        print(point3_array_trans)

        # 测试
        # print("尝试提取")
        # print(point1_array_trans[0][0])
        '''
        # 加上偏移量
        self.point1[0] += self.delta_x
        self.point1[1] += self.delta_y
        self.point1[2] += self.delta_z

        self.point2[0] += self.delta_x
        self.point2[1] += self.delta_y
        self.point2[2] += self.delta_z
        
        self.point3[0] += self.delta_x
        self.point3[1] += self.delta_y
        self.point3[2] += self.delta_z
        print (self.point1)
        print (self.point2)
        print (self.point3)
        '''

        self.normalVector = np.zeros(3) #np.empty([1,3], dtype = float)
        # v1(n1, n2, n3)
        # 平面方程: na * (x – n1) + nb * (y – n2) + nc * (z – n3) = 0 
        '''
        self.normalVector[0] = (self.point2[1] - self.point1[1]) * (self.point3[2] - self.point1[2]) - (self.point2[2] - self.point1[2]) * (self.point3[1] - self.point1[1])
        self.normalVector[1] = (self.point2[2] - self.point1[2]) * (self.point3[1] - self.point1[1]) - (self.point2[0] - self.point1[0]) * (self.point3[2] - self.point1[2])
        self.normalVector[2] = (self.point2[0] - self.point1[0]) * (self.point3[1] - self.point1[1]) - (self.point2[1] - self.point1[1]) * (self.point3[0] - self.point1[0])
        '''
        self.normalVector[0] = (point2_array_trans[1] - point1_array_trans[1]) * (point3_array_trans[2] - point1_array_trans[2]) - (point2_array_trans[2] - point1_array_trans[2]) * (point3_array_trans[1] - point1_array_trans[1])
        self.normalVector[1] = (point2_array_trans[2] - point1_array_trans[2]) * (point3_array_trans[0] - point1_array_trans[0]) - (point2_array_trans[0] - point1_array_trans[0]) * (point3_array_trans[2] - point1_array_trans[2])
        self.normalVector[2] = (point2_array_trans[0] - point1_array_trans[0]) * (point3_array_trans[1] - point1_array_trans[1]) - (point2_array_trans[1] - point1_array_trans[1]) * (point3_array_trans[0] - point1_array_trans[0])
        print ("计算得到的法向量")
        print (self.normalVector)

        # 化为单位向量
        pingFang = self.normalVector[0]**2 + self.normalVector[1]**2 +self.normalVector[2]**2
        kaiPingFang = np.sqrt(pingFang)
        print ("法向量的模长")
        print (kaiPingFang)
        
        self.normalVector[0] = self.normalVector[0] / kaiPingFang
        self.normalVector[1] = self.normalVector[1] / kaiPingFang
        self.normalVector[2] = self.normalVector[2] / kaiPingFang
        #referVecStandard = np.sqrt(self.normalVector ** 2)
        #self.normalVector = (self.normalVector[0] / referVecStandard, self.normalVector[1] / referVecStandard, self.normalVector[2] / referVecStandard)
        
        print ("得到最终的单位法向量")
        print (self.normalVector)


        self.reformatLogic = slicer.modules.reformat.logic()
        redNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSliceNodeRed")
        self.reformatLogic.SetSliceOrigin(redNode, point2_array_trans[0], point2_array_trans[1], point2_array_trans[2])
        self.reformatLogic.SetSliceNormal(redNode, self.normalVector[0], self.normalVector[1], self.normalVector[2])

    def presetChanged(self, node):
        try:
            Helper.Logger().info("The selected preset volumePropertyNode is %s " % node.GetName())
            volumeRenderingWidgetRep = slicer.modules.volumerendering.widgetRepresentation()
            presetsScene = slicer.modules.volumerendering.logic().GetPresetsScene()
            preset = presetsScene.GetFirstNodeByName(node.GetName())
            volumeRenderingWidgetRep.mrmlVolumePropertyNode().Copy(preset)
        except Exception as err:
            Helper.Logger().exception(err)
    
    ## 
    def presetOffsetChanged(self, xOffset, yOffset, dontMoveFirstAndLast):
        try:
            #print("presetOffsetChanged:", xOffset, yOffset, dontMoveFirstAndLast)
            volRenWidgetRep = slicer.modules.volumerendering.widgetRepresentation()
            if volRenWidgetRep is None:
                Helper.Logger().error("Failed to access volume rendering module")
                return
            volumePropertyNodeWidget = slicer.util.findChild(volRenWidgetRep, 'VolumePropertyNodeWidget')
            # Adjust the transfer function
            volumePropertyNodeWidget.moveAllPoints(xOffset, yOffset, dontMoveFirstAndLast)
        except Exception as err:
            Helper.Logger().exception(err)

    def onEntry(self,comingFrom,transitionType):
        super(ReviewAndMeasurementStep, self).onEntry(comingFrom, transitionType)
        
        # setup the interface
        lm = slicer.app.layoutManager()
        lm.setLayout(3)
        
        #create progress bar dialog
        self.progress = qt.QProgressDialog(slicer.util.mainWindow())
        self.progress.minimumDuration = 0
        self.progress.show()
        self.progress.setValue(0)
        self.progress.setMaximum(0)
        self.progress.setCancelButton(0)
        self.progress.setMinimumWidth(500)
        self.progress.setWindowModality(2)
    
        self.progress.setLabelText('Generating Volume Rendering...')
        slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
        self.progress.repaint()
        
        #read scalar volume node ID from previous step
        pNode = self.parameterNode()
        self.__baselineVolume = pNode.GetNodeReference('baselineVolume')
        if not self.__baselineVolume:
            Helper.Logger().warning("There is no baseline Volume and cannot continue!")
            return
        
        #if ROI was created previously, get its transformation matrix and update current ROI
        roiTransformNode = pNode.GetNodeReference('roiTransform')
        if not roiTransformNode:
            roiTransformNode = slicer.vtkMRMLLinearTransformNode()
            slicer.mrmlScene.AddNode(roiTransformNode)
            pNode.SetNodeReferenceID('roiTransform', roiTransformNode.GetID())

        dm = vtk.vtkMatrix4x4()
        self.__baselineVolume.GetIJKToRASDirectionMatrix(dm)
        dm.SetElement(0,3,0)
        dm.SetElement(1,3,0)
        dm.SetElement(2,3,0)
        dm.SetElement(0,0,abs(dm.GetElement(0,0)))
        dm.SetElement(1,1,abs(dm.GetElement(1,1)))
        dm.SetElement(2,2,abs(dm.GetElement(2,2)))
        roiTransformNode.SetMatrixTransformToParent(dm)
        
        Helper.SetBgFgVolumes(self.__baselineVolume.GetID())
        Helper.SetLabelVolume(None)

        # use this transform node to align ROI with the axes of the baseline volume
        self.__roiTransformNode = pNode.GetNodeReference('roiTransform')
        if not self.__roiTransformNode:
            #Helper.Error('Internal error! Error code CT-S2-NRT, please report!')
            Helper.Logger().error('Internal error! Error code CT-S2-NRT, please report!')

        # get the roiNode from parameters node, if it exists, and initialize the GUI
        self.updateWidgetFromParameterNode(pNode)

        # start VR
        if self.__roi != None:
            self.__roi.SetDisplayVisibility(1)
            # Make sure the GUI is fully initilized because user will see it for a few seconds, while VR is being set up
            slicer.app.processEvents()
            self.InitVRDisplayNode()
        
        #close progress bar
        self.progress.setValue(2)
        self.progress.repaint()
        slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
        self.progress.close()
        self.progress = None
            
        #pNode.SetParameter('currentStep', self.stepid)
        
        qt.QTimer.singleShot(0, self.killButton)
        Helper.Logger().info(" ReviewAndMeasurementStep.onEntry Ends. ")


    def validate( self, desiredBranchId ):
        
        self.__parent.validate( desiredBranchId )
        roi = self.__roiSelector.currentNode()
        if roi == None:
            self.__parent.validationFailed(desiredBranchId, 'Error', 'Please define ROI!')

        volCheck = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLScalarVolumeNode')
        if volCheck != None:
            self.__parent.validationSucceeded('pass')
        else:
            self.__parent.validationSucceeded('fail')
            slicer.mrmlScene.Clear(0)
        
        
    def onExit(self, goingTo, transitionType):
    
        if goingTo.id() != 'Landmarks' and goingTo.id() != 'LoadData': # Change to next step
            return
        
        pNode = self.parameterNode()
        # TODO: add storeWidgetStateToParameterNode() -- move all pNode-related stuff
        # there?
        if self.__roi != None:
            self.__roi.RemoveObserver(self.__roiObserverTag)
            self.__roi.SetDisplayVisibility(0)
            
        if self.__roiSelector.currentNode() != None:
            pNode.SetNodeReferenceID('roiNode', self.__roiSelector.currentNode().GetID())
            
        if self.__vrDisplayNode != None:
            #self.__vrDisplayNode.VisibilityOff()
            pNode.SetNodeReferenceID('vrDisplayNode', self.__vrDisplayNode.GetID())
            
        if goingTo.id() == 'Landmarks': # Change to next step
        
            #create progress bar dialog
            self.progress = qt.QProgressDialog(slicer.util.mainWindow())
            self.progress.minimumDuration = 0
            self.progress.show()
            self.progress.setValue(0)
            self.progress.setMaximum(0)
            self.progress.setCancelButton(0)
            self.progress.setMinimumWidth(500)
            self.progress.setWindowModality(2)
        
            self.progress.setLabelText('Cropping and resampling volume...')
            slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
            self.progress.repaint()
        
            self.doStepProcessing()
            
            #close progress bar
            self.progress.setValue(2)
            self.progress.repaint()
            slicer.app.processEvents(qt.QEventLoop.ExcludeUserInputEvents)
            self.progress.close()
            self.progress = None

        super(ReviewAndMeasurementStep, self).onExit(goingTo, transitionType)

    def updateWidgetFromParameterNode(self, parameterNode):
        roiNode = parameterNode.GetNodeReference('roiNode')
        if not roiNode:
            roiNode = slicer.vtkMRMLAnnotationROINode()
            roiNode.Initialize(slicer.mrmlScene)
            parameterNode.SetNodeReferenceID('roiNode', roiNode.GetID())
            roiNode.SetRadiusXYZ(50, 50, 100)
            # initialize slightly off-center, as spine is usually towards posterior side of the image
            roiNode.SetXYZ(0, -50, 0)
        self.__roiSelector.setCurrentNode(roiNode)
        
        self.onROIChanged()

    def doStepProcessing(self):
        '''
        prepare roi image for the next step
        '''
        #crop scalar volume
        pNode = self.parameterNode()

        pNode.SetParameter('vertebra', self.vSelector.currentText)
        pNode.SetParameter('inst_length', self.iSelector.currentText)
        pNode.SetParameter('approach', self.aSelector.currentText)
        
        cropVolumeNode = slicer.vtkMRMLCropVolumeParametersNode()
        cropVolumeNode.SetScene(slicer.mrmlScene)
        cropVolumeNode.SetName('CropVolume_node')
        cropVolumeNode.SetIsotropicResampling(True)
        cropVolumeNode.SetSpacingScalingConst(0.5)
        slicer.mrmlScene.AddNode(cropVolumeNode)
        # TODO hide from MRML tree

        cropVolumeNode.SetInputVolumeNodeID(pNode.GetNodeReference('baselineVolume').GetID())
        cropVolumeNode.SetROINodeID(pNode.GetNodeReference('roiNode').GetID())
        # cropVolumeNode.SetAndObserveOutputVolumeNodeID(outputVolume.GetID())

        cropVolumeLogic = slicer.modules.cropvolume.logic()
        cropVolumeLogic.Apply(cropVolumeNode)

        # TODO: cropvolume error checking
        outputVolume = slicer.mrmlScene.GetNodeByID(cropVolumeNode.GetOutputVolumeNodeID())
        outputVolume.SetName("baselineROI")
        pNode.SetNodeReferenceID('croppedBaselineVolume',cropVolumeNode.GetOutputVolumeNodeID())
        
        self.__vrDisplayNode = None