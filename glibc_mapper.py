import glob
import networkx as nx
import graphviz 
from matplotlib import pyplot as plt
import json

documentation_folder = '/home/rashik/Documents/DoxyGen_Caller_output/html'

block_list = ['main', 'do_test']
glibc_function_call_map = dict()

def print_sample(holder, num):
    for i in range(num):
        print(holder[i])

def get_cgraph_dot_files():
    count = 0
    cgraph_dot_files = []
    for filename in glob.iglob(documentation_folder + '**/**', recursive=True):
        if filename.endswith('cgraph.dot'):
            cgraph_dot_files.append(filename)
        count +=1 
    return cgraph_dot_files

def cgraph_dot_to_nx(dot_file_path, verbose = False):
    
    dirty_graph = nx.DiGraph(nx.drawing.nx_pydot.read_dot(dot_file_path))
    node_count = dirty_graph.number_of_nodes()
    edge_count = dirty_graph.number_of_edges()

    if verbose:
        print("Number of nodes: {}, Number of edges: {}".format(node_count, edge_count))

    node_labels = nx.get_node_attributes(dirty_graph, 'label')
    edge_set = dirty_graph.edges(data = True)
    cleaned_graph = nx.DiGraph()
    idx = 0
    node_to_idx = dict()
    for k in node_labels:
        node_to_idx[k] = idx
        idx +=1
    for k in node_labels:
        cleaned_graph.add_node(node_to_idx[k], label = node_labels[k])
    for edge in edge_set:
        cleaned_graph.add_edge(node_to_idx[edge[0]], node_to_idx[edge[1]])

    return dirty_graph, cleaned_graph
    

def get_roots_of_nx_graph(graph):
    
    root_nodes = []
    degrees = dict(graph.in_degree)
    for node in degrees:
        if degrees[node] == 0:
            root_nodes.append(node)
    return root_nodes

def get_paths(graph, root_idx, debug = False):
    # Pre-order traversal routine
    out_degrees = dict(graph.out_degree)
    leaf_nodes = []
    for node in out_degrees:
        if out_degrees[node] == 0:
            leaf_nodes.append(node)    
    paths = nx.all_simple_paths(graph, root_idx, target= leaf_nodes)
    node_labels = nx.get_node_attributes(graph, 'label')
    labeled_paths = []
    for path in paths:
        temp = []
        for node in path:
            func_name = node_labels[node].replace('"','')
            func_name = func_name.replace("\l","")
            if func_name not in block_list:
                temp.append(func_name)
        labeled_paths.append(temp)
    
    if debug:
        print(labeled_paths)
    return labeled_paths

def update_db_dict(glibc_call_dict, paths, revert = False):
    # Glibc_call_dict is a map in the for of <String, HashSet>
    # The key is the function name. The Value is the all possile next function call
    assert glibc_call_dict is not None, " Error: Glibc call dictionary object is none."

    for path in paths:
        length = len(path)
        if revert==False:
            for i in range(length-1):
                if path[i] not in glibc_call_dict:
                    glibc_call_dict[path[i]] = set()
                    glibc_call_dict[path[i]].add(path[i+1])
                else:
                    glibc_call_dict[path[i]].add(path[i+1])
        else:
            for i in range(1,length,1):
                if path[i] not in glibc_call_dict:
                    glibc_call_dict[path[i]] = set()
                    glibc_call_dict[path[i]].add(path[i-1])
                else:
                    glibc_call_dict[path[i]].add(path[i-1])


def create_glibc_func_call_db():
    count = 0
    available_dot_files = get_cgraph_dot_files()
    print("Total number of call graph dot files: {}".format(len(available_dot_files)))
    for file in available_dot_files:
        original_graph, cleaned_graph = cgraph_dot_to_nx(file)
        node_labels = nx.get_node_attributes(cleaned_graph, 'label')
        degrees = dict(cleaned_graph.out_degree)
        roots = get_roots_of_nx_graph(cleaned_graph)
        for root in roots:
            func_paths = get_paths(cleaned_graph, root)
            update_db_dict(glibc_function_call_map, func_paths, revert=True)

        print("Completed:{} {}".format(count,file))
        count +=1

create_glibc_func_call_db()
func_call_json_file = '/home/rashik/Documents/scripts/func_caller_map_reverted.json'

transformed_glibc_function_call_map = dict()
for k in glibc_function_call_map:
    transformed_glibc_function_call_map[k] = list(glibc_function_call_map[k])

with open(func_call_json_file, 'w') as f:
    json.dump(transformed_glibc_function_call_map, f)


# count = 0
# for k in glibc_function_call_map:
#     print(k, end=' --> ')
#     for element in glibc_function_call_map[k]:
#         print(element, end=', ')
#     print('\n')
#     count +=1
#     if count == 100:
#         break

# for k in node_labels:
#     print(k , node_labels[k], degrees[k])

