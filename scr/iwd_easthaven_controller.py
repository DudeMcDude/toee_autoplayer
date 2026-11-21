'''
IWD Easthaven / IWD2 Targos (ie2toee) quest-giver scenarios.  Enabled with env AUTOPLAYER_SCENARIO=easthaven or
targos (see templeplus/autoplayer.py); the harness loads a save (TP_AUTOLOAD) and the tour teleports into the town.
The scenario only differs in its town area (SCENARIOS); everything else comes from the converted module.

Everything is data driven from the converted module (no hand-written routes or dialogue line numbers):
  * ie_travel_data.AREAS   - maps, exit regions and entrances (finds the exit icons / teleport fallbacks)
  * py0NNNN<ident>.py      - converted dialogue actions: a reply whose action calls AddJournalEntry(c, strref, "QUEST")
                             starts a quest (strref -> ToEE quest id via ie_journal.JOURNAL)
  * dlg/0NNNN<ident>.dlg   - converted dialogue graph: shortest reply path towards such a quest reply
Per quest giver: travel (click exit icon, wait for the map change), click the NPC, answer towards the quest
replies, check game.quests[...] afterwards. Every fallback (teleport, scripted dialogue start) is an ANOMALY.
Output lines "IWDAP ..." go to stdout (TemplePlus.log) and to $IWDAP_LOG if set.
'''
from toee import *
from toee import game
from controllers import ControlScheme, GoalState, GoalStateStart
from controller_callbacks_common import get_current_map, dlg_reply, find_attack_lines, is_ingame
from utilities import location_from_axis, location_to_axis
import gamedialog as dlg
import os, re

CORE = os.environ.get('IE2TOEE_CORE', '')       # the module's _core dir (e.g. Z:/.../modules/IWD_core); unset: found from ie_journal
LOG = os.environ.get('IWDAP_LOG', '')
# scenario -> town area (ie_travel_data key) and scheme name. IWD's area keys are ARnnnn, IWD2's I2ARnnnn.
# travel 'hub': every interior visit is enter-from-town, talk, leave-to-town (Easthaven, as validated in Oct);
# 'route': goto steps that walk hop by hop from wherever the party is (Targos: AR1000 -> AR1100 -> AR1200 -> AR1201)
SCENARIOS = {'easthaven': {'town': 'AR1000', 'scheme': 'iwd_easthaven', 'travel': 'hub'},
             'targos': {'town': 'I2AR1000', 'scheme': 'iwd2_targos', 'travel': 'route'}}
SCENARIO = os.environ.get('AUTOPLAYER_SCENARIO', 'easthaven')
if SCENARIO not in SCENARIOS:
	SCENARIO = 'easthaven'
TOWN = SCENARIOS[SCENARIO]['town']

def configure(name):
	global SCENARIO, TOWN
	SCENARIO = name; TOWN = SCENARIOS[name]['town']

def find_core():
	'''the converted module's _core dir: $IE2TOEE_CORE, else the folder holding the loose ie_journal.py (its parent),
	so a native Windows run needs no host path'''
	global CORE
	if CORE and os.path.isdir(os.path.join(CORE, 'scr')):
		return CORE
	try:
		import ie_journal
		d = os.path.dirname(os.path.dirname(os.path.abspath(ie_journal.__file__)))
		if os.path.isdir(os.path.join(d, 'scr')) and os.path.isdir(os.path.join(d, 'dlg')):
			CORE = d
	except Exception as e:
		log('find_core: %s' % e)
	return CORE

def log(s):
	print('IWDAP ' + s)
	if LOG:
		f = open(LOG, 'a'); f.write(s + '\n'); f.close()

#region data: quest givers from the converted dialogue
def _core_file(sub, prefix):
	d = os.path.join(CORE, sub)
	for n in sorted(os.listdir(d)):
		if n.startswith(prefix):
			return os.path.join(d, n)
	return None

def load_quest_givers():
	'''-> {script_id: {'ident', 'quests': {reply_line: [(strref, quest_id)]}}} for every converted dialogue
	that can add a 'quest' journal entry.'''
	import ie_journal
	J = ie_journal.JOURNAL
	res = {}
	d = os.path.join(CORE, 'scr')
	for n in sorted(os.listdir(d)):
		m = re.match(r'py0(\d{4})ie_(\w+)\.py$', n)
		if not m:
			continue
		src = open(os.path.join(d, n)).read()
		quests = {}
		for fm in re.finditer(r'def ie_a(\d+)\(npc, pc\):\n(.*)', src):
			for sr in re.findall(r'AddJournalEntry\(c, (\d+), "QUEST"\)', fm.group(2)) + re.findall(QUEST_KW, fm.group(2)):
				sr = int(sr)
				if sr in J and J[sr][1] == 'quest':
					quests.setdefault(int(fm.group(1)), []).append((sr, J[sr][0]))
		if quests:
			res[int(m.group(1))] = {'ident': m.group(2), 'quests': quests}
	return res

