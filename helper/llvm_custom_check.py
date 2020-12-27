import os
import sys
import re
# import gevent
import copy
import time
import shutil
import ccsyspath
import linecache
import platform
import threading
import clang.cindex
import logging.handlers
import logger_factory
import xml.dom.minidom
from time import ctime
from optparse import OptionParser
# from gevent.queue import Queue
from clang.cindex import Config
from clang.cindex import _CXString
from config import *

if platform.system() == "Windows":  # IS_WINDOWS
    slash = '\\'
    Copy_Filter_Keywords = copy.deepcopy(Filter_Keywords)
    Filter_Keywords = []
    for mac_path in Copy_Filter_Keywords:
        Filter_Keywords.append(mac_path.replace('/', '\\'))
    libclang_path = r'C:\Program Files\LLVM\bin\libclang.dll'
    if not os.path.exists(libclang_path):
        raise Exception("Please install clang with libclang.dll")
elif platform.system() == "Darwin":  # IS_MAC
    slash = '/'
    libclang_path = '/Library/Developer/CommandLineTools/usr/lib/libclang.dylib'
    pipe = os.popen('mdfind -name "libclang.dylib"').readlines()
    if not pipe:
        raise Exception("Please install clang with libclang.dylib")
elif platform.system() == "Linux":  # IS_LINUX
    slash = '/'
    libclang_path = '/usr/lib/llvm-7.0/lib/libclang-7.0.so.1'
    if not os.path.exists(libclang_path):
        raise Exception("Please install clang with libclang.so")

if Config.loaded == True:
    pass
else:
    Config.set_library_file(libclang_path)

syspath = ccsyspath.system_include_paths('clang++')
incargs = [b'-I' + inc for inc in syspath]
args = '-x c++'.split() + incargs

parser = OptionParser()
parser.add_option("-s", "--source_dir", action="store", dest="source_dir", help="read input data from source directory")
parser.add_option("-t", "--target_file", action="store", dest="target_file", help="parse data to target file")
(options, _) = parser.parse_args()
INPUT_SOURCE_ORIGIN = []
INPUT_SOURCE_ORIGIN.append(options.source_dir)

_VAR_DECL = []  # record variable offsets
_DECL_REF_EXPR = []  # record variable reference offsets
_NODE_DICT = {}  # record node: domain
_GLOBAL_VAR_COUNT = 0  # records the number of global variables
_BARE_THREAD_COUNT = 0  # records the number of bare thread

doc = xml.dom.minidom.Document()
node_errors = doc.createElement('errors')


def print_run_time(func):
    def wrapper(*args, **kw):
        local_time = time.time()
        func(*args, **kw)
        logging.info('Current function [%s] run time is %.2f' % (func.__name__, time.time() - local_time))

    return wrapper


def _get_token_line(file_item):
    cursor_content_list = []
    cursor_content = ""
    index = clang.cindex.Index.create()
    tu = index.parse(file_item)
    for token in tu.cursor.get_tokens():
        str_token = token.spelling + " "
        cursor_content = cursor_content + str_token
        if token.kind == clang.cindex.TokenKind.PUNCTUATION:
            cursor_content_list.append(cursor_content)
            cursor_content = ""
    return cursor_content_list


def get_text_line(file_item):
    text_line_list = []
    with open(file_item, 'r') as fileReader:
        for line in fileReader:
            text_line_list.append(line.strip('\n'))
    return text_line_list


def get_line_content(file_item, row_nums):
    content_list = []
    for row in row_nums:
        content = linecache.getline(file_item, row)
        content_list.append(content)
    return content_list


