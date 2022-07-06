from toee import *
from utilities import location_from_axis, location_to_axis
from templeplus.controllers import *
from controllers import *
import logbook
from controller_callbacks_common import *




slot_ = None
cntrl_ = None #type: CritterController
cntrl2_ = None #type: CritterController

def do_tutorial_room1(obj = None):
	print("DOING TUTORIAL LEVEL 1")
	global cntrl_
	if obj is None:
		obj = game.party[0]
	
	print("OBJ = " + str(obj))
	
	obj.scripts[12] = 240 #san_dying
	obj.scripts[38] = 240 #san_new_map
	obj.scripts[14] = 240 #san_exit_combat - executes when exiting combat mode
	slot_ = GoalSlot(obj)
	if cntrl_ is not None:
		print('Deactingvating ctrl_')
		cntrl_.activate(False)
	cntrl_ = CritterController(obj, slot_)
	cntrl_.add_scheme(create_tutorial_room1_to_4(), 'tut1')
	cntrl_.add_scheme(create_tutorial_room4_on(), 'tut2')
	cntrl_.set_active_scheme('tut1')
	cntrl_.execute()
	logbook.set_key_entry_need_to_notify(0)
	return cntrl_

def do_tutorial_level2(obj = None):
	print("DOING TUTORIAL LEVEL 2")
	global cntrl_
	if obj is None:
		obj = game.party[0]
	
	print("OBJ = " + str(obj))
	
	obj.scripts[12] = 240 #san_dying
	obj.scripts[38] = 240 #san_new_map
	obj.scripts[14] = 240 #san_exit_combat - executes when exiting combat mode
	slot_  = GoalSlot(obj)
	if cntrl_ is not None:
		print('Deactingvating ctrl_')
		cntrl_.activate(False)
	cntrl_ = CritterController(obj, slot_)
	cntrl_.add_scheme(create_tutorial_level_2(), 'tut_lvl2')	
	cntrl_.set_active_scheme('tut_lvl2')
	cntrl_.execute()
	logbook.set_key_entry_need_to_notify(0)
	return cntrl_
		


def do_tutorial_level3(obj = None):
	print("DOING TUTORIAL LEVEL 3")
	global cntrl_
	global cntrl2_
	if obj is None:
		obj = game.party[0]
	
	print("OBJ = " + str(obj))
	
	obj.scripts[12] = 240 #san_dying
	obj.scripts[38] = 240 #san_new_map
	obj.scripts[14] = 240 #san_exit_combat - executes when exiting combat mode
	
	if cntrl_ is not None:
		print('Deactingvating ctrl_')
		cntrl_.activate(False)
	cntrl_ = None
	
	# cntrl_ = CritterController(obj, slot_)
	# cntrl_.add_scheme(create_tutorial_level_2(), 'tut_lvl2')	
	# cntrl_.set_active_scheme('tut_lvl2')
	# cntrl_.execute()

	cntrl_ = CritterController(obj)
	cntrl_.add_scheme(create_tutorial_level_3(), 'tut_lvl3')	
	cntrl_.set_active_scheme('tut_lvl3')
	cntrl_.execute()
	game.party[0].ai_strategy_set_custom( ['valkor tut', 
		'target damaged', '', '', 
		'attack threatened', '', '',
		
		'target closest', '', '', 
		'attack','','',

		'five foot step','',''
		])

	cntrl2_ = CritterController(game.party[1])
	cntrl2_.add_scheme(create_tutorial_level_3_ariel(), 'tut_lvl3_ariel')	
	cntrl2_.set_active_scheme('tut_lvl3_ariel')
	cntrl2_.execute()
	game.party[1].ai_strategy_set_custom( ['ariel tut', 
		'target closest', '', '', 
		'five foot step','','',
		'target damaged', '', '', 
		'cast single', '', '\'Magic Missile\' class_wizard 1',
		'target threatened', '', '',
		'attack','',''])
	return cntrl_
		
#region callbacks


def gs_give_wand_to_ariel(slot):
	game.party[0].item_transfer_to_by_proto(game.party[1], 12581)
	return 1


def load_and_do_tut():
	CritterController.deactivate_all()
	press_quickload()
	print("QUICK LOADED")

