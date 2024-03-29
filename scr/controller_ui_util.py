from toee import *
from toee import game
from utilities import *
import autoui as aui
import tpgui

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

MB_LEFT   = 0
MB_RIGHT  = 1
MB_MIDDLE = 2

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
    ''' selects party member [idx]\n
    idx starts at 0
    '''
    press_key(DIK_1 + idx)
def select_all():
    press_key(DIK_GRAVE)

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
    #type: ( list[aui.TWidgetIdentifier | int | aui.TWidget | None] , list[int] )-> aui.TWidget
    '''
    * identifier_list: \n
         If None is specified, it just looks in the entire children list of the last found widget. \n
         i.e. it finds 'any' child, not just those match a specific identifier.\n
         Useful for when the widget name is garbage and there is no identifying information...\n
     returns None if none found
    '''
    import autoui as aui
    widget_ids = None
    find_res = []
    res = None # type: aui.TWidget
    
    if isinstance(identifier_list, aui.TWidget): # is already specified widget, just check if it's visible
        res = identifier_list
        return res if res.visible else None
    elif type(identifier_list) == int: # is explicit widget_id (number), just fetch it directly
        widget_id = identifier_list
        res = aui.TWidget(widget_id)
        return res if res.visible else None

    for wid_identifier in identifier_list:
        # print('wid_identifier: ' + str(wid_identifier) + ' widget_ids: ' + str(widget_ids))
        if type(wid_identifier) == int: # numbers are used to select from several widgets with identical identifiers (usually buttons/children)
            idx = wid_identifier
            if idx >= len(find_res):
                return None
            res = find_res[idx]
            # print('res: ' + str(res))
            find_res = [res,]
            continue
        elif len(find_res) > 1:
            print('obtain_widget: needs index to disambiguate results! ', str(find_res))
            return None
        elif len(find_res) == 1: # to be used with None entry e.g. identifier_list = [('utility_bar.c 481', ), None, 3]
            widget_ids = res.children_ids # search among last widget's children
        
        find_res = aui.find_by_identifier( wid_identifier, widget_ids )
        # print('find_res: ' + str(find_res))
        if len(find_res) == 0:
            # print('not found')
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
    CHAR_POOL_CHARS = [ 
        [('party_pool.c 1349'), ('party_pool.c 1383'), x] for x in range(7) ]
    
    CHAR_POOL_ADD_BTN = [('party_pool.c 885'), ('party_pool.c 914')]

    MAIN_MENU_LOAD_GAME = [  ('', 'templeplus/ui/main_menu.json'), ('pages', 'templeplus/ui/main_menu.json'), 
     ('page-main-menu', 'templeplus/ui/main_menu.json'),   ('load-game', 'templeplus/ui/main_menu.json')  
    ]
    INGAME_LOAD_GAME = [  ('', 'templeplus/ui/main_menu.json'), ('pages', 'templeplus/ui/main_menu.json'), 
     ('page-ingame-normal', 'templeplus/ui/main_menu.json'),   ('ingame-normal-load', 'templeplus/ui/main_menu.json')  
    ]
    LOAD_GAME_ENTRY_BTNS = [ [('loadgame_ui.c 327'), ('loadgame_ui.c 448'), x ] for x in range(0,8)]
    LOAD_GAME_LOAD_BTN = [ ('loadgame_ui.c 327'), ('loadgame_ui.c 351'), ]
    UTIL_BAR_CAMP_BTN = [ ('utility_bar_ui.c 481',), None, 4]
    UTIL_BAR_MAP_BTN = [ ('utility_bar_ui.c 481',), None, 3]

    CAMPING_UI_REST_BTN         = [ ('camping_ui.c 570',), None, 0]
    CAMPING_UI_DAYS_INC         = [ ('camping_ui.c 570',), None, 2]
    CAMPING_UI_UNTIL_HEALED_BTN = [ ('camping_ui.c 570',), None, 6]
    
    TOWNMAP_UI_WORLD_BTN = [ ('townmap_ui_main_window',), ('townmap_ui_world_map_butn',) ]

    WORLDMAP_UI_SELECTION_BTNS = [ 
        [ ('worldmap_ui_selection_window',), ('worldmap_ui_acquired_location_butn',), x,  ] for x in range(21)
    ]

    RND_ENC_UI_ACCEPT_BTN = [('random_encounter_ui_main_window',), ('random_encounter_accept_butn')]
    RND_ENC_EXIT_UI_ACCEPT_BTN = [('random_encounter_ui_exit_window',), ('random_encounter_exit_ok_button')]

    CHAR_UI_MAIN_EXIT = [('char_ui_main_exit_window',), ('char_ui_main_exit_button', ) ]
    CHAR_LOOTING_UI_TAKE_ALL_BTN = [('char_looting_ui_main_window', ), ('char_looting_ui_take_all_button',)]
    CHAR_LOOTING_UI_BTNS = [ [('char_looting_ui_loot_window_%0.2d' % x ,),] for x in range(0, 12) ]

    CHAR_UI_INVENTORY_BTNS = [ [('char_inventory_ui_inv_window_%0.2d' % x , ),] for x in range(0, 24) ]
    CHAR_UI_MAIN_SELECT_SPELLS_BTN = [ ('char_ui_main_window',), ('char_ui_main_select_spells_button',)]

    CHAR_SPELLS_UI_SPELLBOOK_SPELL_WINDOWS = [ [ ('char_spells_ui_spellbook_spell_windows',), x] for x in range(0,18) ]
    CHAR_SPELLS_UI_CLASS_SPELLBOOK_WINDOW =  [ ('char_spells_ui_class_spellbook_window',),]
    CHAR_SPELLS_UI_CLASS_SPELLBOOK_SCROLLBAR =  [ ('char_spells_ui_class_spellbook_window',),None, 0]
    
    CHAR_SPELLS_UI_MEMORIZE_SPELL_WINDOWS  = [ [ ('char_spells_ui_memorize_spell_windows',), x] for x in range(0,18) ]
    CHAR_SPELLS_UI_CLASS_MEMORIZE_WINDOW =  [ ('char_spells_ui_class_memorize_window',),]
    CHAR_SPELLS_UI_CLASS_MEMORIZE_SCROLLBAR =  [ ('char_spells_ui_class_memorize_window',),None, 0]

    # CHAR EDITOR
    CHAR_EDITOR_UI_STAGE_BTN_CLASS    = [ ('char_ui.c 2517',), ('char_editor_class',)]
    CHAR_EDITOR_UI_STAGE_BTN_STATS    = [ ('char_ui.c 2517',), ('char_editor_stats',)]
    CHAR_EDITOR_UI_STAGE_BTN_FEATURES = [ ('char_ui.c 2517',), ('char_editor_features',)]
    CHAR_EDITOR_UI_STAGE_BTN_SKILLS   = [ ('char_ui.c 2517',), ('char_editor_skills',)]
    CHAR_EDITOR_UI_STAGE_BTN_FEATS    = [ ('char_ui.c 2517',), ('char_editor_feats',)]
    CHAR_EDITOR_UI_STAGE_BTN_SPELLS   = [ ('char_ui.c 2517',), ('char_editor_spells',)]
    
    CHAR_EDITOR_UI_CLASS_BTNS = [ ( ('char_editor_class_ui.c 193',), x) for x in range (0, 11) ]

    CHAR_EDITOR_UI_SKILL_BTNS     = [ (('char_editor_skills_ui.c 430',), ('char_editor_skills_ui.c 472',), x) for x in range(8) ]
    CHAR_EDITOR_UI_SKILL_INC_BTNS = [ (('char_editor_skills_ui.c 430',), ('char_editor_skills_ui.c 493',), x) for x in range(8) ]
    CHAR_EDITOR_UI_SKILL_DEC_BTNS = [ (('char_editor_skills_ui.c 430',), ('char_editor_skills_ui.c 517',), x) for x in range(8) ]
    CHAR_EDITOR_UI_SKILL_SCROLLBAR = [ ('char_editor_skills_ui.c 430',), 0]
    
    PARTY_UI_LEVELUP_BTNS = [  [('party_ui_main_window',), x, ('party_ui_level_icon',)] for x in range(0,8)]

    POPUP_UI_OK_BTN = [('popup_ui_main_window',), ('popup_ui_button', ), 0]
    SLIDER_UI_OK_BTN = [('slider_window', ), ('slider accept button',) ]

    LOGBOOK_UI_KEY_ENTRY_ACCEPT = [('logbook_ui_keys_key_entry_window', ), ('logbook_ui_key_entry_accept_butn',)]



    

