# problem: python threads are frozen while in main menu...

from toee import game

class UiController:
    __thread__ = None
    __main_thread__ = None
    def __init__(self):
        pass

    @staticmethod
    def start_ui_thread():
        if UiController.__thread__ is not None:
            return
        import threading
        for thread in threading.enumerate():
            if thread.name.lower().find('mainthread') >= 0:
                UiController.__main_thread__ = thread
        UiController.__thread__ = threading.Thread(target = UiController.py_ui_handler)
        UiController.__thread__.start()
        return

    @staticmethod
    def py_ui_handler():
        import time
        while UiController.__main_thread__.is_alive():
            print('all your base' + str(game.global_vars[1]))
            time.sleep(0.3)
            # if game.leader is not None:
            #     if game.leader.location != CritterController.__last_loc__:
            #         CritterController.__hang_count__ = 0
            #         CritterController.__last_loc__ = game.leader.location
            #     elif CritterController.__hang_count__ > 200:
            #         print('dehanger! quickloading')
            #         CritterController.__hang_count__ = 0
            #         CritterController.deactivate_all()
            #         press_quickload()
            #     else: 
            #         CritterController.__hang_count__ += 1
        return