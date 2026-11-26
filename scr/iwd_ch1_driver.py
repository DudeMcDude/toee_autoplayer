'''
IWD chapter-1 critical-path driver (ie2toee IWD convert, module IWD).  AUTOPLAYER_SCENARIO=iwd_ch1.

A real new game: the harness loads a save (TP_AUTOLOAD), the driver quits to the main menu (in-game menu -> Quit)
and starts a new game with the party pool's pregenerated characters (controller_scheme_builders' new-game stages).
Then the prologue to chapter 1, as test_ch1_path.py walks it offline:
  intro -> Hrothgar greets the party in Winter's Cradle (AR1006, his EHHROTHT script)
  -> meet Hrothgar at home (AR1004) for Caravan_Quest 1 (Join_Posse 3) -> AR1200: enter CARATRG1 (Caravan_Quest 2)
  -> Hrothgar gives the List (Supply_Quest 1) -> Pomab (AR1007) takes it (Supply_Quest 2) -> Hrothgar
  "Let us be off" -> cutscene EHHROTHM -> AR2000 Kuldahar Pass = SUMMARY CH1 PASS.
Dialogue: data driven, the shortest reply path (dlg graph) to a reply whose converted action matches the step's
regex. The party walks to area exits, quest triggers and speakers. Each conversation uses the NPC's dialogue script.
'''
from toee import *
from toee import game
from controllers import ControlScheme, GoalState, GoalStateStart
from controller_callbacks_common import get_current_map, dlg_reply, find_attack_lines, gs_press_widget, gs_is_main_menu, gs_create_and_push_scheme
from controller_ui_util import WID_IDEN
from utilities import location_from_axis, location_to_axis
import gamedialog as dlg
import iwd_easthaven_controller as E
import chapter_camera
import chapter_sidequests as side
import os, re, glob, time

log = E.log
INGAME_QUIT = [('', 'templeplus/ui/main_menu.json'), ('pages', 'templeplus/ui/main_menu.json'),
               ('page-ingame-normal', 'templeplus/ui/main_menu.json'), ('ingame-normal-quit', 'templeplus/ui/main_menu.json')]

def shot(name):
	if E.LOG:
		f = open(E.LOG, 'a'); f.write('SHOT %s\n' % name); f.close()

def key(k):
	if E.LOG:
		f = open(E.LOG, 'a'); f.write('KEY %s\n' % k); f.close()

#region converted-module data
def npc_script(ident, area):
	'''(script id, module source) of the converted dialogue script py<sid>ie_<ident>*.py whose AREA is area'''
	# Hrothgar's converted script uses his death variable "hroth" in newer installs.
	prefix = 'hroth' if ident == 'hrothgar' else ident
	shared = None
	for p in sorted(glob.glob(os.path.join(E.find_core(), 'scr', 'py*ie_%s*.py' % prefix))):
		src = open(p).read()
		m = re.search(r'''^AREA\s*=\s*["']([^"']*)["']''', src, re.M)
		if m and m.group(1).upper() == area.upper():
			return int(os.path.basename(p)[2:7]), src
		if m and not m.group(1) and os.path.basename(p)[10:-3].lower() == ident.lower():
			shared = int(os.path.basename(p)[2:7]), src
	return shared or (None, '')

def dlg_graph(sid, src, goal):
	'''npc lines {line: [reply lines]}, reply -> next npc line, goal replies (their action source matches goal)'''
	f = glob.glob(os.path.join(E.find_core(), 'dlg', '%05d*.dlg' % sid))[0]
	fns = dict((m.group(1), m.group(2)) for m in re.finditer(r'^def (ie_a\d+)\(.*?\):\n((?:[ \t]+.*\n|\n)*)', src, re.M))
	npc, to, goals, cur = {}, {}, set(), None
	for m in re.finditer(r'\{(\d+)\}\{[^}]*\}\{[^}]*\}\{([^}]*)\}\{[^}]*\}\{([^}]*)\}\{([^}]*)\}', open(f).read()):
		ln, iq, nxt, eff = int(m.group(1)), m.group(2), m.group(3), m.group(4)
		if iq.strip():
			to[ln] = int(nxt) if nxt.strip().lstrip('-').isdigit() else 0
			if cur is not None:
				npc[cur].append(ln)
			fn = re.match(r'\s*(ie_a\d+)', eff)
			if fn and re.search(goal, fns.get(fn.group(1), '')):
				goals.add(ln)
		else:
			cur = ln; npc[ln] = []
	return npc, to, goals
#endregion

TALK = {'cur': None}
_dialogue_lengths = {}


def dialogue_delay(sid, line):
	"""Give every displayed NPC line a reading pause, capped for long speeches."""
	if sid not in _dialogue_lengths:
		paths = glob.glob(os.path.join(E.find_core(), 'dlg', '%05d*.dlg' % sid))
		lengths = {}
		if paths:
			with open(paths[0]) as source:
				for match in re.finditer(r'^\{(\d+)\}\{([^}]*)\}', source.read(), re.M):
					lengths[int(match.group(1))] = len(match.group(2))
		_dialogue_lengths[sid] = lengths
	return min(7.5, max(3.0, _dialogue_lengths[sid].get(line, 0) / 45.0))

def ch1_dialog_handler(slot):
	'''Pause on each line, then reply on the shortest path to the step's goal.'''
	ds = dlg.get_current_state()
	N = ds.reply_count
	c = TALK['cur']
	st = ST
	if not st.get('shot_dlg_%d' % ds.script_id):
		st['shot_dlg_%d' % ds.script_id] = 1
		import ie_cutscene
		if not ie_cutscene.active():
			chapter_camera.frame(find_obj(ds.script_id), game.leader)
		shot('dlg_%d' % ds.script_id)
	line = (ds.script_id, ds.line_number, N)
	now = time.time()
	if TALK.get('line') != line:
		TALK['line'] = line
		TALK['ready_at'] = now + dialogue_delay(ds.script_id, ds.line_number)
	if now < TALK['ready_at']:
		return max(150, int(1000 * (TALK['ready_at'] - now)))
	TALK.pop('line', None)
	if N == 0:
		dlg_reply(0); return 150
	pick = None
	if c and ds.script_id == c['sid']:
		c['replies'] += 1
		v = c['visits'][ds.line_number] = c['visits'].get(ds.line_number, 0) + 1
		attack = find_attack_lines(ds); best = 1e9
		for i in range(N):
			if i in attack:
				continue
			if c['hit']:
				nxt = ds.get_npc_reply_id(i)
				d = (0 if nxt <= 0 else 1 + c['exit_dist'].get(nxt, 1000)) + (0.1 if ds.get_reply_effect(i) else 0)
				if d < best:
					pick, best = i, d
				continue
			m = re.search(r'ie_a(\d+)', ds.get_reply_effect(i) or '')     # (the action function is named by its reply line)
			if m and int(m.group(1)) in c['goals']:
				pick = i; c['hit'] = 1; break
			nxt = ds.get_npc_reply_id(i)
			d = c['dist'].get(nxt, 1e8) + 3 * c['choices'].get((ds.line_number, nxt), 0)
			if d < best:
				pick, best = i, d
		if v >= 3 or c['replies'] > 60:
			pick = N - 1
		if pick is not None and not c['hit']:
			edge = (ds.line_number, ds.get_npc_reply_id(pick))
			c['choices'][edge] = c['choices'].get(edge, 0) + 1
	if pick is None:
		# Incidental conversations can return to a menu of questions. Keep
		# the first visit natural, then try a different reply on each return.
		visits = TALK.setdefault('incidental_visits', {})
		count = visits.get(line, 0)
		attacks = find_attack_lines(ds)
		options = [i for i in range(N) if i not in attacks] or list(range(N))
		pick = options[count % len(options)]
		visits[line] = count + 1
	log('REPLY sid %d line %d: %d replies -> pick %d (npc line %d)' % (ds.script_id, ds.line_number, N, pick, ds.get_npc_reply_id(pick)))
	dlg_reply(pick)
	return 150

#region steps
def V(name):
	import ie_runtime as rt
	return rt.get_var(None, name, 'GLOBAL')

def area_map(area):
	import ie_travel_data as D
	return D.AREAS[area]['map']

def area_of(m):
	import ie_travel_data as D
	for a, d in D.AREAS.items():
		if d['map'] == m:
			return a
	return None

def find_obj(sid):
	for o in game.obj_list_range(game.leader.location, 300, OLC_NPC):
		if o.scripts[san_dialog] == sid and o not in game.party:
			return o
	return OBJ_HANDLE_NULL

class Step(object):
	def __init__(self, kind, **kw):
		self.kind, self.n = kind, 0
		self.__dict__.update(kw)

def prepare_dialogue(st):
	# Keep the tried branches if the same quest requires reopening a conversation.
	# A short route in the converted graph may depend on a reply the PC cannot see.
	if not hasattr(st, 'choices'):
		st.choices = {}
	TALK['cur'] = {'sid': st.sid, 'goals': st.goals, 'dist': st.dist, 'exit_dist': st.exit_dist,
	               'visits': {}, 'choices': st.choices, 'replies': 0, 'hit': 0}
	TALK.pop('line', None)


def talk_step(st, ident, area, goal, until, speaker=None):
	"""Choose dialogue replies leading to the goal and verify the resulting quest state."""
	if until():
		return 1
	if not hasattr(st, 'sid'):
		st.arrived = st.n
		st.sid, src = npc_script(ident, area[-6:])     # (IWD2 travel keys carry an I2 prefix)
		if st.sid is None:
			return fail('no converted %s in %s' % (ident, area))
		npc, to, goals = dlg_graph(st.sid, src, goal)
		st.goals, st.dist, st.talks = goals, E.dist_to_goal(npc, to, goals), 0
		st.exit_dist = E.dist_to_goal(npc, to, set(r for r in to if to[r] <= 0))
		log('TALK %s sid %d goal %r: %d goal replies' % (ident, st.sid, goal, len(goals)))
		# A character can start talking as soon as the party steps inside.
		prepare_dialogue(st)
	if not st.goals:
		return fail('no matching reply for %s: %s' % (ident, goal))
	if get_current_map() != area_map(area):
		return walk_to_area(st, area)
	if dlg.is_engaged():
		return 0
	if st.talks >= 4:
		return fail('%s: %s not reached after %d conversations' % (ident, goal, st.talks))
	if st.n >= getattr(st, 'next_talk', 0):
		st.next_talk = st.n + 10
		pc = speaker() if speaker else next(p for p in game.party if not p.is_unconscious())
		if pc.is_unconscious():
			pc = next(p for p in game.party if not p.is_unconscious())
		o = find_obj(st.sid)
		if o == OBJ_HANDLE_NULL:
			now = time.time()
			position = location_to_axis(pc.location)
			if getattr(st, 'search_position', None) != position:
				st.search_position, st.search_progress = position, now
			if now - st.search_progress < 20:
				spots = E.spawn_tiles(ident, area)
				if spots:
					walk_party(st, spots[0], 5, pc)
				return 0
			return fail('%s (sid %d) not found after 20 seconds without search progress' % (ident, st.sid))
		x, y = location_to_axis(o.location)
		def talking_range(member):
			mx,my = location_to_axis(member.location)
			return max(abs(mx-x),abs(my-y)) <= 6 and member.has_los(o)
		if not speaker and not talking_range(pc):
			pc = next((p for p in game.party if not p.is_unconscious() and talking_range(p)),pc)
		if not talking_range(pc):
			position = location_to_axis(pc.location)
			now = time.time()
			if getattr(st, 'approach_position', None) != (pc.id, position):
				st.approach_position, st.approach_progress = (pc.id, position), now
				st.approach_retry = False
			idle = now - st.approach_progress
			if idle > 25:
				return fail('party could not reach %s, no approach progress for 25 seconds' % ident)
			if idle > 8 and not st.approach_retry:
				log('TALK retrying blocked approach to %s with %s' % (ident, pc))
				pc.anim_goal_interrupt()
				st.next_walk = 0
				st.last_walk = None
				st.approach_retry = True
			if open_door_on_route(pc, (x, y)):
				return 0
			lx,ly = location_to_axis(pc.location)
			if max(abs(lx-x),abs(ly-y)) <= 16:
				import debug
				# A speaker behind an open door can be reached from the threshold.
				# Pick a tile the speaker can stand on, including the edge of talking range.
				near = [(x+dx,y+dy) for dx in range(-6,7) for dy in range(-6,7)]
				near.sort(key=lambda pt: ((pt[0]-lx)**2+(pt[1]-ly)**2,(pt[0]-x)**2+(pt[1]-y)**2))
				point = next((pt for pt in near if pt != (lx,ly) and debug.pathto(pc,*pt)),None)
				if point:
					pc.run_to(location_from_axis(*point))
					return 0
			walk_party(st, (x, y), 6, pc)
			return 0
		prepare_dialogue(st)
		st.talks += 1
		log('TALK %s #%d at %s, %s at %s, distance %.1f ft' % (ident, st.talks, location_to_axis(o.location), pc, location_to_axis(pc.location), pc.distance_to(o)))
		chapter_camera.frame(o, pc)
		o.object_script_execute(pc, san_dialog)
		st.next_talk = st.n + 20
	return 0

def fail(msg):
	ST['fail'] = msg; log('ANOMALY ' + msg)
	return 1

SPELL_PREPARATIONS = (
	(stat_level_cleric, 0, (spell_cure_minor_wounds,)),
	(stat_level_cleric, 1, (spell_cure_light_wounds, spell_cure_light_wounds, spell_bless)),
	(stat_level_cleric, 2, (spell_cure_moderate_wounds,)),
	(stat_level_wizard, 1, (spell_sleep, spell_magic_missile, spell_mage_armor)),
	(stat_level_wizard, 2, (spell_scorching_ray, spell_melfs_acid_arrow)))

