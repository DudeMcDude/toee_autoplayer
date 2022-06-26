from scr.controller_ui_util import WID_IDEN
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
		GoalState('start', gs_press_widget, ('normaldiff', 1000), (), {'param1': WID_IDEN.NEW_GAME } ),
		GoalState('normaldiff', gs_press_widget, ('end', 1000), (), {'param1': WID_IDEN.NORMAL_DIFF } ),
		GoalState('end', gs_idle, ('end', 1000) )
	])
	return cs
