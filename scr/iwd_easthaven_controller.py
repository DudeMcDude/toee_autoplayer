'''
IWD Easthaven (ie2toee) quest-giver scenario.  Enabled with env AUTOPLAYER_SCENARIO=easthaven (see
templeplus/autoplayer.py); start from the Easthaven new-game save (TP_AUTOLOAD).

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

CORE = os.environ.get('IE2TOEE_CORE', '')       # the module's ToEE_core dir (host path, e.g. Z:/.../modules/ToEE_core)
LOG = os.environ.get('IWDAP_LOG', '')
TOWN = 'AR1000'

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
			for sr in re.findall(r'AddJournalEntry\(c, (\d+), "QUEST"\)', fm.group(2)):
				sr = int(sr)
				if sr in J and J[sr][1] == 'quest':
					quests.setdefault(int(fm.group(1)), []).append((sr, J[sr][0]))
		if quests:
			res[int(m.group(1))] = {'ident': m.group(2), 'quests': quests}
	return res

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
def click_on_obj(o):
	'''engine-side hover + click on the object's tile (no OS cursor: works on a headless/unfocused display)'''
	game.mouse_move_to(o.location)
	game.mouse_click()

def _loc(o):
	return location_to_axis(o.location)

def find_npc(sid):
	for o in game.obj_list_range(game.leader.location, 200, OLC_NPC):
		if o.scripts[san_dialog] == sid and not o.is_unconscious() and o not in game.party:
			return o
	return OBJ_HANDLE_NULL

def exit_icons():
	return [o for o in game.obj_list_range(game.leader.location, 200, OLC_SCENERY) if o.obj_get_int(obj_f_scenery_teleport_to)]

def region_center(r):
	p = r['poly']
	return sum([x for x, y in p]) / len(p), sum([y for x, y in p]) / len(p)

def icon_for(area, dest_area):
	'''the exit icon of <area> nearest the centre of its exit region leading to dest_area (+ fallback entrance)'''
	import ie_travel_data as D
	r = [r for r in D.AREAS[area]['regions'] if r['dest_area'] == dest_area][0]
	ent = D.AREAS[dest_area]['entrances'][r['dest_entrance']]
	cx, cy = region_center(r)
	best, bd = OBJ_HANDLE_NULL, 1e9
	for o in exit_icons():
		x, y = _loc(o); d = (x - cx) ** 2 + (y - cy) ** 2
		if d < bd:
			best, bd = o, d
	return best, (D.AREAS[dest_area]['map'], (ent[0], ent[1]))

def area_of_map(m):
	import ie_travel_data as D
	return D.BY_MAP.get(m)
#endregion

#region the scenario
ST = {'givers': {}, 'plan': [], 'i': 0, 'results': [], 'anomalies': [], 'cur': None}
HOME = {}   # script id -> candidate areas (from the baked areas: ie_bake_arNNNN.OBJS idents)

def locate_givers(givers):
	import ie_travel_data as D
	for a in sorted(D.AREAS):
		try:
			mod = __import__('ie_bake_' + a.lower())
		except Exception, e:
			log('ANOMALY no bake module for %s: %s' % (a, e)); continue
		idents = set([v['spec'].get('ident') for v in mod.OBJS.values() if v.get('k') == 'npc'])
		for sid, g in givers.items():
			if g['ident'] in idents:
				HOME.setdefault(sid, []).append(a)

def anomaly(s):
	log('ANOMALY ' + s); ST['anomalies'].append(s)

class Step:  # tiny state holder per tick-driven task
	def __init__(self, kind, **kw):
		self.kind = kind; self.n = 0; self.__dict__.update(kw)

def build_plan():
	givers = load_quest_givers()
	ST['givers'] = givers
	locate_givers(givers)
	town = [s for s in givers if TOWN in HOME.get(s, [])]
	inside = [s for s in givers if s not in town and HOME.get(s)]
	for sid in sorted(givers):
		g = givers[sid]
		log('GIVER %s script %d areas %s quests %s' % (g['ident'], sid, HOME.get(sid), sorted(set([q for v in g['quests'].values() for _, q in v]))))
	plan = [Step('start')]
	for sid in sorted(town):
		plan.append(Step('talk', sid=sid))
	for sid in sorted(inside, key=lambda s: HOME[s][0]):
		for a in HOME[sid]:                       # e.g. Hrothgar is baked in two areas (day/night): try each
			plan += [Step('enter', area=a), Step('talk', sid=sid, optional=len(HOME[sid]) > 1), Step('leave', area=a)]
	ST['plan'] = plan

def tick_start(st):
	'''be in the town (AR1000) first; a save elsewhere is teleported to the town's first entrance (anomaly)'''
	import ie_travel_data as D
	if get_current_map() == D.AREAS[TOWN]['map']:
		return st.n > 20
	if st.n == 1:
		e = sorted(D.AREAS[TOWN]['entrances'].items())[0][1]
		anomaly('start map %d is not the town: teleport to %s' % (get_current_map(), e[:2]))
		game.fade_and_teleport(0, 0, 0, D.AREAS[TOWN]['map'], e[0], e[1])
	return st.n > 300

