#!/usr/bin/env python
#
'''
# LCC
LLVM Customized Check

## About
    LLVM Customized Check is a set of custom detection collections of C/C++ source code by LLVM (Low Level Virtual Machine).
    Its objectives include, but are not limited to the following:
        1. global variable check
        2. nake thread detection
        3. memory leak analyser
        4. deadlock detection
        5. modules separation

    Global variable check and nake thread detection are now completed in this demo and not involve business logic.
    Deadlock detection demo as https://github.com/xa-Amour/DLD.
    Nake thread detection analyses the following five types of threads:
        1. std::thread
        2. CreateThread
        3. _beginthread
        4. _beginthreadex
        5. pthread_create

## Keywords
    * Python2.7
    * LLVM
    * clang
    * libclang

## Usage
   Two Patterns:
    1. [Dependency arguments to parse code from syspath]:
            python ./llvm_customized_check.py --source=source_folder --target=target_folder
    2. [Dependency arguments to parse code from compile commands json]:
            python ./llvm_customized_check.py --source=source_folder --compile_db=compile_commands.json --target=target_folder
'''

import argparse
import copy
import linecache
import logging.handlers
import os
import platform
import sys
import time
import xml.dom.minidom

import clang.cindex
from clang.cindex import Config

CONTEXT = {}
GLOBAL_VAR_COUNT = 0
NAKE_THREAD_COUNT = 0
DOC = xml.dom.minidom.Document()
NODE_ERRORS = DOC.createElement('errors')

CUSTOMIZED_CHECK = {
    'customized_rules_report': 'customized_rules-report.xml',
    'global_check_result': 'global_check-result',
    'customized_log': 'llvm_customized_check.log',
    'suffix': ['.c', '.cxx', '.cc', '.c++', '.cpp'],
    'ignore_file': [r'placeholder']
}

logger = logging.getLogger()
logging.basicConfig(format='%(asctime)s - %(pathname)s[line:%(lineno)d] - %(levelname)s: %(message)s',
                    level=logging.INFO)
fmt = logging.Formatter(
    '%(asctime)s %(pathname)s %(filename)s %(funcName)s %(lineno)s \
    %(levelname)s - %(message)s', '%Y-%m-%d %H:%M:%S')
rht = logging.handlers.TimedRotatingFileHandler(CUSTOMIZED_CHECK['customized_log'])
rht.setFormatter(fmt)
logger.addHandler(rht)

if platform.system() == 'Windows':  # IS_WINDOWS
    SLASH, libclang_path = '\\', r'C:\Program Files\LLVM\bin\libclang.dll'
    CUSTOMIZED_CHECK.update(
        {'ignore_file': [igo.replace('/', '\\') for igo in copy.deepcopy(CUSTOMIZED_CHECK['ignore_file'])]})
    if not os.path.exists(libclang_path):
        raise Exception('Please install clang with libclang.dll')
elif platform.system() == 'Darwin':  # IS_MAC
    SLASH, libclang_path = '/', '/Library/Developer/CommandLineTools/usr/lib/libclang.dylib'
    if not os.popen('mdfind -name "libclang.dylib"').readlines():
        raise Exception('Please install clang with libclang.dylib')
elif platform.system() == 'Linux':  # IS_LINUX
    SLASH, libclang_path = '/', '/usr/lib/llvm-7.0/lib/libclang-7.0.so.1'
    if not os.path.exists(libclang_path):
        raise Exception('Please install clang with libclang.so')

if Config.loaded == True:
    pass
else:
    Config.set_library_file(libclang_path)


