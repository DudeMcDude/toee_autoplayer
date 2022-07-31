from controller_ui_util import WID_IDEN
from toee import *
from controllers import ControlScheme, GoalState, ControllerBase
from controller_callbacks_common import *
from utilities import *
import autoui as aui
import controller_ui_util
import gamedialog as dlg

def cheat_buff():
	if game.leader != OBJ_HANDLE_NULL: # make us durable!!!
		for pc in game.party:
			if pc.obj_get_int(obj_f_hp_pts) < 500:
				pc.obj_set_int(obj_f_hp_pts, 500)
				pc.stat_base_set(stat_strength,32)
	return

def gs_master(slot):
	pt = Playtester.get_instance()
	if slot.state is None:
		slot.state = {
			'counter': 0,
			'rest_needed': False,
		}
	else:
		# print('master counter: ', slot.state['counter'])
		slot.state['counter'] += 1
	
	if gs_is_main_menu(slot):
		# pt.add_scheme( create_load_game_scheme(0), 'load_game' )
		# pt.push_scheme('load_game')
		pt.push_scheme('new_game')
		return 0
	
	if slot.state['counter'] >= 1 and slot.state['counter'] <= 300000:
		cheat_buff()
		if game.quests[18].state != qs_completed:
			pt.add_scheme( create_hommlet_scheme0(), 'hommlet0' )
			pt.push_scheme('hommlet0')
			return 0
		if game.quests[72].state == qs_unknown:
			pt.add_scheme( create_hommlet_scheme1(), 'hommlet1' )
			pt.push_scheme('hommlet1')
			return 0
		
		leader = game.leader
		if leader == OBJ_HANDLE_NULL:
			return 0
		
		game.areas[3] = 1 # nulb
		if leader.area == 1: # Hommlet
			if leader.map == 5001: # Hommlet main
				if slot.state['rest_needed']:
					slot.state['rest_needed'] = False
					pt.push_scheme('rest')
					return 0
				pt.push_scheme('goto_nulb')
				return 0
			# inside building
			pt.push_scheme('exit_building')
			if game.random_range(0,6) == 1:
				restup()
			return 0
		else: # outside Hommlet
			slot.state['rest_needed'] = True
			pt.push_scheme('goto_hommlet')
			return 0
		
				
	elif slot.state['counter'] == 2:
		# pt.add_scheme( create_load_game_scheme(1), 'load_game' )
		# pt.push_scheme('load_game')
		pass
	else:
		# pt.push_scheme('load_game')
		pass
	return 0

def setup_playtester(autoplayer):
	#type: (Playtester)->None
	autoplayer = autoplayer #type: ControllerBase
	# autoplayer.__logging__ = True
	from controller_console import ControllerConsole
	# autoplayer.console = ControllerConsole()
	autoplayer.add_scheme( create_new_game_scheme(), 'new_game' )
	autoplayer.add_scheme( create_load_game_scheme(), 'load_game' )
	autoplayer.add_scheme( create_true_neutral_scheme(), 'true_neutral_vig' )
	autoplayer.add_scheme( create_hommlet_scheme0(), 'hommlet0')
	autoplayer.add_scheme( create_ui_camp_rest_scheme(), 'ui_camp_rest' )
	autoplayer.add_scheme( create_rest_scheme(), 'rest' )

	autoplayer.add_scheme( create_shop_map_scheme(), 'shopmap' )
	autoplayer.add_scheme( create_master_scheme(), 'main' )
	autoplayer.add_scheme( create_goto_area('moathouse'), 'goto_moathouse' )
	autoplayer.add_scheme( create_goto_area('south hommlet'), 'goto_hommlet' )
	autoplayer.add_scheme( create_goto_area('nulb'), 'goto_nulb' )
	autoplayer.add_scheme( create_scheme_enter_building(None), 'exit_building' )
	
	autoplayer.set_dialog_handler(dialog_handler)
	autoplayer.set_combat_handler(combat_handler)
	
	autoplayer.push_scheme('main')
	print('Beginning scheme in 1 sec...')
	autoplayer.schedule(1000, real_time=1)
	return

def create_master_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalState('start', gs_master, ('end', 500) ),
		GoalState('end', gs_master, ('start', 500), ('start',500) )
	])
	return cs



