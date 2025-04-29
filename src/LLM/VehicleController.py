import os

from dotenv import load_dotenv
from src.common.load_prompt import load_prompt
from src.common.deepseek import DeepSeekApi
from src.common.get_k_shortest_paths import get_k_shortest_paths
from src.common.get_vehicle_routes import get_vehicle_routes
from src.common.get_shortest_path import get_shortest_path
from src.common.save_to_csv import save_to_csv
import traci
import sumolib
import networkx as nx
from typing import Dict, Optional
import re

NUMBER_OF_SHORTEST_PATHS = 3

class VehicleController:
    def __init__(self, net_file: str, rou_file: str, cfg_file: str) -> None:
        load_dotenv()
        self.net_file = net_file
        self.rou_file = rou_file
        self.cfg_file = cfg_file

        self.net_data = sumolib.net.readNet(net_file)
        self.graph = self._init_graph()

        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.total_travel_time: float = 0.0
        self.total_waiting_time: float = 0.0
        self.total_time_loss: float = 0.0

        self.prompt_path = os.getenv("PROMPT_PATH")
        self.deepseek = DeepSeekApi()

    def _init_graph(self) -> nx.DiGraph:
        graph = nx.DiGraph()
        for edge in self.net_data.getEdges():
            from_node = edge.getFromNode().getID()
            to_node = edge.getToNode().getID()
            graph.add_edge(from_node, to_node, edge=edge.getID(), weight=edge.getLength())
        return graph

    def _get_target_edge(self, vehicle_id: str, current_edge: str, vehicle_routes: Dict) -> Optional[str]:
        route_info = vehicle_routes.get(vehicle_id)
        if not route_info:
            return None

        route = route_info['route']
        target_index = route_info['target_edge_index']

        if target_index < len(route):
            target_edge = route[target_index]

            if current_edge == target_edge:
                route_info['target_edge_index'] += 1
                if route_info['target_edge_index'] < len(route):
                    return route_info['route'][route_info['target_edge_index']]
            else:
                return target_edge
        return None

    def _is_approaching_intersection(self, vehicle_id: str, threshold: float = 2.0) -> bool:
        lane_id = traci.vehicle.getLaneID(vehicle_id)
        lane_pos = traci.vehicle.getLanePosition(vehicle_id)
        lane_length = traci.lane.getLength(lane_id)
        return (lane_length - lane_pos) <= threshold

    def _is_inside_intersection(self, vehicle_id: str) -> bool:
        return traci.vehicle.getRoadID(vehicle_id).startswith(":")

    def _save_results(self, file_path: str) -> None:
        records = [{
            "total_travel_time": self.total_travel_time,
            "total_waiting_time": self.total_waiting_time,
            "total_time_loss": self.total_time_loss
        }]
        save_to_csv(file_path, fieldnames=list(records[0].keys()), records=records)

    def _get_traffic_light_count(self, path: list, net_file: str) -> int:
        net_data = sumolib.net.readNet(net_file)
        traffic_lights = net_data.getTrafficLights()
        count = 0
        for tl in traffic_lights:
            if tl.getID() in path:
                count += 1
        return count
    
    def _get_estimated_time(self, path: list) -> float:
        return sum(traci.edge.getTraveltime(edge) for edge in path)

    def _get_vehicle_density_(self, path: list) -> float:
        total_vehicles = sum(traci.edge.getLastStepOccupancy(edge) for edge in path)
        total_path_length = len(path)
        return total_vehicles / total_path_length if total_path_length > 0 else 0.0
    
    def _get_llm_suggestion(
        self,
        k_shortest_paths,
        traffic_light_count,
        estimated_time_list,
        vehicle_density_list
    ):
        prompt = load_prompt(
            self.prompt_path,
            k_shortest_paths=k_shortest_paths,
            traffic_light_count=traffic_light_count,
            estimated_time_list=estimated_time_list,
            vehicle_density_list=vehicle_density_list
        )

        response = self.deepseek.request(prompt)
        chose_path = self._parse_chosen_path(response)

        return chose_path if chose_path else k_shortest_paths[0]

    def _parse_chosen_path(self, response: str) -> list:
        """Parse the chosen path from LLM response."""
        pattern = r"chose_path\s*=\s*\[([^\]]+)\]"
        match = re.search(pattern, response)

        if not match:
            return None

        return re.findall(r"'(.*?)'", match.group(1))

    def run_simulation(self) -> None:
        sumo_cmd = ["sumo-gui", "-n", self.net_file, "-r", self.rou_file, "-c", self.cfg_file]
        traci.start(sumo_cmd)

        vehicle_routes = get_vehicle_routes(self.rou_file)
        step = 0

        while traci.simulation.getMinExpectedNumber() > 0:
            traci.simulationStep()

            if self.start_time is None:
                self.start_time = traci.simulation.getTime()

            vehicles = traci.vehicle.getIDList()
            self.total_travel_time += len(vehicles) * traci.simulation.getDeltaT()

            step += 1

            for vehicle_id in vehicles:
                current_edge = traci.vehicle.getRoadID(vehicle_id)
                target_edge = self._get_target_edge(vehicle_id, current_edge, vehicle_routes)

                if not target_edge:
                    self.total_waiting_time += traci.vehicle.getAccumulatedWaitingTime(vehicle_id)
                    self.total_time_loss += traci.vehicle.getTimeLoss(vehicle_id)
                    continue

                if self._is_inside_intersection(vehicle_id) or not self._is_approaching_intersection(vehicle_id):
                    continue

                k_shortest_paths = get_k_shortest_paths(self.graph, current_edge, target_edge, NUMBER_OF_SHORTEST_PATHS)
                traffic_light_count = [self._get_traffic_light_count(path, self.net_file) for path in k_shortest_paths]
                estimated_time_list = [self._get_estimated_time(path) for path in k_shortest_paths]
                vehicle_density_list = [self._get_vehicle_density_(path) for path in k_shortest_paths]

                choose_path = self._get_llm_suggestion(
                    k_shortest_paths,
                    traffic_light_count,
                    estimated_time_list,
                    vehicle_density_list
                )

                traci.vehicle.setRoute(vehicle_id, choose_path)

        self.end_time = traci.simulation.getTime()

        print(f"Simulation ended at {self.end_time} seconds")
        print(f"Total simulation time: {self.end_time - self.start_time} seconds")
        print(f"Total travel time: {self.total_travel_time} seconds")
        print(f"Total waiting time: {self.total_waiting_time} seconds")
        print(f"Total time loss: {self.total_time_loss} seconds")

    def finish_simulation(self) -> None:
        traci.close()
        print("Simulation finished and closed.")