QUEST_KW = r"journal=\((\d+), 'quest'\)"   # dlg_do(..., journal=(strref, 'quest')): the reply adds a quest entry
GLOB_RE = r'T\.(Global|GlobalGT|GlobalLT)\(c, "(\w+)", "GLOBAL", (\d+)\)'

def load_flag_deps(givers):
	'''per giver: 'sets' = GLOBAL vars its dialogue actions SetGlobal; 'needs' = [(var, op, value, negated)] tested by the
	conditions of its quest-giving replies (story flags other conversations must set first, or must not have set yet)'''
	d = os.path.join(CORE, 'scr')
	for n in sorted(os.listdir(d)):
		m = re.match(r'py0(\d{4})ie_(\w+)\.py$', n)
		if not m or int(m.group(1)) not in givers:
			continue
		g = givers[int(m.group(1))]
		src = open(os.path.join(d, n)).read()
		g['sets'] = set(re.findall(r'SetGlobal\(c, "(\w+)", "GLOBAL", \d+\)', src))
		g['needs'] = []
		for fm in re.finditer(r'def ie_c(\d+)\(npc, pc\):\n(.*)', src):
			if int(fm.group(1)) in g['quests']:
				for neg, op, var, v in re.findall(r'(not )?' + GLOB_RE, fm.group(2)):
					g['needs'].append((var, op, int(v), bool(neg)))

def flag_order(sids, givers):
	'''order the visits so a giver whose quest reply needs flag X > 0 comes after the giver setting X, and one whose
	quest reply needs X == 0 comes before it (data-driven from the converted dialogue conditions)'''
	before = set()   # (a, b): a must be visited before b
	for b in sids:
		for var, op, v, neg in givers[b].get('needs', []):
			if neg or op == 'GlobalLT' and v > 1:
				continue          # (X < 2 already holds before anyone sets X: no order)
			zero = op == 'Global' and v == 0 or op == 'GlobalLT'
			for a in sids:
				if a != b and var in givers[a].get('sets', ()):
					if zero: before.add((b, a))
					else: before.add((a, b))
	order = list(sids)
	for _ in range(len(order) ** 2):
		moved = 0
		for a, b in before:
			if (b, a) in before: continue        # a cycle: the second pass handles it
			ia, ib = order.index(a), order.index(b)
			if ia > ib:
				order.insert(ib, order.pop(ia)); moved = 1
		if not moved: break
	ORDER_DEPS.clear(); ORDER_DEPS.update(before)
	for a, b in sorted(before):
		log('ORDER %s before %s' % (givers[a]['ident'], givers[b]['ident']))
	return order

def load_dlg_graph(sid):
	'''-> (npc_lines {line: [reply lines]}, reply_to {reply line: npc line}) of dlg/0<sid>*.dlg'''
	f = _core_file('dlg', '%05d' % sid)
	npc, to, cur = {}, {}, None
	for m in re.finditer(r'\{(\d+)\}\{[^}]*\}\{([^}]*)\}\{([^}]*)\}\{[^}]*\}\{([^}]*)\}', open(f).read()):
		ln, g, iq, rt = int(m.group(1)), m.group(2), m.group(3), m.group(4)
		if iq.strip():            # PC reply (has an intelligence field)
			to[ln] = int(rt) if rt.strip().lstrip('-').isdigit() else 0
			if cur is not None:
				npc[cur].append(ln)
		else:
			cur = ln; npc[ln] = []
	return npc, to

def dist_to_goal(npc, to, goals):
	'''BFS backwards: npc line -> number of replies to reach a goal reply'''
	dist = {}
	frontier = [(l, 0) for l, rs in npc.items() if [r for r in rs if r in goals]]
	while frontier:
		l, d = frontier.pop(0)
		if l in dist:
			continue
		dist[l] = d
		for l2, rs in npc.items():
			if l2 not in dist and [r for r in rs if to.get(r) == l]:
				frontier.append((l2, d + 1))
	return dist
#endregion

#region world helpers
def click_on_obj(o, action=None):
	'''pre-click verification lives in controller_ui_util.verified_click (generic for all controllers)'''
	import controller_ui_util as cu
	# never fall back to a blind click for a talk: on an NPC that shows the attack cursor (IE neutrals the engine
	# rates hostile, e.g. Firtha) it would be an attack and start a fight the tour itself caused
	ok, msg = cu.verified_click(o, action, log, fallback=None if action == 'talk' else 'click')
	return msg

def _loc(o):
	return location_to_axis(o.location)

def is_hidden(o):
	return o.object_flags_get() & OF_OFF   # IE creatures that start hidden (IWD2 CRE 0x29c) are baked OF_OFF

HIDDEN = {}   # script id -> hidden objects seen (reported as SKIP, not as a missing giver)

