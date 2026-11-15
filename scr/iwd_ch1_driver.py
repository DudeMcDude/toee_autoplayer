'''
IWD chapter-1 critical-path driver (ie2toee IWD convert, module IWD).  AUTOPLAYER_SCENARIO=iwd_ch1.

A real new game: the harness loads a save (TP_AUTOLOAD), the driver quits to the main menu (in-game menu -> Quit)
and starts a new game with the party pool's pregenerated characters (controller_scheme_builders' new-game stages).
Then the prologue to chapter 1, as test_ch1_path.py walks it offline:
  intro (skipped: no_movies) -> Hrothgar greets the party in Winter's Cradle (AR1006, his EHHROTHT script)
  -> talk until Caravan_Quest 1 (Join_Posse 3) -> AR1200: walk into the caravan trigger CARATRG1 (Caravan_Quest 2)
  -> Hrothgar gives the List (Supply_Quest 1) -> Pomab (AR1007) takes it (Supply_Quest 2) -> Hrothgar
  "Let us be off" -> cutscene EHHROTHM -> AR2000 Kuldahar Pass (avalanche movie, skipped) = SUMMARY CH1 PASS.
Dialogue: data driven, the shortest reply path (dlg graph) to a reply whose converted action matches the step's
regex. Travel between areas is a teleport onto the area's entrance (logged TRAVEL); talks are started with the NPC's
dialogue script. Shots: SHOT lines for run_ingame.sh (poster material).
'''
from toee import *
from toee import game
from controllers import ControlScheme, GoalState, GoalStateStart
from controller_callbacks_common import get_current_map, dlg_reply, find_attack_lines, gs_press_widget, gs_is_main_menu, gs_create_and_push_scheme
from controller_scheme_builders import create_party_pool_add_pc_scheme
from controller_ui_util import WID_IDEN
from utilities import location_from_axis, location_to_axis
import gamedialog as dlg
import iwd_easthaven_controller as E
import os, re, glob

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
	for p in sorted(glob.glob(os.path.join(E.find_core(), 'scr', 'py*ie_%s*.py' % ident))):
		src = open(p).read()
		m = re.search(r'''^AREA\s*=\s*["']([^"']*)["']''', src, re.M)
		if m and m.group(1).upper() == area.upper():
			return int(os.path.basename(p)[2:7]), src
	return None, ''

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

def ch1_dialog_handler(slot):
	'''reply on the shortest path to the step's goal reply; first sight of a speaker: a screenshot, then a pause'''
	ds = dlg.get_current_state()
	N = ds.reply_count
	c = TALK['cur']
	st = ST
	if not st.get('shot_dlg_%d' % ds.script_id):
		st['shot_dlg_%d' % ds.script_id] = 1; st['wait'] = 15
		shot('dlg_%d' % ds.script_id)
	if st.get('wait', 0) > 0:
		st['wait'] -= 1; return 0
	if N == 0:
		dlg_reply(0); return 1
	pick = None
	if c and ds.script_id == c['sid']:
		c['replies'] += 1
		v = c['visits'][ds.line_number] = c['visits'].get(ds.line_number, 0) + 1
		attack = find_attack_lines(ds); best = 1e9
		for i in range(N):
			if i in attack:
				continue
			m = re.search(r'ie_a(\d+)', ds.get_reply_effect(i) or '')     # (the action function is named by its reply line)
			if m and int(m.group(1)) in c['goals']:
				pick = i; c['hit'] = 1; break
			d = c['dist'].get(ds.get_npc_reply_id(i), 1e8)
			if d < best:
				pick, best = i, d
		if v >= 3 or c['replies'] > 60:
			pick = N - 1
	if pick is None:
		pick = 0
	log('REPLY sid %d line %d: %d replies -> pick %d (npc line %d)' % (ds.script_id, ds.line_number, N, pick, ds.get_npc_reply_id(pick)))
	dlg_reply(pick)
	return 1

