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
# from gpt4all import GPT4All
# model = GPT4All("Meta-Llama-3-8B-Instruct.Q4_0.gguf") # downloads / loads a 4.66GB LLM

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
    start_node = net_data.getEdge(start_edge).getToNode().getID()
    end_node = net_data.getEdge(end_edge).getFromNode().getID()

    paths = list(nx.shortest_simple_paths(G, start_node, end_node, weight="weight"))

    k_paths = []
    for path in paths[:k]:
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

def get_deepseek_response(prompt):
    deepseek_api_url = os.getenv("DEEPSEEK_API_URL")
    deepseek_api_key = os.getenv("DEEPSEEK_API_KEY")

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
        "Content-Type": "application/json"  # Thêm Content-Type
    }

    response = requests.post(
        deepseek_api_url,
        json=body,  # Dùng json thay vì data=json.dumps(body)
        headers=headers
    )

    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        response.raise_for_status()

def gpt_decision(k_shortest_paths, traffic_light_count, estimated_time_list):
    prompt = f'''
        You are a driver operating a car on city roads.
        Now you have reached an intersection.
        Next, you want to choose a route from up to three available options: {k_shortest_paths}.
        Each route has a specific number of traffic lights: {traffic_light_count}.
        The estimated time to pass through these routes is {estimated_time_list}, represented as [pass_path1_time, pass_path2_time, pass_path3_time] in seconds.


        Please output the route with the shortest estimated time and provide the reasoning for the choice. For example:

        Assume:
        k_shortest_paths = [['edge1','edge2','edge3','edge7'],['edge1','edge4','edge7'],['edge1','edge5','edge6','edge7','edge8','edge7']]
        total_time = [30,40,50]
        traffic_light_count = [3,2,4]
        error_edge = ['edge2']

        Output:
        chose_path = ['edge1','edge4','edge7']
        choice_reason = 'From the total_time perspective: path1 < path2 < path3.
                        From the traffic_light_count perspective: path2 < path1 < path3.
                        Considering the error_edge, we cannot choose a path containing "edge2", meaning path1 is not an option.
                        There is no mandatory path that must be taken.
                        Based on a comprehensive assessment, path2 is selected.'
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

        step += 10
        print("step: ", step)

        vehicles = traci.vehicle.getIDList()

        if tracking_vehicle_id in traci.vehicle.getIDList():
            print("Tracking vehicle still in the simulation")
            traci.gui.setZoom('View #0', 1000)
            traci.gui.trackVehicle('View #0', tracking_vehicle_id)
        
        for vi in vehicles:
            if vi not in traci.vehicle.getIDList() or vi != tracking_vehicle_id:
                continue
            current_edge = traci.vehicle.getRoadID(vi)
            target_edge = traci.vehicle.getRoute(vi)[-1]

            if current_edge == target_edge:
                print(f"Vehicle {vi} finished")
                continue

            #Skip Intersection
            if str(current_edge).startswith(":"):
                continue

            k_shortest_paths = find_k_shortest_paths(net_data, current_edge, target_edge, 3)
            traffic_light_count = [count_traffic_lights(net_data, path, net_file) for path in k_shortest_paths]
            estimated_time_list = [get_estimate_time(path) for path in k_shortest_paths]
            chosen_path = gpt_decision(k_shortest_paths, traffic_light_count, estimated_time_list)
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
