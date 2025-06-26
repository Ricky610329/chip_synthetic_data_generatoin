# generator.py

import random
import copy
import math
import time
from layout import Rectangle, Layout

# 將 QuadTree 放在 generator 中，因為它是演算法加速工具，而非核心資料結構
class QuadTree:
    """四分樹用於加速鄰近搜索"""
    def __init__(self, boundary, capacity=4):
        self.boundary = boundary; self.capacity = capacity; self.rects = []; self.divided = False
    def subdivide(self):
        x, y, w, h = self.boundary.x, self.boundary.y, self.boundary.w, self.boundary.h
        self.northeast = QuadTree(Rectangle(None, x + w / 4, y + h / 4, w / 2, h / 2), self.capacity)
        self.northwest = QuadTree(Rectangle(None, x - w / 4, y + h / 4, w / 2, h / 2), self.capacity)
        self.southeast = QuadTree(Rectangle(None, x + w / 4, y - h / 4, w / 2, h / 2), self.capacity)
        self.southwest = QuadTree(Rectangle(None, x - w / 4, y - h / 4, w / 2, h / 2), self.capacity)
        self.divided = True
    def insert(self, rect):
        if not self.boundary.intersects(rect): return False
        if len(self.rects) < self.capacity: self.rects.append(rect); return True
        else:
            if not self.divided: self.subdivide()
            if self.northeast.insert(rect): return True;
            if self.northwest.insert(rect): return True;
            if self.southeast.insert(rect): return True;
            if self.southwest.insert(rect): return True;
    def query(self, range_rect):
        found = [];
        if not self.boundary.intersects(range_rect): return found
        for r in self.rects:
            if range_rect.intersects(r): found.append(r)
        if self.divided:
            found.extend(self.northeast.query(range_rect)); found.extend(self.northwest.query(range_rect));
            found.extend(self.southeast.query(range_rect)); found.extend(self.southwest.query(range_rect));
        return found


