import networkx as nx
import os
import argparse
import json
import graphviz


def spade_json_load_edges(data):
    edge = {}
    edge["from"] = data["from"]
    edge["to"] = data["to"]
    edge["type"] = data["type"]

    edge_attrs = data["annotations"]
    for attr in edge_attrs.keys():
        edge[attr] = edge_attrs[attr]
    return edge
    
def spade_json_load_graphs(path):
    vertices = []
    edges = []
    log = open(path, 'r', encoding="utf-8")

    line = log.readline()
    while line:
        if "[" in line or "]" in line:
            line = log.readline()
            continue
        if line[0] == ",":
            line = line[1:]
        data = json.loads(line)
        if "from" not in data.keys():
            vertices.append(data)
        else:
            edges.append(spade_json_load_edges(data))
        line = log.readline()
    log.close()

    return vertices, edges


def camflow_graph(vertices, edges):
    provG = nx.MultiDiGraph()
    for vertex in vertices:
        vid = vertex["id"]
        label_dict = vertex["annotations"]
        node_type = label_dict["object_type"]
        if node_type == "unknown":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"])
        elif node_type == "string":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + label_dict["log"])
        elif node_type == "task":
            # TODO: check the name of the task "cf:name"
            try:
                provG.add_node(vid, prov_type=label_dict["object_type"],
                               label=label_dict["object_type"] + ":" + label_dict["cf:name"])
            except:
                print(vid)
                provG.add_node(vid, prov_type=label_dict["object_type"],
                               label=label_dict["object_type"])
        elif node_type == "inode_unknown":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"])
        elif node_type in ["link", "directory", "char", "block", "pipe", "socket"]:
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + label_dict["secctx"] + ":" + str(
                               label_dict["mode"]))
        elif node_type == "file":
            # TODO: check the name of the task "cf:name"
            if "cf:name" in label_dict.keys():
                provG.add_node(vid, prov_type=label_dict["object_type"],
                               label=label_dict["object_type"] + ":" + label_dict["cf:name"] + ":" + label_dict["secctx"])
            else:
                print(vid)
                provG.add_node(vid, prov_type=label_dict["object_type"],
                               label=label_dict["object_type"] + ":" + label_dict["secctx"] + ":" + str(
                                   label_dict["mode"]))
        elif node_type == "msg":
            # TODO: need to decide the attributes
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"])
        elif node_type == "shm":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + str(label_dict["mode"]))
        elif node_type == "address":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + str(label_dict["host"]) + ":" + str(label_dict["service"]))
        elif node_type == "sb":
            # TODO: need to decide the attributes
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"])
        elif node_type == "path":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + label_dict["pathname"])
        elif node_type in ["disc_entity", "disc_activity", "disc_agent"]:
            # TODO: need to decide the attributes
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"])
        elif node_type == "machine":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + label_dict["u_sysname"] + ":" + label_dict["u_nodename"] + ":" + label_dict["u_release"] + ":" + label_dict["u_version"] + ":" + label_dict["u_machine"])
        elif node_type == "packet":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + label_dict["sender"] + ":" + label_dict[
                               "receiver"])
        elif node_type == "iattr":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + str(label_dict["mode"]))
        elif node_type == "xattr":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + label_dict["name"])
        elif node_type == "packet_content":
            # TODO: need to decide the attributes
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"])
        elif node_type == "argv":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + label_dict["argv"])
        elif node_type == "envp":
            provG.add_node(vid, prov_type=label_dict["object_type"],
                           label=label_dict["object_type"] + ":" + label_dict["envp"])
        elif node_type == "process_memory":
            try:
                provG.add_node(vid, prov_type=label_dict["object_type"],
                               label=label_dict["object_type"] + ":" + label_dict["cf:name"] + ":" + str(label_dict["uid"]) + ":" + str(label_dict["gid"]) + ":" + label_dict["secctx"])
            except:
                print(vid)
                provG.add_node(vid, prov_type=label_dict["object_type"],
                               label=label_dict["object_type"] + ":" + str(label_dict["uid"]) + ":" + str(label_dict["gid"]) + ":" + label_dict["secctx"])
        provG.nodes[vid]["anomalous"] = 0

    for edge in sorted(edges, key=lambda a: int(a["jiffies"])):
        provG.add_edge(
            edge["from"],
            edge["to"],
            relation_type=edge["relation_type"] if "relation_type" in edge.keys() else edge["type"],
            # here I use jiffies to identify the recorded time of the edge
            time=int(edge["jiffies"]),
            epoch=int(edge["epoch"]),
            label=(edge["relation_type"] if "relation_type" in edge.keys()
                   else edge["type"]) + ":epoch:" + str(edge["epoch"]),
            anomalous=0
        )

    # remove edges without src or dst nodes
    remove_bad_edges = []
    for edge in provG.edges.data():
        src, dst, attr = edge
        if provG.nodes[src] == {}:
            remove_bad_edges.append(src)
        elif provG.nodes[dst] == {}:
            remove_bad_edges.append(dst)
    provG.remove_nodes_from(remove_bad_edges)

    # remove isolated nodes
    remove_bad_nodes = []
    for nid in provG.nodes:
        if list(provG.successors(nid)) == [] and list(provG.predecessors(nid)) == []:
            remove_bad_nodes.append(nid)
    provG.remove_nodes_from(remove_bad_nodes)

    return provG


