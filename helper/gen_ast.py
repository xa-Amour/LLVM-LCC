import sys

import clang.cindex

_VAR_DECL = []  # record variable offsets
_DECL_REF_EXPR = []  # record variable reference offsets


def gen_ast(node, indent):
    global _VAR_DECL, _DECL_REF_EXPR
    text = node.spelling or node.displayname
    kind = '|' + str(node.kind)[str(node.kind).index('.') + 1:]
    data = ' ' * indent + '{} {} {} {} '.format(kind, text, node.location.line, node.location.column)
    print str(indent) + ' ' * indent + '{} {} {} {} '.format(kind, text, node.location.line, node.location.column)
    if node.kind == clang.cindex.CursorKind.VAR_DECL or node.displayname == 'VAR_DECL':
        if indent == 2:
            pass
        else:
            pass
    with open('ast-struct.txt', 'a') as fileWriter:
        fileWriter.write(str(indent) + str(data) + '\n')
    for i in node.get_children():
        gen_ast(i, indent + 2)


def gvar_check_entrance(node, indent):
    text = node.spelling or node.displayname
    kind = '|' + str(node.kind)[str(node.kind).index('.') + 1:]
    data = ' ' * indent + '{} {} {} {} '.format(kind, text, node.location.line, node.location.column)
    print ' ' * indent, '{} {} {} {} '.format(kind, text, node.location.line, node.location.column)
    if node.kind == clang.cindex.CursorKind.VAR_DECL or node.displayname == 'VAR_DECL':
        _VAR_DECL.append(indent)
    elif node.kind == clang.cindex.CursorKind.DECL_REF_EXPR or node.displayname == 'DECL_REF_EXPR':
        _DECL_REF_EXPR.append(indent)
    if not _VAR_DECL:  # Case 1: if there is no variable declaration, there is no global variable
        pass
    else:
        min_index_var_decl = min(_VAR_DECL)
        if len(
                _DECL_REF_EXPR) > 0:  # Case 2: variable declaration exists and variable declaration level < reference declaration level
            min_index_decl_ref_expr = min(_DECL_REF_EXPR)
            if min_index_var_decl < min_index_decl_ref_expr:
                pass
        else:  # Case 3: there are variable declarations and no reference declarations
            pass
    with open('ast-struct.txt', 'a') as fileWriter:
        fileWriter.write(str(indent) + str(data) + '\n')
    for i in node.get_children():
        gen_ast(i, indent + 2)  # The AST shows offsets


def check_argv():
    if len(sys.argv) != 2:
        print("Usage: gen_ast.py [header file name]")
        sys.exit()


def main():
    check_argv()
    index = clang.cindex.Index.create()
    tu = index.parse(sys.argv[1])
    gen_ast(tu.cursor, 0)
