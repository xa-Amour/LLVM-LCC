import xml.dom.minidom

doc = xml.dom.minidom.Document()
node_errors = doc.createElement('errors')


def gen_custom_rule_pretreatment():
    root = doc.createElement('results')
    root.setAttribute('version', '2')
    doc.appendChild(root)
    node_cppcheck = doc.createElement('cppcheck')
    node_cppcheck.setAttribute('version', "1.87")
    root.appendChild(node_cppcheck)
    root.appendChild(node_errors)


def gen_custom_rule(global_variable_name, analysis_file, global_variable_line):
    node_error = doc.createElement('error')
    node_error.setAttribute('id', 'foundGlobalVariable')
    node_error.setAttribute('severity', 'style')
    node_error.setAttribute('msg', 'The variable [%s] is of a global type' % global_variable_name)
    node_error.setAttribute('verbose', 'The variable [%s] is of a global type' % global_variable_name)
    node_error.setAttribute('cwe', 'undefined')
    node_errors.appendChild(node_error)
    node_location = doc.createElement('location')
    node_location.setAttribute('file0', analysis_file)
    node_location.setAttribute('file', analysis_file)
    node_location.setAttribute('line', str(global_variable_line))
    node_location.setAttribute('info', "The variable is of a global type")
    node_error.appendChild(node_location)


def write_rules_to_xml_result(save_file='custom_rules-report.xml'):
    with open(save_file, 'a') as fileWriter:
        doc.writexml(fileWriter, addindent='\t', newl='\n', encoding="UTF-8")