def find_npc(sid):
	# (obj_list_range radius is not in tiles: 200 missed Elisia ~100 tiles east of the Easthaven start; 300 reaches her)
	for o in game.obj_list_range(game.leader.location, 300, OLC_NPC):
		if o.scripts[san_dialog] == sid and not o.is_unconscious() and o not in game.party:
			if is_hidden(o):
				HIDDEN[sid] = HIDDEN.get(sid, 0) + 1; continue
			return o
	return OBJ_HANDLE_NULL

def spawn_tiles(ident, area):
	'''the giver's placed spot(s) in area (converted creature spec, IE pixels -> tile): scanned first, since only
	loaded sectors are listed and some givers stand far from every entrance (IWD2 AR1200: Isher ~70 tiles away)'''
	try:
		import ie_runtime as rt
		mod = __import__('ie_creatures_' + re.sub('^I2', '', area or '').lower())
		ar = re.sub('^I2', '', area).upper()
		return [rt.ie_to_tile(ar, c['x'], c['y']) for c in getattr(mod, 'CREATURES', [])
		        if c.get('ident') == ident and c.get('x') is not None]
	except Exception as e:
		log('  no spawn spot for %s in %s: %s' % (ident, area, e)); return []

def route(src, dst):
	'''shortest list of areas from src (excluded) to dst over the exit regions of ie_travel_data (converted areas only)'''
	import ie_travel_data as D
	prev, frontier = {src: None}, [src]
	while frontier:
		a = frontier.pop(0)
		if a == dst:
			break
		for r in D.AREAS[a]['regions']:
			b = r['dest_area']
			if b in D.AREAS and b not in prev:
				prev[b] = a; frontier.append(b)
	if dst not in prev:
		return None
	path, a = [], dst
	while a != src:
		path.insert(0, a); a = prev[a]
	return path

def exit_icons(loc=None):
	return [o for o in game.obj_list_range(loc or game.leader.location, 200, OLC_SCENERY) if o.obj_get_int(obj_f_scenery_teleport_to)]

def region_center(r):
	p = r['poly']
	return sum([x for x, y in p]) / len(p), sum([y for x, y in p]) / len(p)

def icon_for(area, dest_area):
	'''the exit icon of <area> nearest the centre of its exit region leading to dest_area (+ fallback entrance)'''
	import ie_travel_data as D
	r = [r for r in D.AREAS[area]['regions'] if r['dest_area'] == dest_area][0]
	ent = D.AREAS[dest_area]['entrances'][r['dest_entrance']]
	cx, cy = r.get('anchor') or region_center(r)   # the icon sits at the anchor: search around it, not around the leader
	best, bd = OBJ_HANDLE_NULL, 1e9                 # (from far away the leader-centred list missed AR1001's icon -> AR1014's)
	for o in exit_icons(location_from_axis(int(cx), int(cy))):
		x, y = _loc(o); d = (x - cx) ** 2 + (y - cy) ** 2
		if d < bd:
			best, bd = o, d
	return best, (D.AREAS[dest_area]['map'], (ent[0], ent[1]))

APPROACH_TILES = 40   # engine path search gives up past ~40 tiles ("Path Length is out of range", node fallback fails)

def approach_icon(area, ic, label):
	'''a player crosses a big map in several clicks: when the leader is more than APPROACH_TILES from the exit icon,
	move the party to this area's entrance nearest the icon (an arrival tile, walkable by construction) first'''
	import ie_travel_data as D
	if os.environ.get('IWDAP_NO_APPROACH') or area not in D.AREAS:
		return
	lx, ly = _loc(game.leader); ix, iy = _loc(ic)
	if max(abs(lx - ix), abs(ly - iy)) <= APPROACH_TILES:
		return
	ents = [e[:2] for e in D.AREAS[area]['entrances'].values()]
	ents = [e for e in ents if max(abs(e[0] - ix), abs(e[1] - iy)) <= APPROACH_TILES]
	if not ents:
		return
	e = min(ents, key=lambda e: (e[0] - ix) ** 2 + (e[1] - iy) ** 2)
	log('APPROACH %s icon: leader %s is %d tiles away, moving to entrance %s first' % (label, (lx, ly), max(abs(lx - ix), abs(ly - iy)), tuple(e)))
	game.fade_and_teleport(0, 0, 0, get_current_map(), e[0], e[1])

def area_of_map(m):
	import ie_travel_data as D
	return D.BY_MAP.get(m)
#endregion

#region the scenario
ST = {'givers': {}, 'plan': [], 'i': 0, 'results': [], 'anomalies': [], 'cur': None, 'skipped': {}}
HOME = {}   # script id -> candidate areas (from the baked areas: ie_bake_arNNNN.OBJS idents)

def locate_givers(givers):
	import ie_travel_data as D
	for a in sorted(D.AREAS):
		try:
			mod = __import__('ie_bake_' + a.lower())
		except Exception as e:
			log('ANOMALY no bake module for %s: %s' % (a, e)); continue
		idents = set([v['spec'].get('ident') for v in mod.OBJS.values() if v.get('k') == 'npc'])
		for sid, g in givers.items():
			if g['ident'] in idents:
				if a != TOWN and route(TOWN, a) is None:
					log('GIVER %s in %s: no route from %s (skipped)' % (g['ident'], a, TOWN)); continue
				HOME.setdefault(sid, []).append(a)

