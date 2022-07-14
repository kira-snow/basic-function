from __main__ import qt, ctk, vtk, slicer

import math
import numpy as np
import DICOM
import PythonQt

from slicer.ScriptedLoadableModule import *
from vtkmodules.vtkCommonCore import vtkMath
from slicer.util import VTKObservationMixin

from .FusionHIFUStep import *
from .Helper import *


class LoadDataStep(FusionHIFUStep):
    '''
    load data and do mpr reconstruction. 1. data probe; 2. adjust layout
    '''
    def __init__( self, stepid ):
        # VTKObservationMixin.__init__(self)
        self.initialize( stepid )
        self.setName( '1. 加载图像' )
        self.setDescription( "Load a volume into the scene. Click 'Import DICOM folder' to import DICOM data; Click 'Show DICOM browser' to open the DICOM browser window. Click 'Load CT/MR from other file' to import other file types, including .nrrd" )

        # # Members
        # self.numberOfRulersInScene = 0
        # self.ruler1 = None
        # self.ruler2 = None
        # self.angleDeg = None
        #
        self.rulerNodeClass = 'vtkMRMLAnnotationRulerNode'

        self.__parent = super(LoadDataStep, self)
        slicer.mrmlScene.AddObserver(slicer.vtkMRMLScene.NodeAddedEvent, self.onVolumeNodeAdded)

        Helper.Logger().info("LoadDataStep.init ends")
    
    def killButton(self):
        # hide useless button
        bl = slicer.util.findChildren(text='Final')
        if len(bl):
            bl[0].hide()
    
    def createUserInterface( self ):
        self.__layout = self.__parent.createUserInterface()

      #import DICOM folder button
        self.__importDICOMBrowser = qt.QPushButton("导入DICOM图像文件夹")
        self.__layout.addRow(self.__importDICOMBrowser)
        self.__importDICOMBrowser.connect('clicked(bool)', self.importDICOMBrowser)

      #show DICOM browser button
        self.__showDICOMBrowserButton = qt.QPushButton("浏览已导入DICOM文件")
        self.__layout.addRow(self.__showDICOMBrowserButton)
        self.__showDICOMBrowserButton.connect('clicked(bool)', self.showDICOMBrowser)

        # open load data dialog for adding nrrd files
        self.__loadScrewButton = qt.QPushButton("从其他文件加载CT/MR图像")
        self.__layout.addRow(self.__loadScrewButton)
        self.__loadScrewButton.connect('clicked(bool)', self.loadVolume)

        # Active Volume text
        self.activeText = qt.QLabel("激活体积数据:")
        self.__layout.addRow(self.activeText)

        # select volume
        # creates combobox and populates it with all vtkMRMLScalarVolumeNodes in the scene
        self.__inputSelector = slicer.qMRMLNodeComboBox()
        self.__inputSelector.nodeTypes = (("vtkMRMLScalarVolumeNode"), "")
        self.__inputSelector.addEnabled = False
        self.__inputSelector.removeEnabled = False
        self.__inputSelector.selectNodeUponCreation = True
        self.__inputSelector.noneEnabled = False
        self.__inputSelector.showHidden = False
        self.__inputSelector.showChildNodeTypes = True
        self.__inputSelector.setMRMLScene(slicer.mrmlScene)
        self.__layout.addRow(self.__inputSelector)

        # Hide volumes information Details
        volumesDetailsCollapsibleButton = ctk.ctkCollapsibleButton()
        volumesDetailsCollapsibleButton.text = "体积详情"
        self.__layout.addWidget(volumesDetailsCollapsibleButton)
        volumesDetailsCollapsibleButton.collapsed = True

        # Layout
        volumesDetailsLayout = qt.QFormLayout(volumesDetailsCollapsibleButton)

        # -----------------------------------------------------------------------------------------------

        volumeNode = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLScalarVolumeNode')
        slicer.modules.volumes.logic().SetActiveVolumeNode(volumeNode)
        self.scalarVolumeDisplayWidget = PythonQt.qSlicerVolumesModuleWidgets.qSlicerScalarVolumeDisplayWidget()
        self.scalarVolumeDisplayWidget.setMRMLVolumeNode(volumeNode)  # 设置当前的volumeNode
        self.scalarVolumeDisplayWidget.enabled =  True

        colorTableComboBox = slicer.util.findChild(self.scalarVolumeDisplayWidget,  'ColorTableComboBox')  # 类型是 qMRMLColorTableComboBox
        colorTableComboBox.setMRMLScene(slicer.mrmlScene)  # 参考了 https://github.com/Slicer/Slicer/blob/master/Libs/MRML/Widgets/Testing/qMRMLNodeComboBoxLazyUpdateTest1.cxx
        volumesDetailsLayout.addRow(colorTableComboBox)

        windowLevelWidget = slicer.util.findChild(self.scalarVolumeDisplayWidget, 'MRMLWindowLevelWidget')
        volumesDetailsLayout.addRow(windowLevelWidget)
        
        volumeThreadWidget = slicer.util.findChild(self.scalarVolumeDisplayWidget, 'MRMLVolumeThresholdWidget')
        volumesDetailsLayout.addRow(volumeThreadWidget)

        # Camera Transform Sliders
        transCam = ctk.ctkCollapsibleButton()
        transCam.text = "变换"
        transCam.collapsed = True
        self.__layout.addWidget(transCam)
        camLayout = qt.QFormLayout(transCam)

        #
        # fit control
        #
        self.fitHolder = qt.QWidget()
        fitlayout = qt.QHBoxLayout()
        self.fitHolder.setLayout(fitlayout)
        fits = { "Fit": "Fit", }
        for fitLabel, fitFactor in fits.items():
            fitButton = qt.QPushButton(fitLabel)
            fitButton.connect('clicked()', lambda zf=fitFactor: self.onfit(zf))
            fitlayout.addWidget(fitButton)
        camLayout.addRow("fit", self.fitHolder)

        # orientation display

        self.orientationBox = qt.QGroupBox("方向")
        self.orientationBox.setLayout(qt.QFormLayout())
        self.orientationButtons = {}
        self.orientations = ("水平面", "矢状面", "冠状面")
        for orientation in self.orientations:
            self.orientationButtons[orientation] = qt.QRadioButton()
            self.orientationButtons[orientation].text = orientation
            self.orientationButtons[orientation].connect("clicked()",
                                                         lambda o=orientation: self.setOrientation(o))
            self.orientationBox.layout().addWidget(
                self.orientationButtons[orientation])
        camLayout.addWidget(self.orientationBox)
        self.setOrientation(self.orientations[0])

        #
        # target volume selector
        #
        self.inputSelector = slicer.qMRMLNodeComboBox()
        self.inputSelector.nodeTypes = (("vtkMRMLVolumeNode"), "")
        self.inputSelector.setMRMLScene(slicer.mrmlScene)
        self.inputSelector.setToolTip("Pick the input to the algorithm.")
        camLayout.addRow("目标体积: ", self.inputSelector)

        #
        # the selecteMake a set of slice views that show each of the currently loaded volumes, with optional companion volumes, in d orientation
        #
        self.lightboxVolumesButton = qt.QPushButton("Lightbox All Volumes")
        self.lightboxVolumesButton.setToolTip(
            "Make a set of slice views that show each of the currently loaded volumes, with optional companion volumes, in the selected orientation.")
        camLayout.addRow(self.lightboxVolumesButton)
        self.lightboxVolumesButton.connect("clicked()", self.onLightboxVolumes)

        #
        # Make a set of slice views that span the extent of this study at equally spaced locations in the selected orientation
        #
        self.lightboxVolumeButton = qt.QPushButton("FourOverFourLayout")
        self.lightboxVolumeButton.setToolTip(
            "Make a set of slice views that span the extent of this study at equally spaced locations in the selected orientation.")
        camLayout.addRow(self.lightboxVolumeButton)
        self.lightboxVolumeButton.connect("clicked()", self.SlicerLayoutFourOverFourView)

        self.lightboxVolumeButton = qt.QPushButton("ThreeOverThreeLayout")
        self.lightboxVolumeButton.setToolTip(
            "Make a set of slice views that span the extent of this study at equally spaced locations in the selected orientation.")
        camLayout.addRow(self.lightboxVolumeButton)
        self.lightboxVolumeButton.connect("clicked()", self.SlicerLayoutThreeOverThreeView)

        self.lightboxVolumeButton = qt.QPushButton("3DViewLayout")
        self.lightboxVolumeButton.setToolTip(
            "Make a set of slice views that span the extent of this study at equally spaced locations in the selected orientation.")
        camLayout.addRow(self.lightboxVolumeButton)
        self.lightboxVolumeButton.connect("clicked()", self.SlicerLayoutOneUp3DView)

        #
        # Measurements angle etc...
        #
        MeasurementsCollapsibleButton = ctk.ctkCollapsibleButton()
        MeasurementsCollapsibleButton.text = "测量"
        self.__layout.addWidget(MeasurementsCollapsibleButton)
        MeasurementsCollapsibleButton.collapsed = True

        # Layout
        MeasurementsLayout = qt.QFormLayout(MeasurementsCollapsibleButton)
        self.layoutOptions = ("angle", "distance", "plane", "curve","compute area")
        self.layoutOption = 'angle/distance/plane/curve/compute area'

        #
        # layout selection
        #
        self.layoutHolder = qt.QWidget()
        layout = qt.QHBoxLayout()
        self.layoutHolder.setLayout(layout)
        for layoutOption in self.layoutOptions:
            layoutButton = qt.QPushButton(layoutOption)
            layoutButton.connect('clicked()', lambda lo = layoutOption: self.selectLayout(lo))
            layout.addWidget(layoutButton)
        MeasurementsLayout.addRow("method:", self.layoutHolder)

        self.Measurementstable2 = qt.QTableWidget()
        self.Measurementstable2.setRowCount(1)
        self.Measurementstable2.setColumnCount(2)
        # self.Measurementstable2.horizontalHeader().setResizeMode(qt.QHeaderView.Stretch)
        self.Measurementstable2.setSizePolicy(qt.QSizePolicy.MinimumExpanding, qt.QSizePolicy.Preferred)
        self.Measurementstable2.setMinimumWidth(50)
        self.Measurementstable2.setMinimumHeight(215)
        self.Measurementstable2.setMaximumHeight(215)
        horizontalHeaders = ["type", "Figure"]
        self.Measurementstable2.setHorizontalHeaderLabels(horizontalHeaders)
        MeasurementsLayout.addWidget(self.Measurementstable2)
        self.rownumber=0
        # self.newItem = 'area'

        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        # call the set reference to make sure the event is invoked
        selectionNode.SetReferenceActivePlaceNodeClassName(self.rulerNodeClass)
        selectionNode.SetActivePlaceNodeID(None)
        interactionNode = slicer.app.applicationLogic().GetInteractionNode()
        interactionNode.SetPlaceModePersistence(True)

        # function

        # loaddata function
        Helper.Logger().info("LoadDataStep.createUserInterface ends")

    def loadVolume(self):
        slicer.util.openAddDataDialog()

    def importDICOMBrowser(self):
        """If DICOM database is invalid then try to create a default one. If fails then show an error message."""
        if slicer.modules.DICOMInstance.browserWidget is None:
            slicer.util.selectModule('DICOM')
            slicer.util.selectModule('FusionHIFU')
        # Make the DICOM browser disappear after loading data
        slicer.modules.DICOMInstance.browserWidget.browserPersistent = False
        if not slicer.dicomDatabase or not slicer.dicomDatabase.isOpen:
        # Try to create a database with default settings
            slicer.modules.DICOMInstance.browserWidget.dicomBrowser.createNewDatabaseDirectory()
            if not slicer.dicomDatabase or not slicer.dicomDatabase.isOpen:
            # Failed to create database
            # Show DICOM browser then display error message
                slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutDicomBrowserView)
                slicer.util.warningDisplay("Could not create a DICOM database with default settings. Please create a new database or"
                " update the existing incompatible database using options shown in DICOM browser.")
                return

        slicer.modules.dicom.widgetRepresentation().self().browserWidget.dicomBrowser.openImportDialog()
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutDicomBrowserView)
        slicer.modules.DICOMInstance.browserWidget.waitForImportFinished()
    
    @vtk.calldata_type(vtk.VTK_OBJECT)
    def onVolumeNodeAdded(self, caller, event, calldata):
        node = calldata
        if isinstance(node, slicer.vtkMRMLScalarVolumeNode):
        # Call setMRMLVolumeNode using a timer instead of calling it directly to allow the volume loading to fully complete.
            qt.QTimer.singleShot(0, lambda : self.scalarVolumeDisplayWidget.setMRMLVolumeNode(node))

    def showDICOMBrowser(self):
        if slicer.modules.DICOMInstance.browserWidget is None:
            slicer.util.selectModule('DICOM')
            slicer.util.selectModule('FusionHIFU')
        # Make the DICOM browser disappear after loading data
        slicer.modules.DICOMInstance.browserWidget.browserPersistent = False
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutDicomBrowserView)

    def edit_button_callable(self):
        self.TextEdit.setReadOnly(False)

    def save_button_callable(self):
        self.TextEdit.setReadOnly(True)

    def clear_button_callable(self):
        self.TextEdit.clear()

        # windowslevel function



    def selectLayout(self, layoutOption):
        self.layoutOption = layoutOption
        if self.layoutOption == "angle":
            selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            # place angle
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsAngleNode")
            # to place ROIs use the class name vtkMRMLMarkupsAngleNode
            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            placeModePersistence = 1
            interactionNode.SetPlaceModePersistence(placeModePersistence)
            # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
            interactionNode.SetCurrentInteractionMode(1)
        elif self.layoutOption == "distance":
            selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            # place rulers
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLAnnotationRulerNode")
            # to place ROIs use the class name vtkMRMLAnnotationROINode
            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            placeModePersistence = 1
            interactionNode.SetPlaceModePersistence(placeModePersistence)
            # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
            interactionNode.SetCurrentInteractionMode(1)
        elif self.layoutOption == "plane":
            selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            # place Plane
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsPlaneNode")
            # to place ROIs use the class name vtkMRMLMarkupsPlaneNode
            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            placeModePersistence = 1
            interactionNode.SetPlaceModePersistence(placeModePersistence)
            # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
            interactionNode.SetCurrentInteractionMode(1)
            planes = slicer.util.getNodesByClass("vtkMRMLMarkupsPlaneNode")
            # TODO Added by YCS, The method of area calculation is wrong
            for plane in planes:
                bounds=[0,0,0,0,0,0]
                plane.GetPlaneBounds(bounds)

                area = (bounds[1]-bounds[0])*(bounds[3]-bounds[2])*0.01
                print("Plane{0}:surface area ={1:2f}".format(plane.GetName(),area))

        elif self.layoutOption == "curve":
            slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsClosedCurveNode")
            selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
            # place closed curve
            selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsClosedCurveNode")
            # to place ROIs use the class name vtkMRMLMarkupsClosedCurveNode
            interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
            placeModePersistence = 1
            interactionNode.SetPlaceModePersistence(placeModePersistence)
            # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
            interactionNode.SetCurrentInteractionMode(1)
            # curves = slicer.util.getNodesByClass("vtkMRMLMarkupsClosedCurveNode")
            # # TODO YCS: is the method suitable to rectangle?
        elif self.layoutOption == "compute area":
            planes = slicer.util.getNodesByClass("vtkMRMLMarkupsPlaneNode")
            curves = slicer.util.getNodesByClass("vtkMRMLMarkupsClosedCurveNode")
            self.rownumber=0
            self.Measurementstable2.setRowCount(len(curves)+len(planes)-1)
            for curve in curves:
                crossSectionSurface = vtk.vtkPolyData()
                areaMm2 = slicer.modules.markups.logic().GetClosedCurveSurfaceArea(curve, crossSectionSurface)
                crossSectionSurfaceModel = slicer.modules.models.logic().AddModel(crossSectionSurface)
                crossSectionSurfaceModel.SetName("{0} surface".format(curve.GetName()))
                crossSectionSurfaceModel.CreateDefaultDisplayNodes()
                crossSectionSurfaceModel.GetDisplayNode().BackfaceCullingOff()
                crossSectionSurfaceModel.GetDisplayNode().SetColor(curve.GetDisplayNode().GetColor())
                crossSectionSurfaceModel.GetDisplayNode().SetOpacity(0.5)
                crossSectionSurfaceModel.SetDescription("Area[cm2] = {0:.2f}".format(areaMm2*0.01))
                print("Curve {0}: surface area = {1:.2f} cm2".format(curve.GetName(), areaMm2*0.01))
                self.Measurementstable2.setItem(self.rownumber, 0, qt.QTableWidgetItem(curve.GetName()))
                self.Measurementstable2.setItem(self.rownumber, 1, qt.QTableWidgetItem("{:.2f} cm2".format(areaMm2*0.01)))
                self.rownumber = self.rownumber + 1
            for plane in planes:
                bounds=[0,0,0,0,0,0]
                plane.GetPlaneBounds(bounds)
                area = (bounds[1]-bounds[0])*(bounds[3]-bounds[2])*0.01
                if area!=0 :
                    print("Plane{0}:surface area ={1:2f}".format(plane.GetName(),area))
                    self.Measurementstable2.setItem(self.rownumber, 0, qt.QTableWidgetItem(plane.GetName()))
                    self.Measurementstable2.setItem(self.rownumber, 1, qt.QTableWidgetItem("{:.2f} cm2".format(area)))
                    self.rownumber = self.rownumber + 1


    def onTableCellClicked(self):
        pass
    def onfit(self, fitFactor):
        import CompareVolumes
        compareLogic = CompareVolumes.CompareVolumesLogic()
        compareLogic.zoom(fitFactor)

        # Make a set of slice views  function

    def setOrientation(self, orientation):
        if orientation in self.orientations:
            self.selectedOrientation = orientation
            self.orientationButtons[orientation].checked = True

    def SlicerLayoutFourOverFourView(self):
        layoutManager = slicer.app.layoutManager()
        layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourOverFourView)
        # slicer.mrmlScene.Clear(0)
    def SlicerLayoutThreeOverThreeView(self):
        layoutManager = slicer.app.layoutManager()
        layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutThreeOverThreeView)
    def SlicerLayoutOneUp3DView(self):
        layoutManager = slicer.app.layoutManager()
        layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)


    def onLightboxVolumes(self):
        import CompareVolumes
        logic = CompareVolumes.CompareVolumesLogic()
        logic.viewerPerVolume(
            orientation=self.selectedOrientation,
            background=self.inputSelector.currentNode()
            # label=self.labelSelector.currentNode(),
        )

        # Measurements angle function

    def onsetrulerButton(self):

        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        # place rulers
        selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLAnnotationRulerNode")
        # to place ROIs use the class name vtkMRMLAnnotationROINode
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        placeModePersistence = 1
        interactionNode.SetPlaceModePersistence(placeModePersistence)
        # mode 1 is Place, can also be accessed via slicer.vtkMRMLInteractionNode().Place
        interactionNode.SetCurrentInteractionMode(1)

    def onAddToTableButton(self):
        rowIndex = self.resultsTableNode.AddEmptyRow()
        volumeNode = slicer.util.getNode(self.ruler1.GetAttribute('AssociatedNodeID'))
        self.resultsTableNode.SetCellText(rowIndex, 0, volumeNode.GetName() if volumeNode else "")
        self.resultsTableNode.SetCellText(rowIndex, 1, "{:.1f}".format(self.angleDeg))
        self.onClearRulers()

    def onSceneUpdated(self, caller=None, event=None):
        oldNumberOfRulersInScene = self.numberOfRulersInScene
        oldRuler1 = self.ruler1
        oldRuler2 = self.ruler2
        newRuler1 = None
        newRuler2 = None
        self.numberOfRulersInScene = slicer.mrmlScene.GetNumberOfNodesByClass(self.rulerNodeClass)

        if self.numberOfRulersInScene == 2:
            newRuler1 = slicer.mrmlScene.GetNthNodeByClass(0, self.rulerNodeClass)
            newRuler2 = slicer.mrmlScene.GetNthNodeByClass(1, self.rulerNodeClass)

        if newRuler1 == oldRuler1 and newRuler2 == oldRuler2 and oldNumberOfRulersInScene == self.numberOfRulersInScene:
            # no change
            return

        if self.numberOfRulersInScene >= 2:
            interactionNode = slicer.app.applicationLogic().GetInteractionNode()
            interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)

        self.ruler1 = newRuler1
        self.ruler2 = newRuler2
        self.removeObservers(self.onRulerChanged)
        if self.ruler1 and self.ruler2:
            self.addObserver(self.ruler1, vtk.vtkCommand.ModifiedEvent, self.onRulerChanged)
            self.addObserver(self.ruler2, vtk.vtkCommand.ModifiedEvent, self.onRulerChanged)
        self.onRulerChanged()

    def onRulerChanged(self, caller=None, event=None):
        if self.numberOfRulersInScene != 2:
            if self.numberOfRulersInScene < 2:
                self.resultPreview.text = "Not enough rulers"
            else:
                self.resultPreview.text = "There are more than two rulers"
            self.angleDeg = None
            self.applyButton.enabled = False
            return

        directionVectors = []
        for ruler in [self.ruler1, self.ruler2]:
            p1 = np.array([0, 0, 0])
            p2 = np.array([0, 0, 0])
            ruler.GetControlPointWorldCoordinates(0, p1)
            ruler.GetControlPointWorldCoordinates(1, p2)
            directionVectors.append(p2 - p1)

        # Compute angle (0 <= angle <= 90)
        cosang = np.dot(directionVectors[0], directionVectors[1])
        sinang = np.linalg.norm(np.cross(directionVectors[0], directionVectors[1]))
        angleDeg = math.fabs(np.arctan2(sinang, cosang) * 180.0 / math.pi)

        self.angleDeg = angleDeg
        self.resultPreview.text = "{:.1f}".format(self.angleDeg)
        self.applyButton.enabled = True

    def onClearRulers(self):
        rulers = slicer.util.getNodesByClass(self.rulerNodeClass)
        for ruler in rulers:
            slicer.mrmlScene.RemoveNode(ruler)

    def onClearLastMeasurement(self):
        numOfRows = self.resultsTableNode.GetNumberOfRows()
        if numOfRows > 0:
            self.resultsTableNode.RemoveRow(numOfRows - 1)

    def addFiducials(self):
        pass

    #called when entering step
    def onEntry(self, comingFrom, transitionType):
        super(LoadDataStep, self).onEntry(comingFrom, transitionType)

        # setup the interface
        lm = slicer.app.layoutManager()
        lm.setLayout(3)
        
        qt.QTimer.singleShot(0, self.killButton)
        Helper.Logger().info("LoadDataStep.onEntry Ends.")
      
    
    #check that conditions have been met before proceeding to next step
    def validate( self, desiredBranchId ):
        self.__parent.validate( desiredBranchId )
        
        #read current scalar volume node
        self.__baseline = self.__inputSelector.currentNode()  
      
        #if scalar volume exists proceed to next step and save node ID as 'baselineVolumeID'
        pNode = self.parameterNode()
        if self.__baseline != None:
            baselineID = self.__baseline.GetID()
            if baselineID != '':
              pNode = self.parameterNode()
              pNode.SetNodeReferenceID('baselineVolume', baselineID)
              self.__parent.validationSucceeded(desiredBranchId)
        else:
            self.__parent.validationFailed(desiredBranchId, 'Error','Please load a volume before proceeding')
        
    #called when exiting step
    def onExit(self, goingTo, transitionType):
        #check to make sure going to correct step
        if goingTo.id() == 'ReviewAndMeasurement':
            self.doStepProcessing()
        
        if goingTo.id() != 'ReviewAndMeasurement':
            return

        super(LoadDataStep, self).onExit(goingTo, transitionType)
                 
    def doStepProcessing(self):
        #transforms center of imported volume to world origin
        coords = [0,0,0]
        coords = self.__baseline.GetOrigin()
        
        transformVolmat = vtk.vtkMatrix4x4()
        transformVolmat.SetElement(0,3,coords[0]*-1)
        transformVolmat.SetElement(1,3,coords[1]*-1)
        transformVolmat.SetElement(2,3,coords[2]*-1)
        
        transformVol = slicer.vtkMRMLLinearTransformNode()
        slicer.mrmlScene.AddNode(transformVol)
        transformVol.ApplyTransformMatrix(transformVolmat)
        
        #harden transform
        self.__baseline.SetAndObserveTransformNodeID(transformVol.GetID())
        slicer.vtkSlicerTransformLogic.hardenTransform(self.__baseline)
        
        #offsets volume so its center is registered to world origin
        newCoords = [0,0,0,0,0,0]
        self.__baseline.GetRASBounds(newCoords)
        print(newCoords) 
        shift = [0,0,0]
        shift[0] = 0.5*(newCoords[1] - newCoords[0])
        shift[1] = 0.5*(newCoords[3] - newCoords[2])
        shift[2] = 0.5*(newCoords[4] - newCoords[5])
        
        transformVolmat2 = vtk.vtkMatrix4x4()
        transformVolmat2.SetElement(0,3,shift[0])
        transformVolmat2.SetElement(1,3,shift[1])
        transformVolmat2.SetElement(2,3,shift[2])
        
        transformVol2 = slicer.vtkMRMLLinearTransformNode()
        slicer.mrmlScene.AddNode(transformVol2)
        transformVol2.ApplyTransformMatrix(transformVolmat2)
        
        #harden transform
        self.__baseline.SetAndObserveTransformNodeID(transformVol2.GetID())
        slicer.vtkSlicerTransformLogic.hardenTransform(self.__baseline)
        
        #remove transformations from scene
        slicer.mrmlScene.RemoveNode(transformVol)
        slicer.mrmlScene.RemoveNode(transformVol2)
        Helper.Logger().info("LoadDataStep.doStepProcessing ends")
