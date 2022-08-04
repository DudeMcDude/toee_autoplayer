from toee import game
import playtester
from ui_time_event import UiTimeEvent

autoplayer = None #type: Autoplayer

def play_new_game():
    print('gonna play a new game')
    #controllers.UiController.start_ui_thread()
    import new_game_controller
    global autoplayer
    autoplayer = playtester.Playtester()
    new_game_controller.setup_playtester(autoplayer)
    return

def excb(arg):
    print('cawback #%s, is main menu: %s' %( str(arg), check_main_menu()) )
    # UiTimeEvent.schedule( excb, (arg+1,), 1000 )
    if (check_main_menu()):
        autoplayer.game_reset()
    return

def advance_time(time_real):
    # print(str(time_real))
    # print("game.is_ingame = " + str(game.is_ingame()))
    UiTimeEvent.__is_advance_time__ = True
    if UiTimeEvent.__first_after_reset__:
        # print('scheduling')
        UiTimeEvent.schedule( excb, (1,), 400 )
        UiTimeEvent.__first_after_reset__ = False
        return
    UiTimeEvent.expire_events()
    UiTimeEvent.__is_advance_time__ = False
    return

def check_main_menu():
    # there is not clear 
    if len(game.party) > 0:
        print('not main menu')
        return 0
    print('is main menu')
    return 1

def reset():
    # actually a bad place to do anything
    # UiTimeEvent.schedule( 1000 )
    UiTimeEvent.__first_after_reset__ = True
    return