class DialogHandler:
	cb = None
	presets = None
	__is_fixed_sequence__ = False
	def __init__(self, presets, cb = None ):
		self.presets = presets
		self.cb = cb
		if type(presets) is list or type(presets) is tuple:
			self.__is_fixed_sequence__ = True
		return
	
	@staticmethod
	def default_handler(ds,slot):
		dlg_reply(0)
		return 1
	
	def is_fixed_sequence(self):
		return self.__is_fixed_sequence__
	
	def do_fixed_sequence(self, ds, slot):
		#type: (dlg.DialogState, GoalSlot)->int
		if slot.__dialog_state__ is None:
			slot.__dialog_state__ = {
				'reply_counter': 0,
				'line_number': -1,
				}
		
		state = slot.__dialog_state__

		N = ds.reply_count
		cur_line = ds.line_number
		prev_line = state['line_number']
		if cur_line == prev_line:
			print("Repeating the same line??")
		state['line_number'] = cur_line
		
		replies = self.presets
		cur_idx = state['reply_counter']
		if cur_idx >= len(replies):
			print("Reply script shorter than actual dialog! currently at ", cur_idx)
			if dlg_reply_nonattack(ds):
				return 1
			dlg_reply(0)
			return 1
		
		cur_reply = replies[cur_idx]
		if cur_reply < N: # normal case
			state['reply_counter'] += 1
			dlg_reply(cur_reply)
			return 1
		
		# fallback
		print("Warning: bad reply ID!")
		state['reply_counter'] += 1
		dlg_reply(0)
		return 1
	
	def do_presets(self, ds, slot):
		#type: (dlg.DialogState, GoalSlot)->int
		if slot.__dialog_state__ is None:
			slot.__dialog_state__ = {
				'reply_counter': 0,
				'line_number': -1,
				}
			return 0
		state = slot.__dialog_state__
		
		reply_cb = self.cb #type: callable[ [dlg.DialogState, dict, dict], int]
		presets  = self.presets
		if presets is None:
			presets = {}
		
		if ds.line_number in presets:
			reply = presets[ds.line_number]
			dlg_reply(reply)
			return 1
		
		if reply_cb is not None:
			reply = reply_cb(ds, presets, state)
			dlg_reply(reply)
			return 1

		if dlg_reply_nonattack(ds):
			return 1
		dlg_reply(0)
		return 1

dialog_handler_dict = {
	91: DialogHandler( {1: 0, 10: 0, 20: 1, 50: 0, 60: 0, 70:0 , 580: 1,}), # Elmo
	228: DialogHandler([0,0,0,0,0,0,0]), # kent

	416: DialogHandler([0,0,1]) # std equipment chest
}

def dialog_handler(slot):
	#type: (GoalSlot)->int
	state = slot.__dialog_state__

	ds = dlg.get_current_state()
	script_id = ds.script_id
	print('handling dialog script ID: ', script_id)
	
	if not script_id in dialog_handler_dict:
		return DialogHandler.default_handler(ds, slot)
	
	handler = dialog_handler_dict[script_id]
	if handler.is_fixed_sequence():
		return handler.do_fixed_sequence(ds, slot)
	
	if handler.cb is None:
		return handler.do_presets(ds, slot)
	
	return handler.cb(ds, handler.presets, slot)

def combat_handler(slot):
	
	Playtester.get_instance().interrupt()

	def select_target(obj):
		vlist = game.obj_list_vicinity(obj.location, OLC_NPC)
		best_tgt = OBJ_HANDLE_NULL
		least_dist = 100000
		tgt_priority = []
		for tgt in vlist:
			if tgt.is_friendly(obj):
				continue
			if tgt.is_unconscious():
				continue
			flags = tgt.object_flags_get()
			if flags & OF_DONTDRAW:
				continue
			
			dist = tgt.distance_to(obj)
			if dist < 15:
				if obj.can_melee(tgt):
					dist = 0
			hp_pct = obj_percent_hp(tgt)
			tgt_priority.append( [tgt, dist, hp_pct])
		def sort_key(x):
			dist   = x[1]
			hp_pct = x[2]
			if dist == 0:
				return hp_pct
			return dist + 100
		
		if len(tgt_priority) > 0:
			tgt_priority.sort(key=sort_key)
			print('possible targets: [distance, hp_pct]', tgt_priority)
			return tgt_priority[0][0]
		return OBJ_HANDLE_NULL #best_tgt
	
	obj = game.leader
	if not game.combat_is_active():
		return 500
	if not (obj in game.party):
		return 500
	
	def can_cast(spell_enum, spell_class, spell_level):
		sp = PySpellStore( spell_enum , spell_class, spell_level)
		return obj.can_cast_spell(sp)

	import tpactions
	actor = tpactions.get_current_tb_actor()
	if obj != actor: # delay
		return 500
	
	act_seq_cur = tpactions.get_cur_seq()
	tgt = select_target(obj)
	if tgt == OBJ_HANDLE_NULL: # end turn for now..
		print('No target, ending turn')
		press_space()
		return 500

	if obj.is_performing():
		return 500
	# restup()
	if True: #obj == game.party[1]: # ariel
		result = obj.ai_strategy_execute(tgt)
		if result == 1:
			return 1000

	# if act_seq_cur.tb_status.hourglass_state >= 4: # Full action bar
	# 	print('Attacking ', tgt)
	# 	if can_cast(spell_magic_missile, stat_level_wizard | 0x80, 1):
	# 		obj.cast_spell(spell_magic_missile, tgt)
	# 		return 500
	# 	perform_action(D20A_UNSPECIFIED_ATTACK, obj, tgt, tgt.location)
	# 	return 500
	# if act_seq_cur.tb_status.hourglass_state >= 2: # Standard Action
	#     # todo
	#     pass
	# if act_seq_cur.tb_status.hourglass_state >= 1: # Move Action
	#     # todo
	#     pass
	print('Ending turn... ')
	press_space()
	return 300

