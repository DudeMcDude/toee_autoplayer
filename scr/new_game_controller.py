from controller_ui_util import WID_IDEN
from toee import *
from toee import PySpellStore, game
from controllers import ControlScheme, GoalState, GoalStateStart,GoalStateEnd, ControllerBase, GoalStateCondition, GoalStateCreatePushScheme

from controller_callbacks_common import *
from controller_scheme_builders import *
from controller_navigation import map_connectivity, get_map_course, exterior_maps, random_wander_amount
from controller_constants import *

from utilities import *
import autoui as aui
import controller_ui_util
import tpdp
import gamedialog as dlg
import logbook
import debug

PLAYTEST_EN  = True
SKIP_LOOTING = False
START_NEW_GAME = False
INITIAL_LOAD = ['Moathousing', 'Did some rounds', 'Fighting!']
LOGGING_EN   = True


		
def cheat_buff():
	for pc in game.party:
		if pc.obj_get_int(obj_f_hp_pts) <= 500:
			pc.obj_set_int(obj_f_hp_pts, 100)
			pc.stat_base_set(stat_strength,28)
	return

def gs_master(slot):
	#type: (GoalSlot)->int

	# IMPORTANT NOTE: 
	# 	push_scheme resets slot.state !!!! so don't modify it afterwards, always do:
	#   state[..] = ..; push_scheme(..); return 0

	pt = Playtester.get_instance()
	if slot.state is None:
		slot.state = {
			'counter': 0,
			'rest_needed': False,
			'sell_loot_needed': False,
			'try_go_outside_counter': 0,
			'needs_memorize': True,
		}
		
	else:
		# print('master counter: ', slot.state['counter'])
		slot.state['counter'] += 1
	
	
	if gs_is_main_menu(slot):
		if not START_NEW_GAME:
			pt.add_scheme( create_load_game_scheme(INITIAL_LOAD), 'load_game' )
			pt.push_scheme('load_game')
		else:
			pt.push_scheme('new_game')
		return 0
	
	if len(game.party) == 0:
			return 0
	print('Controller: main state = %s ' % ( str(slot.state) ) )

	if slot.state['counter'] >= 1 and slot.state['counter'] <= 300000:
		cheat_buff()
		if game.quests[18].state != qs_completed:
			pt.add_scheme( create_hommlet_scheme0(), 'hommlet0' )
			pt.push_scheme('hommlet0')
			return 0
		if game.quests[72].state == qs_unknown:
			pt.add_scheme( create_hommlet_scheme1(), 'hommlet1' )
			pt.push_scheme('hommlet1')
			return 0
		
		if slot.state['needs_memorize']:
			slot.state['needs_memorize'] = False
			pt.push_scheme('memorize_spells')
			return 0
		
		leader = game.leader

		game.areas[3] = 1 # nulb
		game.areas[4] = 1 # ToEE
		if can_access_worldmap():
			slot.state['try_go_outside_counter'] = 0
		
		if leader.area == 1: # Hommlet
			if game.party[0].is_unconscious():
				game.party[0].obj_set_int(obj_f_hp_damage, 0) # can't get out of welcome wench when party[0] is dead
			if leader.map == 5001: # Hommlet main
				if slot.state['rest_needed']:
					slot.state['rest_needed'] = False
					pt.push_scheme('rest')
					return 0
				if slot.state['sell_loot_needed']:
					slot.state['sell_loot_needed'] = False
					pt.push_scheme('sell_loot')
					return 0
				random_schemes = ['goto_nulb', 'goto_brigand_tower', 'do_moathouse_randomly']
				# random_schemes = [ 'goto_brigand_tower']
				# random_schemes = [ 'goto_nulb']
				# random_schemes = ['do_moathouse_randomly']
				random_schemes = ['do_temple_randomly']
				random_choice  = game.random_range(0, len(random_schemes)-1)
				pt.push_scheme(random_schemes[random_choice])
				return 0
			# inside building
			pt.push_scheme('exit_building')
			if game.random_range(0,2) == 1:
				restup()
			return 0
		else: # outside Hommlet
			if not can_access_worldmap():
				if slot.state['try_go_outside_counter'] >= 5:
					pt.add_scheme( create_load_game_scheme(INITIAL_LOAD), 'load_game' )
					pt.push_scheme('load_game')
					return 0
				slot.state['try_go_outside_counter'] += 1
				pt.push_scheme('get_worldmap_access')
				return 0
			slot.state['rest_needed'] = True
			slot.state['sell_loot_needed'] = True
			pt.push_scheme('goto_hommlet')
			return 0
		
				
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
	autoplayer.__logging__ = LOGGING_EN
	from controller_console import ControllerConsole
	autoplayer.console = ControllerConsole(autoplayer)

	autoplayer.add_scheme( create_new_game_scheme(), 'new_game' )
	autoplayer.add_scheme( create_true_neutral_scheme(), 'true_neutral_vig' )
	autoplayer.add_scheme( create_hommlet_scheme0(), 'hommlet0')
	autoplayer.add_scheme( create_ui_camp_rest_scheme(), 'ui_camp_rest' )
	autoplayer.add_scheme( create_memorize_clear(), 'memorize_clear_all' )
	autoplayer.add_scheme( create_memorize_spells_all(), 'memorize_spells' )

	autoplayer.add_scheme( create_open_worldmap_ui(), 'open_worldmap')
	autoplayer.add_scheme( create_rest_scheme(), 'rest' )
	autoplayer.add_scheme( create_sell_loot(), 'sell_loot')
	autoplayer.add_scheme( create_prebuff(), 'prebuff')
	

	autoplayer.add_scheme( create_shop_map_scheme(), 'shopmap' )
	autoplayer.add_scheme( create_master_scheme(), 'main' )
	autoplayer.add_scheme( create_goto_area('moathouse', 2), 'goto_moathouse' )
	autoplayer.add_scheme( create_goto_area('south hommlet'), 'goto_hommlet' )
	autoplayer.add_scheme( create_goto_area('nulb', 3), 'goto_nulb' )
	autoplayer.add_scheme( create_goto_area('Temple of Elemental Evil', 4), 'goto_temple' )
	autoplayer.add_scheme( create_brigand_tower_scheme(), 'goto_brigand_tower' )
	
	autoplayer.add_scheme( create_scheme_enter_building(None), 'exit_building' )
	autoplayer.add_scheme( create_get_worldmap_access(), 'get_worldmap_access')
	autoplayer.add_scheme( create_scheme_moathouse(), 'do_moathouse_randomly' )
	autoplayer.add_scheme( create_scheme_temple_random(), 'do_temple_randomly' )
	
	
	autoplayer.set_dialog_handler(dialog_handler)
	autoplayer.set_combat_handler(combat_handler)
	
	autoplayer.push_scheme('main')
	print('Beginning scheme in 1 sec...')
	# autoplayer.set_active(False)
	if PLAYTEST_EN:
		# autoplayer.set_active(True)
		autoplayer.schedule(700)

	return

def create_master_scheme():
	cs = ControlScheme()
	cs.__set_stages__( [
		GoalStateStart( gs_master, ('end', 500) ),
		GoalState('end', gs_master, ('start', 500), ('start',500) )
	])
	return cs