#region steps
def V(name):
	import ie_runtime as rt
	return rt.get_var(None, name, 'GLOBAL')

def set_var(name, v):
	import ie_runtime as rt
	rt.set_var(None, name, 'GLOBAL', v)

def area_map(area):
	import ie_travel_data as D
	return D.AREAS[area]['map']

def area_of(m):
	import ie_travel_data as D
	for a, d in D.AREAS.items():
		if d['map'] == m:
			return a
	return None

def travel(area):
	"""a teleport onto the area's first entrance. (Walking out through the town hub instead, AR1007 -> AR1000 -> AR1006,
	did not avoid the IWD AR1006 re-entry crash: run3 of Nov 15; tools/ieap_ch1.sh relaunches from the autosave.)"""
	import ie_travel_data as D
	e = sorted(D.AREAS[area]['entrances'].items())[0][1]
	log('TRAVEL %s (map %d) entrance %s' % (area, D.AREAS[area]['map'], e[:2]))
	game.fade_and_teleport(0, 0, 0, D.AREAS[area]['map'], e[0], e[1])

def find_obj(sid):
	for o in game.obj_list_range(game.leader.location, 300, OLC_NPC):
		if o.scripts[san_dialog] == sid and o not in game.party:
			return o
	return OBJ_HANDLE_NULL

class Step(object):
	def __init__(self, kind, **kw):
		self.kind, self.n = kind, 0
		self.__dict__.update(kw)

