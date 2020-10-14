import clang.cindex
import ccsyspath
from llvm_custom_check import *

_BARE_THREAD_COUNT = 0  # records the number of bare thread


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
            _BARE_THREAD_COUNT += 1
            write_data_to_result(analysis_file, indent, '_', text, '_',
                                 node.location.line, node.location.column)
            print str(indent) + ' ' * indent + '{} {} {} {}'.format(kind, text, node.location.line,
                                                                    node.location.column)

    for c in node.get_children():
        _find_bare_threads(analysis_file, c, indent + 2)


def main():
    syspath = ccsyspath.system_include_paths('clang++')
    incargs = [b'-I' + inc for inc in syspath]
    args = '-x c++'.split() + incargs
    source_code = [r'placeholder']
    for path_item in source_code:
        for file_item in filter_file_by_suffixation(path_item, '.c', '.cxx', '.cc', '.c++', '.cpp'):
            index = clang.cindex.Index.create()
            tu = index.parse(file_item, args=args)
            root = tu.cursor
            _find_bare_threads(file_item, root, 0)


if __name__ == '__main__':
    main()