def anomaly(s):
	log('ANOMALY ' + s); ST['anomalies'].append(s)

# walk timeouts (ticks of ~100 ms): a step gives up at its timeout unless the leader is still getting closer to (or
# moving towards) the target, then it is extended by WALK_EXTEND at a time, at most WALK_CAP ticks past the timeout.
WALK_TIMEOUT = 150; WALK_EXTEND = 50; WALK_CAP = 450
# per-step overrides: 'kind:AREA' (enter/leave), 'talk:<giver ident>' or 'quest:<id>' (the largest that applies wins)
TIMEOUTS = {}

def step_timeout(kind, area=None, sid=None):
	t = [TIMEOUTS.get('%s:%s' % (kind, area))]
	if sid is not None:
		g = ST['givers'][sid]
		t += [TIMEOUTS.get('talk:%s' % g['ident'])] + [TIMEOUTS.get('quest:%d' % q) for v in g['quests'].values() for _, q in v]
	t = [x for x in t if x]
	return t and max(t) or WALK_TIMEOUT

def walk_due(st, target):
	'''call once per tick: True on the tick the step's walk timeout runs out (extended while the leader makes progress)'''
	if not hasattr(st, 'dl'):
		st.dl = getattr(st, 'timeout', WALK_TIMEOUT); st.dl0 = st.dl; st.snap = None
	if st.n % 25 == 0 and st.n > 0:
		pos = _loc(game.leader); d = target and target != OBJ_HANDLE_NULL and game.leader.distance_to(target) or 0
		st.moving = st.snap is not None and (d < st.snap[1] - 0.5 or (pos != st.snap[0] and d <= st.snap[1] + 0.5))
		st.snap = (pos, d)
	if st.n != st.dl:
		return False
	if getattr(st, 'moving', 0) and st.dl + WALK_EXTEND <= st.dl0 + WALK_CAP:
		st.dl += WALK_EXTEND
		log('EXTEND %s %s timeout to %d ticks: leader %s still closing in (dist %.1f)' % (st.kind, getattr(st, 'area', '') or st.sid, st.dl, st.snap[0], st.snap[1]))
		return False
	return True

class Step:  # tiny state holder per tick-driven task
	def __init__(self, kind, **kw):
		self.kind = kind; self.n = 0; self.__dict__.update(kw)

def build_plan():
	find_core()
	givers = load_quest_givers()
	ST['givers'] = givers
	locate_givers(givers)
	load_flag_deps(givers)
	for sid in sorted(givers):
		g = givers[sid]
		log('GIVER %s script %d areas %s quests %s needs %s' % (g['ident'], sid, HOME.get(sid), sorted(set([q for v in g['quests'].values() for _, q in v])), g.get('needs')))
	sids = flag_order(sorted([s for s in givers if HOME.get(s)], key=lambda s: (TOWN not in HOME[s], HOME[s][0], s)), givers)
	if os.environ.get('IWDAP_ONLY'):   # debug probe: a single giver
		sids = [x for x in sids if givers[x]['ident'] in os.environ['IWDAP_ONLY'].split(',')]
	plan = [Step('start')]
	route_mode = SCENARIOS[SCENARIO].get('travel') == 'route'
	if route_mode:   # visit the givers area by area (stable: the flag order wins inside each area's run)
		sids = route_order(sids)
	for pas in (1, 2):
		for sid in sids:
			plan += route_mode and goto_visit_steps(sid, pas) or visit_steps(sid, pas)
		if route_mode:
			plan.append(Step('goto', area=TOWN, pas=pas))
	ST['plan'] = plan

def route_order(sids):
	'''group the givers by home area (areas in first-seen order), but keep a giver after any giver whose flags it needs
	(flag_order's constraints) by only moving a giver earlier past givers of other areas it does not depend on'''
	first = {}
	for s in sids:
		first.setdefault(home_area(s), len(first))
	return sorted(sids, key=lambda s: (first[home_area(s)], sids.index(s))) if not ORDER_DEPS else _stable_group(sids, first)

ORDER_DEPS = set()   # (a, b) giver script ids: a must be visited before b (filled by flag_order)

def _stable_group(sids, first):
	out = list(sids)
	for _ in range(len(out) ** 2):
		moved = 0
		for i in range(1, len(out)):
			a, b = out[i - 1], out[i]
			if first[home_area(b)] < first[home_area(a)] and (a, b) not in ORDER_DEPS:
				out[i - 1], out[i] = b, a; moved = 1
		if not moved:
			break
	return out

def home_area(sid):
	return TOWN in HOME[sid] and TOWN or HOME[sid][0]