def unfilled_spell_slots():
	slots = []
	for pc in game.party:
		for cls,level,choices in SPELL_PREPARATIONS:
			if pc.stat_level_get(cls) < 2:
				continue
			code = cls | 0x80
			known = [s.spell_enum for s in pc.spells_known if s.spell_class == code and s.spell_level == level]
			selected = [spell for spell in choices if spell in known]
			if not selected:
				continue
			book = [s for s in pc.spells_memorized if s.spell_class == code and s.spell_level == level]
			for i in range(len(book), pc.get_num_spells_per_day(code, level)):
				slots.append((pc, selected[i % len(selected)], code, level))
	return slots

def ready_party():
	for pc in game.party:
		pc.item_wield_best_all()
		# Choose a fresh pregen's starting spells from its own spellbook.
		for cls, level, choices in SPELL_PREPARATIONS:
			if not pc.stat_level_get(cls):
				continue
			code = cls | 0x80
			known = set(s.spell_enum for s in pc.spells_known if s.spell_class == code and s.spell_level == level)
			selected = [spell for spell in choices if spell in known]
			book = [s.spell_enum for s in pc.spells_memorized if s.spell_class == code and s.spell_level == level]
			capacity = pc.get_num_spells_per_day(code, level)
			if selected and capacity > 0:
				others = [(s.spell_enum, s.spell_class, s.spell_level) for s in pc.spells_memorized
				          if s.spell_class != code or s.spell_level != level]
				book = [selected[i % len(selected)] for i in range(capacity)]
				pc.spells_memorized_forget()
				for spell, original, other_level in others:
					pc.spell_memorized_add(spell, original, other_level, int(not(original & 0x80)))
				for spell in book:
					pc.spell_memorized_add(spell, code, level)
			log('SPELLBOOK %s level %d preparations %s of %d' % (pc, level, book, capacity))

def step_newgame(st):
	m = get_current_map()
	if st.n == 1:
		log('NEW GAME started on map %d, party %d' % (m, len(game.party)))
		ready_party()
	if st.n == 60:
		shot('newgame_%d' % m)
	return st.n > 80

def step_greet(st):
	'''the new-game opening: Hrothgar walks up and talks (his EHHROTHT script); answer with the first replies'''
	import ie_cutscene
	if dlg.is_engaged() or ie_cutscene.active():
		return 0
	# The dialogue handler consumes the greeting before the quest step runs again.
	known = V('Know_Hrothgar')
	if known:
		log('GREET done (Know_Hrothgar %d, Join_Posse %d)' % (known, V('Join_Posse')))
		return 1
	if st.n > 900:
		log('ANOMALY Hrothgar did not greet the party within 90 s (map %d)' % get_current_map()); return 1
	return 0

def step_caravan(st):
	if V('Caravan_Quest') >= 2:
		st.found = getattr(st, 'found', st.n)
		if st.n == st.found + 30:
			shot('caravan')
		if st.n < st.found + 60:
			return 0
		log('CARAVAN found (Caravan_Quest %d)' % V('Caravan_Quest')); return 1
	if get_current_map() != area_map('AR1200'):
		return walk_to_area(st, 'AR1200')
	import ie_travel_data as D
	trig = [t for t in D.AREAS['AR1200'].get('triggers', []) if t.get('module') == 'ie_bcs_caratrg1_area']
	if not trig:
		return fail('no CARATRG1 trigger in AR1200')
	if not hasattr(st, 'at'):
		xs, ys = zip(*trig[0]['poly'])
		st.at = (int(sum(xs) / len(xs)), int(sum(ys) / len(ys))); st.t0 = st.n
		log('CARAVAN walking into CARATRG1 at %s' % (st.at,))
	walk_party(st, st.at, 1)
	return st.n > st.t0 + 1500 and fail('Caravan_Quest stays %d at CARATRG1' % V('Caravan_Quest'))

def step_ar2000(st):
	if get_current_map() == area_map('AR2000'):
		st.arr = getattr(st, 'arr', st.n)
		if st.n == st.arr + 30:
			shot('ar2000')
		if st.n >= st.arr + 40:
			log('SUMMARY CH1 %s: AR2000 reached (CHAPTER %d, AR2000_INIT %d, AR2000_visited %d)' % (
				side_result(), V('CHAPTER'), V('AR2000_INIT'), V('AR2000_visited')))
			return 1
		return 0
	return st.n > 1200 and fail('no jump to AR2000 after the departure talk')

def revisit_open_quests(st):
	"""Use the last town visit to retry an unfinished errand before the chapter leaves it behind."""
	current = ST['i']
	previous = ST['steps'][:current]
	seen = set()
	pending = []
	for step in previous:
		if step.kind in side.OUTCOMES and step.kind not in seen:
			seen.add(step.kind)
			if not side.OUTCOMES[step.kind]():
				pending.append(Step(step.kind, fn=step.fn))
	if pending:
		log('SIDEQUEST revisiting ' + ', '.join(step.kind for step in pending))
		ST['steps'][current+1:current+1] = pending
	return 1

STEPS = [
	('newgame', step_newgame),
	('greet', step_greet),
	('posse', lambda st: talk_step(st, 'hrothgar', 'AR1004', r'"Caravan_Quest", "GLOBAL", 1\)|"Know_Hrothgar", "GLOBAL", 1\)',
	                               lambda: V('Caravan_Quest') >= 1)),
] + side.easthaven([
	('caravan', step_caravan),
	('list', lambda st: talk_step(st, 'hrothgar', 'AR1004', r'GiveItemCreate\(c, "List"', lambda: V('Supply_Quest') >= 1)),
	('pomab', lambda st: talk_step(st, 'pomab', 'AR1007', r'TakePartyItem\(c, "List"', lambda: V('Supply_Quest') >= 2)),
	('ammunition', side.stock_ammunition),
	('outfit', side.outfit_at_pomab),
]) + [
	('town_returns', revisit_open_quests),
	('depart', lambda st: talk_step(st, 'hrothgar', 'AR1004', r'StartCutScene\(c, "EHHrothM"',
	                                lambda: get_current_map() == area_map('AR2000') or ST.get('departed'))),
	('ar2000', step_ar2000),
]

# ---- IWD2 (AUTOPLAYER_SCENARIO=iwd2_ch1, module ToEE of the iwd2-targos convert) ----
def step_newgame2(st):
	"""new game in the ToEE module (the party starts in the base module's opening): go to Targos"""
	if st.n == 1:
		log('NEW GAME started on map %d, party %d' % (get_current_map(), len(game.party)))
	if dlg.is_engaged():
		dlg_reply(0); return 0          # (a vignette or greeting of the base module: answer and move on)
	if get_current_map() != area_map('I2AR1000'):
		if st.n > 400:
			return fail('new game did not reach Targos docks')
		return 0
	if not hasattr(st, 'arrived'):
		ready_party()
		for pc in game.party:
			log('PARTY %s weapon=%s armor=%s HP=%d' % (pc, pc.item_worn_at(3), pc.item_worn_at(5), pc.stat_level_get(stat_hp_current)))
		st.arrived = st.n
		shot('targos_docks')
	return st.n >= st.arrived + 20

DOCK_AREAS = ('AR1000', 'AR1002', 'AR1004', 'AR1005', 'AR1007')


_walk_nodes = {}

def walk_waypoint(leader, start, dest):
	"""Use the map's linked walking nodes to get around buildings and the dock gangplank."""
	import debug, heapq, math, struct
	def distance(a, b):
		return math.hypot(a[0]-b[0], a[1]-b[1])
	if distance(start, dest) <= 32 and debug.pathto(leader, int(dest[0]), int(dest[1])):
		return dest
	area = area_of(leader.map)
	if area not in _walk_nodes:
		directory = os.path.join(E.find_core()[:-5], 'maps', area)
		# The converter tests the baked graph against sector blocking. TemplePlus's
		# expanded graph also links nodes across impassable buildings in Targos.
		for name in ('pathnode.pnd', 'pathnodenew.pnd'):
			path = os.path.join(directory, name)
			if os.path.isfile(path):
				break
		nodes = {}
		if os.path.isfile(path):
			with open(path, 'rb') as f:
				for _ in range(struct.unpack('<i', f.read(4))[0]):
					idx, x, y, ox, oy, count = struct.unpack('<iIIffi', f.read(24))
					nodes[idx] = ((x,y), struct.unpack('<%di' % count, f.read(4*count)))
		_walk_nodes[area] = nodes
	nodes = _walk_nodes[area]
	if not nodes:
		return local_waypoint(leader, start, dest)
	near = sorted(nodes, key=lambda i: distance(nodes[i][0], start))
	src = next((i for i in near[:8] if distance(nodes[i][0], start) <= 3 or debug.pathto(leader, *nodes[i][0])), None)
	if src is None:
		return local_waypoint(leader, start, dest)
	goal = min(nodes, key=lambda i: distance(nodes[i][0], dest))
	steps, queue = {src: (0, None)}, [(0, src)]
	while queue:
		cost, i = heapq.heappop(queue)
		if i == goal:
			break
		if cost != steps[i][0]:
			continue
		for j in nodes[i][1]:
			new = cost + distance(nodes[i][0], nodes[j][0])
			if j not in steps or new < steps[j][0]:
				steps[j] = (new, i)
				heapq.heappush(queue, (new, j))
	if goal not in steps:
		return local_waypoint(leader, start, dest)
	route = []
	while goal != src:
		route.append(nodes[goal][0])
		goal = steps[goal][1]
	for point in route:
		if 3 < distance(point, start) <= 32 and debug.pathto(leader, *point):
			return point
	# A doorway, creature, or a small prop can occupy a path node. Try a
	# nearby tile on the way to the next node instead of running into it.
	for point in reversed(route):
		if distance(point, start) <= 3:
			continue
		for radius in (1, 2, 3):
			near = [(point[0]+dx, point[1]+dy) for dx in range(-radius,radius+1)
			        for dy in range(-radius,radius+1) if max(abs(dx),abs(dy)) == radius]
			near.sort(key=lambda p: distance(p, dest))
			for p in near:
				if debug.pathto(leader, *p):
					return p
		break
	return local_waypoint(leader, start, dest)


_ground_tiles = {}


def ground_waypoint(pc, start, dest):
	"""Route around a blocked graph link using the current map's actual walkable tiles."""
	import debug, heapq
	# TemplePlus sector flags for blocked or fly-over subtiles and legacy TF_Blocks.
	blocked_tile_flags = 0x1 | 0x7FFFE00
	if not hasattr(game,'tile_flags_get'):
		return start
	tiles = _ground_tiles.setdefault(pc.map,{})
	def clear(p):
		if p not in tiles:
			tiles[p] = not (game.tile_flags_get(location_from_axis(*p)) & blocked_tile_flags)
		return tiles[p]
	def distance(p,q):
		return max(abs(p[0]-q[0]),abs(p[1]-q[1]))
	goal = tuple(dest)
	ends = [(goal[0]+x,goal[1]+y) for x in range(-3,4) for y in range(-3,4)]
	ends = sorted((p for p in ends if clear(p)),key=lambda p: (distance(p,goal),distance(p,start)))
	if not ends:
		return start
	goal = ends[0]
	queue,parents,costs = [(distance(start,goal),0,start)],{start:None},{start:0}
	while queue and len(parents) < 10000:
		unused,cost,at = heapq.heappop(queue)
		if at == goal:
			break
		if cost != costs[at]:
			continue
		for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(-1,-1),(-1,1),(1,-1)):
			p = at[0]+dx, at[1]+dy
			if distance(start,p) > distance(start,goal)+35 or not clear(p):
				continue
			if dx and dy and not (clear((at[0]+dx,at[1])) and clear((at[0],at[1]+dy))):
				continue
			new = cost + (1.42 if dx and dy else 1)
			if new >= costs.get(p,1e9):
				continue
			parents[p],costs[p] = at,new
			heapq.heappush(queue,(new+distance(p,goal),new,p))
	if goal not in parents:
		return start
	at = goal
	while at != start:
		if distance(at,start) <= 14 and debug.pathto(pc,*at):
			return at
		at = parents[at]
	return start


def local_waypoint(pc, start, dest):
	"""Advance to a reachable intermediate tile when the destination itself is obstructed."""
	import debug
	dx, dy = dest[0]-start[0], dest[1]-start[1]
	length = max(abs(dx),abs(dy),1)
	for distance in (10, 6, 3):
		span = min(length,distance)
		for side in (0, 2, -2, 4, -4):
			x = start[0] + int(round((span*dx - side*dy)/float(length)))
			y = start[1] + int(round((span*dy + side*dx)/float(length)))
			if (x,y) != start and debug.pathto(pc,x,y):
				return x,y
	return ground_waypoint(pc,start,dest)

