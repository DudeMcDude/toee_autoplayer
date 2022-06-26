import tpgui

def debug_print(m):
    print(m)
    return

def get_active_windows():
    return tpgui._get_active_windows()

def convert_widget_ids(widget_ids):
    # debug_print('convert_widget_ids: ' + str(widget_ids))
    return [TWidget(id) for id in widget_ids]

class TWidget:
    is_legacy_widget = False
    is_window = False
    is_button = False
    wid = None
    children_ids = None
    id = -1
    name = ""
    source_uri = ""

    def __init_from_legacy_widget__(self, id):
        wid = tpgui._get_legacy_widget(id)
        if wid is None:
            return False
        
        self.is_legacy_widget = True

        self.wid = wid
        self.name = wid.name
        self.is_window = wid.is_window
        self.is_button = wid.is_button
        if self.is_window:
            self.children_ids = wid.children
        return True

    def __init_from_advanced_widget__(self, id):
        wnd = tpgui._get_adv_widget_container(id)
        if wnd is not None:
            self.wid = wnd
            self.is_window = True
            self.children_ids = wnd.children_legacy_ids
            self.name = wnd.name
            self.source_uri = wnd.source_uri
            return True
        btn = tpgui._get_adv_widget_button(id)
        if btn is not None:
            self.wid = btn
            self.is_button = True
            self.source_uri = btn.source_uri
            self.name = btn.name
            return True
        return False
    
    def __init__(self, id):
        #type: (int)->None
        # debug_print( 'TWidget __init__: ID = ' + str(id) )
        self.children_ids = []
        if self.__init_from_legacy_widget__(id):
            self.id = id
            return
        
        self.is_legacy_widget = False
        if self.__init_from_advanced_widget__(id):
            self.id = id
        return

    @property
    def full_name(self):
        return \
            self.source_uri + \
            " " if self.source_uri and self.name else "" +  \
            self.name

    def __repr__(self):
        return "TWidget ({}, {})".format(self.id, self.full_name)

class TWidgetIdentifier:
    name = None
    source_uri = None
    parent_name = None
    child_idx = None # index in parent's children
    def __init__(self, name, source_uri = None, parent_name = None, child_idx = -1):
        self.name = name
        self.source_uri = source_uri
        self.parent_name = parent_name
        self.child_idx = child_idx
        return
    @property
    def has_name_and_uri(self):
        return len(self.name) > 0 and self.source_uri is not None and len(self.source_uri) > 0
    @property
    def has_parent_name(self):
        return self.parent_name is not None and len(self.parent_name)

def find_by_identifier(w_identifier, wid_ids = None, searching_in_parent = False):
    # type: (TWidgetIdentifier, list[int], bool)->list[TWidget]
    # debug_print('searching for widget: ' + str(w_identifier.name))

    if type(w_identifier) is str:
        w_identifier = TWidgetIdentifier(w_identifier)
    elif type(w_identifier) is list or type(w_identifier) is tuple:
        w_identifier = TWidgetIdentifier(*w_identifier)

    if wid_ids is None:
        widgets = convert_widget_ids(get_active_windows())
    elif isinstance(wid_ids, TWidget):
        widgets = [wid_ids,]
    else:
        widgets = convert_widget_ids(wid_ids)
    if len(widgets) == 0:
        return []
    
    def find_in_children():
        par_idx = w_identifier.child_idx
        if not w_identifier.has_parent_name: # searching in root widget list
            if par_idx >= len(widgets):
                return None
            return [widgets[par_idx],]

        par_name = w_identifier.parent_name
        for wid in widgets:
            if wid.name == par_name:
                if par_idx >= len(wid.children_ids):
                    return []
                return [TWidget(wid.children_ids[par_idx]) , ]
        return []

    if w_identifier.has_name_and_uri:
        for wid in widgets:
            if wid.name == w_identifier.name and wid.source_uri == w_identifier.source_uri:
                return [wid,]
    
    elif w_identifier.child_idx >= 0: # find by parent name and child index
        return find_in_children()
        
    else: # search just by name
        the_list = [wid for wid in widgets if wid.name == w_identifier.name]
        if len(the_list) >= 1:
            return the_list
    
    # not found - search in children
    for wid in widgets:
        result = find_by_identifier(w_identifier, wid.children_ids)
        if len(result) >= 0:
            return result
    
    return []   