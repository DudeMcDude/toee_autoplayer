from controller_ui_util import WID_IDEN
from toee import *
from controllers import ControlScheme, GoalState
from controller_callbacks_common import *
from utilities import *
import autoui as aui
import controller_ui_util
import gamedialog as dlg


def setup_playtester(autoplayer):
	#type: (Playtester)->None
	autoplayer.add_scheme( create_new_game_scheme(), 'new_game' )
	autoplayer.add_scheme( create_load_game_scheme(), 'load_game' )
	autoplayer.add_scheme( create_true_neutral_scheme(), 'true_neutral_vig' )
	autoplayer.add_scheme( create_hommlet_scheme0(), 'hommlet0')
	
	autoplayer.add_scheme( create_shop_map_scheme(), 'shopmap' )
	# autoplayer.set_active_scheme('new_game')
	autoplayer.set_active_scheme('new_game')
	print('Beginning scheme in 1 sec...')
	# autoplayer.schedule(1000, real_time=1)
	return

#region callbacks
def gs_move_mouse_to_widget(slot):
	# type: (GoalSlot)->int
	wid_identifier = slot.param1
	wid = controller_ui_util.obtain_widget(wid_identifier)
	if wid is None:
		return 0
	controller_ui_util.move_mouse_to_widget(wid)
	return 1

def gs_press_widget(slot):
	# type: (GoalSlot)->int
	# uses param1 for widget identifier
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
		click_mouse()
		return 1
	return 0

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

def gs_handle_dialogue(slot):
	# param1 - callback for handling current dialogue state
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
			return 1
		else:
			slot.state['wait_for_dialog_counter'] += 1
			return 0
	reply_cb = slot.param1 #type: callable[ [dlg.DialogState, dict, dict], int]
	presets  = slot.param2
	if presets is None:
		presets = {}
	
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

	
	def reply_nonattack():
		# for now just select any non-attacking lines
		attack_lines = find_attack_lines(ds)
		for i in range(N):
			if i in attack_lines:
				continue
			dlg_reply(i)
			return 1
	
	replies = slot.param1
	cur_idx = slot.state['reply_counter']
	if cur_idx >= len(replies):
		print("Reply script shorter than actual dialog! currently at ", cur_idx)
		if reply_nonattack():
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

def gs_await_condition(slot):
	# param1 - condition callback
	cond_cb= slot.param1
	if slot.state is None and slot.param2 is not None:
		slot.state = dict(slot.param2)
	if cond_cb(slot.state):
		return 1
	return 0

#endregion

