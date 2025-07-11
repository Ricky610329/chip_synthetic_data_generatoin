# demo_generator.py (已修正物件屬性存取錯誤)

import random
import numpy as np
import yaml
import os
import time
import shutil

# --- 視覺化與 GIF 生成函式庫 ---
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import imageio

# --- 從專案中匯入必要的類別 ---
from generator import LayoutGenerator
from layout import Rectangle, Layout
from symmetry import SymmetricGenerator
from grouper import LayoutGrouper

# --- 全域變數，用於儲存生成的影格 ---
FRAME_DIR = "_frames_for_gif"
frame_files = []
frame_counter = 0

def load_config(path='config.yaml'):
    """載入設定檔"""
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def get_randomized_params(config):
    """從設定檔中獲取一組隨機參數"""
    params = config['base_params'].copy()
    for key, value in config.items():
        if isinstance(value, dict):
            params.setdefault(key, value.copy())
    for key, rule in config.get('randomize_params', {}).items():
        if rule['type'] == 'randint':
            params[key] = random.randint(rule['low'], rule['high'])
        elif rule['type'] == 'uniform':
            params[key] = random.uniform(rule['low'], rule['high'])
        elif rule['type'] == 'uniform_pair':
            val1 = random.uniform(rule['low'][0], rule['high'][0])
            val2 = random.uniform(rule['low'][1], rule['high'][1])
            params[key] = (min(val1, val2), max(val1, val2))
    return params

def save_frame(rects, params, title, is_final=False):
    """
    將目前的佈局狀態繪製並儲存為一張圖片。
    """
    global frame_counter
    
    fig, ax = plt.subplots(1, figsize=(10, 10))
    ax.set_xlim(0, params['CANVAS_WIDTH'])
    ax.set_ylim(params['CANVAS_HEIGHT'], 0) # 保持 Y 軸反轉
    ax.set_aspect('equal', adjustable='box')
    
    ax.set_facecolor('white')
    plt.title(title, fontsize=16, color='black', pad=20)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    # 繪製所有矩形
    for r in rects:
        x, y, w, h = r.x - r.w/2, r.y - r.h/2, r.w, r.h
        
        # ✨ FIX: Use direct attribute access (r.attribute) instead of dict access (r.get('attribute'))
        group_type = r.group_type

        if group_type == 'hierarchical':
            face_color = '#E1BEE7'; edge_color = '#6A1B9A'; alpha = 1.0
        elif group_type: # Covers 'vertical', 'horizontal', 'quad'
            face_color = 'mediumseagreen'; edge_color = 'darkgreen'; alpha = 1.0
        else:
            is_macro = r.growth_prob >= params.get('MACRO_GROWTH_PROB_RANGE', [0.7, 0.9])[0]
            face_color = 'skyblue' if is_macro else 'lightcoral'; edge_color = 'black'; alpha = 0.9

        rect_patch = patches.Rectangle((x, y), w, h, linewidth=1.5, edgecolor=edge_color, facecolor=face_color, alpha=alpha)
        ax.add_patch(rect_patch)

    # 繪製群組元件的 Pin
    for r in rects:
        if r.group_id and hasattr(r, 'pins') and r.pins:
            for pin in r.pins:
                abs_pos = (r.x + pin.rel_pos[0], r.y + pin.rel_pos[1])
                pin_marker = patches.Circle(abs_pos, radius=1.5, color='black', zorder=10)
                ax.add_patch(pin_marker)

    filepath = os.path.join(FRAME_DIR, f"frame_{frame_counter:05d}.png")
    plt.savefig(filepath, dpi=120, bbox_inches='tight', pad_inches=0.2, facecolor='white')
    plt.close(fig)
    
    duration_multiplier = 5 if is_final else 1
    for _ in range(duration_multiplier):
        frame_files.append(filepath)
        
    frame_counter += 1
    print(f"  [+] Saved Frame {frame_counter-1}: {title}")


