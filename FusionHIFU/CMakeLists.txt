#-----------------------------------------------------------------------------
set(MODULE_NAME FusionHIFU)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  FusionHIFUWizard/__init__.py
  FusionHIFUWizard/DefineROIStep.py
  FusionHIFUWizard/EndStep.py
  FusionHIFUWizard/Helper.py
  FusionHIFUWizard/LoadDataStep.py
  FusionHIFUWizard/RegistrationStep.py
  FusionHIFUWizard/ReviewAndMeasurementsStep.py
  FusionHIFUWizard/TreatmentEvaluationStep.py
  FusionHIFUWizard/TreatmentPlanSettingStep.py
  FusionHIFUWizard/TreatmentStep.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_GENERIC_TESTS
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)

  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(SCRIPT ${MODULE_NAME}.py)

  # Additional build-time testing
  add_subdirectory(Testing)
endif()
