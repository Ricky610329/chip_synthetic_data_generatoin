# visualize_abstraction.py (圖層修正版)

import json
import argparse
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def load_json_data(file_path):
    """安全地載入 JSON 檔案"""
    if not os.path.exists(file_path):
        print(f"錯誤：找不到檔案 {file_path}")
        exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def draw_rects_and_pins(ax, rects, pins, title):
    """在給定的 axis 上繪製詳細的元件與引腳"""
    ax.set_title(title, fontsize=14)
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)

    # 繪製元件
    for r in rects:
        is_symmetric = r.get('group_id') is not None
        face_color = '#FFDDC1' if is_symmetric else '#DAE8FC'
        edge_color = '#E57373' if is_symmetric else '#6C8EBF'
        
        rect_patch = patches.Rectangle(
            (r['x'] - r['w'] / 2, r['y'] - r['h'] / 2),
            r['w'], r['h'],
            linewidth=1.5,
            edgecolor=edge_color,
            facecolor=face_color,
            zorder=2  # <<< MODIFIED: 設定元件圖層為 2
        )
        ax.add_patch(rect_patch)
        ax.text(r['x'], r['y'], str(r['id']), ha='center', va='center', fontsize=6, zorder=5) # <<< MODIFIED: 文字在最上層

    # 繪製引腳
    rect_map = {r['id']: r for r in rects}
    for pin in pins:
        parent_rect = rect_map.get(pin['parent_rect_id'])
        if parent_rect:
            abs_x = parent_rect['x'] + pin['rel_pos'][0]
            abs_y = parent_rect['y'] + pin['rel_pos'][1]
            ax.plot(abs_x, abs_y, 'k.', markersize=3, zorder=4) # <<< MODIFIED: 引腳在連線之上

def draw_nets(ax, pins, edges, rects):
    """繪製引腳之間的連線"""
    pin_map = {p['id']: p for p in pins}
    rect_map = {r['id']: r for r in rects}

    for pin1_id, pin2_id in edges:
        pin1, pin2 = pin_map.get(pin1_id), pin_map.get(pin2_id)
        if not pin1 or not pin2: continue
        
        rect1, rect2 = rect_map.get(pin1['parent_rect_id']), rect_map.get(pin2['parent_rect_id'])
        if not rect1 or not rect2: continue

        pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
        pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])
        
        # <<< MODIFIED: 提高連線的圖層順序，使其在元件之上 >>>
        ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='r', alpha=0.4, linewidth=0.6, zorder=3)


def draw_abstracted_view(ax, rects_data, pins, edges):
    """繪製模型眼中的抽象化視圖"""
    ax.set_title("Abstracted View (For ML Model)", fontsize=14)
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)

    # 重新實現 format_for_ml.py 的核心邏輯來找到節點
    grouped_rects = defaultdict(list)
    single_rects = []
    for r in rects_data:
        if r.get('group_id'):
            grouped_rects[r['group_id']].append(r)
        else:
            single_rects.append(r)

    # 繪製代表單一元件的節點
    draw_rects_and_pins(ax, single_rects, [], "temp")

    # 繪製代表對稱群組的節點 (虛線邊界框)
    for group_id, rects_in_group in grouped_rects.items():
        min_x = min(r['x'] - r['w']/2 for r in rects_in_group)
        max_x = max(r['x'] + r['w']/2 for r in rects_in_group)
        min_y = min(r['y'] - r['h']/2 for r in rects_in_group)
        max_y = max(r['y'] + r['h']/2 for r in rects_in_group)

        group_w = max_x - min_x
        group_h = max_y - min_y
        
        # 繪製抽象的邊界框
        bbox_patch = patches.Rectangle(
            (min_x, min_y), group_w, group_h,
            linewidth=2,
            edgecolor='#00695C',
            facecolor='#E0F2F1',
            linestyle='--',
            alpha=0.7,
            zorder=1 # <<< MODIFIED: 抽象框在最底層
        )
        ax.add_patch(bbox_patch)
        ax.text(min_x + group_w / 2, max_y + 5, group_id, ha='center', va='bottom', fontsize=8, color='#00695C', zorder=5)

    # 在抽象視圖上，重新繪製所有的 Pin 和 Net
    # 新的繪製函式會自動處理圖層順序
    draw_rects_and_pins(ax, [], pins, "temp") # 這裡只繪製 Pin
    draw_nets(ax, pins, edges, rects_data)
    ax.set_title("Abstracted View (For ML Model)", fontsize=14)


def main():
    parser = argparse.ArgumentParser(description="Visualize the abstraction from a raw layout to an ML-ready format.")
    parser.add_argument("layout_json", help="Path to the original layout_*.json file.")
    parser.add_argument("output_image", help="Path to save the output comparison image (e.g., abstraction.png).")
    args = parser.parse_args()

    # 自動推斷 formatted_json 的路徑 (此部分邏輯不變)
    base_dir = os.path.dirname(args.layout_json)
    filename = os.path.basename(args.layout_json)
    # 假設原始 layout 在 'dataset' 資料夾中
    if 'dataset' in base_dir:
        # 推斷 formatted 資料夾在 'dataset' 的同級目錄
        formatted_dir_name = 'formatted_' + os.path.basename(base_dir) # e.g., 'formatted_dataset_symmetric'
        project_root = os.path.dirname(base_dir)
        formatted_dir = os.path.join(project_root, formatted_dir_name)
    else:
        # 如果找不到 'dataset'，則假設在同一個資料夾
        formatted_dir = base_dir
        
    formatted_filename = filename.replace('layout_', 'formatted_')
    formatted_json_path = os.path.join(formatted_dir, formatted_filename)
    
    # 載入數據
    layout_data = load_json_data(args.layout_json)['layout_data']
    
    rects = layout_data['rectangles']
    pins = layout_data['pins']
    edges = layout_data['edges']
    canvas_w = layout_data['canvas_width']
    canvas_h = layout_data['canvas_height']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(22, 10))
    fig.suptitle("Layout Abstraction Visualization", fontsize=18, y=0.98)

    # 繪製左圖 (原始佈局)
    # 繪圖順序不重要，因為 zorder 會控制圖層
    draw_rects_and_pins(ax1, rects, pins, "Original Detailed Layout")
    draw_nets(ax1, pins, edges, rects)
    
    # 繪製右圖 (抽象化視圖)
    draw_abstracted_view(ax2, rects, pins, edges)

    # 設定圖例
    legend_patches = [
        patches.Patch(facecolor='#DAE8FC', edgecolor='#6C8EBF', label='Standard Component'),
        patches.Patch(facecolor='#FFDDC1', edgecolor='#E57373', label='Symmetric Component'),
        patches.Patch(facecolor='#E0F2F1', edgecolor='#00695C', linestyle='--', label='Abstracted Group Node (for ML)')
    ]
    fig.legend(handles=legend_patches, loc='lower center', ncol=3, bbox_to_anchor=(0.5, 0.01))

    for ax in [ax1, ax2]:
        ax.set_xlim(0, canvas_w)
        ax.set_ylim(canvas_h, 0)
    plt.tight_layout(rect=[0, 0.05, 1, 0.95])
    plt.savefig(args.output_image, dpi=150)
    
    print(f"視覺化對比圖已成功儲存至: {args.output_image}")

if __name__ == '__main__':
    main()