def main(argv):
    if not argv or len(argv) < 1:
        print '''Two Patterns of Usage:
    1. [Dependency arguments to parse code from syspath]:
            python ./llvm_customized_check.py --source=source_folder --target=target_folder
    2. [Dependency arguments to parse code from compile commands json]:
            python ./llvm_customized_check.py --source=source_folder --compile_db=compile_commands.json --target=target_folder'''
        sys.exit()

    parser = argparse.ArgumentParser()
    parser.add_argument('--source', metavar='source', default='',
                        help='root directory of source code')
    parser.add_argument('--compile_db', metavar='compile_db', default='',
                        help='file of compile commands json')
    parser.add_argument('--target', metavar='target', default='',
                        help='target folder of analysis result')
    args = parser.parse_args()

    # Save the config into context
    CONTEXT['source'] = args.source
    CONTEXT['compile_db'] = args.compile_db
    CONTEXT['target'] = args.target
    fail = handle({(args.source)})
    exit(1 if fail else 0)


def handle(src):
    clean_workspace(CUSTOMIZED_CHECK['global_check_result'], CUSTOMIZED_CHECK['customized_rules_report'])

    init_customized_report(DOC, NODE_ERRORS)

    checker = {
        'Nake Thread Detection Process': detect_nake_thread_process,
        'Global Variable Detection Process': detect_global_var_process
    }

    for check, detect in checker.items():
        logging.info('[INIT]: {0} Init'.format(check))
        detect(src)

    with open(CUSTOMIZED_CHECK['customized_rules_report'], 'a') as fa:
        DOC.writexml(fa, addindent='\t', newl='\n', encoding='UTF-8')

    _ = [clear_spec_row(CUSTOMIZED_CHECK['global_check_result'], spec=elec) for elec in
         CUSTOMIZED_CHECK['ignore_file']]

    return False


def count_time(func):
    def wrapper(*args, **kwargs):
        cur = time.time()
        res = func(*args, **kwargs)
        logging.info('--> RUN TIME: <{0}> : {1}\n'.format(func.__name__, round(time.time() - cur, 4)))
        return res

    return wrapper


@count_time
def detect_global_var_process(src):
    index = clang.cindex.Index.create()
    for path in src:
        for anls in filter_by_suffix(path, CUSTOMIZED_CHECK['suffix']):
            clear_spec_row(anls)
            root = index.parse(anls, args=DepArgsFactory().getArgs(anls)).cursor
            detect_global_var(anls, root, '|' + str(root.kind)[str(root.kind).index('.') + 1:], 0)
    logging.info('[RESULT]: Found [{0}] global variable(s) in check.'.format(GLOBAL_VAR_COUNT))


@count_time
def detect_nake_thread_process(src):
    index = clang.cindex.Index.create()
    for path in src:
        for anls in filter_by_suffix(path, CUSTOMIZED_CHECK['suffix']):
            root = index.parse(anls, args=DepArgsFactory().getArgs(anls)).cursor
            detect_nake_thread(anls, root, 0)
    logging.info('[RESULT]: Found [{0}] nake thread(s) in scan.'.format(NAKE_THREAD_COUNT))


def detect_global_var(anls, node, scope, indent):
    global GLOBAL_VAR_COUNT
    text = node.spelling or node.displayname
    kind = '|' + str(node.kind)[str(node.kind).index('.') + 1:]
    unit = str(scope + kind).replace(' ', '')
    if unit.endswith('VAR_DECL'):
        if unit.rindex('VAR_DECL') - unit.rindex('TRANSLATION_UNIT') == 17:  # CASE_1: contains extern cases
            line = linecache.getline(anls, node.location.line)
            if text in line and 'const' not in line and 'void' not in line:
                if '(' not in line:
                    update_gv_to_report(anls, indent, unit, text, 'CASE_1',
                                        node.location.line, node.location.column)
                    if if_analyse(anls, CUSTOMIZED_CHECK['ignore_file']):
                        update_gv_detct_rule(text, anls, node.location.line)
                        GLOBAL_VAR_COUNT += 1
                elif '(' in line and '=' in line:
                    update_gv_to_report(anls, indent, unit, text, 'CASE_1',
                                        node.location.line, node.location.column)
                    if if_analyse(anls, CUSTOMIZED_CHECK['ignore_file']):
                        update_gv_detct_rule(text, anls, node.location.line)
                        GLOBAL_VAR_COUNT += 1
        elif 'NAMESPACE' in unit and 'UNEXPOSED_DECL' not in unit and unit.index('VAR_DECL') - unit.index(
                'NAMESPACE') == 10:  # CASE_2
            line = linecache.getline(anls, node.location.line)
            if text in line and 'const' not in line and 'void' not in line:
                if '(' not in line:
                    update_gv_to_report(anls, indent, unit, text, 'CASE_2',
                                        node.location.line, node.location.column)
                    if if_analyse(anls, CUSTOMIZED_CHECK['ignore_file']):
                        update_gv_detct_rule(text, anls, node.location.line)
                        GLOBAL_VAR_COUNT += 1
                elif '(' in line and '=' in line:
                    update_gv_to_report(anls, indent, unit, text, 'CASE_2',
                                        node.location.line, node.location.column)
                    if if_analyse(anls, CUSTOMIZED_CHECK['ignore_file']):
                        update_gv_detct_rule(text, anls, node.location.line)
                        GLOBAL_VAR_COUNT += 1
    for child in node.get_children():
        detect_global_var(anls, child, scope + '' + kind, indent + 2)


