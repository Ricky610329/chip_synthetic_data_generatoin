# alignment.py

import random
from layout import Rectangle

class AlignmentGenerator:
    def __init__(self, main_params):
        self.params = main_params
        self.align_config = main_params['alignment_settings']
        self.canvas_w = main_params['CANVAS_WIDTH']
        self.canvas_h = main_params['CANVAS_HEIGHT']

    def _generate_set(self, start_id, group_id, existing_rects):
        components_per_set_config = self.align_config['components_per_set']
        num_components = random.randint(components_per_set_config['low'], components_per_set_config['high'])
        modes = [choice['mode'] for choice in self.align_config['alignment_mode_weights']]
        weights = [choice['weight'] for choice in self.align_config['alignment_mode_weights']]
        align_mode = random.choices(modes, weights=weights, k=1)[0]
        
        generated_rects, alignment_constraints = [], []
        current_id = start_id

        w, h = random.uniform(*self.align_config['component_width_range']), random.uniform(*self.align_config['component_height_range'])
        padding = 100
        x, y = random.uniform(padding + w/2, self.canvas_w - padding - w/2), random.uniform(padding + h/2, self.canvas_h - padding - h/2)
        
        seed_rect = Rectangle(current_id, x, y, w, h)
        seed_rect.fixed = True
        seed_rect.group_id = group_id
        seed_rect.group_type = 'aligned'
        
        generated_rects.append(seed_rect)
        last_rect = seed_rect
        current_id += 1

        for i in range(1, num_components):
            w, h = random.uniform(*self.align_config['component_width_range']), random.uniform(*self.align_config['component_height_range'])
            gap = random.uniform(*self.align_config['gap_range'])
            
            if align_mode == 'left': new_x, new_y = (seed_rect.x - seed_rect.w/2) + w/2, last_rect.y + last_rect.h/2 + gap + h/2
            elif align_mode == 'right': new_x, new_y = (seed_rect.x + seed_rect.w/2) - w/2, last_rect.y + last_rect.h/2 + gap + h/2
            elif align_mode == 'top': new_x, new_y = last_rect.x + last_rect.w/2 + gap + w/2, (seed_rect.y - seed_rect.h/2) + h/2
            elif align_mode == 'bottom': new_x, new_y = last_rect.x + last_rect.w/2 + gap + w/2, (seed_rect.y + seed_rect.h/2) - h/2
            elif align_mode == 'h_center': new_x, new_y = seed_rect.x, last_rect.y + last_rect.h/2 + gap + h/2
            else: new_x, new_y = last_rect.x + last_rect.w/2 + gap + w/2, seed_rect.y
            
            new_rect = Rectangle(current_id, new_x, new_y, w, h)
            new_rect.fixed = True
            new_rect.group_id = group_id
            new_rect.group_type = 'aligned'
            alignment_constraints.append((last_rect.id, new_rect.id, align_mode))
            generated_rects.append(new_rect)
            last_rect = new_rect
            current_id += 1
            
        return generated_rects, alignment_constraints, current_id

    def generate_aligned_sets(self, start_id, existing_rects):
        print("\n--- 開始生成對齊群組 (無 Pin 生成) ---")
        num_sets_config = self.align_config['num_sets']
        num_sets = random.randint(num_sets_config['low'], num_sets_config['high'])
        all_newly_placed_rects, all_alignment_constraints = [], []
        current_id = start_id
        
        for i in range(num_sets):
            group_id_str = f"align_group_{i}"
            is_placed = False
            for _ in range(150):
                potential_rects, potential_constraints, next_id = self._generate_set(current_id, group_id_str, existing_rects)
                if any(not (0 <= r.x - r.w/2 and r.x + r.w/2 <= self.canvas_w and 0 <= r.y - r.h/2 and r.y + r.h/2 <= self.canvas_h) for r in potential_rects): continue
                if any(pr.intersects(er) for pr in potential_rects for er in existing_rects): continue
                all_newly_placed_rects.extend(potential_rects)
                all_alignment_constraints.extend(potential_constraints)
                existing_rects.extend(potential_rects)
                current_id = next_id
                is_placed = True
                break
            if not is_placed:
                print(f"--- 警告: 無法為對齊群組 {group_id_str} 找到足夠空間 ---")

        print(f"--- 對齊群組生成完畢，共 {len(all_newly_placed_rects)} 個元件。 ---")
        return all_newly_placed_rects, all_alignment_constraints, current_id