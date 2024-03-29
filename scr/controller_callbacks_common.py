from templeplus.playtester import Playtester
from toee import *
from toee import game
from controllers import GoalSlot
import autoui as aui
from controller_ui_util import *
import controller_ui_util
import gamedialog as dlg
from controller_constants import *

#region utils
def is_ingame():
	return len(game.party) > 0

def gs_is_main_menu(slot):
	# todo expand this..
	wid = controller_ui_util.obtain_widget(WID_IDEN.MAIN_MENU_LOAD_GAME)
	if wid is None:
		# print('is_main_menu: false')
		return 0
	return 1	

def playtester_push_scheme(cs, id):
	pt = Playtester.get_instance()
	pt.add_scheme(cs, id)
	result = pt.push_scheme(id)
	return result

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
		if 'location' in obj_identifier:
			loc = obj_identifier['location']
			if type(loc) is tuple:
				loc = location_from_axis(*loc)
		obj_type = OLC_ALL
		if obj_identifier.get('obj_t'):
			obj_type = obj_identifier['obj_t']
		
		obj_list = game.obj_list_vicinity(loc, obj_type)
		if 'proto' in obj_identifier:
			proto_id = obj_identifier['proto']
			if type(proto_id) == int:
				proto_id = (proto_id,) 
			obj_list = [x for x in obj_list if x.proto in proto_id]
		if len(obj_list) == 0:
			return OBJ_HANDLE_NULL
		if 'guid' in obj_identifier:
			guid = obj_identifier['guid']
			obj_list = [x for x in obj_list if x.__getstate__() == guid]
			if len(obj_list) == 0:
				return OBJ_HANDLE_NULL
		# get closest one
		obj_list.sort(key = lambda x: x.distance_to(loc))
		if len(obj_list) > 1:
			print('ambiguous obj_ref, found multiple objects: %s' %(str(obj_list)) )
		return obj_list[0]
	elif isinstance(obj_identifier, PyObjHandle):
		return obj_identifier
	return OBJ_HANDLE_NULL


def perform_action( action_type, actor, tgt, location ):
    try:
        result = actor.action_perform( action_type, tgt, location)
    except RuntimeError as e:
        print(e.message)
        result = 0
        pass
    return result

def can_levelup(pc):
	idx = get_party_idx(pc)
	if idx < 0:
		return False
	wid_id = WID_IDEN.PARTY_UI_LEVELUP_BTNS[idx]
	wid = obtain_widget(wid_id)
	if wid is None:
		return False
	return True

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
	if not 'widget_scan' in state:
		print('gs_scan_get_widget_from_list: initing scheme state')
		state['widget_scan'] = {
				'idx': -1,
				'found': False,
				'wid_id': None, 
				'text_contents': [],
			}
	
	text_contents = []
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
		text_contents.append(wid.rendered_text)

		# print('obtained: %s, now checking condition' % str(wid))
		if callable(condition):
			res = condition(slot)
			if res:	
				state['widget_scan']['found'] = True
				state['widget_scan']['wid_id'] = wid_list[idx]
				state['widget_scan']['text_contents'] = []
				# print(str(wid))
				return 1
			# else:
				# print('condition failed!')
		# else:
			# print('what happened to you, condition? %s' % str(condition))
	
	# None found, try scrolling down
	print('gs_scan_get_widget_from_list: none found, trying to scroll down')
	should_scroll = False
	
	
	saved_contents = state['widget_scan']['text_contents']
	print('current text contents: %s' % text_contents)
	print('saved text contents: %s' % saved_contents)
	
	if len(saved_contents) != len(text_contents):
		print('gs_scan_get_widget_from_list: should scroll due to len diff')
		should_scroll = True
	else:
		for idx in range(len(text_contents)):
			if text_contents[idx] != saved_contents[idx]:
				print('gs_scan_get_widget_from_list: should scroll due to content diff at idx = %d' % idx)
				should_scroll = True
				break

	if not should_scroll:
		print('gs_scan_get_widget_from_list: Not found & should not scroll! (no content diffs from saved)')
		print('gs_scan_get_widget_from_list: saved contents: %s, current contents: %s' % (saved_contents, text_contents))
		state['widget_scan']['text_contents'] = []
		return 0

	print('gs_scan_get_widget_from_list: scrolling down')
	# save contents for later comparison
	state['widget_scan']['text_contents'] = text_contents
	
	# push scrolling scheme
	from controller_scheme_builders import create_scheme_scroll
	cs = create_scheme_scroll(wid_list[0], 1)
	playtester_push_scheme(cs, 'widget_scan_scroll')
	return 1

