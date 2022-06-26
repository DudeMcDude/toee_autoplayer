from toee import *
from controllers import ControlScheme, GoalState
from controller_callbacks_common import *
from utilities import *
import autoui as aui
import controller_ui_util


def gs_move_mouse_to_widget(slot):
	# type: (GoalSlot)->int
	wid_identifier = slot.param1
	wid = controller_ui_util.obtain_widget(wid_identifier)
	if wid is None:
		return 0
	controller_ui_util.move_mouse_to_widget(wid)
	return 1

def gs_press_new_game(slot):
	# type: (GoalSlot)->int
	state = slot.state
	if state is None:	
		slot.state = {
			'clicked_new_game': False,
			'clicked_new_game_normal_diff': False
		}
	if not slot.state['clicked_new_game']:
		if controller_ui_util.click_new_game(): # TODO this needs to be split to move and then click
			slot.state['clicked_new_game'] = True
			return 0
		else:
			return 0
	if not slot.state['clicked_new_game_normal_diff']:
		if controller_ui_util.click_normal_difficulty():
			slot.state['clicked_new_game_normal_diff'] = True
			return 0
		else:
			return 0
	return 1



def create_new_game_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalState('start', gs_wait_cb, ('end', 1000) ),
		GoalState('press_new_game', gs_press_new_game, ('end', 1000) ),
		GoalState('end', gs_idle, ('end', 1000) )
	])
	return cs
