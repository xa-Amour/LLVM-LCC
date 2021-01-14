# LCC
LLVM Customized Check

## About
LLVM Customized Check is a set of customized detection collections of C/C++ source code by LLVM (Low Level Virtual Machine). Its objectives include, but are not limited to the following:
1. global variable check
2. nake thread detection
3. memory leak analyser
4. deadlock detection
5. modules separation

Global variable check and nake thread detection are now completed in this demo and not involve any business logic. Deadlock detection demo as https://github.com/xa-Amour/DLD. Nake thread detection analyses the following five types of threads:
1. std::thread
2. CreateThread
3. _beginthread
4. _beginthreadex
5. pthread_create

## Keywords
* Python2.7
* LLVM (Low Level Virtual Machine)
* clang
* libclang

## Usage
Two Patterns:
1. [Dependency arguments from syspath to parse code]:
* python ./llvm_customized_check.py --source=source_folder --target=target_folder
2. [Dependency arguments from compile commands json to parse code]:
* python ./llvm_customized_check.py --source=source_folder --compile_db=compile_commands.json --target=target_folder
