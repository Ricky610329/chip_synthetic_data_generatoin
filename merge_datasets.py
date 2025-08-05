# merge_datasets.py

import os
import shutil
import argparse
from tqdm import tqdm

def merge_datasets(dir1, dir2, output_dir):
    """
    合併兩個生成的資料集資料夾到一個新的輸出資料夾。

    Args:
        dir1 (str): 第一個資料來源資料夾的路徑。
        dir2 (str): 第二個資料來源資料夾的路徑。
        output_dir (str): 合併後要儲存的新資料夾路徑。
    """
    os.makedirs(output_dir, exist_ok=True)
    print(f"輸出資料夾 '{output_dir}' 已建立。")

    try:
        files1 = sorted([f for f in os.listdir(dir1) if f.startswith('layout_') and f.endswith('.json')])
        files2 = sorted([f for f in os.listdir(dir2) if f.startswith('layout_') and f.endswith('.json')])
        print(f"找到來源 A ('{dir1}') 中 {len(files1)} 個檔案。")
        print(f"找到來源 B ('{dir2}') 中 {len(files2)} 個檔案。")
    except FileNotFoundError as e:
        print(f"錯誤：找不到指定的資料夾。請檢查路徑是否正確。 {e}")
        return

    print(f"\n正在複製來源 A ('{dir1}') 的檔案...")
    for filename in tqdm(files1, desc="複製來源 A"):
        src_path = os.path.join(dir1, filename)
        dst_path = os.path.join(output_dir, filename)
        shutil.copy2(src_path, dst_path)
    
    current_files_in_output = [f for f in os.listdir(output_dir) if f.startswith('layout_') and f.endswith('.json')]
    start_index = 0
    if current_files_in_output:
        indices = [int(f.replace('layout_', '').replace('.json', '')) for f in current_files_in_output]
        start_index = max(indices)

    print(f"\n正在複製並重新編號來源 B ('{dir2}') 的檔案...")
    print(f"檔案將從索引 {start_index + 1} 開始編號。")
    
    for i, filename in enumerate(tqdm(files2, desc="複製並重新編號來源 B")):
        new_index = start_index + 1 + i
        new_filename = f"layout_{new_index}.json"
        
        src_path = os.path.join(dir2, filename)
        dst_path = os.path.join(output_dir, new_filename)
        shutil.copy2(src_path, dst_path)

    total_files = len(os.listdir(output_dir))
    print(f"\n合併完成！")
    print(f"新的資料夾 '{output_dir}' 中總共有 {total_files} 個檔案。")

def main():
    parser = argparse.ArgumentParser(description="Merge two generated layout datasets into one.")
    parser.add_argument("source_dir1", type=str, help="Path to the first source dataset directory.")
    parser.add_argument("source_dir2", type=str, help="Path to the second source dataset directory.")
    parser.add_argument("output_dir", type=str, help="Path to the new merged dataset directory.")
    args = parser.parse_args()

    merge_datasets(args.source_dir1, args.source_dir2, args.output_dir)

if __name__ == '__main__':
    main()