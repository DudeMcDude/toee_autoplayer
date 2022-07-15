# import controllers
from controllers import ControllerBase, GoalSlot
print("tatakae")
print("tatakae")
# import autoui
from ui_time_event import UiTimeEvent

class Playtester(ControllerBase):
    __instance__ = None #type: Playtester
    def __init__(self):
        self.__goal_slot__ = GoalSlot()
        Playtester.__instance__ = self
        return
    
    @staticmethod
    def get_instance():
        return Playtester.__instance__
    
    def schedule(self, delay_msec = 200, real_time = 1):
        UiTimeEvent.schedule( self.execute, (), delay_msec)
        # game.timevent_add( self.execute, (), delay_msec, real_time) 
        # # removed the above to avoid the game (not) serializing the controller object (which would lead to a crash on game load)
        return
    