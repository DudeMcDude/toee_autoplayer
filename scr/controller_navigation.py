from controller_constants import *

exterior_maps = {
	AREA_ID_MOATHOUSE: MOATHOUSE_EXTERIOR_MAP,
	AREA_ID_HOMMLET: HOMMLET_EXTERIOR_MAP,
	AREA_ID_NULB: NULB_EXTERIOR_MAP,
	AREA_ID_TEMPLE: TEMPLE_COURTYARD_MAP,
}
map_connectivity_moathouse = {
	MOATHOUSE_EXTERIOR_MAP: { # 5002
		MOATHOUSE_TOWER_MAP: (485, 480),
		MOATHOUSE_RUINS_MAP: (468, 452),
	},
	MOATHOUSE_TOWER_MAP: { # 5003
		MOATHOUSE_EXTERIOR_MAP: (467, 488),
	},
	MOATHOUSE_RUINS_MAP: { # 5004
		MOATHOUSE_EXTERIOR_MAP: (481, 482),
		MOATHOUSE_DUNGEON_MAP: (484, 474)
	},
	MOATHOUSE_DUNGEON_MAP: { # 5005
		MOATHOUSE_RUINS_MAP: (429, 410),
		MOATHOUSE_CAVE_EXIT_MAP: (532, 560),
	},
	MOATHOUSE_CAVE_EXIT_MAP: { # 5091
		MOATHOUSE_DUNGEON_MAP: (492, 476),
	},
}

map_connectivity_temple = {
TEMPLE_COURTYARD_MAP: { # 5062
		TEMPLE_INTERIOR: (518, 458),
		TEMPLE_TOWER_EXTERIOR_MAP: (400, 470) 
	},
	
	TEMPLE_INTERIOR: { # 5064
		TEMPLE_COURTYARD_MAP: (493, 571),
		TEMPLE_DUNGEON_LEVEL_1: [ (555, 515) , (423, 516)],
		TEMPLE_SECRET_STAIRCASE: (482, 487),
	},

	TEMPLE_SECRET_STAIRCASE: { # 5106
		TEMPLE_INTERIOR: (468, 477),
		TEMPLE_DUNGEON_LEVEL_1: (479, 475),
		TEMPLE_DUNGEON_LEVEL_2: (480,466),
	},

	TEMPLE_DUNGEON_LEVEL_1: { # 5066
		TEMPLE_INTERIOR: [(544, 589), (418, 588)],
		TEMPLE_DUNGEON_LEVEL_2: (558, 392),
		TEMPLE_SECRET_STAIRCASE: (487, 517),
	},

	TEMPLE_DUNGEON_LEVEL_2: { # 5067
		TEMPLE_DUNGEON_LEVEL_1: (564, 375),
	},

	TEMPLE_TOWER_INTERIOR_MAP: { # 5065
		TEMPLE_TOWER_EXTERIOR_MAP: (485, 497) ,
	},

	TEMPLE_TOWER_EXTERIOR_MAP: { # 5111
		TEMPLE_TOWER_INTERIOR_MAP: (480, 500),
		TEMPLE_COURTYARD_MAP: (495, 552), 
	},
}

map_connectivity = { # TODO: automate this
	HOMMLET_EXTERIOR_MAP: { #5001
		HOMMLET_INN_MAIN_MAP: (619, 404)
	},

	HOMMLET_INN_MAIN_MAP: { # 5007
		HOMMLET_EXTERIOR_MAP: (486, 489)
	},
	
}
map_connectivity.update(map_connectivity_moathouse)
map_connectivity.update(map_connectivity_temple)

random_encounter_maps = [x for x in range(5070, 5079) ]
worldmap_access_maps = random_encounter_maps + [ HOMMLET_EXTERIOR_MAP, 
    MOATHOUSE_EXTERIOR_MAP, 
    MOATHOUSE_CAVE_EXIT_MAP,
    NULB_EXTERIOR_MAP, 
    TEMPLE_COURTYARD_MAP,
    RAMSHACKLE_FARM_MAP,

    IMERYDS_RUN_MAP,
    DEKLO_GROVE_MAP,
    EMRIDY_MEADOWS_MAP,
    OGRE_CAVE_MAP,

    WELKWOOD_BOG_MAP,
    HICKORY_BRANCH_MAP,
    VERBOBONC_MAP,
    VERBOBONC_CAVE_EXIT_MAP,
    QUARRY_MAP,
     ]

random_wander_amount = {
	MOATHOUSE_TOWER_MAP: 3,
	TEMPLE_SECRET_STAIRCASE: 3, 
	TEMPLE_TOWER_EXTERIOR_MAP: 20,
	TEMPLE_COURTYARD_MAP: 25,
	TEMPLE_INTERIOR: 35,
}

class CourseSearchNode:
	id = -1
	prev = -1
	cost = 0
	def __init__(self, id, prev, cost):
		self.id = id
		self.prev = prev
		self.cost = cost
		return
	def __repr__(self):
		return "id = %d, prev = %d, cost = %d" % (self.id, self.prev, self.cost)

def pop_search_node(open_set):
	#type: (list[CourseSearchNode])->CourseSearchNode
	result = None
	
	min_cost = 100000
	result_idx = -1
	for i in range(len(open_set)):
		cost = open_set[i].cost
		if cost < 0:
			continue
		if cost < min_cost:
			min_cost = open_set[i].cost
			result_idx = i

	if result_idx >= 0:
		result = open_set.pop(result_idx)
	return result

def get_map_course(cur_map, tgt_map):
	best_course = [cur_map,]
	test_course = [cur_map,]
	open_set = [] #type: list[CourseSearchNode]
	
	
	best_node = CourseSearchNode(cur_map, -1, 0)
		
	while best_node.id != tgt_map:
		# print('get_map_course: current: ' + str(best_node) )

		cur_node_id = best_node.id
		neighbours = map_connectivity[cur_node_id]

		for map_id, loc in neighbours.items():
			# print('neighbour: ' + str(map_id))
			n_node = CourseSearchNode(map_id, cur_node_id, best_node.cost + 1)
			
			# search for neighbour in open set
			found_in_open = False
			for i,s in enumerate(open_set):
				if s.id == n_node.id:
					found_in_open = True
					if s.prev == n_node.prev and s.cost > n_node.cost:
						s = n_node
			if not found_in_open:
				open_set.append(n_node)
		
		best_node.cost = -1
		open_set.append(best_node)
		
		best_node  = pop_search_node(open_set)
		if best_node is None:
			return None
	
	tmp_node = best_node
	best_course = [tgt_map, ]
	while tmp_node.prev != -1:
		# search for prev node
		for i in range(len(open_set)):
			node = open_set[i]
			if node.id == tmp_node.prev:
				best_course.insert(0, node.id)
				tmp_node = open_set[i]
				break
	return best_course
