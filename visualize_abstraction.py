# visualize_abstraction.py

import json
import argparse
import os
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as patches

VIVID_COLORS = {
    'grouping':     {'face': "#1F1F1F", 'edge': '#6A1B9A'},
    'symmetry':     {'face': '#C8E6C9', 'edge': '#2E7D32'},
    'alignment':    {'face': '#FFECB3', 'edge': '#FF8F00'},
    'macro':        {'face': '#2196F3', 'edge': '#0D47A1'},
    'std_cell':     {'face': '#BBDEFB', 'edge': '#42A5F5'},
    'default':      {'face': '#CFD8DC', 'edge': '#37474F'}
}

FADED_COLORS = {
    'grouping':     {'face': '#F3E5F5', 'edge': '#CE93D8'},
    'symmetry':     {'face': '#E8F5E9', 'edge': '#A5D6A7'},
    'alignment':    {'face': '#FFF8E1', 'edge': '#FFD54F'},
    'macro':        {'face': '#2196F3', 'edge': '#0D47A1'},
    'std_cell':     {'face': '#E3F2FD', 'edge': '#90CAF9'},
    'default':      {'face': '#ECEFF1', 'edge': '#B0BEC5'}
}

def load_json_data(file_path):
    if not os.path.exists(file_path):
        print(f"錯誤：找不到檔案 {file_path}")
        exit(1)
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_color_scheme(r_data, color_palette):
    """根據元件的約束和類型，從指定的調色盤中獲取顏色"""
    constraints = r_data.get('constraints', {})
    component_type = r_data.get('component_type')

    if 'grouping_id' in constraints:
        return color_palette['grouping']
    elif 'symmetry_id' in constraints:
        return color_palette['symmetry']
    elif 'alignment_id' in constraints:
        return color_palette['alignment']
    elif component_type == 'macro':
        return color_palette['macro']
    elif component_type == 'std_cell':
        return color_palette['std_cell']
    else:
        return color_palette['default']

def draw_rects_and_pins(ax, rects_data, pins, edges, color_palette):
    """根據指定的調色盤繪製元件、引腳和連線"""
    rect_map = {r['id']: r for r in rects_data}
    pin_map = {p['id']: p for p in pins}

    for r in rects_data:
        colors = get_color_scheme(r, color_palette)
        rect_patch = patches.Rectangle(
            (r['x'] - r['w'] / 2, r['y'] - r['h'] / 2), r['w'], r['h'],
            linewidth=1.5, edgecolor=colors['edge'], facecolor=colors['face'], zorder=2
        )
        ax.add_patch(rect_patch)
        ax.text(r['x'], r['y'], str(r['id']), ha='center', va='center', fontsize=6, zorder=5)

    for pin1_id, pin2_id in edges:
        pin1, pin2 = pin_map.get(pin1_id), pin_map.get(pin2_id)
        if not pin1 or not pin2: continue
        rect1, rect2 = rect_map.get(pin1['parent_rect_id']), rect_map.get(pin2['parent_rect_id'])
        if not rect1 or not rect2: continue
        pos1 = (rect1['x'] + pin1['rel_pos'][0], rect1['y'] + pin1['rel_pos'][1])
        pos2 = (rect2['x'] + pin2['rel_pos'][0], rect2['y'] + pin2['rel_pos'][1])
        ax.plot([pos1[0], pos2[0]], [pos1[1], pos2[1]], color='gray', alpha=0.5, linewidth=0.6, zorder=3)

    for pin in pins:
        parent_rect = rect_map.get(pin['parent_rect_id'])
        if parent_rect:
            abs_x = parent_rect['x'] + pin['rel_pos'][0]
            abs_y = parent_rect['y'] + pin['rel_pos'][1]
            ax.plot(abs_x, abs_y, 'k.', markersize=3, zorder=4)

