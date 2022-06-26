from controllers import CritterController
from toee import *
from tutorial_level_1_controller import do_tutorial_room1, press_quickload
from tutorial_level_1_controller import do_tutorial_level2, do_tutorial_level3




def san_heartbeat( attachee, triggerer ):
	# game.timevent_add( press_quicksave, (), 300, 1)
	for obj in game.obj_list_vicinity(attachee.location,OLC_PC):
		if (critter_is_unconscious(obj) == 0):
			#attachee.turn_towards(obj)
			if not game.tutorial_is_active():
				game.tutorial_toggle()
			
			do_tutorial_room1(obj)
			# game.tutorial_show_topic( TAG_TUT_ROOM1_OVERVIEW )
			game.new_sid = 0
			return RUN_DEFAULT
	return RUN_DEFAULT

def load_and_do_tut():
	press_quickload()
	print("QUICK LOADED")
	# game.timevent_add( do_tutorial_room1, (), 1500, 1)
	#do_tutorial_room1()
	return

def san_new_map(attachee, triggerer):
	cur_map = attachee.map
	print("New map: " , cur_map, attachee)
	# cntrl_.activate(False)
	if attachee.map == 5116:
		do_tutorial_room1(attachee)
	elif attachee.map == 5117:
		# game.timevent_add( press_quickload, (), 3000, 1)
		do_tutorial_level2()
	elif attachee.map == 5118:
		# game.timevent_add( load_and_do_tut, (), 1500, 1)
		do_tutorial_level3()
		pass
		
	return RUN_DEFAULT

def san_dying(attachee, triggerer):
	CritterController.deactivate_all()
	print("DYING! QUICK LOADING")
	press_quickload()
	return RUN_DEFAULT

def san_exit_combat(attachee, triggerer):
	if game.party[0].is_unconscious():
		print("EXITED COMBAT KO'D! QUICK LOADING")
		press_quickload()
	return RUN_DEFAULT