def open_door_on_route(pc, dest):
	"""Approach and open a visible, unlocked door between the walker and a nearby destination."""
	import debug, ie_doors
	x,y = location_to_axis(pc.location)
	dx,dy = dest[0]-x,dest[1]-y
	length = dx*dx + dy*dy
	if not length or length > 25*25 or ie_doors._area != area_of(pc.map):
		return False
	candidates = []
	for spec,portal,_ in ie_doors._doors:
		if spec.get('secret') or not portal or ie_doors._is_open(portal) or portal.portal_flags_get() & OPF_LOCKED:
			continue
		px,py = spec['loc'][:2]
		vx,vy = px-x,py-y
		projection = vx*dx + vy*dy
		if projection < -2 or projection > length+3 or (vx*dy-vy*dx)**2 > 9*length:
			continue
		candidates.append((vx*vx+vy*vy,spec,portal))
	for _,spec,portal in sorted(candidates,key=lambda item:item[0]):
		if pc.distance_to(portal) <= 7:
			if spec.get('script'):
				import controller_ui_util as ui
				ui.select_party(list(game.party).index(pc))
				game.scroll_to(portal.location)
				ok, message = ui.verified_click(portal, 'use', log, fallback=None)
				return ok
			portal.portal_toggle_open()
			log('OPEN %s while approaching %s' % (spec['name'],dest))
			return True
		if debug.pathto(pc,int(dest[0]),int(dest[1])):
			return False
		px,py = spec['loc'][:2]
		near = [(px+i,py+j) for i in range(-2,3) for j in range(-2,3)]
		near.sort(key=lambda pt: ((pt[0]-px)**2+(pt[1]-py)**2,(pt[0]-x)**2+(pt[1]-y)**2))
		point = next((pt for pt in near if debug.pathto(pc,*pt)),None)
		if point:
			pc.run_to(location_from_axis(*point))
			return True
	return False


def walk_party(st, dest, radius, lead=None):
	party = [pc for pc in game.party if not pc.is_unconscious()]
	if not party:
		return False
	front = lead or next((pc for pc in party if pc.id == getattr(st,'walk_leader',None)),None)
	if front in party:
		party.remove(front)
		party.insert(0, front)
	leader = party[0]
	x, y = location_to_axis(leader.location)
	close = max(abs(dest[0] - x), abs(dest[1] - y)) <= radius
	if close:
		return True
	if st.n >= getattr(st, 'next_walk', 0):
		st.next_walk = st.n + 20
		if open_door_on_route(leader, dest):
			return False
		import debug
		for pc in party[1:]:
			pos = location_to_axis(pc.location)
			if max(abs(pos[0]-x), abs(pos[1]-y)) > 12:
				tx, ty = walk_waypoint(pc, pos, (x,y))
				pc.run_to(location_from_axis(int(tx), int(ty)))
		last = getattr(st, 'last_walk', None)
		if last and getattr(st, 'last_dest', None) == tuple(dest) and last[0] != (x,y):
			px, py = last[1]
			if max(abs(px-x), abs(py-y)) > 3:
				st.last_walk = ((x,y), last[1])
				return False
		st.last_dest = tuple(dest)
		goal = dest
		if max(abs(x-dest[0]), abs(y-dest[1])) <= 16:
			# NPCs, containers and exit icons occupy the destination tile.
			# Choose a reachable interaction tile before asking for a waypoint.
			near = [(dest[0]+dx, dest[1]+dy) for dx in range(-radius,radius+1)
			        for dy in range(-radius,radius+1)]
			near.sort(key=lambda p: (max(abs(x-p[0]),abs(y-p[1])), abs(p[0]-dest[0])+abs(p[1]-dest[1])))
			goal = next((p for p in near if debug.pathto(leader,int(p[0]),int(p[1]))), dest)
		nx, ny = walk_waypoint(leader, (x,y), goal)
		if (nx,ny) == (x,y) and (x,y) != goal:
			for member in party[1:]:
				pos = location_to_axis(member.location)
				waypoint = walk_waypoint(member,pos,goal)
				if waypoint == pos or not debug.pathto(member,*waypoint):
					continue
				member.run_to(location_from_axis(*waypoint))
				if lead is None:
					st.walk_leader = member.id
					st.last_walk = None
					log('WALK %s leads around the obstruction at %s' % (member,(x,y)))
					return False
			if st.n >= getattr(st,'next_blocked_log',0):
				st.next_blocked_log = st.n+200
				log('WALK blocked at %s on map %s toward %s' % ((x,y),leader.map,goal))
		if getattr(st,'close_formation',False) and max(abs(nx-x),abs(ny-y)) > 10:
			nx,ny = local_waypoint(leader,(x,y),(nx,ny))
		stalled = getattr(st, 'last_walk', None) == ((x,y),(nx,ny))
		st.last_walk = ((x,y),(nx,ny))
		if st.n >= getattr(st, 'next_walk_log', 0):
			st.next_walk_log = st.n + 100
			log('WALK party %s via %s towards %s' % ((x,y),(nx,ny),dest))
		loc = location_from_axis(int(nx), int(ny))
		if stalled and not leader.is_performing():
			try:
				leader.action_perform(D20A_UNSPECIFIED_MOVE, OBJ_HANDLE_NULL, loc)
			except RuntimeError:
				leader.run_to(loc)
		else:
			leader.run_to(loc)
		dx, dy = nx-x, ny-y
		length = max(abs(dx), abs(dy), 1)
		for i, pc in enumerate(party[1:]):
			pos = location_to_axis(pc.location)
			if max(abs(pos[0]-x), abs(pos[1]-y)) > 12:
				continue
			behind = 1 if i == 0 else 3
			side = 1 if i % 2 == 0 else -1
			tx = int(round(nx - (behind*dx + side*dy)/float(length)))
			ty = int(round(ny - (behind*dy - side*dx)/float(length)))
			if not debug.pathto(pc, tx, ty):
				tx, ty = int(nx), int(ny)
			pc.run_to(location_from_axis(tx, ty))
	return False


def walk_to_area(st, area):
	ST['walking_to'] = area
	cur = area_of(get_current_map())
	path = E.route(cur, area) if cur else None
	if not path:
		return fail('no connected exit from %s to %s' % (cur, area))
	hop = (cur, path[0])
	if getattr(st, 'hop', None) != hop:
		st.hop, st.hop_start, st.next_walk, st.next_click = hop, st.n, 0, 0
		st.exit_clicks = 0
		log('WALK %s -> %s' % hop)
	if st.n - st.hop_start > 1500:
		return fail('could not reach the exit %s -> %s' % hop)
	import ie_travel_data as D
	region = next(r for r in D.AREAS[cur]['regions'] if r['dest_area'] == hop[1])
	if region.get('world_jump'):
		try:
			import ie_atlas
		except ImportError:
			ie_atlas = None  # older conversions travel directly from the exit
		if ie_atlas and ie_atlas.active():
			if not getattr(st, 'atlas_since', 0):
				st.atlas_since = time.time()
			elif time.time() - st.atlas_since >= 3:
				st.atlas_since = 0
				if not ie_atlas.select(hop[1]):
					return fail('world map does not offer %s from %s' % (hop[1], cur))
			return False
	center = region.get('anchor') or E.region_center(region)
	if walk_party(st, center, 5 if st.exit_clicks < 2 else 2) and st.n >= st.next_click:
		st.next_click = st.n + 35
		st.exit_clicks += 1
		if st.exit_clicks > 2 and not region.get('world_jump') and not getattr(st, 'require_click', False):
			import ie_travel
			log('EXIT using %s at %s -> %s' % (region['name'], location_to_axis(game.leader.location), hop[1]))
			ie_travel.travel(region)
			return 0
		icon, unused = E.icon_for(*hop)
		if icon != OBJ_HANDLE_NULL:
			import controller_ui_util as ui
			if getattr(st, 'require_click', False):
				# The previously selected combatant may still be in the last room.
				players = [(i, pc) for i, pc in enumerate(game.party) if pc.type == obj_t_pc and not pc.is_unconscious()]
				if players:
					i, actor = min(players, key=lambda pair: pair[1].distance_to(icon))
					if st.exit_clicks > 2 and actor.distance_to(icon) <= 7 and actor.has_los(icon):
						# The same use-object goal that a mouse click queues on the selected PC.
						if not actor.is_performing():
							actor.anim_goal_use_object(icon)
							log('EXIT %s uses %s' % (actor, region['name']))
						return 0
					ui.select_party(i)
			game.scroll_to(icon.location)
			ok, message = ui.verified_click(icon, 'jump', log, fallback=None)
			if st.exit_clicks in (1, 3, 10):
				log('EXIT %s attempt %d at %s: %s; party distances %s' %
				    (region['name'], st.exit_clicks, location_to_axis(icon.location), message,
				     [round(pc.distance_to(icon), 1) for pc in game.party]))
	return 0


def targos_enemy(npc, include_dying=False):
	"""The converted scripts set ONF_KOS when an NPC becomes hostile to the party."""
	return (npc.npc_flags_get() & ONF_KOS and npc not in game.party and npc.leader_get() == OBJ_HANDLE_NULL
	        and not npc.object_flags_get() & (OF_OFF | OF_DONTDRAW | OF_CLICK_THROUGH)
	        and (not npc.is_unconscious() or (include_dying and -10 < npc.stat_level_get(stat_hp_current) < 0)))


def rally_before_fight(st, leader):
	"""Wait for stragglers before the front line advances on another group of enemies."""
	x,y = location_to_axis(leader.location)
	behind = [pc for pc in game.party if not pc.is_unconscious() and pc.distance_to(leader) > 23]
	if not behind:
		st.rally_since = None
		return False
	if st.n < getattr(st, 'next_rally', 0):
		return False
	if getattr(st, 'rally_since', None) is None:
		st.rally_since = st.n
		log('RALLY waiting for %s' % ', '.join(str(p) for p in behind))
	if st.n - st.rally_since > 100:
		st.rally_since, st.next_rally = None, st.n + 100
		return False
	now = time.time()
	if now < getattr(st, 'rally_order_at', 0):
		return True
	st.rally_order_at = now + 1
	gather_at(behind, (x, y))
	return True


def gather_at(behind, point):
	import debug
	x,y = point
	for pc in behind:
		start = location_to_axis(pc.location)
		near = [(x+dx,y+dy) for dx,dy in ((-2,0),(2,0),(0,-2),(0,2),(-2,-2),(2,2))]
		near.sort(key=lambda p: (p[0]-start[0])**2 + (p[1]-start[1])**2)
		goal = next((p for p in near if debug.pathto(pc,*p)),(x,y))
		wx,wy = walk_waypoint(pc,start,goal)
		pc.run_to(location_from_axis(int(wx),int(wy)))


def regroup_at_cave_entrance(st):
	"""Hold the next quest action until the party is together and recovered."""
	regroup = ST['cave_regroup']
	x, y = regroup['point']
	living = [pc for pc in game.party if not pc.is_dead_or_destroyed()]
	now = time.time()
	behind = []
	for pc in living:
		px, py = location_to_axis(pc.location)
		if (px-x)**2 + (py-y)**2 > 16:
			behind.append(pc)
	if now - regroup['start'] > 40:
		fail('party could not regroup and heal at the cave entrance')
		return True
	if behind and now >= regroup.get('order_at', 0):
		gather_at([pc for pc in behind if not pc.is_unconscious()], (x,y))
		regroup['order_at'] = now + 1
	hp = [(pc.stat_level_get(stat_hp_current), pc.stat_level_get(stat_hp_max)) for pc in living]
	if any(cur < maximum for cur, maximum in hp):
		recover_after_battle(st, heal_only=True)
	if behind or any(cur < maximum for cur, maximum in hp):
		regroup.pop('ready_at', None)
		return True
	# Leave a visible beat after the last straggler arrives before picking a target.
	if now < regroup.setdefault('ready_at', now + 3):
		return True
	log('REGROUP ready at %s after %.1fs; all %d survivors within 4 tiles; HP %s' %
	    ((x,y), now-regroup['start'], len(living), hp))
	del ST['cave_regroup']
	ST['cave_entrance_recovered'] = True
	return False


def step_fight(st, area, flag):
	"""Fight in this area until its own script records victory."""
	if V(flag):
		return 1
	if get_current_map() != area_map('I2' + area):
		return walk_to_area(st, 'I2' + area)
	if not hasattr(st, 'fight_start'):
		st.fight_start = st.n
	if st.n - st.fight_start > 3600:
		return fail('%s: the battle did not set %s' % (area, flag))
	if st.n % 12 != 1:
		return 0
	import ie_runtime as rt
	leader = next(pc for pc in game.party if not pc.is_unconscious())
	if rally_before_fight(st, leader):
		return 0
	st.close_formation = True
	enemies = [o for o in game.obj_list_vicinity(leader.location, OLC_NPC) if targos_enemy(o)]
	if not enemies and st.kind == 'palisade':
		# Follow the visible raiders across the walls before searching their
		# starting positions. Later waves can still be hidden by the area script.
		enemies = [o for o in game.obj_list_range(leader.location, 300, OLC_NPC) if targos_enemy(o)]
	if enemies:
		target = min(enemies, key=lambda o: leader.distance_to(o))
		if st.kind == 'palisade' and st.n >= getattr(st, 'next_volley', 0):
			# Give the raiders a reason to approach the front line while the
			# party still has room to get a shot off.
			for pc in game.party:
				if pc.is_unconscious() or pc.is_performing() or not pc.get_ammo_used():
					continue
				if not (15 < pc.distance_to(target) <= 60 and pc.has_los(target)):
					continue
				st.next_volley = st.n + 80
				try:
					pc.action_perform(D20A_UNSPECIFIED_ATTACK, target, 0)
					chapter_camera.frame(pc, target)
					log('OPENING %s fires from the formation at %s' % (pc, target))
					return 0
				except RuntimeError:
					break
		dest = location_to_axis(target.location)
	else:
		if not hasattr(st, 'patrol'):
			actors = __import__('ie_creatures_' + area.lower()).CREATURES
			allowed = getattr(rt, 'area_spawn_allowed', None)
			st.patrol = [rt.ie_to_tile(area, a['x'], a['y']) for a in actors
			             if a.get('ident') and a.get('hostility') == 'hostile' and a.get('x') is not None
			             and (not allowed or allowed(a))]
			x, y = location_to_axis(leader.location)
			st.patrol.sort(key=lambda p: (p[0]-x)**2 + (p[1]-y)**2)
			st.waypoint = 0
		if not st.patrol:
			return fail('no hostile placements to search in ' + area)
		dest = st.patrol[st.waypoint]
		pos = location_to_axis(leader.location)
		if pos != getattr(st, 'last_pos', None):
			st.last_progress = st.n
		if max(abs(pos[0] - dest[0]), abs(pos[1] - dest[1])) <= 5 or st.n - getattr(st, 'last_progress', 0) > 100:
			st.waypoint = (st.waypoint + 1) % len(st.patrol)
			dest = st.patrol[st.waypoint]
			st.last_progress = st.n
		st.last_pos = pos
	walk_party(st, dest, 2)
	return 0


