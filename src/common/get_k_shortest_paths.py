import networkx as nx
from networkx import DiGraph

def get_k_shortest_paths(graph: DiGraph, start_edge: str, end_edge: str, k: int) -> list:
    """
    Find the k shortest paths in a network using Yen's algorithm.

    :param graph: The network graph (DiGraph).
    :param start_edge: The starting edge ID.
    :param end_edge: The ending edge ID.
    :param k: The number of shortest paths to find.
    :return: A list of k shortest paths, each represented as a list of edge IDs.
    """
    start_node, end_node = None, None

    # Find the corresponding start and end nodes
    for u, v, data in graph.edges(data=True):
        if data.get('edge') == start_edge:
            start_node = v
        if data.get('edge') == end_edge:
            end_node = u

    if start_node is None or end_node is None:
        raise ValueError("Cannot find start_node or end_node based on the given edge IDs.")

    # Step 1: Find the first shortest path
    shortest_path_nodes = nx.dijkstra_path(graph, start_node, end_node, weight='weight')
    k_shortest_paths_nodes = [shortest_path_nodes]

    for _ in range(1, k):
        temp_graph = graph.copy()

        # Remove edges (u, v) along the last found path
        last_path = k_shortest_paths_nodes[-1]
        for i in range(len(last_path) - 1):
            u, v = last_path[i], last_path[i + 1]
            if temp_graph.has_edge(u, v):
                temp_graph.remove_edge(u, v)

        try:
            alternative_path_nodes = nx.dijkstra_path(temp_graph, start_node, end_node, weight='weight')
            k_shortest_paths_nodes.append(alternative_path_nodes)
        except nx.NetworkXNoPath:
            print("No more paths available")
            break

    # Convert node paths to edge IDs
    k_shortest_paths_edges = []
    for path_nodes in k_shortest_paths_nodes:
        path_edges = [start_edge]
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            edge_id = graph.edges[u][v]['edge']
            path_edges.append(edge_id)
        path_edges.append(end_edge)
        k_shortest_paths_edges.append(path_edges)

    return k_shortest_paths_edges
