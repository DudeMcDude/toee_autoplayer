from toee import game
from utilities import location_to_axis, location_from_axis, obj_percent_hp
import gamedialog as dlg
from toee import *
from collections import deque



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
            raise Exception("bad arg for state",s)

class GoalStateCb:
    cb = lambda slot: 1 #type: callable
    params = None #type: dict
    state = None #type: dict
    def __init__(self, cb, params = None, state = None):
        if params is None:
            params = {}
        
        self.cb = cb        
        self.params = params
        self.state = state
        assert type(params) == dict, 'params must be dict'

class GoalState(GoalStateCb):
    id = '' #type: str
    after_success = StateTrans('',0) #type: StateTrans
    after_failure = None #type: StateTrans
    
    def __init__(self, id, cb, after_s, after_f = None, params = None, state = None):
        GoalStateCb.__init__(self, cb, params, state)
        
        self.id = id
        
        self.after_success = StateTrans.convert_state(after_s)
        self.after_failure = StateTrans.convert_state(after_f)
        return
    def __repr__(self):
        return 'GoalState( id= "' + str(self.id) + '", after_success= ' + str(self.after_success) + ' )'

    @staticmethod
    def from_sequence(base_id, s, after_s, after_f = None):
        #type: (str, list[GoalState], StateTrans, StateTrans)->list[GoalState]
        N = len(s)
        if N == 0:
            raise ValueError("empty s")
        result = []
        idx = 0
        # print('appending GoalStates: ')
        for state in s:
            if idx == 0: # first 
                state.id = base_id
                state.after_success.new_state = base_id + "_{:d}".format(idx+1)
                if StateTrans.convert_state(state.after_failure) is None:
                    state.after_failure = StateTrans('', 300)
                state.after_failure.new_state = base_id
            elif idx < N-1:
                state.id = base_id + "_{:d}".format(idx)
                state.after_success.new_state = base_id + "_{:d}".format(idx+1)
                if StateTrans.convert_state(state.after_failure) is None:
                    state.after_failure = StateTrans('', 300)
                state.after_failure.new_state = base_id + "_{:d}".format(idx)
            else: # idx == N-1
                state.id = base_id + "_{:d}".format(idx)
                state.after_success = StateTrans.convert_state(after_s)
                state.after_failure = StateTrans.convert_state(after_f)
                
            idx += 1
            # print(state.id, state.after_success)
            result.append(state)
        return result

class GoalStateCondition(GoalState):
    def __init__(self, id, condition_cb, after_s, after_f):    
        GoalState.__init__(self, id, lambda slot: condition_cb(slot) != 0, after_s, after_f,  )
        return

class GoalStateCreatePushScheme(GoalState):
    def __init__(self, id, scheme_id, scheme_generator, args, after_s ):
        import controller_callbacks_common
        GoalState.__init__(self, id, controller_callbacks_common.gs_create_and_push_scheme, after_s, None, params={'param1': scheme_id, 'param2': (scheme_generator, args)})
        return

class GoalStackEntry:
    scheme_id = None #type: str
    scheme = None
    # for saving state when pushing other goals
    state_save = None #type: dict 
    __cur_stage_id__ = 'start'
    scheme_state = None #type: dict # for scheme-level statekeeping


    def __init__(self, scheme_id, scheme, stage_id = None, state = None):
        #type: (str, ControlScheme, str, dict)->None
        if stage_id is None:
            stage_id = 'start'
        
        self.scheme_id = scheme_id
        self.scheme = scheme
        self.__cur_stage_id__ = stage_id
        self.state_save = state
        self.scheme_state = {}
        return

    def __repr__(self):
        return 'GoalStackEntry( scheme_id = %s, cur stage = %s )' % (self.scheme_id, self.__cur_stage_id__)

    def get_cur_stage_id(self):
        #type: ()->str
        return self.__cur_stage_id__

    def get_cur_stage(self):
        #type: ()->GoalState
        cur_id = self.get_cur_stage_id()
        scheme = self.get_scheme()
        stage = scheme.get_stage(cur_id)
        return stage

    def get_scheme(self):
        #type: ()->ControlScheme
        return self.scheme

    def execute(self, slot):
        #type: (GoalSlot)->int
        scheme = self.get_scheme()
        cur_id = self.get_cur_stage_id()
        res = scheme.execute(cur_id, slot)
        return res

    def advance_stage(self, slot, succeeded):
        #type: (GoalSlot, int)-> int
        ''' Advances stage
        * slot: GoalSlot
        * succeeded: whether prev execution succeeded
        Return value: next stage delay
        '''
        scheme = self.get_scheme()
        
        stage = self.get_cur_stage()
        result = succeeded

        next_stage = stage.after_success
        if result == 0:
            if stage.after_failure is not None:
                next_stage = stage.after_failure
            else:
                next_stage = StateTrans(stage.id, 333)
        # print('next stage: ' + str(next_stage))

        new_id = next_stage.new_state
        
        new_stage = scheme.get_stage(new_id)
        if new_stage is None:
            raise KeyError("No such stage: " + str(new_id))
        if new_id != self.__cur_stage_id__: # if entering new stage, reset GoalSlot's state
            slot.reset_by_goal_state(new_stage, new_stage.state)
        self.__cur_stage_id__ = new_id

        return next_stage.delay
    
    def is_ended(self):#TODO
        if self.scheme.is_endless:
            return False
        return self.__cur_stage_id__ == ControlScheme.END_STAGE_ID

    def reset(self):
        self.__cur_stage_id__ = ControlScheme.START_STAGE_ID
        return

