from __future__ import print_function

import json
import sys
import re

from queue import Queue
import os

from pycparser import parse_file, c_ast
from pycparser.plyparser import Coord


RE_CHILD_ARRAY = re.compile(r'(.*)\[(.*)\]')
RE_INTERNAL_ATTR = re.compile('__.*__')


class SimplifiedAstNode:
    def __init__(self, _type, _name = None):
        self.type = _type
        self.name = _name # Only has a name if node_type is FuncCall
        self.calls = [] # Only has calls if node_type is if-else and FuncCalls are in condition blocks
        self.children = []
        self.children_json = []

class CJsonError(Exception):
    pass


def memodict(fn):
    """ Fast memoization decorator for a function taking a single argument """
    class memodict(dict):
        def __missing__(self, key):
            ret = self[key] = fn(key)
            return ret
    return memodict().__getitem__


@memodict
def child_attrs_of(klass):
    """
    Given a Node class, get a set of child attrs.
    Memoized to avoid highly repetitive string manipulation
    """
    non_child_attrs = set(klass.attr_names)
    all_attrs = set([i for i in klass.__slots__ if not RE_INTERNAL_ATTR.match(i)])
    return all_attrs - non_child_attrs


def to_dict(node, level = 0):
    """ Recursively convert an ast into dict representation. """
    klass = node.__class__
    
    result = {}
    # Metadata
    result['_nodetype'] = klass.__name__
    # Local node attributes
    for attr in klass.attr_names:
        result[attr] = getattr(node, attr)
    # Coord object
    if node.coord:
        result['coord'] = str(node.coord)
    else:
        result['coord'] = None

    # Child attributes
    #print(node.__class__, len(node.children()))
    for child_name, child in node.children():
        # Child strings are either simple (e.g. 'value') or arrays (e.g. 'block_items[1]')
        # print(child_name, level+1)
        match = RE_CHILD_ARRAY.match(child_name)
        if match:
            array_name, array_index = match.groups()
            array_index = int(array_index)
            # arrays come in order, so we verify and append.
            result[array_name] = result.get(array_name, [])
            if array_index != len(result[array_name]):
                raise CJsonError('Internal ast error. Array {} out of order. '
                    'Expected index {}, got {}'.format(
                    array_name, len(result[array_name]), array_index))
            result[array_name].append(to_dict(child, level+1))
        else:
            result[child_name] = to_dict(child, level+1)

    # Any child attributes that were missing need "None" values in the json.
    for child_attr in child_attrs_of(klass):
        if child_attr not in result:
            result[child_attr] = None

    return result


def to_json(node, **kwargs):
    """ Convert ast node to json string """
    return json.dumps(to_dict(node), **kwargs)


def file_to_dict(filename):
    """ Load C file into dict representation of ast """
    ast = parse_file(filename, use_cpp=True)
    return to_dict(ast)


def file_to_json(filename, **kwargs):
    """ Load C file into json string representation of ast """
    ast = parse_file(filename, use_cpp=True)
    return to_json(ast, **kwargs)


def _parse_coord(coord_str):
    """ Parse coord string (file:line[:column]) into Coord object. """
    if coord_str is None:
        return None

    vals = coord_str.split(':')
    vals.extend([None] * 3)
    filename, line, column = vals[:3]
    return Coord(filename, line, column)


def _convert_to_obj(value):
    """
    Convert an object in the dict representation into an object.
    Note: Mutually recursive with from_dict.
    """
    value_type = type(value)
    if value_type == dict:
        return from_dict(value)
    elif value_type == list:
        return [_convert_to_obj(item) for item in value]
    else:
        # String
        return value


def from_dict(node_dict):
    """ Recursively build an ast from dict representation """
    class_name = node_dict.pop('_nodetype')

    klass = getattr(c_ast, class_name)

    # Create a new dict containing the key-value pairs which we can pass
    # to node constructors.
    objs = {}
    for key, value in node_dict.items():
        if key == 'coord':
            objs[key] = _parse_coord(value)
        else:
            objs[key] = _convert_to_obj(value)

    # Use keyword parameters, which works thanks to beautifully consistent
    # ast Node initializers.
    return klass(**objs)


def from_json(ast_json):
    """ Build an ast from json string representation """
    return from_dict(json.loads(ast_json))


def parse_func_call_node(root, node, is_if_node = False):
    assert node['_nodetype'] == 'FuncCall'
    print("Function Call Node Found")
    func_call = node['name']['name']
    temp_node = SimplifiedAstNode('FuncCall', func_call)
    if is_if_node:
        root.calls.append(temp_node)
        print("Function call inside if caluse: {}".format(func_call))
    else:
        root.children.append(temp_node)
        print("Function Call: {}".format(func_call))
    

def parse_assignment_node(root, node):
    assert node['_nodetype'] == 'Assignment'
    print("Assignment Node Found")
    if node['rvalue']['_nodetype'] == 'FuncCall':
        parse_func_call_node(root, node['rvalue'])
    