def detect_nake_thread(anls, node, indent):
    global NAKE_THREAD_COUNT
    text = node.spelling or node.displayname
    kind = str(node.kind)[str(node.kind).index('.') + 1:].replace(' ', '')

    ThreadCases = ['thread',  # CASE: std::thread
                   'CreateThread',  # CASE: CreateThread
                   '_beginthread',  # CASE: _beginthread
                   '_beginthreadex',  # CASE: _beginthreadex
                   'pthread_create', ]  # CASE: pthread_create

    for thread in ThreadCases:
        if kind == 'CALL_EXPR' and text == thread.replace(' ', ''):
            update_gv_to_report(anls, indent, '_', text, '_', node.location.line, node.location.column)
            if if_analyse(anls, CUSTOMIZED_CHECK['ignore_file']):
                upadte_nthd_detct_rule(text, anls, node.location.line)
                NAKE_THREAD_COUNT += 1
    for child in node.get_children():
        detect_nake_thread(anls, child, indent + 2)


def detect_typerefs(node, typename):
    if node.kind.is_reference():
        ref_node = clang.cindex.Cursor_ref(node)
        if ref_node.spelling == typename:
            print 'Found %s [line=%s, col=%s]' % (
                typename, node.location.line, node.location.column)
    for child in node.get_children():
        detect_typerefs(child, typename)


def filter_by_suffix(folder, suffs):
    def _all_path(folder):
        path = [root + SLASH + file for root, subdir,
                                        files in os.walk(folder) for file in files]
        logging.info('[INFO]: Found {num} file(s).'.format(num=len(path)))
        return path

    filter = [file for file in _all_path(folder) if os.path.splitext(file)[1] in tuple(suff for suff in suffs)]
    logging.info(('[INFO]: Found {num} target file(s).').format(num=len(filter)))

    return filter


def clear_spec_row(file, spec='#include'):
    with open(file, 'r+') as fr:
        new_f = fr.readlines()
        fr.seek(0)
        for line in new_f:
            if spec not in line:
                fr.write(line)
        fr.truncate()


def clean_workspace(*files):
    _ = [os.remove(file) for file in files if os.path.exists(file)]


def if_analyse(anls, iggs):
    return True if all([False for igg in iggs if igg in anls]) else False


def update_gv_to_report(anls, indent, scope, node_dpn, case_type,
                        node_loc_line, node_loc_col, save_file=CUSTOMIZED_CHECK['global_check_result']):
    with open(save_file, 'a') as fw:
        data_record = '{anls}\n  [Details]: indent:{indent}, scope:{scope}, name:{node_dpn}, type:{case_type}, {node_loc_line}-{node_loc_col}\n\n'.format(
            anls=anls, indent=indent, scope=scope, node_dpn=node_dpn, case_type=case_type, node_loc_line=node_loc_line,
            node_loc_col=node_loc_col)
        fw.write(data_record)


