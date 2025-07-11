# format_for_ml.py (Corrected)

import json
import os
import argparse
from tqdm import tqdm
import multiprocessing
from collections import defaultdict

def format_one_file(json_path):
    """
    Reads a raw layout JSON, converts it to the model format, and saves restoration information.
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        layout = raw_data['layout_data']
        canvas_w, canvas_h = layout['canvas_width'], layout['canvas_height']
        
        rects_data = sorted(layout['rectangles'], key=lambda r: r['id'])
        pins_map = {p['id']: p for p in layout['pins']}
        rect_map = {r['id']: r for r in rects_data}

        # --- 1. Identify groups and define nodes ---
        grouped_rects = defaultdict(list)
        single_rects = []
        for r in rects_data:
            if r.get('group_id') and r['group_id'] is not None:
                grouped_rects[r['group_id']].append(r)
            else:
                single_rects.append(r)

        node_defs = []
        rect_id_to_node_idx = {}
        node_idx_counter = 0

        # Process grouped nodes
        for group_id, rects_in_group in grouped_rects.items():
            min_x = min(r['x'] - r['w']/2 for r in rects_in_group)
            max_x = max(r['x'] + r['w']/2 for r in rects_in_group)
            min_y = min(r['y'] - r['h']/2 for r in rects_in_group)
            max_y = max(r['y'] + r['h']/2 for r in rects_in_group)

            group_w, group_h = max_x - min_x, max_y - min_y
            group_center_x, group_center_y = min_x + group_w / 2, min_y + group_h / 2

            sub_components = []
            for r in rects_in_group:
                offset_x = r['x'] - group_center_x
                offset_y = r['y'] - group_center_y
                sub_components.append({
                    "offset": [offset_x, offset_y],
                    "dims": [r['w'], r['h']]
                })

            node_defs.append({
                'node_idx': node_idx_counter, 'center_x': group_center_x, 'center_y': group_center_y,
                'w': group_w, 'h': group_h, 'sub_components': sub_components
            })
            for r in rects_in_group:
                rect_id_to_node_idx[r['id']] = node_idx_counter
            node_idx_counter += 1

        # Process single-component nodes
        for r in single_rects:
            sub_components = [{"offset": [0, 0], "dims": [r['w'], r['h']]}]
            node_defs.append({
                'node_idx': node_idx_counter, 'center_x': r['x'], 'center_y': r['y'],
                'w': r['w'], 'h': r['h'], 'sub_components': sub_components
            })
            rect_id_to_node_idx[r['id']] = node_idx_counter
            node_idx_counter += 1
        
        node_idx_to_def = {n['node_idx']: n for n in node_defs}

        # --- 2. Generate p, target, etc. ---
        p = [[n['w'] / canvas_w * 2, n['h'] / canvas_h * 2] for n in node_defs]
        target = [[(n['center_x'] / canvas_w * 2) - 1, (n['center_y'] / canvas_h * 2) - 1] for n in node_defs]
        sub_components_list = [n['sub_components'] for n in node_defs]

        # --- 3. Generate edge_index, q ---
        edge_index, q = [], []
        for pin1_id, pin2_id in layout['edges']:
            pin1, pin2 = pins_map[pin1_id], pins_map[pin2_id]
            src_rect_id, dst_rect_id = pin1['parent_rect_id'], pin2['parent_rect_id']
            if src_rect_id == dst_rect_id: continue
            
            src_node_idx, dst_node_idx = rect_id_to_node_idx[src_rect_id], rect_id_to_node_idx[dst_rect_id]
            if src_node_idx == dst_node_idx: continue
            
            src_node_def, dst_node_def = node_idx_to_def[src_node_idx], node_idx_to_def[dst_node_idx]
            
            # ✨ FIX: Corrected typo from `dst_src_id` to `dst_rect_id`
            pin1_rect, pin2_rect = rect_map[src_rect_id], rect_map[dst_rect_id]

            pin1_abs_x, pin1_abs_y = pin1_rect['x'] + pin1['rel_pos'][0], pin1_rect['y'] + pin1['rel_pos'][1]
            pin2_abs_x, pin2_abs_y = pin2_rect['x'] + pin2['rel_pos'][0], pin2_rect['y'] + pin2['rel_pos'][1]
            
            pin1_rel_to_node_x, pin1_rel_to_node_y = pin1_abs_x - src_node_def['center_x'], pin1_abs_y - src_node_def['center_y']
            pin2_rel_to_node_x, pin2_rel_to_node_y = pin2_abs_x - dst_node_def['center_x'], pin2_abs_y - dst_node_def['center_y']
            
            q_forward = [pin1_rel_to_node_x/canvas_w*2, pin1_rel_to_node_y/canvas_h*2, pin2_rel_to_node_x/canvas_w*2, pin2_rel_to_node_y/canvas_h*2]
            q_backward = [pin2_rel_to_node_x/canvas_w*2, pin2_rel_to_node_y/canvas_h*2, pin1_rel_to_node_x/canvas_w*2, pin1_rel_to_node_y/canvas_h*2]
            
            edge_index.extend([[src_node_idx, dst_node_idx], [dst_node_idx, src_node_idx]])
            q.extend([q_forward, q_backward])

        return os.path.basename(json_path), {
            "p": p, "q": q, "edge_index": edge_index, "target": target,
            "sub_components": sub_components_list
        }

    except Exception as e:
        return os.path.basename(json_path), f"Error processing file: {e}"

def main():
    parser = argparse.ArgumentParser(description="Format raw layout JSONs into a clean, ML-ready JSON format, abstracting symmetric groups.")
    parser.add_argument("input_dir", type=str, help="Directory containing the raw JSON files.")
    parser.add_argument("output_dir", type=str, help="Directory to save the formatted JSON files.")
    args = parser.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    json_files = [os.path.join(args.input_dir, f) for f in os.listdir(args.input_dir) if f.endswith('.json')]
    print(f"Found {len(json_files)} raw JSON files. Starting formatting with group abstraction...")
    with multiprocessing.Pool(processes=multiprocessing.cpu_count()) as pool:
        results = list(tqdm(pool.imap_unordered(format_one_file, json_files), total=len(json_files)))
    errors = []
    for filename, data in results:
        if isinstance(data, str):
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