def create_prebuff():
	self_buffs = [spell_mage_armor, spell_shield_of_faith]
	def gs_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['prebuff'] = {
			'casters': [x for x in game.party if obj_is_caster(x)],
			'casters_cast': {},
			
			'cur_caster': OBJ_HANDLE_NULL,
			'spell': None,
			'cast_target': OBJ_HANDLE_NULL,
		}
		if len(state['prebuff']['casters']) == 0:
			return 0
		state['prebuff']['cur_caster'] = state['prebuff']['casters'][-1]
		return 1
	
	def gs_switch_to_next(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()['prebuff']
		state['casters'].pop()
		# print("casters: ", state['casters'])
		if len(state['casters']) == 0:
			return 0
		return 1

	def gs_configure_prebuff(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		caster = state['prebuff']['casters'][-1] #type: PyObjHandle
		state['prebuff']['cur_caster'] = caster
		state['prebuff']['spell'] = None

		arcane_class = caster.highest_arcane_class
		divine_class = caster.highest_divine_class
		
		spells_known_enums  = [x.spell_enum for x in caster.spells_known]
		spells_known_levels = [x.spell_level for x in caster.spells_known]
		
		for sp in caster.spells_known:
			if not sp.spell_enum in self_buffs:
				continue
			if not obj_can_cast(caster, sp.spell_enum, sp.spell_class, sp.spell_level):
				continue
			
			state['prebuff']['cast_target'] = caster
			state['prebuff']['spell'] = sp
			break
		
		if state['prebuff']['spell'] is None:
			return 0
		return 1
	
	def gs_cast_prebuff(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()['prebuff']
		caster = state['cur_caster'] #type: PyObjHandle
		spell  = state['spell'] #type: PySpellStore 
		tgt    = state['cast_target']
		caster.cast_spell(spell.spell_enum, tgt)
		party_idx = list(game.party).index(caster)
		state['casters_cast'][party_idx] = [spell,]
		return 1

	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('configure_prebuff', 300),('end', 100) ),
	  
	  GoalState('configure_prebuff', gs_configure_prebuff, ('cast_prebuff', 300), ('next_prebuffer', 100)),
	  GoalState('cast_prebuff', gs_cast_prebuff, ('next_prebuffer', 1000), ('end', 100) ),
	  GoalState('next_prebuffer', gs_switch_to_next, ('configure_prebuff', 100), ('end', 100),),
	  
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
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
	121: DialogHandler( {1: 0, 30:1, 40: 1} ), # Tower Sentinel
	228: DialogHandler([0,0,0,0,0,0,0]), # kent
	302: DialogHandler( {66: 0, 68: 0, 70: 0, 166: 0, 168: 0, 170: 0, }),
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

def combat_handler(slot):
	#type: (GoalSlot)->None
	cs = ControlScheme()
	def gs_combat_init(slot):
		if game.combat_is_active():
			return 1
		return 0

	def gs_combat_action_handler(slot):
		if not game.combat_is_active():
			print('gs_combat_action_handler: ending because combat is not active')
			return 0
		combat_action_handler(slot)
		return 1

	def gs_combat_end(slot):
		Playtester.get_instance().combat_mode_set(False)
		return 1
	def gs_item_wield_best_all(slot):
		# type: (GoalSlot)->int
		for pc in game.party:
			if pc.type == obj_t_pc:
				pc.item_wield_best_all()
		return 1

	cs.__set_stages__([
		GoalStateStart(gs_combat_init, ('combat_loop', 100), ('end', 100),  ),
		GoalState('combat_loop', gs_combat_action_handler, ('combat_loop', 100), ('loot_critters', 100),  ),
		GoalState('loot_critters', gs_loot_after_combat, ('equip_best', 100),  ),
		GoalState('equip_best', gs_item_wield_best_all, ('end', 100) ),
		GoalState('end',gs_combat_end, ('end', 100),   ),
	])
	id = 'handle_combat'
	Playtester.get_instance().add_scheme(cs, id)
	Playtester.get_instance().push_scheme(id)
	return


def combat_action_handler(slot):
	
	# Playtester.get_instance().interrupt()

	def select_target(obj):
		vlist = game.obj_list_vicinity(obj.location, OLC_NPC)
		best_tgt = OBJ_HANDLE_NULL
		least_dist = 100000
		tgt_priority = []
		for tgt in vlist:
			if tgt.is_friendly(obj):
				continue
			if tgt.is_unconscious():
				continue
			flags = tgt.object_flags_get()
			if flags & OF_DONTDRAW:
				continue
			if flags & OF_CLICK_THROUGH:
				continue
			
			dist = tgt.distance_to(obj)
			if dist < 15:
				if obj.can_melee(tgt):
					dist = 0
			hp_pct = obj_percent_hp(tgt)
			tgt_priority.append( [tgt, dist, hp_pct])
		def sort_key(x):
			dist   = x[1]
			hp_pct = x[2]
			if dist == 0:
				return hp_pct
			return dist + 100
		
		if len(tgt_priority) > 0:
			tgt_priority.sort(key=sort_key)
			print('possible targets: [distance, hp_pct]', tgt_priority)
			return tgt_priority[0][0]
		return OBJ_HANDLE_NULL #best_tgt
	
	obj = game.leader
	if not game.combat_is_active():
		return 500
	if not (obj in game.party):
		return 500
	# TODO charmed/confused PC.. 

	
	def is_out_of_ammo(obj):
		if obj.item_worn_at(item_wear_ammo) == OBJ_HANDLE_NULL:
			return True
		# todo check matching weapon...
		return False
	def is_ranged_weapon(weap):
		#type: (PyObjHandle)->int
		if weap == OBJ_HANDLE_NULL:
			return 0
		weap_flags = weap.obj_get_int(obj_f_weapon_flags)
		if not (weap_flags & OWF_RANGED_WEAPON):
			return 0
		return 1
	def obj_has_ranged_weapon(attachee):
		weap = attachee.item_worn_at(3)
		return is_ranged_weapon(weap)
	

	import tpactions
	actor = tpactions.get_current_tb_actor()
	if obj != actor: # delay
		return 500
	
	act_seq_cur = tpactions.get_cur_seq()
	tgt = select_target(obj)
	if tgt == OBJ_HANDLE_NULL: # end turn for now..
		print('No target, ending turn')
		press_space()
		return 500

	if obj.is_performing():
		return 500
	is_caster = obj_is_caster(obj)
	has_ranged = obj_has_ranged_weapon(obj)

	def should_cast():
		if not is_caster:
			return False
		if act_seq_cur.tb_status.hourglass_state < 4: # Full action bar
			return False
		if obj.d20_query_has_spell_condition(sp_Silence_Hit):
			return False
		return True
	if is_caster:
		# try cast
		if should_cast():
			spells_known = obj.spells_known
			castable_offensive = []
			castable_defensive = []
			castable_buffs     = []
			castable_personal  = []
			castable_count = 0
			for spell in spells_known:
				sp_entry = tpdp.SpellEntry(spell.spell_enum)
				is_offensive = ( sp_entry.ai_spell_type & (1 << 1) ) != 0
				spell_range = sp_entry.get_spell_range_exact(spell.spell_level, obj)
				if not obj_can_cast(obj,spell.spell_enum, spell.spell_class, spell.spell_level):
					continue
				
				if is_offensive:
					if obj.distance_to(tgt) > spell_range:
						continue
					castable_count += 1
					castable_offensive.append(spell)
				elif sp_entry.spellRangeType == tpdp.SpellRangeType.SRT_Personal:
					castable_personal.append(spell)
					castable_count += 1
			castable_count = len(castable_personal) + len(castable_offensive)
			
			offensive_chance = 100
			defensive_chance = 100 - offensive_chance
			will_cast_offensive = len(castable_offensive) > 0
			if will_cast_offensive:
				idx = game.random_range(0, len(castable_offensive)-1)
				spell = castable_offensive[idx]
				tpactions.cur_seq_reset(obj)
				print('Controller: casting spell %s' % (str(spell)) )
				obj.cast_spell(spell.spell_enum, tgt)
				return 1000
			
		# no spells can cast / out of time
		if has_ranged and is_out_of_ammo(obj):
			press_space()
			pass # todo: unequip ranged weapon, go melee?
			return 300
	else:
		if has_ranged and is_out_of_ammo(obj):
			press_space()
			pass # todo: unequip ranged weapon, go melee?
			return 300
				
		
	# restup()
	if True: #obj == game.party[1]: # ariel
		result = obj.ai_strategy_execute(tgt)
		if result == 1:
			return 1000

	# if act_seq_cur.tb_status.hourglass_state >= 4: # Full action bar
	# 	print('Attacking ', tgt)
	# 	if can_cast(spell_magic_missile, stat_level_wizard | 0x80, 1):
	# 		obj.cast_spell(spell_magic_missile, tgt)
	# 		return 500
	# 	perform_action(D20A_UNSPECIFIED_ATTACK, obj, tgt, tgt.location)
	# 	return 500
	# if act_seq_cur.tb_status.hourglass_state >= 2: # Standard Action
	#     # todo
	#     pass
	# if act_seq_cur.tb_status.hourglass_state >= 1: # Move Action
	#     # todo
	#     pass
	print('Ending turn... ')
	press_space()
	return 300

#region callbacks

def gs_move_mouse_to_object(slot):
	# print('gs_move_mouse_to_object')
	# type: (GoalSlot)->int
	obj = get_object( slot.param1 )
	if obj is None:
		return 0 # todo handle this..
	off_x, off_y = 0,0
	if slot.state is not None and 'tweak_x' in slot.state:
		off_x = slot.state['tweak_x']
		off_y = slot.state['tweak_y']
	controller_ui_util.move_mouse_to_obj(obj, off_x, off_y)
	return 1

def gs_scroll_to_tile_and_click(slot):
	#type: (GoalSlot)->int
	
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

	
def gs_handle_dialogue(slot):
	'''
	param1 - callback(ds, presets, slot.state)-> reply idx[int]\n
	param2 - presets [dict]\n
	'''
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

#endregion


#region schemes

def create_rest_scheme():
	rest_map_IDs = {
		AREA_ID_HOMMLET: HOMMLET_INN_MAIN_MAP,
		AREA_ID_MOATHOUSE: MOATHOUSE_TOWER_MAP,
		AREA_ID_TEMPLE: TEMPLE_SECRET_STAIRCASE,
	}
	def init_rest_scheme(slot):
		#type: (GoalSlot)->int
		state =slot.get_scheme_state()

		tgt_map_id = -1
		cur_map = get_current_map()
		if game.leader.area in rest_map_IDs:
			tgt_map_id = rest_map_IDs[game.leader.area]
		else:
			return 0

		args = ( tgt_map_id, )
		
		state['push_scheme'] = {
			'id': 'goto_building',
			'callback': (create_scheme_navigate_to_map, args)
		}
		state['target_map'] = tgt_map_id
		return 1
	
	def check_map(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()

		if state['target_map'] == get_current_map(): 
			return 1
		if state['target_map'] == -1:
			import random_encounter
			sleep_safety = random_encounter.can_sleep()
			if sleep_safety == SLEEP_DANGEROUS or sleep_safety == SLEEP_SAFE:
				return 1
		return 0

	cs = ControlScheme()
	cs.__set_stages__([
		GoalStateStart( init_rest_scheme, ('check_map', 100),('end', 100)  ),
		GoalState('check_map', gs_condition, ('memorize_spells', 100), ('go_building', 100), params={'param1': check_map} ),
		
		GoalState('go_building', gs_create_and_push_scheme, ('memorize_spells', 500),('end', 100)  ),
		GoalState('memorize_spells', gs_push_scheme, ('start_resting', 100), params = {'param1': 'memorize_spells' }),
		GoalState('start_resting', gs_push_scheme, ('end', 500),  params={'param1': 'ui_camp_rest',  } ),
		
		GoalState('end', gs_wait_cb, ('end', 100),  ),
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


def create_scheme_go_to_tile( loc ):
	'''loc: PyLong or tuple '''
	if type(loc) is tuple:
		loc = location_from_axis( *loc )
	cs = ControlScheme()

	def gs_go_to_tile_init(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['go_to_tile'] = {
			'map':get_current_map(),
			'try_count': 0,
			'target_tile': location_to_axis(loc)
			}
		for n in range(len(game.party)):
			pc = game.party[n]
			state['go_to_tile']['pc%d' % n] = pc.location
			state['go_to_tile']['pc%d_rot' % n] = pc.rotation
		return 1

	def gs_try_count_failsafe(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()['go_to_tile']
		if state['try_count'] >= 3:
			print('create_scheme_go_to_tile: try count >= 3, aborting. Destination was %s' % str(state['target_tile']) )
			print('Party locations:')
			for pc in game.party:
				print(location_to_axis(pc.location))
			return 0
		state['try_count'] += 1
		gs_select_all(slot)
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


		
		DIST_THRESHOLD = 15
		not_all_near = False
		for pc in game.party:
			if pc.is_unconscious():
				continue
			if pc.distance_to(loc) > DIST_THRESHOLD:
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

def create_scheme_enter_building( loc, tgt_map_id = None ): #TODO
	cs = ControlScheme()
	DOOR_ICON_PROTO = 2011
	LADDER_DOWN_ICON_PROTO = 2012
	LADDER_UP_ICON_PROTO = 2013
	STAIRS_DOWN_ICON_PROTO = 2014
	STAIRS_UP_ICON_PROTO = 2015
	SECRET_DOOR_ICON_PROTO = 2035
	SECRET_LADDER_DOWN_ICON_PROTO   = 2036
	SECRET_LADDER_UP_ICON_PROTO   = 2037
	SECRET_STAIRS_DOWN_ICON_PROTO = 2038
	SECRET_STAIRS_UP_ICON_PROTO   = 2039
	
	MAP_TRANSFER_PROTOS = (DOOR_ICON_PROTO, LADDER_DOWN_ICON_PROTO,LADDER_UP_ICON_PROTO, STAIRS_DOWN_ICON_PROTO, STAIRS_UP_ICON_PROTO, SECRET_DOOR_ICON_PROTO, SECRET_LADDER_DOWN_ICON_PROTO,SECRET_LADDER_UP_ICON_PROTO, SECRET_STAIRS_DOWN_ICON_PROTO, SECRET_STAIRS_UP_ICON_PROTO)
	def gs_enter_building_init(slot):
		#type: (GoalSlot)->int
		if len(game.party) == 0 or game.leader == OBJ_HANDLE_NULL:
			return 0
		state = slot.get_scheme_state()
		state['map_change_check'] = {'map':  get_current_map() }
		if loc is None: # trying to click something nearby
			obj = get_object( {'proto': MAP_TRANSFER_PROTOS})
			if obj != OBJ_HANDLE_NULL:
				state['click_object'] = { 'obj_ref': {'proto': MAP_TRANSFER_PROTOS, 'guid': obj.__getstate__()} }
		else:
			obj = get_object( {'proto': MAP_TRANSFER_PROTOS, 'location': loc})
			if obj != OBJ_HANDLE_NULL:
				state['click_object'] = {'obj_ref': {'proto': MAP_TRANSFER_PROTOS, 'guid': obj.__getstate__()} }
		return 1
	
	def check_tgt_map(slot):
		#type: (GoalSlot)->int
		# check if scheme can be ended early (because already on the target map ID)
		if tgt_map_id is None or tgt_map_id == -1:
			return 1
		if len(game.party) == 0 or game.leader == OBJ_HANDLE_NULL:
			return 0
		if get_current_map() == tgt_map_id:
			return 0 # already there, abort scheme
		return 1 # needs to proceed with this scheme
	

	if loc is None: # no location given, try nearest door icon
		cs.__set_stages__([
			GoalStateStart( gs_enter_building_init, ('check_tgt_map', 50), ('end', 50) ),

			GoalStateCondition('check_tgt_map', check_tgt_map, ('select_all', 100), ('end', 100), ),
			GoalState('select_all', gs_select_all, ('click_door_icon', 100), ),
			# GoalState('go_to_loc', gs_create_and_push_scheme, ('click_door_icon', 500), params = {'param1': 'goto', 'param2': (create_scheme_go_to_tile, ( loc, ) ) }),

			GoalState('refresh_select_all', gs_select_all, ('map_change_check', 100), ),
			GoalState('map_change_check', gs_condition_map_change, ('end', 100), ('click_door_icon', 100) ),
			GoalState('click_door_icon', gs_click_on_object, ('map_change_loop', 100), params={'param1': {'proto': MAP_TRANSFER_PROTOS} }),
			

			
			GoalState('map_change_loop', gs_condition_map_change, ('end', 200), ('moving_check', 500) ),
			GoalState('moving_check', is_moving_check, ('moving_check', 500), ('refresh_select_all', 100) ),
			

			GoalState('end', gs_wait_cb, ('end', 500), ),	
		])
	else:
		cs.__set_stages__([
			GoalStateStart( gs_enter_building_init, ('check_tgt_map', 50), ('end', 50) ),
			GoalStateCondition('check_tgt_map', check_tgt_map, ('select_all', 100), ('end', 100),),
			
			GoalState('select_all', gs_select_all, ('go_to_loc', 200), ),
			GoalState('go_to_loc', gs_create_and_push_scheme, ('refresh_select_all', 200), params = {'param1': 'enter_building_goto_tile', 'param2': (create_scheme_go_to_tile, ( loc, ) ) }),
			
			GoalState('refresh_select_all', gs_select_all, ('map_change_check', 100), ), # in case we get interrupted along the way
			GoalState('map_change_check', gs_condition_map_change, ('end', 100), ('click_door_icon', 100) ),
			GoalState('click_door_icon', gs_click_on_object, ('map_change_loop', 100), params={'param1': {'proto': MAP_TRANSFER_PROTOS, 'location': loc} }),
			
			GoalState('map_change_loop', gs_condition_map_change, ('end', 200), ('moving_check', 500) ),
			GoalState('moving_check', is_moving_check, ('moving_check', 500), ('check_tgt_map', 100) ),

			GoalState('end', gs_wait_cb, ('end', 500), ),
		])
	return cs

def create_open_worldmap_ui():
	cs = ControlScheme()
	def gs_encounter_exit_dialog_active(slot):
		wid = controller_ui_util.obtain_widget(WID_IDEN.RND_ENC_EXIT_UI_ACCEPT_BTN)
		if wid is None:
			return 0
		return 1
	cs.__set_stages__([
		# check if already there
		GoalStateStart( gs_is_widget_visible, ('end', 100), ('is_townmap_ui', 100), params={'param1': WID_IDEN.WORLDMAP_UI_SELECTION_BTNS[0]} ),
		# no, so check if the townmap ui is active
		GoalState('is_townmap_ui', gs_is_widget_visible, ('press_worldmap', 100), ('click_utilitybar_map', 100), params={'param1': WID_IDEN.TOWNMAP_UI_WORLD_BTN} ) ,
		
		# if neither, click the map button in the toolbar,
		GoalState('click_utilitybar_map', gs_press_widget, ('exiting_random_encounter_check', 500), (), {'param1': WID_IDEN.UTIL_BAR_MAP_BTN } ),
		
		# check dialogue for exiting random encounter
		GoalState('exiting_random_encounter_check', gs_condition, ('press_encounter_exit', 100), ('is_townmap_ui2', 100), params={'param1':gs_encounter_exit_dialog_active }),
		GoalState('press_encounter_exit', gs_press_widget, ('is_townmap_ui2', 100), params={'param1':WID_IDEN.RND_ENC_EXIT_UI_ACCEPT_BTN }),
		
		GoalState('is_townmap_ui2', gs_is_widget_visible, ('press_worldmap', 500), ('end', 100), params={'param1': WID_IDEN.TOWNMAP_UI_WORLD_BTN} ) ,
		
		GoalState('press_worldmap', gs_press_widget, ('end', 300), (), {'param1': WID_IDEN.TOWNMAP_UI_WORLD_BTN } ),
		GoalState('end', gs_wait_cb, ('end', 100))
	])
	return cs

def create_scheme_navigate_to_map(MAP_ID):
	''' Navigates within area
	'''
	def gs_navigate_to_map_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		cur_map = get_current_map()
		tgt_map = MAP_ID
		if not tgt_map in map_connectivity or not cur_map in map_connectivity:
			return 0
		print('create_scheme_navigate_to_map: getting map course')
		map_course = get_map_course(cur_map, tgt_map)
		print('result: ' + str(map_course) )
		state['navigate_to_map'] = {
			'cur_map': cur_map,
			'cur_area': game.leader.area,
			'tgt_map': tgt_map,
			'map_course': map_course,
			'next_loc': None,
			'next_map': None,
		}
		return 1

	def gs_configure_destination(slot):
		''' configures scheme_state['push_scheme']
		'''
		# type: (GoalSlot)->int
		print('create_scheme_navigate_to_map: configuring destination...')
		state = slot.get_scheme_state()
		cur_map = get_current_map() 
		tgt_map = state['navigate_to_map']['tgt_map']
		
		map_course = state['navigate_to_map']['map_course']
		if map_course is None:
			return 0

		
		for idx,map_id in enumerate(map_course):
			if map_id != cur_map:
				continue
			next_map = map_course[idx+1]
			if not (type(map_connectivity[cur_map][next_map]) == tuple):
				next_loc = map_connectivity[cur_map][next_map][0]
			else:
				next_loc = map_connectivity[cur_map][next_map]
			state['navigate_to_map']['next_loc'] = next_loc
			state['navigate_to_map']['next_map'] = next_map
			state['push_scheme']  = {
				'id': 'navigate_to_map_tmp', 
				'callback': (create_scheme_enter_building, (next_loc, next_map))
				}
			return 1
		
		return 1

	
	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_navigate_to_map_init, ('check_map', 100),('end', 100) ),
	  GoalState('check_map', lambda slot: get_current_map() == MAP_ID, ('end', 100), ('configure_destination', 100),   ),
	  GoalState('configure_destination', gs_configure_destination, ('go_next', 100), ('end', 100),),
	  GoalState('go_next', gs_create_and_push_scheme, ('check_map', 100), ('end', 100), ),	
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

def create_get_worldmap_access():
	cs = ControlScheme()
	worldmap_access_map_by_area = {
		0: None,
		2: MOATHOUSE_EXTERIOR_MAP,
		4: TEMPLE_COURTYARD_MAP,
		8: MOATHOUSE_CAVE_EXIT_MAP,
	}
	special_map_cases = {
		TEMPLE_TOWER_EXTERIOR_MAP: TEMPLE_COURTYARD_MAP
	}
	def gs_init_get_worldmap_access(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		cur_map = get_current_map()
		if not (game.leader.area in worldmap_access_map_by_area):
			print('worldmap_access_map_by_area: not defined for area [%d]' % game.leader.area)
			return 0
		tgt_map = worldmap_access_map_by_area[game.leader.area]
		
		if cur_map in special_map_cases:
			tgt_map = special_map_cases[cur_map]
		
		if tgt_map is None:
			print('gs_init_get_worldmap_access: tgt map is None')
			return 0
		
		map_course = get_map_course(cur_map, tgt_map)
		if map_course is None:
			return 0
		
		state['navigate_to_map'] = {
			'cur_map': cur_map,
			'cur_area': game.leader.area,
			'tgt_map': tgt_map,
			'map_course': map_course,
			'next_loc': None,
			'next_map': None,
		}
		
		state['push_scheme']  = {
			'id': 'get_worldmap_access_tmp', 
			'callback': (create_scheme_navigate_to_map, (tgt_map,))
			}
		return 1

	
	cs.__set_stages__([
		GoalStateStart( gs_init_get_worldmap_access, ('check_access_worldmap', 100), ),
		GoalStateCondition('check_access_worldmap', lambda slot: can_access_worldmap(), ('end', 100), ('do_map_navigation', 100) ),
		GoalState('do_map_navigation', gs_create_and_push_scheme, ('check_access_worldmap', 100), ('end', 100), ),
		GoalState('end', gs_wait_cb, ('end', 100), )
	])
	return cs

def create_goto_area(area_name, area_id = None):
	#type: (str, int)->ControlScheme

	# TODO: handle if not outdoors... (seek exit or sthg like that)
	# TODO: what if we're already there? currently handle this above...
	cs = ControlScheme()
	wid_list = WID_IDEN.WORLDMAP_UI_SELECTION_BTNS

	def gs_goto_area_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['map_change_check'] = {'map': get_current_map()}
		return 1
	
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
		print('obtained widget: %s'%str(wid))
		print('rendered text: ', wid.rendered_text)
		if wid.rendered_text.lower().find(area_name.lower()) >= 0:
			return True
		return False

	def gs_found(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		if state['widget_scan']['found']:
			# print('found it', slot.state_prev['idx'])
			return 1
		return 0
	
	
	def gs_survival_check_active(slot):
		wid = controller_ui_util.obtain_widget(WID_IDEN.RND_ENC_UI_ACCEPT_BTN)
		if wid is None:
			return 0
		return 1
	
	def gs_is_townmap_active(slot):
		wid = controller_ui_util.obtain_widget(WID_IDEN.TOWNMAP_UI_WORLD_BTN)
		if wid is None:
			return 0
		return 1


	cs.__set_stages__(
		[
			GoalStateStart( gs_goto_area_init, ('check_outdoors',100 ), ),
			GoalStateCondition('check_outdoors', lambda slot: can_access_worldmap(), ('open_worldmap', 500), ('end', 100), ) ,
		
			GoalState('open_worldmap', gs_push_scheme, ('find_acq_loc_btn', 100), params={'param1': 'open_worldmap'}),
		
			GoalState('find_acq_loc_btn', gs_scan_get_widget_from_list, ('check_result', 100), (), {'param1': wid_list, 'param2': check_widget } ),
			GoalState('check_result', gs_found, ('press_acq_loc_btn', 100), ('end', 300),  ),
			GoalState('press_acq_loc_btn', gs_press_widget, ('wait_loop', 200), (), {'param1': None } ),

			GoalState('wait_loop', gs_wait_cb, ('wait_for_map_change', 500), ) ,	
			GoalState('wait_for_map_change', gs_condition_map_change, ('is_intended_area', 100), ('survival_check_window', 100), ) ,
			GoalStateCondition('is_intended_area', lambda slot: (game.leader.area == area_id) or (area_id is None), ('end', 100), ('await_combat', 1200), ) ,

			# map hasn't changed yet - periodically check for "Survival Check" window (random encounter Accept/Deny)
			GoalStateCondition('survival_check_window', gs_survival_check_active, ('press_encounter_accept', 100), ('wait_loop', 100),  ) ,
			GoalState('press_encounter_accept', gs_press_widget, ('await_combat', 100), params={'param1':WID_IDEN.RND_ENC_UI_ACCEPT_BTN }),
			GoalState('await_combat', gs_wait_cb, ('is_intended_area2', 1200), ),	

			GoalStateCondition('is_intended_area2', lambda slot: (game.leader.area == area_id) or (area_id is None), ('end', 100), ('start', 100), ) ,

			GoalState('end', gs_wait_cb, ('end', 500), ) ,	
		])
	return cs

def create_hommlet_scheme1():
	cs = ControlScheme()
	JAROO_DOOR_ICON_LOC = (614, 518)
	GROVE_ENTRANCE_LOC = (625, 520)
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
		GoalStateStart( gs_condition, ('go_jaroo', 100), ('start2', 100), params={'param1': lambda slot: get_current_map() == 5001}),
		GoalState('start2', gs_condition, ('handle_jaroo', 100), ('start', 100), params={'param1': lambda slot: get_current_map() == 5042}), # wait until this is fulfilled
		
		GoalState('go_jaroo', gs_create_and_push_scheme, ('handle_jaroo', 100), params={'param1': 'go_grove', 'param2': (create_scheme_enter_building, (GROVE_ENTRANCE_LOC,5042) ) })
		] +
		
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
	WENCH_DOOR_ENTRANCE_LOC = (619, 405)
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
		GoalStateStart( gs_condition, ('go_inn', 100), ('handle_inn', 100), params={'param1': lambda slot: get_current_map() == 5001}),
		GoalState('go_inn', gs_create_and_push_scheme, ('handle_inn', 100), params={'param1': 'go_wench', 'param2': (create_scheme_enter_building, (WENCH_DOOR_ENTRANCE_LOC, 5007) )}),
		] +
		
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

def create_brigand_tower_scheme():
	cs = ControlScheme()
	
	def gs_brigand_tower_init(slot):
		# type: (GoalSlot)->int
		if len(game.party) == 0:
			return 0
		state = slot.get_scheme_state()
		state['tower_brigands'] = {'quicksave_counter': 0}
		return 1
	def gs_make_quicksave(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['tower_brigands']['quicksave_counter'] += 1
		press_quicksave()
		return 1
	def gs_make_quickload(slot):
		# type: (GoalSlot)->int
		press_quickload()
		return 1
	def gs_brigand_tower_end(slot):
		return 1
	
	cs.__set_stages__([
		GoalStateStart( gs_brigand_tower_init, ('check_temple_area', 100), ),

		GoalStateCondition('check_temple_area', lambda slot: game.leader.area == 4, ('check_exterior_map', 100), ('go_temple', 100), ),
		GoalState('go_temple', gs_push_scheme, ('check_exterior_map', 100), params={'param1': 'goto_temple'}),
		
		GoalStateCondition('check_exterior_map', lambda slot: get_current_map() == TEMPLE_COURTYARD_MAP, ('go_temple_tower_map', 100), ('check_temple_tower_ext', 100), ),
		GoalStateCreatePushScheme('go_temple_tower_map', 'go_temple_tower_exterior', create_scheme_enter_building, (map_connectivity[TEMPLE_COURTYARD_MAP][TEMPLE_TOWER_EXTERIOR_MAP], TEMPLE_TOWER_EXTERIOR_MAP ),('check_temple_tower_ext', 100) ),
		
		GoalStateCondition('check_temple_tower_ext', lambda slot: get_current_map() == TEMPLE_TOWER_EXTERIOR_MAP, ('make_quicksave_check', 100), ('go_temple', 100), ),
		GoalStateCondition('make_quicksave_check', lambda slot: slot.get_scheme_state()['tower_brigands']['quicksave_counter'] < 5, ('make_quicksave', 100), ('do_prebuff', 100)),
		GoalState('make_quicksave', gs_make_quicksave, ('do_prebuff', 100)),
		GoalState('do_prebuff', gs_push_scheme, ('go_temple_tower_interior', 100), params={'param1': 'prebuff'}),
		GoalStateCreatePushScheme('go_temple_tower_interior', 'go_temple_tower_interior', create_scheme_enter_building, (map_connectivity[TEMPLE_TOWER_EXTERIOR_MAP][TEMPLE_TOWER_INTERIOR_MAP], TEMPLE_TOWER_INTERIOR_MAP ),('await_combat', 100) ),

		GoalState('await_combat', gs_wait_cb, ('make_quickload_check', 2000)),
		GoalState('make_quickload_check', lambda slot: slot.get_scheme_state()['tower_brigands']['quicksave_counter'] < 5, ('make_quickload', 100), ('check_temple_tower_int', 100)),
		GoalState('make_quickload', gs_make_quickload, ('check_temple_tower_ext', 5000)),

		GoalStateCondition('check_temple_tower_int', lambda slot: get_current_map() == TEMPLE_TOWER_INTERIOR_MAP, ('exit_tower', 100), ('check_temple_tower_ext2', 100), ),
		GoalStateCreatePushScheme('exit_tower', 'exit_temple_tower', create_scheme_enter_building, (map_connectivity[TEMPLE_TOWER_INTERIOR_MAP][TEMPLE_TOWER_EXTERIOR_MAP], TEMPLE_TOWER_EXTERIOR_MAP ), ('check_temple_tower_ext2', 100) ),

		GoalStateCondition('check_temple_tower_ext2', lambda slot: get_current_map() == TEMPLE_TOWER_EXTERIOR_MAP, ('go_temple_courtyard', 100), ('end', 100), ),
		GoalState('go_temple_courtyard', gs_push_scheme, ('end', 100), params={'param1': 'get_worldmap_access'} ),

		GoalState('end', gs_brigand_tower_end, ('end', 100), )
	])
	return cs

#WIP
def create_scheme_go_random_map():
	def gs_random_map_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		
		cur_map = get_current_map()
		tgt_map = cur_map
		N = game.random_range(2,7)
		for i in range(N):
			N_connections = len(map_connectivity[tgt_map])
			if N_connections == 0:
				raise Exception('no connections defined, this is gonna screw things up')
			map_idx = game.random_range(0, N_connections-1)
			keys = list(map_connectivity[tgt_map].keys())
			tgt_map = keys[map_idx]
		
		state['push_scheme']  = {
				'id': 'navigate_to_random_map_tmp', 
				'callback': (create_scheme_navigate_to_map, (tgt_map,))
				}
			
		return 1

	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_random_map_init, ('navigate_to_random_map', 100),('end', 100) ),
	  GoalState('navigate_to_random_map', gs_create_and_push_scheme, ('end', 100), ('end', 100) ),
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

def create_scheme_wander_around(count_max_def = 50):
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
			'callback': (create_scheme_go_to_tile, ((0,0),) )
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
		slot_state = slot.get_scheme_state()
		
		state = slot_state['wander_around']
		if state['count'] >= state['count_max']:
			return 0
		if group_percent_hp(game.leader) < 66: # go rest if low on HP (or high casualties!)
			return 0
		state['count'] += 1
		prev_src = state['src_loc']
		prev_tgt = state['tgt_loc']
		bias = state['bias']
		x_src,y_src = location_to_axis(game.leader.location)
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
		# 	x,y = get_rand_location(game.leader, 5, last_diff)
		x,y = get_rand_location(game.leader, 18, bias)
		if x <= 0 or y <= 0:
			#try smaller radius
			x,y = get_rand_location(game.leader, 10)
			if x <= 0 or y <= 0:
				return 0
		tgt_loc = (x,y)
		state['tgt_loc'] = tgt_loc

		args = (tgt_loc,)
		slot_state['push_scheme']['callback'] =\
			 (create_scheme_go_to_tile, args )
		
		# check if there's someone to talk to
		vlist = [x for x in game.obj_list_range(game.leader.location, 7, OLC_NPC) 
			if (not (x in game.party) and not game.leader.has_met(x)) and not x.is_unconscious() and debug.pathto(game.leader, *location_to_axis(x.location) > 0 ) ]
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

def create_scheme_moathouse():
	AREA_ID = 2
	AREA_WORLDMAP_NAME = 'moathouse'
	AREA_EXTERIOR_MAP = exterior_maps[AREA_ID]
	WANDER_COUNT = 77
	random_count = game.random_range(2,7)
	def gs_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['go_random_map'] = {
			'counter': 0,
			'max': random_count,
		}
		return 1
	def gs_check_counter(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()['go_random_map']
		state['counter'] += 1
		if state['counter'] >= state['max']:
			return 0
		if group_percent_hp(game.leader) < 66: # go rest if low on HP (or high casualties!)
			return 0
		return 1
	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('check_area', 100),('end', 100) ),
	
	  GoalStateCondition('check_area', lambda slot: game.leader.area == AREA_ID, ('check_exterior_map', 100), ('go_area', 100), ),
	  GoalStateCreatePushScheme('go_area', 'go_area_%d' % AREA_ID , create_goto_area, (AREA_WORLDMAP_NAME, AREA_ID), ('check_exterior_map', 100), ),
	  
	  GoalState('check_exterior_map', lambda slot: get_current_map() == AREA_EXTERIOR_MAP, ('go_random_map', 100), ('navigate_to_exterior_map', 100), ),
	  GoalStateCreatePushScheme('navigate_to_exterior_map', 'go_to_map', create_scheme_navigate_to_map, (AREA_EXTERIOR_MAP, ),('check_exterior_map', 100) ),
		
	  GoalStateCreatePushScheme('go_random_map', 'go_to_map', create_scheme_go_random_map, (), ('wander_around', 100) ),
	  GoalStateCreatePushScheme('wander_around', 'wander_around', create_scheme_wander_around, (WANDER_COUNT,), ('check_counter', 100) ),
	  GoalStateCondition('check_counter', gs_check_counter, ('go_random_map', 100), ('end', 100) ),
	  
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

def create_scheme_temple_random():
	AREA_ID = 4
	AREA_WORLDMAP_NAME = 'temple of elemental evil'
	AREA_EXTERIOR_MAP = exterior_maps[AREA_ID]
	WANDER_COUNT = 77
	random_count = game.random_range(2,7)
	def gs_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['go_random_map'] = {
			'counter': 0,
			'max': random_count,
		}
		return 1
	def gs_check_counter(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()['go_random_map']
		state['counter'] += 1
		if state['counter'] >= state['max']:
			return 0
		if group_percent_hp(game.leader) < 66: # go rest if low on HP (or high casualties!)
			return 0
		return 1
	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('check_area', 100),('end', 100) ),
	
	  GoalStateCondition('check_area', lambda slot: game.leader.area == AREA_ID, ('check_exterior_map', 100), ('go_area', 100), ),
	  GoalStateCreatePushScheme('go_area', 'go_area_%d' % AREA_ID , create_goto_area, (AREA_WORLDMAP_NAME, AREA_ID), ('check_exterior_map', 100), ),
	  
	  GoalState('check_exterior_map', lambda slot: get_current_map() == AREA_EXTERIOR_MAP, ('go_random_map', 100), ('navigate_to_exterior_map', 100), ),
	  GoalStateCreatePushScheme('navigate_to_exterior_map', 'go_to_map', create_scheme_navigate_to_map, (AREA_EXTERIOR_MAP, ),('check_exterior_map', 100) ),
		
	  GoalStateCreatePushScheme('go_random_map', 'go_to_map', create_scheme_go_random_map, (), ('wander_around', 100) ),
	  GoalStateCreatePushScheme('wander_around', 'wander_around', create_scheme_wander_around, (WANDER_COUNT,), ('check_counter', 100) ),
	  GoalStateCondition('check_counter', gs_check_counter, ('go_random_map', 100), ('end', 100) ),
	  
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

def get_obj_inventory(obj, lootable_only = True):
	#type: (PyObjHandle, bool)->list[PyObjHandle]
	result = []
	if obj.is_critter():
		inven_count = obj.obj_get_idx_obj_size(obj_f_critter_inventory_list_idx)
		for i in range(0, inven_count):
			item = obj.obj_get_idx_obj(obj_f_critter_inventory_list_idx, i)
			if item == OBJ_HANDLE_NULL:
				continue
			if lootable_only and (item.obj_get_int(obj_f_item_flags) & OIF_NO_LOOT) != 0:
				continue
			result.append(item)
	elif obj.type == obj_t_container:
		inven_count = obj.obj_get_idx_obj_size(obj_f_container_inventory_list_idx)
		for i in range(0, inven_count):
			item = obj.obj_get_idx_obj(obj_f_container_inventory_list_idx, i)
			if item == OBJ_HANDLE_NULL:
				continue
			if lootable_only and (item.obj_get_int(obj_f_item_flags) & OIF_NO_LOOT) != 0:
				continue
			result.append(item)
	else:
		return result
	return result

def gs_loot_after_combat(slot):
	# type: (GoalSlot)->int
	if slot.state is None:
		# init
		slot.state = {
			'lootable_critters': []
		}
		for obj in game.obj_list_vicinity(game.leader.location, OLC_NPC):
			if obj in game.party:
				continue
			if not obj.is_unconscious():
				continue
			inventory = get_obj_inventory(obj)
			if len(inventory) == 0:
				continue
			slot.state['lootable_critters'].append(obj)
	
	state = slot.state
	
	if len(state['lootable_critters']) == 0:
		return 1
	if SKIP_LOOTING:
		return 1
	
	obj = state['lootable_critters'].pop()
	cs = create_loot_critter_scheme(obj)
	Playtester.get_instance().add_scheme(cs, 'loot_critter')
	Playtester.get_instance().push_scheme('loot_critter')
	return 0

def create_loot_critter_scheme(obj):
	#type: (PyObjHandle)->ControlScheme
	cs = ControlScheme()
	WID_ID_LOOT_ALL_BTN   = WID_IDEN.CHAR_LOOTING_UI_TAKE_ALL_BTN
	WID_ID_EXIT_INVENTORY = WID_IDEN.CHAR_UI_MAIN_EXIT
	WID_ID_INVEN_FULL     = WID_IDEN.POPUP_UI_OK_BTN
	WID_ID_KEY_ENTRY      = WID_IDEN.LOGBOOK_UI_KEY_ENTRY_ACCEPT
	obj_loc = obj.location
	def gs_loot_critter_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['loot_critter'] = {
			'obj': obj,
			'looters_full': [],
			'looter_priority': [x for x in range(0, len(game.party)) if game.party[x].type == obj_t_pc]
		}
		state['click_object'] = {
			'obj_ref': {'guid': obj.__getstate__(), 'location': obj.location }
		}
		
		# sort by strength, descending
		def sort_key(x):
			strength = game.party[x].stat_base_get(stat_strength)
			return strength
		
		state['loot_critter']['looter_priority'].sort(key=sort_key, reverse=True)
		return 1

	def gs_check_lootable(slot):
		# type: (GoalSlot)->int
		if not obj.is_unconscious():
			return 0
		inventory = get_obj_inventory(obj)
		for item in inventory:
			if item.type == obj_t_money:
				return 1
			if item.type in [obj_t_armor , obj_t_weapon]:
				if item.obj_get_int(obj_f_item_worth) < 10: # less than 1 silver - skip
					continue
			# more criteria?
			return 1
		return 0
	
	def gs_mark_looter_full(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		for x in state['loot_critter']['looter_priority']:
			if x in state['loot_critter']['looters_full']:
				continue
			state['loot_critter']['looters_full'].append(x)
			return 1
		return 1

	def gs_select_looter(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		for x in state['loot_critter']['looter_priority']:
			if x in state['loot_critter']['looters_full']:
				continue
			select_party(x)
			return 1
		return 0
	def gs_check_fogged(slot):
		# type: (GoalSlot)->int
		
		for p in game.party:
			if p.distance_to(obj_loc) < 20:
				return 0
		state = slot.get_scheme_state()
		state['push_scheme'] = {
			'id': 'critter_loot_approach',
			'callback': (create_scheme_go_to_tile, (obj_loc,) ),
		}
		return 1

	cs.__set_stages__([
		# TODO: prioritize mules / unburdened
		GoalStateStart( gs_loot_critter_init, ('check_lootable_inventory', 100),  ),
		
		GoalStateCondition('check_lootable_inventory', gs_check_lootable, ('select_all', 100), ('end', 100)),

		GoalState('select_all', gs_select_all, ('center_on_target', 100)),
		GoalState('center_on_target', gs_center_on_tile, ('check_loc_in_fog', 330), params={'param1': obj_loc}),
		GoalState('check_loc_in_fog', gs_check_fogged, ('approach', 100), ('click_object', 100)), # will set state['push_scheme'] to 'critter_loot_approach', create_scheme_go_to_tile
		GoalState('approach', gs_create_and_push_scheme, ('click_object', 100), ),
		GoalState('click_object', gs_click_on_object, ('wait_for_inventory_loop', 100), ('end', 100) ),

		GoalState('wait_for_inventory_loop', gs_is_widget_visible, ('select_looter', 100), ('check_is_moving', 100), params={'param1': WID_ID_LOOT_ALL_BTN}),
		GoalState('check_is_moving', is_moving_check, ('check_is_moving', 100), ('anti_hang', 100), ),
		GoalState('anti_hang', gs_anti_hang, ('wait_for_inventory_loop', 100), ('end', 100)),
		
		# after bringing up the looting UI, select party member to do the looting
		GoalState('select_looter', gs_select_looter, ('press_loot_all', 100), ('exit_inventory', 100)),
		GoalState('press_loot_all', gs_press_widget, ('check_inventory_full_dlg', 100), params={'param1': WID_ID_LOOT_ALL_BTN}),


		# GoalState('check_can_proceed', gs_wait_cb, ('check_inventory_full_dlg', 100), ), # note: I've checked that both the below dialogus cannot occur at the same time (getting the key requires actually transferring it, so it won't happen if the inventory gets filled up)
		GoalState('check_inventory_full_dlg', gs_is_widget_visible, ('inventory_full_ok', 100), ('check_key_entry_dlg', 100), params={'param1': WID_ID_INVEN_FULL}),
		GoalState('inventory_full_ok', gs_press_widget, ('mark_loot_full', 100), params={'param1': WID_ID_INVEN_FULL}),

		GoalState('check_key_entry_dlg', gs_is_widget_visible, ('press_key_entry_accept', 100),('exit_inventory', 100), params={'param1': WID_ID_KEY_ENTRY}),
		GoalState('press_key_entry_accept', gs_press_widget, ('exit_inventory', 100), params={'param1': WID_ID_KEY_ENTRY}),
		
		GoalState('mark_loot_full', gs_mark_looter_full, ('select_looter', 100), ),
		
		
		GoalState('exit_inventory', gs_press_widget, ('end', 100), params={'param1': WID_ID_EXIT_INVENTORY}),
		GoalStateEnd( gs_wait_cb, ('end', 10),  ),
	])
	return cs

def create_barter_ui_sell_loot(obj):
	#type: (PyObjHandle)->None
	cs = ControlScheme()
	
	def gs_init_barter_sell(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['selling_loot'] = {
			'slots_to_sell': []
		}
		try:
			x = list(game.party).index(obj)
			if x >= 0:
				print('Selecting party member %s to sell loot' % game.party[x])
				select_party(x)
		except ValueError:
			print('Could not find %s in party' % str(obj))
		
		for idx in range(0, 24):
			item = obj.inventory_item(idx)
			if item == OBJ_HANDLE_NULL:
				continue
			# print('item idx = 0 is %s' % str(item))
			item_flags = item.obj_get_int(obj_f_item_flags)
			if item_flags & OIF_IS_MAGICAL:
				if (item_flags & OIF_IDENTIFIED) == 0:
					continue
				continue # for now..
			if (item_flags & OIF_WONT_SELL) != 0:
				continue
			if item.obj_get_int(obj_f_item_worth) < 10: # less than 1 silver - skip
					continue
			state['selling_loot']['slots_to_sell'].append(idx)
		
		return 1
	
	def gs_select_inventory_item_slot(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		slots_to_sell = state['selling_loot']['slots_to_sell']
		# print('slots_to_sell: %s' % str(slots_to_sell))
		if len(slots_to_sell) == 0:
			return 0
		wid_idx = state['selling_loot']['slots_to_sell'].pop()
		# print('wid_idx: %d' % wid_idx)
		wid_id = WID_IDEN.CHAR_UI_INVENTORY_BTNS[wid_idx]
		state['widget_scan'] = {
			'wid_id' : wid_id,
		}
		return 1
	
	def gs_select_container_item_slot(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		wid_id = WID_IDEN.CHAR_LOOTING_UI_BTNS[0]
		state['widget_scan'] = {
			'wid_id' : wid_id,
		}
		return 1
	
	cs.__set_stages__([
		GoalStateStart( gs_init_barter_sell, ('check_inventory_ui_open', 100), ('end', 100)),

		GoalState('check_inventory_ui_open', gs_is_widget_visible, ('select_inventory_item', 100), ('end', 100), params={'param1': WID_IDEN.CHAR_LOOTING_UI_TAKE_ALL_BTN}), # same widget is used for both looting and barter
		GoalState('select_inventory_item', gs_select_inventory_item_slot, ('move_mouse', 100),('end', 100) ),
		GoalState('move_mouse', gs_move_mouse_to_widget, ('mouse_down', 330), ('end', 100), ),
		GoalState('mouse_down', gs_lmb_down, ('select_container_item_slot', 100),  ),
		GoalState('select_container_item_slot', gs_select_container_item_slot, ('move_mouse_to_container', 200), ),
		GoalState('move_mouse_to_container', gs_move_mouse_to_widget, ('mouse_up', 330), ('end', 100), ),
		GoalState('mouse_up', gs_lmb_up, ('is_transfer_slider_active', 100),  ),
		GoalState('is_transfer_slider_active', gs_is_widget_visible, ('press_slider_ok', 100), ('check_inventory_ui_open', 100) , params={'param1': WID_IDEN.SLIDER_UI_OK_BTN}),
		GoalState('press_slider_ok', gs_press_widget, ('check_inventory_ui_open', 330), params={'param1': WID_IDEN.SLIDER_UI_OK_BTN}),
		# handle "no room"..
		
		GoalStateEnd( gs_wait_cb, ('end', 10), )
	])
	return cs

def gs_sell_loot(slot):
	# type: (GoalSlot)->int
	if slot.state is None:
		slot.state = {
			'need_to_sell': [x for x in game.party if x.type == obj_t_pc]
		}
	state = slot.state
	
	if len(slot.state['need_to_sell']) == 0:
		return 1
	obj = state['need_to_sell'].pop()
	cs = create_barter_ui_sell_loot(obj)
	Playtester.get_instance().add_scheme(cs, 'loot_sell_ui')
	Playtester.get_instance().push_scheme('loot_sell_ui')
	return 1

def create_sell_loot():
	cs = ControlScheme()
	def smyth_barterer(ds, presets, state):
		#type: (dlg.DialogState, dict, dict)->int
		N = ds.reply_count
		idx = find_barter_line(ds)
		if idx >= 0:
			return idx
		return 0
	cs.__set_stages__([
		GoalStateStart(gs_wait_cb, ('talk_to_smyth', 100), ),
		
		GoalState('talk_to_smyth', gs_center_on_tile, ('talk2', 500), params = {'param1': (582, 434) }),
		GoalState('talk2', gs_click_to_talk, ('talk3', 100), params = {'param1': {'proto': 14010, 'location': location_from_axis(582, 434)}} ),
		GoalState('talk3', gs_handle_dialogue, ('sell', 500), (), {'param1': smyth_barterer, 'param2': {} } ),
		GoalState('sell', gs_sell_loot, ('exit_barter_ui', 500),  ),
		GoalState('exit_barter_ui', gs_press_widget, ('end', 100), params={'param1': WID_IDEN.CHAR_UI_MAIN_EXIT}),

		GoalStateEnd( gs_wait_cb, ('end', 100))
	])
	return cs

def create_open_char_ui(obj):
	def gs_init(slot):
		#type: (GoalSlot)->int
		return 1
	
	def gs_press_char_number(slot):
	# type: (GoalSlot)->int
		idx = get_party_idx(obj)
		select_party(idx)
		return 1
	
	def gs_press_inventory_hotkey(slot):
		# type: (GoalSlot)->int
		press_key(DIK_I)
		return 1
	
	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_is_widget_visible, ('select_char', 100), ('open_char_ui', 100), params={'param1': WID_IDEN.CHAR_UI_MAIN_EXIT}),
	  GoalState('open_char_ui', gs_press_inventory_hotkey, ('check_inventory_again', 100), ),
	  GoalState('check_inventory_again', gs_is_widget_visible, ('select_char', 100), ('end', 100), params={'param1': WID_IDEN.CHAR_UI_MAIN_EXIT}),
	  
	  GoalState('select_char', gs_press_char_number, ('end', 100)),
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

def create_memorize_spells_all():
	def gs_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['memorize'] = {
			'spellcasters_queue': [pc for pc in game.party if len(pc.spells_known) > 0],
		}
		if len(state['memorize']['spellcasters_queue']) == 0:
			return 0
		return 1
	
	def gs_set_memorizer(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		if len(state['memorize']['spellcasters_queue']) == 0:
			return 0
		queue = state['memorize']['spellcasters_queue'] # type: list[PyObjHandle]
		caster = queue.pop()
		state['push_scheme'] = {
			'id': 'obj_memorize_spells',
			'callback': (create_memorize_spells, (caster,) )
		}
		return 1

	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('set_party', 100),('is_char_ui_visible', 100) ),
	  GoalState('set_party',gs_set_memorizer, ('do_memorize', 100), ('is_char_ui_visible', 100) ),
	  GoalState('do_memorize', gs_create_and_push_scheme, ('set_party', 100), ),
	 
	  GoalState('is_char_ui_visible', gs_is_widget_visible, ('exit_char_ui', 100), ('end', 100), params={'param1': WID_IDEN.CHAR_UI_MAIN_EXIT} ), 
	  GoalState('exit_char_ui', gs_press_widget, ('end', 100), params={'param1': WID_IDEN.CHAR_UI_MAIN_EXIT} ),
	  
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

def create_memorize_clear():
	wid_list = WID_IDEN.CHAR_SPELLS_UI_MEMORIZE_SPELL_WINDOWS
	scrollbar_id = WID_IDEN.CHAR_SPELLS_UI_CLASS_MEMORIZE_SCROLLBAR

	def gs_init(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['widget_scan'] = {
			'wid_id': wid_list[0],
			'idx': -1
		}
		scrollbar_wid = obtain_widget(scrollbar_id)
		if scrollbar_wid is None:
			return 0
		state['scrollbar_max'] = scrollbar_wid.scrollbar_max
		state['scrollbar_wid'] = scrollbar_wid
		return 1

	def gs_next_widget(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		idx = state['widget_scan']['idx']
		idx += 1
		if idx >= len(wid_list):
			return 0
		wid_id = wid_list[idx]
		if obtain_widget(wid_id) is None:
			return 0
		state['widget_scan']['wid_id'] = wid_id
		state['widget_scan']['idx'] = idx
		return 1

	cs = ControlScheme()
	cs.__set_stages__([
	  GoalStateStart(gs_init, ('scroll_memo_up', 100),('end', 100) ),
	  # scroll to beginning
	  GoalState('scroll_memo_up', gs_create_and_push_scheme, ('next_widget', 100), params={'param1': 'memorize_clear__scroll_to_top', 'param2': (create_scheme_scroll, (WID_IDEN.CHAR_SPELLS_UI_CLASS_MEMORIZE_SCROLLBAR, -1, -1) )} ),
	  
	  GoalState('next_widget', gs_next_widget, ('press_widget', 100), ('scrollbar_is_end', 100)),
	  GoalState('press_widget', gs_press_widget, ('next_widget', 100), ),
	  
	  GoalState('scrollbar_is_end', lambda slot: slot.get_scheme_state()['scrollbar_wid'].scrollbar_value >= slot.get_scheme_state()['scrollbar_max'] , ('end',100), ('scroll_memo_down', 100) ),
	  GoalState('scroll_memo_down', gs_create_and_push_scheme, ('next_widget', 100), params={'param1': 'memorize_clear__scroll_down_once', 'param2': (create_scheme_scroll, (WID_IDEN.CHAR_SPELLS_UI_CLASS_MEMORIZE_SCROLLBAR, 1, 1) )} ),
	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs

class SpellClassifier:
	buff_spells = [spell_shield, spell_shield_of_faith, spell_bless, spell_protection_from_evil, spell_enlarge,
	 spell_aid, spell_endurance, spell_bulls_strength,
	 spell_prayer,spell_haste, spell_false_life,
	 ]
	self_buff_spells = [spell_mage_armor, 
	spell_magic_circle_against_evil,
	spell_righteous_might
	]
	
	animal_companion_spells = [spell_magic_fang, spell_greater_magic_fang]
	elemental_protection_spells = [spell_resist_elements, spell_endure_elements, spell_protection_from_elements]
	
	offensive_spells = [
		spell_magic_missile, spell_burning_hands, spell_magic_stone, spell_produce_flame, 
		spell_searing_light, spell_sound_burst,
		spell_fireball, spell_call_lightning,
		spell_cone_of_cold,
		spell_flame_strike,
	]
	cc_spells = [spell_command,spell_cause_fear, spell_grease, spell_entangle, spell_color_spray,
	spell_web, spell_glitterdust, spell_hold_person,
	]
	
	summon_spells = [spell_summon_monster_i, spell_summon_monster_ii, ]
	utility_spells = [spell_read_magic, spell_guidance, spell_virtue,
	spell_knock,]
	def __init__(self):
		pass
	@staticmethod
	def categorize_spells(known):
		#type: (tuple[PySpellStore])-> dict[str,list[PySpellStore]]
		relevant_spells = {'offensive': [], 'buff': [], 'self_buff': [], 'cc': [], 'util': []} #type: dict[str, list[PySpellStore] ]
		
		for sp in known:
			sp_enum = sp.spell_enum
			if sp_enum in SpellClassifier.offensive_spells:
				relevant_spells['offensive'].append(sp)
			elif sp_enum in SpellClassifier.buff_spells:
				relevant_spells['buff'].append(sp)
			elif sp_enum in SpellClassifier.self_buff_spells:
				relevant_spells['self_buff'].append(sp)
			elif sp_enum in SpellClassifier.cc_spells:
				relevant_spells['cc'].append(sp)
			elif sp_enum in SpellClassifier.utility_spells:
				relevant_spells['util'].append(sp)
		return relevant_spells

def create_memorize_spells(obj):
	#type: (PyObjHandle)->ControlScheme
	
	def gs_init_memorize_spells(slot):
		#type: (GoalSlot)->int
		print('gs_init_memorize_spells')
		state = slot.get_scheme_state()
		known = obj.spells_known
		if len(known) == 0:
			return 0
		state['memorize_spells'] = {
			'known': known,
			'memo_wid': None,
			'spell_level': -1, # spell level of the current slot being filled
		}
		return 1

	def memoslot_check(slot):
		#type: (GoalSlot)->int
		state = slot.get_scheme_state()
		idx = state['widget_scan']['idx']
		wid_list = slot.param1
		wid_id = wid_list[idx]
		# print('checking widget:', wid_id)
		wid = controller_ui_util.obtain_widget(wid_id)
		if wid is None:
			print('memoslot_check: widget ID %s not found' % (wid_id))
			return False

		print('obtained widget: %s'%str(wid))
		print('rendered text: ', wid.rendered_text)
		if wid.rendered_text != '':
			if wid.rendered_text[-1] in [str(x) for x in range(0,10)]:
				spell_level = int(wid.rendered_text[-1])
				print('create_memorize_spells: Setting spell level to: %d' % spell_level)
				state['memorize_spells']['spell_level'] = spell_level
			return False

		if wid.render_status != 0:
			print('create_memorize_spells::memoslot_check: found a valid empty spell slot')
			return True
		return False

	def gs_select_memorized_spell_slot(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		memo_wid = state['widget_scan']['wid_id']
		state['memorize_spells']['memo_wid'] = memo_wid
		if memo_wid:
			return 1
		return 0
	
	def gs_set_widget_scan_to_memo_spell_slot(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		state['widget_scan']['wid_id'] = state['memorize_spells']['memo_wid']
		return 1

	def gs_select_known_spell(slot):
		# type: (GoalSlot)->int
		state = slot.get_scheme_state()
		spell_level = state['memorize_spells']['spell_level']
		known = state['memorize_spells']['known'] #type: tuple[PySpellStore]
		relevant_spells = SpellClassifier.categorize_spells( (sp for sp in known if sp.spell_level == spell_level) )
		keys = [k for k in relevant_spells.keys() if len(relevant_spells[k]) > 0 ]
		if len(keys) == 0:
			return 0
		cat_idx = game.random_range(0, len(keys)-1 )
		spells = relevant_spells[keys[cat_idx]]
		chosen_spell_idx = game.random_range(0, len(spells) - 1)
		chosen_spell = spells[chosen_spell_idx]
		state['memorize_spells']['known_select'] = chosen_spell.spell_name

		print('gs_select_known_spell: chosen spell %s' % chosen_spell.spell_name)
		return 1

	def known_slot_check(slot):
		state = slot.get_scheme_state()
		idx = state['widget_scan']['idx']
		wid_list = slot.param1
		wid_id = wid_list[idx]
		# print('checking widget:', wid_id)
		wid = controller_ui_util.obtain_widget(wid_id)
		if wid is None:
			# print('not found')
			return False
		
		print('obtained widget: %s'%str(wid))
		print('rendered text: ', wid.rendered_text)
		if wid.rendered_text.lower().endswith(state['memorize_spells']['known_select'].lower()):
			return True
		return False

	cs = ControlScheme()
	cs.__set_stages__([
		GoalStateStart(lambda slot: len(obj.spells_known) > 0, ('open_char_ui', 100), ('end', 100)),
		GoalState('open_char_ui', gs_create_and_push_scheme, ('open_spells_ui', 100), params={'param1': 'memorize_open_char_ui', 'param2': (create_open_char_ui, (obj,))}),

		GoalState('open_spells_ui', gs_press_widget, ('check_memorized_slots', 100), params={'param1': WID_IDEN.CHAR_UI_MAIN_SELECT_SPELLS_BTN}),
		GoalState('check_memorized_slots', gs_is_widget_visible, ('init_spell_selection', 100), ('end', 100), params={'param1': WID_IDEN.CHAR_SPELLS_UI_MEMORIZE_SPELL_WINDOWS[0]}),
		
	  	GoalState('init_spell_selection', gs_init_memorize_spells, ('clear_memo_up', 100),('end', 100) ),
		
		GoalState('clear_memo_up', gs_push_scheme, ('scroll_memo_to_top', 100), params={'param1': 'memorize_clear_all', } ),
		GoalState('scroll_memo_to_top', gs_create_and_push_scheme, ('scan_memorization_slots', 100), params={'param1': 'memorize_scroll_to_top', 'param2': (create_scheme_scroll, (WID_IDEN.CHAR_SPELLS_UI_CLASS_MEMORIZE_SCROLLBAR, -1, -1) )} ),
		
		GoalState('scan_memorization_slots', gs_scan_get_widget_from_list, ('check_memorization_slot', 100), ('end', 100), 
			params={'param1':  WID_IDEN.CHAR_SPELLS_UI_MEMORIZE_SPELL_WINDOWS, 'param2': memoslot_check } ),
		GoalState('check_memorization_slot', gs_select_memorized_spell_slot, ('scroll_known_to_top', 100), ('end', 100) ),
		
		GoalState('scroll_known_to_top', gs_create_and_push_scheme, ('select_spell_known', 100), params={'param1': 'known_scroll_to_top', 'param2': (create_scheme_scroll, (WID_IDEN.CHAR_SPELLS_UI_CLASS_SPELLBOOK_SCROLLBAR, -1, -1) )} ),
		GoalState('select_spell_known', gs_select_known_spell, ('scan_known_slots', 100), ('TODO', 100) ),
		GoalState('TODO', lambda slot: 1, ('end', 100)),

		GoalState('scan_known_slots', gs_scan_get_widget_from_list, ('move_mouse', 100), ('end', 100), 
			params={'param1':  WID_IDEN.CHAR_SPELLS_UI_SPELLBOOK_SPELL_WINDOWS, 'param2': known_slot_check } ),
		

		GoalState('move_mouse', gs_move_mouse_to_widget, ('mouse_down', 330), ('end', 100), ),
		GoalState('mouse_down', gs_lmb_down, ('set_widget_scan_to_memo_spell_slot', 100),  ),
		GoalState('set_widget_scan_to_memo_spell_slot', gs_set_widget_scan_to_memo_spell_slot, ('move_mouse_to_memo_slot', 100), ),
		GoalState('move_mouse_to_memo_slot', gs_move_mouse_to_widget, ('mouse_up', 330), ('end', 100), ),
		GoalState('mouse_up', gs_lmb_up, ('scan_memorization_slots', 100),  ),

	  GoalStateEnd(gs_wait_cb, ('end', 100), ),
	])
	return cs
#endregion