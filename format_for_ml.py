# format_for_ml.py

import json
import os
import argparse
from tqdm import tqdm
import multiprocessing
from collections import defaultdict

def get_node_definition(rects_in_node, node_idx):
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
        sub_components.append({ "offset": [offset_x, offset_y], "dims": [r['w'], r['h']] })
        
    return {
        'node_idx': node_idx, 'center_x': node_center_x, 'center_y': node_center_y,
        'w': node_w, 'h': node_h, 'sub_components': sub_components,
        'contained_rect_ids': [r['id'] for r in rects_in_node]
    }

def format_one_file(json_path):
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        layout = raw_data['layout_data']
        canvas_w, canvas_h = layout['canvas_width'], layout['canvas_height']
        
        rects_data = sorted(layout['rectangles'], key=lambda r: r['id'])
        rect_map = {r['id']: r for r in rects_data}
        pins_map = {p['id']: p for p in layout.get('pins', [])}

        # 節點抽象化 (Node Abstraction)
        node_defs = []
        rect_id_to_node_idx = {}
        node_idx_counter = 0
        
        processed_rect_ids = set()

        # 建立約束 ID 到矩形列表的對應
        constraint_map = defaultdict(lambda: defaultdict(list))
        for r in rects_data:
            for c_type, c_id in r.get('constraints', {}).items():
                 constraint_map[c_type][c_id].append(r)
        
        # 優先處理對稱群組
        if 'symmetry_id' in constraint_map:
            for sym_id, rects_in_group in constraint_map['symmetry_id'].items():
                node_def = get_node_definition(rects_in_group, node_idx_counter)
                node_defs.append(node_def)
                for r_id in node_def['contained_rect_ids']:
                    rect_id_to_node_idx[r_id] = node_idx_counter
                    processed_rect_ids.add(r_id)
                node_idx_counter += 1

        # 處理剩餘的對齊群組
        if 'alignment_id' in constraint_map:
            for align_id, rects_in_group in constraint_map['alignment_id'].items():
                unprocessed_rects = [r for r in rects_in_group if r['id'] not in processed_rect_ids]
                if not unprocessed_rects: continue
                node_def = get_node_definition(unprocessed_rects, node_idx_counter)
                node_defs.append(node_def)
                for r_id in node_def['contained_rect_ids']:
                    rect_id_to_node_idx[r_id] = node_idx_counter
                    processed_rect_ids.add(r_id)
                node_idx_counter += 1
        
        # 處理剩餘的階層群組
        if 'grouping_id' in constraint_map:
            for group_id, rects_in_group in constraint_map['grouping_id'].items():
                unprocessed_rects = [r for r in rects_in_group if r['id'] not in processed_rect_ids]
                if not unprocessed_rects: continue
                node_def = get_node_definition(unprocessed_rects, node_idx_counter)
                node_defs.append(node_def)
                for r_id in node_def['contained_rect_ids']:
                    rect_id_to_node_idx[r_id] = node_idx_counter
                    processed_rect_ids.add(r_id)
                node_idx_counter += 1

        # 處理所有剩餘的單一元件
        for r in rects_data:
            if r['id'] not in processed_rect_ids:
                node_def = get_node_definition([r], node_idx_counter)
                node_defs.append(node_def)
                rect_id_to_node_idx[r['id']] = node_idx_counter
                node_idx_counter += 1

        node_idx_to_def = {n['node_idx']: n for n in node_defs}

        p = [[n['w'] / canvas_w, n['h'] / canvas_h] for n in node_defs]
        target = [[(n['center_x'] / canvas_w * 2) - 1, (n['center_y'] / canvas_h * 2) - 1] for n in node_defs]
        sub_components_list = [n['sub_components'] for n in node_defs]
        
        netlist_edges, alignment_edges, group_edges = [], [], []

        for pin1_id, pin2_id in layout.get('netlist_edges', []):
            pin1, pin2 = pins_map.get(pin1_id), pins_map.get(pin2_id)
            if not pin1 or not pin2: continue
            src_rect_id, dst_rect_id = pin1['parent_rect_id'], pin2['parent_rect_id']
            if src_rect_id == dst_rect_id: continue
            src_node_idx, dst_node_idx = rect_id_to_node_idx.get(src_rect_id), rect_id_to_node_idx.get(dst_rect_id)
            if src_node_idx is None or dst_node_idx is None or src_node_idx == dst_node_idx: continue
            src_node_def, dst_node_def = node_idx_to_def[src_node_idx], node_idx_to_def[dst_node_idx]
            src_rect, dst_rect = rect_map[src_rect_id], rect_map[dst_rect_id]
            pin1_abs_x, pin1_abs_y = src_rect['x'] + pin1['rel_pos'][0], src_rect['y'] + pin1['rel_pos'][1]
            pin2_abs_x, pin2_abs_y = dst_rect['x'] + pin2['rel_pos'][0], dst_rect['y'] + pin2['rel_pos'][1]
            sx, sy = (pin1_abs_x - src_node_def['center_x']) / canvas_w, (pin1_abs_y - src_node_def['center_y']) / canvas_h
            dx, dy = (pin2_abs_x - dst_node_def['center_x']) / canvas_w, (pin2_abs_y - dst_node_def['center_y']) / canvas_h
            netlist_edges.append([[src_node_idx, dst_node_idx], [sx, sy, dx, dy]])
            netlist_edges.append([[dst_node_idx, src_node_idx], [dx, dy, sx, sy]])

        align_map = {"left": 0, "right": 1, "top": 2, "bottom": 3, "h_center": 4, "v_center": 5}
        for id1, id2, align_type in layout.get('alignment_constraints', []):
            node1_idx, node2_idx = rect_id_to_node_idx.get(id1), rect_id_to_node_idx.get(id2)
            if node1_idx is None or node2_idx is None or node1_idx == node2_idx: continue
            feature_vec = [0] * len(align_map)
            if align_type in align_map: feature_vec[align_map[align_type]] = 1
            alignment_edges.append([[node1_idx, node2_idx], feature_vec])
            alignment_edges.append([[node2_idx, node1_idx], feature_vec])

        for group in layout.get('hierarchical_group_constraints', []):
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    id1, id2 = group[i], group[j]
                    node1_idx, node2_idx = rect_id_to_node_idx.get(id1), rect_id_to_node_idx.get(id2)
                    if node1_idx is None or node2_idx is None or node1_idx == node2_idx: continue
                    group_edges.append([[node1_idx, node2_idx], [1]])
                    group_edges.append([[node2_idx, node1_idx], [1]])

        return os.path.basename(json_path), {
            "nodes": {"p": p, "sub_components": sub_components_list},
            "edges": { "basic_component_edge": netlist_edges, "align_edge": alignment_edges, "group_edge": group_edges },
            "target": target
        }
    except Exception as e:
        import traceback
        return os.path.basename(json_path), f"Error: {e}\n{traceback.format_exc()}"

def main():
    parser = argparse.ArgumentParser(description="Format raw layout JSONs into a clean, ML-ready JSON format.")
    parser.add_argument("input_dir", type=str, help="Directory containing the raw layout JSON files.")
    parser.add_argument("output_dir", type=str, help="Directory to save the formatted ML-ready JSON files.")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    json_files = [os.path.join(args.input_dir, f) for f in os.listdir(args.input_dir) if f.endswith('.json')]
    
    print(f"找到 {len(json_files)} 個原始佈局檔案。開始轉換為 ML 格式...")
    
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(format_one_file, json_files), total=len(json_files)))
        
    for filename, data in results:
        if isinstance(data, str):
            print(f"--- 檔案: {filename} ---\n{data}\n--------------------")
        else:
            output_path = os.path.join(args.output_dir, filename.replace('layout_', 'ml_formatted_'))
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

if __name__ == '__main__':
    main()