#region callbacks
def gs_is_main_menu(slot):
	# todo expand this..
	wid = controller_ui_util.obtain_widget(WID_IDEN.MAIN_MENU_LOAD_GAME)
	if wid is None:
		# print('is_main_menu: false')
		return 0
	return 1

def gs_scan_get_widget_from_list(slot):
	#type: (GoalSlot)->int
	''' 
	param1 - widget identifier list\n
	param2 - condition callback. signature: cb(slot)->bool\n
	scheme_state { 'widget_scan': 
					{ 'idx': int, 
					  'found': bool, 
					  'wid_id': TWidgetIdentifier} 
				    }
	'''
	wid_list = slot.param1
	condition = slot.param2
	state = slot.get_scheme_state()
	
	state['widget_scan'] = {
			'idx': -1,
			'found': False,
			'wid_id': None
		}
	# todo: scrolling

	for idx in range(len(wid_list)):
		state['widget_scan']['idx'] = idx
		# print('scan_get_widget: idx %d' % idx)
		try:
			# print('trying to obtain widget: %s' % str(wid_list[idx]))
			wid = controller_ui_util.obtain_widget(wid_list[idx])
		except Exception as e:
			wid = None
			# print('Failed!')
			print(str(e))
			# print(str(e.__traceback__))

		if wid is None:
			# print('Wid is None!')
			continue
		# print('obtained: %s, now checking condition' % str(wid))
		if callable(condition):
			res = condition(slot)
			if res:	
				state['widget_scan']['found'] = True
				state['widget_scan']['wid_id'] = wid_list[idx]
				# print(str(wid))
				return 1
			# else:
				# print('condition failed!')
		# else:
			# print('what happened to you, condition? %s' % str(condition))
	
	return 1
	

def gs_move_mouse_to_object(slot):
	# print('gs_move_mouse_to_object')
	# type: (GoalSlot)->int
	obj = get_object( slot.param1 )
	if obj is None:
		return 0 # todo handle this..
	controller_ui_util.move_mouse_to_obj(obj)
	return 1

def gs_scroll_to_tile_and_click(slot):
	#type: (GoalSlot)->int
	# todo make sure the tile is clear first :)
	state = slot.state
	if state is None:	
		slot.state = {
			'scrolled': False,
			'hovered': False,
			'clicked': False,
		}
	loc = slot.param1

	if not slot.state['scrolled']:
		center_screen_on(loc)
		slot.state['scrolled'] = True
		return 0

	if not slot.state['hovered']:
		controller_ui_util.move_mouse_to_loc(loc)
		slot.state['hovered']=True
		return 0
	if not slot.state['clicked']:
		click_mouse()
		return 1
	return 0


def gs_click_on_object(slot):
	# print('gs_click_on_object')
	state = slot.state
	if state is None:	
		slot.state = {
			'hovered': False,
			'clicked': False,
		}
	
	if not slot.state['hovered']:
		result = gs_move_mouse_to_object(slot) 
		if result:
			slot.state['hovered']=True
			return 0
		return 0
		#todo handle failures...
	if not slot.state['clicked']:
		# print('\t clicking!')
		click_mouse()
		return 1
	return 0

def gs_click_to_talk(slot):
	''' Similar to gs_click_on_object, except it immediately disables the automatic dialogue handler (because it could happen right away)
	'''
	Playtester.get_instance().dialog_handler_en(False) # halt the automatic dialogue handler
	return gs_click_on_object(slot)
	