def gs_ariel_throw_fireball(slot):
	ariel = game.party[1]
	tgt = select_target(ariel)
	wand  = ariel.item_find_by_proto(12581)
	if tgt == OBJ_HANDLE_NULL or wand == OBJ_HANDLE_NULL:
		return 1
	game.party[1].use_item( wand, tgt)
	game.timevent_add( load_and_do_tut, (), 70000, 1 ) # hope valkor doesn't die in those 40 secs :)
	return 1

def wield_best(slot):
	slot.obj.item_wield_best_all()
	return 1


def do_nothing(slot):
	# print('do_nothing: Killing controller...') # this causes issues
	# global cntrl_
	# cntrl_.activate(False)
	# cntrl_ = None
	return 0

def open_spells_ui(slot):
	UI_CHAR_PAGE_SPELLS = 7
	state = slot.state
	if state is None:
		slot.state = 0
		return 0
	else:
		if slot.state == 0:
			press_key( DIK_I )
			slot.state = 1
			return 0
		if slot.state == 1:
			press_key( DIK_2 )
			slot.state = 2 # switch to Ariel...
			return 0
		
		if slot.state == 2:

			if game.char_ui_page != UI_CHAR_PAGE_SPELLS:
				click_spells_button()
				return 0
			return 1
	return 0

def memorize_magic_missile(slot):

	if slot.state is None:
		slot.state = 0
		return 0
	else:
		if slot.state < 3:
			rightclick_at(480, 342, 1)
			slot.state += 1
			return 0
		press_escape()
		return 1
	return 0

def rest_memorize(slot):
	if slot.state is None:
		slot.state = 0
		press_key(DIK_R)
		return 0
	if slot.state == 0:
		click_at(900, 614, 1)
	return 1


def cast_magic_missile(slot):
	if slot.state is None:
		move_mouse(500,500)
		slot.state = 0
		return 0
	elif slot.state == 0:
		game.mouse_click(1)
		slot.state += 1
		return 0
	elif slot.state == 1:
		move_mouse(530,500)
		slot.state += 1
		return 0
	elif slot.state == 2:
		move_mouse(570,500) # Wiz
		slot.state += 1
		return 0
	elif slot.state == 3:
		move_mouse(590,500) # 1
		slot.state += 1
		return 0
	elif slot.state == 4:
		move_mouse(610,500) # Magic Missile
		slot.state += 1
		return 0
	elif slot.state == 5:
		game.mouse_click()
		slot.state += 1
		return 0
	elif slot.state == 6:
		game.mouse_click()
		slot.state += 1
		return 0
	return 1
#endregion

room3_loc = location_from_axis(466, 467)
room4_loc = location_from_axis(466, 484)
tutorial_room1_to_4 = None
def create_tutorial_room1_to_4():
	return ControlScheme( [
	GoalState('start', gs_wait_cb, ('go room2', 1000), () ),
	GoalState('go room2', gs_arrive_at_tile, ('open_room2_chest', 250), (), {'param1': location_from_axis(478, 453)} ),
	GoalState('open_room2_chest', perform_on_nearest, ('loot_room2_chest', 500), (), {'param1': D20A_OPEN_CONTAINER, 'param2': OLC_CONTAINER} ),
	GoalState('loot_room2_chest', loot_nearest_chest, ('wield_best_all', 500), (), {'param1': D20A_OPEN_CONTAINER, 'param2': OLC_CONTAINER} ),
	GoalState('wield_best_all', wield_best, ('go_room3', 500), (), {} ),
	GoalState('go_room3', gs_arrive_at_tile, ('go_room4', 500), (), {'param1': room3_loc} ),
	GoalState('go_room4', gs_click_and_scroll_to_tile, ('fight_room4', 500), (), {'param1': room4_loc} ),
	GoalState('fight_room4', fight_room, ('end', 500), (), {'param1': room4_loc} ),
	
	GoalState('end', activate_scheme, ('start', 500), (), {'param1': 'tut2'} ),
	])

room4_cor_loc = location_from_axis(452,490) # needs intermittent location due to lack of PF nodes
room5_loc = location_from_axis(441,489)