def get_window_rect(name = "Temple of Elemental Evil (Temple+)"):
    import ctypes
    import ctypes.wintypes
    # import ctypes; hwnd = ctypes.windll.user32.FindWindowW('TemplePlusMainWnd', "Temple of Elemental Evil (Temple+)")
    import ctypes; hwnd = ctypes.windll.user32.FindWindowA('TemplePlusMainWnd', 0)
    rect = ctypes.wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.pointer(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)

def client_to_screen(x,y):
    # convert coordinate from client space to screen space
    import ctypes; hwnd = ctypes.windll.user32.FindWindowA('TemplePlusMainWnd', 0)
    import ctypes.wintypes
    pt = ctypes.wintypes.POINT()
    pt.x = x
    pt.y = y
    ctypes.windll.user32.ClientToScreen(hwnd, ctypes.pointer(pt))
    
    return pt.x, pt.y

def get_mouse_pos():
    import ctypes; GetCursorPos = ctypes.windll.user32.GetCursorPos
    import ctypes.wintypes
    pt = ctypes.wintypes.POINT()
    GetCursorPos(ctypes.pointer(pt))

    return pt.x, pt.y

def move_mouse(x,y):
    ''' in screenspace only; useful for UIs (esp. radial menu) '''
    import ctypes; SetCursorPos = ctypes.windll.user32.SetCursorPos
    # l,t,r,b = get_window_rect()
    x,y   = tpgui.map_from_scene(x,y) # takes care of scaled windows
    xs,ys = client_to_screen(x,y)

    # print("Moving Mouse to: xs, ys", xs,ys)
    SetCursorPos(xs,ys)
    # mouse_event = ctypes.windll.user32.mouse_event
    return

def move_mouse_to_loc(loc, off_x = 0, off_y = 0):
    if type(loc) is tuple:
        x,y = loc
        loc = location_from_axis(x,y)
        x,y = tpgui.world_to_screen(loc)
    else:
        x,y = tpgui.world_to_screen(loc)
    move_mouse(x + off_x,y + off_y)
    return

def move_mouse_to_obj(obj, off_x = 0, off_y = 0):
    # loc = obj.location
    # game.mouse_move_to(loc)
    x,y = tpgui.world_to_screen(obj.location_full)
    move_mouse(x + off_x,y + off_y)
    return

def click_on_obj(obj):
    move_mouse_to_obj(obj)
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

def center_screen_on(loc):
    ''' loc - tuple or location
    '''
    if type(loc) is tuple:
        x,y = loc
        loc = location_from_axis(x,y)
    game.scroll_to(loc, 0) # non-smooth transition
    return

def scroll_to(loc, y = None):
    if type(loc) is tuple:
        x,y = loc
        loc = location_from_axis(x,y)
    elif y is not None:
        x = loc
        loc = location_from_axis(x,y)
    game.scroll_to(loc)
    return