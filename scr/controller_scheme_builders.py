from toee import *
from toee import PySpellStore, game
from controller_callbacks_common import *
from controllers import ControlScheme, GoalState, GoalStateStart,GoalStateEnd, ControllerBase, GoalStateCondition, GoalStateCreatePushScheme
from controller_ui_util import WID_IDEN
from controller_navigation import map_connectivity, get_map_course, random_wander_amount
from controller_constants import *
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
		
		GoalStateStart( gs_scan_get_widget_from_list, ('check_result', 100), ('end', 100), {'param1': wid_list, 'param2': check_widget } ),
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

def create_scheme_scroll(wid_identifier, scroll_delta, times = 1):
	#type: (aui.TWidgetIdentifier, int, int)->ControlScheme
	'''
	scroll_delta: 1 for scroll down, -1 for up
	'''
	
	
	# wid_list = [wid_identifier,]
	def gs_init(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		wid = obtain_widget(wid_identifier)
		if wid.is_scrollbar:
			state['scrollbar_wid'] = wid
		else:
			state['scrollbar_wid'] = None
		return 1

	def gs_check_count(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		if not 'widget_scrolling' in state:
			state['widget_scrolling'] = {
				'count': 0,
				'text_contents': []
			}
		
		if times > 0:
			if state['widget_scrolling']['count'] >= times:
				return 0
			state['widget_scrolling']['count'] += 1
			return 1
		
		scrollbar_wid = state['scrollbar_wid'] #type: aui.TWidget
		if scrollbar_wid is not None:
			if scroll_delta > 0: # scroll down
				if scrollbar_wid.scrollbar_value < scrollbar_wid.scrollbar_max:
					return 1
				return 0
			else: # scroll up
				if scrollbar_wid.scrollbar_value > 0:
					return 1
				return 0

		#TODO check contents
		text_contents = []
		for idx in range(len(wid_list)):
			state['widget_scrolling']['idx'] = idx
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

		return 1

	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('move_mouse_to_widget', 100), ('end', 100) ),
	  GoalState('move_mouse_to_widget',gs_move_mouse_to_widget, ('check_count', 100), params={'param1': wid_identifier}),
	  GoalState('check_count', gs_check_count, ('scroll_it', 100), ('end', 100)),
	  GoalState('scroll_it', lambda slot: game.mouse_scroll(-scroll_delta) or 1, ('check_count', 100), ),
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs


def create_move_mouse_to_vacant_pos(loc):
	def gs_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['mouse_move'] = {
			'tweak_x': 0,
			'tweak_y': 0,
			'tweak_amount': 10,
			'tweak_max': 30, # pixels
			'use_fine': False,
		}
		if game.hovered == OBJ_HANDLE_NULL:
			return 0
		
		return 1
	def gs_move_mouse(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()['mouse_move']
		off_x = state['tweak_x']
		off_y = state['tweak_y']
		controller_ui_util.move_mouse_to_loc(loc, off_x, off_y)
		return 1
	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('check_hovered', 100),('end', 100) ),
	  GoalState('move_mouse', gs_move_mouse, ('check_hovered', 100),),
	  GoalStateCondition('check_hovered', lambda slot: game.hovered == OBJ_HANDLE_NULL, ('end', 10), ('tweak', 10) ),
	  GoalState('tweak', gs_tweak_mouse_pos, ('move_mouse', 10), ('end', 10) ),	
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

def create_scheme_go_to_tile( loc, pc = None, DIST_THRESHOLD = 15 ):
	'''loc: PyLong or tuple '''
	if type(loc) is tuple:
		loc = location_from_axis( *loc )
	cs = ControlScheme()

	def get_group():
		if pc is None:
			group = game.party
		else:
			group = [pc,]
		return group

	def gs_go_to_tile_init(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['go_to_tile'] = {
			'map':get_current_map(),
			'try_count': 0,
			'target_tile': location_to_axis(loc)
			}
		
		group = get_group()
		if all([x.is_unconscious() for x in group]):
			print('create_scheme_go_to_tile: cannot do, group %s are all unconscious' % str(group))
			return 0
		
		for n in range(len(group)):
			pc = group[n]
			state['go_to_tile']['pc%d' % n] = pc.location
			state['go_to_tile']['pc%d_rot' % n] = pc.rotation
		return 1

	def gs_try_count_failsafe(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()['go_to_tile']
		if state['try_count'] >= 3:
			print('create_scheme_go_to_tile: try count >= 3, aborting. Destination was %s' % str(state['target_tile']) )
			print('Party locations:')
			
			group = get_group()
			for pc in group:
				print(location_to_axis(pc.location))
			return 0
		state['try_count'] += 1
		
		if pc is None:
			gs_select_all(slot)
		else:
			idx = get_party_idx(pc)
			select_party(idx)
		return 1

	def arrived_at_check(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		
		# failsafe mechanism
		is_toggling_selection = False
		selected = game.selected
		if not 'selected_count' in state:
			state['selected_count'] = len(selected)
		else:
			if state['selected_count'] != len(selected):
				is_toggling_selection = True
		
		not_all_near = False
		group = get_group()
		for pc_ in group:
			if pc_.is_unconscious():
				continue
			if pc_.distance_to(loc) > DIST_THRESHOLD:
				not_all_near = True
		if is_toggling_selection:
			return 1
		if not_all_near:
			return 0

		return 1
	
	cs.__set_stages__([
		GoalStateStart( gs_go_to_tile_init, ('is_inventory_open', 100), ),

		GoalState('is_inventory_open', gs_is_widget_visible, ('close_inventory', 100), ('select_all', 100), params={'param1': WID_IDEN.CHAR_UI_MAIN_EXIT}),
		GoalState('close_inventory', gs_press_widget, ('select_all', 100), params={'param1': WID_IDEN.CHAR_UI_MAIN_EXIT}),


		GoalState('select_all', gs_try_count_failsafe, ('check_loc', 100),('end', 100) ),
		GoalStateCondition('check_loc', arrived_at_check, ('just_scroll', 100), ('scroll_and_click', 100), ),
		GoalState('just_scroll', gs_center_on_tile, ('end', 700), params = {'param1': loc }),
		
		GoalState('scroll_and_click', gs_scroll_to_tile_and_click, ('is_moving_loop', 700), params = {'param1': loc }),
		# GoalState('arrived_at', gs_condition, ('end', 0)        , ('is_moving_loop', 100), params={'param1': arrived_at_check}),
		GoalStateCondition('is_moving_loop' , is_moving_check, ('is_moving_loop', 800), ('check_arrived', 100), ),
		GoalStateCondition('check_arrived', arrived_at_check, ('end', 0), ('select_all', 100), ),
		
		GoalState('end', gs_wait_cb, ('end', 10), ),
	])
	return cs

def create_scheme_wander_around(count_max_def = 50, pc = None):
	import debug
	def gs_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()

		cur_map = get_current_map()
		if cur_map in random_wander_amount:
			count_max = random_wander_amount[cur_map]
		else:
			count_max = count_max_def
		
		state['wander_around'] = {
			'tgt_loc': None,
			'src_loc': None,
			'bias': (0,0),
			'count': 0,
			'count_max': count_max,
		}
		state['push_scheme'] = {
			'id': 'wander_goto_tile',
			'callback': (create_scheme_go_to_tile, ((0,0), pc) )
		}
		return 1

	def get_rand_location(obj, distance = 10, bias = (0,0)):
		x_src,y_src = location_to_axis(obj.location)
		for _ in range(100):
			x = x_src + bias[0] + game.random_range(-distance, distance)
			y = y_src + bias[1] + game.random_range(-distance, distance)
			# x,y = location_to_axis(game.target_random_tile_near_get( obj, distance) )
			if ( abs(x-x_src) + abs(y - y_src) ) < distance / 2:
				continue
			import debug
			result = debug.pathto(obj, x,y)
			if result > 0:
			# if x != 0 and y != 0:
				return x,y
		return 0,0
	def gs_configure_wander(slot):
		# type: (GoalSlot)->int
		leader = game.leader if (pc is None) else pc
		print('gs_configure_wander: leader = %s' % str(leader))
		slot_state = slot.get_scheme_state()
		
		state = slot_state['wander_around']
		if state['count'] >= state['count_max']:
			return 0
		if group_percent_hp(leader) < 66: # go rest if low on HP (or high casualties!)
			return 0
		state['count'] += 1
		prev_src = state['src_loc']
		prev_tgt = state['tgt_loc']
		bias = state['bias']
		x_src,y_src = location_to_axis(leader.location)
		last_diff = (0,0)

		if prev_src is not None and prev_tgt is not None:
			last_diff = (prev_tgt[0] - prev_src[0], prev_tgt[1] - prev_src[1])
			bias_adj = ( (2*last_diff[0]) // 3 , (2*last_diff[1]) // 3 )
			bias_x = (bias[0] * 4 + bias_adj[0]) // 5
			bias_y = (bias[1] * 4 + bias_adj[1]) // 5
			bias = (bias_x, bias_y)

			if abs(prev_tgt[0] - x_src) + abs(prev_tgt[1] - y_src) >= 6: 
				print('zeroing bias because could not reach prev destination')
				bias = (0,0)

			state['bias'] = bias
			print("bias: " + str(bias))
		
		
		state['src_loc'] = (x_src,y_src)
		# if abs(last_diff[0]) + abs(last_diff[1]) >= 7:
		# 	x,y = get_rand_location(leader, 5, last_diff)
		x,y = get_rand_location(leader, 18, bias)
		if x <= 0 or y <= 0:
			#try smaller radius
			x,y = get_rand_location(leader, 10)
			if x <= 0 or y <= 0:
				return 0
		tgt_loc = (x,y)
		state['tgt_loc'] = tgt_loc

		args = (tgt_loc,pc)
		slot_state['push_scheme']['callback'] =\
			 (create_scheme_go_to_tile, args )
		
		# check if there's someone to talk to
		vlist = [x for x in game.obj_list_range(leader.location, 7, OLC_NPC) 
			if (not (x in game.party) and not leader.has_met(x)) and not x.is_unconscious() and debug.pathto(leader, *location_to_axis(x.location) > 0 ) ]
		vlist.sort()
		if len(vlist) > 0:
			args = (vlist[0],)
			slot_state['push_scheme']['callback'] =\
			 (create_talk_to, args )
			
		
		return 1
	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('configure', 100),('end', 100) ),
	  GoalState('configure', gs_configure_wander, ('execute', 100), ('end', 100)),
	  GoalState('execute', gs_create_and_push_scheme , ('configure', 100), ('end', 100), ),
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

def create_move_mouse_to_obj(obj_ref, move_obstructing_pc = False):
	cs = ControlScheme()

	def gs_init_move_mouse(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		obj = get_object(obj_ref)
		print('create_move_mouse_to_obj init: obj ref is %s, loc = %s ; move_obstructing_pc=%s' % (str(obj) , str(location_to_axis(obj.location)), str(move_obstructing_pc) ) )
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
		GoalStateCondition('check_hovered', lambda slot: game.hovered == slot.get_scheme_state()['mouse_move']['obj'], ('end', 100), ('is_pc_obstructing' if move_obstructing_pc else 'tweak', 100) ),

		GoalStateCondition('is_pc_obstructing', lambda slot: (game.hovered in game.party) and move_obstructing_pc == True and not game.hovered.is_unconscious(), ('move_obstructing_pc', 100), ('tweak', 100) ),
		GoalState('move_obstructing_pc', gs_create_and_push_scheme, ('center_on', 100), params={'param1': 'create_move_mouse_to_obj__obstructing_pc_wander', 'param2': (create_scheme_wander_around, (1, game.hovered))} ),
		GoalState('center_on', gs_center_on_obj, ('move_mouse', 100), params={'param1': obj_ref}),


		GoalState('tweak', gs_tweak_mouse_pos, ('move_mouse', 10), ('end', 10) ),
		GoalState('end', gs_wait_cb, ('end', 10)),
	])
	return cs

def create_talk_to(obj_ref):
	def gs_init(slot):
		#type: (GoalSlot)->int
		obj = get_object(obj_ref)
		if obj == OBJ_HANDLE_NULL:
			return 0
		if obj.is_unconscious():
			return 0
		return 1

	def gs_click_mouse(slot):
		# type: (GoalSlot)->int
		Playtester.get_instance().dialog_handler_en(False) # halt the automatic dialogue handler
		click_mouse()
		return 1
		
	def gs_print_error(slot):
		print('Error! Hovered item is wrong, expected %s, game.hovered = %s' %( str(get_object(obj_ref)), str(game.hovered) ) )
		return 1
	cs = ControlScheme()
	# print('gs_click_on_object')
	
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('scroll_to', 100),('end', 100) ),
	  GoalState('scroll_to', gs_center_on_obj, ('move_mouse', 100), ('end', 100), params={'param1': obj_ref} ),
	  GoalState('move_mouse', gs_create_and_push_scheme, ('check_hovered', 100), params={'param1': 'create_talk_to__move_mouse', 'param2': (create_move_mouse_to_obj, (obj_ref,))} ),
	  GoalStateCondition('check_hovered', lambda slot: game.hovered == get_object(obj_ref), ('hover_ok', 100), ('end', 100)),
	  GoalState('hover_error', gs_print_error, ('end', 100)),
	  GoalState('hover_ok', gs_click_mouse, ('check_hovered', 100), params={'param1': 'create_talk_to__move_mouse', 'param2': (create_move_mouse_to_obj, (obj_ref,))} ),
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

