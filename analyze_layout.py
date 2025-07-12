# analyze_layout.py (已更新，可顯示 Pins 和 Netlist Edges)

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
    ax.set_ylim(canvas_height, 0) # 保持 Y 軸反轉
    ax.set_aspect('equal', adjustable='box')
    ax.set_title(f"Layout Visualization with Pins & Edges (Seed: {params.get('SEED', 'N/A')})")
    ax.grid(True, linestyle='--', alpha=0.5)

    all_rects = layout_data['rectangles']
    all_pins = layout_data.get('pins', [])
    all_edges = layout_data.get('netlist_edges', [])
    
    # 建立 ID 到物件的對應，方便快速尋找
    rects_map = {r['id']: r for r in all_rects}
    pins_map = {p['id']: p for p in all_pins}
    
    print("繪製元件 (Macros, Std Cells, Groups)...")
    for r in all_rects:
        x, y, w, h = r['x'] - r['w']/2, r['y'] - r['h']/2, r['w'], r.get('h', r['w'])
        group_type = r.get('group_type')
        component_type = r.get('component_type')

        if group_type == 'hierarchical':
            face_color, edge_color = '#E1BEE7', '#6A1B9A'
        elif group_type == 'aligned':
            face_color, edge_color = '#FFECB3', '#FF8F00'
        elif group_type in ['vertical', 'horizontal', 'quad']:
            face_color, edge_color = '#C8E6C9', '#2E7D32'
        elif component_type == 'macro':
            face_color, edge_color = '#2196F3', '#0D47A1'
        elif component_type == 'std_cell':
            face_color, edge_color = '#BBDEFB', '#42A5F5'
        else:
            face_color, edge_color = '#CFD8DC', '#37474F'

        rect_patch = patches.Rectangle((x, y), w, h, linewidth=1.5, edgecolor=edge_color, facecolor=face_color, alpha=0.9, zorder=2)
        ax.add_patch(rect_patch)
        ax.text(r['x'], r['y'], str(r['id']), ha='center', va='center', fontsize=7, color='black', zorder=5)

    # ==========================================================
    # ✨ 1. 新增：繪製所有引腳 (Pins) ✨
    # ==========================================================
    # 這會自動包含對稱元件（綠色）和其他類型元件上的引腳
    print(f"繪製 {len(all_pins)} 個引腳...")
    for pin in all_pins:
        parent_rect = rects_map.get(pin['parent_rect_id'])
        if not parent_rect: continue
        
        # 計算引腳在畫布上的絕對座標
        abs_pos = (parent_rect['x'] + pin['rel_pos'][0], parent_rect['y'] + pin['rel_pos'][1])
        # 繪製一個小黑點代表引腳
        pin_marker = patches.Circle(abs_pos, radius=2.5, color='black', zorder=4)
        ax.add_patch(pin_marker)

    # ==========================================================
    # ✨ 2. 新增：繪製 Netlist 連線 (Basic Edges) ✨
    # ==========================================================
    print(f"繪製 {len(all_edges)} 條 Netlist 連線...")
    for pin1_id, pin2_id in all_edges:
        pin1 = pins_map.get(pin1_id)
        pin2 = pins_map.get(pin2_id)
        
        if not pin1 or not pin2: continue
        
        rect1 = rects_map.get(pin1['parent_rect_id'])
        rect2 = rects_map.get(pin2['parent_rect_id'])
        
        if not rect1 or not rect2: continue
            
        # 計算兩個引腳的絕對座標
        pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
        pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])
        
        # 在兩個引腳之間繪製一條線
        ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='gray', linewidth=0.6, alpha=0.7, zorder=3)

    # (可選) 繪製對齊約束線 (保持不變)
    for id1, id2, align_type in layout_data.get('alignment_constraints', []):
        r1, r2 = rects_map.get(id1), rects_map.get(id2)
        if r1 and r2:
            ax.plot([r1['x'], r2['x']], [r1['y'], r2['y']], color='#FF8F00', linestyle=':', linewidth=1.0, alpha=0.7, zorder=3)

    # 更新圖例 (保持不變)
    legend_patches = [
        patches.Patch(facecolor='#2196F3', edgecolor='#0D47A1', label='Macro'),
        patches.Patch(facecolor='#BBDEFB', edgecolor='#42A5F5', label='Standard Cell'),
        patches.Patch(facecolor='#C8E6C9', edgecolor='#2E7D32', label='Symmetric Group'),
        patches.Patch(facecolor='#FFECB3', edgecolor='#FF8F00', label='Aligned Group'),
        patches.Patch(facecolor='#E1BEE7', edgecolor='#6A1B9A', label='Hierarchical Group')
    ]
    ax.legend(handles=legend_patches, loc='upper right', fontsize='medium')
    
    plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Visualize and analyze a generated layout JSON file with full constraints, pins, and edges.")
    parser.add_argument("json_file", type=str, help="Path to the raw layout JSON file (from 'raw_layouts_with_constraints' dir).")
    args = parser.parse_args()
    try:
        with open(args.json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        visualize_and_analyze(data)
    except FileNotFoundError:
        print(f"Error: File not found at {args.json_file}")
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {args.json_file}")