from toee import game
import playtester
from ui_time_event import UiTimeEvent

autoplayer = None #type: Autoplayer

def play_new_game():
    print('gonna play a new game')
    #controllers.UiController.start_ui_thread()
    import os
    scenario = os.environ.get('AUTOPLAYER_SCENARIO')
    if scenario in ('iwd_ch1', 'iwd2_ch1'): # ie2toee: new game -> IWD prologue to AR2000 / IWD2 Shawford chain to Ulbrec (scr/iwd_ch1_driver.py)
        import iwd_ch1_driver
        global autoplayer
        autoplayer = playtester.Playtester()
        iwd_ch1_driver.setup_playtester(autoplayer, 'iwd2' if scenario == 'iwd2_ch1' else 'iwd')
        return
    if scenario in ('easthaven', 'targos'): # ie2toee IWD Easthaven / IWD2 Targos conversions (see scr/iwd_easthaven_controller.py)
        import iwd_easthaven_controller
        global autoplayer
        autoplayer = playtester.Playtester()
        iwd_easthaven_controller.setup_playtester(autoplayer, scenario)
        return
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