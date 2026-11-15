'''Offline tests for scr/iwd_easthaven_controller.py (IWD Easthaven / IWD2 Targos tours), run with python3:
    python3 tests/test_ie_tour.py                       # synthetic data only (no game data in the repo)
    IE_CORE=<converted module>/modules/ToEE_core python3 tests/test_ie_tour.py   # + the plan for a real local convert
The engine modules (toee, controllers, gamedialog...) are stubbed; the controller is Python 2.7 code kept 3-parseable.'''
import os, sys, types, tempfile, shutil, unittest
sys.dont_write_bytecode = True

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, '..', 'scr')

def stub_engine():
	toee = types.ModuleType('toee')
	for i, n in enumerate(['OLC_NPC', 'OLC_SCENERY', 'OF_OFF', 'san_dialog', 'obj_f_scenery_teleport_to',
	                       'qs_unknown', 'qs_mentioned', 'qs_accepted', 'qs_completed']):
		setattr(toee, n, [1, 2, 16, 9, 77, 0, 1, 2, 3][i])
	toee.OBJ_HANDLE_NULL = None
	game = types.ModuleType('toee.game'); game.quests = {}; game.party = []
	toee.game = game; toee.__all__ = [n for n in dir(toee) if not n.startswith('_')]
	sys.modules['toee'] = toee; sys.modules['toee.game'] = game
	c = types.ModuleType('controllers')
	c.ControlScheme = c.GoalState = c.GoalStateStart = object
	sys.modules['controllers'] = c
	cc = types.ModuleType('controller_callbacks_common')
	cc.get_current_map = lambda: 0; cc.dlg_reply = lambda i: None; cc.find_attack_lines = lambda ds: []; cc.is_ingame = lambda: 1
	sys.modules['controller_callbacks_common'] = cc
	u = types.ModuleType('utilities'); u.location_from_axis = lambda x, y: (x, y); u.location_to_axis = lambda l: l
	sys.modules['utilities'] = u
	sys.modules['gamedialog'] = types.ModuleType('gamedialog')

def load_controller(core, scenario):
	stub_engine()
	for m in ['iwd_easthaven_controller', 'ie_travel_data', 'ie_journal'] + [m for m in sys.modules if m.startswith('ie_bake_')]:
		sys.modules.pop(m, None)
	os.environ['IE2TOEE_CORE'] = core; os.environ['AUTOPLAYER_SCENARIO'] = scenario; os.environ.pop('IWDAP_LOG', None)
	sys.path[:0] = [SCR, os.path.join(core, 'scr')]
	import iwd_easthaven_controller as C
	C.log = lambda s: None
	return C

def write(path, s):
	if not os.path.isdir(os.path.dirname(path)):
		os.makedirs(os.path.dirname(path))
	open(path, 'w').write(s)