tutorial_room4_on = None
def create_tutorial_room4_on():
	return ControlScheme(	[
	GoalState('start', gs_wait_cb, ('loot_room4', 500)),
	GoalState('loot_room4', loot_critters, ('go_room5', 500), (), {'param1': room4_loc} ),
	GoalState('go_room5', gs_arrive_at_tile, ('go_room5_2', 500), (), {'param1': room4_cor_loc} ),
	GoalState('go_room5_2', gs_arrive_at_tile, ('go_down', 500), (), {'param1': room5_loc} ),
	GoalState('go_down', gs_click_on_loc_nearest, ('end', 500), (), {'param1': room5_loc, 'param2': OLC_SCENERY} ),
	GoalState('end', do_nothing, ('end', 500), (), {'param1': room4_loc} ),
	] )


lvl2_room2_loc = location_from_axis(461, 480)
def create_tutorial_level_2():
	return ControlScheme( [
		GoalState('start', wait_for_dlg, ('ariel_open_spells', 200)),
		GoalState('ariel_open_spells', open_spells_ui, ('ariel_memorize_magic_missile', 200)),
		GoalState('ariel_memorize_magic_missile', memorize_magic_missile, ('rest_memorize', 200)),
		GoalState('rest_memorize', rest_memorize, ('go_next_room', 1000)),
		GoalState('go_next_room', gs_click_and_scroll_to_tile, ('arrived_next_room', 1000), params={'param1': lvl2_room2_loc} ),
		GoalState('arrived_next_room', arrived_at, ('go_down', 250), (), {'param1': lvl2_room2_loc} ),
		GoalState('go_down', gs_click_on_loc_nearest, ('end', 500), (), {'param1': lvl2_room2_loc, 'param2': OLC_SCENERY} ),
		GoalState('end', do_nothing, ('end', 500)),
	])
	
lvl3_loc1 = location_from_axis(512, 486)
lvl3_loc2 = location_from_axis(499, 486)
lvl3_loc3 = location_from_axis(486, 486)
lvl3_loc4 = location_from_axis(478, 486)

def create_tutorial_level_3(): # valkor
	return ControlScheme( [
		GoalState('start', arrived_at, ('select_me', 500), params={'param1': lvl3_loc1, 'param2': 5}),
		GoalState('select_me', gs_select_me, ('go_to_room',500)),
		GoalState('go_to_room', gs_arrive_at_tile, ('fight_room', 200), params={'param1':lvl3_loc2, 'param2': 10 }),
		GoalState('fight_room', fight_room, ('loot_zombie', 500), (), {'param1': lvl3_loc2} ),
		GoalState('loot_zombie', loot_critters, ('give_wand_to_ariel', 500), params={'param1':lvl3_loc2 }),
		GoalState('give_wand_to_ariel', gs_give_wand_to_ariel, ('select_all', 500), params={'param1':lvl3_loc2 }),
		GoalState('select_all', gs_select_all, ('go_to_corridor2', 500)),
		GoalState('go_to_corridor2', gs_arrive_at_tile, ('select_me2', 200), params={'param1':lvl3_loc3 }),
		GoalState('select_me2', gs_select_me, ('go_to_corridor3',500)),
		GoalState('go_to_corridor3', gs_arrive_at_tile, ('ariel_throw_fireball', 1500), params={'param1':lvl3_loc4 }),
		GoalState('ariel_throw_fireball', gs_ariel_throw_fireball, ('fight_room2',500)),
		GoalState('fight_room2', fight_room, ('end', 500), (), {'param1': lvl3_loc3} ),
		GoalState('end', gs_idle, ('end', 200)),
	])

def create_tutorial_level_3_ariel():
	return ControlScheme( [
		GoalState('start', gs_wait_cb, ('select_all', 500)),
		GoalState('select_all', gs_select_all, ('go_to_corridor1', 500)),
		GoalState('go_to_corridor1', gs_arrive_at_tile, ('fight_room', 200), params={'param1':lvl3_loc1 }),
		GoalState('fight_room', fight_room, ('end', 500), (), {'param1': lvl3_loc2} ),
		GoalState('end', gs_idle, ('end', 200)),
	])