def gs_move_mouse_to_widget(slot):
	# type: (GoalSlot)->int
	'''param1 - widget identifier\n
	alternative:\n
	scheme_state {'widget_scan': {'wid_id': TWidgetIdentifier} }
	'''
	wid_identifier = slot.param1
	
	if wid_identifier is None:
		scheme_state = slot.get_scheme_state()
		if 'widget_scan' in scheme_state:
			if 'wid_id' in scheme_state['widget_scan']:
				wid_identifier = scheme_state['widget_scan']['wid_id']

	if wid_identifier is None:
		print('gs_move_mouse_to_widget: wid_identifier is None! scheme_state was %s' % (str(scheme_state)))
	wid = controller_ui_util.obtain_widget(wid_identifier)
	if wid is None:
		return 0
	controller_ui_util.move_mouse_to_widget(wid)
	return 1

def gs_is_widget_visible(slot):
	#type: (GoalSlot)->int
	''' param1 - TWidgetIdentifier
	'''
	wid_identifier = slot.param1
	wid = controller_ui_util.obtain_widget(wid_identifier)
	if wid is None:
		return 0
	return 1

def gs_press_widget(slot):
	# type: (GoalSlot)->int
	'''param1 - widget identifier\n
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

def gs_lmb_down(slot):
	game.mouse_set_button_state(MB_LEFT, 1)
	return 1
def gs_lmb_up(slot):
	game.mouse_set_button_state(MB_LEFT, 0)
	return 1

def gs_tweak_mouse_pos(slot):
	#type: (GoalSlot)->int
	''' { \n
		'mouse_move': {'tweak_x': int, 'tweak_y': int, 'tweak_amount': int, 'use_fine': bool} \n
		}
	'''
	state = slot.get_scheme_state()
	x = state['mouse_move']['tweak_x']
	y = state['mouse_move']['tweak_y']
	amount = state['mouse_move']['tweak_amount']
	use_fine = state['mouse_move']['use_fine']
	tweak_max = state['mouse_move']['tweak_max']

	radius = max( abs(x), abs(y) )
	
	if radius > tweak_max: # try a finer grained search
		if amount == 1 or not use_fine:
			print('mouse tweak failed (reached max limit = %d)' % (tweak_max))
			return 0
		state['mouse_move']['tweak_amount'] = 1
		state['mouse_move']['tweak_x'] = 0
		state['mouse_move']['tweak_y'] = 0
		return 1

	if x == 0 and y == -radius: # end position: top
		state['mouse_move']['tweak_x'] = amount
		state['mouse_move']['tweak_y'] = -radius - amount
		return 1

	dx = amount if y < 0 else -amount
	dy = amount if x > 0 else -amount
	if abs(y) == radius and abs(x) < radius:
		state['mouse_move']['tweak_x'] = x + dx
		return 1
	if abs(x) == radius and abs(y) < radius:
		state['mouse_move']['tweak_y'] = y + dy
		return 1
	# corners
	if x == y: # both == radius or -radius
		state['mouse_move']['tweak_x'] = x + dx
		return 1
	# if x == -radius and y == -radius:
	#     state['mouse_move']['tweak_y'] = y + dy
	#     return 1
	if x == -y:
		state['mouse_move']['tweak_y'] = y + dy
		return 1
	# if x == -radius and y == radius:
	#     state['mouse_move']['tweak_x'] = x + dx
	#     return 1
	return 1

#endregion widget callbacks

#region navigation
def get_current_map():
	if not is_ingame():
		return 5000
	return game.leader.map

def can_access_worldmap():
	from controller_navigation import worldmap_access_maps
	if len(game.party) == 0:
		return False
	map_id = get_current_map()
	return map_id in worldmap_access_maps

def gs_scroll_to_tile(slot):
	loc = slot.param1
	if type(loc) is tuple:
		x,y = loc
	else:
		x,y = location_to_axis(loc)
	scroll_to( x-10, y,  )
	return 1

def gs_center_on_tile(slot):
	'''
	param1 - loc ( obj.location or (x,y) tuple)
	'''
	loc = slot.param1
	center_screen_on( loc )
	return 1

def gs_center_on_obj(slot):
	''' param1 - obj_ref (used with get_object)'''
	obj_ref = slot.param1
	obj = get_object(obj_ref)
	if obj == OBJ_HANDLE_NULL:
		return 0
	loc = obj.location
	center_screen_on(loc)
	return 1


def gs_scroll_to_tile_and_click(slot):
	#type: (GoalSlot)->int
	from controller_scheme_builders import create_move_mouse_to_vacant_pos
	state = slot.state
	if state is None:	
		slot.state = {
			'scrolled': False,
			'hovered': False,
			'tweaked': False,
			'clicked': False,
		}
	loc = slot.param1
	if type(loc) is tuple:
		print('scroll_to_tile_and_click: loc = %s' % (str(loc)) )
	else:
		print('scroll_to_tile_and_click: loc = %s' % ( str(location_to_axis(loc))) )
	
	if not slot.state['scrolled']:
		center_screen_on(loc)
		slot.state['scrolled'] = True
		return 0

	if not slot.state['hovered']:
		controller_ui_util.move_mouse_to_loc(loc)
		slot.state['hovered']=True
		return 0
	if game.hovered != OBJ_HANDLE_NULL: # target not clear
		if slot.state['tweaked']:
			print('scroll_to_tile_and_click: tweaking failed, aborting...')
			return 1
		print('scroll_to_tile_and_click: target not clear, needs tweaking' )
		cs = create_move_mouse_to_vacant_pos(loc)
		Playtester.get_instance().add_scheme(cs, 'scroll_to_tile_and_click__move_mouse')
		slot.state['tweaked'] = True
		Playtester.get_instance().push_scheme('scroll_to_tile_and_click__move_mouse')
		return 0
	if not slot.state['clicked']:
		click_mouse()
		return 1
	return 0

def is_moving_check(slot):
	#type: (GoalSlot)->int
	''' Returns 1 if any party member is moving/rotating (or, is in init stage)'''
	if slot.state is None: # initialize locs
		slot.state = {}
		for n in range(len(game.party)):
			pc = game.party[n]
			slot.state['pc%d' % n] = pc.location
			slot.state['pc%d_rot' % n] = pc.rotation

		slot.state['map'] = get_current_map()
		return 1
	
	result = 0
	for n in range(len(game.party)):
		pc = game.party[n]
		key = 'pc%d' % n
		key_rot = 'pc%d_rot' % n
		if key in slot.state:
			prev_loc = slot.state[key]	
			prev_rot = slot.state[key_rot]
			cur_rot = pc.rotation
			cur_loc = pc.location
			if prev_loc != cur_loc:
				result = 1
				slot.state['pc%d' % n] = pc.location
			elif prev_rot != cur_rot:
				result = 1
				slot.state[key_rot] = cur_rot
			
		else: # in case someone joined along the way... e.g. Elmo in his impromptu dialogue
			slot.state[key] = pc.location
			slot.state[key_rot] = pc.rotation
	return result


def gs_click_and_scroll_to_tile(slot):
	# type: (GoalSlot) -> int
	''' old version, don't use '''
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

