from templeplus.constants import *
# from ..utilities import *
OBJ_HANDLE_NULL = 0
class PySpellStore:
    spell_enum = 0
    spell_level = 0
    spell_class = 0
    spell_name = ''
    
    def is_area_spell(self):
        return False
    def is_mode_target(self, mode):
        return False
    def is_naturally_cast(self):
        return False
    def is_used_up(self):
        return False

    
    pass