from toee import *
from toee import PySpellStore, game
from controller_callbacks_common import *
from controllers import ControlScheme, GoalState, GoalStateStart,GoalStateEnd, ControllerBase, GoalStateCondition, GoalStateCreatePushScheme
from controller_ui_util import WID_IDEN
from utilities import *
import controller_ui_util
import tpdp
import gamedialog as dlg
import logbook



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
		
		GoalStateStart( gs_scan_get_widget_from_list, ('check_result', 100), (), {'param1': wid_list, 'param2': check_widget } ),
		GoalState('check_result', gs_found, ('press_char_btn', 100), ('end', 300),  ),
		GoalState('press_char_btn', gs_press_widget, ('press_add', 200), (), {'param1': None } ),
		
		GoalState('press_add', gs_press_widget, ('end', 200), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('end', gs_wait_cb, ('end', 0), )
	])
	return cs

def create_new_game_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalStateStart( gs_press_widget, ('normaldiff', 500), (), {'param1': WID_IDEN.NEW_GAME } ),
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
			GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )}),
			GoalState('', gs_create_and_push_scheme, ('', 300), params={'param1': 'party_pool_add_pc', 'param2': (create_party_pool_add_pc_scheme, () )})
		], ('char_pool_begin_adventure', 300), ('char_pool_begin_adventure', 300))
		+[
		GoalState('char_pool_begin_adventure', gs_press_widget, ('do_shopmap', 100), (), {'param1': WID_IDEN.CHAR_POOL_BEGIN_ADVENTURE } ),
		GoalState('do_shopmap', gs_push_scheme, ('end', 100), (), {'param1': 'shopmap'} ),
		GoalState('end', gs_wait_cb, ('end', 100), (), ),
	])
	return cs

def create_shop_map_scheme():
	cs = ControlScheme()
	std_chest_dlg_choices = [0, 0,1]
	cs.__set_stages__(
		[ GoalStateStart( gs_wait_cb, ('equipment_chests', 300) ), ] +
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
		[GoalStateStart( gs_wait_cb, ('talk_jaroo', 500)),] +
		GoalState.from_sequence('talk_jaroo', [
			GoalState('', gs_scroll_to_tile, ('', 3500), params = {'param1': (488, 474) }),
			GoalState('', gs_click_to_talk, ('', 3000), params = {'param1': {'proto': 14322, 'location': location_from_axis(488, 474)}} ),
			GoalState('', gs_handle_dialogue_prescripted, ('', 500), (), {'param1': druid_dlg_choices } ),
		], ('do_hommlet', 500)) + 
		[GoalState('do_hommlet', gs_push_scheme, ('end', 100), (), {'param1': 'hommlet0'} ),
		GoalState('end', gs_wait_cb, ('end', 100) ), ]
	)
	return cs

