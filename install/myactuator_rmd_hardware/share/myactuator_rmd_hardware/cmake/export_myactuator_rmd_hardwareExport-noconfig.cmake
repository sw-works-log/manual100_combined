#----------------------------------------------------------------
# Generated CMake target import file.
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "myactuator_rmd_hardware::myactuator_rmd_hardware" for configuration ""
set_property(TARGET myactuator_rmd_hardware::myactuator_rmd_hardware APPEND PROPERTY IMPORTED_CONFIGURATIONS NOCONFIG)
set_target_properties(myactuator_rmd_hardware::myactuator_rmd_hardware PROPERTIES
  IMPORTED_LOCATION_NOCONFIG "${_IMPORT_PREFIX}/lib/libmyactuator_rmd_hardware.so"
  IMPORTED_SONAME_NOCONFIG "libmyactuator_rmd_hardware.so"
  )

list(APPEND _IMPORT_CHECK_TARGETS myactuator_rmd_hardware::myactuator_rmd_hardware )
list(APPEND _IMPORT_CHECK_FILES_FOR_myactuator_rmd_hardware::myactuator_rmd_hardware "${_IMPORT_PREFIX}/lib/libmyactuator_rmd_hardware.so" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
