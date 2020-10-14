import sys

import clang.cindex

_NODE_DICT = {}


def visitor(analysis_file, node, scope, indent):
    global _NODE_DICT
    text = node.spelling or node.displayname
    kind = '|' + str(node.kind)[str(node.kind).index('.') + 1:]
    unit = str(scope + kind)
    _NODE_DICT[text] = unit
    print str(indent) + ' ' * indent + '{} {} {} {} '.format(scope, kind, node.location.line, node.location.column)
    for i in node.get_children():
        visitor(analysis_file, i, scope + '' + kind, indent + 2)


def check_argv():
    if len(sys.argv) != 2:
        print("Usage: gen_scope_struct.py [header file name]")
        sys.exit()


def main():
    check_argv()
    index = clang.cindex.Index.create()
    tu = index.parse(sys.argv[1])
    node = tu.cursor
    visitor(sys.argv[1], tu.cursor, '|' + str(node.kind)[str(node.kind).index('.') + 1:], 0)
