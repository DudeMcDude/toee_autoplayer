# import controllers
from controllers import ControllerBase, GoalSlot
print("tatakae")
print("tatakae")
# import autoui


class Playtester(ControllerBase):
    __instance__ = None #type: Playtester
    def __init__(self):
        self.__goal_slot__ = GoalSlot()
        Playtester.__instance__ = self
        return
    
    @staticmethod
    def get_instance():
        return Playtester.__instance__
    
    