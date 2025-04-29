from networkx import DiGraph
from networkx import shortest_path

def get_shortest_path(graph: DiGraph, start_edge: str, end_edge: str) -> list:
    """
    Get the shortest path between two edges in a directed graph.

    :param graph: DiGraph
    :param start_edge: The starting edge ID.
    :param end_edge: The ending edge ID.
    :return: A list of edges representing the shortest path.
    """
    try:
        start_node = None
        end_node = None

        for u, v, data in graph.edges(data=True):
            if data.get('edge') == start_edge:
                start_node = v
            if data.get('edge') == end_edge:
                end_node = u

        if start_node is None or end_node is None:
            raise ValueError(f"Start or end edge not found in graph! start_edge={start_edge}, end_edge={end_edge}")

        nodes_path = shortest_path(graph, source=start_node, target=end_node, weight='weight')
        edge_path = [start_edge] + [graph[u][v]['edge'] for u, v in zip(nodes_path[:-1], nodes_path[1:])] + [end_edge]
        return edge_path

    except Exception as e:
        print(f"Error finding shortest path: {e}")
        return []