def goto_visit_steps(sid, pas):
	'''route travel: [goto home area, talk] per home area; .group lets the second pass skip both'''
	steps = []
	for a in (TOWN in HOME[sid] and [TOWN] or HOME[sid]):
		g = Step('goto', area=a, pas=pas, sid=sid, timeout=step_timeout('enter', a, sid))
		g.group = 2
		steps += [g, Step('talk', sid=sid, optional=len(HOME[sid]) > 1, pas=pas, timeout=step_timeout('talk', sid=sid))]
	return steps

def visit_steps(sid, pas):
	'''per home area: [enter hop..., talk, leave hop...]; the first step of a visit carries .group (its step count) so
	the second pass can skip a whole visit. Easthaven interiors are one hop (enter, talk, leave); IWD2 Targos areas
	further out (AR1100 -> AR1200 -> AR1201) are routed hop by hop over the converted exit regions.'''
	steps = []
	for a in (TOWN in HOME[sid] and [TOWN] or HOME[sid]):  # e.g. Hrothgar is baked in two areas (day/night): try each
		talk = Step('talk', sid=sid, optional=len(HOME[sid]) > 1, pas=pas, timeout=step_timeout('talk', sid=sid))
		if a == TOWN:
			visit = [talk]
		else:
			path = [TOWN] + route(TOWN, a)
			visit = [Step('enter', area=path[i + 1], frm=path[i], pas=pas, sid=sid, timeout=step_timeout('enter', path[i + 1], sid))
			         for i in range(len(path) - 1)] + [talk]
			visit += [Step('leave', area=path[i], dest=path[i - 1], pas=pas, sid=sid, timeout=step_timeout('leave', path[i], sid))
			          for i in range(len(path) - 1, 0, -1)]
		visit[0].group = len(visit)
		steps += visit
	return steps

def open_quests(sid):
	return [q for v in ST['givers'][sid]['quests'].values() for _, q in v if game.quests[q].state not in (qs_mentioned, qs_accepted, qs_completed)]

def tick_start(st):
	'''be in the town (AR1000) first; a save elsewhere is teleported to the town's first entrance (expected with the vanilla harness save, not an anomaly)'''
	import ie_travel_data as D
	if get_current_map() == D.AREAS[TOWN]['map']:
		sp = os.environ.get('IWDAP_START')   # debug probe: put the party at x,y first
		if sp and not getattr(st, 'placed', 0):
			st.placed = 1; x, y = [int(v) for v in sp.split(',')]; log('probe start at %d,%d' % (x, y))
			game.fade_and_teleport(0, 0, 0, D.AREAS[TOWN]['map'], x, y); st.n = 0
		return st.n > 20
	if st.n == 1:
		e = sorted(D.AREAS[TOWN]['entrances'].items())[0][1]
		log('start map %d (the harness loads a vanilla save): teleport into the town at %s' % (get_current_map(), e[:2]))
		game.fade_and_teleport(0, 0, 0, D.AREAS[TOWN]['map'], e[0], e[1])
	return st.n > 300

def tick_enter(st):
	due = walk_due(st, getattr(st, 'ic', None))
	if area_of_map(get_current_map()) == st.area:
		log('ENTER %s ok after %d ticks' % (st.area, st.n)); return 1
	if st.n == 1:
		ic, st.fb = icon_for(getattr(st, 'frm', TOWN), st.area)
		if ic == OBJ_HANDLE_NULL:
			anomaly('no exit icon to %s near the party' % st.area); st.n = st.dl - 1; st.dl0 = st.dl - WALK_CAP
		else:
			game.scroll_to(ic.location); st.ic = ic
	elif st.n == 3 and getattr(st, 'ic', None):
		approach_icon(area_of_map(get_current_map()), st.ic, st.area)
	elif st.n == 10:
		st.click_from = _loc(game.leader); r = click_on_obj(st.ic, 'jump'); log('CLICKED icon to %s at %s: %s' % (st.area, _loc(st.ic), r))
	elif st.n == 60 and getattr(st, 'ic', None) and _loc(game.leader) == getattr(st, 'click_from', None):
		st.click_from = _loc(game.leader); r = click_on_obj(st.ic, 'jump'); log('RECLICK %s icon (leader has not moved from %s): %s' % (st.area, st.click_from, r))
	elif st.n % 25 == 0 and st.n < st.dl and getattr(st, 'ic', None):
		log('  wait icon: leader %s icon %s dist %.1f' % (_loc(game.leader), _loc(st.ic), game.leader.distance_to(st.ic)))
	elif due:
		anomaly('icon click to %s did not change the map: teleport' % st.area)
		m, (x, y) = st.fb; game.fade_and_teleport(0, 0, 0, m, x, y)
	elif st.n > st.dl + 150:
		anomaly('could not reach %s' % st.area); return 1
	return 0