def parse_if_else_node(root,node):
    assert node['_nodetype'] == 'If'
    print("If Node Found")

    curr_node = SimplifiedAstNode('If')
    root.children.append(curr_node)
    
    if node['cond']['left']['_nodetype'] == 'FuncCall':
        # Do something
        parse_func_call_node(curr_node, node['cond']['left'], is_if_node=True)
        
    if node['cond']['right']['_nodetype'] == 'FuncCall':
        # Do something
        parse_func_call_node(curr_node, node['cond']['right'], is_if_node=True)
        
    
    true_node = SimplifiedAstNode('iftrue')
    curr_node.children.append(true_node)
    if 'iftrue' in node:
        true_block = node['iftrue']
        if 'block_items' in true_block and true_block['block_items'] is not None:
            for item in true_block['block_items']:
                if item['_nodetype'] == 'If':
                    parse_if_else_node(true_node, item)
                elif item['_nodetype'] == 'FuncCall':
                    parse_func_call_node(true_node, item)            
                elif item['_nodetype'] == 'Assignment':
                    parse_assignment_node(true_node, item)
                else:
                    pass

    false_node = SimplifiedAstNode('iffalse')
    curr_node.children.append(false_node)
    if 'iffalse' in node and node['iffalse'] is not None:
        false_block = node['iffalse']
        if 'block_items' in false_block and false_block['block_items'] is not None:
            for item in false_block['block_items']:
                if item['_nodetype'] == 'If':
                    parse_if_else_node(false_node, item)
                elif item['_nodetype'] == 'FuncCall':
                    parse_func_call_node(false_node, item)            
                elif item['_nodetype'] == 'Assignment':
                    parse_assignment_node(true_node, item)
                else:
                    pass

def parse_function_definition(node):
    assert node["_nodetype"] == 'FuncDef'
    items_in_function_block = node["body"]["block_items"]
    function_name = node["decl"]["name"]
    function_root_node = SimplifiedAstNode('FuncDef', function_name)
    num_block_items = len(items_in_function_block)

    for item in items_in_function_block:
        if item['_nodetype'] == 'FuncCall':
            parse_func_call_node(function_root_node, item)
        elif item['_nodetype'] == 'Assignment':
            parse_assignment_node(function_root_node, item)    
        elif item['_nodetype'] == 'If':
            parse_if_else_node(function_root_node, item)
        else:
            pass

    return function_root_node


def get_paths_from_conditon_node(node):
    paths = []
    if len(node.calls)>0:
        paths.extend(node.calls)
    true_node = node.children[0]
    false_node = node.children[1]

    true_paths = get_paths_from_branch(true_node)
    # print("True node length: {}".format(len(true_paths)))
    false_paths = get_paths_from_branch(false_node)
    # if false_paths is not None:
    #     print("False node length: {}".format(len(false_paths)))
    
    num_paths = 0
    if false_paths is not None:
        num_paths += len(false_paths)
    
    num_paths += len(true_paths)

    result_paths = []
    if len(paths) == 0:
        result_paths.extend(true_paths)
        if false_paths is not None:
            result_paths.extend(false_paths)
    else:
        for path in paths:
            for t_path in true_paths:
                temp = path.copy()
                temp.extend(t_path)
                result_paths.append(temp)
            if false_paths is not None:
                for f_path in false_paths:
                    temp = path.copy()
                    temp.extend(f_path)
                    result_paths.append(temp)
    
    return result_paths



def get_paths_from_branch(node):
    if node is None:
        return None
    paths = list() # [Cal3, Call4]
    paths.append([])
    for child in node.children:
        if child.type == 'FuncCall':
            for path in paths:
                path.append(child.name)
        elif child.type == 'Assignment':
            for path in paths:
                path.append(child.name)
        elif child.type == 'If':
            temp_paths = get_paths_from_conditon_node(child) # [[], [Call5]]
            new_paths = []
            for path in paths:
                for t_path in temp_paths:
                    temp_original_path = path.copy()
                    temp_original_path.extend(t_path)
                    new_paths.append(temp_original_path)
            paths = new_paths
        else:
            pass
    
    return paths

def get_paths_from_func_def(node):
    block_paths = []
    for child in node.children:
        if child.type == 'FuncCall':
            block_paths.append([child.name])
        elif child.type == 'Assignment':
            block_paths.append([child.name])
        elif child.type == 'If':
            block_paths.append(get_paths_from_conditon_node(child))

    result_paths = []
    q = Queue()
    q.put([])

    for block_path in block_paths:
        curr_size = q.qsize()
        for i in range(curr_size):
            incomplete_path = q.get()
            if len(block_path) == 1:
                temp = incomplete_path.copy()
                temp.extend(block_path)
                q.put(temp)
            elif len(block_path)>1:
                for path in block_path:
                    temp = incomplete_path.copy()
                    temp.extend(path)
                    q.put(temp)
    
    while q.empty() == False:
        result_paths.append(q.get())
    
    return result_paths
    


def store_paths_in_a_json(input_file_path):
    func_name_to_paths_map = dict()
    with open(input_file_path,'r') as f:
        ast_dict = json.load(f)
    
    elements = ast_dict['ext']
    for element in elements:
        if element['_nodetype'] == 'FuncDef':
            func_name = element['decl']['name']
            print(func_name)
            root = parse_function_definition(element)
            paths = get_paths_from_func_def(root)
            count = 0
            temp_dict = dict()
            for path in paths:
                temp_dict[count] = path
                count +=1 
            func_name_to_paths_map[func_name] = temp_dict


    output_file_name = 'paths.json'
    output_fp = open(output_file_name, 'w')
    json.dump(func_name_to_paths_map, output_fp)



#------------------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        
        ast_dict = file_to_dict(sys.argv[1])
        ast = from_dict(ast_dict)
        ast.show()
        fp = open('json_ast.json','w')
        print(to_json(ast, sort_keys=True, indent=4), file=fp)

        store_paths_in_a_json('json_ast.json')
    else:
        print("Please provide a filename as argument")