def map_from_scene(x,y):
    #type: (int, int)->list[int]
    return

def world_to_screen(loc_or_obj):
    #type: (...)->list[int]
    return

class WidgetBase:
    id = 0
    name = ''
    source_uri = ''
    width = 0
    height = 0
    x = 0
    y = 0
    parent = None #type: WidgetContainer
    visible = False
    def abs_x(self):
        return 0
    def abs_y(self):
        return 0
    @property
    def pos(self):
        return (self.x,self.y)
    @pos.setter
    def pos(self, value):
        self.x, self.y = value
    def show():
        return
    def hide():
        return
    def bring_to_front():
        return
    
    pass


class WidgetContent:
    x = 0
    y = 0
    width = 0
    height = 0

class WidgetText(WidgetContent):
    def set_text(self, txt):
        #type: (str)->None
        return
    def set_style_by_id(self, style_id):
        #type: (str)->None
        return

class WidgetImage(WidgetContent):
    def set_image(self, path):
        #type: (str)->None
        return

class WidgetContainer(WidgetBase):
    def add_image(self, path):
        #type: (str)->WidgetImage
        return WidgetImage()
    def add_text(self, txt = '', txt_style_id = ''):
        #type: (str, str)->WidgetText
        return WidgetText()
    pass

def _add_root_container(id, w, h):
    return WidgetContainer()

def _add_container(parent_id, id,w,h):
    #type: (str,str,int,int)->WidgetContainer
    return WidgetContainer()

def _get_container(id):
    #type: (str)->WidgetContainer
    return WidgetContainer()