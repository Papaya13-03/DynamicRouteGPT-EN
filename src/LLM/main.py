from src.LLM.VehicleController import VehicleController
import time
from dotenv import load_dotenv
import os

if __name__ == '__main__':
    load_dotenv()

    dataset_path = "./dataset/mini-grid"
    net_file = f'{dataset_path}/net.xml'
    rou_file = f'{dataset_path}/routes.xml'
    cfg_file = f'{dataset_path}/config_file.sumocfg'

    vehicle_controller = VehicleController(net_file, rou_file, cfg_file)
    vehicle_controller.run_simulation()

    file_name = time.strftime("%d-%m-%Y %H:%M:%S")

    vehicle_controller._save_results(f"results/LLM/{file_name}.csv")
    vehicle_controller.finish_simulation()