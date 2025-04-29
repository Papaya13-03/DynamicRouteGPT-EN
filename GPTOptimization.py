import traci
import sumolib
import networkx as nx
import xml.etree.ElementTree as ET
import time
from dotenv import load_dotenv
import os
import requests
import json
import sys
import re
import heapq

load_dotenv()
G = nx.DiGraph()

def init_graph(net_data):
    for edge in net_data.getEdges():
        from_node = edge.getFromNode().getID()
        to_node = edge.getToNode().getID()
        length = edge.getLength()
        G.add_edge(from_node, to_node, edge=edge.getID(), weight=length)

def get_shortest_path(net_data, start_edge, end_edge):
    path = net_data.getShortestPath(start_edge, end_edge)
    return path[0] if path else []

def find_k_shortest_paths(net_data, start_edge, end_edge, k):
    G = nx.DiGraph()

    for edge in net_data.getEdges():
        from_node = edge.getFromNode().getID()
        to_node = edge.getToNode().getID()
        length = edge.getLength()
        G.add_edge(from_node, to_node, edge=edge.getID(), weight=length)

    start_node = net_data.getEdge(start_edge).getToNode().getID()
    end_node = net_data.getEdge(end_edge).getFromNode().getID()

    paths = []
    heap = []

    try:
        shortest_path = nx.shortest_path(G, start_node, end_node, weight="weight")
        paths.append(shortest_path)
    except nx.NetworkXNoPath:
        return []

    for _ in range(k - 1):
        for i in range(len(paths[-1]) - 1):
            spur_node = paths[-1][i]
            root_path = paths[-1][:i + 1]

            removed_edges = []
            for path in paths:
                if len(path) > i and path[:i + 1] == root_path:
                    u, v = path[i], path[i + 1]
                    if G.has_edge(u, v):
                        removed_edges.append((u, v, G[u][v]['weight'], G[u][v]['edge']))
                        G.remove_edge(u, v)

            try:
                spur_path = nx.shortest_path(G, spur_node, end_node, weight="weight")
                new_path = root_path[:-1] + spur_path
                heapq.heappush(heap, (nx.path_weight(G, new_path, weight="weight"), new_path))
            except nx.NetworkXNoPath:
                pass

            for u, v, weight, edge in removed_edges:
                G.add_edge(u, v, weight=weight, edge=edge)

        if not heap:
            break

        _, next_best_path = heapq.heappop(heap)
        paths.append(next_best_path)

    k_paths = []
    for path in paths:
        edge_path = [start_edge]
        for u, v in zip(path[:-1], path[1:]):
            edge_path.append(G[u][v]['edge'])
        edge_path.append(end_edge)
        k_paths.append(edge_path)

    return k_paths

def get_node_id(net_data, path):
    node_ids = []
    for edge in path:
        edge_obj = net_data.getEdge(edge)
        node_ids.append(edge_obj.getFromNode().getID())
        node_ids.append(edge_obj.getToNode().getID())

    node_ids = list(set(node_ids))
    return node_ids

def count_traffic_lights(net_data, path, net_path):
    count = 0
    tree = ET.parse(net_path)
    root = tree.getroot()
    node_ids = get_node_id(net_data, path)

    for tl_logic in root.findall(".//tlLogic"):
        if tl_logic.attrib['id'] in node_ids:
            count += 1

    return count

def get_estimate_time(path):
    total_time = sum(traci.edge.getTraveltime(edge) for edge in path)
    return total_time

def get_vehicle_density(path):
    total_vehicles = sum(traci.edge.getLastStepVehicleNumber(edge) for edge in path)
    return total_vehicles / len(path) if len(path) > 0 else 0
def get_deepseek_response(prompt):
    deepseek_api_url = os.getenv("DEEPSEEK_API_URL")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

    # Ghi prompt vào file
    with open("deepseek_tracking.txt", "a") as f:
        f.write(f"Prompt: {prompt}\n\n")

    body = {
        "model": "deepseek-chat",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }

    headers = {
        "Authorization": f"Bearer {deepseek_api_key}",
        "Content-Type": "application/json"
    }

    response = requests.post(
        deepseek_api_url,
        json=body,
        headers=headers
    )

    # Ghi response vào file
    with open("deepseek_tracking.txt", "a") as f:
        if response.status_code == 200:
            response_content = response.json()["choices"][0]["message"]["content"]
            f.write(f"Response: {response_content}\n\n")
        else:
            f.write(f"Error: {response.status_code} - {response.text}\n\n")

    # In ra nội dung response nếu cần thiết
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        response.raise_for_status()


def gpt_decision(k_shortest_paths, traffic_light_count, estimated_time_list, vehicle_density_list):
    prompt = f'''
        You are a driver operating a car on city roads.
        Now you have reached an intersection.
        You want to choose one of up to three available routes: {k_shortest_paths}.
        Each route has a number of traffic lights: {traffic_light_count}.
        The estimated time to pass through these routes is {estimated_time_list}, in seconds.
        The average vehicle density (number of vehicles per edge) for each route is: {vehicle_density_list}.

        Please choose the best path to minimize delay and traffic issues.

        Output format:
        chose_path = [...]
        choice_reason = '...'
    '''

    response = get_deepseek_response(prompt)

    pattern = r"chose_path\s*=\s*\[([^\]]+)\]"
    match = re.search(pattern, response)

    if match:
        chose_path = re.findall(r"'(.*?)'", match.group(1))
        print("chose_path: ", chose_path)
        return chose_path

    return k_shortest_paths[0]

def run_sumo_simulation(net_file, rou_file, cfg_file, tracking_vehicle_id):
    sumo_cmd = ["sumo-gui", "-n", net_file, "-r", rou_file, "-c", cfg_file]
    traci.start(sumo_cmd)

    net_data = sumolib.net.readNet(net_file)
    init_graph(net_data)

    step = 0

    while traci.simulation.getMinExpectedNumber() > 0:
        traci.simulationStep(step)
        step += 1
        print("step: ", step)
        time.sleep(0.1)

        vehicles = traci.vehicle.getIDList()
        for vi in vehicles:
            # if vi != tracking_vehicle_id:
            #     continue

            current_edge = traci.vehicle.getRoadID(vi)
            target_edge = traci.vehicle.getRoute(vi)[-1]

            if current_edge == target_edge:
                print(f"Vehicle {vi} finished")
                continue

            if str(current_edge).startswith(":"):
                continue

            lane_id = traci.vehicle.getLaneID(vi)
            lane_pos = traci.vehicle.getLanePosition(vi)
            lane_length = traci.lane.getLength(lane_id)

            if (lane_length - lane_pos) > 1.0:
                continue

            k_shortest_paths = find_k_shortest_paths(net_data, current_edge, target_edge, 3)
            traffic_light_count = [count_traffic_lights(net_data, path, net_file) for path in k_shortest_paths]
            estimated_time_list = [get_estimate_time(path) for path in k_shortest_paths]
            vehicle_density_list = [get_vehicle_density(path) for path in k_shortest_paths]

            chosen_path = gpt_decision(k_shortest_paths, traffic_light_count, estimated_time_list, vehicle_density_list)
            traci.vehicle.setRoute(vi, chosen_path)

    print("Finished simulation")
    traci.close()

if __name__ == '__main__':
    dataset_path = "./dataset/hangzhou"
    net_file = f'{dataset_path}/net.xml'
    rou_file = f'{dataset_path}/routes.xml'
    cfg_file = f'{dataset_path}/config_file.sumocfg'

    tracking_vehicle_id = '0'

    run_sumo_simulation(net_file, rou_file, cfg_file, tracking_vehicle_id)
