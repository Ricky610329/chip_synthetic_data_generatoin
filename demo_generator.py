# demo_generator.py

import random
import numpy as np
import yaml
import os
import time
import shutil
import imageio
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from generator import LayoutGenerator
from layout import Layout, Rectangle
from symmetry import SymmetricGenerator
from alignment import AlignmentGenerator
from grouper import LayoutGrouper

FRAME_DIR = "_frames_for_gif"
frame_files = []
frame_counter = 0

def load_config(path='config.yaml'):
    """載入設定檔"""
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

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
    return params

def save_frame(rects, params, title, is_final=False):
    """將目前的佈局狀態繪製並儲存為一張圖片。"""
    global frame_counter
    
    fig, ax = plt.subplots(1, figsize=(10, 10))
    ax.set_xlim(0, params['CANVAS_WIDTH'])
    ax.set_ylim(params['CANVAS_HEIGHT'], 0)
    ax.set_aspect('equal', adjustable='box')
    ax.set_facecolor('white')
    plt.title(title, fontsize=16, color='black', pad=20)
    ax.grid(True, linestyle='--', alpha=0.6)
    
    for r in rects:
        x, y, w, h = r.x - r.w/2, r.y - r.h/2, r.w, r.h
        
        constraints = r.constraints
        component_type = r.component_type

        # 更新後的著色邏輯，帶有優先級
        if 'grouping_id' in constraints:
            face_color, edge_color = '#E1BEE7', '#6A1B9A' # 紫色系 (階層)
        elif 'symmetry_id' in constraints:
            face_color, edge_color = '#C8E6C9', '#2E7D32' # 綠色系 (對稱)
        elif 'alignment_id' in constraints:
            face_color, edge_color = '#FFECB3', '#FF8F00' # 橘黃色系 (對齊)
        elif component_type == 'macro':
            face_color, edge_color = '#2196F3', '#0D47A1' # 深藍色系 (Macro)
        elif component_type == 'std_cell':
            face_color, edge_color = '#BBDEFB', '#42A5F5' # 淺藍色系 (Std Cell)
        else:
            face_color, edge_color = '#CFD8DC', '#37474F' # 灰色系

        rect_patch = patches.Rectangle((x, y), w, h, linewidth=1.5, edgecolor=edge_color, facecolor=face_color, alpha=0.9)
        ax.add_patch(rect_patch)

    filepath = os.path.join(FRAME_DIR, f"frame_{frame_counter:05d}.png")
    plt.savefig(filepath, dpi=120, bbox_inches='tight', pad_inches=0.2, facecolor='white')
    plt.close(fig)
    
    duration_multiplier = 5 if is_final else 1
    for _ in range(duration_multiplier):
        frame_files.append(filepath)
        
    frame_counter += 1
    print(f"  [+] Saved Frame {frame_counter-1}: {title}")


class DemoLayoutGenerator(LayoutGenerator):
    """繼承自 LayoutGenerator，並在關鍵函式中插入儲存影格的邏輯。"""
    def _rollback_growth(self, rects):
        save_frame(rects, self.params, "Stagnation Limit Hit! Rolling back...", is_final=True)
        result = super()._rollback_growth(rects)
        save_frame(result, self.params, "After Rollback", is_final=False)
        return result

    def _shake_components(self, rects, legalize=False):
        title_prefix = "Final Legalization" if legalize else "Light Shake"
        save_frame(rects, self.params, f"{title_prefix}: Before", is_final=True)
        result = super()._shake_components(rects, legalize)
        save_frame(result, self.params, f"{title_prefix}: After", is_final=True)
        return result

    def _infill_empty_spaces(self, rects):
        save_frame(rects, self.params, "Triggering In-fill...", is_final=True)
        result, success = super()._infill_empty_spaces(rects)
        if success:
            save_frame(result, self.params, "After In-fill", is_final=False)
        return result, success

    def generate(self):
        p = self.params
        print("\n[DEMO] Starting Generation Loop...")
        rects = p.get('initial_rects', [])
        
        stagnation_counter, shakes_since_last_infill, infill_triggered_count = 0, 0, 0

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
                else: r.h += p['GROWTH_STEP']; r.y -= p['GROWTH_STEP'] / 2
                
                if (r.w / r.h > p['MAX_ASPECT_RATIO']) or (r.h / r.w > p['MAX_ASPECT_RATIO']):
                    r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h; continue
                if not (0 <= r.x - r.w/2 and r.x + r.w/2 <= p['CANVAS_WIDTH'] and 0 <= r.y - r.h/2 and r.y + r.h/2 <= p['CANVAS_HEIGHT']):
                    r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h; continue
                
                if any(r.intersects(other_r) for other_r in rects if r.id != other_r.id):
                    r.x, r.y, r.w, r.h = original_x, original_y, original_w, original_h
                else:
                    changed_this_iteration = True
            
            current_density = sum(r.w * r.h for r in rects) / (p['CANVAS_WIDTH'] * p['CANVAS_HEIGHT'])
            if (i + 1) % 15 == 0:
                save_frame(rects, p, f"Iteration {i+1} | Density: {current_density:.2%}")

            if current_density >= p['TARGET_DENSITY']: print(f"\nTarget density reached {p['TARGET_DENSITY']:.2%}"); break

            stagnation_counter = 0 if changed_this_iteration else stagnation_counter + 1
            if stagnation_counter >= p['SHAKE_TRIGGER_THRESHOLD']:
                if stagnation_counter >= p['STAGNATION_LIMIT']: print(f"\nStagnation limit exceeded {p['STAGNATION_LIMIT']} iterations..."); break
                if shakes_since_last_infill >= p['INFILL_TRIGGER_AFTER_N_SHAKES'] and infill_triggered_count < p['INFILL_MAX_TRIGGERS']:
                    rects, success = self._infill_empty_spaces(rects)
                    if success: infill_triggered_count += 1; shakes_since_last_infill = 0
                else:
                    rects = self._rollback_growth(rects); rects = self._shake_components(rects)
                    shakes_since_last_infill += 1
                stagnation_counter = 0
                
        print("\n[DEMO] Generation loop finished. Performing final legalization...")
        final_rects = self._shake_components(rects, legalize=True)
                
        final_layout = Layout(p['CANVAS_WIDTH'], p['CANVAS_HEIGHT'])
        final_layout.rectangles = final_rects
        return final_layout

