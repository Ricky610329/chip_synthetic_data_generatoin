# demo_generator.py
import yaml
import random
import copy
import math
import time
import os
import imageio
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from tqdm import tqdm

# --- 從 layout.py 引入的核心資料結構 ---

class Pin:
    def __init__(self, pin_id, parent_rect, rel_pos):
        self.id = pin_id
        self.parent_rect = parent_rect
        self.rel_pos = rel_pos

class Rectangle:
    def __init__(self, rect_id, x, y, w, h, growth_prob=0.5):
        self.id = rect_id
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.growth_prob = growth_prob

    def intersects(self, other):
        return not (self.x + self.w / 2 < other.x - other.w / 2 or
                    self.x - self.w / 2 > other.x + other.w / 2 or
                    self.y + self.h / 2 < other.y - other.h / 2 or
                    self.y - self.h / 2 > other.y + other.h / 2)

    def is_point_inside(self, px, py):
        return (px >= self.x - self.w/2 and px <= self.x + self.w/2 and
                py >= self.y - self.h/2 and py <= self.y + self.h/2)

# --- 從 generator.py 引入的演算法核心 ---

class QuadTree:
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

class DemoLayoutGenerator:
    """
    修改過的 LayoutGenerator，增加了在生成過程中產生影格的功能。
    """
    def __init__(self, params):
        self.params = params
        self.frames = [] # 用來儲存每一幀的圖片路徑
        self.frame_dir = "demo_frames"
        os.makedirs(self.frame_dir, exist_ok=True)

    def _save_frame(self, rects, iteration, message):
        """繪製並儲存目前佈局狀態為一張圖片"""
        p = self.params
        fig, ax = plt.subplots(1, figsize=(10, 10))
        ax.set_xlim(0, p['CANVAS_WIDTH'])
        ax.set_ylim(0, p['CANVAS_HEIGHT'])
        ax.set_aspect('equal', adjustable='box')
        
        # 繪製元件
        for r in rects:
            is_macro = r.growth_prob >= p['MACRO_GROWTH_PROB_RANGE'][0]
            face_color = 'skyblue' if is_macro else 'lightcoral'
            rect_patch = patches.Rectangle((r.x - r.w/2, r.y - r.h/2), r.w, r.h, linewidth=1, edgecolor='black', facecolor=face_color, alpha=0.8)
            ax.add_patch(rect_patch)

        density = sum(r.w * r.h for r in rects) / (p['CANVAS_WIDTH'] * p['CANVAS_HEIGHT'])
        plt.title(f"Iteration: {iteration} | Density: {density:.3%} | {message}", fontsize=12)
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.gca().invert_yaxis()
        
        frame_path = os.path.join(self.frame_dir, f"frame_{len(self.frames):04d}.png")
        plt.savefig(frame_path)
        plt.close(fig) # 關閉圖像以釋放記憶體
        self.frames.append(frame_path)

    def _rollback_growth(self, rects):
        shrink_amount = self.params['ROLLBACK_STEPS'] * self.params['GROWTH_STEP']
        for r in rects:
            r.w = max(1, r.w - shrink_amount)
            r.h = max(1, r.h - shrink_amount)
        return rects

    def _shake_components(self, rects, legalize=False):
        strength = self.params['SHAKE_STRENGTH']
        max_passes = 100 if legalize else self.params['SHAKE_ITERATIONS']
        
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
                break
            
            for r in current_rects:
                vec = shake_vectors[r.id]; r.x += vec[0] * strength; r.y += vec[1] * strength
                r.x = max(r.w / 2, min(r.x, self.params['CANVAS_WIDTH'] - r.w / 2))
                r.y = max(r.h / 2, min(r.y, self.params['CANVAS_HEIGHT'] - r.h / 2))
        
        return current_rects

    def _infill_empty_spaces(self, rects):
        num_to_add = self.params['INFILL_COMPONENT_COUNT']
        empty_points = []
        step_x = self.params['CANVAS_WIDTH'] / self.params['INFILL_GRID_DENSITY']
        step_y = self.params['CANVAS_HEIGHT'] / self.params['INFILL_GRID_DENSITY']
        for i in range(self.params['INFILL_GRID_DENSITY']):
            for j in range(self.params['INFILL_GRID_DENSITY']):
                px, py = i * step_x, j * step_y
                is_empty = all(not r.is_point_inside(px, py) for r in rects)
                if is_empty: empty_points.append((px, py))
        
        if not empty_points: return rects, False
            
        new_points = random.sample(empty_points, min(num_to_add, len(empty_points)))
        max_id = max(r.id for r in rects) if rects else -1
        for idx, (px, py) in enumerate(new_points):
            new_id = max_id + 1 + idx
            prob = random.uniform(self.params['STD_CELL_GROWTH_PROB_RANGE'][0], self.params['STD_CELL_GROWTH_PROB_RANGE'][1])
            rects.append(Rectangle(rect_id=new_id, x=px, y=py, w=1, h=1, growth_prob=prob))
        return rects, True

    def generate(self, frame_interval=50):
        p = self.params
        rects = []
        num_macros = int(p['NUM_RECTANGLES'] * p['MACRO_RATIO'])
        for i in range(p['NUM_RECTANGLES']):
            prob = (random.uniform(*p['MACRO_GROWTH_PROB_RANGE']) if i < num_macros 
                    else random.uniform(*p['STD_CELL_GROWTH_PROB_RANGE']))
            rects.append(Rectangle(rect_id=i, x=random.uniform(0, p['CANVAS_WIDTH']), 
                                   y=random.uniform(0, p['CANVAS_HEIGHT']), w=1, h=1, growth_prob=prob))
        
        self._save_frame(rects, 0, "Initial Placement")

        stagnation_counter = 0; shakes_since_last_infill = 0; infill_triggered_count = 0
        growth_directions = ['right', 'left', 'down', 'up']

        for i in tqdm(range(p['MAX_ITERATIONS']), desc="Generating Layout"):
            changed_this_iteration = False
            random.shuffle(rects)
            for r in rects:
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
                    
                    collided = any(r.intersects(other_r) for other_r in rects if r.id != other_r.id)
                    
                    if collided:
                        r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h; continue
                    else:
                        changed_this_iteration = True; has_grown_this_turn = True; break
                
                if not has_grown_this_turn: r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h
            
            if (i + 1) % frame_interval == 0:
                self._save_frame(rects, i + 1, "Growing...")

            current_density = sum(r.w * r.h for r in rects) / (p['CANVAS_WIDTH'] * p['CANVAS_HEIGHT'])
            if current_density >= p['TARGET_DENSITY']: break

            stagnation_counter = 0 if changed_this_iteration else stagnation_counter + 1

            if stagnation_counter >= p['SHAKE_TRIGGER_THRESHOLD']:
                if stagnation_counter >= p['STAGNATION_LIMIT']: break
                
                event_message = ""
                if shakes_since_last_infill >= p['INFILL_TRIGGER_AFTER_N_SHAKES'] and infill_triggered_count < p['INFILL_MAX_TRIGGERS']:
                    rects, success = self._infill_empty_spaces(rects)
                    if success: 
                        infill_triggered_count += 1; shakes_since_last_infill = 0
                        event_message = f"In-fill Triggered ({infill_triggered_count})"
                else:
                    rects = self._rollback_growth(rects)
                    rects = self._shake_components(rects)
                    shakes_since_last_infill += 1
                    event_message = f"Rollback & Shake Triggered ({shakes_since_last_infill})"
                self._save_frame(rects, i + 1, event_message)
                stagnation_counter = 0
                
        self._save_frame(rects, p['MAX_ITERATIONS'], "Final Growth Result")
        final_rects = self._shake_components(rects, legalize=True)
        self._save_frame(final_rects, p['MAX_ITERATIONS'], "After Final Legalization")
        
        return self.frames