def gs_handle_dialogue(slot):
	# param1 - callback for handling current dialogue state
	if slot.state is None:
		slot.state = {
			'was_in_dialog': False,
			'reply_counter': 0,
			'line_number': -1,
			'wait_for_dialog_counter': 0
			}
		Playtester.get_instance().dialog_handler_en(False)
		return 0
	

	if dlg.is_engaged():
		slot.state['was_in_dialog'] = True
	else:
		if slot.state['was_in_dialog']:
			Playtester.get_instance().dialog_handler_en(True)
			return 1
		else:
			slot.state['wait_for_dialog_counter'] += 1
			return 0
	reply_cb = slot.param1 #type: callable[ [dlg.DialogState, dict, dict], int]
	presets  = slot.param2
	if presets is None:
		presets = {}
	if reply_cb is None:
		reply_cb = dialog_handler	
	
	ds = dlg.get_current_state()

	if ds.line_number in presets:
		reply = presets[ds.line_number]
		dlg_reply(reply)
		return 0
	
	reply = reply_cb(ds, presets, slot.state)
	dlg_reply(reply)
	return 0


#endregion



def create_party_pool_add_pc_scheme():
	cs = ControlScheme()
	wid_list = WID_IDEN.CHAR_POOL_CHARS

	def check_widget(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		idx = state['widget_scan']['idx']
		wid_list = slot.param1
		wid_id = wid_list[idx]
		# print('checking widget:', wid_id)
		wid = controller_ui_util.obtain_widget(wid_id)
		if wid is None:
			# print('not found')
			return False
		if not wid.is_button_enabled:
			# print('button not enabled')
			return False
		
		# print('rendered text: ', wid.rendered_text)
		if wid.rendered_text.lower().find('has joined') >= 0:
			# print('has already joined')
			return False
		if wid.rendered_text.lower().find('not compat') >= 0:
			# print('not compatible')
			return False
		# print('ok!')
		
		return True

	def gs_found(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		if state['widget_scan']['found']:
			# print('found it', slot.state_prev['idx'])
			return 1
		return 0

	cs.__set_stages__([
		
		GoalState('start', gs_scan_get_widget_from_list, ('check_result', 100), (), {'param1': wid_list, 'param2': check_widget } ),
		GoalState('check_result', gs_found, ('press_char_btn', 100), ('end', 300),  ),
		GoalState('press_char_btn', gs_press_widget, ('press_add', 200), (), {'param1': None } ),
		
		GoalState('press_add', gs_press_widget, ('end', 200), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('end', gs_wait_cb, ('end', 0), )
	])
	return cs

def create_new_game_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalState('start', gs_press_widget, ('normaldiff', 500), (), {'param1': WID_IDEN.NEW_GAME } ),
		GoalState('normaldiff', gs_press_widget, ('select_true_neutral_alignment', 500), (), {'param1': WID_IDEN.NORMAL_DIFF } ),
		GoalState('select_true_neutral_alignment', gs_press_widget, ('party_alignment_accept', 800), (), {'param1': WID_IDEN.TRUE_NEUTRAL_BTN_WID_ID } ),
		GoalState('party_alignment_accept', gs_press_widget, ('add_party_members', 300), (), {'param1': WID_IDEN.PARTY_ALIGNMENT_ACCEPT_BTN } ),
	]+
		# GoalState('should_add_party_mem', )
		GoalState.from_sequence('add_party_members', [
			GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )}),
			GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )}),
			GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )}),
			GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )}),
			GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )}),
			GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )})
		], ('char_pool_begin_adventure', 300), ('char_pool_begin_adventure', 300))
		+[
		GoalState('char_pool_begin_adventure', gs_press_widget, ('do_shopmap', 100), (), {'param1': WID_IDEN.CHAR_POOL_BEGIN_ADVENTURE } ),
		GoalState('do_shopmap', gs_push_scheme, ('end', 100), (), {'param1': 'shopmap'} ),
		GoalState('end', gs_wait_cb, ('end', 100), (), ),
	])
	return cs

