# symmetry.py (群組標記修正版)

import random
import copy
from layout import Rectangle, Pin

class SymmetricGenerator:
    """
    生成對稱群組，並為每個群組中的元件分配一個共同的 group_id。
    """
    def __init__(self, main_params):
        self.params = main_params
        self.analog_config = main_params['analog_symmetry_settings']
        self.canvas_w = main_params['CANVAS_WIDTH']
        self.canvas_h = main_params['CANVAS_HEIGHT']

    def _generate_rects_for_group_at_center(self, config, center_x, center_y, start_id, start_pin_id, group_id):
        """
        在給定的中心點生成一組對稱元件，並標記它們的 group_id。
        """
        rects_per_group = config['rects_per_group']
        axis = config['group_axis']
        
        generated_rects = []
        current_id = start_id
        current_pin_id = start_pin_id

        pins_per_comp = random.randint(*self.analog_config['pins_per_component'])
        gap_range = self.analog_config['group_gap_range']

        # 為所有將要生成的矩形設定共同的群組屬性
        def _set_group_properties(rect):
            rect.fixed = True
            rect.group_id = group_id
            rect.group_type = axis
            return rect

        if axis == 'quad':
            if rects_per_group != 4: return None, 0, 0
            w = random.uniform(*self.analog_config['component_width_range'])
            h = random.uniform(*self.analog_config['component_height_range'])
            gap_x = random.uniform(*gap_range)
            gap_y = random.uniform(*gap_range)

            x_L = center_x - gap_x / 2 - w / 2
            x_R = center_x + gap_x / 2 + w / 2
            y_T = center_y - gap_y / 2 - h / 2
            y_B = center_y + gap_y / 2 + h / 2

            rect_A1 = _set_group_properties(Rectangle(current_id, x_L, y_T, w, h))
            for _ in range(pins_per_comp):
                pin_x_rel = random.uniform(-w / 2, w / 2); pin_y_rel = random.uniform(-h / 2, h / 2)
                rect_A1.pins.append(Pin(current_pin_id, rect_A1, (pin_x_rel, pin_y_rel))); current_pin_id += 1
            
            rect_B1 = _set_group_properties(Rectangle(current_id + 1, x_R, y_T, w, h))
            for base_pin in rect_A1.pins:
                rect_B1.pins.append(Pin(current_pin_id, rect_B1, (-base_pin.rel_pos[0], base_pin.rel_pos[1]))); current_pin_id += 1

            rect_A2 = _set_group_properties(Rectangle(current_id + 2, x_L, y_B, w, h))
            for base_pin in rect_A1.pins:
                rect_A2.pins.append(Pin(current_pin_id, rect_A2, (base_pin.rel_pos[0], -base_pin.rel_pos[1]))); current_pin_id += 1

            rect_B2 = _set_group_properties(Rectangle(current_id + 3, x_R, y_B, w, h))
            for base_pin in rect_A1.pins:
                rect_B2.pins.append(Pin(current_pin_id, rect_B2, (-base_pin.rel_pos[0], -base_pin.rel_pos[1]))); current_pin_id += 1

            generated_rects.extend([rect_A1, rect_B1, rect_A2, rect_B2])
            current_id += 4
        
        else: # Vertical or Horizontal
            num_pairs = rects_per_group // 2
            base_rects_info = [{'w': random.uniform(*self.analog_config['component_width_range']), 'h': random.uniform(*self.analog_config['component_height_range'])} for _ in range(num_pairs)]
            gap_stack = random.uniform(*gap_range)
            
            if axis == 'vertical':
                total_stack_height = sum(info['h'] for info in base_rects_info) + (num_pairs - 1) * gap_stack
                cursor = center_y - total_stack_height / 2
            else: # horizontal
                total_stack_width = sum(info['w'] for info in base_rects_info) + (num_pairs - 1) * gap_stack
                cursor = center_x - total_stack_width / 2

            for i in range(num_pairs):
                info = base_rects_info[i]; w, h = info['w'], info['h']
                gap_mirror = random.uniform(*gap_range)
                
                if axis == 'vertical':
                    base_x, base_y = center_x - gap_mirror / 2 - w / 2, cursor + h / 2
                    mirror_x, mirror_y = center_x + gap_mirror / 2 + w / 2, base_y
                    cursor += (h + gap_stack)
                else: # horizontal
                    base_x, base_y = cursor + w / 2, center_y - gap_mirror / 2 - h / 2
                    mirror_x, mirror_y = base_x, center_y + gap_mirror / 2 + h / 2
                    cursor += (w + gap_stack)
                
                base_rect = _set_group_properties(Rectangle(current_id, base_x, base_y, w, h))
                mirror_rect = _set_group_properties(Rectangle(current_id + 1, mirror_x, mirror_y, w, h))

                for _ in range(pins_per_comp):
                    pin_x_rel, pin_y_rel = random.uniform(-w / 2, w / 2), random.uniform(-h / 2, h / 2)
                    base_rect.pins.append(Pin(current_pin_id, base_rect, (pin_x_rel, pin_y_rel))); current_pin_id += 1
                    mirror_rel_pos = (-pin_x_rel, pin_y_rel) if axis == 'vertical' else (pin_x_rel, -pin_y_rel)
                    mirror_rect.pins.append(Pin(current_pin_id, mirror_rect, mirror_rel_pos)); current_pin_id += 1
                
                generated_rects.extend([base_rect, mirror_rect])
                current_id += 2

        return generated_rects, current_id, current_pin_id

    def generate_analog_groups(self, start_id, start_pin_id, existing_rects):
        print("\n--- 開始生成進階類比對稱群組 (群組標記模式) ---")
        num_groups = random.randint(self.analog_config['num_groups']['low'], self.analog_config['num_groups']['high'])
        group_choices = self.analog_config['group_configs']
        weights = [config['weight'] for config in group_choices]
        
        newly_placed_rects = []
        current_id = start_id
        current_pin_id = start_pin_id
        
        for i in range(num_groups):
            # 為每個即將生成的群組創建一個唯一的 ID
            group_id_str = f"sym_group_{i}"
            chosen_config = random.choices(group_choices, weights=weights, k=1)[0]
            
            is_placed = False
            for _ in range(200):
                center_x = random.uniform(150, self.canvas_w - 150)
                center_y = random.uniform(150, self.canvas_h - 150)
                
                potential_rects, next_id, next_pin_id = self._generate_rects_for_group_at_center(
                    chosen_config, center_x, center_y, current_id, current_pin_id, group_id_str
                )
                if not potential_rects: continue

                # 檢查與所有已放置元件的重疊
                if any(pr.intersects(er) for pr in potential_rects for er in existing_rects): continue
                # 邊界檢查
                if any(not (r.x - r.w/2 >= 0 and r.x + r.w/2 <= self.canvas_w and r.y - r.h/2 >= 0 and r.y + r.h/2 <= self.canvas_h) for r in potential_rects): continue
                
                newly_placed_rects.extend(potential_rects)
                existing_rects.extend(potential_rects)
                current_id, current_pin_id = next_id, next_pin_id
                is_placed = True
                break
            
            if not is_placed:
                print(f"--- 警告：無法為第 {i+1} 組 (ID: {group_id_str}) 找到足夠空間，已略過。 ---")

        total_pins = sum(len(r.pins) for r in newly_placed_rects)
        print(f"--- 類比對稱群組生成完畢，共 {len(newly_placed_rects)} 個元件，{total_pins} 個引腳。 ---")
        return newly_placed_rects, current_id, current_pin_id