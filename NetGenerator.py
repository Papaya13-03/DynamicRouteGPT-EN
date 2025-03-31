import subprocess

def osm_to_net(osm_file, net_file):
    """Chuyển đổi tệp OSM thành net.xml sử dụng netconvert từ SUMO."""
    command = [
        "netconvert",              # Lệnh netconvert của SUMO
        "--osm-files", osm_file,   # Đường dẫn tới tệp OSM
        "--output-file", net_file  # Đường dẫn tới tệp net.xml sẽ được tạo ra
    ]
    
    try:
        # Chạy lệnh netconvert
        subprocess.run(command, check=True)
        print(f"Đã tạo tệp {net_file} từ {osm_file}.")
    except subprocess.CalledProcessError as e:
        print(f"Lỗi khi chuyển đổi: {e}")

import xml.etree.ElementTree as ET

def adjust_net_xml(net_file):
    try:
        # Phân tích cú pháp tệp XML
        tree = ET.parse(net_file)
        root = tree.getroot()

        # Duyệt qua tất cả các đoạn đường trong tệp XML
        for lane in root.findall(".//lane"):
            # Xóa bỏ thuộc tính disallow nếu có
            if 'disallow' in lane.attrib:
                del lane.attrib['disallow']
            
            if 'allow' in lane.attrib:
                del lane.attrib['allow']

            # Thêm thuộc tính allow cho phép mọi phương tiện (nếu chưa có)
            # if 'allow' not in lane.attrib:
            #     lane.set('allow', 'car')  # Cho phép phương tiện 'car', có thể thay đổi nếu cần

        # Lưu lại các thay đổi vào tệp net.xml
        tree.write(net_file)
        print(f"Tệp {net_file} đã được điều chỉnh.")

    except ET.ParseError as e:
        print(f"Lỗi khi phân tích tệp XML: {e}")
    except Exception as e:
        print(f"Lỗi: {e}")

# Sử dụng hàm để điều chỉnh tệp net.xml
dataset_path = "./dataset/test 02"
osm_file = f"{dataset_path}/map.osm"
net_file = f"{dataset_path}/net.xml"

# Sử dụng hàm để chuyển đổi OSM sang net.xml
osm_to_net(osm_file, net_file)
adjust_net_xml(net_file)