# alignment.py (已修改為真正的邊緣對齊)

import random
from layout import Rectangle

class AlignmentGenerator:
    """
    生成具有特定對齊關係 (左/右/上/下邊緣對齊, 水平/垂直置中) 的元件集合。
    """
    def __init__(self, main_params):
        self.params = main_params
        self.align_config = main_params['alignment_settings']
        self.canvas_w = main_params['CANVAS_WIDTH']
        self.canvas_h = main_params['CANVAS_HEIGHT']

    def _generate_set(self, start_id, group_id, existing_rects):
        """為單個對齊集合生成所有元件和約束。"""
        num_components = random.randint(self.align_config['components_per_set']['low'], 
                                        self.align_config['components_per_set']['high'])
        
        mode_choices = self.align_config['alignment_mode_weights']
        modes = [choice['mode'] for choice in mode_choices]
        weights = [choice['weight'] for choice in mode_choices]
        align_mode = random.choices(modes, weights=weights, k=1)[0]
        
        generated_rects = []
        alignment_constraints = []
        current_id = start_id

        # 1. 生成種子元件，它的位置將決定整個群組的對齊基準線
        w_seed = random.uniform(*self.align_config['component_width_range'])
        h_seed = random.uniform(*self.align_config['component_height_range'])
        
        padding = 100 # 確保元件群組不會生成在太靠近畫布邊緣的地方
        x_seed = random.uniform(padding + w_seed/2, self.canvas_w - padding - w_seed/2)
        y_seed = random.uniform(padding + h_seed/2, self.canvas_h - padding - h_seed/2)
        
        seed_rect = Rectangle(current_id, x_seed, y_seed, w_seed, h_seed)
        seed_rect.fixed = True
        seed_rect.group_id = group_id
        seed_rect.group_type = 'aligned'
        
        generated_rects.append(seed_rect)
        last_rect = seed_rect
        current_id += 1

        # 2. 基於種子元件，生成後續的對齊元件
        for i in range(1, num_components):
            w = random.uniform(*self.align_config['component_width_range'])
            h = random.uniform(*self.align_config['component_height_range'])
            gap = random.uniform(*self.align_config['gap_range'])

            # =================================================================
            # ✨ 核心修改：重寫座標計算邏輯 ✨
            # =================================================================

            # --- A. 真正的「邊緣」對齊 ---
            # 說明：元件將沿著一條固定的軸線排列（例如垂直堆疊），
            # 同時它們的特定邊緣會對齊到由 seed_rect 決定的基準線上。

            if align_mode == 'left':
                # [目標] 左邊緣對齊，垂直堆疊
                # X 座標: 新元件的左邊緣 (x - w/2) 需與種子元件的左邊緣對齊
                align_line_x = seed_rect.x - seed_rect.w / 2
                new_x = align_line_x + w / 2
                # Y 座標: 在前一個元件的下方，並留有間隙
                new_y = last_rect.y + last_rect.h / 2 + gap + h / 2
                
            elif align_mode == 'right':
                # [目標] 右邊緣對齊，垂直堆疊
                # X 座標: 新元件的右邊緣 (x + w/2) 需與種子元件的右邊緣對齊
                align_line_x = seed_rect.x + seed_rect.w / 2
                new_x = align_line_x - w / 2
                # Y 座標: 在前一個元件的下方
                new_y = last_rect.y + last_rect.h / 2 + gap + h / 2

            elif align_mode == 'top':
                # [目標] 上邊緣對齊，水平排列
                # Y 座標: 新元件的上邊緣 (y - h/2) 需與種子元件的上邊緣對齊
                align_line_y = seed_rect.y - seed_rect.h / 2
                new_y = align_line_y + h / 2
                # X 座標: 在前一個元件的右方
                new_x = last_rect.x + last_rect.w / 2 + gap + w / 2
                
            elif align_mode == 'bottom':
                # [目標] 下邊緣對齊，水平排列
                # Y 座標: 新元件的下邊緣 (y + h/2) 需與種子元件的下邊緣對齊
                align_line_y = seed_rect.y + seed_rect.h / 2
                new_y = align_line_y - h / 2
                # X 座標: 在前一個元件的右方
                new_x = last_rect.x + last_rect.w / 2 + gap + w / 2

            # --- B. 明確的「中心」對齊 ---
            # 說明：這裡我們使用舊的邏輯，但將其明確地賦予給 h_center 和 v_center。
            
            elif align_mode == 'h_center': 
                # [目標] 水平置中，垂直堆疊
                new_x = seed_rect.x # 所有元件的 X 中心點與種子元件相同
                new_y = last_rect.y + last_rect.h / 2 + gap + h / 2

            elif align_mode == 'v_center':
                # [目標] 垂直置中，水平排列
                new_y = seed_rect.y # 所有元件的 Y 中心點與種子元件相同
                new_x = last_rect.x + last_rect.w / 2 + gap + w / 2

            # 3. 創建新的 Rectangle 物件並儲存約束
            new_rect = Rectangle(current_id, new_x, new_y, w, h)
            new_rect.fixed = True
            new_rect.group_id = group_id
            new_rect.group_type = 'aligned'
            
            # 約束仍然是基於相鄰元件之間的關係
            alignment_constraints.append((last_rect.id, new_rect.id, align_mode))

            generated_rects.append(new_rect)
            last_rect = new_rect
            current_id += 1
            
        return generated_rects, alignment_constraints, current_id

    def generate_aligned_sets(self, start_id, existing_rects):
        """
        (此函數不變) 生成多個對齊集合，並確保它們之間不重疊。
        """
        print("\n--- 開始生成對齊約束群組 (使用邊緣對齊邏輯) ---")
        num_sets_config = self.align_config.get('num_sets', {'low': 2, 'high': 5})
        num_sets = random.randint(num_sets_config['low'], num_sets_config['high'])
        
        all_newly_placed_rects = []
        all_alignment_constraints = []
        current_id = start_id
        
        for i in range(num_sets):
            group_id_str = f"align_group_{i}"
            is_placed = False
            for _ in range(150): # 嘗試 150 次以找到不重疊的位置
                
                potential_rects, potential_constraints, next_id = self._generate_set(current_id, group_id_str, existing_rects)
                
                # 邊界檢查
                if any(not (r.x - r.w/2 >= 0 and r.x + r.w/2 <= self.canvas_w and r.y - r.h/2 >= 0 and r.y + r.h/2 <= self.canvas_h) for r in potential_rects):
                    continue
                
                # 與所有已放置的元件檢查重疊
                if any(pr.intersects(er) for pr in potential_rects for er in existing_rects):
                    continue

                # 如果成功，則確認放置
                all_newly_placed_rects.extend(potential_rects)
                all_alignment_constraints.extend(potential_constraints)
                existing_rects.extend(potential_rects)
                current_id = next_id
                is_placed = True
                align_mode_used = potential_constraints[0][2] if potential_constraints else "N/A"
                print(f"  - 成功放置對齊群組 '{group_id_str}' (模式: {align_mode_used}, 元件數: {len(potential_rects)})")
                break
            
            if not is_placed:
                print(f"--- 警告: 無法為對齊群組 {group_id_str} 找到足夠空間，已略過。 ---")

        print(f"--- 對齊群組生成完畢，共生成 {len(all_newly_placed_rects)} 個元件。 ---")
        return all_newly_placed_rects, all_alignment_constraints, current_id