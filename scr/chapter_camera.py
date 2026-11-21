"""Follow the chapter autoplayer using the same camera pan as the game."""
import os
import time
from toee import game, OBJ_HANDLE_NULL, OF_OFF, OF_DONTDRAW
from utilities import location_from_axis, location_to_axis

_last_map = None
_last_point = None
_next_sample = 0
_trace = os.environ.get('IWDAP_CAMERA_LOG')
_pending = None
_last_pan = 0


def frame(actor, other=None):
    global _last_map, _last_point, _pending, _last_pan
    if not actor or actor == OBJ_HANDLE_NULL:
        return
    x, y = location_to_axis(actor.location)
    if other and other != OBJ_HANDLE_NULL and other.map == actor.map:
        ox, oy = location_to_axis(other.location)
        # Include both ends of a nearby action. For long shots keep the acting
        # character in frame instead of centering on empty ground between them.
        if max(abs(ox-x), abs(oy-y)) <= 14:
            x, y = (x+ox)//2, (y+oy)//2
    tile = location_from_axis(x, y)
    now = time.time()
    still = (_last_map == actor.map and _last_point and
             max(abs(x-_last_point[0]), abs(y-_last_point[1])) < 4)
    if still and now - _last_pan < 0.5:
        return
    from controller_ui_util import obtain_widget
    import tpgui
    window = obtain_widget([('intgame_main_window',)])
    sx, sy = tpgui.world_to_screen(tile)
    w,h = (window.wid.width,window.wid.height) if window else (0,0)
    if still and (not w or not h or (w*.12 < sx < w*.88 and h*.10 < sy < h*.82)):
        return
    offscreen = w and h and not (0 <= sx < w and 0 <= sy < h)
    if offscreen:
        # A world click can leave the engine cursor in its edge-scroll margin.
        # Park it in the viewport before reacquiring a lost subject.
        game.mouse_move_to((w//2,h//2),1)
    if _trace:
        _pending = actor.map, tile, (sx,sy), now
    game.scroll_to(tile, 0 if offscreen else 1)
    _last_pan = now
    _last_map, _last_point = actor.map, (x, y)


def follow():
    global _next_sample, _pending
    now = time.time()
    if now < _next_sample:
        return
    _next_sample = now + 0.30
    import ie_cutscene
    if game.char_ui_display_type or ie_cutscene.active():
        return
    leader = game.leader
    if not leader or leader == OBJ_HANDLE_NULL:
        return
    if _pending and now - _pending[3] >= 0.25:
        import tpgui
        m, tile, before, unused = _pending
        if m == leader.map:
            with open(_trace, 'a') as trace:
                trace.write('map %d tile %s pixels %s -> %s\n' % (m, location_to_axis(tile), before, tuple(tpgui.world_to_screen(tile))))
        _pending = None
    import gamedialog
    if gamedialog.is_engaged():
        return
    if game.combat_is_active():
        import tpactions
        actor = tpactions.get_current_tb_actor()
        if not actor or actor == OBJ_HANDLE_NULL or actor.map != leader.map or actor.object_flags_get() & (OF_OFF | OF_DONTDRAW):
            frame(leader)
            return
        seq = tpactions.get_cur_seq() if actor.is_performing() else None
        target = seq.target if seq and seq.performer == actor else None
        if target and target.object_flags_get() & (OF_OFF | OF_DONTDRAW):
            target = None
        if actor in game.party:
            frame(actor, target)
        else:
            party = [pc for pc in game.party if not pc.is_unconscious()]
            witnesses = [pc for pc in party if pc.distance_to(actor) < 55 and pc.has_los(actor)]
            if witnesses:
                observer = min(witnesses, key=lambda pc: pc.distance_to(actor))
                frame(actor, target or observer)
            else:
                # Native initiative also pans to distant orcs in unexplored
                # tunnels. Keep the visible action in frame on those turns.
                anchor = target if target in party else min(party or [leader], key=lambda pc: pc.distance_to(actor))
                frame(anchor)
    else:
        frame(next((pc for pc in game.party if not pc.is_unconscious()), leader))
