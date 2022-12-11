import json
import os
import graphviz

indirection_map = {'fopen':'_IO_new_fopen', 'fclose':'_IO_new_fclose'}

exec_path_file = os.path.join(os.getcwd(), 'paths.json')
path_dict = dict()

with open(exec_path_file, 'r') as fp:
    path_dict = json.load(fp)

if 'main' not in path_dict:
    print("Main function not found.")
    exit()
else:
    main_func_paths = path_dict['main']
    print(main_func_paths)


print("For the demonstration purpose we will be using the longest path.")
print("Longest path is: {}".format(main_func_paths['1']))

glibc_map = json.load(open('func_caller_map_reverted.json', 'r'))
syscall_map = json.load(open('syscall_map.json', 'r'))

provenance_edges = []

for func_call in  main_func_paths['1']:
    if func_call not in glibc_map:
        print('Function call not found in glibc map: {}'.format(func_call))
        print("Looking into indirection map.")

        if func_call in indirection_map:
            ind_func_call = indirection_map[func_call]
            if ind_func_call in glibc_map:
                calls = glibc_map[ind_func_call]
                for call in calls:
                    if call in syscall_map:
                        provenance_edges.append(syscall_map[call])
    else:
        calls = glibc_map[func_call]
        for call in calls:
            if call in syscall_map:
                provenance_edges.append(syscall_map[call])

print(provenance_edges)

# Default setting of the graph # 

g = graphviz.Digraph()

g.node('1', label="Artifact")
g.node('2', label = os.path.join(os.getcwd(), "Binary name"))
g.node('3', label = os.path.join(os.getcwd(), "Binary name"))

g.edge('1','2', label = 'gettime')
g.edge('2','3', label = 'load')


# Add the provenance edges now # 
curr_count = 5

for edge in provenance_edges:
    g.node(str(curr_count), label = os.path.join(os.getcwd(), "Artifact_Object"))
    g.edge('2', str(curr_count), edge)
    curr_count +=1

g.node(str(curr_count), label = os.path.join(os.getcwd(), "Binary name"))
g.edge('2',str(curr_count), label = 'exit')

g.render("graph.dot", format="pdf", outfile="graph.pdf")