def main():
    global frame_files, frame_counter
    
    print("--- Setting up Demo Generation ---")
    if os.path.exists(FRAME_DIR): shutil.rmtree(FRAME_DIR)
    os.makedirs(FRAME_DIR)
    
    config = load_config('config.yaml')
    params = get_randomized_params(config)
    
    seed = random.randint(0, 2**32 - 1)
    params['SEED'] = seed
    random.seed(seed); np.random.seed(seed)
    print(f"Parameters loaded. Using SEED: {seed}")
    
    placed_rects = []
    last_id, last_pin_id = -1, 0
    
    print("\n--- Phase 1: Generating Pre-constrained Groups ---")
    if params.get('analog_symmetry_settings', {}).get('enable', False):
        sym_gen = SymmetricGenerator(params)
        _, last_id, last_pin_id = sym_gen.generate_analog_groups(0, last_pin_id, placed_rects)
        
    if params.get('alignment_settings', {}).get('enable', False):
        align_gen = AlignmentGenerator(params)
        _, _, last_id = align_gen.generate_aligned_sets(last_id + 1, placed_rects)
    save_frame(placed_rects, params, "Phase 1: Pre-constrained Groups Placed", is_final=True)

    print("\n--- Phase 2: Placing Initial Random Components ---")
    component_definitions = params.get('component_types', {})
    types_to_generate = []
    total_random_rects = params['NUM_RECTANGLES']
    for type_name, definition in component_definitions.items():
        count = int(total_random_rects * definition.get('proportion', 0))
        types_to_generate.extend([type_name] * count)
    while len(types_to_generate) < total_random_rects:
        types_to_generate.append('std_cell')
    random.shuffle(types_to_generate)

    for component_type in types_to_generate:
        type_def = component_definitions.get(component_type)
        if not type_def: continue
        for _ in range(500):
            w, h = random.uniform(*type_def['width_range']), random.uniform(*type_def['height_range'])
            prob = random.uniform(*type_def['growth_prob_range'])
            rand_x, rand_y = random.uniform(w/2, params['CANVAS_WIDTH'] - w/2), random.uniform(h/2, params['CANVAS_HEIGHT'] - h/2)
            temp_rect = Rectangle(None, rand_x, rand_y, w, h)
            if not any(temp_rect.intersects(r) for r in placed_rects):
                last_id += 1
                placed_rects.append(Rectangle(last_id, rand_x, rand_y, w, h, prob, component_type))
                break
    save_frame(placed_rects, params, "Phase 2: Initial Random Components Placed", is_final=True)
    
    print("\n--- Phase 3: Growth and Optimization ---")
    params['initial_rects'] = placed_rects
    demo_generator = DemoLayoutGenerator(params)
    final_layout = demo_generator.generate()

    print("\n--- Phase 4: Applying Post-Placement Grouping ---")
    if params.get('grouping_settings', {}).get('enable', False):
        grouper = LayoutGrouper(final_layout, params)
        final_layout = grouper.create_hierarchical_groups()
    save_frame(final_layout.rectangles, params, "Phase 4: Hierarchical Groups Formed", is_final=True)
    
    print("\n--- Phase 5: Generating Pins and Edges ---")
    final_layout.generate_pins(
        k=params['PIN_DENSITY_K'], p=params['RENT_EXPONENT_P'], 
        start_pin_id=last_pin_id, pin_edge_margin_ratio=params.get('PIN_EDGE_MARGIN_RATIO', 0.1)
    )
    final_layout.generate_edges(
        p_max=params['EDGE_P_MAX'], decay_rate=params['EDGE_DECAY_RATE'],
        max_length_limit=params['MAX_WIRELENGTH_LIMIT'], k_neighbors=params['EDGE_K_NEAREST_NEIGHBORS']
    )
    
    # 創建一個包含 Pins 和 Edges 的最終畫面
    final_layout_with_nets = final_layout
    save_frame(final_layout_with_nets.rectangles, params, "Final Layout with Pins & Edges", is_final=True)

    print("\n--- Phase 6: Compiling GIF ---")
    gif_path = "layout_generation_demo.gif"
    with imageio.get_writer(gif_path, mode='I', duration=0.2, loop=0) as writer:
        for filename in frame_files:
            image = imageio.v2.imread(filename)
            writer.append_data(image)
    print(f"Success! GIF saved to: {gif_path}")

    print("\n--- Phase 7: Cleaning up temporary files ---")
    shutil.rmtree(FRAME_DIR)
    print("Done.")

if __name__ == "__main__":
    main()