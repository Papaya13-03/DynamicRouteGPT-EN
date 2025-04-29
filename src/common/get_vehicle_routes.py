import xml.etree.ElementTree as ET

def get_vehicle_routes(route_file):
    """
    Hàm đọc XML từ file và tạo dictionary với key là vehicleId, value là một dictionary gồm:
    - 'route': list các edges,
    - 'target_edge_index': edge đang được đi đến route.
    
    Parameters:
    route_file (str): Đường dẫn đến file XML cần đọc.
    
    Returns:
    dict: Dictionary với key là vehicleId và value là một dictionary chứa route và current_target_edge.
    """
    tree = ET.parse(route_file)
    root = tree.getroot()

    vehicle_routes = {}

    for vehicle in root.findall('vehicle'):
        vehicle_id = vehicle.get('id')
        route_edges = vehicle.find('route').get('edges').split()
        
        vehicle_routes[vehicle_id] = {
            'route': route_edges,
            'target_edge_index': 0
        }

    return vehicle_routes
