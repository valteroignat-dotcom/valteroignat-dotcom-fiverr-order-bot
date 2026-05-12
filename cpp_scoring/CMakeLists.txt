cmake_minimum_required(VERSION 3.15)
project(FiverrOrderScoring LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_executable(scoring main.cpp)

# Windows-specific: set console subsystem for Visual Studio
if(MSVC)
    target_compile_options(scoring PRIVATE /W4 /utf-8)
    set_target_properties(scoring PROPERTIES
        VS_DEBUGGER_WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
    )
else()
    target_compile_options(scoring PRIVATE -Wall -Wextra -pedantic)
endif()
