# symmetry.py (緊密排列修正版)

import random
import copy
from layout import Rectangle, Pin

class SymmetricGenerator:
    """
    採用全域碰撞檢測策略，確保生成的對稱群組內部和外部均無重疊。
    在生成對稱元件的同時，也生成位置對稱的引腳。
    新的邏輯會根據設定的間隙 (gap) 來緊密排列元件。
    """
    def __init__(self, main_params):
        self.params = main_params
        self.analog_config = main_params['analog_symmetry_settings']
        self.canvas_w = main_params['CANVAS_WIDTH']
        self.canvas_h = main_params['CANVAS_HEIGHT']

    def _generate_rects_for_group_at_center(self, config, center_x, center_y, start_id, start_pin_id):
        """
        在給定的中心點，根據 'group_gap_range' 設定，緊密排列地生成一組對稱元件及其引腳。
        """
        rects_per_group = config['rects_per_group']
        axis = config['group_axis']
        
        generated_rects = []
        current_id = start_id
        current_pin_id = start_pin_id

        pins_per_comp = random.randint(*self.analog_config['pins_per_component'])
        gap_range = self.analog_config['group_gap_range']

        if axis == 'quad':
            if rects_per_group != 4: return None, 0, 0
            w = random.uniform(*self.analog_config['component_width_range'])
            h = random.uniform(*self.analog_config['component_height_range'])
            gap_x = random.uniform(*gap_range)
            gap_y = random.uniform(*gap_range)

            # --- 計算四個角落的元件中心點 ---
            x_L = center_x - gap_x / 2 - w / 2
            x_R = center_x + gap_x / 2 + w / 2
            y_T = center_y - gap_y / 2 - h / 2 # Top
            y_B = center_y + gap_y / 2 + h / 2 # Bottom

            # --- 創建 A1 (左上) 並為其生成引腳 ---
            rect_A1 = Rectangle(current_id, x_L, y_T, w, h); rect_A1.fixed = True
            for _ in range(pins_per_comp):
                pin_x_rel = random.uniform(-w / 2, w / 2); pin_y_rel = random.uniform(-h / 2, h / 2)
                rect_A1.pins.append(Pin(current_pin_id, rect_A1, (pin_x_rel, pin_y_rel))); current_pin_id += 1
            
            # --- 創建 B1 (右上) ---
            rect_B1 = Rectangle(current_id + 1, x_R, y_T, w, h); rect_B1.fixed = True
            for base_pin in rect_A1.pins:
                rect_B1.pins.append(Pin(current_pin_id, rect_B1, (-base_pin.rel_pos[0], base_pin.rel_pos[1]))); current_pin_id += 1

            # --- 創建 A2 (左下) ---
            rect_A2 = Rectangle(current_id + 2, x_L, y_B, w, h); rect_A2.fixed = True
            for base_pin in rect_A1.pins:
                rect_A2.pins.append(Pin(current_pin_id, rect_A2, (base_pin.rel_pos[0], -base_pin.rel_pos[1]))); current_pin_id += 1

            # --- 創建 B2 (右下) ---
            rect_B2 = Rectangle(current_id + 3, x_R, y_B, w, h); rect_B2.fixed = True
            for base_pin in rect_A1.pins:
                rect_B2.pins.append(Pin(current_pin_id, rect_B2, (-base_pin.rel_pos[0], -base_pin.rel_pos[1]))); current_pin_id += 1

            generated_rects.extend([rect_A1, rect_B1, rect_A2, rect_B2])
            current_id += 4
        
        else: # 垂直或水平對稱 (包含堆疊)
            num_pairs = rects_per_group // 2
            
            # 1. 先生成所有基礎元件的尺寸
            base_rects_info = []
            for _ in range(num_pairs):
                w = random.uniform(*self.analog_config['component_width_range'])
                h = random.uniform(*self.analog_config['component_height_range'])
                base_rects_info.append({'w': w, 'h': h})

            # 2. 計算堆疊的總尺寸和起始位置
            gap_stack = random.uniform(*gap_range) # 堆疊方向的間隙
            if axis == 'vertical':
                total_stack_height = sum(info['h'] for info in base_rects_info) + (num_pairs - 1) * gap_stack
                cursor_y = center_y - total_stack_height / 2
            else: # horizontal
                total_stack_width = sum(info['w'] for info in base_rects_info) + (num_pairs - 1) * gap_stack
                cursor_x = center_x - total_stack_width / 2

            # 3. 迭代生成每一對緊密排列的元件
            for i in range(num_pairs):
                info = base_rects_info[i]
                w, h = info['w'], info['h']
                gap_mirror = random.uniform(*gap_range) # 鏡像軸方向的間隙

                # --- 創建基礎元件和其鏡像元件 ---
                if axis == 'vertical':
                    base_x = center_x - gap_mirror / 2 - w / 2
                    base_y = cursor_y + h / 2
                    mirror_x = center_x + gap_mirror / 2 + w / 2
                    mirror_y = base_y
                    cursor_y += (h + gap_stack) # 更新下一個堆疊位置
                else: # horizontal
                    base_y = center_y - gap_mirror / 2 - h / 2
                    base_x = cursor_x + w / 2
                    mirror_y = center_y + gap_mirror / 2 + h / 2
                    mirror_x = base_x
                    cursor_x += (w + gap_stack) # 更新下一個堆疊位置
                
                base_rect = Rectangle(current_id, base_x, base_y, w, h); base_rect.fixed = True
                mirror_rect = Rectangle(current_id + 1, mirror_x, mirror_y, w, h); mirror_rect.fixed = True

                # --- 為這對元件生成對稱的引腳 ---
                for _ in range(pins_per_comp):
                    pin_x_rel = random.uniform(-w / 2, w / 2); pin_y_rel = random.uniform(-h / 2, h / 2)
                    base_rect.pins.append(Pin(current_pin_id, base_rect, (pin_x_rel, pin_y_rel)))
                    current_pin_id += 1
                    
                    # 根據對稱軸鏡像引腳
                    if axis == 'vertical':
                        mirror_rel_pos = (-pin_x_rel, pin_y_rel)
                    else: # horizontal
                        mirror_rel_pos = (pin_x_rel, -pin_y_rel)
                    mirror_rect.pins.append(Pin(current_pin_id, mirror_rect, mirror_rel_pos))
                    current_pin_id += 1
                
                generated_rects.extend([base_rect, mirror_rect])
                current_id += 2

        return generated_rects, current_id, current_pin_id


    def generate_analog_groups(self, start_id, start_pin_id, existing_rects):
        """
        生成對稱群組，並確保與所有已存在的元件無重疊。
        """
        print("\n--- 開始生成進階類比對稱群組 (緊密排列模式) ---")
        num_groups = random.randint(self.analog_config['num_groups']['low'], self.analog_config['num_groups']['high'])
        group_choices = self.analog_config['group_configs']
        weights = [config['weight'] for config in group_choices]
        
        newly_placed_rects = []
        current_id = start_id
        current_pin_id = start_pin_id
        
        for i in range(num_groups):
            chosen_config = random.choices(group_choices, weights=weights, k=1)[0]
            
            is_placed = False
            for _ in range(200): # 增加尋找位置的嘗試次數
                # 中心點依然隨機，但群組內部是緊密的
                center_x = random.uniform(150, self.canvas_w - 150)
                center_y = random.uniform(150, self.canvas_h - 150)
                
                potential_rects, next_id, next_pin_id = self._generate_rects_for_group_at_center(
                    chosen_config, center_x, center_y, current_id, current_pin_id)
                if not potential_rects: continue

                # 檢查群組內部自體重疊 (雖然新邏輯下不太可能發生，但作為保險)
                has_internal_overlap = False
                for k in range(len(potential_rects)):
                    for l in range(k + 1, len(potential_rects)):
                        if potential_rects[k].intersects(potential_rects[l]):
                            has_internal_overlap = True; break
                    if has_internal_overlap: break
                if has_internal_overlap: continue

                # 檢查與所有已放置元件的重疊
                has_external_overlap = any(pr.intersects(er) for pr in potential_rects for er in existing_rects)
                if has_external_overlap: continue

                # 邊界檢查
                is_out_of_bounds = any(not (r.x - r.w / 2 >= 0 and r.x + r.w / 2 <= self.canvas_w and \
                                            r.y - r.h / 2 >= 0 and r.y + r.h / 2 <= self.canvas_h)
                                       for r in potential_rects)
                if is_out_of_bounds: continue
                
                # 如果所有檢查都通過，才放置元件
                newly_placed_rects.extend(potential_rects)
                existing_rects.extend(potential_rects) # 更新全域列表以供下次檢查
                current_id = next_id
                current_pin_id = next_pin_id
                is_placed = True
                break
            
            if not is_placed:
                print(f"--- 警告：無法為第 {i+1} 組對稱群找到足夠空間，已略過。 ---")

        total_pins = sum(len(r.pins) for r in newly_placed_rects)
        print(f"--- 類比對稱群組生成完畢，共 {len(newly_placed_rects)} 個元件，{total_pins} 個引腳。 ---")
        return newly_placed_rects, current_id, current_pin_id