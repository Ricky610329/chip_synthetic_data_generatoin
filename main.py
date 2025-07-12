# main.py

import random
import numpy as np
import yaml
import os
import json
import time
from generator import LayoutGenerator
from layout import Layout, Rectangle
from symmetry import SymmetricGenerator
from alignment import AlignmentGenerator
from grouper import LayoutGrouper

def load_config(path='config.yaml'):
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def get_randomized_params(config):
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

def save_layout_to_json(layout, params, filepath):
    layout_data = {
        "canvas_width": layout.canvas_width, "canvas_height": layout.canvas_height,
        "rectangles": [ {
            "id": r.id, "x": r.x, "y": r.y, "w": r.w, "h": r.h,
            "growth_prob": r.growth_prob, "fixed": r.fixed,
            "constraints": r.constraints, "component_type": r.component_type
        } for r in layout.rectangles ],
        "pins": [ { "id": pin.id, "parent_rect_id": pin.parent_rect.id, "rel_pos": pin.rel_pos } for r in layout.rectangles for pin in r.pins ],
        "netlist_edges": layout.edges,
        "alignment_constraints": layout.alignment_constraints,
        "hierarchical_group_constraints": layout.hierarchical_group_constraints,
    }
    if 'initial_rects' in params:
        del params['initial_rects']
    full_data = { "generation_params": params, "layout_data": layout_data }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

def main():
    config = load_config('config.yaml')
    run_settings = config['run_settings']
    num_samples = run_settings['num_samples_to_generate']
    output_dir = "raw_layouts_with_constraints"
    os.makedirs(output_dir, exist_ok=True)

    for i in range(num_samples):
        start_time, sample_id = time.time(), i + 1
        print(f"\n--- [樣本 {sample_id}/{num_samples}] 開始生成 ---")

        params = get_randomized_params(config)
        seed = random.randint(0, 2**32 - 1); params['SEED'] = seed
        random.seed(seed); np.random.seed(seed)
        
        placed_rects, alignment_constraints = [], []
        last_id, last_pin_id = -1, 0
        
        if params.get('analog_symmetry_settings', {}).get('enable', False):
            sym_gen = SymmetricGenerator(params)
            _, last_id, last_pin_id = sym_gen.generate_analog_groups(
                start_id=0, start_pin_id=0, existing_rects=placed_rects)
        
        if params.get('alignment_settings', {}).get('enable', False):
            align_gen = AlignmentGenerator(params)
            _, new_constraints, last_id = align_gen.generate_aligned_sets(
                start_id=last_id + 1, existing_rects=placed_rects)
            alignment_constraints.extend(new_constraints)

        print(f"\n--- 開始生成 {params['NUM_RECTANGLES']} 個隨機 Macro 和 Standard Cell ---")
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
                    placed_rects.append(Rectangle(rect_id=last_id, x=rand_x, y=rand_y, w=w, h=h, growth_prob=prob, component_type=component_type))
                    break
        
        params['initial_rects'] = placed_rects
        
        generator = LayoutGenerator(params)
        final_layout = generator.generate()
        
        if final_layout:
            final_layout.alignment_constraints = alignment_constraints
            if params.get('grouping_settings', {}).get('enable', False):
                grouper = LayoutGrouper(final_layout, params)
                final_layout = grouper.create_hierarchical_groups()

            final_layout.generate_pins(
                k=params['PIN_DENSITY_K'], 
                p=params['RENT_EXPONENT_P'], 
                start_pin_id=last_pin_id,
                pin_edge_margin_ratio=params.get('PIN_EDGE_MARGIN_RATIO', 0.1)
            )
            final_layout.generate_edges(
                p_max=params['EDGE_P_MAX'], 
                decay_rate=params['EDGE_DECAY_RATE'],
                max_length_limit=params['MAX_WIRELENGTH_LIMIT'],
                k_neighbors=params['EDGE_K_NEAREST_NEIGHBORS']
            )
            output_filepath = os.path.join(output_dir, f"layout_{sample_id}.json")
            save_layout_to_json(final_layout, params, output_filepath)
            print(f"--- [樣本 {sample_id}] 生成完畢 (耗時: {time.time() - start_time:.2f} 秒) ---")

if __name__ == "__main__":
    main()