class GoalSlot:
    obj = None
    param1 = None #type: ...
    param2 = None #type: ...
    state = None #type: dict
    state_prev = None #type: dict
    goal_stack = None #type: deque[GoalStackEntry]
    __dialog_state__ = None #type: dict

    def __init__(self, obj = None):
        self.obj = obj
        self.param1 = 0
        self.param2 = 0
        self.state = None
        self.goal_stack = deque()
        return
    def init_state(self, state):
        #type: (dict)->None
        if self.state is None:
            self.state = state
            return 1
        return 0
    def reset_by_goal_state(self, stage, state = None):
        # type: (GoalStateCb, dict) -> None
        if self.state is not None:
            self.state_prev = dict(self.state) # copy last state
        self.state = None
        p1 = stage.params.get('param1')
        p2 = stage.params.get('param2')
        self.param1 = p1
        self.param2 = p2
        if state is not None:
            self.state = dict(state) # copy state dict
        return
    
    def get_cur_time(self):
        return game.time.time_game_in_seconds(game.time)
    def get_scheme_state(self):
        scheme_inst = self.goal_stack[0]
        return scheme_inst.scheme_state

class ControlScheme:
    __stages__ = {} #type: dict[str,GoalState]

    START_STAGE_ID = 'start'
    END_STAGE_ID = 'end'
    is_endless = False
    
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

        
        assert s.get('start') is not None, "'stages' Must have 'start' stage"
        for stage_id, stage in self.__stages__.items(): # type: (int, GoalState)
            stage = stage # type: GoalState # this line is just for intellisense...
            next_id = stage.after_success.new_state
            if self.__stages__.get(next_id) is None:
                print('Error! stage %s could not find next ID = (%s) ' % (stage.id ,str(next_id)))
                exit()
        return

    def __repr__(self):
        return 'ControlScheme( stages: ' + str(self.__stages__) + ' )'
        
    def get_stage(self, stage_id):
        # type: (str)->GoalState
        stage = self.__stages__[stage_id]
        return stage

    def execute(self, stage_id, slot):
        #type: (GoalSlot, str) -> int
        # print('Executing: ' + self.__repr__() )

        stage = self.get_stage(stage_id)
        # print('Current stage: ' + str(stage))

        result = stage.cb(slot)
        # if not result:
        #     print('callback result: ' + str(result))
        return result
    
    
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
    __control_schemes__ = {} #type: dict[str, ControlScheme]
    __cur_control_scheme_id__ = ''

    __logging__ = False

    __goal_slot__ = None  #type: GoalSlot
    __cur_scheme_instance__ = None #type: GoalStackEntry

    dialog_handler = lambda slot: 1
    __dialog_handler_en__ = True

    __combat_handler__ = lambda slot: 1
    __combat_mode__ = False
    
    __active__ = True
    
    def __init__(self):
        self.__goal_slot__ = GoalSlot()
        self.__active__ = True
        return

    def set_active(self, value):
        will_execute = False
        if self.__active__ == False and value == True:
            print('activating controller')
            will_execute = True
            # self.schedule(300) # runs the base class..
        
        self.__active__ = value
        if will_execute:
            self.execute()
        return
    def is_active(self):
        return self.__active__

    def game_reset(self):
        self.interrupt()
        return
    def add_scheme(self, scheme, scheme_id):
        # type: (ControlScheme, int)->None
        assert isinstance(scheme, ControlScheme) == True, "bad scheme type!"
        self.__control_schemes__[scheme_id] = scheme
        return

    def set_active_scheme(self, scheme_id, state = None):
        #type: (str, dict)-> bool
        
        self.__cur_control_scheme_id__ = scheme_id
        slot   = self.__goal_slot__
        scheme_inst = self.get_cur_scheme_instance()
        slot.reset_by_goal_state(scheme_inst.get_cur_stage(), state)

        return True
    
    def set_dialog_handler(self, cb):
        self.dialog_handler = cb
        return
    def dialog_handler_en(self, value):
        self.__dialog_handler_en__ = value

    def set_combat_handler(self, cb):
        self.__combat_handler__ = cb
        return
    def combat_mode_set(self, value):
        self.__combat_mode__ = value
        return

    def push_scheme(self, scheme_id):
        #type: (str)-> bool
        if not scheme_id in self.__control_schemes__:
            return False

        prev_scheme_id = self.__cur_control_scheme_id__
        scheme      = self.__control_schemes__[scheme_id]
        scheme_prev = self.__control_schemes__.get(prev_scheme_id)
        
        slot = self.__goal_slot__
        
        # slot.push(scheme_id)
        new_entry = GoalStackEntry(scheme_id, scheme, ControlScheme.START_STAGE_ID, slot.state)

        slot.goal_stack.appendleft( new_entry )
        self.__cur_scheme_instance__ = new_entry
        self.set_active_scheme(scheme_id)
        return True

    def pop_scheme(self):
        slot = self.__goal_slot__
        entry_popped = slot.goal_stack.popleft()
        
        state = entry_popped.state_save

        if len(slot.goal_stack) > 0:
            prev_entry = slot.goal_stack[0]
            if self.__logging__:
                print('pop_scheme: going back to ' + str(prev_entry.scheme_id))
            self.__cur_scheme_instance__ = prev_entry
            self.set_active_scheme(prev_entry.scheme_id, entry_popped.state_save)
        else:
            self.__cur_scheme_instance__ = None
        return

    def interrupt(self):
        print('Controller: Interrupt!')
        slot = self.__goal_slot__
        while len(slot.goal_stack) > 1:
            self.pop_scheme()
        return

    def schedule(self, delay_msec = 200, real_time = 1):
        game.timevent_add( self.execute, (), delay_msec, real_time)
        return
    
    def log_execution(self, scheme_inst = None):
        if self.__logging__:
            if scheme_inst is None:
                scheme_inst = self.get_cur_scheme_instance()
            print('Controller: doing scheme[ID=%s] = %s ' % ( self.__cur_control_scheme_id__, str(scheme_inst)) )
        return

    def get_cur_scheme_instance(self):
        slot = self.__goal_slot__
        scheme_inst = slot.goal_stack[0]
        return scheme_inst

    def execute(self):
        # print('Controller execute()')
        if not self.__active__:
            return
        
        scheme_inst = self.get_cur_scheme_instance()
        self.log_execution(scheme_inst)
        
        slot = self.__goal_slot__
        
        # generic dialogue handler (mostly for unplanned dialogues)
        if dlg.is_engaged() and self.__dialog_handler_en__:
            result = self.dialog_handler(slot)
            delay = 750
            if result > 100:
                delay = result
            self.schedule(delay)
            return
        else:
            slot.__dialog_state__ = None

        if game.combat_is_active():
            if not self.__combat_mode__:
                # self.interrupt()
                self.__combat_handler__(slot) # in charge of creating / pushing a scheme..
                self.combat_mode_set(True)
                return self.schedule(100)
        else:
            self.combat_mode_set(False)
        
            
            # delay = self.__combat_handler__(slot)
            # if delay > 0:
            #     return self.schedule(delay)
            # else:
            #     return self.schedule(100)

        result = scheme_inst.execute(slot)
        if self.__logging__:
            print('  execute() result: %s' % str(result))

        if self.get_cur_scheme() != scheme_inst.scheme: # don't advance the stage yet since we've started a new one (or resumed a previous one)
            #TODO: handle same scheme, but in different instances?
            if self.__logging__:
                print('Controller: scheme changed')
            self.schedule(100)
            return

        self.advance(result) # advance the scheme goal state
        return

    def get_cur_scheme(self):
        if self.__cur_control_scheme_id__ in self.__control_schemes__:
            scheme = self.__control_schemes__[self.__cur_control_scheme_id__] #type: ControlScheme
            return scheme
        return None
        
    def advance(self, result):
        scheme_inst = self.get_cur_scheme_instance()
        if scheme_inst.is_ended():
            self.pop_scheme()
            self.execute()
            return
        
        slot = self.__goal_slot__
        delay  = scheme_inst.advance_stage(slot, result)
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





