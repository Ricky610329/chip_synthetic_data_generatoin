# format_for_ml.py (完全重構以滿足新的ML格式需求)

import json
import os
import argparse
from tqdm import tqdm
import multiprocessing
from collections import defaultdict
import numpy as np

def get_node_definition(rects_in_node, node_idx):
    """根據一組矩形計算抽象節點的屬性。"""
    min_x = min(r['x'] - r['w']/2 for r in rects_in_node)
    max_x = max(r['x'] + r['w']/2 for r in rects_in_node)
    min_y = min(r['y'] - r['h']/2 for r in rects_in_node)
    max_y = max(r['y'] + r['h']/2 for r in rects_in_node)

    node_w, node_h = max_x - min_x, max_y - min_y
    node_center_x, node_center_y = min_x + node_w / 2, min_y + node_h / 2
    
    sub_components = []
    for r in rects_in_node:
        offset_x = r['x'] - node_center_x
        offset_y = r['y'] - node_center_y
        sub_components.append({
            "offset": [offset_x, offset_y],
            "dims": [r['w'], r['h']]
        })
        
    return {
        'node_idx': node_idx, 'center_x': node_center_x, 'center_y': node_center_y,
        'w': node_w, 'h': node_h, 'sub_components': sub_components,
        'contained_rect_ids': [r['id'] for r in rects_in_node]
    }