class Synthetic(unittest.TestCase):
	'''an invented 4-area module: town T (I2AR1000) -> house H (I2AR1001); town -> road R (I2AR1100) -> fort F (I2AR1200)'''
	def setUp(self):
		self.d = tempfile.mkdtemp(dir=os.environ.get('TEST_TMP', HERE))
		scr = os.path.join(self.d, 'scr')
		reg = lambda a, b: "{'name': 'To%s', 'poly': [[1, 1], [3, 1], [3, 3]], 'dest_area': '%s', 'dest_entrance': 'FR%s', 'dest_map': 0}" % (b[-4:], b, a[-4:])
		areas = {'I2AR1000': (5031, ['I2AR1001', 'I2AR1100']), 'I2AR1001': (5032, ['I2AR1000']),
		         'I2AR1100': (5038, ['I2AR1000', 'I2AR1200', 'I2AR1999']), 'I2AR1200': (5039, ['I2AR1100'])}
		src = 'AREAS = {%s}\n' % ', '.join(["'%s': {'map': %d, 'entrances': {%s}, 'regions': [%s]}" % (
			a, m, ', '.join(["'FR%s': [10, 10, 0]" % b[-4:] for b in ds]), ', '.join([reg(a, b) for b in ds])) for a, (m, ds) in areas.items()])
		src += 'BY_MAP = dict([(v["map"], k) for k, v in AREAS.items()])\n'
		write(os.path.join(scr, 'ie_travel_data.py'), src)
		write(os.path.join(scr, 'ie_journal.py'), "JOURNAL = {100: (150, 'quest'), 200: (151, 'quest'), 300: (152, 'quest')}\n")
		for a, ids in [('i2ar1000', ['town1']), ('i2ar1001', ['house1']), ('i2ar1100', []), ('i2ar1200', ['fort1'])]:
			write(os.path.join(scr, 'ie_bake_%s.py' % a), 'OBJS = {%s}\n' % ', '.join(["'g%d': {'k': 'npc', 'spec': {'ident': '%s'}}" % (i, x) for i, x in enumerate(ids)]))
		dlg = lambda n, a: '''def ie_a%d(npc, pc):\n    return rt.dlg_do(npc, pc, IDENT, AREA, [], journal=(%d, 'quest'))\n''' % (n, a)
		write(os.path.join(scr, 'py01500ie_town1.py'), dlg(11, 100) + 'def ie_c11(npc, pc):\n    return rt.dlg_cond(npc, pc, IDENT, AREA, lambda c: T.GlobalGT(c, "Fort_Done", "GLOBAL", 0))\n')
		write(os.path.join(scr, 'py01501ie_house1.py'), '''def ie_a21(npc, pc):\n    return rt.dlg_do(npc, pc, IDENT, AREA, [lambda c: A.AddJournalEntry(c, 200, "QUEST")], journal=None)\n''')
		write(os.path.join(scr, 'py01502ie_fort1.py'), dlg(31, 300).replace('[]', '[lambda c: A.SetGlobal(c, "Fort_Done", "GLOBAL", 1)]'))
		write(os.path.join(scr, 'py01503ie_nobody.py'), dlg(41, 999))   # not a quest strref: not a giver
		write(os.path.join(self.d, 'dlg', '01500ie_town1.dlg'), '{10}{Hi}{}{}{}{}{}\n{11}{Quest?}{}{1}{}{20}{}\n{12}{Bye}{}{1}{}{0}{}\n{20}{Go}{}{}{}{}{}\n{21}{Ok}{}{1}{}{0}{}\n')
		self.C = load_controller(self.d, 'targos')

	def tearDown(self):
		shutil.rmtree(self.d)
		sys.path[:] = [p for p in sys.path if not p.startswith(self.d) and p != SCR]

	def test_scenario(self):
		self.assertEqual(self.C.TOWN, 'I2AR1000')
		self.assertEqual(self.C.SCENARIOS[self.C.SCENARIO]['scheme'], 'iwd2_targos')

	def test_givers_both_journal_forms(self):
		g = self.C.load_quest_givers()
		self.assertEqual(sorted([v['ident'] for v in g.values()]), ['fort1', 'house1', 'town1'])
		self.assertEqual(g[1500]['quests'], {11: [(100, 150)]})
		self.assertEqual(g[1501]['quests'], {21: [(200, 151)]})

	def test_route(self):
		self.assertEqual(self.C.route('I2AR1000', 'I2AR1200'), ['I2AR1100', 'I2AR1200'])
		self.assertEqual(self.C.route('I2AR1200', 'I2AR1001'), ['I2AR1100', 'I2AR1000', 'I2AR1001'])
		self.assertEqual(self.C.route('I2AR1000', 'I2AR1999'), None)   # not converted

	def test_plan_route(self):
		self.C.build_plan()
		P = self.C.ST['plan']
		kinds = [(s.kind, getattr(s, 'area', None), s.kind == 'talk' and self.C.ST['givers'][s.sid]['ident'] or None) for s in P]
		# fort1 sets Fort_Done, which town1's quest reply needs: fort1 before town1; house1 stays after town1 (area order)
		one = [('goto', 'I2AR1200', None), ('talk', None, 'fort1'), ('goto', 'I2AR1000', None), ('talk', None, 'town1'),
		       ('goto', 'I2AR1001', None), ('talk', None, 'house1'), ('goto', 'I2AR1000', None)]
		self.assertEqual(kinds, [('start', None, None)] + one + one)
		self.assertEqual([getattr(s, 'group', None) for s in P[1:8]], [2, None, 2, None, 2, None, None])

	def test_plan_hub(self):   # Easthaven's travel: enter from the town, talk, leave to the town
		C = self.C; C.configure('easthaven'); C.TOWN = 'I2AR1000'
		C.build_plan()
		kinds = [(s.kind, getattr(s, 'area', None), getattr(s, 'frm', getattr(s, 'dest', None))) for s in C.ST['plan']]
		one = [('enter', 'I2AR1100', 'I2AR1000'), ('enter', 'I2AR1200', 'I2AR1100'), ('talk', None, None),
		       ('leave', 'I2AR1200', 'I2AR1100'), ('leave', 'I2AR1100', 'I2AR1000'),
		       ('talk', None, None),
		       ('enter', 'I2AR1001', 'I2AR1000'), ('talk', None, None), ('leave', 'I2AR1001', 'I2AR1000')]
		self.assertEqual(kinds, [('start', None, None)] + one + one)
		self.assertEqual([getattr(s, 'group', None) for s in C.ST['plan'][1:10]], [5, None, None, None, None, 1, 3, None, None])

	def test_goto_hops(self):
		C = self.C; import ie_travel_data as D
		cur = [5031]; clicks = []
		C.get_current_map = lambda: cur[0]
		C.icon_for = lambda a, b: (types.SimpleNamespace(location=(1, 1)), (D.AREAS[b]['map'], (10, 10)))
		def click(o, action):
			clicks.append(action); cur[0] = pending[0]; return 'ok'
		C.click_on_obj = click; C._loc = lambda o: (0, 0)
		C.game.scroll_to = lambda l: None
		C.game.leader = types.SimpleNamespace(distance_to=lambda o: 5.0, location=(0, 0))
		st = C.Step('goto', area='I2AR1200', timeout=150)
		pending = [None]
		for i in range(200):
			hop = getattr(st, 'hop', None)
			pending[0] = hop and D.AREAS[hop.area]['map'] or 5038
			if C.tick_goto(st):
				break
		self.assertEqual(cur[0], 5039); self.assertEqual(st.hops, 2); self.assertEqual(clicks, ['jump', 'jump'])

	def test_dlg_graph(self):
		npc, to = self.C.load_dlg_graph(1500)
		self.assertEqual(npc, {10: [11, 12], 20: [21]})
		self.assertEqual(self.C.dist_to_goal(npc, to, set([11])), {10: 0})

	def test_skip_label(self):
		C = self.C; C.build_plan(); C.ST['results'] = []
		st = [s for s in C.ST['plan'] if s.kind == 'talk' and s.sid == 1501][0]
		C.game.quests = {151: types.SimpleNamespace(state=0)}
		C.finish_talk(st, 0, skipped=1)
		self.assertEqual(C.ST['skipped'], {'house1': 1})

@unittest.skipUnless(os.environ.get('IE_CORE'), 'set IE_CORE to a local convert for the real-data plan')
class RealConvert(unittest.TestCase):
	def test_plan(self):
		core = os.environ['IE_CORE']
		scen = os.environ.get('IE_SCENARIO', 'targos')
		C = load_controller(core, scen)
		out = []; C.log = out.append
		C.build_plan()
		print('\n'.join([l for l in out if l.startswith(('GIVER', 'ORDER'))]))
		for s in C.ST['plan']:
			print('  %-5s %-10s %s' % (s.kind, getattr(s, 'area', ''), s.kind == 'talk' and C.ST['givers'][s.sid]['ident'] or getattr(s, 'frm', getattr(s, 'dest', ''))))
		self.assertTrue([s for s in C.ST['plan'] if s.kind == 'talk'])

if __name__ == '__main__':
	unittest.main()
