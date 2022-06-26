from toee import *
from toee import game
from controllers import GoalSlot
from controller_ui_util import *

#region utils


def get_party_idx(obj):
    i = 0
    for member in game.party:
        if member == obj:
            return i
        i += 1
    return -1

#endregion

def gs_wait_cb(slot):
    # type: (GoalSlot)->int
	return 1

def gs_select_me(slot):
	# type: (GoalSlot)->int
	idx = get_party_idx(slot.obj)
	select_party(idx)
	if game.leader == game.party[idx]:
		return 1
	return 0

def gs_click_and_scroll_to_tile(slot):
	# type: (GoalSlot) -> int
	obj = slot.obj
	loc = slot.param1
	x,y = location_to_axis(loc)
	
	state = slot.state
	if state is None:	
		game.timevent_add( click_at, (x, y), 100, 1 )
		game.timevent_add( scroll_to, (x-10, y), 200, 1)
		slot.state = {
			't0': slot.get_cur_time(),
			'obj_loc' : obj.location
		}
		return 0
	else:
		if obj.location != slot.state['obj_loc']: # has started moving at least
			return 1
		RETRY_TIME = 3
		t_el = slot.get_cur_time() - slot.state['t0']
		if t_el > RETRY_TIME:
			print('gs_click_and_scroll_to_tile: retrying')
			slot.state['t0'] = slot.get_cur_time()
			party_idx = get_party_idx(obj)
			press_key(DIK_1 + party_idx) # make sure is selected
			game.timevent_add( click_at, (x, y), 100, 1 )
			game.timevent_add( scroll_to, (x-10, y), 200, 1)
		# return 0
	
	return 0


def gs_click_on_loc_nearest(slot):
    # type: (GoalSlot)->int
	obj = slot.obj
	loc      = slot.param1
	tgt_type = slot.param2
	
	if loc is None:
		loc = obj.location
	
	
	tgt_obj = game.obj_list_vicinity(loc, tgt_type)[0]

	state = slot.state
	if state is None:	
		click_on_obj(tgt_obj)
		slot.state = {
			't0': slot.get_cur_time(),
			'obj_loc' : obj.location
		}
		return 0
	else:
		if obj.location != slot.state['obj_loc']: # has started moving at least
			return 1
		RETRY_TIME = 3
		t_el = slot.get_cur_time() - slot.state['t0']
		if t_el > RETRY_TIME:
			print('gs_click_on_loc_nearest: retrying')
			slot.state['t0'] = slot.get_cur_time()
			party_idx = get_party_idx(obj)
			press_key(DIK_1 + party_idx) # make sure is selected
			click_on_obj(tgt_obj)
		# return 0

	return 0



def arrived_at(slot):
    # type: (GoalSlot)->int
	loc = slot.param1
	tol = slot.param2 # tolerance, in feet
	if tol is None:
		tol = 2
	print(slot.obj, loc, tol)
	if slot.obj.distance_to(loc) < tol:
		return 1
	return 0

def gs_arrive_at_tile(slot):
    # type: (GoalSlot)->int
	result = gs_click_and_scroll_to_tile(slot)
	if result == 0:
		return 0
	result = arrived_at(slot)
	if result: 
		return 1
	if result == 0:
		RETRY_TIME = 5
		t_el = slot.get_cur_time() - slot.state['t0']
		if t_el > RETRY_TIME:
			slot.state = None # this will retry the click and scroll
	return 0

def activate_scheme(slot):
	# type: (GoalSlot) -> int
	if cntrl_.set_active_scheme(slot.param1):
		return 1
	else:
		print("coudn't actiavte scheme" + str(slot.param1))
		return 0

def gs_idle(slot):
	return 0