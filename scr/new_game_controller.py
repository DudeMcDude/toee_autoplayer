from controller_ui_util import WID_IDEN
from toee import *
from controllers import ControlScheme, GoalState
from controller_callbacks_common import *
from utilities import *
import autoui as aui
import controller_ui_util


def setup_playtester(autoplayer):
	#type: (Playtester)->None
	autoplayer.add_scheme( create_new_game_scheme(), 'new_game' )
	autoplayer.add_scheme( create_load_game_scheme(), 'load_game' )
	
	autoplayer.add_scheme( create_shop_map_scheme(), 'shopmap' )
	autoplayer.set_active_scheme('load_game')
	print('Beginning scheme in 1 sec...')
	autoplayer.schedule(1000, real_time=1)
	return


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



def create_new_game_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalState('start', gs_press_widget, ('normaldiff', 500), (), {'param1': WID_IDEN.NEW_GAME } ),
		GoalState('normaldiff', gs_press_widget, ('select_true_neutral_alignment', 500), (), {'param1': WID_IDEN.NORMAL_DIFF } ),
		GoalState('select_true_neutral_alignment', gs_press_widget, ('party_alignment_accept', 1000), (), {'param1': WID_IDEN.TRUE_NEUTRAL_BTN_WID_ID } ),
		GoalState('party_alignment_accept', gs_press_widget, ('char_pool_ch1', 500), (), {'param1': WID_IDEN.PARTY_ALIGNMENT_ACCEPT_BTN } ),
		GoalState('char_pool_ch1', gs_press_widget, ('char_pool_ch1_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR1 } ),
		GoalState('char_pool_ch1_add', gs_press_widget, ('char_pool_ch2', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch2', gs_press_widget, ('char_pool_ch2_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR2 } ),
		GoalState('char_pool_ch2_add', gs_press_widget, ('char_pool_ch3', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch3', gs_press_widget, ('char_pool_ch3_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR3 } ),
		GoalState('char_pool_ch3_add', gs_press_widget, ('char_pool_ch4', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch4', gs_press_widget, ('char_pool_ch4_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR4 } ),
		GoalState('char_pool_ch4_add', gs_press_widget, ('char_pool_ch5', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch5', gs_press_widget, ('char_pool_ch5_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR5 } ),
		GoalState('char_pool_ch5_add', gs_press_widget, ('char_pool_ch6', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch6', gs_press_widget, ('char_pool_ch6_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR6 } ),
		GoalState('char_pool_ch6_add', gs_press_widget, ('char_pool_begin_adventure', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_begin_adventure', gs_press_widget, ('end', 100), (), {'param1': WID_IDEN.CHAR_POOL_BEGIN_ADVENTURE } ),
		GoalState('end', activate_scheme, ('end', 100), (), {'param1': 'shopmap'} ),
	])
	return cs

def create_load_game_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalState('start', gs_press_widget, ('load_game_entry_1', 500), (), {'param1': WID_IDEN.LOAD_GAME}),
		GoalState('load_game_entry_1', gs_press_widget, ('load_it', 500), (), {'param1': WID_IDEN.LOAD_GAME_ENTRY_1}),
		GoalState('load_it', gs_press_widget, ('end', 500), (), {'param1': WID_IDEN.LOAD_GAME_LOAD_BTN}),
		GoalState('end', activate_scheme, ('end', 1000), (), {'param1': 'shopmap'} ),
	])
	return cs

def create_shop_map_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalState('start', gs_leader_perform_on_target, ('end', 500), (), {'param1': D20A_TALK , 'param2': {'proto': 14575, } } ),
		GoalState('normaldiff', gs_press_widget, ('select_true_neutral_alignment', 500), (), {'param1': WID_IDEN.NORMAL_DIFF } ),
		GoalState('select_true_neutral_alignment', gs_press_widget, ('party_alignment_accept', 1000), (), {'param1': WID_IDEN.TRUE_NEUTRAL_BTN_WID_ID } ),
		GoalState('party_alignment_accept', gs_press_widget, ('char_pool_ch1', 500), (), {'param1': WID_IDEN.PARTY_ALIGNMENT_ACCEPT_BTN } ),
		GoalState('char_pool_ch1', gs_press_widget, ('char_pool_ch1_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR1 } ),
		GoalState('char_pool_ch1_add', gs_press_widget, ('char_pool_ch2', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch2', gs_press_widget, ('char_pool_ch2_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR2 } ),
		GoalState('char_pool_ch2_add', gs_press_widget, ('char_pool_ch3', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch3', gs_press_widget, ('char_pool_ch3_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR3 } ),
		GoalState('char_pool_ch3_add', gs_press_widget, ('char_pool_ch4', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch4', gs_press_widget, ('char_pool_ch4_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR4 } ),
		GoalState('char_pool_ch4_add', gs_press_widget, ('char_pool_ch5', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch5', gs_press_widget, ('char_pool_ch5_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR5 } ),
		GoalState('char_pool_ch5_add', gs_press_widget, ('char_pool_ch6', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_ch6', gs_press_widget, ('char_pool_ch6_add', 500), (), {'param1': WID_IDEN.CHAR_POOL_CHAR6 } ),
		GoalState('char_pool_ch6_add', gs_press_widget, ('char_pool_begin_adventure', 500), (), {'param1': WID_IDEN.CHAR_POOL_ADD_BTN } ),
		GoalState('char_pool_begin_adventure', gs_press_widget, ('end', 100), (), {'param1': WID_IDEN.CHAR_POOL_BEGIN_ADVENTURE } ),
		
		GoalState('end', gs_idle, ('end', 1000) )
	])
	return cs