def clear_dock_areas(st, areas):
	for area in areas:
		flag = area + '_GOBLINS_CLEAR'
		if not V(flag):
			if getattr(st, 'area', None) != area:
				st.area, st.fight = area, Step(area)
				log('DOCKS clearing ' + area)
			st.fight.n += 1
			step_fight(st.fight, area, flag)
			return 0
	return 1


def step_docks(st):
	if not clear_dock_areas(st, DOCK_AREAS):
		return 0
	if V('Dock_Goblin_Quest'):
		log('DOCKS all five areas clear, Dock_Goblin_Quest %d' % V('Dock_Goblin_Quest'))
		return 1
	st.wait = getattr(st, 'wait', 0) + 1
	return st.wait > 120 and fail('all dock areas clear but Dock_Goblin_Quest is still 0')


def step_palisade(st):
	if st.n == 100:
		shot('palisade')
	return step_fight(st, 'AR1200', 'Goblin_Palisade_Quest')


def quest_talk(ident, area, name, value):
	goal = r'"%s", "GLOBAL", %d\)' % (name, value)
	return lambda st: talk_step(st, ident, area, goal, lambda: V(name) >= value)


def step_crane(st):
	"""Put Jorun's wheel into the crane's converted container and wait for its script."""
	import ie_itemrt as items
	if V('Crane_Wheel') > 0:
		return 1
	if get_current_map() != area_map('I2AR1100'):
		return walk_to_area(st, 'I2AR1100')
	if getattr(st, 'installed', False):
		return st.n > st.installed + 120 and fail('wheel is in the crane but Crane_Wheel remained 0')
	if st.n % 20 != 10:
		return 0
	specs = [c for c in items.CONTAINERS.get('I2AR1100', items.CONTAINERS.get('AR1100', []))
	         if c['name'].lower() == 'ar1100_wheel']
	if len(specs) != 1:
		return fail('missing or ambiguous converted crane container')
	spec = specs[0]
	x, y = map(int, spec['toee'])
	carrier = next((pc for pc in game.party if items.find(pc, '10gencrw')), None)
	if carrier is not None:
		if carrier.is_unconscious():
			return fail('the party member carrying the crane wheel is unconscious')
	boxes = [o for o in game.obj_list_vicinity(location_from_axis(x, y), OLC_CONTAINER)
	         if o.proto == spec['proto'] and location_to_axis(o.location) == (x, y)]
	if len(boxes) != 1:
		return fail('expected one crane container at %d,%d, found %d' % (x, y, len(boxes)))
	box = boxes[0]
	if not items.find(box, '10gencrw'):
		if carrier is None:
			return fail("Jorun's wheel is missing from both the party and the crane")
		# The crane occupies a walkable tile. A ray to the scenery on the
		# carrier's own tile can be blocked even when the wheel is in reach.
		if carrier.distance_to(box) > 8 or (carrier.location != box.location and not carrier.has_los(box)):
			if not hasattr(st, 'walk_start'):
				st.walk_start = st.n
				log('CRANE walking from %s to %s' % (location_to_axis(carrier.location), (x, y)))
			if st.n - st.walk_start > 1500:
				return fail('wheel carrier did not reach the crane at %s' % ((x, y),))
			walk_party(st, (x, y), 0, carrier)
			return 0
		if box.container_flags_get() & OCOF_LOCKED:
			return fail('the crane is locked before the wheel can be installed')
		box.item_get(items.find(carrier, '10gencrw'))
	if not items.find(box, '10gencrw'):
		return fail("could not place Jorun's wheel in the crane")
	log('CRANE replacement wheel in %s at %d,%d' % (spec['name'], x, y))
	st.installed = st.n
	return 0


def step_end2(st):
	if not (V('Goblin_Palisade_Quest') and V('Shaengarne_Quest') and V('AR2000_Revealed')):
		return fail('missing palisade victory or Shaengarne assignment')
	log('SUMMARY IWD2 CH1 %s: palisade defended, Ulbrec assigned Shaengarne, AR2000 revealed' % side_result())
	return 1


def side_result():
	missed = sorted(set(step.kind for step in ST['steps'] if step.kind in side.OUTCOMES and not side.OUTCOMES[step.kind]()))
	return 'PARTIAL (unfinished: %s)' % ', '.join(missed) if missed else 'PASS'

def dock_vellum(st):
	if st.n > 600:
		log('VELLUM will look again when investigating Phaen')
		return 1
	if not hasattr(st, 'search'):
		st.search = side.encounter('I2AR1007', '10rukwu', (572,564), lambda: side.has('10vellum'), '10vellum')
	return st.search(st)

STEPS2 = [
	('newgame', step_newgame2),
] + side.targos_before_docks_clear() + [
	('dock_houses', lambda st: clear_dock_areas(st, DOCK_AREAS[:-1])),
] + side.targos_docks() + [
	('docks', step_docks),
	('vellum', dock_vellum),
] + side.targos_town('market') + [
	('shawford0', quest_talk('12shawfo', 'I2AR1201', 'Lumber_Quest', 1)),
] + side.targos_town('palisade') + [
	('olap', quest_talk('12olap', 'I2AR1200', 'Lumber_Quest', 2)),
	('lumbar', quest_talk('11lumbar', 'I2AR1100', 'Know_Crane_Broke', 1)),
	('olap_jorun', quest_talk('12olap', 'I2AR1200', 'Lumber_Quest', 3)),
	('jorun', quest_talk('10jorun', 'I2AR1000', 'Lumber_Quest', 4)),
	('crane', step_crane),
	('shawford1', quest_talk('12shawfo', 'I2AR1201', 'Arrow_Quest', 1)),
	('isherwood', quest_talk('12isher', 'I2AR1200', 'Arrow_Quest', 2)),
	('deirdre', quest_talk('11deird', 'I2AR1102', 'Arrow_Quest', 3)),
	('shawford2', quest_talk('12shawfo', 'I2AR1201', 'Dead_Goblin_Quest', 1)),
	('koluhm', lambda st: talk_step(st, '11koluhm', 'I2AR1107', r'"Dead_Goblin_Quest", "GLOBAL", [2-5]\)', lambda: V('Dead_Goblin_Quest') >= 2)),
	('shawford3', quest_talk('12shawfo', 'I2AR1201', 'Palisade_Iron_Collar_Quest', 1)),
	('geoffrey', quest_talk('10black', 'I2AR1003', 'Palisade_Iron_Collar_Quest', 2)),
] + side.targos_town('returns') + [
	('town_returns', revisit_open_quests),
	('supplies', side.buy_healing_supplies),
	('ammunition', side.stock_ammunition),
	('shawford4', quest_talk('12shawfo', 'I2AR1201', 'Goblins_Attack_Palisade', 1)),
	('palisade', step_palisade),
	('ulbrec', quest_talk('11ulbrec', 'I2AR1101', 'Shaengarne_Quest', 1)),
	('end', step_end2),
]
STATUS = {'iwd': ('Join_Posse', 'Caravan_Quest', 'Supply_Quest'),
          'iwd2': ('Dock_Goblin_Quest', 'Lumber_Quest', 'Arrow_Quest', 'Dead_Goblin_Quest', 'Palisade_Iron_Collar_Quest', 'Goblins_Attack_Palisade', 'Shaengarne_Quest')}
GAME = {'g': 'iwd'}
ST = {'i': 0, 'steps': None, 'fail': None}

def assist_party(in_combat):
	'''Give chapter PCs a fixed stat floor and clear damage once after initiative ends.'''
	if os.environ.get('IWDAP_COMBAT_ASSIST') == '0':
		return
	prepared = ST.setdefault('assisted_pcs', set())
	after_fight = ST.get('assist_in_combat', False) and not in_combat
	ST['assist_in_combat'] = in_combat
	for pc in game.party:
		if pc.type != obj_t_pc:
			continue
		new_pc = pc.id not in prepared
		if not (new_pc or after_fight) or pc.is_dead_or_destroyed():
			continue
		if new_pc:
			for stat in (stat_strength, stat_dexterity, stat_constitution):
				if pc.stat_base_get(stat) < 24:
					pc.stat_base_set(stat, 24)
			if pc.obj_get_int(obj_f_hp_pts) < 64:
				pc.obj_set_int(obj_f_hp_pts, 64)
			prepared.add(pc.id)
			log('ASSIST prepared %s, max HP %d' % (pc, pc.stat_level_get(stat_hp_max)))
		if not in_combat:
			damage = pc.obj_get_int(obj_f_hp_damage)
			subdual = pc.obj_get_int(obj_f_critter_subdual_damage)
			if damage or subdual:
				pc.set_hp_damage(0)
				pc.set_subdual_damage(0)
				log('ASSIST healed %s for %d damage and %d subdual' % (pc, damage, subdual))

def checkpoint_party(st, after_battle):
	import ie_cutscene
	if after_battle:
		st.pending_battle_save = True
	if st.kind in ('newgame','greet') or dlg.is_engaged() or ie_cutscene.active():
		return
	if any(p.is_unconscious() or p.stat_level_get(stat_hp_current) <= 0 for p in game.party):
		return
	key = (ST['i'], get_current_map())
	if not getattr(st, 'pending_battle_save', False) and ST.get('checkpoint') == key:
		return
	if st.n < getattr(st, 'next_save_attempt', 0):
		return
	st.next_save_attempt = st.n + 30
	if any(targos_enemy(o) and game.leader.distance_to(o) < 25
	       for o in game.obj_list_vicinity(game.leader.location, OLC_NPC)):
		return
	filename = 'IEAP_Chapter_' + GAME['g']
	if game.savegame(filename, 'Chapter autoplayer recovery'):
		ST['checkpoint'] = key
		st.pending_battle_save = False
		log('CHECKPOINT %s on map %d' % (st.kind, key[1]))


def retry_battle(st):
	"""Let the launcher restart the engine after this combat callback returns."""
	checkpoint = ST.get('checkpoint')
	marker = os.environ.get('IWDAP_RESTART_FILE')
	retries = int(os.environ.get('IWDAP_BATTLE_RETRIES', '0'))
	if not marker or not checkpoint:
		return False
	step = ST['steps'][checkpoint[0]].kind
	if os.environ.get('IWDAP_BATTLE_STEP') != step:
		retries = 0
	if retries >= 3 or int(os.environ.get('IWDAP_TOTAL_RETRIES', '0')) >= 12:
		return False
	with open(marker + '.tmp','w') as output:
		output.write('%d %s\n' % (os.getpid(), step))
	os.rename(marker + '.tmp',marker)
	ST['restarting'] = True
	log('REQUEST RESTART at %s from checkpoint %s, attempt %d/3' % (st.kind,step,retries+1))
	return True


def camping_button(camp, identifier):
	import autoui
	from controller_ui_util import obtain_widget
	button = obtain_widget(identifier)
	if button or identifier == WID_IDEN.UTIL_BAR_CAMP_BTN:
		return button
	# Some ToEE installs expose an invalid name for the original camping window.
	# Recognize the newly opened panel by its Rest/Cancel pair and time controls.
	for wid in autoui.get_active_windows():
		if wid in camp['previous_windows']:
			continue
		window = autoui.TWidget(wid)
		if not window.is_window or not window.visible:
			continue
		buttons = [autoui.TWidget(i) for i in (window.children_ids or ())]
		buttons = [b for b in buttons if b.is_button and b.visible]
		if len(buttons) < 7:
			continue
		rest,cancel = buttons[:2]
		if abs(rest.y-cancel.y) <= 4 and rest.x < cancel.x and buttons[2].y < rest.y and buttons[6].y < rest.y:
			return buttons[identifier[-1]]
	return None


