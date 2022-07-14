import os
import unittest
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

import FusionHIFUWizard

#
# FusionHIFU
#

class FusionHIFU(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "FusionHIFU" 
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    self.parent.contributors = ["XU Kailiang (Fudan University.)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
HIFusion. Planning, Treatment, and Evaluation for HIFU.
"""
    self.parent.helpText += self.getDefaultModuleDocumentationLink()
    self.parent.acknowledgementText = """
HIFusion. 
""" # replace with organization, grant and thanks.

#
# FusionHIFUWidget
#

class FusionHIFUWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    self.logger = FusionHIFUWizard.Helper.Logger()

    # Instantiate and connect widgets ...
    self.workflow = ctk.ctkWorkflow()
    workflowWidget = ctk.ctkWorkflowStackedWidget()
    workflowWidget.setWorkflow( self.workflow )

    # create all wizard steps
    self.loadDataStep = FusionHIFUWizard.LoadDataStep('LoadData')
    self.reviewAndMeasurementsStep = FusionHIFUWizard.ReviewAndMeasurementStep("ReviewAndMeasurement")
    # self.defineROIStep = FusionHIFUWizard.DefineROIStep( 'DefineROI'  )
    # self.measurementsStep = FusionHIFUWizard.MeasurementsStep( 'Measurements'  )
    # self.landmarksStep = FusionHIFUWizard.LandmarksStep( 'Landmarks' )
    # self.screwStep = FusionHIFUWizard.ScrewStep( 'Screw' )
    # self.gradeStep = FusionHIFUWizard.GradeStep( 'Grade' )
    self.endStep = FusionHIFUWizard.EndStep('Final')
    
    # add the wizard steps to an array for convenience
    allSteps = []

    allSteps.append( self.loadDataStep )
    allSteps.append(self.reviewAndMeasurementsStep)
    # allSteps.append( self.defineROIStep )
    # allSteps.append( self.landmarksStep)
    # allSteps.append( self.measurementsStep )
    # allSteps.append( self.screwStep)
    # allSteps.append( self.gradeStep)
    allSteps.append( self.endStep )
    
    
    # Add transition 
    # Check if volume is loaded
    self.workflow.addTransition( self.loadDataStep, self.reviewAndMeasurementsStep )

    self.workflow.addTransition(self.reviewAndMeasurementsStep, self.loadDataStep, "fail", ctk.ctkWorkflow.Bidirectional)
    
    # self.workflow.addTransition( self.defineROIStep, self.landmarksStep, 'pass', ctk.ctkWorkflow.Bidirectional )
    # self.workflow.addTransition( self.defineROIStep, self.loadDataStep, 'fail', ctk.ctkWorkflow.Bidirectional  )
    
    # self.workflow.addTransition( self.landmarksStep, self.measurementsStep, 'pass', ctk.ctkWorkflow.Bidirectional )
    # self.workflow.addTransition( self.landmarksStep, self.measurementsStep, 'fail', ctk.ctkWorkflow.Bidirectional )
    
    # self.workflow.addTransition( self.measurementsStep, self.screwStep, 'pass', ctk.ctkWorkflow.Bidirectional )
    # self.workflow.addTransition( self.measurementsStep, self.screwStep, 'fail', ctk.ctkWorkflow.Bidirectional )
    
    # self.workflow.addTransition( self.screwStep, self.gradeStep, 'pass', ctk.ctkWorkflow.Bidirectional )
    # self.workflow.addTransition( self.screwStep, self.gradeStep, 'fail', ctk.ctkWorkflow.Bidirectional )
          
    self.workflow.addTransition( self.reviewAndMeasurementsStep, self.endStep )
           
    nNodes = slicer.mrmlScene.GetNumberOfNodesByClass('vtkMRMLScriptedModuleNode')

    self.parameterNode = None
    for n in range(nNodes):
      compNode = slicer.mrmlScene.GetNthNodeByClass(n, 'vtkMRMLScriptedModuleNode')
      nodeid = None
      if compNode.GetModuleName() == 'FusionHIFU':
        self.parameterNode = compNode
        self.logger.info("Found existing FusionHIFU parameter node")
        break
    if self.parameterNode == None:
      self.parameterNode = slicer.vtkMRMLScriptedModuleNode()
      self.parameterNode.SetModuleName('FusionHIFU')
      slicer.mrmlScene.AddNode(self.parameterNode)
 
    for s in allSteps:
        s.setParameterNode (self.parameterNode)
    
    # restore workflow step
    currentStep = self.parameterNode.GetParameter('currentStep')
    
    if currentStep != '':
      self.logger.info("Restoring workflow step to %s" % currentStep)
      if currentStep == 'LoadData':
        self.workflow.setInitialStep(self.loadDataStep)
      if currentStep == 'ReviewAndMeasurement':
        self.workflow.setInitialStep(self.reviewAndMeasurementsStep)
      # if currentStep == 'Measurements':
      #   self.workflow.setInitialStep(self.measurementsStep)
      # if currentStep == 'Landmarks':
      #   self.workflow.setInitialStep(self.landmarksStep)
      # if currentStep == 'Screw':
      #   self.workflow.setInitialStep(self.screwStep) 
      # if currentStep == 'Grade':
      #   self.workflow.setInitialStep(self.gradeStep)   
      if currentStep == 'Final':
        self.workflow.setInitialStep(self.endStep)
    else:
      self.logger.info("currentStep in parameter node is empty!")
    
    
    # start the workflow and show the widget
    self.workflow.start()
    workflowWidget.visible = True
    self.layout.addWidget( workflowWidget )

    self.logger.info("FusionHIFUWidget.setup finish")

    # compress the layout
    #self.layout.addStretch(1)        

    # #
    # # Parameters Area
    # #
    # parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    # parametersCollapsibleButton.text = "Parameters"
    # self.layout.addWidget(parametersCollapsibleButton)

    # # Layout within the dummy collapsible button
    # parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    # #
    # # input volume selector
    # #
    # self.inputSelector = slicer.qMRMLNodeComboBox()
    # self.inputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    # self.inputSelector.selectNodeUponCreation = True
    # self.inputSelector.addEnabled = False
    # self.inputSelector.removeEnabled = False
    # self.inputSelector.noneEnabled = False
    # self.inputSelector.showHidden = False
    # self.inputSelector.showChildNodeTypes = False
    # self.inputSelector.setMRMLScene( slicer.mrmlScene )
    # self.inputSelector.setToolTip( "Pick the input to the algorithm." )
    # parametersFormLayout.addRow("Input Volume: ", self.inputSelector)

    # #
    # # output volume selector
    # #
    # self.outputSelector = slicer.qMRMLNodeComboBox()
    # self.outputSelector.nodeTypes = ["vtkMRMLScalarVolumeNode"]
    # self.outputSelector.selectNodeUponCreation = True
    # self.outputSelector.addEnabled = True
    # self.outputSelector.removeEnabled = True
    # self.outputSelector.noneEnabled = True
    # self.outputSelector.showHidden = False
    # self.outputSelector.showChildNodeTypes = False
    # self.outputSelector.setMRMLScene( slicer.mrmlScene )
    # self.outputSelector.setToolTip( "Pick the output to the algorithm." )
    # parametersFormLayout.addRow("Output Volume: ", self.outputSelector)

    # #
    # # threshold value
    # #
    # self.imageThresholdSliderWidget = ctk.ctkSliderWidget()
    # self.imageThresholdSliderWidget.singleStep = 0.1
    # self.imageThresholdSliderWidget.minimum = -100
    # self.imageThresholdSliderWidget.maximum = 100
    # self.imageThresholdSliderWidget.value = 0.5
    # self.imageThresholdSliderWidget.setToolTip("Set threshold value for computing the output image. Voxels that have intensities lower than this value will set to zero.")
    # parametersFormLayout.addRow("Image threshold", self.imageThresholdSliderWidget)

    # #
    # # check box to trigger taking screen shots for later use in tutorials
    # #
    # self.enableScreenshotsFlagCheckBox = qt.QCheckBox()
    # self.enableScreenshotsFlagCheckBox.checked = 0
    # self.enableScreenshotsFlagCheckBox.setToolTip("If checked, take screen shots for tutorials. Use Save Data to write them to disk.")
    # parametersFormLayout.addRow("Enable Screenshots", self.enableScreenshotsFlagCheckBox)

    # #
    # # Apply Button
    # #
    # self.applyButton = qt.QPushButton("Apply")
    # self.applyButton.toolTip = "Run the algorithm."
    # self.applyButton.enabled = False
    # parametersFormLayout.addRow(self.applyButton)

    # # connections
    # self.applyButton.connect('clicked(bool)', self.onApplyButton)
    # self.inputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)
    # self.outputSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelect)

    # # Add vertical spacer
    # self.layout.addStretch(1)

    # # Refresh Apply button state
    # self.onSelect()

  def cleanup(self):
    pass

  def onReload(self):
    self.logger.debug("Reloading FusionHIFU")

    packageName='FusionHIFUWizard'
    submoduleNames=['FusionHIFUStep',
      'ReviewAndMeasurementsStep'
      'Logger'
      'EndStep',
      'Helper',
      'LoadDataStep']  # add other steps
    
    import imp
    f, filename, description = imp.find_module(packageName)
    package = imp.load_module(packageName, f, filename, description)
    for submoduleName in submoduleNames:
      f, filename, description = imp.find_module(submoduleName, package.__path__)
      try:
          imp.load_module(packageName+'.'+submoduleName, f, filename, description)
      finally:
          f.close()
          
    ScriptedLoadableModuleWidget.onReload(self)

  def onSelect(self):
    self.applyButton.enabled = self.inputSelector.currentNode() and self.outputSelector.currentNode()

  def onApplyButton(self):
    logic = FusionHIFULogic()
    enableScreenshotsFlag = self.enableScreenshotsFlagCheckBox.checked
    imageThreshold = self.imageThresholdSliderWidget.value
    logic.run(self.inputSelector.currentNode(), self.outputSelector.currentNode(), imageThreshold, enableScreenshotsFlag)

#
# FusionHIFULogic
#

class FusionHIFULogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def hasImageData(self,volumeNode):
    """This is an example logic method that
    returns true if the passed in volume
    node has valid image data
    """
    if not volumeNode:
      logging.debug('hasImageData failed: no volume node')
      return False
    if volumeNode.GetImageData() is None:
      logging.debug('hasImageData failed: no image data in volume node')
      return False
    return True

  def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
    """Validates if the output is not the same as input
    """
    if not inputVolumeNode:
      logging.debug('isValidInputOutputData failed: no input volume node defined')
      return False
    if not outputVolumeNode:
      logging.debug('isValidInputOutputData failed: no output volume node defined')
      return False
    if inputVolumeNode.GetID()==outputVolumeNode.GetID():
      logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
      return False
    return True

  def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
    """
    Run the actual algorithm
    """

    if not self.isValidInputOutputData(inputVolume, outputVolume):
      slicer.util.errorDisplay('Input volume is the same as output volume. Choose a different output volume.')
      return False

    logging.info('Processing started')

    # Compute the thresholded output volume using the Threshold Scalar Volume CLI module
    cliParams = {'InputVolume': inputVolume.GetID(), 'OutputVolume': outputVolume.GetID(), 'ThresholdValue' : imageThreshold, 'ThresholdType' : 'Above'}
    cliNode = slicer.cli.run(slicer.modules.thresholdscalarvolume, None, cliParams, wait_for_completion=True)

    # Capture screenshot
    if enableScreenshots:
      self.takeScreenshot('FusionHIFUTest-Start','MyScreenshot',-1)

    logging.info('Processing completed')

    return True


class FusionHIFUTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_FusionHIFU1()

  def test_FusionHIFU1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import SampleData
    SampleData.downloadFromURL(
      nodeNames='FA',
      fileNames='FA.nrrd',
      uris='http://slicer.kitware.com/midas3/download?items=5767')
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = FusionHIFULogic()
    self.assertIsNotNone( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')
