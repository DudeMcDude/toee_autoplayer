from toee import game
from utilities import location_to_axis, location_from_axis, obj_percent_hp
import gamedialog as dlg
from toee import *



class StateTrans:
    new_state = '' # type: str
    # delay in msec
    delay = 0 # type: int
    
    def __init__(self, new_state, delay):
        self.new_state = new_state
        self.delay = delay
        return
    def __repr__(self):
        return 'StateTrans( new_state= "' + str(self.new_state) + '", delay=' + str(self.delay) + ' )'

    @staticmethod
    def convert_state(s):
        if isinstance(s, StateTrans):
            return s
        elif isinstance(s, list) or isinstance(s, tuple):
            if len(s) == 0:
                return None
            return StateTrans(s[0], s[1])
        elif s is None:
            return s
        else:
            raise Exception("bad arg for state")

class GoalState:
    id = '' #type: str
    cb = lambda slot: 1 #type: callable
    after_success = StateTrans('',0) #type: StateTrans
    after_failure = None #type: StateTrans
    params = None #type: dict
    
    def __init__(self, id, cb, after_s, after_f = None, params = None):
        if params is None:
            params = {}

        self.id = id
        self.cb = cb
        
        self.after_success = StateTrans.convert_state(after_s)
        self.after_failure = StateTrans.convert_state(after_f)
        self.params = params
        assert type(params) == dict, 'params must be dict'
        return
    def __repr__(self):
        return 'GoalState( id= "' + str(self.id) + '", after_success= ' + str(self.after_success) + ' )'

class GoalSlot:
    obj = None
    param1 = None #type: ...
    param2 = None #type: ...
    state = None #type: ...
    def __init__(self, obj):
        self.obj = obj
        self.param1 = 0
        self.param2 = 0
        self.state = None
        return
    def reset_by_goal_state(self, stage):
        # type: (GoalState) -> None
        self.state = None
        p1 = stage.params.get('param1')
        p2 = stage.params.get('param2')
        self.param1 = p1
        self.param2 = p2
        return
    def get_cur_time(self):
        return game.time.time_game_in_seconds(game.time)

class ControlScheme:
    __stages__ = {} #type: dict
    __cur_stage_id__ = 'start'
    def __init__(self, s = None):
        if s is not None:
            self.__set_stages__(s)
        return
    
    def __set_stages__(self, s):
        if type(s) == dict:
            self.__stages__ = s
        elif type(s) == list:
            self.__stages__ = {x.id:x for x in s}
        else:
            raise TypeError("__set_stages__: invalid argument type")

        self.__cur_stage_id__ = 'start'
        assert s.get('start') is not None, "'stages' Must have 'start' stage"
        for stage_id, stage in self.__stages__.items(): # type: (int, GoalState)
            stage = stage # type: GoalState
            next_id = stage.after_success.new_state
            if self.__stages__.get(next_id) is None:
                print('Error! stage not found: ' + str(next_id))
                exit()
        return

    def __repr__(self):
        return 'ControlScheme( __cur_stage_id__: "' + str(self.__cur_stage_id__) + '"'+' )' #+ ' stages: ' + str(self.__stages__)
        
    def get_cur_stage(self):
        # type: ()->GoalState
        stage = self.__stages__[self.__cur_stage_id__]
        return stage

    def execute(self, slot):
        #type: (GoalSlot) -> int
        # print('Executing: ' + self.__repr__() )
        stage = self.get_cur_stage()
        # print('Current stage: ' + str(stage))

        result = stage.cb(slot)
        # if not result:
        #     print('callback result: ' + str(result))

        next_stage = stage.after_success #type: StateTrans
        if result == 0:
            if stage.after_failure is not None:
                next_stage = stage.after_failure
            else:
                next_stage = StateTrans(stage.id, 333)
        # print('next stage: ' + str(next_stage))

        new_id = next_stage.new_state
        new_stage = self.__stages__.get(new_id) # type: GoalState
        if new_stage is None:
            raise KeyError("No such stage: " + str(new_id))
        if new_id != self.__cur_stage_id__: # if entering new stage, reset GoalSlot's state
            slot.reset_by_goal_state(new_stage)
        self.__cur_stage_id__ = new_id

        return next_stage.delay