def recover_after_battle(st, prepare=False, heal_only=False):
	"""Camp through the normal UI after a costly battle in a cleared location."""
	import controller_ui_util as ui
	import time
	hp = tuple(pc.stat_level_get(stat_hp_current) for pc in game.party)
	camp = ST.get('camp')
	if camp is None:
		check_slots = ST.pop('check_new_spells',False) or prepare or ST.get('after_battle') or st.n == 0
		slots = unfilled_spell_slots() if check_slots else []
		if not heal_only and ST.get('last_camp') == (get_current_map(), hp):
			return False
		hurt = any(-10 < h < .75 * pc.stat_level_get(stat_hp_max) for h,pc in zip(hp,game.party))
		from controller_callbacks_common import obj_can_cast
		if not heal_only and not hurt and not slots:
			if not prepare and not ST.get('after_battle') and not (st.n == 0 and st.kind in (
			        'grisella','apsel','damien','gaspar','dock_houses','docks','phaen','palisade')):
				return False
			if not any(s.is_used_up() for pc in game.party for s in pc.spells_memorized if s.spell_level == 1):
				return False
		if dlg.is_engaged() or (not heal_only and any(targos_enemy(o) and game.leader.distance_to(o) < 45
		                           for o in game.obj_list_vicinity(game.leader.location, OLC_NPC))):
			return False
		healer = next((p for p in game.party if not p.is_unconscious() and any(
			s.spell_enum == spell_cure_light_wounds and obj_can_cast(p, s.spell_enum, s.spell_class, s.spell_level)
			for s in p.spells_memorized)), None)
		injured = [p for p in game.party if -10 < p.stat_level_get(stat_hp_current) < p.stat_level_get(stat_hp_max)]
		if healer and injured:
			patient = min(injured, key=lambda p: p.stat_level_get(stat_hp_current) / float(p.stat_level_get(stat_hp_max)))
			import time
			now = time.time()
			if now < ST.get('heal_wait', 0):
				return True
			if ST.get('heal_attempt') != (get_current_map(), hp, patient.id):
				ST['heal_attempt'] = (get_current_map(), hp, patient.id)
				ST['heal_wait'] = now + 4
				log('HEAL %s casts Cure Light Wounds on %s' % (healer, patient))
				healer.cast_spell(spell_cure_light_wounds, patient)
				return True
		import random_encounter
		sleep_status = random_encounter.can_sleep()
		if not heal_only and sleep_status == SLEEP_DANGEROUS and not hurt:
			# A fully mobile party can finish the trail and prepare spells
			# back in town without rolling an extra wilderness encounter.
			ST['last_camp'] = (get_current_map(), hp)
			log('CAMP postponing rest on dangerous map %d, party HP %s' % (get_current_map(), hp))
			return False
		no_rest = heal_only or sleep_status in (SLEEP_PASS_TIME_ONLY, SLEEP_IMPOSSIBLE)
		if no_rest or min(hp) < 1 or ST.get('camp_unavailable') == get_current_map():
			from new_game_controller import kit_healing_potion
			if time.time() < ST.get('heal_wait',0):
				return True
			if injured:
				patient = min(injured,key=lambda pc: pc.stat_level_get(stat_hp_current)/float(pc.stat_level_get(stat_hp_max)))
				carriers = sorted((pc for pc in game.party if not pc.is_unconscious()), key=lambda pc: pc.distance_to(patient))
				for pc in carriers:
					potion = kit_healing_potion(pc)
					if not potion:
						continue
					if pc != patient and pc.distance_to(patient) > 5:
						if not patient.is_unconscious():
							continue
						key = (get_current_map(),pc.id,patient.id)
						if key != ST.get('rescue_pair'):
							ST['rescue_pair'], ST['rescue_until'] = key, time.time()+10
						if time.time() < ST['rescue_until']:
							import debug
							tx,ty = location_to_axis(patient.location)
							start = location_to_axis(pc.location)
							near = sorted(((tx+dx,ty+dy) for dx,dy in ((-1,0),(1,0),(0,-1),(0,1))),
							              key=lambda p: (p[0]-start[0])**2 + (p[1]-start[1])**2)
							dest = next((p for p in near if debug.pathto(pc,*p)),(tx,ty))
							x,y = walk_waypoint(pc,start,dest)
							pc.run_to(location_from_axis(int(x),int(y)))
							ST['heal_wait'] = time.time()+1
							return True
						break
					if pc.use_item(potion,patient) == 0:
						ST.pop('rescue_pair', None)
						ST['heal_wait'] = time.time() + 4
						log('HEAL %s uses a healing potion on %s' % (pc,patient))
						return True
			if no_rest or ST.get('camp_unavailable') == get_current_map():
				ST['last_camp'] = (get_current_map(),hp)
				return False
		selected = next((i for i,p in enumerate(game.party) if not p.is_unconscious()), None)
		if selected is not None and game.party[0].is_unconscious():
			ui.select_party(selected)
		game.sleep_status_update()
		import autoui
		camp = ST['camp'] = {'ticks': 0, 'phase': 0, 'hp': hp, 'previous_windows': set(autoui.get_active_windows()),
		                     'start_time': game.time.time_game_in_seconds(game.time)}
		ST['last_camp'] = (get_current_map(), hp)
		log('CAMP seeking recovery on map %d, party HP %s' % (get_current_map(), hp))
	camp['ticks'] += 1
	if camp['ticks'] % 5 != 1:
		return True
	buttons = (WID_IDEN.UTIL_BAR_CAMP_BTN, WID_IDEN.CAMPING_UI_UNTIL_HEALED_BTN,
	           WID_IDEN.CAMPING_UI_DAYS_INC, WID_IDEN.CAMPING_UI_REST_BTN)
	if camp['phase'] < len(buttons):
		widget = camping_button(camp,buttons[camp['phase']])
		if widget and widget.is_button_enabled:
			ui.move_mouse_to_widget(widget)
			game.mouse_click()
			camp['phase'] += 1
		elif camp['phase'] == 1 and camping_button(camp,WID_IDEN.CAMPING_UI_REST_BTN):
			# Until Healed may be disabled when only spell slots need replenishing.
			camp['phase'] = 2
		elif camp['phase'] == 1 and camp['ticks'] in (21,46):
			camp['phase'] = 0
	elif not camping_button(camp,WID_IDEN.CAMPING_UI_REST_BTN):
		if hp == camp['hp'] and camp['ticks'] < 40:
			return True
		log('CAMP %s, party HP %s' % ('recovered' if hp != camp['hp'] else 'no healing', hp))
		if game.time.time_game_in_seconds(game.time) - camp['start_time'] >= 8*3600:
			for pc,spell,code,level in unfilled_spell_slots():
				pc.spell_memorized_add(spell,code,level)
				log('SPELLBOOK %s prepared spell %d in a new level %d slot after resting' % (pc,spell,level))
		del ST['camp']
		return False
	if camp['ticks'] > 100:
		if camping_button(camp,WID_IDEN.CAMPING_UI_REST_BTN):
			ui.press_escape()
		log('CAMP unavailable at control %d, party HP %s' % (camp['phase'],hp))
		ST['camp_unavailable'] = get_current_map()
		ST.pop('last_camp', None)
		del ST['camp']
		return False
	return True

def next_region(st):
	import ie_travel_data as data
	targos = GAME['g'] == 'iwd2'
	destination = 'I2AR2000' if targos else 'AR2100'
	if destination not in data.AREAS:
		return fail('next region missing from converted install: ' + destination)
	if targos and not V('AR2000_Revealed'):
		return fail('Ulbrec has not revealed Shaengarne')
	if get_current_map() != area_map(destination):
		return walk_to_area(st, destination)
	if V('Chapter') < 1:
		st.arrival_tick = getattr(st, 'arrival_tick', st.n)
		return st.n - st.arrival_tick > 200 and fail('arrival script did not advance the chapter')
	shot('shaengarne_arrival' if targos else 'kuldahar_arrival')
	log('PASS next region reached: ' + destination)
	return 1


def enter_vale(st):
	if not V('Vale_Quest'):
		return fail('Arundel has not assigned the Vale of Shadows')
	if get_current_map() != area_map('AR3000'):
		st.require_click = True
		return walk_to_area(st, 'AR3000')
	shot('vale_arrival')
	log('PASS reached the Vale of Shadows with Arundel\'s quest')
	return 1


def use_chapter_portal(st, area, name, pick_lock=False):
	import ie_doors, controller_ui_util as ui
	st.require_click = True
	if get_current_map() != area_map(area):
		return walk_to_area(st, area)
	if getattr(st, 'portal_goal', None) != name:
		st.portal_goal, st.portal_start, st.next_use = name, st.n, 0
	if st.n - st.portal_start > 1200:
		return fail('could not open ' + name)
	for spec, portal, last in ie_doors._doors:
		if spec['name'] != name:
			continue
		if ie_doors._is_open(portal):
			return True
		players = [(i, pc) for i, pc in enumerate(game.party) if pc.type == obj_t_pc and not pc.is_unconscious()]
		locked = pick_lock and portal.portal_flags_get() & OPF_LOCKED
		if locked:
			i, pc = max(players, key=lambda pair: (pair[1].skill_level_get(skill_open_lock), -pair[1].distance_to(portal)))
		else:
			i, pc = min(players, key=lambda pair: pair[1].distance_to(portal))
		if pc.distance_to(portal) > 6:
			walk_party(st, spec['loc'][:2], 2, pc)
		elif locked:
			if st.n >= st.next_use and not pc.is_performing():
				st.next_use = st.n + 100
				ui.select_party(i)
				log('OPEN LOCK %s attempts %s from %s' % (pc, name, location_to_axis(pc.location)))
				try:
					pc.action_perform(D20A_OPEN_LOCK, portal, 0)
				except RuntimeError as exc:
					if 'Target Invalid' not in str(exc):
						raise
					import debug
					x, y = spec['loc'][:2]
					tried = getattr(st, 'lock_positions', set())
					tried.add(location_to_axis(pc.location))
					st.lock_positions = tried
					spots = [(x+dx,y+dy) for dx in range(-2,3) for dy in range(-2,3)]
					spots.sort(key=lambda pt: (pt[0]-x)**2 + (pt[1]-y)**2)
					point = next((pt for pt in spots if pt not in tried and debug.pathto(pc,*pt)),None)
					if point:
						tried.add(point)
						pc.run_to(location_from_axis(*point))
		elif st.n >= st.next_use:
			st.next_use = st.n + 35
			ui.select_party(i)
			game.scroll_to(portal.location)
			ok, message = ui.verified_click(portal, 'use', log, fallback=None)
			if ok:
				log('USE %s from %s: %s' % (name, location_to_axis(pc.location), message))
		return False
	return False


_TOMB_CHAPEL = ((471,478), (461,475), (450,481), (444,485), (451,491), (462,496))
_TOMB_STAIRS = ((464,500), (455,500), (448,499), (446,504), (455,508), (462,511))


def follow_chapter_aisle(st, aisle):
	if not hasattr(st, 'aisle_index'):
		st.aisle_index, st.aisle_started = 0, st.n
	if st.aisle_index >= len(aisle):
		return True
	point = aisle[st.aisle_index]
	if walk_party(st, point, 2):
		st.aisle_index += 1
		st.aisle_started = st.n
	elif st.n - st.aisle_started > 600:
		fail('could not walk the aisle to %s' % (point,))
	return False


def recover_mausoleum_key(st):
	if side.has('keymaus'):
		return True
	st.require_click = True
	if get_current_map() == area_map('AR3502'):
		st.from_stairs = True
		walk_to_area(st, 'AR3501')
		return False
	if get_current_map() != area_map('AR3501'):
		return fail('the mausoleum key is on the first tomb level')
	aisle = tuple(reversed(_TOMB_STAIRS)) if getattr(st, 'from_stairs', False) else _TOMB_CHAPEL
	if not follow_chapter_aisle(st, aisle) or not use_chapter_portal(st, 'AR3501', 'AR3501Door4'):
		return False
	return side.container_item('AR3501', 'Sarcophagus', 'keymaus', require_click=True)(st)


def vale_conversation(st, ident, area, goal, until):
	if until():
		return True
	st.require_click = True
	if get_current_map() == area_map('AR3501'):
		# The stairs and the gate look close across the chapel walls. Follow the
		# open aisle around the chapel, in either direction, before clicking the exit.
		aisle = tuple(reversed(_TOMB_STAIRS)) + tuple(reversed(_TOMB_CHAPEL)) + (
			(482, 485), (487, 493), (495, 493), (503, 493), (511, 496), (519, 495))
		if area == 'AR3503':
			aisle = tuple(reversed(aisle))
		if not follow_chapter_aisle(st, aisle):
			return False
	return talk_step(st, ident, area, goal, until)


def confront_via_dialogue(st, ident, area, death_var):
	if V(death_var):
		return True
	if get_current_map() == area_map(area) and hasattr(st, 'sid'):
		target = find_obj(st.sid)
		if target and target.npc_flags_get() & ONF_KOS:
			# Once the dialogue makes the speaker hostile, the next interaction is an
			# attack even if combat ended when the last yeti fell.
			if time.time() >= getattr(st, 'next_attack', 0):
				st.next_attack = time.time() + 4
				pc = min((p for p in game.party if not p.is_unconscious()), key=target.distance_to)
				action = D20A_COUP_DE_GRACE if target.is_unconscious() else D20A_UNSPECIFIED_ATTACK
				log('COMBAT engaging hostile %s at %d HP' % (ident, target.stat_level_get(stat_hp_current)))
				pc.action_perform(action, target, 0)
			return False
	conversation = vale_conversation if GAME['g'] == 'iwd' else talk_step
	st.require_click = True
	return conversation(st, ident, area, r'A\.Enemy\(', lambda: V(death_var) > 0)


def open_west_mausoleum(st):
	# The western door is around the corner from the level-two entrance.
	if not follow_chapter_aisle(st, ((472, 499), (470, 489), (474, 479), (470, 469))):
		return False
	return use_chapter_portal(st, 'AR3502', 'AR3502Door4')


def reach_western_desk(st):
	if not follow_chapter_aisle(st, ((460, 473), (450, 477), (442, 479))):
		return False
	if not use_chapter_portal(st, 'AR3502', 'AR3502Door5'):
		return False
	return side.container_item('AR3502', 'Desk', 'keynrm', require_click=True)(st)


def open_inner_mausoleum(st):
	# Follow the eastern aisle with the PC who just opened its outer door.
	aisle = ((501, 488), (504, 498), (508, 504))
	if not hasattr(st, 'aisle_index'):
		start = location_from_axis(497, 483)
		walker = min((pc for pc in game.party if not pc.is_unconscious()), key=lambda pc: pc.distance_to(start))
		st.walk_leader = walker.id
	if not follow_chapter_aisle(st, aisle):
		return False
	return use_chapter_portal(st, 'AR3502', 'AR3502Door1')


def open_talisman_stairs(st):
	if get_current_map() != area_map('AR3502'):
		return fail('the talisman switch is on the second tomb level')
	# Leave the skeleton chamber through the two open eastern doors.
	if not follow_chapter_aisle(st, ((519, 501), (511, 504), (507, 496), (502, 488), (495, 481), (487, 474))):
		return False
	return use_chapter_portal(st, 'AR3502', 'AR3502Switch1')


