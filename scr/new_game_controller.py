from controller_ui_util import WID_IDEN
from toee import *
from controllers import ControlScheme, GoalState, ControllerBase
from controller_callbacks_common import *
from utilities import *
import autoui as aui
import controller_ui_util
import gamedialog as dlg



def gs_master(slot):
	pt = Playtester.get_instance()
	if slot.state is None:
		slot.state = {
			'counter': 0
		}
	else:
		# print('master counter: ', slot.state['counter'])
		slot.state['counter'] += 1
	
	if gs_is_main_menu(slot):
		
		pt.add_scheme( create_load_game_scheme(1), 'load_game' )
		pt.push_scheme('load_game')
		# pt.push_scheme('new_game')
	elif slot.state['counter'] >= 1:
		if game.quests[18].state != qs_completed:
			pt.add_scheme( create_hommlet_scheme0(), 'hommlet0' )
			pt.push_scheme('hommlet0')
		elif game.quests[72].state == qs_unknown:
			pt.add_scheme( create_hommlet_scheme1(), 'hommlet1' )
			pt.push_scheme('hommlet1')
		else:
			pt.add_scheme( create_goto_area(2), 'goto_moathouse' )
			pt.push_scheme('goto_moathouse')
			pass
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
	autoplayer.__logging__ = True
	from controller_console import ControllerConsole
	# autoplayer.console = ControllerConsole()
	autoplayer.add_scheme( create_new_game_scheme(), 'new_game' )
	autoplayer.add_scheme( create_load_game_scheme(), 'load_game' )
	autoplayer.add_scheme( create_true_neutral_scheme(), 'true_neutral_vig' )
	autoplayer.add_scheme( create_hommlet_scheme0(), 'hommlet0')
	autoplayer.add_scheme( create_rest_scheme(), 'rest' )
	
	autoplayer.add_scheme( create_shop_map_scheme(), 'shopmap' )
	autoplayer.add_scheme( create_master_scheme(), 'main' )

	autoplayer.set_dialog_handler(dialog_handler)
	
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
	

def gs_move_mouse_to_widget(slot):
	# type: (GoalSlot)->int
	'''param1 - widget identifier
	scheme_state {'wid_id': TWidgetIdentifier}
	'''
	wid_identifier = slot.param1
	
	if wid_identifier is None:
		scheme_state = slot.get_scheme_state()
		if 'widget_scan' in scheme_state:
			if 'wid_id' in scheme_state['widget_scan']:
				wid_identifier = scheme_state['widget_scan']['wid_id']

	wid = controller_ui_util.obtain_widget(wid_identifier)
	if wid is None:
		return 0
	controller_ui_util.move_mouse_to_widget(wid)
	return 1

def gs_is_widget_visible(slot):
	#type: (GoalSlot)->int
	wid_identifier = slot.param1
	wid = controller_ui_util.obtain_widget(wid_identifier)
	if wid is None:
		return 0
	return 1

def gs_press_widget(slot):
	# type: (GoalSlot)->int
	'''param1 - widget identifier
	scheme_state { 'widget_scan': { 'wid_id': TWidgetIdentifier}
				 }
	'''
	state = slot.state
	if state is None:	
		slot.state = {
			'hovered': False,
			'clicked': False,
		}
	
	if not slot.state['hovered']:
		result = gs_move_mouse_to_widget(slot) 
		if result:
			slot.state['hovered']=True
			return 0
		return 0
		#todo handle failures...
	if not slot.state['clicked']:
		click_mouse()
		return 1
	return 0


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
	

def dlg_reply(i):
	print('Reply %d' % (i))
	press_key(DIK_1 + i)
	return

def find_attack_lines(dlg_state):
	#type: (dlg.DialogState)->list
	attack_lines = []
	N = dlg_state.reply_count
	for i in range(N):
		effect = dlg_state.get_reply_effect(i)
		if effect.find('npc.attack') >= 0:
			attack_lines.append(i)
	return attack_lines

def dlg_reply_nonattack(ds):
	#type: (dlg.DialogState)-> int
	# for now just select any non-attacking lines
	attack_lines = find_attack_lines(ds)
	for i in range(ds.reply_count):
		if i in attack_lines:
			continue
		dlg_reply(i)
		return 1
	return 0

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

def gs_handle_dialogue_prescripted(slot):
	# print('gs_handle_dialogue_prescripted')
	# goes through a pre-set reply specification:
	# param1 is a list of replies (in linear sequence)
	print('Disabling automatic dialogue handling')
	Playtester.get_instance().dialog_handler_en(False) # halt the automatic dialogue handler

	if slot.state is None:
		slot.state = {
			'was_in_dialog': False,
			'reply_counter': 0,
			'line_number': -1,
			'wait_for_dialog_counter': 0
			}
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
	
	ds = dlg.get_current_state()
	N = ds.reply_count
	cur_line = ds.line_number
	prev_line = slot.state['line_number']
	if cur_line == prev_line:
		print("Repeating the same line??")
	slot.state['line_number'] = cur_line

	replies = slot.param1
	cur_idx = slot.state['reply_counter']
	if cur_idx >= len(replies):
		print("Reply script shorter than actual dialog! currently at ", cur_idx)
		if dlg_reply_nonattack(ds):
			return 0
		dlg_reply(0)
		return 0
	
	cur_reply = replies[cur_idx]
	if cur_reply < N: # normal case
		slot.state['reply_counter'] += 1
		dlg_reply(cur_reply)
		return 0
	
	# fallback
	print("Warning: bad reply ID!")
	slot.state['reply_counter'] += 1
	dlg_reply(0)
	return 0

def gs_condition(slot):
	# param1 - condition callback
	cond_cb= slot.param1
	if slot.state is None and slot.param2 is not None:
		slot.state = dict(slot.param2)
	if cond_cb(slot):
		return 1
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
			# GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )}),
			# GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )})
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
	cs = ControlScheme()
	cs.__set_stages__(
		[GoalState('start', gs_wait_cb, ('click_camp', 100), ) ,] +
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

def create_goto_area(area_id):
	cs = ControlScheme()
	cs.__set_stages__([
		
	])
	return cs

def create_hommlet_scheme1():
	cs = ControlScheme()
	JAROO_DOOR_ICON_LOC = (614, 518)
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
		GoalState('start', gs_condition, ('go_jaroo', 100), ('handle_jaroo', 100), params={'param1': lambda slot: game.leader.map == 5001}),
		] +
		GoalState.from_sequence('go_jaroo', [
			GoalState('', gs_create_and_push_scheme, ('', 500), params = {'param1': 'goto', 'param2': (create_scheme_go_to_tile, ( (620, 520), ) ) }),
			GoalState('', gs_scroll_to_tile_and_click, ('', 500), params = {'param1': JAROO_DOOR_ICON_LOC }),
			GoalState('', gs_condition, ('', 500), params = {'param1': lambda slot: game.leader.map == 5042 }),	
		], ('handle_jaroo', 500)) +

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
		] +
		GoalState.from_sequence('go_inn', [
			GoalState('', gs_create_and_push_scheme, ('', 500), params = {'param1': 'goto', 'param2': (create_scheme_go_to_tile, ( (619, 405), ) ) }),
			GoalState('', gs_scroll_to_tile_and_click, ('', 500), params = {'param1': WENCH_DOOR_ICON_LOC }),
			GoalState('', gs_condition, ('', 500), params = {'param1': lambda slot: game.leader.map == 5007 }),	
		], ('handle_inn', 500)) + 

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