def tick_leave(st):
	due = walk_due(st, getattr(st, 'ic', None))
	import ie_travel_data as D
	dest = getattr(st, 'dest', TOWN)
	if get_current_map() == D.AREAS[dest]['map']:     # (was 5900: Easthaven's map before the 5012-5030 renumbering)
		log('LEAVE %s ok after %d ticks' % (st.area, st.n)); return 1
	if st.n == 1:
		ic, st.fb = icon_for(st.area, dest)
		if ic == OBJ_HANDLE_NULL:
			anomaly('no exit icon in %s' % st.area); st.n = st.dl - 1; st.dl0 = st.dl - WALK_CAP
		else:
			game.scroll_to(ic.location); st.ic = ic
	elif st.n == 3 and getattr(st, 'ic', None):
		approach_icon(st.area, st.ic, st.area)
	elif st.n == 10:
		st.click_from = _loc(game.leader); r = click_on_obj(st.ic, 'jump'); log('CLICKED exit icon of %s at %s: %s' % (st.area, _loc(st.ic), r))
	elif st.n == 60 and getattr(st, 'ic', None) and _loc(game.leader) == getattr(st, 'click_from', None):
		st.click_from = _loc(game.leader); r = click_on_obj(st.ic, 'jump'); log('RECLICK %s icon (leader has not moved from %s): %s' % (st.area, st.click_from, r))
	elif st.n % 25 == 0 and st.n < st.dl and getattr(st, 'ic', None):
		log('  wait icon: leader %s icon %s dist %.1f' % (_loc(game.leader), _loc(st.ic), game.leader.distance_to(st.ic)))
	elif due:
		anomaly('exit icon click in %s did not change the map: teleport' % st.area)
		m, (x, y) = st.fb; game.fade_and_teleport(0, 0, 0, m, x, y)
	elif st.n > st.dl + 150:
		anomaly('could not leave %s' % st.area); return 1
	return 0

def tick_goto(st):
	'''route travel: hop by hop (each hop is an 'enter' step: click the exit icon, teleport fallback = ANOMALY) from the
	current area to st.area, re-routing after every hop'''
	cur = area_of_map(get_current_map())
	if cur == st.area and getattr(st, 'hop', None) is None:
		log('GOTO %s ok after %d ticks, %d hops' % (st.area, st.n, getattr(st, 'hops', 0))); return 1
	if getattr(st, 'hop', None) is None:
		path = cur and route(cur, st.area)
		st.hops = getattr(st, 'hops', 0) + 1
		if not path or st.hops > 8:
			anomaly('no way from %s to %s (map %d, hop %d)' % (cur, st.area, get_current_map(), st.hops)); return 1
		st.hop = Step('enter', area=path[0], frm=cur, sid=getattr(st, 'sid', None), timeout=step_timeout('enter', path[0], getattr(st, 'sid', None)))
		log('HOP %s -> %s (towards %s)' % (cur, path[0], st.area))
	st.hop.n += 1
	if tick_enter(st.hop):
		st.hop = None
	return 0

def tick_talk(st):
	g = ST['givers'][st.sid]
	due = st.n >= 1 and walk_due(st, getattr(st, 'npc', None))
	if st.n < 1:            # waiting for scrolled-to sectors (the scan sets n = -5): nothing set up yet
		return 0
	if st.n == 1:
		st.npc = find_npc(st.sid)
		if st.npc == OBJ_HANDLE_NULL and getattr(st, 'scan', None) is None:
			import ie_travel_data as D            # only loaded sectors are listed: look around the area's entrances
			a = area_of_map(get_current_map())
			st.scan = [e[:2] for _, e in sorted(D.AREAS[a]['entrances'].items())] if a in D.AREAS else []
			st.scan = spawn_tiles(g['ident'], a) + st.scan   # far from every entrance (IWD2 Isher/Caulder in AR1200)
			st.scanned = None
		if st.npc == OBJ_HANDLE_NULL and st.scanned:   # sectors around the last scroll target are loaded by now
			e = st.scanned
			for o in game.obj_list_range(location_from_axis(e[0], e[1]), 60, OLC_NPC):
				if o.scripts[san_dialog] == st.sid and not o.is_unconscious():
					st.npc = o; log('  found %s near %s' % (g['ident'], e)); break
		if st.npc == OBJ_HANDLE_NULL and st.scan:      # scroll there and look again in a few ticks
			st.scanned = st.scan.pop(0); game.scroll_to(location_from_axis(st.scanned[0], st.scanned[1]))
			st.n = -5; return 0
		if st.npc == OBJ_HANDLE_NULL:
			if getattr(st, 'optional', 0):
				log('TALK %s not in %s (optional)' % (g['ident'], area_of_map(get_current_map()))); return 1
			if HIDDEN.get(st.sid):      # placed hidden (IE: revealed later by a script or story flag): not a conversion bug
				log('SKIP %s (script %d) is hidden on map %d (starts hidden in the IE; revealed by a script later)' % (g['ident'], st.sid, get_current_map()))
				finish_talk(st, 0, skipped=1); return 1
			anomaly('%s (script %d) not found on map %d' % (g['ident'], st.sid, get_current_map())); finish_talk(st, 0); return 1
		npc, to = load_dlg_graph(st.sid)
		goals = set(g['quests'])
		ST['cur'] = {'sid': st.sid, 'goals': goals, 'dist': dist_to_goal(npc, to, goals), 'visits': {}, 'replies': 0,
		             'hit': [], 'talked': 0}
		game.scroll_to(st.npc.location)
	elif st.n == 5:
		lx, ly = location_to_axis(game.leader.location); nx, ny = location_to_axis(st.npc.location)
		if max(abs(lx - nx), abs(ly - ny)) > 40 and not os.environ.get('IWDAP_NO_APPROACH'):   # engine path search gives up past ~40 tiles (path length out of range,
			# node fallback fails): move the party next to the NPC first, then click as a player would
			log('APPROACH %s: leader %s is %d tiles away, moving next to the NPC' % (g['ident'], (lx, ly), max(abs(lx - nx), abs(ly - ny))))
			game.fade_and_teleport(0, 0, 0, get_current_map(), nx + 4, ny + 4)
	elif st.n == 20:
		r = click_on_obj(st.npc, 'talk'); log('CLICKED %s at %s: %s' % (g['ident'], _loc(st.npc), r))
		if r.startswith('not clicked'):   # the click would be an attack: start the dialogue directly instead
			anomaly('%s shows no talk cursor (attack cursor on a friendly?): scripted dialogue start, no click' % g['ident'])
			st.npc.object_script_execute(game.leader, san_dialog)
	elif st.n % 25 == 0 and st.n < st.dl and not ST['cur']['talked']:
		log('  wait %s: leader %s npc %s dist %.1f' % (g['ident'], _loc(game.leader), _loc(st.npc), game.leader.distance_to(st.npc)))
	elif due and not ST['cur']['talked']:
		anomaly('click on %s did not start the dialogue: scripted start' % g['ident'])
		st.npc.object_script_execute(game.leader, san_dialog)
	elif st.n > st.dl and not dlg.is_engaged() and (ST['cur']['talked'] or st.n > st.dl + 150):
		finish_talk(st, 1); return 1
	return 0