def reach_kresselack(st):
	if get_current_map() != area_map('AR3503'):
		return enter_tomb_level(st, 'AR3503')
	if not follow_chapter_aisle(st, ((465, 501), (466, 493), (473, 485), (475, 477),
	                                (475, 469), (478, 461), (483, 457))):
		return False
	return use_chapter_portal(st, 'AR3503', 'AR3503Door2')


def enter_tomb_level(st, area):
	st.require_click = True
	if area == 'AR3502' and get_current_map() == area_map('AR3501'):
		# The stairs are across a wall. Follow the west aisle and double
		# back around the chapel before approaching the stairway door.
		aisle = _TOMB_STAIRS if side.has('keymaus') else _TOMB_CHAPEL + _TOMB_STAIRS
		if not follow_chapter_aisle(st, aisle):
			return False
	if area == 'AR3503' and get_current_map() == area_map('AR3502'):
		if not follow_chapter_aisle(st, ((479, 461), (480, 453), (486, 445))):
			return False
	if get_current_map() != area_map(area):
		return walk_to_area(st, area)
	if V(area + '_visited'):
		shot('kresselack_tomb_' + area.lower())
		log('PASS entered Kresselack\'s tomb on foot: ' + area)
		return 1
	st.tomb_arrival = getattr(st, 'tomb_arrival', st.n)
	return st.n - st.tomb_arrival > 150 and fail('the tomb arrival script did not register')


def clear_ford_keg(st, dest):
	"""When the trail is blocked, break a nearby ordinary keg with a party weapon."""
	import ie_bake_i2ar2000 as ford
	party = [pc for pc in game.party if not pc.is_unconscious()]
	if not party:
		return False
	if getattr(st, 'keg_destination', None) != dest:
		st.keg_destination = dest
		st.ford_best, st.ford_retry_at, st.ford_keg = 999, 0, None
	x, y = dest
	def remaining(obj):
		px, py = location_to_axis(obj.location)
		return max(abs(px-x), abs(py-y))
	distance = min(remaining(pc) for pc in party)
	now = time.time()
	if distance <= st.ford_best - 2:
		st.ford_best, st.ford_retry_at = distance, now + 8
	if now < st.ford_retry_at:
		return False
	st.ford_retry_at = now + 8
	candidates = []
	for guid, entry in ford.OBJS.items():
		if entry.get('spec', {}).get('resref') not in ('20keg1', '20keg2', '20keg3'):
			continue
		keg = game.get_obj_by_id(guid)
		if not keg or keg.is_unconscious() or keg.object_flags_get() & (OF_OFF | OF_DONTDRAW):
			continue
		if remaining(keg) >= distance:
			continue
		for pc in party:
			if pc.distance_to(keg) <= 15 and pc.has_los(keg) and not pc.is_performing():
				candidates.append((pc.distance_to(keg), pc, keg))
	if not candidates:
		return False
	_, pc, keg = min(candidates, key=lambda c: c[0])
	st.ford_keg = keg.id
	# A prop can leave initiative after a single swing. Keep trying it while
	# the party is stalled. Walking two tiles earns a new full progress window.
	st.ford_retry_at = now + 3
	try:
		pc.action_perform(D20A_UNSPECIFIED_ATTACK, keg, 0)
	except RuntimeError as exc:
		if 'Target Invalid' not in str(exc):
			raise
		st.ford_keg = None
		return False
	log('FORD %s attacks the obstructing keg at %s (%d HP)' % (pc, location_to_axis(keg.location),
	    keg.stat_level_get(stat_hp_current)))
	return True


def help_dereth(st):
	"""Clear the two orc camps and ask Dereth to open the trail to the far bank."""
	import ie_bake_i2ar2000 as ford
	import ie_runtime as rt
	for team, flag in (('T3_', 'SR_Dereth_Freed'), ('T4_', 'SR_Cleared_House')):
		if V(flag) >= 2:
			continue
		if getattr(st, 'ford_team', None) != team:
			st.ford_team, st.team_start, st.team_retry = team, st.n, 0
			st.camp_guids = [guid for guid, entry in ford.OBJS.items()
			                 if entry.get('spec', {}).get('actor', '').startswith(team)
			                 and entry['spec'].get('family') != 'keg' and rt.area_spawn_allowed(entry['spec'])]
			log('FORD clearing %s for Dereth (%d placements)' % (team.rstrip('_'), len(st.camp_guids)))
		if st.n - st.team_start > 1000:
			return fail('Dereth camp %s did not advance %s (value %d)' % (team, flag, V(flag)))
		if st.n < st.team_retry:
			return 0
		st.team_retry = st.n + 6
		leader = next(pc for pc in game.party if not pc.is_unconscious())
		enemies = [game.get_obj_by_id(guid) for guid in st.camp_guids]
		enemies = [o for o in enemies if o and not o.is_unconscious() and not o.object_flags_get() & OF_OFF]
		if enemies:
			target = min(enemies, key=leader.distance_to)
			if targos_enemy(target) and leader.distance_to(target) <= 6 and not leader.is_performing():
				leader.action_perform(D20A_UNSPECIFIED_ATTACK, target, 0)
			else:
				walk_party(st, location_to_axis(target.location), 2)
		return 0
	if not hasattr(st, 'dereth'):
		st.dereth = Step('dereth')
	st.dereth.n = st.n
	return talk_step(st.dereth, '20dereth', 'I2AR2000', r'StartCutScene\(c, "20cPath1"',
	                 lambda: bool(V('SR_Reveal_Path_1')))


def release_ford_log(st, name):
	# These are two original unlocked portals, one on each bank. When both
	# are open the Ford area script removes the obstruction between them.
	import ie_doors
	for spec, portal, last in ie_doors._doors:
		if spec['name'] != 'AR2000_Door2_' + name:
			continue
		if ie_doors._is_open(portal):
			return True
		if getattr(st, 'log_target', None) != name:
			st.log_target, st.log_started = name, st.n
		if st.n - st.log_started > 700:
			return fail('could not reach the Ford log ' + name)
		pc = min((p for p in game.party if not p.is_unconscious()), key=lambda p: p.distance_to(portal))
		if pc.distance_to(portal) <= 7:
			portal.portal_toggle_open()
			log('FORD released ' + name)
		else:
			walk_party(st, spec['toggle_tile'], 2)
		return False
	return fail('missing Ford log ' + name)


def shaengarne_bridge(st):
	st.require_click = True
	if get_current_map() == area_map('I2AR2000'):
		import ie_travel_data as data
		# Torak lowers the bridge after his fourth encounter at the Ford.
		# Enter the original floor triggers and let his dialogue advance the quest.
		call = max(2, V('SR_Torak_Talk') + 1)
		if call == 3 and not V('SR_Reveal_Path_1'):
			help_dereth(st)
			return 0
		if call == 3 and not release_ford_log(st, 'RightLog'):
			return 0
		if call == 3 and not V('SR_Reveal_Path_2'):
			# The near bank faces the blocked logjam. Dereth opens the trail
			# by the first camp, which loops around to the opposite bank.
			trail = ((531,507), (537,501), (541,496), (540,490), (544,478), (536,466))
			if not hasattr(st, 'ford_trail'):
				# A recovery save may already be on the narrow far-bank trail.
				x, y = location_to_axis(game.leader.location)
				st.ford_trail = max([0] + [i for i, (tx,ty) in enumerate(trail)
				                          if max(abs(x-tx), abs(y-ty)) <= 6])
			index = st.ford_trail
			if index < len(trail):
				if getattr(st, 'trail_target', None) != index:
					st.trail_target, st.trail_start = index, st.n
					log('FORD following Dereth\'s open trail to %s' % (trail[index],))
				if st.n - st.trail_start > 1000:
					return fail('could not walk through Dereth\'s trail at %s' % (trail[index],))
				if not clear_ford_keg(st, trail[index]) and walk_party(st, trail[index], 2):
					st.ford_trail = index + 1
				return 0
		if call == 4 and not release_ford_log(st, 'LeftLog'):
			return 0
		if call <= 4:
			name = 'Torak_Call_%d' % call
			if getattr(st, 'ford_call', None) != call:
				region = next((r for r in data.AREAS['I2AR2000']['triggers'] if r['name'] == name), None)
				if region is None:
					return fail('missing Ford encounter ' + name)
				st.ford_call, st.ford_start = call, st.n
				st.ford_at = tuple(int(round(v)) for v in E.region_center(region))
				log('FORD approaching %s at %s' % (name, st.ford_at))
			if st.n - st.ford_start > 1200:
				return fail('could not complete %s at the Ford (SR_Torak_Talk %d)' % (name, V('SR_Torak_Talk')))
			if not clear_ford_keg(st, st.ford_at):
				walk_party(st, st.ford_at, 1)
			return 0
	if get_current_map() == area_map('I2AR2001'):
		if not getattr(st, 'sneak_open', False):
			st.sneak_open = use_chapter_portal(st, 'I2AR2001', 'AR2001_Door1_RealSneak')
			return 0
		if not side.has('22keyhg1'):
			if not hasattr(st, 'torak_hunt'):
				st.torak_hunt = Step('torak_hunt')
			st.torak_hunt.n = st.n
			side.encounter('I2AR2001', '20orcwar_29', (2804, 1130), lambda: side.has('22keyhg1'), loot='22keyhg1')(st.torak_hunt)
			return 0
		if not use_chapter_portal(st, 'I2AR2001', 'AR2001_Door2'):
			return 0
	st.ford_keg = None
	if get_current_map() == area_map('I2AR2101') and V('Destroy_Dam_Quest') != 4:
		if not getattr(st, 'dam_support_open', False):
			st.dam_support_open = use_chapter_portal(st, 'I2AR2101', 'AR2101_Door2_Support1')
			return 0
		if not use_chapter_portal(st, 'I2AR2101', 'AR2101_Door1_Bridge'):
			return 0
		if not hasattr(st, 'dam_opened'):
			st.dam_opened = st.n
		if st.n - st.dam_opened > 300:
			return fail('the dam cutscene did not finish after the bridge opened')
		return 0
	if get_current_map() != area_map('I2AR2102'):
		return walk_to_area(st, 'I2AR2102')
	return step_fight(st, 'AR2102', 'Shaengarne_Bridge_Cleared')


def report_bridge(st):
	if V('Fortress_Quest') >= 1:
		return True
	st.require_click = True
	# The short line from the mill gate to the Ford crosses a building.
	# Walk the south lane, which reconnects with the exit road at its east end.
	if get_current_map() == area_map('I2AR2001'):
		if not follow_chapter_aisle(st, ((478, 443), (481, 451), (478, 459), (478, 467),
		                                (475, 475), (469, 482), (473, 490), (480, 495),
		                                (496, 496), (512, 488), (528, 489), (544, 485))):
			return False
	return talk_step(st, '11ulbrec', 'I2AR1101', r'"Fortress_Quest", "GLOBAL", 1\)', lambda: V('Fortress_Quest') >= 1)


def meet_fortress_scout(st):
	st.require_click = True
	return talk_step(st, '30enneli', 'I2AR3000', r'"30Enneli_BQuest", "GLOBAL", 1\)', lambda: V('30Enneli_BQuest') >= 1)


def enter_chapter_map(st, area):
	st.require_click = True
	if get_current_map() != area_map(area):
		return walk_to_area(st, area)
	shot(('fortress_' if area.startswith('I2') else 'temple_') + area.lower())
	return True


def escort_braston(st, area, point, stage):
	import ie_runtime as rt
	if V('31brasto_Dead'):
		return fail('Braston died during the escort')
	if V('30brasto_escape') >= stage:
		return True
	st.require_click = True
	if area == 'I2AR3000' and get_current_map() == area_map('I2AR3100') and not V('AR3000_Door1_MainGate'):
		# Opening the courtyard gate from within also unlocks its exterior half.
		use_chapter_portal(st, 'I2AR3100', 'AR3100_Door4_OuterGate')
		return False
	if get_current_map() != area_map(area):
		return walk_to_area(st, area)
	goal = rt.ie_to_tile(area[-6:], *point)
	ctx = rt.ctx_for(game.leader, area=area[-6:])
	escort = rt.N(ctx, 'Braston')
	if st.n % 100 == 1:
		log('ESCORT stage %d paused %d, Braston %s, party %s' % (V('30brasto_escape'), V('BRASTON_PAUSED_STATE'),
		    location_to_axis(escort.location) if escort else None, [location_to_axis(p.location) for p in game.party]))
	if area == 'I2AR3101':
		# Leave the cells by the west passage and turn east at Guthma's hall.
		aisle = ((495,506),(487,503),(485,495),(488,487),(490,479),(492,471),(500,470),(508,472),(516,472))
		index = getattr(st, 'escort_waypoint', 0)
		if index >= 7 and not getattr(st, 'escort_gate_open', False):
			st.escort_gate_open = use_chapter_portal(st, area, 'AR3101_Door2')
			if not st.escort_gate_open:
				return False
		if index < len(aisle):
			goal = aisle[index]
			if escort and escort.distance_to(location_from_axis(*goal)) <= 22:
				st.escort_waypoint = index + 1
	# Move the PC he is following. A straggler in the next room can be
	# farther from a waypoint even though they are already closer to the exit.
	party = [pc for pc in game.party if not pc.is_unconscious()]
	walker = min(party, key=escort.distance_to) if escort else party[0]
	walk_party(st, goal, 2, walker)
	return False


