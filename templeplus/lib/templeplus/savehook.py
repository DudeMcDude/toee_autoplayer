
#use 4 space indentation!

def save(filename):
    return

def load(filename):
    return

# Co8 python save hook - executes after the archive is done
# save hook (default - Co8 hook; will silently fail for vanilla; feel free to change for your own custom mod!)
def post_save(filename):
    try:
        import _co8init
        print "imported Co8Init inside templeplus package"
        _co8init.save(filename)
        print "Co8 Save hook successful"
    except:
        print "Co8 Save hook failed\n"

def do_tutorial_on_load():
    from toee import game
    if game.leader.map != 5116: # tutorial map
        return

    from utilities import location_to_axis
    x,y = location_to_axis(game.leader.location)
    if x >= 500 and y <= 470: # first room
        from tutorial_level_1_controller import do_tutorial_room1
        do_tutorial_room1()
    return

# save hook (default - Co8 hook; will silently fail for vanilla; feel free to change for your own custom mod!)
def post_load(filename):
    try:
        import _co8init
        _co8init.load(filename)
        do_tutorial_on_load()
        
    except:
        print "Co8 Load hook failed\n"