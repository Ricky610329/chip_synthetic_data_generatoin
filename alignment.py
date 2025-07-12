# alignment.py (支援邊緣對齊)

import random
import math
from layout import Rectangle

class AlignmentGenerator:
    """
    生成固定相對位置的、對齊的元件群組。
    現在支援邊緣對齊（上/下/左/右）。
    """
    def __init__(self, params):
        self.params = params
        self.config = params['alignment_settings']
        self.canvas_w = params['CANVAS_WIDTH']
        self.canvas_h = params['CANVAS_HEIGHT']

    def generate_aligned_sets(self, start_id, existing_rects):
        """主函式，生成多個對齊的元件集合"""
        print("\n--- 開始生成邊緣對齊元件集合 ---")
        num_sets = random.randint(self.config['num_sets']['low'], self.config['num_sets']['high'])
        
        current_id = start_id
        
        for i in range(num_sets):
            group_id_str = f"align_group_{i}"
            is_placed = False
            for _ in range(200):
                align_type = random.choice(['horizontal', 'vertical'])
                
                # ✨ 1. 新增邏輯：隨機決定對齊模式
                if align_type == 'vertical':
                    # 垂直排列時，隨機選擇是靠左對齊還是靠右對齊
                    edge_align_mode = random.choice(['left', 'right'])
                else: # horizontal
                    # 水平排列時，隨機選擇是靠上對齊還是靠下對齊
                    edge_align_mode = random.choice(['top', 'bottom'])

                potential_rects = self._create_one_set(current_id, group_id_str, align_type, edge_align_mode)

                if any(pr.intersects(er) for pr in potential_rects for er in existing_rects):
                    continue
                if any(not (r.x - r.w/2 >= 0 and r.x + r.w/2 <= self.canvas_w and r.y - r.h/2 >= 0 and r.y + r.h/2 <= self.canvas_h) for r in potential_rects):
                    continue
                
                existing_rects.extend(potential_rects)
                current_id += len(potential_rects)
                is_placed = True
                print(f"  - 已放置對齊群組 '{group_id_str}' (類型: {align_type}, 模式: {edge_align_mode}, 數量: {len(potential_rects)})")
                break
            
            if not is_placed:
                print(f"--- 警告：無法為對齊群組 {i+1} 找到足夠空間，已略過。 ---")

        print(f"--- 邊緣對齊元件集合生成完畢，共新增 {current_id - start_id} 個元件。 ---")
        return existing_rects, current_id

    def _create_one_set(self, start_id, group_id, align_type, edge_align_mode):
        """
        內部函式，生成單一一個對齊的元件集合。
        - align_type: 'vertical' 或 'horizontal'
        - edge_align_mode: 'top', 'bottom', 'left', 'right'
        """
        set_rects = []
        num_components = random.randint(self.config['components_per_set']['low'], self.config['components_per_set']['high'])
        
        start_x = random.uniform(self.canvas_w * 0.1, self.canvas_w * 0.9)
        start_y = random.uniform(self.canvas_h * 0.1, self.canvas_h * 0.9)

        current_pos_tracker = 0 # 用於追蹤下一個元件的位置

        for i in range(num_components):
            w = random.uniform(*self.config['component_width_range'])
            h = random.uniform(*self.config['component_height_range'])
            gap = random.uniform(*self.config['gap_range'])

            # ✨ 2. 修改座標計算邏輯以支援邊緣對齊
            if align_type == 'vertical':
                # 垂直排列，元件從上到下堆疊
                # y 座標的中心點計算
                rect_y = start_y + current_pos_tracker + h / 2
                
                # x 座標的中心點計算
                if edge_align_mode == 'left':
                    # 左邊緣對齊在 start_x
                    rect_x = start_x + w / 2
                else: # 'right'
                    # 右邊緣對齊在 start_x
                    rect_x = start_x - w / 2
                
                # 更新下一個元件的起始 y 位置
                current_pos_tracker += h + gap

            else: # Horizontal
                # 水平排列，元件從左到右排列
                # x 座標的中心點計算
                rect_x = start_x + current_pos_tracker + w / 2

                # y 座標的中心點計算
                if edge_align_mode == 'top':
                    # 上邊緣對齊在 start_y
                    rect_y = start_y + h / 2
                else: # 'bottom'
                    # 下邊緣對齊在 start_y
                    rect_y = start_y - h / 2

                # 更新下一個元件的起始 x 位置
                current_pos_tracker += w + gap

            new_rect = Rectangle(start_id + i, rect_x, rect_y, w, h)
            new_rect.group_id = group_id
            new_rect.group_type = 'aligned'
            new_rect.fixed = True 
            
            set_rects.append(new_rect)
            
        return set_rects