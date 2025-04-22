import xml.etree.ElementTree as ET
import random
from xml.dom import minidom

def generate_routes(net_file, routes_file):
    """Sinh ra tệp routes.xml dựa trên tệp net.xml với lộ trình hợp lệ."""
    try:
        # Đọc tệp net.xml
        tree = ET.parse(net_file)
        root = tree.getroot()

        # Lấy danh sách các đoạn đường (edges) không phải internal
        edges = [edge.attrib['id'] for edge in root.findall(".//edge") if edge.attrib.get('function') != 'internal']

        # Lấy danh sách các kết nối hợp lệ giữa các đoạn đường
        connections = {}
        for connection in root.findall(".//connection"):
            from_edge = connection.attrib["from"]
            to_edge = connection.attrib["to"]
            if from_edge in edges and to_edge in edges:  # Đảm bảo không phải internal
                if from_edge not in connections:
                    connections[from_edge] = []
                connections[from_edge].append(to_edge)

        # Tạo gốc cho routes.xml
        routes = ET.Element("routes")

        # Tạo một số phương tiện với lộ trình hợp lệ
        num_vehicles = 100  # Số lượng phương tiện
        for i in range(num_vehicles):
            vehicle_id = f"{i}"  # ID của phương tiện
            depart_time = str(i)  # Thời gian khởi hành

            # Tạo lộ trình hợp lệ
            route_edges = create_valid_route(edges, connections)
            if not route_edges:
                continue  # Bỏ qua nếu không tạo được lộ trình hợp lệ

            route_edges_str = " ".join(route_edges)

            # Tạo phần tử vehicle và route
            vehicle = ET.SubElement(routes, "vehicle", id=vehicle_id, depart=depart_time)
            ET.SubElement(vehicle, "route", edges=route_edges_str)

        # Ghi tệp XML với định dạng đẹp
        pretty_xml = minidom.parseString(ET.tostring(routes)).toprettyxml(indent="  ")
        with open(routes_file, "w") as f:
            f.write(pretty_xml)

        print(f"Đã tạo tệp {routes_file} với {num_vehicles} phương tiện hợp lệ.")

    except ET.ParseError as e:
        print(f"Lỗi khi phân tích XML: {e}")
    except Exception as e:
        print(f"Lỗi: {e}")

def create_valid_route(edges, connections):
    """Tạo một lộ trình hợp lệ bằng cách kết nối các đoạn đường liên tiếp."""
    if not edges or not connections:
        return []

    # Chọn một đoạn đường ngẫu nhiên để bắt đầu
    start_edge = random.choice(edges)
    route_edges = [start_edge]

    # Tạo lộ trình bằng cách nối tiếp các đoạn đường hợp lệ
    current_edge = start_edge
    while len(route_edges) < 10:  # Giới hạn số cạnh trong route
        next_edges = connections.get(current_edge, [])
        if not next_edges:
            break  # Dừng nếu không có cạnh nối tiếp hợp lệ
        next_edge = random.choice(next_edges)  # Chọn cạnh tiếp theo ngẫu nhiên
        route_edges.append(next_edge)
        current_edge = next_edge

    return route_edges if len(route_edges) > 1 else []  # Chỉ trả về nếu có lộ trình hợp lệ

# Chạy chương trình để tạo routes.xml

dataset_path = "./dataset/HUST"
net_file = f"{dataset_path}/net.xml"
routes_file = f"{dataset_path}/routes.xml"

generate_routes(net_file, routes_file)
