# visualize_abstraction.py (支援階層式群組顯示)

import json
import argparse
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches

def load_json_data(file_path):
    if not os.path.exists(file_path):
        print(f"錯誤：找不到檔案 {file_path}")
        exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def draw_detailed_view(ax, rects, pins, edges):
    """在給定的 axis 上繪製詳細的元件、引腳與連線"""
    ax.set_title("Original Detailed Layout", fontsize=14)
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)

    # ✨ 1. 繪製元件 (三種顏色)
    for r in rects:
        group_type = r.get('group_type')
        if group_type == 'hierarchical':
            face_color = '#E1BEE7'; edge_color = '#6A1B9A' # 紫色系
        elif group_type: # 任何其他非空的 group_type (即對稱群組)
            face_color = '#C8E6C9'; edge_color = '#2E7D32' # 綠色系
        else:
            face_color = '#BBDEFB'; edge_color = '#0D47A1' # 藍色系
        
        rect_patch = patches.Rectangle(
            (r['x'] - r['w'] / 2, r['y'] - r['h'] / 2), r['w'], r['h'],
            linewidth=1.5, edgecolor=edge_color, facecolor=face_color, zorder=2
        )
        ax.add_patch(rect_patch)
        ax.text(r['x'], r['y'], str(r['id']), ha='center', va='center', fontsize=6, zorder=5)

    # 繪製引腳
    rect_map = {r['id']: r for r in rects}
    for pin in pins:
        parent_rect = rect_map.get(pin['parent_rect_id'])
        if parent_rect:
            abs_x = parent_rect['x'] + pin['rel_pos'][0]
            abs_y = parent_rect['y'] + pin['rel_pos'][1]
            ax.plot(abs_x, abs_y, 'k.', markersize=3, zorder=4)

    # 繪製連線
    pin_map = {p['id']: p for p in pins}
    for pin1_id, pin2_id in edges:
        pin1, pin2 = pin_map.get(pin1_id), pin_map.get(pin2_id)
        if not pin1 or not pin2: continue
        rect1, rect2 = rect_map.get(pin1['parent_rect_id']), rect_map.get(pin2['parent_rect_id'])
        if not rect1 or not rect2: continue
        pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
        pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])
        ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='r', alpha=0.4, linewidth=0.6, zorder=3)