def finish_talk(st, talked, skipped=0):
	g = ST['givers'][st.sid]; c = ST['cur'] or {'hit': [], 'replies': 0}
	byq = {}
	for line, qs in sorted(g['quests'].items()):
		for sr, q in qs:
			byq.setdefault((q, sr), []).append(line)
	for (q, sr), lines in sorted(byq.items()):
		if not talked and [r for r in ST['results'] if r[1] == q and r[3]]:
			continue       # (second copy of a giver, e.g. Hrothgar day/night, already passed)
		state = game.quests[q].state
		ok = state in (qs_mentioned, qs_accepted)
		chosen = [l for l in lines if l in c['hit']]
		ST['results'].append((g['ident'], q, sr, ok, state, chosen))
		if skipped and not ok:
			ST['skipped'][g['ident']] = 1
		log('RESULT %s %s quest %d (journal %d, replies %s) state %d, chosen %s' % (ok and 'PASS' or skipped and 'SKIP' or 'FAIL', g['ident'], q, sr,
			lines, state, chosen))
	if LOG:
		f = open(LOG, 'a'); f.write('SHOT talk_%s\n' % g['ident']); f.close()
	log('TALK %s done: %d replies, quest replies chosen %s' % (g['ident'], c['replies'], c['hit']))
	ST['cur'] = None

def iwd_dialog_handler(slot):
	'''generic, data-driven reply choice: a quest-giving reply > the reply closest to one > first non-attack reply;
	loop guard: a line seen 3 times -> take its last reply.'''
	ds = dlg.get_current_state()
	c = ST['cur']
	N = ds.reply_count
	if c is None or ds.script_id != c['sid'] or N == 0:
		dlg_reply(0); return 1
	c['talked'] = 1; c['replies'] += 1
	ln = ds.line_number
	v = c['visits'][ln] = c['visits'].get(ln, 0) + 1
	attack = find_attack_lines(ds)
	pick, best = None, 1e9
	for i in range(N):
		if i in attack:
			continue
		eff = ds.get_reply_effect(i)
		m = re.search(r'ie_a(\d+)', eff)
		if m and int(m.group(1)) in c['goals'] and int(m.group(1)) not in c['hit']:
			pick = i; c['hit'].append(int(m.group(1))); break
		d = c['dist'].get(ds.get_npc_reply_id(i), 1e8)
		if d < best:
			pick, best = i, d
	if v >= 3 or c['replies'] > 60:
		pick = N - 1
	if pick is None:
		pick = 0
	log('REPLY %s line %d: %d replies %s -> pick %d (npc line %d)' % (ST['givers'][c['sid']]['ident'], ln, N,
		[ds.get_npc_reply_id(i) for i in range(N)], pick, ds.get_npc_reply_id(pick)))
	dlg_reply(pick)
	return 1

