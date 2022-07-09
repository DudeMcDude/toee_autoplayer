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
    move_mouse(wid.x, wid.y)
    return



def obtain_widget(identifier_list, widget_ids = None):
    import autoui as aui
    widget_ids = None
    find_res = []
    res = None # type: aui.TWidget
    
    if isinstance(identifier_list, aui.TWidget):
        res = identifier_list
        return res if res.visible else None
    elif type(identifier_list) == int:
        widget_id = identifier_list
        res = aui.TWidget(widget_id)
        return res if res.visible else None

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
            if not res.visible:
                return None
    return res

class WID_IDEN:
    # see autoui.TWidgetIdentifier
    aui.TWidgetIdentifier
    NEW_GAME = [
        ('', 'templeplus/ui/main_menu.json'), 0,    ('pages', 'templeplus/ui/main_menu.json'),   
        ('page-main-menu', 'templeplus/ui/main_menu.json'),    ('new-game', 'templeplus/ui/main_menu.json')
    ] 
    NORMAL_DIFF = [
       ('', 'templeplus/ui/main_menu.json'), 0,   ('pages', 'templeplus/ui/main_menu.json'),  ('page-difficulty', 'templeplus/ui/main_menu.json'),        ('difficulty-normal', 'templeplus/ui/main_menu.json')
    ]
    CHAR_POOL_BEGIN_ADVENTURE = [('pc_creation.c 2024'),('pc_creation.c 2048')]
    TRUE_NEUTRAL_BTN_WID_ID = [
        ('pc_creation.c 1566'), ('pc_creation.c 1590'), 4 
    ]
    PARTY_ALIGNMENT_ACCEPT_BTN = [('pc_creation.c 1566'), ('pc_creation.c 1641'), ]
    CHAR_POOL_CHAR1 = [('party_pool.c 1349'), ('party_pool.c 1383'), 0]
    CHAR_POOL_CHAR2 = [('party_pool.c 1349'), ('party_pool.c 1383'), 1]
    CHAR_POOL_CHAR3 = [('party_pool.c 1349'), ('party_pool.c 1383'), 2]
    CHAR_POOL_CHAR4 = [('party_pool.c 1349'), ('party_pool.c 1383'), 3]
    CHAR_POOL_CHAR5 = [('party_pool.c 1349'), ('party_pool.c 1383'), 4]
    CHAR_POOL_CHAR6 = [('party_pool.c 1349'), ('party_pool.c 1383'), 5]
    CHAR_POOL_ADD_BTN = [('party_pool.c 885'), ('party_pool.c 914')]

    LOAD_GAME = [  ('', 'templeplus/ui/main_menu.json'), ('pages', 'templeplus/ui/main_menu.json'), 
     ('page-main-menu', 'templeplus/ui/main_menu.json'),   ('load-game', 'templeplus/ui/main_menu.json')  
    ]
    LOAD_GAME_ENTRY_1 = [
        ('loadgame_ui.c 327'), ('loadgame_ui.c 448'), 1
    ]
    LOAD_GAME_LOAD_BTN = [ ('loadgame_ui.c 327'), ('loadgame_ui.c 351'), ]
    

def get_window_rect(name = "Temple of Elemental Evil (Temple+)"):
    import ctypes
    import ctypes.wintypes
    # import ctypes; hwnd = ctypes.windll.user32.FindWindowW('TemplePlusMainWnd', "Temple of Elemental Evil (Temple+)")
    import ctypes; hwnd = ctypes.windll.user32.FindWindowA('TemplePlusMainWnd', 0)
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.pointer(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)

def client_to_screen(x,y):
    import ctypes; hwnd = ctypes.windll.user32.FindWindowA('TemplePlusMainWnd', 0)
    import ctypes.wintypes
    pt = ctypes.wintypes.POINT()
    pt.x = x
    pt.y = y
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.pointer(pt))
    
    return pt.x, pt.y

def move_mouse(x,y):
    ''' in screenspace only; useful for UIs (esp. radial menu) '''
    import ctypes; SetCursorPos = ctypes.windll.user32.SetCursorPos
    # l,t,r,b = get_window_rect()
    import tpgui
    x,y   = tpgui.map_from_scene(x,y) # takes care of scaled windows
    xs,ys = client_to_screen(x,y)

    # print("Moving Mouse to: xs, ys", xs,ys)
    SetCursorPos(xs,ys)
    # mouse_event = ctypes.windll.user32.mouse_event
    return

def click_on_obj(obj):
    loc = obj.location
    game.mouse_move_to(loc)
    game.mouse_click()
    return

def click_mouse(rightclick = 0):
    game.mouse_click(rightclick)
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