# format_for_ml.py

import json
import os
import argparse
from tqdm import tqdm
import multiprocessing

def format_one_file(json_path):
    """
    讀取一個原始 layout JSON 檔案，將其轉換為模型所需的 p, q, target 格式。
    所有座標和尺寸都會被正規化。
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        layout_data = raw_data['layout_data']
        canvas_w = layout_data['canvas_width']
        canvas_h = layout_data['canvas_height']

        # --- 建立 ID 到索引的映射 ---
        # 確保節點順序是固定的
        rects = sorted(layout_data['rectangles'], key=lambda r: r['id'])
        rect_id_to_idx = {r['id']: i for i, r in enumerate(rects)}
        pins_map = {p['id']: p for p in layout_data['pins']}
        
        # --- 1. 產生 'p' (Node Features) ---
        # p_i = [normalized_width, normalized_height]
        p = [
            [r['w'] / canvas_w * 2, r['h'] / canvas_h * 2] for r in rects
        ]

        # --- 2. 產生 'target' (Target Placements) ---
        # target_i = [normalized_center_x, normalized_center_y] in [-1, 1]
        target = [
            [(r['x'] / canvas_w * 2) - 1, (r['y'] / canvas_h * 2) - 1] for r in rects
        ]

        # --- 3. 產生 'edge_index' 和 'q' (Edge Attributes) ---
        edge_index = []
        q = []
        for pin1_id, pin2_id in layout_data['edges']:
            pin1 = pins_map[pin1_id]
            pin2 = pins_map[pin2_id]
            
            src_node_idx = rect_id_to_idx[pin1['parent_rect_id']]
            dst_node_idx = rect_id_to_idx[pin2['parent_rect_id']]
            
            # 建立雙向邊
            edge_index.append([src_node_idx, dst_node_idx])
            edge_index.append([dst_node_idx, src_node_idx])

            # q_ij = [src_pin_rel_x, src_pin_rel_y, dst_pin_rel_x, dst_pin_rel_y]
            # 正規化引腳的相對位置
            q_forward = [
                pin1['rel_pos'][0] / canvas_w * 2, pin1['rel_pos'][1] / canvas_h * 2,
                pin2['rel_pos'][0] / canvas_w * 2, pin2['rel_pos'][1] / canvas_h * 2
            ]
            q_backward = [
                pin2['rel_pos'][0] / canvas_w * 2, pin2['rel_pos'][1] / canvas_h * 2,
                pin1['rel_pos'][0] / canvas_w * 2, pin1['rel_pos'][1] / canvas_h * 2
            ]
            q.append(q_forward)
            q.append(q_backward)

        formatted_data = {
            "p": p,
            "q": q,
            "edge_index": edge_index,
            "target": target
        }
        
        return os.path.basename(json_path), formatted_data

    except Exception as e:
        # 返回錯誤訊息，以便主進程可以收集
        return os.path.basename(json_path), f"Error: {e}"


def main():
    parser = argparse.ArgumentParser(description="Format raw layout JSONs into a clean, ML-ready JSON format.")
    parser.add_argument("input_dir", type=str, help="Directory containing the raw JSON files (e.g., 'dataset/').")
    parser.add_argument("output_dir", type=str, help="Directory to save the formatted JSON files (e.g., 'formatted_dataset/').")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    
    json_files = [os.path.join(args.input_dir, f) for f in os.listdir(args.input_dir) if f.endswith('.json')]
    
    print(f"Found {len(json_files)} raw JSON files. Starting formatting...")
    
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(format_one_file, json_files), total=len(json_files)))

    errors = []
    for filename, data in results:
        if isinstance(data, str): # 如果 data 是字串，代表是錯誤訊息
            errors.append((filename, data))
        else:
            output_path = os.path.join(args.output_dir, filename.replace('layout_', 'formatted_'))
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

    if errors:
        print(f"\nCompleted with {len(errors)} errors:")
        for fname, err in errors[:10]:
            print(f" - File: {fname}, Reason: {err}")
    else:
        print("\nFormatting successful with no errors!")

if __name__ == '__main__':
    main()