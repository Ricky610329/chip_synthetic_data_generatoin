# analyze_layout.py (支援階層式群組顯示)

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import argparse
from collections import defaultdict

def visualize_and_analyze(data):
    layout_data = data['layout_data']
    params = data['generation_params']
    
    canvas_width = layout_data['canvas_width']
    canvas_height = layout_data['canvas_height']
    
    fig, ax = plt.subplots(1, figsize=(12, 12))
    ax.set_xlim(0, canvas_width)
    ax.set_ylim(canvas_height, 0) # 保持 Y 軸反轉
    ax.set_aspect('equal', adjustable='box')
    ax.set_title(f"Layout Visualization (Seed: {params.get('SEED', 'N/A')})")
    ax.grid(True, linestyle='--', alpha=0.5)

    all_rects = layout_data['rectangles']
    all_pins = layout_data.get('pins', [])
    all_edges = layout_data.get('edges', [])
    
    rects_map = {r['id']: r for r in all_rects}
    pins_map = {p['id']: p for p in all_pins}
    
    # ✨ 1. 修改顏色邏輯以區分三種類型
    print("繪製元件 (標準、對稱、對齊、階層)...")
    for r in all_rects:
        x, y, w, h = r['x'] - r['w']/2, r['y'] - r['h']/2, r['w'], r.get('h', r['w'])
        group_type = r.get('group_type')

        if group_type == 'hierarchical':
            face_color = '#E1BEE7'; edge_color = '#6A1B9A' # 紫色系
        elif group_type == 'aligned':
            face_color = '#FFECB3'; edge_color = '#FF8F00' # 橘黃色系
        elif group_type in ['vertical', 'horizontal', 'quad']:
            face_color = '#C8E6C9'; edge_color = '#2E7D32' # 綠色系
        else: # 標準元件
            is_macro = r['growth_prob'] >= params.get('MACRO_GROWTH_PROB_RANGE', [0.7, 0.9])[0]
            face_color = '#BBDEFB' if is_macro else '#E3F2FD'
            edge_color = '#0D47A1' # 藍色系

        rect_patch = patches.Rectangle((x, y), w, h, linewidth=1.5, edgecolor=edge_color, facecolor=face_color, alpha=0.8, zorder=2)
        ax.add_patch(rect_patch)
        ax.text(r['x'], r['y'], str(r['id']), ha='center', va='center', fontsize=6, color='black', zorder=5)

    # ✨ 2. 繪製所有群組內元件的 Pin
    print("繪製所有群組元件的引腳...")
    for pin in all_pins:
        parent_rect = rects_map.get(pin['parent_rect_id'])
        # 只要元件屬於任何一個群組，就繪製其 Pin
        if parent_rect and parent_rect.get('group_id') is not None:
            abs_pos = (parent_rect['x'] + pin['rel_pos'][0], parent_rect['y'] + pin['rel_pos'][1])
            pin_marker = patches.Circle(abs_pos, radius=2, color='black', zorder=4)
            ax.add_patch(pin_marker)

    # 繪製所有連線
    wirelengths = []
    if all_edges:
        print("繪製所有元件之間的連線...")
        for pin1_id, pin2_id in all_edges:
            pin1, pin2 = pins_map.get(pin1_id), pins_map.get(pin2_id)
            if not pin1 or not pin2: continue
            rect1, rect2 = rects_map[pin1['parent_rect_id']], rects_map[pin2['parent_rect_id']]
            pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
            pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])
            ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='gray', linewidth=0.5, alpha=0.6, zorder=3)
            wirelengths.append(abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1]))
    
    # ✨ 3. 更新圖例
    legend_patches = [
        patches.Patch(facecolor='#BBDEFB', edgecolor='#0D47A1', label='Standard Component'),
        patches.Patch(facecolor='#C8E6C9', edgecolor='#2E7D32', label='Symmetric Component'),
        patches.Patch(facecolor='#FFECB3', edgecolor='#FF8F00', label='Aligned Component'),
        patches.Patch(facecolor='#E1BEE7', edgecolor='#6A1B9A', label='Hierarchical Group Component')
    ]
    ax.legend(handles=legend_patches, loc='upper right', fontsize='small')
    
    # ... (統計分析部分保持不變) ...
    
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Visualize and analyze a generated layout JSON file.")
    parser.add_argument("json_file", type=str, help="Path to the layout JSON file.")
    args = parser.parse_args()
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        visualize_and_analyze(data)
    except FileNotFoundError:
        print(f"Error: File not found at {args.json_file}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {args.json_file}")