def draw_abstracted_view(ax, rects_data, pins, edges):
    """繪製模型眼中的抽象化視圖"""
    ax.set_title("Abstracted View (For ML Model)", fontsize=14)
    ax.set_aspect('equal')
    ax.grid(True, linestyle='--', alpha=0.5)

    processed_rect_ids = set()
    constraint_map = defaultdict(lambda: defaultdict(list))
    for r in rects_data:
        for c_type, c_id in r.get('constraints', {}).items():
            constraint_map[c_type][c_id].append(r)

    def draw_abstract_bbox(rects_in_group, edge_color):
        if not rects_in_group: return
        min_x = min(r['x'] - r['w']/2 for r in rects_in_group)
        max_x = max(r['x'] + r['w']/2 for r in rects_in_group)
        min_y = min(r['y'] - r['h']/2 for r in rects_in_group)
        max_y = max(r['y'] + r['h']/2 for r in rects_in_group)
        bbox_patch = patches.Rectangle((min_x, min_y), max_x - min_x, max_y - min_y,
            linewidth=2, edgecolor=edge_color, facecolor='none',
            linestyle='--', alpha=0.9, zorder=10)
        ax.add_patch(bbox_patch)

    if 'symmetry_id' in constraint_map:
        for rects_in_group in constraint_map['symmetry_id'].values():
            draw_abstract_bbox(rects_in_group, VIVID_COLORS['symmetry']['edge'])
            processed_rect_ids.update(r['id'] for r in rects_in_group)

    if 'alignment_id' in constraint_map:
        for rects_in_group in constraint_map['alignment_id'].values():
            unprocessed = [r for r in rects_in_group if r['id'] not in processed_rect_ids]
            if not unprocessed: continue
            draw_abstract_bbox(unprocessed, VIVID_COLORS['alignment']['edge'])
            processed_rect_ids.update(r['id'] for r in unprocessed)
    
    if 'grouping_id' in constraint_map:
        for rects_in_group in constraint_map['grouping_id'].values():
            unprocessed = [r for r in rects_in_group if r['id'] not in processed_rect_ids]
            if not unprocessed: continue
            draw_abstract_bbox(unprocessed, VIVID_COLORS['grouping']['edge'])
            processed_rect_ids.update(r['id'] for r in unprocessed)

    draw_rects_and_pins(ax, rects_data, pins, edges, FADED_COLORS)


def main():
    parser = argparse.ArgumentParser(description="Visualize the abstraction from a raw layout to an ML-ready format.")
    parser.add_argument("layout_json", help="Path to the original layout_*.json file.")
    parser.add_argument("output_image", help="Path to save the output comparison image.")
    args = parser.parse_args()

    layout_data = load_json_data(args.layout_json)['layout_data']
    rects = layout_data['rectangles']
    pins = layout_data.get('pins', [])
    edges = layout_data.get('netlist_edges', [])
    canvas_w, canvas_h = layout_data['canvas_width'], layout_data['canvas_height']

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(22, 10))
    fig.suptitle("Layout Abstraction Visualization", fontsize=18, y=0.98)

    ax1.set_title("Original Detailed Layout", fontsize=14)
    ax1.set_aspect('equal')
    ax1.grid(True, linestyle='--', alpha=0.5)
    draw_rects_and_pins(ax1, rects, pins, edges, VIVID_COLORS)
    
    draw_abstracted_view(ax2, rects, pins, edges)

    legend_patches = [
        patches.Patch(facecolor=VIVID_COLORS['macro']['face'], edgecolor=VIVID_COLORS['macro']['edge'], label='Macro'),
        patches.Patch(facecolor=VIVID_COLORS['std_cell']['face'], edgecolor=VIVID_COLORS['std_cell']['edge'], label='Standard Cell'),
        patches.Patch(facecolor=VIVID_COLORS['symmetry']['face'], edgecolor=VIVID_COLORS['symmetry']['edge'], label='Symmetric'),
        patches.Patch(facecolor=VIVID_COLORS['alignment']['face'], edgecolor=VIVID_COLORS['alignment']['edge'], label='Aligned'),
        patches.Patch(facecolor=VIVID_COLORS['grouping']['face'], edgecolor=VIVID_COLORS['grouping']['edge'], label='Hierarchical Group'),
        patches.Patch(facecolor='none', edgecolor='gray', linestyle='--', label='Abstracted Node BBox')
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