def investigate_altar(st):
	if V('Heartstone_Stolen'):
		return True
	import debug, ie_travel, ie_travel_data
	triggers = ie_travel_data.AREAS['AR3603'].get('triggers', [])
	for trigger in triggers:
		if trigger.get('module') == 'ie_bcs_caratrg3_area':
			# The altar region wraps around the dais. Its mean vertex can lie outside it.
			poly = trigger['poly']
			if not getattr(st, 'altar_tile', None):
				xs, ys = zip(*poly)
				px, py = location_to_axis(game.leader.location)
				tiles = [(x, y) for x in range(int(min(xs)), int(max(xs))+1)
				         for y in range(int(min(ys)), int(max(ys))+1)
				         if all(ie_travel.near_region(x+dx, y+dy, poly, 0) for dx, dy in ((0,0),(0,1),(1,0),(1,1)))]
				tiles.sort(key=lambda p: (p[0]-px)**2 + (p[1]-py)**2)
				st.altar_tile = next((p for p in tiles if debug.pathto(game.leader, *p)), None)
			if st.altar_tile:
				walk_party(st, st.altar_tile, 0, game.leader)
			return False
	return fail('missing Heartstone quest trigger in AR3603')


def warren_gate_access():
	if side.has('30keydgu') or V('AR3001_Door_Unlocked'):
		return True
	import ie_doors
	return any(spec['name'] == 'AR3001_Door3' and not portal.portal_flags_get() & OPF_LOCKED
	           for spec, portal, last in ie_doors._doors)


def open_spider_den(st):
	if warren_gate_access() or V('30hobDGu_Pass') or side.has('30wspidr'):
		return True
	# Approach the near side from Pondmuk. Targeting the spider across the
	# closed door sends the party on a long detour through the guarded passage.
	aisle = ((491, 482), (499, 481), (507, 479), (509, 471), (505, 463), (499, 457))
	return follow_chapter_aisle(st, aisle) and use_chapter_portal(st, 'I2AR3001', 'AR3001_Door1')


def answer_warren_guard(st):
	if not hasattr(st, 'sid') and V('30hobDGu_Pass') == 1:
		# Clicking the watched door starts the guard's conversation.
		st.sid, src = npc_script('30hobca', 'AR3001')
		npc, replies, st.goals = dlg_graph(st.sid, src, r'"AR3001_Door_Unlocked", "GLOBAL", 1')
		st.dist = E.dist_to_goal(npc, replies, st.goals)
		st.exit_dist = E.dist_to_goal(npc, replies, set(r for r in replies if replies[r] <= 0))
		prepare_dialogue(st)
	return use_chapter_portal(st, 'I2AR3001', 'AR3001_Door3')


def gs_ch1(slot):
	if ST.get('restarting') or not len(game.party):
		return 0
	if ST['steps'] is None:
		steps = STEPS2 if GAME['g'] == 'iwd2' else STEPS
		if os.environ.get('IWDAP_NEXT_REGION') == '1':
			steps = list(steps) + [('next_region', next_region)]
			if GAME['g'] == 'iwd':
				steps.append(('arundel', quest_talk('arundel', 'AR2112', 'Vale_Quest', 1)))
				steps.append(('vale', enter_vale))
				steps.append(('gate_key', side.container_item('AR3101', 'Statue', 'keygate', require_click=True)))
				steps.append(('sanctum_key', side.container_item('AR3301', 'Sarcophagus', 'keysanc', require_click=True)))
				steps.append(('tomb', lambda st: enter_tomb_level(st, 'AR3501')))
				steps.append(('tomb_gate', lambda st: use_chapter_portal(st, 'AR3501', 'AR3501Door1')))
				steps.append(('tomb_sanctum', lambda st: use_chapter_portal(st, 'AR3501', 'AR3501Door6')))
				steps.append(('tomb_priest_key', side.container_item('AR3501', 'Sarcophagus', 'keyprst', require_click=True)))
				steps.append(('tomb_priest_gate', lambda st: use_chapter_portal(st, 'AR3501', 'AR3501Door2')))
				steps.append(('tomb_symbol', side.container_item('AR3501', 'Sarcophagus', 'holysym', require_click=True)))
				steps.append(('tomb_symbol_gate', lambda st: use_chapter_portal(st, 'AR3501', 'AR3501Door5')))
				steps.append(('tomb_mausoleum_key', recover_mausoleum_key))
				steps.append(('tomb_descent', lambda st: enter_tomb_level(st, 'AR3502')))
				steps.append(('tomb_foyer', lambda st: use_chapter_portal(st, 'AR3502', 'AR3502Door3')))
				steps.append(('tomb_west_gate', open_west_mausoleum))
				steps.append(('tomb_room_key', reach_western_desk))
				steps.append(('tomb_east_gate', lambda st: use_chapter_portal(st, 'AR3502', 'AR3502Door2')))
				steps.append(('tomb_inner_gate', open_inner_mausoleum))
				steps.append(('tomb_talisman', side.container_item('AR3502', 'Skeleton', 'bwtalis', require_click=True)))
				steps.append(('tomb_switch', open_talisman_stairs))
				steps.append(('tomb_third_level', lambda st: enter_tomb_level(st, 'AR3503')))
				steps.append(('tomb_crypt', reach_kresselack))
				steps.append(('kresselack', quest_talk('kress', 'AR3503', 'Kress_Quest', 3)))
				steps.append(('lysan', lambda st: confront_via_dialogue(st, 'lysan', 'AR3001', 'SPRITE_IS_DEADLysan')))
				steps.append(('kresselack_report', lambda st: vale_conversation(st, 'kress', 'AR3503', r'"Kress_Quest", "GLOBAL", 4', lambda: V('Kress_Quest') >= 4)))
				steps.append(('vale_report', lambda st: vale_conversation(st, 'arundel', 'AR2112', r'"Temple_Quest", "GLOBAL", 1', lambda: V('Temple_Quest') >= 1)))
				import ie_travel_data
				if 'AR3603' in ie_travel_data.AREAS:
					for goal, area in (('temple_approach', 'AR3600'), ('temple_hall', 'AR3601'),
					                   ('temple_lower', 'AR3602')):
						steps.append((goal, lambda st, dest=area: enter_chapter_map(st, dest)))
					steps.append(('temple_altar_door', lambda st: use_chapter_portal(st, 'AR3602', 'AR3602Door1')))
					steps.append(('temple_altar', lambda st: enter_chapter_map(st, 'AR3603')))
					steps.append(('heartstone', investigate_altar))
					steps.append(('temple_report', lambda st: vale_conversation(st, 'arundel', 'AR2112',
					              r'"Deye_Quest", "GLOBAL", 1', lambda: V('Deye_Quest') >= 1)))
					if 'AR4000' in ie_travel_data.AREAS:
						steps.append(('dragons_eye', lambda st: enter_chapter_map(st, 'AR4000')
						              and V('Chapter') >= 2))
			else:
				steps.append(('bridge', shaengarne_bridge))
				steps.append(('bridge_report', report_bridge))
				import ie_travel_data
				if 'I2AR3000' in ie_travel_data.AREAS:
					steps.append(('fortress_scout', meet_fortress_scout))
				if 'I2AR3101' in ie_travel_data.AREAS:
					steps.append(('warren_key', side.encounter('I2AR3000', '30orctru', (3368, 822),
					                                            lambda: side.has('30keywar'), loot='30keywar')))
					steps.append(('warren_gate', lambda st: use_chapter_portal(st, 'I2AR3000', 'AR3000_Door2_SideGate')))
					steps.append(('warrens', lambda st: enter_chapter_map(st, 'I2AR3001')))
					if npc_script('30hobdgu', 'AR3001')[0] is not None:
						steps.append(('pondmuk', lambda st: warren_gate_access() or V('30hobDGu_Pass') or
						              talk_step(st, '30gobpon', 'I2AR3001', r'"30gobPon_Spid", "GLOBAL", 1',
						                        lambda: V('30gobPon_Spid') >= 1)))
						steps.append(('spider_den', open_spider_den))
						steps.append(('warren_spider', side.encounter('I2AR3001', '30spiwo', (969, 1247),
						              lambda: warren_gate_access() or V('30hobDGu_Pass') or side.has('30wspidr'), loot='30wspidr')))
						steps.append(('warren_password', lambda st: warren_gate_access() or
						              talk_step(st, '30gobpon', 'I2AR3001', r'"30hobDGu_Pass", "GLOBAL", 1',
						                        lambda: V('30hobDGu_Pass') >= 1)))
						steps.append(('warren_inner_gate', answer_warren_guard))
					steps.append(('deep_warrens', lambda st: enter_chapter_map(st, 'I2AR3002')))
					for goal, owner, point, stone in (
					        ('taskmaster_stone', '30orotas', (700, 2297), '30bstone'),
					        ('gumph_stone', '30hobgum', (2285, 1148), '30istone')):
						steps.append((goal, side.encounter('I2AR3002', owner, point,
						              lambda item=stone: side.has(item), loot=stone)))
					steps.append(('fortress_courtyard', lambda st: enter_chapter_map(st, 'I2AR3100')))
					steps.append(('fortress_ward', lambda st: use_chapter_portal(st, 'I2AR3100', 'AR3100_Door2_InnerDoor')))
					steps.append(('fortress_keep', lambda st: enter_chapter_map(st, 'I2AR3101')))
					steps.append(('keep_key', side.encounter('I2AR3101', '31orcold', (356, 1360),
					              lambda: side.has('31key01'), loot='31key01')))
					steps.append(('keep_inner_door', lambda st: use_chapter_portal(st, 'I2AR3101', 'AR3101_Door2')))
					steps.append(('defeat_guthma', lambda st: confront_via_dialogue(st, '31buggut', 'I2AR3101', '31BugGut_Dead')))
					steps.append(('braston_cell', lambda st: use_chapter_portal(st, 'I2AR3101', 'AR3101_Door9', pick_lock=True)))
					steps.append(('free_braston', quest_talk('31brasto', 'I2AR3101', '30brasto_escape', 1)))
					for goal, area, point, stage in (
						('escort_keep', 'I2AR3101', (338,1384), 2),
						('escort_courtyard', 'I2AR3100', (730,1786), 3),
						('escort_approach', 'I2AR3000', (652,2850), 4)):
						steps.append((goal, lambda st, a=area, p=point, s=stage: escort_braston(st, a, p, s)))
					steps.append(('braston_reunion', lambda st: talk_step(st, '30enneli', 'I2AR3000',
					              r'A\.AddXPVar.*Braston_Ennelia_Leave', lambda: V('Braston_Ennelia_Leave') == 1)))
					steps.append(('fortress_report', quest_talk('11ulbrec', 'I2AR1101', 'Fortress_Quest', 2)))
					if 'I2AR4001' in ie_travel_data.AREAS:
						steps.append(('oswald_flight', lambda st: talk_step(st, '11oswald', 'I2AR1100',
						              r'A\.StartCutScene\(c, "O_4001a"', lambda: V('RJ_AR4001') == 1)))
						steps.append(('airship_arrival', lambda st: get_current_map() == area_map('I2AR4001') and V('Chapter') >= 2))
		ST['steps'] = [Step(k, fn=f) for k, f in steps]
		fr = os.environ.get('IWDAP_CH1_FROM')     # resume from a save made on the way (e.g. depart)
		if fr:
			ST['i'] = [k for k, f in steps].index(fr)
			if os.environ.get('TP_AUTOLOAD') == 'IEAP_Chapter_' + GAME['g']:
				ST['checkpoint'] = (ST['i'], get_current_map())
			log('RESUME at step %s (map %d)' % (fr, get_current_map()))
		try:
			import ie_travel; ie_travel.start()
		except Exception as e:
			log('travel start: %s' % e)
	if ST['i'] >= len(ST['steps']) or ST['fail']:
		if not ST.get('done'):
			ST['done'] = 1
			if ST['fail']:
				log('SUMMARY CH1 FAIL at step %s: %s' % (ST['steps'][min(ST['i'], len(ST['steps']) - 1)].kind, ST['fail']))
			fallen = [str(pc) for pc in game.party if pc.stat_level_get(stat_hp_current) <= -10]
			if fallen:
				log('PARTY casualties at finish: ' + ', '.join(fallen))
			log('DONE')
		return 0
	st = ST['steps'][ST['i']]
	ST.pop('walking_to', None)
	now = time.time()
	if now - ST.get('last_chapter_tick', now) > 2:
		# Dialogue, movies, loading and a focus pause suspend this callback.
		st.combat_progress = None
		approach = getattr(st, 'part', st)
		approach.approach_progress = approach.search_progress = now
	ST['last_chapter_tick'] = now
	in_combat = game.combat_is_active()
	assist_party(in_combat)
	if game.char_ui_display_type == 1:  # A queued interaction with a slain target can open its inventory.
		if not ST.get('closing_loot'):
			log('LOOT closing inventory on map %d before continuing %s' % (get_current_map(), st.kind))
		ST['closing_loot'] = True
		game.char_ui_hide()
		return 0
	ST.pop('closing_loot', None)
	# A barter reply ends dialogue but leaves the merchant and party inventories open.
	# Finish that interaction before a quest step can unload the merchant's map.
	if game.char_ui_display_type == 2:  # UiCharDisplayType::Bartering
		part = getattr(st, 'part', None)
		if part and getattr(part, 'service', None) and side.shop_service(part):
			return 0
		ticks = ST.get('barter_ticks', 0)
		if ticks == 0:
			log('BARTER closing shop on map %d before continuing %s' % (get_current_map(), st.kind))
			game.char_ui_hide()
		elif ticks >= 50:
			return fail('barter screen stayed open on map %d' % get_current_map())
		ST['barter_ticks'] = ticks + 1
		return 0
	if ST.pop('barter_ticks', 0):
		log('BARTER confirmed closed on map %d' % get_current_map())
	# Scripted scenes can chain across several seconds. Leaving early invalidates
	# actors still speaking on the old map (Shawford's palisade briefing).
	import ie_cutscene
	if ie_cutscene.active():
		st.combat_progress = None
		if 'scene_started' not in ST:
			ST['scene_started'] = time.time()
			log('SCENE watching the scripted scene on map %d' % get_current_map())
		return 0
	if ST.get('scene_started') is not None:
		log('SCENE finished after %.1f seconds' % (time.time() - ST.pop('scene_started')))
	if dlg.is_engaged():
		return 0
	TALK.pop('line', None)
	TALK.pop('incidental_visits', None)
	chapter_camera.follow()
	hp = [pc.stat_level_get(stat_hp_current) for pc in game.party]
	fallen = tuple(pc.id for pc, health in zip(game.party, hp) if health <= -10)
	if fallen != ST.get('fallen', ()):
		ST['fallen'] = fallen
		if fallen:
			log('PARTY casualty during %s, HP %s' % (st.kind, hp))
	if all(pc.is_unconscious() for pc in game.party) and max(hp) <= 0:
		if retry_battle(st):
			return 0
		return fail('party could not recover during %s, HP %s' % (st.kind,hp))
	if in_combat:
		import tpactions
		if (not getattr(st, 'combat_ticks', 0) and GAME['g'] == 'iwd' and st.kind == 'gaspar'
		    and not ST.get('cave_entrance_recovered') and get_current_map() == area_map('AR1201')):
			import ie_travel_data
			x,y = ie_travel_data.AREAS['AR1201']['entrances']['FR1200'][:2]
			party_tiles = [location_to_axis(pc.location) for pc in game.party if not pc.is_unconscious()]
			if party_tiles:
				rear = min(party_tiles, key=lambda p: (p[0]-x)**2 + (p[1]-y)**2)
				if (rear[0]-x)**2 + (rear[1]-y)**2 <= 14**2:
					st.cave_rally_point = rear
		if hasattr(st,'looting'):
			del st.looting
		actor = tpactions.get_current_tb_actor()
		has_actor = actor and actor != OBJ_HANDLE_NULL
		turn = (game.combat_turn, actor.id if has_actor else None)
		st.combat_ticks = getattr(st, 'combat_ticks', 0) + 1
		now = time.time()
		if getattr(st, 'last_turn', None) != turn:
			st.last_turn, st.turn_start = turn, st.combat_ticks
			st.next_combat_action = 0
			if has_actor and actor.type == obj_t_npc and targos_enemy(actor):
				# A battle between guards and raiders can enter initiative
				# before the party can see a target from its own position.
				slot.get_scheme_state()['battle_front'] = actor.map, location_to_axis(actor.location)
		witnesses = list(game.party)
		if has_actor:
			witnesses += list(game.obj_list_vicinity(actor.location, OLC_CRITTERS))
		progress = (turn, bool(has_actor and actor.is_performing()),
		            tuple((pc.id, pc.location, pc.stat_level_get(stat_hp_current)) for pc in witnesses),
		            tpactions.get_cur_seq().tb_status.hourglass_state if has_actor else None)
		if getattr(st, 'combat_progress', None) != progress:
			st.combat_progress, st.combat_progress_at = progress, now
			st.unstuck, st.ended_idle_turn, st.idle_logged = False, False, False
		idle = now - st.combat_progress_at
		if idle >= 8 and not st.idle_logged:
			st.idle_logged = True
			import autoui
			windows = [str(autoui.TWidget(w)) for w in autoui.get_active_windows()]
			log('COMBAT waiting on round %d actor %s performing %s, open windows %s' %
			    (game.combat_turn, actor, actor.is_performing() if actor and actor != OBJ_HANDLE_NULL else None, windows))
		ST.pop('camp', None)
		if idle >= 12 and has_actor and actor.is_performing() and not st.unstuck:
			st.unstuck = True
			log('COMBAT cancelling an action after 12 seconds without progress for %s' % actor)
			actor.anim_goal_interrupt()
			return 0
		if idle >= 18 and has_actor and actor in game.party and not actor.is_performing() and not st.ended_idle_turn:
			from controller_ui_util import press_space
			st.ended_idle_turn = True
			log('COMBAT ending inactive turn for %s' % actor)
			press_space()
		if idle >= 30:
			if not retry_battle(st):
				fail('combat stalled during ' + st.kind)
		elif now >= getattr(st, 'next_combat_action', 0):
			from new_game_controller import combat_action_handler
			delay = combat_action_handler(slot, target_filter=targos_enemy, chapter_log=log,
			                             practice=ST.get('practice'), pursue_raiders=st.kind == 'palisade',
			                             obstruction=game.get_obj_by_id(st.ford_keg) if getattr(st, 'ford_keg', None) else None)
			st.next_combat_action = time.time() + max(150, delay) / 1000.0
		return 0
	import chapter_levelup
	if chapter_levelup.tick(st):
		return 0
	if getattr(st, 'combat_ticks', 0):
		log('COMBAT ended on map %d, party HP %s' % (get_current_map(), [pc.stat_level_get(stat_hp_current) for pc in game.party]))
		slot.get_scheme_state().pop('battle_front', None)
		ST['after_battle'] = True
		if hasattr(st, 'cave_rally_point'):
			ST['cave_regroup'] = {'point': st.cave_rally_point, 'start': time.time()}
			log('REGROUP gathering at the cave entrance near %s' % (st.cave_rally_point,))
			del st.cave_rally_point
		ST.pop('last_camp',None)
	st.combat_ticks = 0
	st.last_turn = None
	if ST.get('cave_regroup') and regroup_at_cave_entrance(st):
		return 0
	if ST.get('after_battle') and st.kind in ('docks','vellum','phaen','damien','gaspar'):
		drops = {'AR1000': ('goblinbowelitequ','fish'), 'AR1201': ('ogre','contract'), 'I2AR1007': ('10rukwu','10vellum')}
		area = area_of(get_current_map())
		if area in drops:
			ident,res = drops[area]
			if not hasattr(st,'looting'):
				st.looting = Step('loot')
			loot = st.looting
			loot.n += 1
			if loot.n <= 150 and not side.has(res) and (loot.n == 1 or getattr(loot,'found',False)):
				if loot.n % 10 == 1:
					loot.found = side.recover_drop(loot,area,ident,res)
				if loot.found and not side.has(res):
					return 0
	if st.kind != 'newgame' and recover_after_battle(st):
		return 0
	checkpoint_party(st, ST.pop('after_battle', False))
	st.n += 1
	if st.n == 1 or st.n % 100 == 0:
		log('STEP %s n=%d map %d dlg %d %s' % (st.kind, st.n, get_current_map(), dlg.is_engaged(),
			' '.join('%s %d' % (v, V(v)) for v in STATUS[GAME['g']])))
	try:
		done = st.fn(st)
	except Exception as e:
		import traceback; done = fail('step %s raised %s %s' % (st.kind, e, traceback.format_exc()))
	if getattr(st, 'sidequest', False) and ST['fail']:
		ST.pop('practice', None)
		log('SIDEQUEST FAIL %s: %s' % (st.kind, ST['fail']))
		ST['fail'] = None
		TALK['cur'] = None
		ST['i'] += 1
		return 0
	if done and not ST['fail']:
		if st.kind in ('bridge_report', 'fortress_scout', 'warren_key', 'warren_gate', 'warrens', 'pondmuk', 'warren_spider', 'warren_password',
			               'warren_inner_gate', 'deep_warrens', 'taskmaster_stone', 'gumph_stone',
				               'fortress_courtyard', 'fortress_ward', 'fortress_keep', 'keep_key', 'keep_inner_door', 'defeat_guthma', 'free_braston',
			               'escort_keep', 'escort_courtyard', 'escort_approach', 'braston_reunion', 'fortress_report', 'airship_arrival',
		               'kresselack', 'lysan', 'kresselack_report', 'vale_report', 'temple_approach', 'temple_hall',
			               'temple_lower', 'temple_altar', 'heartstone', 'temple_report', 'dragons_eye'):
			if game.savegame('IEAP_Chapter_' + GAME['g'], 'Chapter autoplayer recovery'):
				log('CHECKPOINT after %s on map %d' % (st.kind, get_current_map()))
		if st.kind == 'depart':
			ST['departed'] = 1
		log('STEP %s done' % st.kind); ST['i'] += 1
	return 0