def spade_graph(vertices, edges):
    provG = nx.MultiDiGraph()
    for vertex in vertices:
        nid = vertex["id"]
        label_dict = vertex["annotations"]

        if vertex["type"] == "Process":
            provG.add_node(nid, prov_type="Process", label="Process")
            provG.nodes[nid]["anomalous"] = 0
            if "exe" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + ":" + label_dict["exe"]
        elif vertex["type"] == "Artifact":
            provG.add_node(nid, prov_type="Artifact", label="Artifact")
            provG.nodes[nid]["anomalous"] = 0
            if "subtype" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + ":" + label_dict["subtype"]
            if "path" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + ":" + label_dict["path"]
            if "permission" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + \
                    ":" + label_dict["permission"]
            if "local address" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + \
                    ":" + label_dict["local address"]
            if "local port" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + \
                    ":" + label_dict["local port"]
            if "remote address" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + \
                    ":" + label_dict["remote address"]
            if "remote port" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + \
                    ":" + label_dict["remote port"]
            if "protocol" in label_dict.keys():
                provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + ":" + label_dict["protocol"]
        # we don't collect agent, but write down in advance in case we collect for the future
        elif vertex["type"] == "Agent":
            provG.add_node(nid, prov_type="Agent", label="Agent")
            provG.nodes[nid]["anomalous"] = 0
            provG.nodes[nid]["label"] = provG.nodes[nid]["label"] + ":" + label_dict["uid"]\
                + ":" + label_dict["euid"]\
                + ":" + label_dict["gid"]\
                + ":" + label_dict["egid"]

    for edge in edges:
        u = edge["from"]
        v = edge["to"]
        relation = edge["operation"] if "operation" in edge.keys() else edge["type"]
        provG.add_edge(
            u,
            v,
            relation_type=relation,
            time=float(edge["time"]),
            label=relation + ":" + edge["time"],
            anomalous=0
        )

    # remove edges without src or dst nodes
    remove_bad_edges = []
    for edge in provG.edges.data(keys=True):
        src, dst, key, attr = edge
        if provG.nodes[src] == {}:
            remove_bad_edges.append(src)
        elif provG.nodes[dst] == {}:
            remove_bad_edges.append(dst)
    provG.remove_nodes_from(remove_bad_edges)

    # remove isolated nodes
    remove_bad_nodes = []
    for nid in provG.nodes:
        if list(provG.successors(nid)) == [] and list(provG.predecessors(nid)) == []:
            remove_bad_nodes.append(nid)
    provG.remove_nodes_from(remove_bad_nodes)

    return provG


def write_graphviz(graph):
    g = graphviz.Digraph()
    for nid in graph.nodes:
        nid_str = nid.replace("=", "")
        g.node(nid_str, label=graph.nodes[nid]["label"])
    for (u, v, k) in graph.edges:
        u_str = u.replace("=", "")
        v_str = v.replace("=", "")
        g.edge(u_str, v_str, label=graph.edges[u, v, k]["label"])

    g.render("graph.dot", format="pdf", outfile="graph.pdf")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', help='input log file path', required=True)
    parser.add_argument(
        '--c', help='input capturer of the log file (0 for camflow and 1 for spade)', required=True)
    # parser.add_argument('-o', '--output', help='output file path', required=True)
    args = parser.parse_args()

    vertices, edges = spade_json_load_graphs(args.file)
    print("finish loading graph!\n")

    if args.c == "0":
        graph = camflow_graph(vertices, edges)

    elif args.c == "1":
        graph = spade_graph(vertices, edges)

    write_graphviz(graph)