def _find_global_vars(analysis_file, node, scope, indent):
    """ Find all global variables """
    global _VAR_DECL, _DECL_REF_EXPR, _NODE_DICT, _GLOBAL_VAR_COUNT

    text = node.spelling or node.displayname
    kind = '|' + str(node.kind)[str(node.kind).index('.') + 1:]
    unit = str(scope + kind).replace(' ', '')
    _NODE_DICT[text] = unit
    if unit.endswith('VAR_DECL'):
        if unit.rindex('VAR_DECL') - unit.rindex('TRANSLATION_UNIT') == 17:  # CASE_1 contains extern cases
            item_line = linecache.getline(analysis_file, node.location.line)
            if text in item_line and 'const' not in item_line and 'void' not in item_line:
                if '(' not in item_line:
                    write_data_to_result(analysis_file, indent, unit, text, 'CASE_1',
                                         node.location.line, node.location.column)
                    if filter_keywords_method(analysis_file, Filter_Keywords):  # filter analysis_file contains keywords
                        gen_global_variable_custom_rule(text, analysis_file, node.location.line)
                        _GLOBAL_VAR_COUNT += 1
                elif '(' in item_line and '=' in item_line:
                    write_data_to_result(analysis_file, indent, unit, text, 'CASE_1',
                                         node.location.line, node.location.column)
                    if filter_keywords_method(analysis_file, Filter_Keywords):
                        gen_global_variable_custom_rule(text, analysis_file, node.location.line)
                        _GLOBAL_VAR_COUNT += 1
        elif 'NAMESPACE' in unit and 'UNEXPOSED_DECL' not in unit and unit.index('VAR_DECL') - unit.index(
                'NAMESPACE') == 10:  # CASE_2
            item_line = linecache.getline(analysis_file, node.location.line)
            if text in item_line and 'const' not in item_line and 'void' not in item_line:
                if '(' not in item_line:
                    write_data_to_result(analysis_file, indent, unit, text, 'CASE_2',
                                         node.location.line, node.location.column)
                    if filter_keywords_method(analysis_file, Filter_Keywords):
                        gen_global_variable_custom_rule(text, analysis_file, node.location.line)
                        _GLOBAL_VAR_COUNT += 1
                elif '(' in item_line and '=' in item_line:
                    write_data_to_result(analysis_file, indent, unit, text, 'CASE_2',
                                         node.location.line, node.location.column)
                    if filter_keywords_method(analysis_file, Filter_Keywords):
                        gen_global_variable_custom_rule(text, analysis_file, node.location.line)
                        _GLOBAL_VAR_COUNT += 1
    for c in node.get_children():
        _find_global_vars(analysis_file, c, scope + '' + kind, indent + 2)


def _find_bare_threads(analysis_file, node, indent):
    """ Find all bare threads """
    global _BARE_THREAD_COUNT

    text = node.spelling or node.displayname
    kind = str(node.kind)[str(node.kind).index('.') + 1:].replace(' ', '')

    ThreadCases = ['thread',  # CASE: std::thread
                   'CreateThread',  # CASE: CreateThread
                   '_beginthread',  # CASE: _beginthread
                   '_beginthreadex',  # CASE: _beginthreadex
                   'pthread_create', ]  # CASE: pthread_create

    for thread_item in ThreadCases:
        if kind == 'CALL_EXPR' and text == thread_item.replace(' ', ''):
            write_data_to_result(analysis_file, indent, '_', text, '_',
                                 node.location.line, node.location.column)
            if filter_keywords_method(analysis_file, Filter_Keywords):
                gen_bare_thread_custom_rule(text, analysis_file, node.location.line)
                _BARE_THREAD_COUNT += 1
    for c in node.get_children():
        _find_bare_threads(analysis_file, c, indent + 2)


def _find_typerefs(node, typename):
    """ Find all references to the type named 'typename'"""
    if node.kind.is_reference():
        ref_node = clang.cindex.Cursor_ref(node)
        if ref_node.spelling == typename:
            print 'Found %s [line=%s, col=%s]' % (
                typename, node.location.line, node.location.column)
    for c in node.get_children():
        _find_typerefs(c, typename)


def gen_custom_rule_pretreatment():
    root = doc.createElement('results')
    root.setAttribute('version', '2')
    doc.appendChild(root)
    node_cppcheck = doc.createElement('cppcheck')
    node_cppcheck.setAttribute('version', "1.87")
    root.appendChild(node_cppcheck)
    root.appendChild(node_errors)