class LayoutGenerator:
    """佈局生成器，封裝了所有的生成演算法"""
    def __init__(self, params):
        self.params = params

    def _rollback_growth(self, rects):
        print(f"--- 觸發回退！所有元件縮小 {self.params['ROLLBACK_STEPS']} 步... ---")
        shrink_amount = self.params['ROLLBACK_STEPS'] * self.params['GROWTH_STEP']
        for r in rects:
            r.w = max(1, r.w - shrink_amount)
            r.h = max(1, r.h - shrink_amount)
        return rects

    def _shake_components(self, rects, legalize=False):
        strength = self.params['SHAKE_STRENGTH']
        if legalize:
            print("--- 執行最終強制合法化 Shake... ---")
            max_passes = 100
        else:
            print("--- 觸發輕量 Shake... ---")
            max_passes = self.params['SHAKE_ITERATIONS']
        
        current_rects = copy.deepcopy(rects)
        for pass_num in range(max_passes):
            boundary = Rectangle(None, self.params['CANVAS_WIDTH']/2, self.params['CANVAS_HEIGHT']/2, self.params['CANVAS_WIDTH'], self.params['CANVAS_HEIGHT'])
            qtree = QuadTree(boundary, 4)
            for r in current_rects: qtree.insert(r)
            
            shake_vectors = {r.id: [0, 0] for r in current_rects}
            total_overlaps = 0
            for r in current_rects:
                neighbors = qtree.query(r)
                for neighbor in neighbors:
                    if r.id >= neighbor.id: continue
                    dx = r.x - neighbor.x; dy = r.y - neighbor.y
                    overlap_x = (r.w / 2 + neighbor.w / 2) - abs(dx)
                    overlap_y = (r.h / 2 + neighbor.h / 2) - abs(dy)
                    if overlap_x > 0 and overlap_y > 0:
                        total_overlaps += 1
                        push_vec = (math.copysign(overlap_x, dx), 0) if overlap_x < overlap_y else (0, math.copysign(overlap_y, dy))
                        shake_vectors[r.id][0] += push_vec[0]; shake_vectors[r.id][1] += push_vec[1]
                        shake_vectors[neighbor.id][0] -= push_vec[0]; shake_vectors[neighbor.id][1] -= push_vec[1]
            
            if legalize and total_overlaps == 0:
                print(f"--- Shake 在第 {pass_num + 1} 輪後完成，已無重疊。 ---")
                return current_rects
            
            for r in current_rects:
                vec = shake_vectors[r.id]; r.x += vec[0] * strength; r.y += vec[1] * strength
                r.x = max(r.w / 2, min(r.x, self.params['CANVAS_WIDTH'] - r.w / 2))
                r.y = max(r.h / 2, min(r.y, self.params['CANVAS_HEIGHT'] - r.h / 2))
        
        if legalize and total_overlaps > 0: print(f"--- 警告：最終合法化結束，仍有 {total_overlaps} 個重疊。 ---")
        return current_rects

    def _infill_empty_spaces(self, rects):
        num_to_add = self.params['INFILL_COMPONENT_COUNT']
        print(f"--- 觸發 In-fill！正在尋找 {num_to_add} 個空白點... ---")
        empty_points = []
        step_x = self.params['CANVAS_WIDTH'] / self.params['INFILL_GRID_DENSITY']
        step_y = self.params['CANVAS_HEIGHT'] / self.params['INFILL_GRID_DENSITY']
        for i in range(self.params['INFILL_GRID_DENSITY']):
            for j in range(self.params['INFILL_GRID_DENSITY']):
                px, py = i * step_x, j * step_y
                is_empty = all(not r.is_point_inside(px, py) for r in rects)
                if is_empty: empty_points.append((px, py))
        
        if not empty_points:
            print("--- 警告：找不到任何空白點可供填充。 ---")
            return rects, False
            
        new_points = random.sample(empty_points, min(num_to_add, len(empty_points)))
        max_id = max(r.id for r in rects) if rects else -1
        for idx, (px, py) in enumerate(new_points):
            new_id = max_id + 1 + idx
            prob = random.uniform(self.params['STD_CELL_GROWTH_PROB_RANGE'][0], self.params['STD_CELL_GROWTH_PROB_RANGE'][1])
            rects.append(Rectangle(rect_id=new_id, x=px, y=py, w=1, h=1, growth_prob=prob))
        print(f"--- 成功加入 {len(new_points)} 個新元件！ ---")
        return rects, True

    def generate(self):
        """ 主生成函式，採用「智慧成長」和「尺寸差異化」邏輯 """
        p = self.params # 簡化參數訪問
        print(f"開始生成佈局 (模組化版)...")
        start_time = time.time()
        
        rects = []
        num_macros = int(p['NUM_RECTANGLES'] * p['MACRO_RATIO'])
        for i in range(p['NUM_RECTANGLES']):
            prob = (random.uniform(*p['MACRO_GROWTH_PROB_RANGE']) if i < num_macros 
                    else random.uniform(*p['STD_CELL_GROWTH_PROB_RANGE']))
            rects.append(Rectangle(rect_id=i, x=random.uniform(0, p['CANVAS_WIDTH']), 
                                   y=random.uniform(0, p['CANVAS_HEIGHT']), w=1, h=1, growth_prob=prob))

        stagnation_counter = 0; shakes_since_last_infill = 0; infill_triggered_count = 0
        growth_directions = ['right', 'left', 'down', 'up']

        for i in range(p['MAX_ITERATIONS']):
            changed_this_iteration = False
            random.shuffle(rects)
            for r_idx, r in enumerate(rects):
                if random.random() > r.growth_prob: continue
                random.shuffle(growth_directions)
                has_grown_this_turn = False
                for direction in growth_directions:
                    original_x, original_y, original_w, original_h = r.x, r.y, r.w, r.h
                    if direction == 'right': r.w += p['GROWTH_STEP']; r.x += p['GROWTH_STEP'] / 2
                    elif direction == 'left': r.w += p['GROWTH_STEP']; r.x -= p['GROWTH_STEP'] / 2
                    elif direction == 'down': r.h += p['GROWTH_STEP']; r.y += p['GROWTH_STEP'] / 2
                    elif direction == 'up': r.h += p['GROWTH_STEP']; r.y -= p['GROWTH_STEP'] / 2
                    
                    if (r.w / r.h > p['MAX_ASPECT_RATIO']) or (r.h / r.w > p['MAX_ASPECT_RATIO']):
                        r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h; continue
                    if (r.x - r.w/2 < 0 or r.x + r.w/2 > p['CANVAS_WIDTH'] or 
                        r.y - r.h/2 < 0 or r.y + r.h/2 > p['CANVAS_HEIGHT']):
                        r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h; continue
                    
                    collided = any(r.intersects(other_r) for other_r_idx, other_r in enumerate(rects) if r_idx != other_r_idx)
                    
                    if collided:
                        r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h; continue
                    else:
                        changed_this_iteration = True; has_grown_this_turn = True; break
                
                if not has_grown_this_turn: r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h

            current_density = sum(r.w * r.h for r in rects) / (p['CANVAS_WIDTH'] * p['CANVAS_HEIGHT'])
            if (i + 1) % 50 == 0:
                print(f"迭代 {i+1} | 密度: {current_density:.3%} | 連續停滯: {stagnation_counter} | Shake計數: {shakes_since_last_infill} | 元件數: {len(rects)}")
            
            if current_density >= p['TARGET_DENSITY']: print(f"\n已達到目標密度 {p['TARGET_DENSITY']:.2%}"); break

            stagnation_counter = 0 if changed_this_iteration else stagnation_counter + 1

            if stagnation_counter >= p['SHAKE_TRIGGER_THRESHOLD']:
                if stagnation_counter >= p['STAGNATION_LIMIT']: print(f"\n系統停滯超過 {p['STAGNATION_LIMIT']} 輪，最終停止生成。"); break
                
                if shakes_since_last_infill >= p['INFILL_TRIGGER_AFTER_N_SHAKES'] and infill_triggered_count < p['INFILL_MAX_TRIGGERS']:
                    rects, success = self._infill_empty_spaces(rects)
                    if success: infill_triggered_count += 1; shakes_since_last_infill = 0
                else:
                    rects = self._rollback_growth(rects)
                    rects = self._shake_components(rects)
                    shakes_since_last_infill += 1
                stagnation_counter = 0
                
        print("\n生成迴圈結束，執行最後的合法化整理...")
        final_rects = self._shake_components(rects, legalize=True)
                
        end_time = time.time()
        final_layout = Layout(p['CANVAS_WIDTH'], p['CANVAS_HEIGHT'])
        final_layout.rectangles = final_rects
        
        print(f"\n佈局生成完畢，耗時: {end_time - start_time:.2f} 秒")
        print(f"最終元件數量: {len(final_layout.rectangles)}, 最終密度: {final_layout.get_density():.3%}")
        return final_layout