class UiController:
    def __init__(self):
        pass

    @staticmethod
    def start_ui_thread():
        game.timevent_add( UiController.py_ui_sched, (), 400, 1 )
        return

    @staticmethod
    def py_ui_sched():
        game.timevent_add( UiController.py_ui_sched, (), 400, 1 )
        UiController.py_ui_handler()
        return

    @staticmethod
    def py_ui_handler():
        # print('all your base' + str(game.global_vars[1]))
        return

    @staticmethod
    def py_ui_handler_old():
        if game.leader is not None:
            if game.leader.location != CritterController.__last_loc__:
                CritterController.__hang_count__ = 0
                CritterController.__last_loc__ = game.leader.location
            elif CritterController.__hang_count__ > 200:
                print('dehanger! quickloading')
                CritterController.__hang_count__ = 0
                CritterController.deactivate_all()
                press_quickload()
            else: 
                CritterController.__hang_count__ += 1
        return
    

class ControllerBase:
    __control_schemes__ = {} #type: dict #[str, ControlScheme]
    __cur_control_scheme_id__ = ''

    __logging__ = False

    __goal_slot__ = None  #type: GoalSlot
    
    def __init__(self):
        return

    def add_scheme(self, scheme, scheme_id):
        # type: (ControlScheme, int)->None
        self.__control_schemes__[scheme_id] = scheme
        return

    def set_active_scheme(self, scheme_id):
        if self.__control_schemes__.get(scheme_id) is None:
            return False
        
        self.__cur_control_scheme_id__ = scheme_id
        scheme = self.__control_schemes__[scheme_id] # type: ControlScheme
        self.__goal_slot__.reset_by_goal_state(scheme.get_cur_stage())
        return True

    def schedule(self, delay_msec = 200, real_time = 1):
        game.timevent_add( self.execute, (), delay_msec, real_time)
        return
    
    def execute_log(self, scheme):
        if self.__logging__:
            print('Controller: doing scheme[ID=%s] = %s ' % ( self.__cur_control_scheme_id__, str(scheme)) )
        return

    def execute(self):
        print('Controller execute()')

        scheme = self.__control_schemes__[self.__cur_control_scheme_id__] #type: ControlScheme
        self.execute_log(scheme)

        delay = scheme.execute(self.__goal_slot__)
        if delay:
            self.schedule(delay)
        else: # immediately execute
            self.execute()
        return

class CritterController(ControllerBase):
    __instance_ids__ = []
    __instances__ = {} #type: dict[int, CritterController]
    __id__ = None
    __last_id__ = -1
    
    __obj__ = None
    __was_in_combat__ = False
    __was_in_dialog__ = False
    
    __active__ = True
    
    __last_loc__ = 0
    __hang_count__ = 0

    def __init__(self, obj, slot = None):
        UiController.start_ui_thread()

        if slot is None:
            self.__goal_slot__ = GoalSlot(obj)
        else:
            self.__goal_slot__ = slot
            # assert type(slot) == type(GoalSlot), 'hrmpf'
        self.__obj__ = obj
        self.__id__ = CritterController.__last_id__ + 1
        CritterController.__last_id__ += 1
        print('CritterController inited, ID = %d' % self.__id__)
        if len(CritterController.__instances__) > 2:
            print('Lots of controllers... %d' % len(CritterController.__instances__) )
        CritterController.__instances__[self.__id__] = self
        return
    
    def __del__(self):
        print('Deleting CritterController, ID = %d' % self.__id__)
        self.activate(False)
        if self.__id__ in CritterController.__instances__:
            CritterController.__instances__.pop(self.__id__)
        return
    
    @staticmethod
    def get_instance(id):
        if type(id) == int:
            if id in CritterController.__instances__:
                return CritterController.__instances__[id]
        if type(id) == PyObjHandle:
            for k,v in CritterController.__instances__.items():
                v=v # type: CritterController
                if v.__obj__ == id:
                    return v
                pass    
            
        return None
    
    @staticmethod
    def deactivate_all():
        for k,v in CritterController.__instances__.items():
            v.activate(False)
        return
        
    def activate(self, val):
        self.__active__ = val
    
    def execute_log(self, scheme):
        if self.__logging__:
            print('Controller (ID %d): doing scheme[%s] = %s ' % ( self.__id__, self.__cur_control_scheme_id__, str(scheme)) )
        return

    def execute(self):
        # print('Critter Controller execute()')
        if not self.__active__:
            print('Critter Controller (ID %d): not active' % self.__id__)
            return
        
        # handle popups
        if game.is_alert_popup_active():
            press_enter()
            return self.schedule(100)
        
        if game.combat_is_active():
            self.__was_in_combat__ = True
            
            delay = combat_controller(self.__goal_slot__)
            if delay > 0:
                return self.schedule(delay)
            else:
                return self.schedule(100)

        if dlg.is_engaged():
            self.__was_in_dialog__ = True
            delay = dialog_controller(self.__goal_slot__)
            if delay <= 0:
                delay = 100
            return self.schedule(delay)
        
        super(CritterController).execute()
        return
        

