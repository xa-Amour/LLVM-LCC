import os

pipe = os.popen('clang -cc1 -ast-dump .\main.cpp')
text = pipe.read()
with open('clang_parser.txt', 'w') as fileWriter:
    for data in text:
        fileWriter.write(data)
print 'Clang Parser Done!'