def tick_enter(st):
	if area_of_map(get_current_map()) == st.area:
		log('ENTER %s ok after %d ticks' % (st.area, st.n)); return 1
	if st.n == 1:
		ic, st.fb = icon_for(TOWN, st.area)
		if ic == OBJ_HANDLE_NULL:
			anomaly('no exit icon to %s near the party' % st.area); st.n = 150
		else:
			game.scroll_to(ic.location); st.ic = ic
	elif st.n == 10:
		click_on_obj(st.ic); log('CLICK icon to %s at %s' % (st.area, _loc(st.ic)))
	elif st.n == 150:
		anomaly('icon click to %s did not change the map: teleport' % st.area)
		m, (x, y) = st.fb; game.fade_and_teleport(0, 0, 0, m, x, y)
	elif st.n > 300:
		anomaly('could not reach %s' % st.area); return 1
	return 0

def tick_leave(st):
	if get_current_map() == 5900:
		log('LEAVE %s ok after %d ticks' % (st.area, st.n)); return 1
	if st.n == 1:
		ic, st.fb = icon_for(st.area, TOWN)
		if ic == OBJ_HANDLE_NULL:
			anomaly('no exit icon in %s' % st.area); st.n = 150
		else:
			game.scroll_to(ic.location); st.ic = ic
	elif st.n == 10:
		click_on_obj(st.ic); log('CLICK exit icon of %s at %s' % (st.area, _loc(st.ic)))
	elif st.n == 150:
		anomaly('exit icon click in %s did not change the map: teleport' % st.area)
		m, (x, y) = st.fb; game.fade_and_teleport(0, 0, 0, m, x, y)
	elif st.n > 300:
		anomaly('could not leave %s' % st.area); return 1
	return 0

def tick_talk(st):
	g = ST['givers'][st.sid]
	if st.n == 1:
		st.npc = find_npc(st.sid)
		if st.npc == OBJ_HANDLE_NULL:
			if getattr(st, 'optional', 0):
				log('TALK %s not in %s (optional)' % (g['ident'], area_of_map(get_current_map()))); return 1
			anomaly('%s (script %d) not found on map %d' % (g['ident'], st.sid, get_current_map())); finish_talk(st, 0); return 1
		npc, to = load_dlg_graph(st.sid)
		goals = set(g['quests'])
		ST['cur'] = {'sid': st.sid, 'goals': goals, 'dist': dist_to_goal(npc, to, goals), 'visits': {}, 'replies': 0,
		             'hit': [], 'talked': 0}
		game.scroll_to(st.npc.location)
	elif st.n == 10:
		click_on_obj(st.npc); log('CLICK %s at %s' % (g['ident'], _loc(st.npc)))
	elif st.n == 150 and not ST['cur']['talked']:
		anomaly('click on %s did not start the dialogue: scripted start' % g['ident'])
		st.npc.object_script_execute(game.leader, san_dialog)
	elif st.n > 150 and not dlg.is_engaged() and (ST['cur']['talked'] or st.n > 300):
		finish_talk(st, 1); return 1
	return 0

def finish_talk(st, talked):
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
		log('RESULT %s %s quest %d (journal %d, replies %s) state %d, chosen %s' % (ok and 'PASS' or 'FAIL', g['ident'], q, sr,
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
	dlg_reply(pick)
	return 1

def gs_iwd_tour(slot):
	if not is_ingame() or not len(game.party):
		return 0
	if not ST['plan'] and ST['i'] == 0:
		import ie_travel
		try: ie_travel.start()
		except Exception, e: log('travel start: %s' % e)
		build_plan()
	if ST['i'] >= len(ST['plan']):
		report(); return 1
	st = ST['plan'][ST['i']]
	st.n += 1
	try:
		done = {'start': tick_start, 'enter': tick_enter, 'leave': tick_leave, 'talk': tick_talk}[st.kind](st)
	except Exception, e:
		import traceback; anomaly('step %s raised %s %s' % (st.kind, e, traceback.format_exc())); done = 1
	if done:
		ST['i'] += 1
	return 0

def report():
	log('SUMMARY %d/%d quests reached, %d anomalies' % (len([r for r in ST['results'] if r[3]]), len(ST['results']), len(ST['anomalies'])))
	for r in ST['results']:
		log('TABLE %s | quest %d | journal %d | %s | state %d' % (r[0], r[1], r[2], r[3] and 'PASS' or 'FAIL', r[4]))
	log('DONE')

def gs_idle_forever(slot):
	return 0

def setup_playtester(autoplayer):
	cs = ControlScheme()
	cs.__set_stages__([
		GoalStateStart(gs_iwd_tour, ('end', 100), ('start', 100)),
		GoalState('end', gs_idle_forever, ('end', 5000), ('end', 5000)),
	])
	if os.environ.get('IWDAP_IGNORE_FOCUS'):   # headless runs (private Xvfb, no window manager): Win32 focus is unreliable
		import controllers
		controllers.tpgui.game_is_focused = lambda: True
	autoplayer.add_scheme(cs, 'iwd_easthaven')
	autoplayer.set_dialog_handler(iwd_dialog_handler)
	autoplayer.set_combat_handler(lambda slot: None)
	autoplayer.push_scheme('iwd_easthaven')
	log('scenario easthaven: core=%s' % CORE)
	if LOG:
		f = open(LOG, 'a'); f.write('SHOT town_start\n'); f.close()
	autoplayer.schedule(700)
#endregion
