from toee import game
import bisect


class UiTimeEvent:
    __t_expire__ = None
    __serial_id__ = 0
    __callback__ = None
    __is_advance_time__ = False
    ui_time_events = [] # type: list[UiTimeEvent]
    ui_time_events_advance = []
    __first_after_reset__ = False
    
    def __init__(self, t_stamp, cb, args):
        self.__t_expire__ = t_stamp
        self.__id__ = UiTimeEvent.__serial_id__
        self.__callback__ = cb
        self.__args__ = args
        UiTimeEvent.__serial_id__ += 1
        return
    def __cmp__(self, other):
        return self.__t_expire__.__cmp__(other.__t_expire__)
    
    @staticmethod
    def schedule(cb, args, delay_ms):
        t_stamp = game.time_session
        t_stamp.add_ms( delay_ms )
        new_evt = UiTimeEvent(t_stamp, cb, args)
        if UiTimeEvent.__is_advance_time__ == False:
            bisect.insort(UiTimeEvent.ui_time_events, new_evt)
        else:
            bisect.insort(UiTimeEvent.ui_time_events_advance, new_evt)
        return
    
    @staticmethod
    def expire_events():
        time_real = game.time_session
        last_idx = None
        # need to copy ui_time_events in case the callback changes them...
        for idx, evt in enumerate(UiTimeEvent.ui_time_events):
            if evt.delta_ms(time_real) <= 0: # time event expired
                evt.cb()
                last_idx = idx+1
            else:
                break # time events are sorted, so beyond this they should be un-expired
        if last_idx: # expire all the events
            del(UiTimeEvent.ui_time_events[0:last_idx])
        
        for evt in UiTimeEvent.ui_time_events_advance:
            bisect.insort(UiTimeEvent.ui_time_events, evt)
        UiTimeEvent.ui_time_events_advance = []
        return

    def delta_ms( self, t_stamp ):
        # type: (int)->int
        return self.__t_expire__.delta_ms(t_stamp)
    
    def cb(self):
        # print("I have expired! me = " + str(self) ) + " cur time: " + str(game.time_session)
        self.__callback__(*self.__args__)
        return
    def __repr__(self):
        return "UiTimeEvent (ID: " + str(self.__id__) + ", expiration time: " + str(self.__t_expire__) + ")"