def create_new_game_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalState('start', gs_press_widget, ('normaldiff', 500), (), {'param1': WID_IDEN.NEW_GAME } ),
		GoalState('normaldiff', gs_press_widget, ('select_true_neutral_alignment', 500), (), {'param1': WID_IDEN.NORMAL_DIFF } ),
		GoalState('select_true_neutral_alignment', gs_press_widget, ('party_alignment_accept', 800), (), {'param1': WID_IDEN.TRUE_NEUTRAL_BTN_WID_ID } ),
		GoalState('party_alignment_accept', gs_press_widget, ('char_pool_ch1', 300), (), {'param1': WID_IDEN.PARTY_ALIGNMENT_ACCEPT_BTN } ),
		GoalState('char_pool_ch1', gs_press_widget, ('char_pool_ch1_add', 300), (), {'param1': WID_IDEN.CHAR_POOL_CHAR1 } ),
		GoalState('char_pool_ch1_add', gs_press_widget, ('char_pool_ch2', 300), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch2', gs_press_widget, ('char_pool_ch2_add', 300), (), {'param1': WID_IDEN.CHAR_POOL_CHAR2 } ),
		GoalState('char_pool_ch2_add', gs_press_widget, ('char_pool_ch3', 300), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch3', gs_press_widget, ('char_pool_ch3_add', 300), (), {'param1': WID_IDEN.CHAR_POOL_CHAR3 } ),
		GoalState('char_pool_ch3_add', gs_press_widget, ('char_pool_ch4', 300), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch4', gs_press_widget, ('char_pool_ch4_add', 300), (), {'param1': WID_IDEN.CHAR_POOL_CHAR4 } ),
		GoalState('char_pool_ch4_add', gs_press_widget, ('char_pool_ch5', 300), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch5', gs_press_widget, ('char_pool_ch5_add', 300), (), {'param1': WID_IDEN.CHAR_POOL_CHAR5 } ),
		GoalState('char_pool_ch5_add', gs_press_widget, ('char_pool_ch6', 300), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch6', gs_press_widget, ('char_pool_ch6_add', 300), (), {'param1': WID_IDEN.CHAR_POOL_CHAR6 } ),
		GoalState('char_pool_ch6_add', gs_press_widget, ('char_pool_begin_adventure', 300), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_begin_adventure', gs_press_widget, ('end', 100), (), {'param1': WID_IDEN.CHAR_POOL_BEGIN_ADVENTURE } ),
		GoalState('end', activate_scheme, ('end', 100), (), {'param1': 'shopmap'} ),
	])
	return cs

def create_load_game_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalState('start', gs_press_widget, ('load_game_entry_1', 200), (), {'param1': WID_IDEN.LOAD_GAME}),
		GoalState('load_game_entry_1', gs_press_widget, ('load_it', 200), (), {'param1': WID_IDEN.LOAD_GAME_ENTRY_1}),
		GoalState('load_it', gs_press_widget, ('end', 200), (), {'param1': WID_IDEN.LOAD_GAME_LOAD_BTN}),
		GoalState('end', activate_scheme, ('end', 200), (), {'param1': 'hommlet0'} ),
	])
	return cs

def create_shop_map_scheme():
	cs = ControlScheme()
	std_chest_dlg_choices = [0, 0,1]
	cs.__set_stages__(
		[ GoalState('start', gs_wait_cb, ('equipment_chests', 300) ), ] +
		GoalState.from_sequence('equipment_chests', [
			GoalState('', gs_click_on_object, ('', 500), (), {'param1': {'proto': 14575, } } ),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': std_chest_dlg_choices } ),
		], ('game_portal', 500), ()) +
		GoalState.from_sequence('game_portal', [
			GoalState('', gs_click_on_object, ('', 500), (), {'param1': {'proto': 14758, } } ),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': std_chest_dlg_choices } ),
		], ('end', 500), ()) +
		[ GoalState('end', activate_scheme, ('end', 1000) , params={'param1': 'true_neutral_vig'}),]
		)
	return cs

def create_true_neutral_scheme():
	cs = ControlScheme()
	
	druid_dlg_choices = [0, 0,0,0,0]
	cs.__set_stages__( 
		[GoalState('start', gs_wait_cb, ('talk_jaroo', 500)),] +
		GoalState.from_sequence('talk_jaroo', [
			GoalState('', gs_scroll_to_tile, ('', 3500), params = {'param1': (488, 474) }),
			GoalState('', gs_click_on_object, ('', 3000), params = {'param1': {'proto': 14322, 'location': location_from_axis(488, 474)}} ),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': druid_dlg_choices } ),
		], ('end', 500)) + 
		[GoalState('end', activate_scheme, ('end', 100) , params={'param1': 'hommlet0'}), ]
	)
	return cs

def create_hommlet_scheme0():
	cs = ControlScheme()
	WENCH_DOOR_ICON_LOC = (617, 395)
	WENCH_EXIT_ICON_LOC = (486, 488)
	elmo_dlg_choices = [0, 1,1,0,0, 1, 0] # hire drunk elmo

	def furnok_dlg_handler(ds, presets, state):
		#type: (dlg.DialogState, dict, dict)->int
		N = ds.reply_count
		npc_line = ds.line_number
		
		if npc_line == 160:
			for idx in range(N):
				if ds.get_npc_reply_id(idx) == 200: # caught cheating
					return idx
			return 0 # play again
		return 0 #

	cs.__set_stages__( 
		[GoalState('start', gs_wait_cb, ('go_inn', 500)),] +
		GoalState.from_sequence('go_inn', [
			GoalState('', gs_scroll_to_tile_and_click, ('', 3500), params = {'param1': (619, 405) }),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': [0,0,0,0,0,0,0,0] } ), # Kent first
			GoalState('', gs_scroll_to_tile_and_click, ('', 3500), params = {'param1': (619, 405) }),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': elmo_dlg_choices } ), # Elmo
			GoalState('', gs_select_all, ('', 500), ),
			GoalState('', gs_scroll_to_tile_and_click, ('', 500), params = {'param1': WENCH_DOOR_ICON_LOC }),
			GoalState('', gs_await_condition, ('', 500), params = {'param1': lambda slot: game.leader.map == 5007 }),
			
			
		], ('handle_inn', 500)) + 
		GoalState.from_sequence('handle_inn', [
		GoalState('', gs_click_on_object, ('', 1500), params = {'param1': {'proto': 14016}} ), # Ostler
		GoalState('', gs_handle_dialogue_prescripted, ('', 1500), (), {'param1': [0,1,0,0,0,0,0] } ), 
		GoalState('', gs_center_on_tile, ('', 800), params = {'param1':  (474,477) } ), # Furnok
		GoalState('', gs_click_on_object, ('', 1500), params = {'param1': {'proto': 14025}} ), # Furnok
		GoalState('', gs_handle_dialogue, ('', 500), (), {'param1': furnok_dlg_handler, 'param2': {1: 1, 130: 0, 140: 0, 150:0, 200:0, 210:0 } } ), # Furnk

		GoalState('', gs_center_on_tile, ('', 800), params = {'param1':  (483,483) } ), # Exit
		GoalState('', gs_click_on_object, ('', 500), params = {'param1': {'proto': 14016}} ), # Ostler again - get lodging
		GoalState('', gs_handle_dialogue_prescripted, ('', 1500), (), {'param1': [0,0,0,0] } ), 

		GoalState('', gs_press_widget, ('', 500), (), {'param1': WID_IDEN.UTIL_BAR_CAMP_BTN } ),
		GoalState('', gs_press_widget, ('', 1500), (), {'param1': WID_IDEN.CAMPING_UI_REST_BTN } ),
		
		GoalState('', gs_center_on_tile, ('', 800), params = {'param1':  (483,483) } ), # Exit
		GoalState('', gs_scroll_to_tile_and_click, ('', 500), params = {'param1': WENCH_EXIT_ICON_LOC }),
		

		], ('end', 500))
			
		+ [GoalState('end', gs_idle, ('end', 100) ), ]
	)
	return cs

