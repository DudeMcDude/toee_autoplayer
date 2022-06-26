from toee import *
from toee import game
from utilities import *
import autoui as aui

DIK_ESCAPE = 1
DIK_1 = 2
DIK_2 = 3
DIK_3 = 4
DIK_4 = 5
DIK_5 = 6
DIK_Q = 16
DIK_W = 17
DIK_E = 18
DIK_R = 19
DIK_I = 23

DIK_RETURN = 28
DIK_GRAVE = 41
DIK_SPACE = 57
DIK_F12 = 88 # quicksave
DIK_F9 = 67  # quickload

def press_key(key):
    game.keypress(key)

def press_enter():
    press_key(DIK_RETURN)
def press_space():
    press_key(DIK_SPACE)
def press_escape():
    press_key(DIK_ESCAPE)
def press_quicksave():
    press_key(DIK_F12)
def press_quickload():
    press_key(DIK_F9)

def select_party(idx):
    press_key(DIK_1 + idx)

def click_loot_all_button():
    print("Loot all")
    # 77,182
    click_at( 77,182, 1)
    return
def click_spells_button():
    print("click_spells_button")
    click_at(670, 130, 1)
    return


def click_key_dlg_btn():
    ''' clicks Key UI button '''
    click_at( 947,621, 1) # hardcoded...
    return
    
def move_mouse_to_widget(wid):
    # type: (aui.TWidget)->None
    move_mouse(wid.wid.abs_x(), wid.wid.abs_y())
    return



def obtain_widget(identifier_list, widget_ids = None):
    import autoui as aui
    widget_ids = None
    find_res = []
    res = None # type: aui.TWidget
    
    for wid_identifier in identifier_list:
        
        if type(wid_identifier) == int:
            res = find_res[wid_identifier]
            continue
        elif len(find_res) > 1:
            print('obtain_widget: needs index to disambiguate results!')
            return None
        elif len(find_res) == 1:
            widget_ids = res.children_ids

        find_res = aui.find_by_identifier( wid_identifier, widget_ids )
        if len(find_res) == 0:
            return None
        if len(find_res) == 1:
            res = find_res[0]
            if not res.wid.visible:
                return None
    return res




def move_mouse_new_game():
    import autoui as aui
    
    new_game_btn = obtain_widget( [
        ('', 'templeplus/ui/main_menu.json'), 0,    ('pages', 'templeplus/ui/main_menu.json'),   ('page-main-menu', 'templeplus/ui/main_menu.json'),    ('new-game', 'templeplus/ui/main_menu.json')
    ] )
    if new_game_btn is None:
        return False
    move_mouse_to_widget(new_game_btn)
    return True

def move_mouse_normal_difficulty():
    import autoui as aui; 	
    diff_normal_btn = obtain_widget( [
        ('', 'templeplus/ui/main_menu.json'), 0,      ('pages', 'templeplus/ui/main_menu.json'),      ('page-difficulty', 'templeplus/ui/main_menu.json'),        ('difficulty-normal', 'templeplus/ui/main_menu.json')
    ] )
    if diff_normal_btn is None:
        return False
    move_mouse_to_widget(diff_normal_btn)
    return

def move_mouse(x,y):
    ''' in screenspace only; useful for UIs (esp. radial menu) '''
    import ctypes; SetCursorPos = ctypes.windll.user32.SetCursorPos
    SetCursorPos(x,y)
    # mouse_event = ctypes.windll.user32.mouse_event
    return

def click_on_obj(obj):
    loc = obj.location
    game.mouse_move_to(loc)
    game.mouse_click()
    return

def click_at(x,y, screenspace = 0):
    loc = location_from_axis(x,y)
    game.mouse_move_to(loc, screenspace)
    game.mouse_click()
    return

def rightclick_at(x,y, screenspace = 0):
    loc = location_from_axis(x,y)
    game.mouse_move_to(loc, screenspace)
    game.mouse_click(1)
    return

def scroll_to(x,y):
    loc = location_from_axis(x,y)
    game.scroll_to(loc)
    return