class DemoLayoutGenerator(LayoutGenerator):
    """
    繼承自 LayoutGenerator，並在關鍵函式中插入儲存影格的邏輯。
    """
    def __init__(self, params):
        super().__init__(params)

    def _rollback_growth(self, rects):
        save_frame(rects, self.params, f"Stagnation Limit Hit! Rolling back...", is_final=True)
        result = super()._rollback_growth(rects)
        save_frame(result, self.params, f"After Rollback", is_final=False)
        return result

    def _shake_components(self, rects, legalize=False):
        title_prefix = "Final Legalization" if legalize else "Light Shake"
        save_frame(rects, self.params, f"{title_prefix}: Before", is_final=True)
        result = super()._shake_components(rects, legalize)
        save_frame(result, self.params, f"{title_prefix}: After", is_final=True)
        return result

    def _infill_empty_spaces(self, rects):
        save_frame(rects, self.params, f"Triggering In-fill...", is_final=True)
        result, success = super()._infill_empty_spaces(rects)
        if success:
            save_frame(result, self.params, f"After In-fill", is_final=False)
        return result, success

    def generate(self):
        p = self.params
        print(f"\n[DEMO] Starting Generation Loop...")
        start_time = time.time()
        
        rects = p.get('initial_rects', [])
        
        stagnation_counter = 0; shakes_since_last_infill = 0; infill_triggered_count = 0

        for i in range(p['MAX_ITERATIONS']):
            changed_this_iteration = False
            movable_rects = [r for r in rects if not r.fixed]
            random.shuffle(movable_rects)

            for r in movable_rects:
                if random.random() > r.growth_prob: continue
                original_x, original_y, original_w, original_h = r.x, r.y, r.w, r.h
                direction = random.choice(['right', 'left', 'down', 'up'])
                
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
                    r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h
                else:
                    changed_this_iteration = True
            
            current_density = sum(r.w * r.h for r in rects) / (p['CANVAS_WIDTH'] * p['CANVAS_HEIGHT'])
            if (i + 1) % 15 == 0:
                save_frame(rects, p, f"Iteration {i+1} | Density: {current_density:.2%}")

            if current_density >= p['TARGET_DENSITY']:
                print(f"\nTarget density reached {p['TARGET_DENSITY']:.2%}")
                break

            stagnation_counter = 0 if changed_this_iteration else stagnation_counter + 1
            if stagnation_counter >= p['SHAKE_TRIGGER_THRESHOLD']:
                if stagnation_counter >= p['STAGNATION_LIMIT']:
                    print(f"\nStagnation limit exceeded {p['STAGNATION_LIMIT']} iterations...")
                    break
                if shakes_since_last_infill >= p['INFILL_TRIGGER_AFTER_N_SHAKES'] and infill_triggered_count < p['INFILL_MAX_TRIGGERS']:
                    rects, success = self._infill_empty_spaces(rects)
                    if success:
                        infill_triggered_count += 1; shakes_since_last_infill = 0
                else:
                    rects = self._rollback_growth(rects)
                    rects = self._shake_components(rects)
                    shakes_since_last_infill += 1
                stagnation_counter = 0
                
        print("\n[DEMO] Generation loop finished. Performing final legalization...")
        final_rects = self._shake_components(rects, legalize=True)
                
        end_time = time.time()
        final_layout = Layout(p['CANVAS_WIDTH'], p['CANVAS_HEIGHT'])
        final_layout.rectangles = final_rects
        
        print(f"\nLayout generation complete. Time elapsed: {end_time - start_time:.2f} seconds")
        print(f"Final component count: {len(final_layout.rectangles)}, Final density: {final_layout.get_density():.3%}")
        return final_layout


def main():
    """
    主函式， orchestrates the entire demo generation process.
    """
    global frame_files, frame_counter
    
    print("--- Setting up Demo Generation ---")
    if os.path.exists(FRAME_DIR):
        shutil.rmtree(FRAME_DIR)
    os.makedirs(FRAME_DIR)
    
    config = load_config('config.yaml')
    params = get_randomized_params(config)
    
    seed = 42
    params['SEED'] = seed
    random.seed(seed); np.random.seed(seed)
    print(f"Parameters loaded. Using fixed SEED: {seed}")
    
    placed_rects = []
    last_id = -1
    last_pin_id = 0
    
    # A. 對稱元件
    print("\n--- Phase 1: Generating Symmetric Groups (with Pins) ---")
    if params.get('analog_symmetry_settings', {}).get('enable', False):
        sym_gen = SymmetricGenerator(params)
        _, last_id, last_pin_id = sym_gen.generate_analog_groups(
            start_id=0, start_pin_id=0, existing_rects=placed_rects
        )
    save_frame(placed_rects, params, "Phase 1: Symmetric Groups Placed", is_final=True)

    # B. 隨機元件
    print("\n--- Phase 2: Placing Initial Random Components ---")
    num_macros = int(params['NUM_RECTANGLES'] * params['MACRO_RATIO'])
    for j in range(params['NUM_RECTANGLES']):
        is_placed = False
        for _ in range(200):
            rand_x = random.uniform(1, params['CANVAS_WIDTH'] - 1)
            rand_y = random.uniform(1, params['CANVAS_HEIGHT'] - 1)
            temp_rect = Rectangle(None, rand_x, rand_y, 1, 1)
            if not any(temp_rect.intersects(r) for r in placed_rects):
                prob = (random.uniform(*params['MACRO_GROWTH_PROB_RANGE']) if j < num_macros 
                        else random.uniform(*params['STD_CELL_GROWTH_PROB_RANGE']))
                last_id += 1
                new_rect = Rectangle(rect_id=last_id, x=rand_x, y=rand_y, w=1, h=1, growth_prob=prob)
                placed_rects.append(new_rect)
                is_placed = True
                break
        if not is_placed:
             print(f"Warning: Could not find space for random component {j+1}. Skipping.")
    save_frame(placed_rects, params, "Phase 2: Initial Random Components Placed", is_final=True)
    
    # C. 階層式分組
    print("\n--- Phase 2.5: Applying Hierarchical Grouping ---")
    if params.get('grouping_settings', {}).get('enable', False):
        temp_layout = Layout(params['CANVAS_WIDTH'], params['CANVAS_HEIGHT'])
        temp_layout.rectangles = placed_rects
        grouper = LayoutGrouper(temp_layout, params)
        grouper.create_hierarchical_groups()
    save_frame(placed_rects, params, "Phase 2.5: Hierarchical Groups Formed", is_final=True)

    # D. 生長與優化
    print("\n--- Phase 3: Growth and Optimization ---")
    params['initial_rects'] = placed_rects
    demo_generator = DemoLayoutGenerator(params)
    final_layout = demo_generator.generate()
    
    save_frame(final_layout.rectangles, params, "Final Layout", is_final=True)

    # E. 產生 GIF
    print("\n--- Phase 4: Compiling GIF ---")
    gif_path = "layout_generation_demo.gif"
    with imageio.get_writer(gif_path, mode='I', duration=0.12) as writer:
        for filename in frame_files:
            image = imageio.v2.imread(filename)
            writer.append_data(image)
    print(f"Success! GIF saved to: {gif_path}")

    # F. 清理
    print("\n--- Phase 5: Cleaning up temporary files ---")
    shutil.rmtree(FRAME_DIR)
    print("Done.")

if __name__ == "__main__":
    main()