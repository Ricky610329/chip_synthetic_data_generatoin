# grouper.py (增加了最大搜尋半徑限制)

import random
import math
from collections import defaultdict

class LayoutGrouper:
    def __init__(self, layout, params):
        self.layout = layout
        self.params = params
        self.config = params['grouping_settings']

    def _get_placeable_items(self):
        # ... (此內部函式不變) ...
        items = []
        existing_groups = defaultdict(list)
        single_rects = []
        for r in self.layout.rectangles:
            if r.group_id:
                existing_groups[r.group_id].append(r)
            else:
                single_rects.append(r)
        for group_id, rects_in_group in existing_groups.items():
            min_x = min(r.x - r.w/2 for r in rects_in_group)
            max_x = max(r.x + r.w/2 for r in rects_in_group)
            min_y = min(r.y - r.h/2 for r in rects_in_group)
            max_y = max(r.y + r.h/2 for r in rects_in_group)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            items.append({
                "id": group_id,
                "center": (center_x, center_y),
                "rect_ids": [r.id for r in rects_in_group],
                "is_group": True
            })
        for r in single_rects:
            items.append({
                "id": r.id,
                "center": (r.x, r.y),
                "rect_ids": [r.id],
                "is_group": False
            })
        return items


    def create_hierarchical_groups(self):
        if self.config['method'] != 'proximity':
            print("Warning: Only 'proximity' grouping method is supported.")
            return self.layout

        items = self._get_placeable_items()
        num_groups_config = self.config['num_groups_to_create']
        num_groups_to_create = random.randint(num_groups_config['low'], num_groups_config['high'])
        
        # ✨ 1. 從設定檔讀取最大搜尋半徑
        max_radius = self.config.get('max_search_radius', float('inf'))

        grouped_item_indices = set()
        print(f"\nAttempting to create {num_groups_to_create} hierarchical groups (max radius: {max_radius})...")

        for i in range(num_groups_to_create):
            available_indices = [idx for idx in range(len(items)) if idx not in grouped_item_indices]
            if not available_indices:
                break

            seed_idx = random.choice(available_indices)
            seed_item = items[seed_idx]
            
            items_per_group_config = self.config['items_per_group']
            items_per_group = random.randint(items_per_group_config['low'], items_per_group_config['high'])
            num_neighbors_to_find = items_per_group - 1
            if num_neighbors_to_find <= 0: continue

            # 尋找鄰居
            distances = []
            for j in available_indices:
                if j == seed_idx: continue
                other_item = items[j]
                dist = math.hypot(seed_item['center'][0] - other_item['center'][0], 
                                  seed_item['center'][1] - other_item['center'][1])
                
                # ✨ 2. 只有在距離小於最大半徑時，才將其視為候選鄰居
                if dist <= max_radius:
                    distances.append((dist, j))
            
            distances.sort(key=lambda x: x[0])
            neighbors_indices = [idx for _, idx in distances[:num_neighbors_to_find]]
            
            new_group_members_indices = [seed_idx] + neighbors_indices
            if len(new_group_members_indices) < 2:
                # 如果找不到足夠的近鄰，就放棄建立這個群組
                print(f"  - Could not find enough neighbors for item {seed_item['id']} within radius. Skipping group formation.")
                continue

            # ... (建立新群組並更新屬性的邏輯不變) ...
            new_group_id = f"h_group_{i}"
            member_ids_for_print = [items[idx]['id'] for idx in new_group_members_indices]
            print(f"  - Creating group '{new_group_id}' with items: {member_ids_for_print}")
            all_rect_ids_in_new_group = set()
            for member_idx in new_group_members_indices:
                all_rect_ids_in_new_group.update(items[member_idx]['rect_ids'])
            for r in self.layout.rectangles:
                if r.id in all_rect_ids_in_new_group:
                    r.group_id = new_group_id
                    r.group_type = 'hierarchical'
            grouped_item_indices.update(new_group_members_indices)

        print("--- Hierarchical grouping complete. ---")
        return self.layout