def gs_click_on_object(slot):
	#type: (GoalSlot)->int
	'''
	param1 - object ref
	scheme_state['click_object']['obj_ref']
	'''
	
	# print('gs_click_on_object')
	state = slot.state
	obj_ref = slot.param1
	if obj_ref is None:
		scheme_state = slot.get_scheme_state()
		if 'click_object' in scheme_state:
			obj_ref = scheme_state['click_object']['obj_ref']
	if obj_ref is None:
		print('gs_click_on_object: obj_ref not found' )
	
	obj = get_object(obj_ref)
	if obj == OBJ_HANDLE_NULL:
		print('gs_click_on_object: cannot find obj %s specified by obj_ref = ' % str(obj_ref) )
		return 0
	
	if state is None:	
		slot.state = {
			'hovered': False,
			'clicked': False,
		}
		from controller_scheme_builders import create_move_mouse_to_obj
		cs = create_move_mouse_to_obj(obj_ref, True)
		if playtester_push_scheme(cs, 'gs_click_on_object__move_mouse_to_obj'):
			return 1
		# print("coudn't activate scheme " + str(slot.param1))
		return 0
	
	if game.hovered == obj:
		print('gs_click_on_object: clicking object')
		click_mouse()
		return 1
	else:
		print('Error! Hovered item is wrong, expected %s, game.hovered = %s' %( str(obj), str(game.hovered) ) )
	return 0