def gs_quit_to_menu(slot):
	'''in game (the harness save): open the in-game menu once; the next stage presses Quit'''
	if gs_is_main_menu(slot):
		return 1
	if len(game.party) and not slot.state:
		slot.state = {'k': 1}; key('Escape')
	return 1 if slot.state else 0

def pick_targos_role(role, preferred=None, party_log=log, on_missing=fail):
	import controller_ui_util as ui
	from controller_callbacks_common import gs_wait_cb
	def find(slot):
		if ST['fail']:
			return 1
		state = slot.get_scheme_state()
		rows = [(key, ui.obtain_widget(key)) for key in WID_IDEN.CHAR_POOL_CHARS]
		rows = [(key, w) for key, w in rows if w is not None]
		if not rows:
			return 0
		page = []
		for key, widget in rows:
			label = widget.rendered_text or ''
			page.append(label)
			if preferred and not state.get('fallback') and not label.lower().startswith(preferred.lower()):
				continue
			if widget.is_button_enabled and role in [line.strip().lower() for line in label.splitlines()] and 'not in party' in label.lower():
				state['widget_scan'] = {'wid_id': key}
				party_log('PARTY selecting %s: %s' % (role, ' '.join(label.split())))
				return 1
		if state.get('page') == page:
			if state.get('back'):
				if not preferred or state.get('fallback'):
					on_missing('no compatible %s in the party pool' % role)
					return 1
				state['fallback'], state['back'], state['page'] = True, False, None
				return 0
			state['back'] = True
		state['page'] = page
		ui.move_mouse_to_widget(rows[len(rows)//2][1])
		game.mouse_scroll(1 if state.get('back') else -1)
		return 0
	cs = ControlScheme()
	cs.__set_stages__([
		GoalStateStart(find, ('found', 100), ('start', 300)),
		GoalState('found', lambda slot: not ST['fail'], ('select', 150), ('end', 100)),
		GoalState('select', gs_press_widget, ('add', 200), ('select', 150), {'param1': None}),
		GoalState('add', gs_press_widget, ('end', 300), ('add', 150), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN}),
		GoalState('end', gs_wait_cb, ('end', 0))])
	return cs

def setup_playtester(autoplayer, which='iwd'):
	GAME['g'] = which
	E.configure('targos' if which == 'iwd2' else 'easthaven')
	cs = ControlScheme()
	party = [('fighter',None), ('barbarian',None), ('rogue',None), ('cleric',None), ('wizard',None)]
	alignment = WID_IDEN.TRUE_NEUTRAL_BTN_WID_ID
	if which == 'iwd2':
		# Armoured fighters take the front. Individual dialogue goals choose their own speaker.
		party = [('fighter','Ranould'), ('fighter','Regdar'), ('cleric','Brunhilda'), ('rogue','Lidda'), ('wizard','Karrin')]
		alignment = WID_IDEN.TRUE_NEUTRAL_BTN_WID_ID[:-1] + [1]
	add = [GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'pick_%d_%s' % (i, role),
	       'param2': (pick_targos_role, (role, preferred))}) for i, (role, preferred) in enumerate(party)]
	ch1 = [GoalState('ch1', gs_ch1, ('ch1', 100), ('ch1', 100))]
	if os.environ.get('IWDAP_CH1_FROM'):
		cs.__set_stages__([GoalStateStart(gs_ch1, ('ch1', 100), ('ch1', 100))] + ch1)
	else:
		startup = [GoalStateStart(gs_is_main_menu, ('new_game', 1000), ('start', 500))]
		if os.environ.get('TP_AUTOLOAD'):
			startup = [
				GoalStateStart(gs_quit_to_menu, ('press_quit', 1500), ('start', 500)),
				GoalState('press_quit', gs_press_widget, ('menu', 3000), (), {'param1': INGAME_QUIT}),
				GoalState('menu', gs_is_main_menu, ('new_game', 1000), ('menu', 500)),
			]
		cs.__set_stages__(startup + [
		GoalState('new_game', gs_press_widget, ('normaldiff', 800), (), {'param1': WID_IDEN.NEW_GAME}),
		GoalState('normaldiff', gs_press_widget, ('align', 800), (), {'param1': WID_IDEN.NORMAL_DIFF}),
		GoalState('align', gs_press_widget, ('align_ok', 800), (), {'param1': alignment}),
		GoalState('align_ok', gs_press_widget, ('add_pcs', 500), (), {'param1': WID_IDEN.PARTY_ALIGNMENT_ACCEPT_BTN}),
	] + GoalState.from_sequence('add_pcs', add, ('begin', 500), ('begin', 500)) + [
		GoalState('begin', gs_press_widget, ('ch1', 2000), (), {'param1': WID_IDEN.CHAR_POOL_BEGIN_ADVENTURE}),
	  ] + ch1)
	import controllers
	if os.environ.get('IWDAP_IGNORE_FOCUS'):
		controllers.tpgui.game_is_focused = lambda: True
	autoplayer.add_scheme(cs, 'iwd_ch1')
	autoplayer.set_dialog_handler(ch1_dialog_handler)
	autoplayer.set_combat_handler(lambda slot: None)
	autoplayer.push_scheme('iwd_ch1')
	autoplayer.__exc_hook__ = lambda tb: log('ANOMALY controller tick raised: ' + tb)
	log('scenario %s_ch1: core=%s' % (which, E.find_core()))
	E.no_movies(show=True)
	autoplayer.schedule(700)
