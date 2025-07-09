# analyze_layout.py (最終視覺化修正版)

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
    
    fig, ax = plt.subplots(1, figsize=(12, 12))
    ax.set_xlim(0, canvas_width)
    ax.set_ylim(0, canvas_height)
    ax.set_aspect('equal', adjustable='box')
    plt.title(f"Layout Visualization (Seed: {params.get('SEED', 'N/A')})")

    all_rects = layout_data['rectangles']
    all_pins = layout_data.get('pins', [])
    all_edges = layout_data.get('edges', [])
    
    rects_map = {r['id']: r for r in all_rects}
    pins_map = {p['id']: p for p in all_pins}
    
    # 建立一個集合，存放所有固定(對稱)元件的 ID，方便快速查詢
    fixed_rect_ids = {r['id'] for r in all_rects if r.get('fixed', False)}

    # --- 繪製元件 ---
    for r in all_rects:
        x, y, w, h = r['x'] - r['w']/2, r['y'] - r['h']/2, r['w'], r.get('h', r['w'])
        
        if r.get('fixed', False):
            # 固定的對稱元件使用綠色
            face_color = 'mediumseagreen'; edge_color = 'darkgreen'
        else:
            # 可變的隨機元件使用原來的顏色
            is_macro = r['growth_prob'] >= params['MACRO_GROWTH_PROB_RANGE'][0]
            face_color = 'skyblue' if is_macro else 'lightcoral'
            edge_color = 'black'

        rect_patch = patches.Rectangle((x, y), w, h, linewidth=1, edgecolor=edge_color, facecolor=face_color, alpha=0.7)
        ax.add_patch(rect_patch)
        ax.text(r['x'], r['y'], str(r['id']), ha='center', va='center', fontsize=6, color='white', 
                bbox=dict(facecolor='black', alpha=0.4, boxstyle='round,pad=0.1', ec='none'))

    # --- 只繪製對稱元件的 Pin ---
    print("繪製對稱元件的引腳...")
    for pin in all_pins:
        # 檢查 Pin 的父元件是否為對稱元件
        if pin['parent_rect_id'] in fixed_rect_ids:
            parent_rect = rects_map[pin['parent_rect_id']]
            abs_pos = (parent_rect['x'] + pin['rel_pos'][0], parent_rect['y'] + pin['rel_pos'][1])
            # 繪製一個黑色小圓點代表 Pin
            pin_marker = patches.Circle(abs_pos, radius=2, color='black', zorder=10)
            ax.add_patch(pin_marker)

    # --- MODIFICATION: 繪製【所有】連線，但使用灰色以降低視覺權重 ---
    wirelengths = []
    if all_edges:
        print("繪製所有元件之間的連線...")
        for pin1_id, pin2_id in all_edges:
            pin1 = pins_map.get(pin1_id)
            pin2 = pins_map.get(pin2_id)
            if not pin1 or not pin2: continue

            rect1 = rects_map[pin1['parent_rect_id']]
            rect2 = rects_map[pin2['parent_rect_id']]
            pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
            pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])
            
            # 使用灰色來繪製所有連線
            ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='gray', linewidth=0.5, alpha=0.6, zorder=5)
            wirelengths.append(abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1]))
    
    # ... (其餘統計分析部分保持不變)
    print("\n" + "="*40)
    print("      Layout Analysis Report")
    print("="*40)
    # ...
    
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.gca().invert_yaxis()
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