CLR = set()
def ensure_clearance():
	'''converted maps have path nodes but no clearance.bin: without it Temple+ only links path nodes by straight lines,
	so long walks around buildings fail silently (the party doesn't move). IWDAP_GENCLR=1: build it for each map once (experimental: run fx2 crashed on the next map change, and it did not fix the AR1001 icon).'''
	m = get_current_map()
	if os.environ.get('IWDAP_GENCLR') and m not in CLR:
		CLR.add(m)
		import debug
		try:
			debug.genclr(); log('CLEARANCE generated for map %d' % m)
		except Exception as e:
			log('CLEARANCE failed on map %d: %s' % (m, e))

def gs_iwd_tour(slot):
	if not is_ingame() or not len(game.party):
		return 0
	ensure_clearance()
	if not ST['plan'] and ST['i'] == 0:
		import ie_travel
		try: ie_travel.start()
		except Exception as e: log('travel start: %s' % e)
		build_plan()
	if ST['i'] >= len(ST['plan']):
		report(); return 1
	st = ST['plan'][ST['i']]
	if st.n == 0 and st.kind in ('enter', 'talk', 'goto') and getattr(st, 'sid', None) is not None and getattr(st, 'pas', 1) == 2 and not open_quests(st.sid):
		ST['i'] += getattr(st, 'group', 1); return 0   # (an interior visit: enter, talk, leave)                   # second pass: only givers with quests still open
	st.n += 1
	if st.n % 25 == 1 or os.environ.get('IWDAP_VERBOSE'):
		log('TICK step %d/%d %s n=%d map %d dlg %d' % (ST['i'], len(ST['plan']), st.kind, st.n, get_current_map(), dlg.is_engaged()))
	try:
		done = {'start': tick_start, 'enter': tick_enter, 'leave': tick_leave, 'talk': tick_talk, 'goto': tick_goto}[st.kind](st)
	except Exception as e:
		import traceback; anomaly('step %s raised %s %s' % (st.kind, e, traceback.format_exc())); done = 1
	if done:
		ST['i'] += 1
	return 0

def report():
	log('SUMMARY %d/%d quests reached, %d anomalies' % (len([r for r in ST['results'] if r[3]]), len(ST['results']), len(ST['anomalies'])))
	seen = {}
	for r in ST['results']:
		seen[(r[0], r[1])] = r
	for (who, q), r in sorted(seen.items()):
		st = game.quests[q].state
		verdict = st in (qs_mentioned, qs_accepted, qs_completed) and 'PASS' or ST['skipped'].get(who) and 'SKIP' or 'FAIL'
		log('TABLE %s | quest %d | journal %d | %s | state %d' % (who, q, r[2], verdict, st))
	log('DONE')

def gs_idle_forever(slot):
	return 0

def no_movies(show=False):
	'''Chapter runs show movies by default. The older tours retain their skip default.'''
	movies = os.environ.get('IWDAP_MOVIES')
	try:
		import ie_movies_rt as M
	except ImportError:
		return
	if not hasattr(M, '_autoplayer_playback'):
		M._autoplayer_playback = (M.play, M.play_intro, getattr(M, 'prologue', None))
	if movies == '1' or (show and movies != '0'):
		M.play, M.play_intro = M._autoplayer_playback[:2]
		if M._autoplayer_playback[2] is not None:
			M.prologue = M._autoplayer_playback[2]
		log('MOVIE playback enabled; chapter scenes use their normal playback')
		return
	def play(key):
		log('MOVIE %s skipped (autoplayer; IWDAP_MOVIES=1 plays it)' % key); return 0
	def play_intro():
		if not game.global_vars[M.FLAG_VAR]:
			game.global_vars[M.FLAG_VAR] = 1; log('MOVIE intro skipped (autoplayer)')
		return 0
	def prologue(slide):
		play_intro()
		return play(slide)
	M.play = play; M.play_intro = play_intro
	if M._autoplayer_playback[2] is not None:
		M.prologue = prologue

def setup_playtester(autoplayer, scenario=None):
	if scenario:
		configure(scenario)
	name = SCENARIOS[SCENARIO]['scheme']
	cs = ControlScheme()
	cs.__set_stages__([
		GoalStateStart(gs_iwd_tour, ('end', 100), ('start', 100)),
		GoalState('end', gs_idle_forever, ('end', 5000), ('end', 5000)),
	])
	if os.environ.get('IWDAP_IGNORE_FOCUS'):   # headless runs (private Xvfb, no window manager): Win32 focus is unreliable
		import controllers
		controllers.tpgui.game_is_focused = lambda: True
	autoplayer.add_scheme(cs, name)
	autoplayer.set_dialog_handler(iwd_dialog_handler)
	autoplayer.set_combat_handler(lambda slot: None)
	autoplayer.push_scheme(name)
	autoplayer.__exc_hook__ = lambda tb: anomaly('controller tick raised: ' + tb)
	log('scenario %s: town %s core=%s' % (SCENARIO, TOWN, find_core()))
	no_movies()
	if LOG:
		f = open(LOG, 'a'); f.write('SHOT town_start\n'); f.close()
	autoplayer.schedule(700)
#endregion
