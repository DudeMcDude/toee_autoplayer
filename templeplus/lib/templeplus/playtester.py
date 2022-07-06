import controllers
from controllers import ControllerBase, GoalSlot
print("tatakae")
print("tatakae")
import autoui


from new_game_controller import create_new_game_scheme

class Playtester(ControllerBase):
    def __init__(self):
        self.__goal_slot__ = GoalSlot()
        self.add_scheme( create_new_game_scheme(), 'new_game' )
        self.set_active_scheme('new_game')
        print('Beginning scheme in 1 sec...')
        self.schedule(1000, real_time=1)
        return