from templeplus.playtester import Playtester
from toee import *
from toee import game
from controllers import GoalSlot
from controller_ui_util import *
import controller_ui_util
import gamedialog as dlg

#region utils
debug_prints_en = True
def debug_print(msg):
	if debug_prints_en:
		print(msg)

def get_party_idx(obj):
    i = 0
    for member in game.party:
        if member == obj:
            return i
        i += 1
    return -1

def get_object(obj_identifier):
	if type(obj_identifier) is dict:
		loc = game.leader.location
		if obj_identifier.get('location'):
			loc = obj_identifier['location']
		obj_list = game.obj_list_vicinity(loc, OLC_ALL)
		if obj_identifier.get('proto'):
			proto_id = obj_identifier['proto']
			obj_list = [x for x in obj_list if x.proto == proto_id]
		if len(obj_list) == 0:
			return OBJ_HANDLE_NULL
		return obj_list[0]
	return OBJ_HANDLE_NULL


def perform_action( action_type, actor, tgt, location ):
    try:
        result = actor.action_perform( action_type, tgt, location)
    except RuntimeError as e:
        print(e.message)
        result = 0
        pass
    return result
#endregion

#region callbacks
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


def gs_press_key(slot):
	dik = slot.param1
	press_key(dik)
	return 1

def gs_select_all(slot):
	select_all()
	return 1


#region widget callbacks
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
		print('gs_press_widget: moving cursor')
		result = gs_move_mouse_to_widget(slot) 
		if result:
			slot.state['hovered']=True
			return 0
		return 0
		#todo handle failures...
	if not slot.state['clicked']:
		print('gs_press_widget: clicking')
		click_mouse()
		return 1
	return 0

#endregion widget callbacks


def gs_scroll_to_tile(slot):
	loc = slot.param1
	if type(loc) is tuple:
		x,y = loc
	else:
		x,y = location_to_axis(loc)
	scroll_to( x-10, y,  )
	return 1

def gs_center_on_tile(slot):
	loc = slot.param1
	center_screen_on( loc )
	return 1

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


def gs_condition(slot):
	# param1 - condition callback
	cond_cb= slot.param1
	if slot.state is None and slot.param2 is not None:
		slot.state = dict(slot.param2)
	if cond_cb(slot):
		return 1
	return 0