def draw_abstracted_view(ax, rects_data, pins, edges):
    """繪製模型眼中的抽象化視圖"""
    ax.set_title("Abstracted View (For ML Model)", fontsize=14)
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)

    # 1. 找到所有群組
    grouped_rects = defaultdict(list)
    single_rects = []
    for r in rects_data:
        if r.get('group_id'):
            grouped_rects[r['group_id']].append(r)
        else:
            single_rects.append(r)

    # 2. 繪製單一元件節點 (藍色)
    for r in single_rects:
        ax.add_patch(patches.Rectangle(
            (r['x'] - r['w'] / 2, r['y'] - r['h'] / 2), r['w'], r['h'],
            linewidth=1.5, edgecolor='#0D47A1', facecolor='#BBDEFB', zorder=2
        ))
        ax.text(r['x'], r['y'], str(r['id']), ha='center', va='center', fontsize=6, zorder=5)

    # ✨ 2. 繪製群組節點的抽象邊界框 (區分顏色)
    for group_id, rects_in_group in grouped_rects.items():
        min_x = min(r['x'] - r['w']/2 for r in rects_in_group)
        max_x = max(r['x'] + r['w']/2 for r in rects_in_group)
        min_y = min(r['y'] - r['h']/2 for r in rects_in_group)
        max_y = max(r['y'] + r['h']/2 for r in rects_in_group)
        group_w, group_h = max_x - min_x, max_y - min_y
        
        # 檢查群組類型來決定顏色
        # 我們假設一個群組內所有元件的 group_type 都是一樣的
        group_type = rects_in_group[0].get('group_type')
        if group_type == 'hierarchical':
            edge_color = '#6A1B9A'; face_color = '#F3E5F5' # 紫色系
        else: # 對稱群組
            edge_color = '#2E7D32'; face_color = '#E8F5E9' # 綠色系
            
        bbox_patch = patches.Rectangle(
            (min_x, min_y), group_w, group_h,
            linewidth=2, edgecolor=edge_color, facecolor=face_color,
            linestyle='--', alpha=0.8, zorder=1
        )
        ax.add_patch(bbox_patch)
        ax.text(min_x + group_w / 2, max_y + 10, group_id, ha='center', va='bottom', 
                fontsize=8, color=edge_color, weight='bold', zorder=5)

    # 3. 在抽象視圖上，重新繪製所有的 Pin 和 Net
    # (這部分邏輯不變，因為它與元件顏色無關)
    rect_map = {r['id']: r for r in rects_data}
    pin_map = {p['id']: p for p in pins}
    for pin in pins:
        parent_rect = rect_map.get(pin['parent_rect_id'])
        if parent_rect:
            abs_x = parent_rect['x'] + pin['rel_pos'][0]
            abs_y = parent_rect['y'] + pin['rel_pos'][1]
            ax.plot(abs_x, abs_y, 'k.', markersize=3, zorder=4)
    for pin1_id, pin2_id in edges:
        pin1, pin2 = pin_map.get(pin1_id), pin_map.get(pin2_id)
        if not pin1 or not pin2: continue
        rect1, rect2 = rect_map.get(pin1['parent_rect_id']), rect_map.get(pin2['parent_rect_id'])
        if not rect1 or not rect2: continue
        pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
        pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])
        ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='r', alpha=0.4, linewidth=0.6, zorder=3)


def main():
    parser = argparse.ArgumentParser(description="Visualize the abstraction from a raw layout to an ML-ready format.")
    parser.add_argument("layout_json", help="Path to the original layout_*.json file.")
    parser.add_argument("output_image", help="Path to save the output comparison image.")
    args = parser.parse_args()

    layout_data = load_json_data(args.layout_json)['layout_data']
    rects, pins, edges = layout_data['rectangles'], layout_data['pins'], layout_data['edges']
    canvas_w, canvas_h = layout_data['canvas_width'], layout_data['canvas_height']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(22, 10))
    fig.suptitle("Layout Abstraction Visualization", fontsize=18, y=0.98)

    # 繪製左圖 (原始詳細佈局)
    draw_detailed_view(ax1, rects, pins, edges)
    
    # 繪製右圖 (抽象化視圖)
    draw_abstracted_view(ax2, rects, pins, edges)

    # ✨ 3. 更新圖例以包含所有類型
    legend_patches = [
        patches.Patch(facecolor='#BBDEFB', edgecolor='#0D47A1', label='Standard Component'),
        patches.Patch(facecolor='#C8E6C9', edgecolor='#2E7D32', label='Symmetric Component'),
        patches.Patch(facecolor='#E1BEE7', edgecolor='#6A1B9A', label='Hierarchical Group Component'),
        patches.Patch(facecolor='#E8F5E9', edgecolor='#2E7D32', linestyle='--', label='Abstracted Symmetric Node'),
        patches.Patch(facecolor='#F3E5F5', edgecolor='#6A1B9A', linestyle='--', label='Abstracted Hierarchical Node')
    ]
    fig.legend(handles=legend_patches, loc='lower center', ncol=3, bbox_to_anchor=(0.5, 0.01), fontsize='medium')

    for ax in [ax1, ax2]:
        ax.set_xlim(-20, canvas_w + 20)
        ax.set_ylim(canvas_h + 20, -20)
    plt.tight_layout(rect=[0, 0.08, 1, 0.95])
    plt.savefig(args.output_image, dpi=150)
    
    print(f"視覺化對比圖已成功儲存至: {args.output_image}")

if __name__ == '__main__':
    main()