def create_load_game_scheme(save_idx = 1):
	cs = ControlScheme()
	if save_idx < 0:
		save_idx = 0
	if save_idx > 7:
		save_idx = 7
	
	load_entry_wid_id = WID_IDEN.LOAD_GAME_ENTRY_1
	load_entry_wid_id[-1] = save_idx
	
	cs.__set_stages__( [
		GoalState('start', gs_is_main_menu, ('main_menu_load', 100), ('ingame_load', 100) ),

		GoalState('main_menu_load', gs_press_widget, ('load_game_entry_1', 200), (), {'param1': WID_IDEN.MAIN_MENU_LOAD_GAME}),
		GoalState('load_game_entry_1', gs_press_widget, ('load_it', 200), (), {'param1': load_entry_wid_id}),
		GoalState('load_it', gs_press_widget, ('end', 200), (), {'param1': WID_IDEN.LOAD_GAME_LOAD_BTN}),
		
		GoalState('ingame_load', gs_is_widget_visible, ('ingame_press_load', 200), ('ingame_bring_up_menu', 100), {'param1': WID_IDEN.INGAME_LOAD_GAME}),
		GoalState('ingame_bring_up_menu', gs_press_key, ('ingame_load', 100), ('ingame_load', 100) , params={'param1': DIK_ESCAPE}),
		
		GoalState('ingame_press_load', gs_press_widget, ('ingame_load_game_entry', 200), (), {'param1': WID_IDEN.INGAME_LOAD_GAME}),
		GoalState('ingame_load_game_entry', gs_press_widget, ('load_it', 200), (), {'param1': load_entry_wid_id}),
		GoalState('load_it', gs_press_widget, ('end', 200), (), {'param1': WID_IDEN.LOAD_GAME_LOAD_BTN}),
		
		
		GoalState('end', gs_wait_cb, ('end', 200), ),
	])
	return cs

def create_shop_map_scheme():
	cs = ControlScheme()
	std_chest_dlg_choices = [0, 0,1]
	cs.__set_stages__(
		[ GoalState('start', gs_wait_cb, ('equipment_chests', 300) ), ] +
		GoalState.from_sequence('equipment_chests', [
			GoalState('', gs_click_to_talk, ('', 100), (), {'param1': {'proto': 14575, } } ),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': std_chest_dlg_choices } ),
		], ('game_portal', 500), ()) +
		GoalState.from_sequence('game_portal', [
			GoalState('', gs_click_to_talk, ('', 100), (), {'param1': {'proto': 14758, } } ),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': std_chest_dlg_choices } ),
		], ('do_vignette', 500), ()) +

		[ GoalState('do_vignette', gs_push_scheme, ('end', 100), (), {'param1': 'true_neutral_vig'} ),
		GoalState('end', gs_wait_cb, ('end', 100) ),]
		)
	return cs

def create_true_neutral_scheme():
	cs = ControlScheme()
	
	druid_dlg_choices = [0, 0,0,0,0]
	cs.__set_stages__( 
		[GoalState('start', gs_wait_cb, ('talk_jaroo', 500)),] +
		GoalState.from_sequence('talk_jaroo', [
			GoalState('', gs_scroll_to_tile, ('', 3500), params = {'param1': (488, 474) }),
			GoalState('', gs_click_to_talk, ('', 3000), params = {'param1': {'proto': 14322, 'location': location_from_axis(488, 474)}} ),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': druid_dlg_choices } ),
		], ('do_hommlet', 500)) + 
		[GoalState('do_hommlet', gs_push_scheme, ('end', 100), (), {'param1': 'hommlet0'} ),
		GoalState('end', gs_wait_cb, ('end', 100) ), ]
	)
	return cs

def create_rest_scheme():
	WELCOME_WENCH_MAP_ID = 5007; WELCOME_WENCH_ENTRANCE_LOC = (619, 404)
	def init_rest_scheme(slot):
		#type: (GoalSlot)->int
		state =slot.get_scheme_state()

		loc = (500,500)
		tgt_map_id = -1
		if game.leader.map == 5001: # Hommlet
			loc        = WELCOME_WENCH_ENTRANCE_LOC
			tgt_map_id = WELCOME_WENCH_MAP_ID

		args = ( loc, tgt_map_id )
		
		state['push_scheme'] = {
			'id': 'goto_building',
			'callback': (create_scheme_enter_building, args)
		}
		state['target_map'] = tgt_map_id
		return 1
	
	def check_map(slot):
		#type: (GoalSlot)->int
		state =slot.get_scheme_state()

		if state['target_map'] == game.leader.map: 
			return 1
		if state['target_map'] == -1:
			import random_encounter
			sleep_safety = random_encounter.can_sleep()
			if sleep_safety == SLEEP_DANGEROUS or sleep_safety == SLEEP_SAFE:
				return 1
		return 0

	cs = ControlScheme()
	cs.__set_stages__([
		GoalState('start', init_rest_scheme, ('check_map', 100),  ),
		GoalState('check_map', gs_condition, ('start_resting', 100), ('go_building', 100), params={'param1': check_map} ),
		
		GoalState('go_building', gs_create_and_push_scheme, ('start_resting', 500),('end', 100)  ),
		GoalState('start_resting', gs_push_scheme, ('end', 500),  params={'param1': 'ui_camp_rest',  } ),
		
		GoalState('end', gs_wait_cb, ('end', 100),  ),
	])
	return cs

