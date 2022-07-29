_is_dlg_engaged_ = False

class DialogState:
    action_type = 0
    line_number = 0
    reply_count = 0
    script_id = 0

    def get_reply_effect(self, idx):
        return str('abcd=1')
    def get_npc_reply_id(self, idx):
        return 0

def is_engaged() -> bool:
    return _is_dlg_engaged_

def get_current_state():

    return DialogState()