def gen_global_variable_custom_rule(global_variable_name, analysis_file, global_variable_line):
    node_error = doc.createElement('error')
    node_error.setAttribute('id', 'foundGlobalVariable')
    node_error.setAttribute('severity', 'style')
    node_error.setAttribute('msg', 'Global variable [%s] is not allowed in the project' % global_variable_name)
    node_error.setAttribute('verbose', 'Global variable [%s] is not allowed in the project' % global_variable_name)
    node_error.setAttribute('cwe', 'Placeholder')
    node_errors.appendChild(node_error)
    node_location = doc.createElement('location')
    node_location.setAttribute('file', analysis_file)
    node_location.setAttribute('line',
                               str(global_variable_line))  # Note that here should pass in a str instead of a integer
    node_location.setAttribute('info', "The variable is of a global type")
    node_error.appendChild(node_location)


def gen_bare_thread_custom_rule(bare_thread_name, analysis_file, bare_thread_line):
    node_error = doc.createElement('error')
    node_error.setAttribute('id', 'foundBareThread')
    node_error.setAttribute('severity', 'style')
    node_error.setAttribute('msg', 'Bare thread [%s] is not allowed in the project' % bare_thread_name)
    node_error.setAttribute('verbose', 'Bare thread [%s] is not allowed in the project' % bare_thread_name)
    node_error.setAttribute('cwe', 'Placeholder')
    node_errors.appendChild(node_error)
    node_location = doc.createElement('location')
    node_location.setAttribute('file', analysis_file)
    node_location.setAttribute('line',
                               str(bare_thread_line))  # Note that here should pass in a str instead of a integer
    node_location.setAttribute('info', "The thread is of a bare type")
    node_error.appendChild(node_location)


def write_rules_to_xml_result(save_file=Custom_Rules_Report_Xml):
    with open(save_file, 'a') as fileWriter:
        doc.writexml(fileWriter, addindent='\t', newl='\n', encoding="UTF-8")


def write_data_to_result(analysis_file, indent, global_variable_scope, node_displayname, case_type,
                         node_location_line, node_location_column, save_file=Custom_Check_Result_Txt):
    try:
        with open(save_file, 'a') as fileWriter:
            data_record = '{file_name}, ' \
                          'indent:{indent}, ' \
                          'scope:{global_variable_scope}, ' \
                          'name:{node_displayname}, ' \
                          'type:{case_type}, ' \
                          '{node_location_line}-{node_location_column}\n'. \
                format(file_name=analysis_file, \
                       indent=indent, \
                       global_variable_scope=global_variable_scope, \
                       node_displayname=node_displayname, \
                       case_type=case_type, \
                       node_location_line=node_location_line, \
                       node_location_column=node_location_column)
            fileWriter.write(data_record)
    except IOError:
        print 'IOError: write data to result failed !'
    finally:
        fileWriter.close()


def filter_keywords_method(analysis_file, filter_list=Filter_Keywords):
    for item in filter_list:
        if item in analysis_file:
            return False
    return True


def check_str_contain_keywords(analysis_file, key_word, filter_list):
    if set(analysis_file.split(key_word)).intersection(set(filter_list)):
        return False
    return True


def get_all_filename(dir_path):
    filename_list = []
    for root, dirs, files in os.walk(dir_path):
        for i in files:
            filename_list.append(root + slash + i)
    logging.info(('Under this dir -- {dir}: There are {num} files ').format(dir=dir_path, num=len(filename_list)))
    return filename_list


def filter_file_by_suffixation(dir_path, *keySuffixation):
    filename_list = get_all_filename(dir_path)
    file_contain_suffixation = []
    for file in filename_list:
        if os.path.splitext(file)[1] in tuple(keySuffixation):
            file_contain_suffixation.append(file)
    logging.info(('Under this dir -- {dir}: There are {num} files, '
                  'suffix called {key}').format(dir=dir_path, num=len(file_contain_suffixation), key=keySuffixation))
    return file_contain_suffixation