def format_one_file(json_path):
    """
    讀取一個原始佈局 JSON，將其轉換為模型格式。
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        layout = raw_data['layout_data']
        canvas_w, canvas_h = layout['canvas_width'], layout['canvas_height']
        
        rects_data = sorted(layout['rectangles'], key=lambda r: r['id'])
        rect_map = {r['id']: r for r in rects_data}
        pins_map = {p['id']: p for p in layout.get('pins', [])}

        # --- 1. 節點抽象化 (Node Abstraction) ---
        # 將所有 group_id 相同的矩形視為一個節點
        grouped_rects = defaultdict(list)
        single_rects = []
        # 以 group_id 將所有矩形分桶
        for r in rects_data:
            if r.get('group_id'):
                grouped_rects[r['group_id']].append(r)
            else:
                single_rects.append(r)

        node_defs = []
        rect_id_to_node_idx = {}
        node_idx_counter = 0

        # 處理成組的節點 (對稱, 對齊, 階層)
        for group_id, rects_in_group in grouped_rects.items():
            node_def = get_node_definition(rects_in_group, node_idx_counter)
            node_defs.append(node_def)
            for r_id in node_def['contained_rect_ids']:
                rect_id_to_node_idx[r_id] = node_idx_counter
            node_idx_counter += 1

        # 處理單一元件節點
        for r in single_rects:
            node_def = get_node_definition([r], node_idx_counter)
            node_defs.append(node_def)
            rect_id_to_node_idx[r['id']] = node_idx_counter
            node_idx_counter += 1
        
        node_idx_to_def = {n['node_idx']: n for n in node_defs}

        # --- 2. 準備節點特徵 (p) 和目標位置 (target) ---
        # p: [w, h] - 節點的尺寸 (正規化)
        p = [[n['w'] / canvas_w, n['h'] / canvas_h] for n in node_defs]
        # target: [x, y] - 節點的中心位置 (正規化到 [-1, 1])
        target = [[(n['center_x'] / canvas_w * 2) - 1, (n['center_y'] / canvas_h * 2) - 1] for n in node_defs]
        # sub_components: 用於後續恢復佈局
        sub_components_list = [n['sub_components'] for n in node_defs]
        
        # --- 3. 生成三種類型的邊 ---
        netlist_edges = []
        alignment_edges = []
        group_edges = []

        # 3.1 basic_component_edge (Netlist)
        # 特徵: [sx, sy, dx, dy] - pin 相對於其節點中心的相對位置 (正規化)
        for pin1_id, pin2_id in layout.get('netlist_edges', []):
            pin1, pin2 = pins_map.get(pin1_id), pins_map.get(pin2_id)
            if not pin1 or not pin2: continue
            
            src_rect_id, dst_rect_id = pin1['parent_rect_id'], pin2['parent_rect_id']
            if src_rect_id == dst_rect_id: continue

            src_node_idx = rect_id_to_node_idx.get(src_rect_id)
            dst_node_idx = rect_id_to_node_idx.get(dst_rect_id)
            if src_node_idx is None or dst_node_idx is None or src_node_idx == dst_node_idx: continue

            src_node_def, dst_node_def = node_idx_to_def[src_node_idx], node_idx_to_def[dst_node_idx]
            src_rect, dst_rect = rect_map[src_rect_id], rect_map[dst_rect_id]
            
            pin1_abs_x, pin1_abs_y = src_rect['x'] + pin1['rel_pos'][0], src_rect['y'] + pin1['rel_pos'][1]
            pin2_abs_x, pin2_abs_y = dst_rect['x'] + pin2['rel_pos'][0], dst_rect['y'] + pin2['rel_pos'][1]
            
            # 計算 pin 相對於其所屬「節點」中心的偏移
            sx = (pin1_abs_x - src_node_def['center_x']) / canvas_w
            sy = (pin1_abs_y - src_node_def['center_y']) / canvas_h
            dx = (pin2_abs_x - dst_node_def['center_x']) / canvas_w
            dy = (pin2_abs_y - dst_node_def['center_y']) / canvas_h
            
            netlist_edges.append([[src_node_idx, dst_node_idx], [sx, sy, dx, dy]])
            # 通常邊是雙向的
            netlist_edges.append([[dst_node_idx, src_node_idx], [dx, dy, sx, sy]])

        # 3.2 align_edge
        # 特徵: [left, right, top, bottom, h_center, v_center] - one-hot 編碼
        align_map = {"left": 0, "right": 1, "top": 2, "bottom": 3, "h_center": 4, "v_center": 5}
        for id1, id2, align_type in layout.get('alignment_constraints', []):
            node1_idx = rect_id_to_node_idx.get(id1)
            node2_idx = rect_id_to_node_idx.get(id2)
            if node1_idx is None or node2_idx is None or node1_idx == node2_idx: continue

            feature_vec = [0] * len(align_map)
            if align_type in align_map:
                feature_vec[align_map[align_type]] = 1
            
            alignment_edges.append([[node1_idx, node2_idx], feature_vec])
            alignment_edges.append([[node2_idx, node1_idx], feature_vec]) # 對齊關係是對稱的

        # 3.3 group_edge
        # 特徵: [1] - 表示同屬一個階層群組
        for group in layout.get('hierarchical_group_constraints', []):
            # 建立群組內所有節點對之間的邊
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    id1, id2 = group[i], group[j]
                    node1_idx = rect_id_to_node_idx.get(id1)
                    node2_idx = rect_id_to_node_idx.get(id2)
                    if node1_idx is None or node2_idx is None or node1_idx == node2_idx: continue
                    
                    group_edges.append([[node1_idx, node2_idx], [1]])
                    group_edges.append([[node2_idx, node1_idx], [1]])

        return os.path.basename(json_path), {
            "nodes": {"p": p, "sub_components": sub_components_list},
            "edges": {
                "basic_component_edge": netlist_edges,
                "align_edge": alignment_edges,
                "group_edge": group_edges,
            },
            "target": target
        }

    except Exception as e:
        import traceback
        return os.path.basename(json_path), f"Error: {e}\n{traceback.format_exc()}"

def main():
    parser = argparse.ArgumentParser(description="Format raw layout JSONs into a clean, ML-ready JSON format with multiple edge types.")
    parser.add_argument("input_dir", type=str, help="Directory containing the raw layout JSON files (e.g., 'raw_layouts_with_constraints').")
    parser.add_argument("output_dir", type=str, help="Directory to save the formatted ML-ready JSON files (e.g., 'dataset_ml_ready').")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    json_files = [os.path.join(args.input_dir, f) for f in os.listdir(args.input_dir) if f.endswith('.json')]
    
    print(f"找到 {len(json_files)} 個原始佈局檔案。開始轉換為 ML 格式...")
    
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(format_one_file, json_files), total=len(json_files)))
        
    errors = []
    for filename, data in results:
        if isinstance(data, str):
            errors.append((filename, data))
        else:
            output_path = os.path.join(args.output_dir, filename.replace('layout_', 'ml_formatted_'))
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2) # 使用 indent=2 提高可讀性
                
    if errors:
        print(f"\n轉換完成，但有 {len(errors)} 個錯誤:")
        # 只顯示前 5 個錯誤的詳細資訊
        for fname, err in errors[:5]:
            print(f"--- 檔案: {fname} ---\n{err}\n--------------------")
    else:
        print("\n格式轉換成功，沒有錯誤！")

if __name__ == '__main__':
    main()