# --- 主執行函式 ---

def load_config(path='config.yaml'):
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def get_randomized_params(config):
    params = config['base_params'].copy()
    for key, rule in config['randomize_params'].items():
        if rule['type'] == 'randint':
            params[key] = random.randint(rule['low'], rule['high'])
        elif rule['type'] == 'uniform':
            params[key] = random.uniform(rule['low'], rule['high'])
        elif rule['type'] == 'uniform_pair':
            val1 = random.uniform(rule['low'][0], rule['high'][0])
            val2 = random.uniform(rule['low'][1], rule['high'][1])
            params[key] = (min(val1, val2), max(val1, val2))
    return params

def main():
    config = load_config('config.yaml')
    params = get_randomized_params(config)
    
    # --- 您可以在這裡手動覆蓋參數以進行特定測試 ---
    # params['MAX_ASPECT_RATIO'] = 3.5 
    # params['NUM_RECTANGLES'] = 150
    # 解決您上次遇到的問題
    if params['GROWTH_STEP'] >= params['MAX_ASPECT_RATIO']:
        print("警告: GROWTH_STEP >= MAX_ASPECT_RATIO，可能導致無法生長。自動調整 GROWTH_STEP 為 1。")
        params['GROWTH_STEP'] = 1
    # ----------------------------------------------------

    seed = random.randint(0, 2**32 - 1)
    params['SEED'] = seed
    random.seed(seed)
    np.random.seed(seed)
    
    print(f"--- 開始生成 Demo 動畫 ---")
    print(f"使用種子: {seed}, 元件數: {params['NUM_RECTANGLES']}, 目標密度: {params['TARGET_DENSITY']:.2f}")

    generator = DemoLayoutGenerator(params)
    
    # 執行生成並獲取所有影格的路徑
    # frame_interval 控制每隔多少次迭代儲存一次影格，數值越小，GIF越慢越長
    frame_paths = generator.generate(frame_interval=25) 

    if frame_paths:
        output_gif_path = "layout_generation_demo.gif"
        print(f"\n生成影格完畢，共 {len(frame_paths)} 幀。")
        print(f"正在將影格合成為 GIF: {output_gif_path} ...")
        
        # 使用 imageio 將圖片序列合成為 GIF
        with imageio.get_writer(output_gif_path, mode='I', duration=100, loop=0, subrectangles=True) as writer:
            for filename in tqdm(frame_paths, desc="Composing GIF"):
                image = imageio.imread(filename)
                writer.append_data(image)
        
        print(f"GIF 動畫已成功儲存！")

        # (可選) 清理單獨的影格圖片
        print("正在清理暫存影格...")
        for filename in frame_paths:
            os.remove(filename)
        os.rmdir(generator.frame_dir)
        print("清理完畢。")

    else:
        print("生成失敗，未產生任何影格。")

if __name__ == "__main__":
    main()