def create_ui_camp_rest_scheme():
	cs = ControlScheme()
	cs.__set_stages__(
		[
		GoalState('start', gs_wait_cb, ('click_camp', 100), ) ,] +
		GoalState.from_sequence('click_camp', [
		GoalState('', gs_press_widget, ('', 500), (), {'param1': WID_IDEN.UTIL_BAR_CAMP_BTN } ),
		GoalState('', gs_press_widget, ('', 1500), (), {'param1': WID_IDEN.CAMPING_UI_REST_BTN } ),
		], ('end', 100) ) + 
		[GoalState('end', gs_wait_cb, ('end', 100), ) ,	])
	return cs

def create_scheme_go_to_tile( loc ):
	if type(loc) is tuple:
		loc = location_from_axis( *loc )
	cs = ControlScheme()
	def is_moving_check(slot):
		if slot.state is None: # initialize locs
			slot.state = {}
			for n in range(len(game.party)):
				pc = game.party[n]
				slot.state['pc%d' % n] = pc.location
			slot.state['map'] = game.leader.map
			return 1
		
		result = 0
		for n in range(len(game.party)):
			pc = game.party[n]
			key = 'pc%d' % n
			if key in slot.state:
				prev_loc = slot.state[key]	
				if prev_loc != pc.location:
					result = 1
					slot.state['pc%d' % n] = pc.location
			else:
				slot.state[key] = pc.location
		return result

	def arrived_at_check(slot):
		DIST_THRESHOLD = 15
		for pc in game.party:
			if pc.distance_to(loc) > DIST_THRESHOLD:
				return False
		return True
	
	cs.__set_stages__([
		GoalState('start', gs_select_all, ('check_loc', 500), ),
		GoalState('check_loc', gs_condition, ('just_scroll', 100), ('scroll_and_click', 100), params={'param1': arrived_at_check}),
		GoalState('just_scroll', gs_center_on_tile, ('end', 700), params = {'param1': loc }),
		
		GoalState('scroll_and_click', gs_scroll_to_tile_and_click, ('is_moving_loop', 700), params = {'param1': loc }),
		# GoalState('arrived_at', gs_condition, ('end', 0)        , ('is_moving_loop', 100), params={'param1': arrived_at_check}),
		GoalState('is_moving_loop' , gs_condition, ('is_moving_loop', 800), ('check_arrived', 100), params={'param1': is_moving_check}),
		GoalState('check_arrived', gs_condition, ('end', 0), ('start', 100), params={'param1': arrived_at_check}),
		
		GoalState('end', gs_wait_cb, ('end', 10), ),
	])
	return cs

def create_scheme_enter_building( loc, tgt_map_id = None ): #TODO
	cs = ControlScheme()
	DOOR_ICON_PROTO = 2011
	def check_tgt_map(slot):
		if tgt_map_id is None or tgt_map_id == -1:
			return 1
		if game.leader == OBJ_HANDLE_NULL:
			return 0
		if game.leader.map == tgt_map_id:
			return 0
		return 1
	if loc is None:
		cs.__set_stages__([
			GoalState('start', gs_condition, ('click_door_icon', 100), ('end', 100), params={'param1': check_tgt_map}),
			# GoalState('go_to_loc', gs_create_and_push_scheme, ('click_door_icon', 500), params = {'param1': 'goto', 'param2': (create_scheme_go_to_tile, ( loc, ) ) }),
			GoalState('click_door_icon', gs_click_on_object, ('map_change_loop', 100), params={'param1': {'proto': DOOR_ICON_PROTO} }),
			
			GoalState('map_change_loop', gs_condition_map_change, ('end', 500), ),
			GoalState('end', gs_wait_cb, ('end', 500), ),	
		])
	else:
		cs.__set_stages__([
			GoalState('start', gs_condition, ('go_to_loc', 100), ('end', 100), params={'param1': check_tgt_map}),
			GoalState('go_to_loc', gs_create_and_push_scheme, ('click_door_icon', 500), params = {'param1': 'goto', 'param2': (create_scheme_go_to_tile, ( loc, ) ) }),
			GoalState('click_door_icon', gs_click_on_object, ('map_change_loop', 100), params={'param1': {'proto': DOOR_ICON_PROTO, 'loc': loc} }),
			
			GoalState('map_change_loop', gs_condition_map_change, ('end', 500), ),
			GoalState('end', gs_wait_cb, ('end', 500), ),
		])
	return cs