def copy_single_file(source_file, target_dir):
    if not os.path.exists(source_file):
        raise Exception('No such source file !!!')
    shutil.copy(source_file, target_dir)


def remove_keywords_line(file, keywords='#include'):
    if os.path.exists(file):
        with open(file, 'r') as fileReader:
            lines = fileReader.readlines()
        with open(file, 'w') as fileWriter:
            for line in lines:
                if keywords not in line:
                    fileWriter.write(line)


def remove_duplicate_line(file):
    if os.path.exists(file):
        with open(file, 'r') as fileReader:
            all_lines = fileReader.readlines()
    with open(file, 'w') as fileWriter:
        hash_dict = {}
        for line in all_lines:
            if not hash_dict.has_key(line):
                hash_dict[line] = 1
                fileWriter.write(line)


def post_processing(file):
    for item in Filter_Keywords:
        remove_keywords_line(file, keywords=item)


def empty_last_result(file_list):
    for file in file_list:
        if os.path.exists(file):
            os.remove(file)


def check_argv():
    if len(sys.argv) != 2:
        print("Usage: llvm_custom_check.py [header file name]")
        sys.exit()


def run_thread(suffixation):
    INPUT_SOURCE_ORIGIN = []
    INPUT_SOURCE_ORIGIN.append(options.source_dir)
    for path_item in INPUT_SOURCE_ORIGIN:
        for file_item in filter_file_by_suffixation(path_item, suffixation):
            index = clang.cindex.Index.create()
            tu = index.parse(file_item)
            node = tu.cursor
            _find_global_vars(file_item, tu.cursor, '|' + str(node.kind)[str(node.kind).index('.') + 1:], 0)


@print_run_time
def task_thread():
    print "Start at: %s" % ctime()
    start = time.time()
    empty_last_result(Custom_Check_Result_Txt)
    threads = []
    for suffixation in Suffixiation_List:
        t = threading.Thread(target=run_thread, args=(suffixation,))
        threads.append(t)
    for thread in threads:
        thread.setDaemon(True)
        thread.start()
    thread.join()
    end = time.time()
    print str(end - start)


@print_run_time
def global_check_process():
    logging.info("Global Check Starts...")
    for path_item in INPUT_SOURCE_ORIGIN:
        for file_item in filter_file_by_suffixation(path_item, '.c', '.cxx', '.cc', '.c++', '.cpp'):
            remove_keywords_line(file_item)
            index = clang.cindex.Index.create()
            tu = index.parse(file_item)
            root = tu.cursor
            _find_global_vars(file_item, root, '|' + str(root.kind)[str(root.kind).index('.') + 1:], 0)
    logging.info("There are [%s] global variables in this scan" % _GLOBAL_VAR_COUNT)


@print_run_time
def forbid_bare_thread_process():
    logging.info("Bare Thread Check Starts...")
    for path_item in INPUT_SOURCE_ORIGIN:
        for file_item in filter_file_by_suffixation(path_item, '.c', '.cxx', '.cc', '.c++', '.cpp'):
            index = clang.cindex.Index.create()
            tu = index.parse(file_item, args=args)
            root = tu.cursor
            _find_bare_threads(file_item, root, 0)
    logging.info("There are [%s] bare threads in this scan" % _BARE_THREAD_COUNT)


def main():
    logging.info("Custom Check Start at: %s" % ctime())
    start = time.time()
    empty_last_result([Custom_Check_Result_Txt, Custom_Rules_Report_Xml])
    gen_custom_rule_pretreatment()
    forbid_bare_thread_process()
    global_check_process()
    write_rules_to_xml_result()
    post_processing(Custom_Check_Result_Txt)  # remove the items by sonar.exclusions in sonar-project.properties
    copy_single_file(Custom_Rules_Report_Xml, Work_Path)
    end = time.time()
    logging.info("Running Time of Custom Check is %.2f" % (end - start))


if __name__ == '__main__':
    main()