def gs_condition(slot):
	# param1 - condition callback
	cond_cb= slot.param1
	
	if cond_cb(slot):
		return 1
	return 0

def gs_condition_map_change(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		if not 'map_change_check' in state:
			# print('map change check: initing with %s' % str(game.leader.map))
			state['map_change_check'] = {'map': get_current_map()}
			return 0
		if state['map_change_check']['map'] != get_current_map():
			# print('map change check: current %s is different than previous %s' % (str(get_current_map()), str(state['map_change_check']['map']) ))
			return 1
		# print('map change check: no change %s' % ( str(state['map_change_check']['map']) ))
		return 0

def gs_anti_hang(slot):
	# type: (GoalSlot)->int
	ANTI_HANG_MAX = 10
	state = slot.get_scheme_state()
	if not 'anti_hang' in state:
		state['anti_hang'] = {
			'count': 0,
		}
		return 1
	state['anti_hang']['count'] += 1
	if state['anti_hang']['count'] >= ANTI_HANG_MAX:
		return 0
	return 1

def gs_anti_hang_rapid(slot):
	# type: (GoalSlot)->int
	MAX_COUNT = 1000
	state = slot.get_scheme_state()
	if not 'anti_hang' in state:
		state['anti_hang'] = {
			'count': 0
		}
		for idx, pc in enumerate(game.party):
			state['anti_hang']['pc%d' % idx] = pc.location
		return 1
	
	changed_detected = False
	for idx, pc in enumerate(game.party):
		key = 'pc%d' % idx
		cur_loc = pc.location

		if not key in state['anti_hang']:
			changed_detected = True
			state['anti_hang'][key] = cur_loc
			continue
	
		prev_loc = state['anti_hang'][key]
		if prev_loc != cur_loc:
			changed_detected = True
			state['anti_hang'][key] = cur_loc
			continue
	
	if changed_detected:
		state['anti_hang']['count'] = 0
		return 1
	
	state['anti_hang']['count'] += 1
	if state['anti_hang']['count'] > MAX_COUNT:
		return 0
	return 1

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
	''' old version, don't use '''
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
#endregion

#region dialogue funcs
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

def find_barter_line(dlg_state):
	#type: (dlg.DialogState)->list
	N = dlg_state.reply_count
	for i in range(N):
		reply_opcode = dlg_state.get_reply_opcode(i)
		if reply_opcode in [3, 26]: # barter or NPC barter
			return i
	return -1

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
	'''
	goes through a pre-set reply specification:
	* param1: a list of replies (in linear sequence)
	'''
	
	# print('Disabling automatic dialogue handling')
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

def gs_click_to_talk(slot):
	''' Similar to gs_click_on_object, except it immediately disables the automatic dialogue handler (because it could happen right away)
	param1 - object ref
	scheme_state['click_object']['obj_ref']
	'''
	Playtester.get_instance().dialog_handler_en(False) # halt the automatic dialogue handler
	return gs_click_on_object(slot)

#endregion

#region action funcs
def obj_is_caster(obj):
	#type: (PyObjHandle)->bool
	res = len(obj.spells_known) > 0
	return res

def obj_can_cast(obj, spell_enum, spell_class, spell_level):
	sp = PySpellStore( spell_enum , spell_class, spell_level)
	result = obj.can_cast_spell(sp)
	if not result:
		return False
	if sp.is_naturally_cast():
		if not obj.spontaneous_spells_remaining(sp.spell_class, sp.spell_level): # TODO this disregard that sorcs can cast at a higher level..
			return False
	return True

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

#endregion

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

	do_push = False
	if slot.state is None:
		do_push = True
	
	if do_push:
		print('gs_create_and_push_scheme: ID = %s , args = %s' %(id, str(args)) )
		cs = create_cb(*args)
		slot.state = {}
		
		if playtester_push_scheme(cs,id):
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