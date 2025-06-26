# main.py (YAML-Powered & Randomized)

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random
import numpy as np
import yaml       # <<< NEW: 引入 yaml
import os         # <<< NEW: 引入 os 用於檔案路徑操作
import json       # <<< NEW: 引入 json 用於儲存
import time

from generator import LayoutGenerator
from layout import Layout

def load_config(path='config.yaml'):
    """從 YAML 檔案載入設定"""
    with open(path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    return config

def get_randomized_params(config):
    """根據設定檔規則生成一組隨機化參數"""
    params = config['base_params'].copy() # 從基礎參數開始

    for key, rule in config['randomize_params'].items():
        if rule['type'] == 'randint':
            params[key] = random.randint(rule['low'], rule['high'])
        elif rule['type'] == 'uniform':
            params[key] = random.uniform(rule['low'], rule['high'])
        elif rule['type'] == 'uniform_pair':
            val1 = random.uniform(rule['low'][0], rule['high'][0])
            val2 = random.uniform(rule['low'][1], rule['high'][1])
            params[key] = (min(val1, val2), max(val1, val2))
        # 可以依需求增加更多規則，例如 'choice'
        
    return params

def save_layout_to_json(layout, params, filepath):
    """將 Layout 物件和生成參數序列化為 JSON 檔案"""
    
    # 將 layout 物件轉換為字典
    layout_data = {
        "canvas_width": layout.canvas_width,
        "canvas_height": layout.canvas_height,
        "rectangles": [
            {
                "id": r.id, "x": r.x, "y": r.y, "w": r.w, "h": r.h,
                "growth_prob": r.growth_prob
            } for r in layout.rectangles
        ],
        "pins": [
            {
                "id": pin.id, "parent_rect_id": pin.parent_rect.id,
                "rel_pos": pin.rel_pos
            } for r in layout.rectangles for pin in r.pins
        ],
        "edges": [
            # 儲存相連的 pin id
            (pin1.id, pin2.id) for pin1, pin2 in layout.edges
        ]
    }
    
    # 組合最終要儲存的資料
    full_data = {
        "generation_params": params,
        "layout_data": layout_data
    }
    
    # 寫入檔案
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(full_data, f, ensure_ascii=False, indent=2)

def main():
    """主執行函式"""
    # 1. 載入設定
    config = load_config('config.yaml')
    run_settings = config['run_settings']
    num_samples = run_settings['num_samples_to_generate']
    output_dir = run_settings['output_directory']

    # 2. 建立輸出資料夾
    os.makedirs(output_dir, exist_ok=True)
    print(f"將在 '{output_dir}' 資料夾中生成 {num_samples} 個樣本...")

    # 3. 進入生成迴圈
    for i in range(num_samples):
        start_time = time.time()
        sample_id = i + 1
        print(f"\n--- [樣本 {sample_id}/{num_samples}] 開始生成 ---")

        # 3.1 取得本次的隨機參數
        params = get_randomized_params(config)
        
        # 3.2 設定並儲存隨機種子，以供重現
        seed = random.randint(0, 2**32 - 1)
        params['SEED'] = seed
        random.seed(seed)
        np.random.seed(seed)
        
        print(f"使用種子: {seed}, 元件數: {params['NUM_RECTANGLES']}, 目標密度: {params['TARGET_DENSITY']:.2f}")

        # 3.3 執行生成
        generator = LayoutGenerator(params)
        final_layout = generator.generate()

        if final_layout:
            final_layout.generate_pins(k=params['PIN_DENSITY_K'], p=params['RENT_EXPONENT_P'])
            final_layout.generate_edges(
                p_max=params['EDGE_P_MAX'], 
                decay_rate=params['EDGE_DECAY_RATE'],
                max_length_limit=params['MAX_WIRELENGTH_LIMIT']
            )

            # 3.4 儲存結果到 JSON
            output_filepath = os.path.join(output_dir, f"layout_{sample_id}.json")
            save_layout_to_json(final_layout, params, output_filepath)
            
            end_time = time.time()
            print(f"--- [樣本 {sample_id}] 生成完畢並已儲存至 {output_filepath} (耗時: {end_time - start_time:.2f} 秒) ---")
        else:
            print(f"--- [樣本 {sample_id}] 生成失敗，已跳過 ---")

    print(f"\n全部 {num_samples} 個樣本已生成完畢！")


if __name__ == "__main__":
    main()