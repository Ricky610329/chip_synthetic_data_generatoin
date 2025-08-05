# grouper.py

import random
import math
from collections import defaultdict

class LayoutGrouper:
    def __init__(self, layout, params):
        self.layout = layout
        self.params = params
        self.config = params['grouping_settings']

    def _get_placeable_items(self):
        items = []
        grouped_items = defaultdict(list)
        single_rects = []
        
        for r in self.layout.rectangles:
            if 'grouping_id' in r.constraints:
                continue

            if 'symmetry_id' in r.constraints:
                grouped_items[('sym', r.constraints['symmetry_id'])].append(r)
            elif 'alignment_id' in r.constraints:
                grouped_items[('align', r.constraints['alignment_id'])].append(r)
            else:
                single_rects.append(r)
        
        for (g_type, g_id), rects_in_group in grouped_items.items():
            min_x = min(r.x - r.w/2 for r in rects_in_group)
            max_x = max(r.x + r.w/2 for r in rects_in_group)
            min_y = min(r.y - r.h/2 for r in rects_in_group)
            max_y = max(r.y + r.h/2 for r in rects_in_group)
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2
            items.append({
                "id": g_id, "center": (center_x, center_y),
                "rect_ids": [r.id for r in rects_in_group]
            })

        for r in single_rects:
            items.append({
                "id": r.id, "center": (r.x, r.y),
                "rect_ids": [r.id]
            })
        return items

    def create_hierarchical_groups(self):
        if self.config['method'] != 'proximity':
            return self.layout

        items = self._get_placeable_items()
        num_groups_config = self.config['num_groups_to_create']
        num_groups_to_create = random.randint(num_groups_config['low'], num_groups_config['high'])
        max_radius = self.config.get('max_search_radius', float('inf'))

        grouped_item_indices = set()
        hierarchical_group_constraints = []
        print(f"\nAttempting to create {num_groups_to_create} hierarchical groups...")

        for i in range(num_groups_to_create):
            available_indices = [idx for idx in range(len(items)) if idx not in grouped_item_indices]
            if len(available_indices) < 2: break

            seed_idx = random.choice(available_indices)
            seed_item = items[seed_idx]
            
            items_per_group_config = self.config['items_per_group']
            items_per_group = random.randint(items_per_group_config['low'], items_per_group_config['high'])
            num_neighbors_to_find = items_per_group - 1
            if num_neighbors_to_find <= 0: continue

            distances = []
            for j in available_indices:
                if j == seed_idx: continue
                dist = math.hypot(seed_item['center'][0] - items[j]['center'][0], 
                                  seed_item['center'][1] - items[j]['center'][1])
                if dist <= max_radius:
                    distances.append((dist, j))
            
            distances.sort(key=lambda x: x[0])
            neighbors_indices = [idx for _, idx in distances[:num_neighbors_to_find]]
            
            new_group_members_indices = [seed_idx] + neighbors_indices
            if len(new_group_members_indices) < 2:
                continue

            new_group_id = f"h_group_{i}"
            all_rect_ids_in_new_group = set()
            
            rect_ids_for_this_group = []
            for member_idx in new_group_members_indices:
                rect_ids_for_this_group.extend(items[member_idx]['rect_ids'])
            
            all_rect_ids_in_new_group.update(rect_ids_for_this_group)
            
            hierarchical_group_constraints.append(list(all_rect_ids_in_new_group))
            
            for r in self.layout.rectangles:
                if r.id in all_rect_ids_in_new_group:
                    r.constraints['grouping_id'] = new_group_id
            
            grouped_item_indices.update(new_group_members_indices)
        
        self.layout.hierarchical_group_constraints = hierarchical_group_constraints
        print("--- Hierarchical grouping complete. ---")
        return self.layout