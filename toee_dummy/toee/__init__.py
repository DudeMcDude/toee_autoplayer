from templeplus.constants import *

# from ..utilities import *
OBJ_HANDLE_NULL = 0
class PySpellStore:
    spell_enum = 0
    spell_level = 0
    spell_class = 0
    spell_name = ''
    
    def __init__(self, spell_enum, spell_class, spell_level):
        return
    def is_area_spell(self):
        return False
    def is_mode_target(self, mode):
        return False
    def is_naturally_cast(self):
        return False
    def is_used_up(self):
        return False

    
    pass

class PyObjHandle:
    spells_known = () #type: tuple[PySpellStore]
    highest_arcane_class = 0
    highest_divine_class = 0
    def obj_get_int(self, obj_f_):
        return 0
    def obj_get_spell(self, obj_f_, idx):
        return PySpellStore()
    def obj_get_idx_obj(self, obj_f, idx):
        return PyObjHandle()
    def obj_get_idx_obj_size(self, obj_f_):
        return 0
    def inventory_item(self, idx):
        return PyObjHandle()
    def can_cast_spell(self, spell):
        #type: (PySpellStore)->int
        return 0
    def cast_spell(self, spell_enum, tgt = OBJ_HANDLE_NULL):
        return 0
    def get_num_spells_per_day(self, char_class, spell_level):
        return 0
    def get_num_spells_used(self, spell_class, spell_level):
        return 0
    def spontaneous_spells_remaining(self, char_class, spell_level):
        return 0
    def is_unconscious(self):
        return 0
    pass