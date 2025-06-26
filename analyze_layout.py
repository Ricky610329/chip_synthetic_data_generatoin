# analyze_layout.py

import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import argparse
import random

def visualize_and_analyze(data):
    """將載入的 layout 資料視覺化並進行分析"""
    
    layout_data = data['layout_data']
    params = data['generation_params']
    
    canvas_width = layout_data['canvas_width']
    canvas_height = layout_data['canvas_height']
    
    # --- 視覺化 ---
    fig, ax = plt.subplots(1, figsize=(12, 12))
    ax.set_xlim(0, canvas_width)
    ax.set_ylim(0, canvas_height)
    ax.set_aspect('equal', adjustable='box')
    plt.title(f"Layout Visualization (Seed: {params.get('SEED', 'N/A')})")

    # 建立 ID 到 rect/pin 的映射，方便查找
    rects_map = {r['id']: r for r in layout_data['rectangles']}
    pins_map = {p['id']: p for p in layout_data['pins']}

    # 繪製元件
    for r in layout_data['rectangles']:
        x, y, w, h = r['x'] - r['w']/2, r['y'] - r['h']/2, r['w'], r['h']
        # 根據是否為 macro 給予不同顏色
        is_macro = r['growth_prob'] >= params['MACRO_GROWTH_PROB_RANGE'][0]
        face_color = 'skyblue' if is_macro else 'lightcoral'
        rect_patch = patches.Rectangle((x, y), w, h, linewidth=1.5, edgecolor='black', facecolor=face_color, alpha=0.8)
        ax.add_patch(rect_patch)
        ax.text(r['x'], r['y'], str(r['id']), ha='center', va='center', fontsize=6, color='black', 
                bbox=dict(facecolor='white', alpha=0.5, boxstyle='round,pad=0.1', ec='none'))

    # 繪製連線
    wirelengths = []
    if layout_data['edges']:
        for pin1_id, pin2_id in layout_data['edges']:
            pin1 = pins_map[pin1_id]
            pin2 = pins_map[pin2_id]
            
            rect1 = rects_map[pin1['parent_rect_id']]
            rect2 = rects_map[pin2['parent_rect_id']]

            pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
            pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])

            ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='red', linewidth=0.5, alpha=0.7, zorder=5)
            
            # 計算 L1 (Manhattan) distance
            l1_distance = abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])
            wirelengths.append(l1_distance)

    # --- 統計分析 ---
    print("\n" + "="*40)
    print("      Layout Analysis Report")
    print("="*40)
    print(f"  - Component Count: {len(layout_data['rectangles'])}")
    print(f"  - Pin Count: {len(layout_data['pins'])}")
    print(f"  - Connection (Edge) Count: {len(layout_data['edges'])}")
    print("-"*40)
    if wirelengths:
        print("  Wirelength (L1 Distance) Statistics:")
        print(f"  - Total Wirelength: {np.sum(wirelengths):.2f}")
        print(f"  - Average Wirelength: {np.mean(wirelengths):.2f}")
        print(f"  - Median Wirelength: {np.median(wirelengths):.2f}")
        print(f"  - Max Wirelength: {np.max(wirelengths):.2f}")
        print(f"  - Min Wirelength: {np.min(wirelengths):.2f}")
    else:
        print("  No wirelength data available.")
    print("="*40 + "\n")

    plt.grid(True, linestyle='--', alpha=0.6)
    plt.gca().invert_yaxis() # y軸反轉，使左上角為(0,0)，符合一般佈局習慣
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