def create_goto_area(area_name):
	#type: (str)->ControlScheme

	# TODO: handle if not outdoors... (seek exit or sthg like that)
	# TODO: what if we're already there? currently handle this above...
	cs = ControlScheme()
	wid_list = WID_IDEN.WORLDMAP_UI_SELECTION_BTNS

	def gs_goto_area_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['map_change_check'] = {'map': game.leader.map}
		return 1
	
	def check_widget(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		idx = state['widget_scan']['idx']
		wid_list = slot.param1
		wid_id = wid_list[idx]
		print('checking widget:', wid_id)
		wid = controller_ui_util.obtain_widget(wid_id)
		if wid is None:
			# print('not found')
			return False
		if not wid.is_button_enabled:
			# print('button not enabled')
			return False
		print('obtained widget: %s'%str(wid))
		print('rendered text: ', wid.rendered_text)
		if wid.rendered_text.lower().find(area_name.lower()) >= 0:
			return True
		return False

	def gs_found(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		if state['widget_scan']['found']:
			# print('found it', slot.state_prev['idx'])
			return 1
		return 0
	
	
	def gs_survival_check_active(slot):
		wid = controller_ui_util.obtain_widget(WID_IDEN.RND_ENC_UI_ACCEPT_BTN)
		if wid is None:
			return 0
		return 1
	def gs_encounter_exit_dialog_active(slot):
		wid = controller_ui_util.obtain_widget(WID_IDEN.RND_ENC_EXIT_UI_ACCEPT_BTN)
		if wid is None:
			return 0
		return 1
	def gs_is_townmap_active(slot):
		wid = controller_ui_util.obtain_widget(WID_IDEN.TOWNMAP_UI_WORLD_BTN)
		if wid is None:
			return 0
		return 1


	cs.__set_stages__(
		[
			GoalState('start', gs_goto_area_init, ('check_outdoors',100 ), ),
			GoalState('check_outdoors', gs_condition, ('click_map', 500), ('end', 100), params={'param1': lambda slot: game.is_outdoor()} ) ,
		
			GoalState('click_map', gs_press_widget, ('exiting_random_encounter_check', 500), (), {'param1': WID_IDEN.UTIL_BAR_MAP_BTN } ),
			GoalState('exiting_random_encounter_check', gs_condition, ('press_encounter_exit', 100), ('is_townmap_ui', 100), params={'param1':gs_encounter_exit_dialog_active }),
			GoalState('press_encounter_exit', gs_press_widget, ('is_townmap_ui', 100), params={'param1':WID_IDEN.RND_ENC_EXIT_UI_ACCEPT_BTN }),
			
			GoalState('is_townmap_ui', gs_condition, ('press_worldmap', 500), ('find_acq_loc_btn', 100), params={'param1': gs_is_townmap_active} ) ,
			GoalState('press_worldmap', gs_press_widget, ('find_acq_loc_btn', 600), (), {'param1': WID_IDEN.TOWNMAP_UI_WORLD_BTN } ),

		
			GoalState('find_acq_loc_btn', gs_scan_get_widget_from_list, ('check_result', 100), (), {'param1': wid_list, 'param2': check_widget } ),
			GoalState('check_result', gs_found, ('press_acq_loc_btn', 100), ('end', 300),  ),
			GoalState('press_acq_loc_btn', gs_press_widget, ('wait_loop', 200), (), {'param1': None } ),

			GoalState('wait_loop', gs_wait_cb, ('wait_for_map_change', 500), ) ,	
			GoalState('wait_for_map_change', gs_condition_map_change, ('end', 100), ('survival_check_window', 100), ) ,
			GoalState('survival_check_window', gs_condition, ('press_encounter_accept', 100), ('wait_loop', 100), params={'param1': gs_survival_check_active} ) ,
			GoalState('press_encounter_accept', gs_press_widget, ('end', 100), params={'param1':WID_IDEN.RND_ENC_UI_ACCEPT_BTN }),

			GoalState('end', gs_wait_cb, ('end', 500), ) ,	
		])
	return cs

def create_hommlet_scheme1():
	cs = ControlScheme()
	JAROO_DOOR_ICON_LOC = (614, 518)
	GROVE_ENTRANCE_LOC = (620, 520)
	JAROO_EXIT_ICON_LOC = (495, 478)

	def jaroo_handler(ds, presets, slot):
		N = ds.reply_count
		npc_line = ds.line_number
		def find_target_line_reply(target_line_id):
			for idx in range(N):
				if ds.get_npc_reply_id(idx) == target_line_id: # why haven't you reported
					return idx
			return -1
		
		preferred_target_lines = [
			318, #why haven't you reported to hrudek
			346 # cleared moathouse
		]

		for line in preferred_target_lines:
			idx = find_target_line_reply(line)
			if idx >= 0: return idx

		if npc_line == 1: # greetins
			return 0
		if npc_line == 80:
			idx = find_target_line_reply(0)
			if idx >= 0: return idx
		
		return 0 # default
		

	cs.__set_stages__(
		[
		GoalState('start', gs_condition, ('go_jaroo', 100), ('start2', 100), params={'param1': lambda slot: game.leader.map == 5001}),
		GoalState('start2', gs_condition, ('handle_jaroo', 100), ('start', 100), params={'param1': lambda slot: game.leader.map == 5042}), # wait until this is fulfilled
		
		GoalState('go_jaroo', gs_create_and_push_scheme, ('handle_jaroo', 100), params={'param1': 'go_grove', 'param2': (create_scheme_enter_building, (GROVE_ENTRANCE_LOC,5042) ) })
		] +
		
		GoalState.from_sequence('handle_jaroo', [
			GoalState('', gs_click_to_talk, ('', 1500), params = {'param1': {'proto': 14005}} ), # Jaroo
			GoalState('', gs_handle_dialogue, ('', 500), (), {'param1': jaroo_handler, 'param2': {318: 0, 323: 1, } } ), # Jaroo
			
			GoalState('', gs_center_on_tile, ('', 400), params = {'param1':  (495,478) } ), # Exit
			GoalState('', gs_scroll_to_tile_and_click, ('', 500), params = {'param1': JAROO_EXIT_ICON_LOC }),
		

		], ('end', 500)) +

		[GoalState('end', gs_idle, ('end', 100) ),
		])
	return cs

def create_hommlet_scheme0():
	cs = ControlScheme()
	WENCH_DOOR_ICON_LOC = (617, 395)
	WENCH_DOOR_ENTRANCE_LOC = (619, 405)
	WENCH_EXIT_ICON_LOC = (486, 488)
	
	def furnok_dlg_handler(ds, presets, state):
		#type: (dlg.DialogState, dict, dict)->int
		N = ds.reply_count
		npc_line = ds.line_number
		
		if npc_line == 160:
			for idx in range(N):
				if ds.get_npc_reply_id(idx) == 200: # caught cheating
					return idx
			return 0 # play again
		return 0 # default

	cs.__set_stages__( 
		[
		GoalState('start', gs_condition, ('go_inn', 100), ('handle_inn', 100), params={'param1': lambda slot: game.leader.map == 5001}),
		GoalState('go_inn', gs_create_and_push_scheme, ('handle_inn', 100), params={'param1': 'go_wench', 'param2': (create_scheme_enter_building, (WENCH_DOOR_ENTRANCE_LOC, 5007) )}),
		] +
		
		GoalState.from_sequence('handle_inn', [
			GoalState('', gs_click_to_talk, ('', 1500), params = {'param1': {'proto': 14016}} ), # Ostler
			GoalState('', gs_handle_dialogue_prescripted, ('', 1500), (), {'param1': [0,1,0,0,0,0,0] } ), 
			GoalState('', gs_center_on_tile, ('', 800), params = {'param1':  (474,477) } ), # Furnok
			GoalState('', gs_click_to_talk, ('', 1500), params = {'param1': {'proto': 14025}} ), # Furnok
			GoalState('', gs_handle_dialogue, ('', 500), (), {'param1': furnok_dlg_handler, 'param2': {1: 1, 130: 0, 140: 0, 150:0, 200:0, 210:0 } } ), # Furnk

			GoalState('', gs_center_on_tile, ('', 400), params = {'param1':  (483,483) } ), # Exit
			GoalState('', gs_click_to_talk, ('', 500), params = {'param1': {'proto': 14016}} ), # Ostler again - get lodging
			GoalState('', gs_handle_dialogue_prescripted, ('', 1500), (), {'param1': [0,0,0,0] } ), 

			GoalState('', gs_push_scheme, ('', 100), params={'param1': 'rest'}),
			
			GoalState('', gs_center_on_tile, ('', 800), params = {'param1':  (483,483) } ), # Exit
			GoalState('', gs_scroll_to_tile_and_click, ('', 500), params = {'param1': WENCH_EXIT_ICON_LOC }),
		

		], ('end', 500))
			
		+ [GoalState('end', gs_idle, ('end', 100) ), ]
	)
	return cs

