# main.py (引腳 ID 傳遞修正版)

import random
import numpy as np
import yaml
import os
import json
import time

from generator import LayoutGenerator
from layout import Layout, Rectangle
from symmetry import SymmetricGenerator

def load_config(path='config.yaml'):
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def get_randomized_params(config):
    params = config['base_params'].copy()
    if 'analog_symmetry_settings' in config:
        params['analog_symmetry_settings'] = config['analog_symmetry_settings'].copy()
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

def save_layout_to_json(layout, params, filepath):
    layout_data = {
        "canvas_width": layout.canvas_width, "canvas_height": layout.canvas_height,
        "rectangles": [ { "id": r.id, "x": r.x, "y": r.y, "w": r.w, "h": r.h, "growth_prob": r.growth_prob, "fixed": r.fixed } for r in layout.rectangles ],
        "pins": [ { "id": pin.id, "parent_rect_id": pin.parent_rect.id, "rel_pos": pin.rel_pos } for r in layout.rectangles for pin in r.pins ],
        "edges": [ (pin1.id, pin2.id) for pin1, pin2 in layout.edges ]
    }
    full_data = { "generation_params": params, "layout_data": layout_data }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

def main():
    config = load_config('config.yaml')
    run_settings = config['run_settings']
    num_samples = run_settings['num_samples_to_generate']
    output_dir = run_settings['output_directory']

    os.makedirs(output_dir, exist_ok=True)
    print(f"將在 '{output_dir}' 資料夾中生成 {num_samples} 個樣本...")

    for i in range(num_samples):
        start_time = time.time()
        sample_id = i + 1
        print(f"\n--- [樣本 {sample_id}/{num_samples}] 開始生成 ---")

        params = get_randomized_params(config)
        seed = random.randint(0, 2**32 - 1); params['SEED'] = seed
        random.seed(seed); np.random.seed(seed)
        
        placed_rects = []
        last_id = -1
        last_pin_id = 0 # <<< NEW: 初始化 Pin ID 計數器
        
        if params.get('analog_symmetry_settings', {}).get('enable', False):
            sym_gen = SymmetricGenerator(params)
            # <<< MODIFICATION: 傳遞並接收 pin_id
            new_symmetric_rects, last_id, last_pin_id = sym_gen.generate_analog_groups(
                start_id=0, 
                start_pin_id=0,
                existing_rects=placed_rects
            )
        
        print(f"\n--- 開始生成其餘 {params['NUM_RECTANGLES']} 個隨機填充元件 ---")
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
                 print(f"--- 警告：無法為第 {j+1} 個隨機元件找到空間，已略過。 ---")

        params['initial_rects'] = placed_rects
        
        generator = LayoutGenerator(params)
        final_layout = generator.generate()

        if final_layout:
            # <<< MODIFICATION: 將最新的 pin_id 傳入，以繼續編號
            final_layout.generate_pins(
                k=params['PIN_DENSITY_K'], 
                p=params['RENT_EXPONENT_P'], 
                start_pin_id=last_pin_id
            )
            final_layout.generate_edges(
                p_max=params['EDGE_P_MAX'], 
                decay_rate=params['EDGE_DECAY_RATE'],
                max_length_limit=params['MAX_WIRELENGTH_LIMIT']
            )
            output_filepath = os.path.join(output_dir, f"layout_{sample_id}.json")
            if 'initial_rects' in params: del params['initial_rects']
            save_layout_to_json(final_layout, params, output_filepath)
            
            end_time = time.time()
            print(f"--- [樣本 {sample_id}] 生成完畢並已儲存至 {output_filepath} (耗時: {end_time - start_time:.2f} 秒) ---")
        else:
            print(f"--- [樣本 {sample_id}] 生成失敗，已跳過 ---")

    print(f"\n全部 {num_samples} 個樣本已生成完畢！")

if __name__ == "__main__":
    main()