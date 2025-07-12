# symmetry.py

import random
import math
from layout import Rectangle, Pin

class SymmetricGenerator:
    def __init__(self, main_params):
        self.params = main_params
        self.analog_config = main_params['analog_symmetry_settings']
        self.canvas_w = main_params['CANVAS_WIDTH']
        self.canvas_h = main_params['CANVAS_HEIGHT']
        self.pin_edge_margin_ratio = self.params.get('PIN_EDGE_MARGIN_RATIO', 0.1)
        self.k = self.params.get('PIN_DENSITY_K', 0.01)
        self.p = self.params.get('RENT_EXPONENT_P', 0.6)

    def _generate_pins_on_edge(self, rect, num_pins, start_pin_id):
        """為單個矩形在邊緣生成引腳，並返回引腳列表和最後的 ID"""
        pins = []
        current_pin_id = start_pin_id
        if num_pins == 0:
            return pins, current_pin_id

        hw, hh = rect.w / 2, rect.h / 2
        margin_x = min(rect.w * self.pin_edge_margin_ratio, hw)
        margin_y = min(rect.h * self.pin_edge_margin_ratio, hh)

        for _ in range(num_pins):
            edge = random.choice(['top', 'bottom', 'left', 'right'])
            if edge == 'top': px, py = random.uniform(-hw, hw), random.uniform(-hh, -hh + margin_y)
            elif edge == 'bottom': px, py = random.uniform(-hw, hw), random.uniform(hh - margin_y, hh)
            elif edge == 'left': px, py = random.uniform(-hw, -hw + margin_x), random.uniform(-hh, hh)
            else: px, py = random.uniform(hw - margin_x, hw), random.uniform(-hh, hh)
            
            pin = Pin(current_pin_id, rect, (px, py))
            pins.append(pin)
            current_pin_id += 1
        return pins, current_pin_id

    def _generate_rects_for_group_at_center(self, config, center_x, center_y, start_id, start_pin_id, group_id):
        rects_per_group = config['rects_per_group']
        axis = config['group_axis']
        generated_rects = []
        current_id = start_id
        current_pin_id = start_pin_id

        def _set_group_properties(rect):
            rect.fixed = True
            rect.group_id = group_id
            rect.group_type = axis
            return rect

        if rects_per_group == 2:
            w = random.uniform(*self.analog_config['component_width_range'])
            h = random.uniform(*self.analog_config['component_height_range'])
            gap_mirror = random.uniform(*self.analog_config['group_gap_range'])
            
            if axis == 'vertical':
                base_x, base_y = center_x - gap_mirror / 2 - w / 2, center_y
                mirror_x = center_x + gap_mirror / 2 + w / 2
                base_rect = _set_group_properties(Rectangle(current_id, base_x, base_y, w, h))
                mirror_rect = _set_group_properties(Rectangle(current_id + 1, mirror_x, base_y, w, h))
            else: # horizontal
                base_x, base_y = center_x, center_y - gap_mirror / 2 - h / 2
                mirror_y = center_y + gap_mirror / 2 + h / 2
                base_rect = _set_group_properties(Rectangle(current_id, base_x, base_y, w, h))
                mirror_rect = _set_group_properties(Rectangle(current_id + 1, base_x, mirror_y, w, h))

            area = w * h
            num_pins = int(self.k * (area ** self.p))
            if area > 1 and num_pins == 0: num_pins = 1

            base_pins, temp_pin_id = self._generate_pins_on_edge(base_rect, num_pins, current_pin_id)
            base_rect.pins = base_pins
            
            mirror_pins = []
            for base_pin in base_pins:
                rel_pos = base_pin.rel_pos
                mirror_rel_pos = (-rel_pos[0], rel_pos[1]) if axis == 'vertical' else (rel_pos[0], -rel_pos[1])
                mirror_pin = Pin(temp_pin_id, mirror_rect, mirror_rel_pos)
                mirror_pins.append(mirror_pin)
                temp_pin_id +=1

            mirror_rect.pins = mirror_pins
            current_pin_id = temp_pin_id

            generated_rects.extend([base_rect, mirror_rect])
            current_id += 2
        else:
             pass

        return generated_rects, current_id, current_pin_id

    def generate_analog_groups(self, start_id, start_pin_id, existing_rects):
        print("\n--- 開始生成帶有對稱引腳的對稱群組 ---")
        num_groups_config = self.analog_config['num_groups']
        num_groups = random.randint(num_groups_config['low'], num_groups_config['high'])
        group_choices = self.analog_config['group_configs']
        weights = [config['weight'] for config in group_choices]
        
        newly_placed_rects = []
        current_id = start_id
        current_pin_id = start_pin_id
        
        for i in range(num_groups):
            group_id_str = f"sym_group_{i}"
            chosen_config = random.choices(group_choices, weights=weights, k=1)[0]
            is_placed = False
            for _ in range(200):
                center_x = random.uniform(150, self.canvas_w - 150)
                center_y = random.uniform(150, self.canvas_h - 150)
                
                potential_rects, next_id, next_pin_id = self._generate_rects_for_group_at_center(
                    chosen_config, center_x, center_y, current_id, current_pin_id, group_id_str)

                if not potential_rects: continue
                if any(pr.intersects(er) for pr in potential_rects for er in existing_rects): continue
                if any(not (0 <= r.x - r.w/2 and r.x + r.w/2 <= self.canvas_w and 0 <= r.y - r.h/2 and r.y + r.h/2 <= self.canvas_h) for r in potential_rects): continue
                
                newly_placed_rects.extend(potential_rects)
                existing_rects.extend(potential_rects)
                current_id, current_pin_id = next_id, next_pin_id
                is_placed = True
                break
            
            if not is_placed:
                print(f"--- 警告：無法為對稱群組 {group_id_str} 找到足夠空間，已略過。 ---")

        total_pins = sum(len(r.pins) for r in newly_placed_rects)
        print(f"--- 對稱群組生成完畢，共 {len(newly_placed_rects)} 個元件，{total_pins} 個引腳。 ---")
        return newly_placed_rects, current_id, current_pin_id