def combat_controller(slot):
    obj = slot.obj
    if not game.combat_is_active():
        return 0

    def can_cast(spell_enum, spell_class, spell_level):
        sp = PySpellStore( spell_enum , spell_class, spell_level)
        return obj.can_cast_spell(sp)

    import tpactions
    actor = tpactions.get_current_tb_actor()
    if obj != actor: # delay
        return 500

    act_seq_cur = tpactions.get_cur_seq()
    tgt = select_target(obj)
    if tgt == OBJ_HANDLE_NULL: # end turn for now..
        print('No target, ending turn')
        press_space()
        return 500
    
    if obj.is_performing():
        return 500
    
    if True: #obj == game.party[1]: # ariel
        result = obj.ai_strategy_execute(tgt)
        if result == 1:
            return 1000

    # if act_seq_cur.tb_status.hourglass_state >= 4: # Full action bar
    #     print('Attacking ', tgt)
    #     if can_cast(spell_magic_missile, stat_level_wizard | 0x80, 1):
    #         obj.cast_spell(spell_magic_missile, tgt)
    #         return 500
    #     perform_action(D20A_UNSPECIFIED_ATTACK, obj, tgt, 0L)
    #     return 500
    # if act_seq_cur.tb_status.hourglass_state >= 2: # Standard Action
    #     # todo
    #     pass
    # if act_seq_cur.tb_status.hourglass_state >= 1: # Move Action
    #     # todo
    #     pass
    
    
    
    
    print('Ending turn... ')
    press_space()
    return 300
    

def dialog_controller(slot):
    def reply(i):
        print('Reply %d' % (i))
        press_key(DIK_1 + i)
        return
    
    ds = dlg.get_current_state()
    N = ds.reply_count
    if N <= 1:
        reply(0)
        return 750
    
    def find_attack_lines():
        attack_lines = []
        for i in range(N):
            effect = ds.get_reply_effect(i)
            if effect.find('npc.attack') >= 0:
                attack_lines.append(i)
        return attack_lines
    
    # for now just select any non-attacking lines
    attack_lines = find_attack_lines()
    for i in range(N):
        if i in attack_lines:
            continue
        reply(i)
        return 1000
    
    reply(0)
    return 750

def select_target(obj):
    vlist = game.obj_list_vicinity(obj.location, OLC_NPC)
    best_tgt = OBJ_HANDLE_NULL
    least_dist = 100000
    tgt_priority = []
    for tgt in vlist:
        if tgt.is_friendly(obj):
            continue
        if tgt.is_unconscious():
            continue
        flags = tgt.object_flags_get()
        if flags & OF_DONTDRAW:
            continue
        
        dist = tgt.distance_to(obj)
        if dist < 15:
            if obj.can_melee(tgt):
                dist = 0
        hp_pct = obj_percent_hp(tgt)
        tgt_priority.append( [tgt, dist, hp_pct])
    def sort_key(x):
        dist = x[1]
        hp_pct = x[2]
        if dist == 0:
            return hp_pct
        return dist + 100
    
    if len(tgt_priority) > 0:
        tgt_priority.sort(key=sort_key)
        print(tgt_priority)
        return tgt_priority[0][0]
    return OBJ_HANDLE_NULL #best_tgt




def perform_action( action_type, actor, tgt, location ):
    try:
        result = actor.action_perform( action_type, tgt, location)
    except RuntimeError as e:
        print(e.message)
        result = 0
        pass
    return result