def talk_step(st, ident, area, goal, until, force=None, talks=4):
	'''talk to ident (in area) until until() holds; up to 4 conversations. force: (var, value) set as a logged
	SHORTCUT when the talks don't get there (IWD2 test runs: get past a gate to test the rest)'''
	if until():
		return 1
	if get_current_map() != area_map(area):
		if st.n % 60 == 1:
			travel(area)
		return st.n > 400 and fail('%s: could not reach %s' % (ident, area))
	if dlg.is_engaged():
		return 0
	if not hasattr(st, 'sid'):
		st.sid, src = npc_script(ident, area[-6:])     # (IWD2 travel keys carry an I2 prefix)
		if st.sid is None:
			return fail('no converted %s in %s' % (ident, area))
		npc, to, goals = dlg_graph(st.sid, src, goal)
		st.goals, st.dist, st.talks = goals, E.dist_to_goal(npc, to, goals), 0
		log('TALK %s sid %d goal %r: %d goal replies' % (ident, st.sid, goal, len(goals)))
	if st.talks >= talks:
		if force and st.n % 40 == 30:
			set_var(force[0], force[1]); ST.setdefault('shortcuts', []).append('%s=%d' % force)
			log('SHORTCUT %s: %s not reached after %d conversations: set %s = %d' % (ident, goal, talks, force[0], force[1]))
			return 1
		return not force and fail('%s: %s not reached after %d conversations' % (ident, goal, talks))
	if st.n % 40 == 10:
		o = find_obj(st.sid)
		if o == OBJ_HANDLE_NULL:
			return st.n > 400 and fail('%s (sid %d) not found' % (ident, st.sid))
		x, y = location_to_axis(o.location)
		lx, ly = location_to_axis(game.leader.location)
		if max(abs(lx - x), abs(ly - y)) > 6:
			for i, pc in enumerate(game.party):
				pc.move(location_from_axis(x + 1 + i % 2, y + 2 + i // 2))
		TALK['cur'] = {'sid': st.sid, 'goals': st.goals, 'dist': st.dist, 'visits': {}, 'replies': 0, 'hit': 0}
		st.talks += 1
		log('TALK %s #%d (%s)' % (ident, st.talks, location_to_axis(o.location)))
		o.object_script_execute(game.leader, san_dialog)
	return 0

def fail(msg):
	ST['fail'] = msg; log('ANOMALY ' + msg)
	return 1

def step_newgame(st):
	m = get_current_map()
	if st.n == 1:
		log('NEW GAME started on map %d, party %d' % (m, len(game.party)))
		try:
			import __main__; __main__.cheats.kos = 0
		except Exception:
			pass
	if dlg.is_engaged():
		ST['greeted'] = 1            # Hrothgar walks up and talks right away (his EHHROTHT script)
	if st.n == 60:
		shot('newgame_%d' % m)
	return st.n > 80

def step_greet(st):
	'''the new-game opening: Hrothgar walks up and talks (his EHHROTHT script); answer with the first replies'''
	if dlg.is_engaged():
		st.seen = 1
		return 0
	if (getattr(st, 'seen', 0) or ST.get('greeted')) and st.n > 20:
		log('GREET done (Know_Hrothgar %d, Join_Posse %d)' % (V('Know_Hrothgar'), V('Join_Posse'))); return 1
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
		if st.n % 60 == 1:
			travel('AR1200')
		return st.n > 400 and fail('could not reach AR1200')
	import ie_travel_data as D
	trig = [t for t in D.AREAS['AR1200'].get('triggers', []) if t.get('module') == 'ie_bcs_caratrg1_area']
	if not trig:
		return fail('no CARATRG1 trigger in AR1200')
	if not hasattr(st, 'at'):
		xs, ys = zip(*trig[0]['poly'])
		st.at = (int(sum(xs) / len(xs)), int(sum(ys) / len(ys))); st.t0 = st.n
		log('CARAVAN walking into CARATRG1 at %s' % (st.at,))
		game.fade_and_teleport(0, 0, 0, area_map('AR1200'), st.at[0] - 6, st.at[1] - 6)
	if st.n == st.t0 + 40:
		for i, pc in enumerate(game.party):
			pc.move(location_from_axis(st.at[0] + i % 2, st.at[1] + i // 2))
	return st.n > st.t0 + 900 and fail('Caravan_Quest stays %d at CARATRG1' % V('Caravan_Quest'))

def step_ar2000(st):
	if get_current_map() == area_map('AR2000'):
		st.arr = getattr(st, 'arr', st.n)
		if st.n == st.arr + 80:
			shot('ar2000')
		if st.n >= st.arr + 120:
			log('SUMMARY CH1 PASS: AR2000 reached (CHAPTER %d, AR2000_INIT %d, AR2000_visited %d)' % (
				V('CHAPTER'), V('AR2000_INIT'), V('AR2000_visited')))
			return 1
		return 0
	return st.n > 1200 and fail('no jump to AR2000 after the departure talk')

STEPS = [
	('newgame', step_newgame),
	('greet', step_greet),
	('posse', lambda st: talk_step(st, 'hrothgar', 'AR1006', r'"Caravan_Quest", "GLOBAL", 1\)|"Know_Hrothgar", "GLOBAL", 1\)',
	                               lambda: V('Caravan_Quest') >= 1)),
	('caravan', step_caravan),
	('list', lambda st: talk_step(st, 'hrothgar', 'AR1006', r'GiveItemCreate\(c, "List"', lambda: V('Supply_Quest') >= 1)),
	('pomab', lambda st: talk_step(st, 'pomab', 'AR1007', r'TakePartyItem\(c, "List"', lambda: V('Supply_Quest') >= 2)),
	('depart', lambda st: talk_step(st, 'hrothgar', 'AR1006', r'StartCutScene\(c, "EHHrothM"',
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
	if st.n == 40:
		travel('I2AR1000')
	if st.n == 140:
		shot('targos_docks')
	return st.n > 160

def hostiles():
	out = []
	for o in game.obj_list_vicinity(game.leader.location, OLC_CRITTER):
		if o in game.party or o.is_unconscious() or o.leader_get() != OBJ_HANDLE_NULL:
			continue
		try:
			if not o.is_friendly(game.leader):
				out.append(o)
		except Exception:
			pass
	return out

def step_palisade(st):
	"""Goblins_Attack_Palisade 1: Shawford's cutscene (12cWar0/2) and AR1200.BCS start the battle at the palisade.
	Let it run ~30 s (shot), then the kill helper: every hostile critter near the party dies, until none are left."""
	if dlg.is_engaged():
		return 0
	if get_current_map() != area_map('I2AR1200'):
		if st.n % 100 == 50:
			travel('I2AR1200')
		return st.n > 1200 and fail('palisade: not in AR1200')
	st.t0 = getattr(st, 't0', 0) + 1
	if st.t0 == 300:
		shot('palisade')
	if st.t0 > 400 and st.t0 % 20 == 0:
		h = hostiles()
		if h:
			log('KILL %d hostiles: %s' % (len(h), ', '.join(o.description for o in h[:8])))
			for o in h:
				o.critter_kill()
			st.kills = getattr(st, 'kills', 0) + len(h)
		elif st.t0 > 700:
			log('PALISADE over: %d killed; Goblins_Attack_Palisade %d' % (getattr(st, 'kills', 0), V('Goblins_Attack_Palisade')))
			return 1
	return st.t0 > 2500 and fail('palisade: hostiles keep coming')

def step_end2(st):
	sc = ST.get('shortcuts')
	log('SUMMARY IWD2 CH1 %s: Shaengarne_Quest %d AR2000_Revealed %d (AR2000 is reached by the worldmap and is '
	    'not converted for IWD2: the run ends here)%s' % ('PASS' if not sc else 'END WITH SHORTCUTS', V('Shaengarne_Quest'),
	    V('AR2000_Revealed'), ' shortcuts: ' + ', '.join(sc) if sc else ''))
	return 1

STEPS2 = [
	('newgame', step_newgame2),
	('shawford0', lambda st: talk_step(st, '12shawfo', 'I2AR1201', r'"Lumber_Quest", "GLOBAL", 1\)', lambda: V('Lumber_Quest') >= 1)),
	# Shawford offers the arrow quest once the lumber quest is done (Crane_Wheel) or given up: Olap, at the palisade
	('olap', lambda st: talk_step(st, '12olap', 'I2AR1200', r'"Lumber_Quest_Aborted", "GLOBAL", 1\)',
	                              lambda: V('Lumber_Quest_Aborted') >= 1 or V('Crane_Wheel') > 0, ('Lumber_Quest_Aborted', 1), 1)),
	('shawford1', lambda st: talk_step(st, '12shawfo', 'I2AR1201', r'"Arrow_Quest", "GLOBAL", 1\)', lambda: V('Arrow_Quest') >= 1, ('Arrow_Quest', 1))),
	('deirdre', lambda st: talk_step(st, '11deird', 'I2AR1102', r'"Arrow_Quest", "GLOBAL", 3\)', lambda: V('Arrow_Quest') >= 3, ('Arrow_Quest', 3))),
	('shawford2', lambda st: talk_step(st, '12shawfo', 'I2AR1201', r'"Dead_Goblin_Quest", "GLOBAL", 1\)', lambda: V('Dead_Goblin_Quest') >= 1, ('Dead_Goblin_Quest', 1))),
	('koluhm', lambda st: talk_step(st, '11koluhm', 'I2AR1107', r'"Dead_Goblin_Quest", "GLOBAL", [2-5]\)', lambda: V('Dead_Goblin_Quest') >= 2, ('Dead_Goblin_Quest', 2))),
	('shawford3', lambda st: talk_step(st, '12shawfo', 'I2AR1201', r'"Palisade_Iron_Collar_Quest", "GLOBAL", 1\)',
	                                   lambda: V('Palisade_Iron_Collar_Quest') >= 1, ('Palisade_Iron_Collar_Quest', 1))),
	('geoffrey', lambda st: talk_step(st, '10black', 'I2AR1003', r'"Palisade_Iron_Collar_Quest", "GLOBAL", 2\)',
	                                  lambda: V('Palisade_Iron_Collar_Quest') >= 2, ('Palisade_Iron_Collar_Quest', 2))),
	('shawford4', lambda st: talk_step(st, '12shawfo', 'I2AR1201', r'"Goblins_Attack_Palisade", "GLOBAL", 1\)',
	                                   lambda: V('Goblins_Attack_Palisade') >= 1, ('Goblins_Attack_Palisade', 1))),
	('palisade', step_palisade),
	('ulbrec', lambda st: talk_step(st, '11ulbrec', 'I2AR1101', r'"Shaengarne_Quest", "GLOBAL", 1\)', lambda: V('Shaengarne_Quest') >= 1, ('Shaengarne_Quest', 1))),
	('end', step_end2),
]
STATUS = {'iwd': ('Join_Posse', 'Caravan_Quest', 'Supply_Quest'),
          'iwd2': ('Lumber_Quest', 'Arrow_Quest', 'Dead_Goblin_Quest', 'Palisade_Iron_Collar_Quest', 'Goblins_Attack_Palisade', 'Shaengarne_Quest')}
GAME = {'g': 'iwd'}
ST = {'i': 0, 'steps': None, 'fail': None}

def gs_ch1(slot):
	if not len(game.party):
		return 0
	if ST['steps'] is None:
		steps = STEPS2 if GAME['g'] == 'iwd2' else STEPS
		ST['steps'] = [Step(k, fn=f) for k, f in steps]
		fr = os.environ.get('IWDAP_CH1_FROM')     # resume from a save made on the way (e.g. depart)
		if fr:
			ST['i'] = [k for k, f in steps].index(fr); log('RESUME at step %s (map %d)' % (fr, get_current_map()))
		try:
			import ie_travel; ie_travel.start()
		except Exception as e:
			log('travel start: %s' % e)
	if ST['i'] >= len(ST['steps']) or ST['fail']:
		if not ST.get('done'):
			ST['done'] = 1
			if ST['fail']:
				log('SUMMARY CH1 FAIL at step %s: %s' % (ST['steps'][min(ST['i'], len(ST['steps']) - 1)].kind, ST['fail']))
			log('DONE')
		return 0
	st = ST['steps'][ST['i']]
	st.n += 1
	if st.n == 1 or st.n % 100 == 0:
		log('STEP %s n=%d map %d dlg %d %s' % (st.kind, st.n, get_current_map(), dlg.is_engaged(),
			' '.join('%s %d' % (v, V(v)) for v in STATUS[GAME['g']])))
	try:
		done = st.fn(st)
	except Exception as e:
		import traceback; done = fail('step %s raised %s %s' % (st.kind, e, traceback.format_exc()))
	if done and not ST['fail']:
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

def setup_playtester(autoplayer, which='iwd'):
	GAME['g'] = which
	E.configure('targos' if which == 'iwd2' else 'easthaven')
	cs = ControlScheme()
	add = [GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc',
	       'param2': (create_party_pool_add_pc_scheme, ())}) for i in range(4)]
	ch1 = [GoalState('ch1', gs_ch1, ('ch1', 100), ('ch1', 100))]
	if os.environ.get('IWDAP_CH1_FROM'):
		cs.__set_stages__([GoalStateStart(gs_ch1, ('ch1', 100), ('ch1', 100))] + ch1)
	else:
	  cs.__set_stages__([
		GoalStateStart(gs_quit_to_menu, ('press_quit', 1500), ('start', 500)),
		GoalState('press_quit', gs_press_widget, ('menu', 3000), (), {'param1': INGAME_QUIT}),
		GoalState('menu', gs_is_main_menu, ('new_game', 1000), ('menu', 500)),
		GoalState('new_game', gs_press_widget, ('normaldiff', 800), (), {'param1': WID_IDEN.NEW_GAME}),
		GoalState('normaldiff', gs_press_widget, ('align', 800), (), {'param1': WID_IDEN.NORMAL_DIFF}),
		GoalState('align', gs_press_widget, ('align_ok', 800), (), {'param1': WID_IDEN.TRUE_NEUTRAL_BTN_WID_ID}),
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
	E.no_movies()
	autoplayer.schedule(700)
