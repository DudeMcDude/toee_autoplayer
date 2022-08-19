from controller_constants import *
class ToeeLandmark:
    name = ''
    map = 0
    loc = None
    def __init__(self, name, map, loc):
        self.name = name
        self.map = map
        self.loc = loc
        return

moathouse_landmarks = [ 
    
    ToeeLandmark( 'frogs', MOATHOUSE_EXTERIOR_MAP, (482, 532)  ),
    ToeeLandmark( 'bandits', MOATHOUSE_EXTERIOR_MAP, (477, 467) ),
    #ToeeLandmark( 'back_entrance', MOATHOUSE_EXTERIOR_MAP, (429, 449) ),

    ToeeLandmark( 'viper', MOATHOUSE_RUINS_MAP, (480, 496) ),
    ToeeLandmark( 'raul', MOATHOUSE_RUINS_MAP, (468, 465) ),
    ToeeLandmark( 'stirges', MOATHOUSE_RUINS_MAP, (470, 501) ),
    ToeeLandmark( 'lizard', MOATHOUSE_RUINS_MAP, (509, 477) ),
    ToeeLandmark( 'tick', MOATHOUSE_RUINS_MAP, (502, 483) ),
    
    ToeeLandmark( 'zombies', MOATHOUSE_DUNGEON_MAP, (440, 420) ),
    ToeeLandmark( 'lubash', MOATHOUSE_DUNGEON_MAP, (417, 433) ),
    ToeeLandmark( 'stairs_down', MOATHOUSE_DUNGEON_MAP, (422, 459) ),
    ToeeLandmark( 'bugbears', MOATHOUSE_DUNGEON_MAP, (451, 517) ),

    ToeeLandmark( 'post_gnoll_hub', MOATHOUSE_DUNGEON_MAP, (519, 502) ),

    ToeeLandmark( 'gnolls', MOATHOUSE_DUNGEON_MAP, (480, 494) ),
    ToeeLandmark( 'ghouls', MOATHOUSE_DUNGEON_MAP, (506, 454) ),
    ToeeLandmark( 'crayfish', MOATHOUSE_DUNGEON_MAP, (544, 503) ),
    
    ToeeLandmark( 'outside_barracks_corridor', MOATHOUSE_DUNGEON_MAP, (535, 547) ),
    ToeeLandmark( 'corridor', MOATHOUSE_DUNGEON_MAP, (523, 547) ),
    ToeeLandmark( 'barracks', MOATHOUSE_DUNGEON_MAP, (494, 544) ),
    ToeeLandmark( 'lareth', MOATHOUSE_DUNGEON_MAP, (475, 547) ),
    ]


temple_landmarks = [
    ToeeLandmark( 'spiral_stairs', TEMPLE_INTERIOR, (483, 485) ),
    ToeeLandmark( '', TEMPLE_INTERIOR, () ),
    
]