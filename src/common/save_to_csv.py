# save_to_csv.py
import csv

def save_to_csv(file_path, fieldnames, records):
    """
    Hàm lưu dữ liệu vào file CSV.

    Parameters:
    - file_path (str): Đường dẫn và tên file CSV cần lưu.
    - fieldnames (list): Danh sách các tên cột (headers) cho file CSV.
    - records (list of dict): Danh sách các bản ghi, mỗi bản ghi là một dictionary tương ứng với một dòng trong file CSV.

    Returns:
    - None
    """
    # Mở file ở chế độ ghi ('w') và đảm bảo encoding UTF-8
    with open(file_path, mode='w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()   # Ghi dòng header (tên cột)
        writer.writerows(records)  # Ghi tất cả các bản ghi
