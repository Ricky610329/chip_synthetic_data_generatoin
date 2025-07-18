# analyze_layout.py

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import argparse

def visualize_and_analyze(data):
    layout_data = data['layout_data']
    params = data['generation_params']
    
    canvas_width = layout_data['canvas_width']
    canvas_height = layout_data['canvas_height']
    
    fig, ax = plt.subplots(1, figsize=(14, 14))
    ax.set_xlim(0, canvas_width)
    ax.set_ylim(canvas_height, 0)
    ax.set_aspect('equal', adjustable='box')
    ax.set_title(f"Layout Visualization (Seed: {params.get('SEED', 'N/A')})")
    ax.grid(True, linestyle='--', alpha=0.5)

    all_rects = layout_data['rectangles']
    all_pins = layout_data.get('pins', [])
    all_edges = layout_data.get('netlist_edges', [])
    
    rects_map = {r['id']: r for r in all_rects}
    pins_map = {p['id']: p for p in all_pins}
    
    print("繪製元件...")
    for r_data in all_rects:
        x, y, w, h = r_data['x'] - r_data['w']/2, r_data['y'] - r_data['h']/2, r_data['w'], r_data.get('h', r_data['w'])
        constraints = r_data.get('constraints', {})
        component_type = r_data.get('component_type')

        # 新的著色邏輯，帶有優先級
        if 'grouping_id' in constraints:
            face_color, edge_color = '#E1BEE7', '#6A1B9A' # 紫色系 (階層優先級最高)
        elif 'symmetry_id' in constraints:
            face_color, edge_color = '#C8E6C9', '#2E7D32' # 綠色系 (對稱)
        elif 'alignment_id' in constraints:
            face_color, edge_color = '#FFECB3', '#FF8F00' # 橘黃色系 (對齊)
        elif component_type == 'macro':
            face_color, edge_color = '#2196F3', '#0D47A1' # 深藍色系 (Macro)
        elif component_type == 'std_cell':
            face_color, edge_color = '#BBDEFB', '#42A5F5' # 淺藍色系 (Std Cell)
        else:
            face_color, edge_color = '#CFD8DC', '#37474F' # 灰色系

        rect_patch = patches.Rectangle((x, y), w, h, linewidth=1.5, edgecolor=edge_color, facecolor=face_color, alpha=0.9, zorder=2)
        ax.add_patch(rect_patch)
        ax.text(r_data['x'], r_data['y'], str(r_data['id']), ha='center', va='center', fontsize=7, color='black', zorder=5)

    print(f"繪製 {len(all_pins)} 個引腳...")
    for pin in all_pins:
        parent_rect = rects_map.get(pin['parent_rect_id'])
        if not parent_rect: continue
        abs_pos = (parent_rect['x'] + pin['rel_pos'][0], parent_rect['y'] + pin['rel_pos'][1])
        pin_marker = patches.Circle(abs_pos, radius=2.5, color='black', zorder=4)
        ax.add_patch(pin_marker)

    print(f"繪製 {len(all_edges)} 條 Netlist 連線...")
    for pin1_id, pin2_id in all_edges:
        pin1, pin2 = pins_map.get(pin1_id), pins_map.get(pin2_id)
        if not pin1 or not pin2: continue
        rect1, rect2 = rects_map.get(pin1['parent_rect_id']), rects_map.get(pin2['parent_rect_id'])
        if not rect1 or not rect2: continue
        pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
        pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])
        ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='gray', linewidth=0.6, alpha=0.7, zorder=3)

    legend_patches = [
        patches.Patch(facecolor='#2196F3', edgecolor='#0D47A1', label='Macro'),
        patches.Patch(facecolor='#BBDEFB', edgecolor='#42A5F5', label='Standard Cell'),
        patches.Patch(facecolor='#C8E6C9', edgecolor='#2E7D32', label='Symmetric'),
        patches.Patch(facecolor='#FFECB3', edgecolor='#FF8F00', label='Aligned'),
        patches.Patch(facecolor='#E1BEE7', edgecolor='#6A1B9A', label='Hierarchical Group')
    ]
    ax.legend(handles=legend_patches, loc='upper right', fontsize='medium')
    
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Visualize a generated layout JSON file.")
    parser.add_argument("json_file", type=str, help="Path to the raw layout JSON file.")
    args = parser.parse_args()
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        visualize_and_analyze(data)
    except FileNotFoundError:
        print(f"Error: File not found at {args.json_file}")