def create_load_game_scheme(save_id):
	cs = ControlScheme()
	if type(save_id) == int:
		save_idx = save_id
		if save_idx < 0:
			save_idx = 0
		if save_idx > 7:
			save_idx = 7
	else:
		save_idx = None
		assert (type(save_id) is str) or (type(save_id) is list) or (type(save_id) is tuple), "must be str or tuple/list"
	
	wid_list = WID_IDEN.LOAD_GAME_ENTRY_BTNS
	def match_load_game(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		idx = state['widget_scan']['idx']
		print('idx: ' + str(idx))
		widget = wid_list[idx]
		print('widget: ' + str(widget))
		wid = controller_ui_util.obtain_widget(wid_list[idx])
		if wid is None:
			return 0
		if save_idx is not None:
			return idx == save_idx
		if type(save_id) is str:
			if wid.rendered_text.lower().find(save_id.lower()) >= 0:
				return 1
		elif type(save_id) in [list, tuple]:
			for x in save_id:
				if wid.rendered_text.lower().find(x.lower()) >= 0:
					return 1
		return 0

	cs.__set_stages__( [
		GoalStateStart( gs_is_main_menu, ('main_menu_load', 100), ('ingame_load', 100) ),
		
		# main menu load
		GoalState('main_menu_load', gs_press_widget, ('check_load_entries_visible', 100), (), {'param1': WID_IDEN.MAIN_MENU_LOAD_GAME}),
		GoalState('check_load_entries_visible', gs_is_widget_visible, ('load_game_find_entry', 100), ('main_menu_load', 100), params={'param1': WID_IDEN.LOAD_GAME_ENTRY_BTNS[0]}),
		GoalState('load_game_find_entry',gs_scan_get_widget_from_list, ('load_game_entry', 100), ('end', 100), params={'param1':wid_list, 'param2': match_load_game }),
		
		
		GoalState('ingame_load', gs_is_widget_visible, ('ingame_press_load', 200), ('ingame_bring_up_menu', 100), {'param1': WID_IDEN.INGAME_LOAD_GAME}),
		GoalState('ingame_bring_up_menu', gs_press_key, ('ingame_load', 100), ('ingame_load', 100) , params={'param1': DIK_ESCAPE}),
		GoalState('ingame_press_load', gs_press_widget, ('ingame_check_load_entries_visible', 200), (), {'param1': WID_IDEN.INGAME_LOAD_GAME}),
		GoalState('ingame_check_load_entries_visible', gs_is_widget_visible, ('ingame_load_game_find_entry', 100), ('ingame_press_load', 100), params={'param1': WID_IDEN.LOAD_GAME_ENTRY_BTNS[0]}),
		GoalState('ingame_load_game_find_entry',gs_scan_get_widget_from_list, ('load_game_entry', 100), ('end', 100), params={'param1':wid_list, 'param2': match_load_game }),
		
		GoalState('load_game_entry', gs_press_widget, ('load_it', 200), ),
		GoalState('load_it', gs_press_widget, ('end', 200), (), {'param1': WID_IDEN.LOAD_GAME_LOAD_BTN}),
		
		
		GoalState('end', gs_wait_cb, ('end', 200), ),
	])
	return cs


def create_ui_camp_rest_scheme():
	cs = ControlScheme()
	cs.__set_stages__(
		[
		GoalStateStart( gs_wait_cb, ('click_camp', 100), ) ,] +
		GoalState.from_sequence('click_camp', [
			GoalState('', gs_press_widget, ('', 500), (), {'param1': WID_IDEN.UTIL_BAR_CAMP_BTN } ),
			GoalState('', gs_press_widget, ('', 500), (), {'param1': WID_IDEN.CAMPING_UI_UNTIL_HEALED_BTN } ),
			GoalState('', gs_press_widget, ('', 500), (), {'param1': WID_IDEN.CAMPING_UI_DAYS_INC } ), # incase the above is 0 days (might still want to cure poison/disease and such)
			GoalState('', gs_press_widget, ('', 1500), (), {'param1': WID_IDEN.CAMPING_UI_REST_BTN } ),
		], ('end', 100) ) + 
		[GoalState('end', gs_wait_cb, ('end', 100), ) ,	])
	return cs





def create_move_mouse_to_obj(obj_ref):
	cs = ControlScheme()
	def gs_init_move_mouse(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		obj = get_object(obj_ref)
		print('create_move_mouse_to_obj init: obj ref is %s, loc = %s' % (str(obj) , str(location_to_axis(obj.location)) ) )
		state['mouse_move'] = {
			'obj': obj,
			'tweak_x': 0,
			'tweak_y': 0,
			'tweak_amount': 3,
			'tweak_max': 20,
			'use_fine': True,
		}
		if obj == OBJ_HANDLE_NULL:
			return 0
		return 1

	def gs_move_mouse_to_object(slot):
		# type: (GoalSlot)->int
		# print('gs_move_mouse_to_object')
		state = slot.get_scheme_state()
		obj = state['mouse_move']['obj']
		
		off_x = state['mouse_move']['tweak_x']
		off_y = state['mouse_move']['tweak_y']
		controller_ui_util.move_mouse_to_obj(obj, off_x, off_y)
		return 1

	cs.__set_stages__([
		GoalStateStart( gs_init_move_mouse, ('move_mouse', 10), ('end', 10) ),
		GoalState('move_mouse', gs_move_mouse_to_object, ('check_hovered', 10), ('end', 10) ),
		GoalStateCondition('check_hovered', lambda slot: game.hovered == slot.get_scheme_state()['mouse_move']['obj'], ('end', 10), ('tweak', 10) ),
		GoalState('tweak', gs_tweak_mouse_pos, ('move_mouse', 10), ('end', 10) ),
		GoalState('end', gs_wait_cb, ('end', 10)),
	])
	return cs