def init_customized_report(doc, node_errors):
    root = doc.createElement('results')
    root.setAttribute('version', '2')
    doc.appendChild(root)
    node_cppcheck = doc.createElement('cppcheck')
    node_cppcheck.setAttribute('version', '1.87')
    root.appendChild(node_cppcheck)
    root.appendChild(node_errors)
    CUSTOMIZED_CHECK.update(
        {'customized_rules_report': os.path.join(CONTEXT['target'], CUSTOMIZED_CHECK['customized_rules_report'])})


def update_gv_detct_rule(gv, anls, gv_line):
    node_error = DOC.createElement('error')
    node_error.setAttribute('id', 'foundGlobalVariable')
    node_error.setAttribute('severity', 'style')
    node_error.setAttribute('msg', 'Not allow global variable [%s]' % gv)
    node_error.setAttribute('verbose',
                            'Global variable [%s] is not allowed in our project. Please ask code reviewer for datails.' % gv)
    node_error.setAttribute('cwe', 'Company')
    NODE_ERRORS.appendChild(node_error)
    node_location = DOC.createElement('location')
    node_location.setAttribute('file', anls)
    node_location.setAttribute('line',
                               str(gv_line))  # Note: here should pass in a string instead of a integer
    node_location.setAttribute('info', 'This is a global variable')
    node_error.appendChild(node_location)


def upadte_nthd_detct_rule(nthd, anls, nthd_line):
    node_error = DOC.createElement('error')
    node_error.setAttribute('id', 'foundNakeThread')
    node_error.setAttribute('severity', 'style')
    node_error.setAttribute('msg', 'Not allow nake thread [%s]' % nthd)
    node_error.setAttribute('verbose',
                            'Nake thread [%s] is not allowed in our project. Please ask code reviewer for datails' % nthd)
    node_error.setAttribute('cwe', 'Company')
    NODE_ERRORS.appendChild(node_error)
    node_location = DOC.createElement('location')
    node_location.setAttribute('file', anls)
    node_location.setAttribute('line',
                               str(nthd_line))
    node_location.setAttribute('info', 'This is a nake thread')
    node_error.appendChild(node_location)


class DepArgsBySys(object):

    def get_args(self):
        import ccsyspath
        syspath = ccsyspath.system_include_paths('clang++')
        incargs = [b'-I' + inc for inc in syspath]
        args = '-x c++'.split() + incargs
        logging.debug(
            '[INFO]: Count of dependency args by syspath: {0}.'.format(len(args)))
        return args


class DepArgsByCdb(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, compile_db, src_file):
        self.args = []
        self.args_log = 'argsByCdb.log'
        self.compile_db = compile_db  # Directory of compile_commands.json
        self.src_file = src_file
        self.compdb = clang.cindex.CompilationDatabase.fromDirectory(
            compile_db)

    def __handle_dep_args(self):
        try:
            args = list(iter(self.compdb.getCompileCommands(self.src_file)).next(
            ).arguments)  # Source file should correspond to the compile_commands.json
            args.remove('clang-cl.exe')
            args_lst = [argument for argument in args if argument.startswith(
                '-D') or argument.startswith('-I')]
            os.chdir(self.compile_db)
        except Exception as e:
            logging.warning('===================================================================')
            logging.warning('[DepArgsByCdb]: Dependency args failure handled')
            logging.warning('===================================================================')
            raise

        return args_lst

    def get_args(self):
        self.args = self.__handle_dep_args()
        with open(self.args_log, 'w') as fw:
            for arg in self.args:
                fw.write(arg + '\n')
        logging.debug(
            '[INFO]: Count of dependency args by compile commands json: {0}.'.format(len(self.args)))

        return self.args


class DepArgsFactory(object):

    @staticmethod
    def getArgs(anls):
        return DepArgsByCdb(os.path.dirname(CONTEXT['compile_db']), anls).get_args(
        ) if CONTEXT['compile_db'] else DepArgsBySys().get_args()


if __name__ == '__main__':
    main(sys.argv[1:])
