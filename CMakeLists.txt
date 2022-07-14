cmake_minimum_required(VERSION 3.5)

find_package(Slicer COMPONENTS ConfigurePrerequisites)

project(FusionHIFU)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "http://slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/FusionHIFU")
set(EXTENSION_CATEGORY "IGT")
set(EXTENSION_CONTRIBUTORS "XU Kailiang (Fudan University)")
set(EXTENSION_DESCRIPTION "This is an extention of CT/MRI image guided HIFU(High Intensity Focused Ultrasound) therapy.")
set(EXTENSION_ICONURL "http://www.example.com/Slicer/Extensions/FusionHIFU.png")
set(EXTENSION_SCREENSHOTURLS "http://www.example.com/Slicer/Extensions/FusionHIFU/Screenshots/1.png")
set(EXTENSION_DEPENDS "NA") # Specified as a space separated string, a list or 'NA' if any

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(FusionHIFU)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