def gs_condition_map_change(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		if not 'map_change_check' in state:
			# print('map change check: initing with %s' % str(game.leader.map))
			state['map_change_check'] = {'map': game.leader.map}
			return 0
		if state['map_change_check']['map'] != game.leader.map:
			# print('map change check: current %s is different than previous %s' % (str(game.leader.map), str(state['map_change_check']['map']) ))
			return 1
		# print('map change check: no change %s' % ( str(state['map_change_check']['map']) ))
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


def gs_leader_perform_on_target(slot):
	obj = game.leader
	if obj == OBJ_HANDLE_NULL:
		return 0
	action_type = slot.param1
	target = get_object(slot.param2)
	if target == OBJ_HANDLE_NULL:
		return 0
	target_loc = target.location
	print(str(target))

	if obj.is_performing():
		debug_print("leader_perform_on_target: is performing already. 0")
		return 0

	if slot.state is None:
		debug_print("leader_perform_on_target: setting state to 0")
		slot.state = 0
	elif slot.state == 0: # will only complete this stage when is_performing() == 0 and have queued the action
		debug_print("leader_perform_on_target: setting state to 1")
		slot.state = 1
		return 1
	debug_print("leader_perform_on_target: performing action")
	perf_result = perform_action(action_type, obj, target, target_loc)
	# if perf_result == 0:
		# return 0
	return

def perform_on_nearest(slot):
	obj = slot.obj
	action_type = slot.param1
	tgt_type	= slot.param2
	
	chest_obj = game.obj_list_vicinity(obj.location, tgt_type)[0]
	container_loc = chest_obj.location

	if obj.is_performing():
		debug_print("perform_on_nearest: is performing already. 0")
		return 0
	if slot.state is None:
		debug_print("perform_on_nearest: setting state to 0")
		slot.state = 0
	elif slot.state == 0: # will only complete this stage when is_performing() == 0 and have queued the action
		debug_print("perform_on_nearest: setting state to 1")
		slot.state = 1
		return 1
	debug_print("perform_on_nearest: performing action")
	perf_result = perform_action(action_type, obj, chest_obj, container_loc)
	# if perf_result == 0:
		# return 0
	return 0


def loot_nearest_chest(slot):
	#type: (GoalSlot) -> int
	obj = slot.obj
	action_type = D20A_OPEN_CONTAINER
	tgt_type	= OLC_CONTAINER
	
	chest_obj = game.obj_list_vicinity(obj.location, tgt_type)[0]
	container_loc = chest_obj.location
	

	if obj.is_performing():
		print("loot_nearest_chest: is performing already. 0")
		return 0

	OPENING = 'opening'
	OPENED = 'opened'
	LOCKPICKING = 'lockpicking'
	LOOTING = 'looting'
	FINISHED = 'finished'

	cur_state = slot.state
	if cur_state is None:
		#initialize state
		slot.state = {'state' : OPENING}
		if chest_obj.obj_get_int(obj_f_container_flags) & OCOF_LOCKED:
			action_type = D20A_OPEN_LOCK
			slot.state['state'] = LOCKPICKING
			slot.state['t_start'] = slot.get_cur_time()
	else:
		if cur_state['state'] == OPENING:
			slot.state['state'] = LOOTING
			return 0
		elif cur_state['state'] == LOOTING:
			# print("Looting!")
			click_loot_all_button()
			slot.state['state'] = FINISHED
			return 0
		elif cur_state['state'] == FINISHED:
			press_escape()
			return 1
		elif cur_state['state'] == LOCKPICKING:
			# print("Lockpicking!")
			e_time = slot.get_cur_time() - slot.state['t_start']
			if e_time < 8: # give the animation time to complete (unfortunately this isn't acknowledged in is_performing... the action sequence ends immediately)
				return 0
			else:
				if (chest_obj.obj_get_int(obj_f_container_flags) & OCOF_LOCKED) == 0: # chest has been unlocked
					slot.state['state'] = OPENING
				else:
					print('oh damn, lockpicking failed')
				
			
	
	perform_action(action_type, obj, chest_obj, container_loc)
	return 0

def fight_room(slot):
	# type: (GoalSlot)->int
	cntrl = Playtester.get_instance().get_instance()
	if cntrl is None or not cntrl.__was_in_combat__:
		return 0
	cntrl.__was_in_combat__ = False # the combat controller takes precedence
	return 1

def wait_for_dlg(slot):
	cntrl = Playtester.get_instance()
	if not cntrl.__was_in_dialog__:
		return 0
	cntrl.__was_in_dialog__ = False # the combat controller takes precedence
	return 1

def loot_critters(slot):
	#type: (GoalSlot) -> int
	obj = slot.obj
	action_type = D20A_OPEN_CONTAINER
	tgt_type	= OLC_NPC

	if obj.is_performing():
		print("loot_nearest_chest: is performing already. 0")
		return 0

	OPENING = 'opening'
	OPENED = 'opened'
	LOOTED = 'looted'
	LOOTING = 'looting'
	FINISHED = 'finished'
	def is_lootable_corpse(x):
		if x.is_unconscious() == 0:
			return False
		inven_count = x.obj_get_int(obj_f_critter_inventory_num)
		for i in range(inven_count):
			item = x.obj_get_idx_obj(obj_f_critter_inventory_list_idx, i)
			if item == OBJ_HANDLE_NULL:
				continue
			item_flags = item.obj_get_int(obj_f_item_flags)
			if (item_flags & OIF_NO_LOOT) == 0:
				return True
		return False
	cur_state = slot.state
	if cur_state is None:
		objects = [x for x in game.obj_list_vicinity(obj.location, tgt_type) if is_lootable_corpse(x) ]
		if len(objects) == 0:
			return 1
		#initialize state
		slot.state = {'state' : OPENING}
		slot.state['critters'] = objects
		slot.state['idx'] = 0
		return 0
	else:
		objects = slot.state['critters']
		if cur_state['state'] == OPENING:
			slot.state['state'] = LOOTING
			pass
		elif cur_state['state'] == LOOTING:
			print("Looting!")
			click_loot_all_button()
			slot.state['state'] = LOOTED
			return 0
		elif cur_state['state'] == LOOTED:
			press_escape()
			idx = slot.state['idx'] + 1
			slot.state['idx'] = idx
			if idx >= len(objects):
				slot.state['state'] = FINISHED
			else:
				slot.state['state'] = OPENING
			return 0
		elif cur_state['state'] == FINISHED:
			return 1
	idx = slot.state['idx']
	loc = objects[idx].location
	print("Loot critters: ", idx, loc, objects)
	perform_action(action_type, obj, objects[idx], loc)
	return 0


def gs_create_and_push_scheme(slot):
	#type: (GoalSlot)->int
	'''param1 - id [str]\n
		param2 - (callback, (args,...) )
		alternative: (if none provided)
		scheme_state {'push_scheme': {'id': str, 'callback': (callback, args ) }}
	'''
	
	id        = slot.param1
	if id is None:
		state = slot.get_scheme_state()
		if not 'push_scheme' in state:
			raise Exception("gs_create_and_push_scheme: relying on scheme_state, but 'push_scheme' not inited!")
		id = state['push_scheme']['id']
		create_cb, args = state['push_scheme']['callback']
	else:
		create_cb, args = slot.param2

	if slot.state is None:
		print('gs_create_and_push_scheme: ID = %s args = %s' %(id, str(args)) )
		cs = create_cb(*args)
		slot.state = {}
		
		Playtester.get_instance().add_scheme(cs, id)
		if Playtester.get_instance().push_scheme(id):
			return 1
		# print("coudn't activate scheme " + str(slot.param1))
		return 1
	return 1

def gs_push_scheme(slot):
	# type: (GoalSlot) -> int
	'''
	param1 - scheme id [str] \n
	param2 - callback [callable]
	'''
	# print('activating scheme', slot.param1)
	cb = slot.param2
	if cb:
		if cb(slot):
			if Playtester.get_instance().push_scheme(slot.param1):
				return 1
			return 0 # probably for trying again
		return 1
	else:
		if slot.state is None:
			slot.state = {}
			if Playtester.get_instance().push_scheme(slot.param1):
				return 1
		# print("coudn't activate scheme " + str(slot.param1))
		return 1
	

def gs_idle(slot):
	return 0