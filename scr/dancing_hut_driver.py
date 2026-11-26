"""Drive the Dancing Hut Beta 0.98 opening and optional Chapter 1 continuation."""
import os
import time
from collections import namedtuple

import debug
import gamedialog
from toee import *
from utilities import location_from_axis, location_to_axis

from controller_callbacks_common import dlg_reply, gs_create_and_push_scheme, gs_press_widget
import controller_ui_util as ui
from controllers import ControlScheme, GoalState, GoalStateStart


VILLAGE, STEPPE, CASTLE = 5099, 5062, 5002
KEEP_OUTSIDE = (5095, 5111)
HALL, DORMITORIES, BASEMENT = 5145, 5144, 5143
SOCIAL_SKILLS = (skill_diplomacy, skill_bluff, skill_intimidate,
                 skill_gather_information, skill_sense_motive)
PARTY = (('paladin', 'Alhandra'), ('bard', 'Devis'), ('cleric', 'Jozan'))
LOG = None
ST = {}

# The tuple orders eligible destinations when guards make replies conditional.
# DialogState exposes destination and effect, but not the underlying reply ID.
DIALOGUE = {
    315: {1: 5, 5: 10, 10: 0},                       # Opening narration
    415: {1: 5, 5: 10, 10: 0},
    492: {1: 10, 10: 20, 20: 50, 25: 50, 30: 50, 40: 50,
          45: 50, 50: 55, 55: 60, 60: 70, 70: 80, 80: 90, 90: 0},
    493: {1: 20, 20: 60, 60: 0},
    494: {1: 10, 10: 20, 20: 0, 30: 20, 40: 0},
    495: {1: 10, 10: (60, 50), 20: 25, 25: (60, 50), 50: 55,
          55: 0, 60: 75, 75: 0, 78: 75, 80: (60, 50), 100: 75},
    496: {1: 5, 5: 0, 10: 15, 15: 20, 20: 30, 30: 40, 40: 50,
          50: 60, 60: 70, 70: 80, 75: 80, 80: 90, 90: 0, 100: 0,
          110: (15, 0)},
    506: {1: 5, 5: 20, 20: 0, 30: 0},
    510: {1: 10, 10: 20, 20: 30, 30: 0, 90: 0, 100: 0},
    409: {1: 5, 90: 5, 100: (5, 0), 5: 10, 10: 15,
          15: (35, 30, 40, 45, 50), 30: 60, 35: 60, 40: 60,
          45: 60, 50: 60, 60: 65, 65: 70, 70: 80, 80: 100},
    411: {1: 5, 5: 0},                               # Learn about Pelor
    512: {1: (25, 20), 10: 15, 15: 25, 20: 30, 25: 30, 30: 35,
          35: 40, 40: 50, 50: (55, 70, 60), 55: 60, 60: 70,
          70: 75, 75: 80, 80: 0},                    # Accept the investigation
    412: {1: (100, 10), 10: 15, 15: 20, 20: 30, 25: 30,
          30: 40, 40: 50, 50: 60, 60: 70, 70: 80, 80: 0, 100: 0},
}
REPORT = {10: 15, 15: (163, 100), 100: 115, 115: 130,
          130: 140, 140: 150, 150: 160, 160: 170, 163: 170, 170: 175, 175: 0}
AUDIENCE = {1: 10, 5: 10, 10: 20, 20: 30, 30: 40, 40: 0}

# More than one live reply may lead to row zero. In these cases choose the one
# that actually advances the quest or travel, and never start a barter screen.
EFFECTS = {(493, 60): '5062', (495, 75): '5095',
           (512, 80): 'qs_accepted', (412, 80): '5002', (412, 100): '5002'}

Step = namedtuple('Step', 'label maps action target tile')
ROUTE = (
    Step("Accept Vercingetorix's request", (VILLAGE,), 'chief', 492, (483, 478)),
    Step('Recruit Ariovistus', (VILLAGE,), 'recruit', 494, (487, 477)),
    Step('Ask Valencia for the western trail', (VILLAGE,), 'depart', 493, (482, 480)),
    Step('Gather Hawthorn berries', (STEPPE,), 'berries', 8062, (364, 455)),
    Step('Help Laodecia reach Loche Skye', (STEPPE,), 'guide', 495, (417, 410)),
    Step('Enter Loche Skye', KEEP_OUTSIDE, 'exit', 889, (479, 487)),
    Step('Learn about the priest of Pelor', (HALL, DORMITORIES), 'clue', 510, (498, 487)),
    Step('Find the dormitories', (HALL,), 'exit', 354, (484, 489)),
    Step('Accept the investigation from Ximenez', (DORMITORIES,), 'investigation', 512, (490, 471)),
    Step('Visit the merchants', (DORMITORIES,), 'exit', 353, (492, 496)),
    Step('Learn why Vicenzo split his tithes', (BASEMENT,), 'merchant', 409, (507, 514)),
    Step('Return to Ximenez', (BASEMENT,), 'exit', 354, (497, 501)),
    Step('Report to Ximenez and ask for Franciscus', (DORMITORIES,), 'report', 512, (490, 471)),
    Step('Ask Maynard for an audience', (DORMITORIES,), 'audience', 411, (488, 508)),
    Step('Accept the Bone Castle quest and depart', (DORMITORIES,), 'castle', 412, (490, 512)),
)
EXIT_DESTINATIONS = {889: HALL, 354: DORMITORIES, 353: BASEMENT}


def log(message):
    print('DHAP ' + message)
    if LOG:
        with open(LOG, 'a') as output:
            output.write('DHAP ' + message + '\n')


def current_step():
    index = ST.get('index')
    route = ST.get('route', ROUTE)
    return route[index] if index is not None and index < len(route) else None


def finish(message, success=False):
    if not ST.get('finished'):
        ST['finished'] = True
        log(('PASS ' if success else 'FAIL ') + message)
        log('DONE')
        ST['player'].set_active(False)
        ui.move_mouse = ST['move_mouse']
        if 'game_is_focused' in ST:
            ui.tpgui.game_is_focused = ST['game_is_focused']


def choose_reply(state, action):
    sid, line = state.script_id, state.line_number
    choices = DIALOGUE.get(sid, {})
    if ST.get('campaign'):
        choices, required = ST['campaign'].reply_plan(sid, line, action, choices)
    else:
        required = None
    if sid == 512 and action == 'report':
        choices = REPORT
    if sid == 411 and action == 'audience':
        choices = AUDIENCE
    goals = choices.get(line, ())
    if sid == 409 and line == 100 and game.global_flags[21]:
        goals = 0
    goals = (goals,) if isinstance(goals, int) else goals
    required = required or EFFECTS.get((sid, line))
    for target in goals:
        for index in range(state.reply_count):
            effect = state.get_reply_effect(index) or ''
            destination = max(0, state.get_npc_reply_id(index))
            opcode = state.get_reply_opcode(index)
            # The destination slot may retain an old node for an exit reply.
            if opcode == 1:
                destination = 0
            if destination != target or opcode in (3, 26):
                continue
            if (('npc.attack' in effect and required != 'npc.attack') or
                    '.barter(' in effect or 'qs_botched' in effect):
                continue
            if not required or required in effect:
                return index
    return None


def handle_dialogue(slot):
    state = gamedialog.get_current_state()
    if not state:
        return 200
    step = current_step()
    signature = (state.script_id, state.line_number, state.reply_count)
    if ST.get('dialogue') != signature:
        ST['dialogue'] = signature
        ST['replies'] = 0
    if ST['replies'] >= 3:
        finish('reply did not advance dialogue %d:%d' % signature[:2])
        return 200
    index = choose_reply(state, step.action if step else None)
    if index is None and state.reply_count:
        replies = [(state.get_npc_reply_id(i), state.get_reply_opcode(i))
                   for i in range(state.reply_count)]
        finish('no safe route in dialogue %d:%d while %s. Replies: %s' %
               (state.script_id, state.line_number, step.label if step else 'starting', replies))
        return 200
    campaign = ST.get('campaign')
    if index is None and state.script_id not in DIALOGUE and not (campaign and campaign.knows(state.script_id)):
        finish('unexpected dialogue %d:%d' % signature[:2])
        return 200
    ST['replies'] += 1
    log('REPLY %d:%d %s' % (state.script_id, state.line_number,
                            state.get_npc_reply_id(index) if index is not None else 'continue'))
    dlg_reply(index if index is not None else 0)
    if campaign and signature[0] in campaign.SALAZAAR_SCRIPTS and signature[1] == 195:
        ST['ending_seen'] = True
    return 350


def party_pcs():
    return [pc for pc in game.party if pc.type == obj_t_pc and not pc.is_unconscious()]


def has_berries():
    return any(pc.has_item(8001) for pc in game.party)


def find_healing_potion(pc):
    for proto in (8014, 8602, 8006, 8603, 8007, 8604, 8101, 8037):
        potion = pc.item_find_by_proto(proto)
        if potion:
            return potion
    return None


def ready_or_end_turn():
    import tpactions
    actor = tpactions.get_current_tb_actor()
    # A readied melee action hands off the turn in the engine's action sequence.
    turn = (game.combat_turn, actor.id) if actor else None
    if actor and ST.get('last_ready') != turn and tpactions.get_cur_seq().tb_status.hourglass_state >= 2:
        ST['last_ready'] = turn
        try:
            actor.action_perform(D20A_READY_ENTER, OBJ_HANDLE_NULL, 0)
            if tpactions.get_current_tb_actor() != actor or actor.is_performing():
                log('COMBAT %s readies for an enemy to approach' % actor.description)
                return
        except RuntimeError:
            tpactions.cur_seq_reset(actor)
    if os.name == 'nt':
        # The Python keypress helper queues a release. The combat hotkey needs
        # a press in this build. Send it only to this TemplePlus process.
        from ctypes import byref, windll
        from ctypes.wintypes import DWORD
        user32 = windll.user32
        window = user32.FindWindowA('TemplePlusMainWnd', 0)
        owner = DWORD()
        if window and user32.GetWindowThreadProcessId(window, byref(owner)) and owner.value == os.getpid():
            user32.PostMessageA(window, 0x0100, 0x20, 0)  # WM_KEYDOWN, VK_SPACE
            user32.PostMessageA(window, 0x0101, 0x20, 0)  # WM_KEYUP, VK_SPACE
            return
    ui.press_space()


def quest(index, *states):
    return game.quests[index].state in states


def passed(step, map_id):
    action = step.action
    if ST.get('campaign') and action.startswith('chapter_'):
        return ST['campaign'].passed(step, map_id)
    if action == 'chief':
        return quest(113, qs_accepted, qs_completed)
    if action == 'recruit':
        return any(pc.scripts[san_dialog] == 494 for pc in game.party)
    if action == 'depart':
        return map_id == STEPPE
    if action == 'berries':
        return has_berries() or quest(115, qs_completed)
    if action == 'guide':
        return map_id in KEEP_OUTSIDE and quest(115, qs_completed)
    if action == 'exit':
        return map_id == EXIT_DESTINATIONS[step.target]
    if action == 'clue':
        return game.global_flags[510]
    if action == 'investigation':
        return quest(116, qs_accepted, qs_completed)
    if action == 'merchant':
        return game.global_flags[21]
    if action == 'report':
        return quest(117, qs_accepted, qs_completed)
    if action == 'audience':
        return game.global_flags[305]
    return map_id == CASTLE and quest(118, qs_accepted, qs_completed)


def resume_index(map_id):
    if ST.get('campaign'):
        result = ST['campaign'].resume_index(map_id)
        if result is not None:
            return result
    if map_id == VILLAGE:
        return 0
    if map_id == STEPPE:
        return 3
    if map_id in KEEP_OUTSIDE:
        return 5
    if map_id == HALL:
        return 6
    if map_id == BASEMENT:
        return ST.get('route', ROUTE).index(ROUTE[10])
    if map_id == DORMITORIES:
        route = ST.get('route', ROUTE)
        if quest(117, qs_accepted, qs_completed) or quest(118, qs_accepted, qs_completed):
            return route.index(ROUTE[13])
        if game.global_flags[21]:
            return route.index(ROUTE[12])
        return route.index(ROUTE[8]) if game.global_flags[510] else 6
    if map_id == CASTLE and quest(118, qs_accepted, qs_completed):
        return len(ROUTE)
    return None


def nearby(actor, kind, predicate):
    matching = [obj for obj in game.obj_list_range(actor.location, 180, kind)
                if not obj.object_flags_get() & (OF_OFF | OF_DONTDRAW) and predicate(obj)]
    return min(matching, key=actor.distance_to) if matching else None


def distance(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


def walk(actor, tile, radius, now):
    origin = location_to_axis(actor.location)
    if distance(origin, tile) <= radius:
        return True
    if now < ST.get('walk_at', 0) or actor.is_performing():
        return False
    ST['walk_at'] = now + 0.6
    dx, dy = tile[0] - origin[0], tile[1] - origin[1]
    span = float(max(abs(dx), abs(dy)))
    # Limit native path probes and test the sides of a blocked direct route.
    candidates = []
    for size in (min(24, span), min(12, span), min(5, span)):
        for side in (0, -3, 3, -7, 7):
            point = (origin[0] + int(round((dx * size - dy * side) / span)),
                     origin[1] + int(round((dy * size + dx * side) / span)))
            if point not in candidates and distance(point, tile) < span:
                candidates.append(point)
    for point in candidates:
        if not debug.pathto(actor, *point):
            continue
        actor.run_to(location_from_axis(*point))
        for index, member in enumerate(game.party):
            if member == actor or member.is_unconscious() or member.is_performing():
                continue
            side = 2 if index % 2 else -2
            rear = 2 * (index // 2 + 1) if ST.get('campaign') and len(game.party) > 5 else 2
            formation_tile = point[0] + side, point[1] - rear
            if debug.pathto(member, *formation_tile):
                member.run_to(location_from_axis(*formation_tile))
        return False
    return False


def act(step, actor, now):
    action = step.action
    if ST.get('campaign') and action.startswith('chapter_'):
        ST['campaign'].act(step, actor, now)
        return
    script_id = step.target
    if action == 'clue' and actor.map == DORMITORIES:
        script_id, fallback = 411, (488, 508)
    else:
        fallback = step.tile
    if action == 'berries':
        target = nearby(actor, OLC_ITEMS, lambda item: item.name == 8001 and item.proto == step.target)
        radius = 2
    elif action == 'exit':
        target = nearby(actor, OLC_SCENERY, lambda obj: obj.obj_get_int(obj_f_scenery_teleport_to) == step.target)
        radius = 6
    else:
        target = nearby(actor, OLC_NPC, lambda npc: npc.scripts[san_dialog] == script_id
                        and npc not in game.party and not npc.is_unconscious())
        radius = 7
        if target and action not in ('merchant', 'audience'):
            speakers = party_pcs()
            if action == 'report':
                speakers = [pc for pc in speakers if target.has_met(pc)] or speakers
                actor = speakers[0]
            nearby_speakers = [pc for pc in speakers if pc.distance_to(target) <= 16 and pc.has_los(target)]
            if nearby_speakers:
                actor = min(nearby_speakers, key=target.distance_to)
    if action in ('merchant', 'audience') and target:
        actor = max(party_pcs(), key=lambda pc: max(pc.skill_level_get(target, s) for s in SOCIAL_SKILLS))
        if max(actor.skill_level_get(target, s) for s in SOCIAL_SKILLS) < 5:
            finish('no conscious PC can pass the skill gate for ' + step.label)
            return
    tile = location_to_axis(target.location) if target else fallback
    # The shop counter obstructs the combat raycast while allowing conversation.
    can_interact = target and (action == 'exit' or actor.has_los(target) or
                               (action == 'merchant' and actor.distance_to(target) <= 12))
    if target and not can_interact:
        radius = 1
    if not walk(actor, tile, radius, now) or not target or now < ST.get('act_at', 0):
        return
    if actor.is_performing() or not can_interact:
        return
    ST['act_at'] = now + 4
    ST['attempts'] += 1
    if ST['attempts'] > 3:
        finish('could not complete ' + step.label)
        return
    log('ACT %s at %s' % (step.label, tile))
    if action == 'berries':
        actor.action_perform(D20A_PICKUP_OBJECT, target, target.location)
    elif action == 'exit':
        actor.anim_goal_use_object(target)
    else:
        target.object_script_execute(actor, san_dialog)


def tick(slot):
    now = time.time()
    if len(game.party) == 0:
        if now - ST['started'] > 90:
            finish('waiting for a new game or Dancing Hut checkpoint')
        return 0
    pcs = party_pcs()
    if not pcs:
        finish('no conscious player characters remain')
        return 0
    map_id = pcs[0].map
    if not ST.get('entered'):
        ST['entered'] = True
        ST['index'] = resume_index(map_id)
        if ST['index'] is None:
            finish('unrecognized Dancing Hut starting map %d' % map_id)
            return 0
        log('START map %d with %s' % (map_id, ', '.join(pc.description for pc in pcs)))
        if ST.get('campaign'):
            log('PARTY ' + ', '.join('%s (level %d, HP %d/%d)' %
                                     (member.description, member.stat_level_get(stat_level),
                                      member.stat_level_get(stat_hp_current), member.stat_level_get(stat_hp_max))
                                     for member in game.party))
        if not os.environ.get('TP_AUTOLOAD'):
            for pc in pcs:
                pc.item_wield_best_all()
    if game.combat_is_active():
        import tpactions
        turn_actor = tpactions.get_current_tb_actor()
        turn = (game.combat_turn, turn_actor.id if turn_actor else None)
        if ST.get('combat_turn') != turn:
            ST.update(combat_turn=turn, turn_started=now)
        if now - ST['turn_started'] > 25:
            finish('combat stalled on map %d during %s\'s turn' %
                   (map_id, turn_actor.description if turn_actor else 'an unknown actor'))
            return 0
        if not ST.get('campaign') and now - ST.setdefault('combat_at', now) > 180:
            finish('combat exceeded three minutes on map %d' % map_id)
            return 0
        from new_game_controller import combat_action_handler
        from iwd_ch1_driver import local_waypoint
        campaign = ST.get('campaign')
        if not campaign or not campaign.combat_turn(turn_actor):
            combat_action_handler(slot, chapter_log=log, healing_potion=find_healing_potion,
                                  waypoint=local_waypoint, end_turn=ready_or_end_turn,
                                  target_filter=campaign.combat_target if campaign else None)
        ST['progress_at'] = now
        return 0
    ST.pop('combat_at', None)
    ST.pop('combat_turn', None)
    ST.pop('last_ready', None)
    ST.pop('dialogue', None)
    if game.char_ui_display_type in (1, 2):
        game.char_ui_hide()
        return 0
    while current_step() and passed(current_step(), map_id):
        log('COMPLETE ' + current_step().label)
        ST['index'] += 1
    step = current_step()
    if not step:
        if ST.get('campaign'):
            ST['campaign'].save_ending()
            return 0
        if game.savegame('DancingHut_BoneCastle', 'Dancing Hut - Bone Castle arrival'):
            finish('reached Bone Castle with quest 118 accepted', True)
        else:
            finish('reached Bone Castle with quest 118 accepted, but the checkpoint could not be saved')
        return 0
    position = (map_id, ST['index'], tuple(pc.location for pc in pcs))
    if ST.get('step') != step:
        log('STEP ' + step.label)
        ST.update(step=step, attempts=0, act_at=0, progress_at=now)
    if position != ST.get('position'):
        ST.update(position=position, progress_at=now)
    if now - ST['progress_at'] > 35:
        finish('no progress on map %d at %s while %s' %
               (map_id, location_to_axis(pcs[0].location), step.label))
    elif map_id not in step.maps:
        finish('unexpected map %d while %s' % (map_id, step.label))
    else:
        act(step, pcs[0], now)
    return 0


def wait_for_main_menu(slot):
    if ui.obtain_widget(ui.WID_IDEN.NEW_GAME):
        log('Main menu detected')
        return 1
    if time.time() - ST['started'] > 30:
        widgets = [ui.aui.TWidget(id) for id in ui.aui.get_active_windows()]
        windows = ', '.join('%s (%s)' % (widget.name, widget.source_uri) for widget in widgets)
        finish('main menu did not become available. Active windows: ' + windows)
    return 0


def setup_playtester(player):
    global LOG
    LOG = os.environ.get('DHAP_LOG') or os.environ.get('IWDAP_LOG')
    ST.clear()
    ST.update(player=player, started=time.time(), index=0, move_mouse=ui.move_mouse)
    if os.environ.get('AUTOPLAYER_SCENARIO') == 'dancing_hut_chapter':
        import dancing_hut_campaign
        chapter_route = ROUTE[:-1] + dancing_hut_campaign.REINFORCEMENTS + ROUTE[-1:] + dancing_hut_campaign.ROUTE
        ST.update(campaign=dancing_hut_campaign, route=chapter_route)
    # Keep cursor operations in the game's message queue.
    ui.move_mouse = lambda x, y: game.mouse_move_to((int(x), int(y)), 1)
    if os.environ.get('DHAP_IN_PROCESS') == '1':
        ST['game_is_focused'] = ui.tpgui.game_is_focused
        ui.tpgui.game_is_focused = lambda: True

    game_stage = GoalState('play', tick, ('play', 200), ('play', 200))
    if os.environ.get('TP_AUTOLOAD'):
        stages = [GoalStateStart(tick, ('play', 300), ('play', 300)), game_stage]
    else:
        from iwd_ch1_driver import pick_targos_role
        alignment = ui.WID_IDEN.TRUE_NEUTRAL_BTN_WID_ID[:-1] + [1]  # Neutral Good
        add = [GoalState('', gs_create_and_push_scheme, ('', 300), params={
            'param1': 'pick_%d_%s' % (i, role), 'param2': (pick_targos_role, (role, name, log, finish))
        }) for i, (role, name) in enumerate(PARTY)]
        stages = [
            GoalStateStart(wait_for_main_menu, ('new_game', 600), ('start', 400)),
            GoalState('new_game', gs_press_widget, ('difficulty', 600), (), {'param1': ui.WID_IDEN.NEW_GAME}),
            GoalState('difficulty', gs_press_widget, ('alignment', 600), (), {'param1': ui.WID_IDEN.NORMAL_DIFF}),
            GoalState('alignment', gs_press_widget, ('align_ok', 600), (), {'param1': alignment}),
            GoalState('align_ok', gs_press_widget, ('add_pcs', 600), (), {'param1': ui.WID_IDEN.PARTY_ALIGNMENT_ACCEPT_BTN}),
        ] + GoalState.from_sequence('add_pcs', add, ('begin', 500), ('begin', 500)) + [
            GoalState('begin', gs_press_widget, ('play', 1500), (), {'param1': ui.WID_IDEN.CHAR_POOL_BEGIN_ADVENTURE}),
            game_stage,
        ]
    scheme = ControlScheme()
    scheme.__set_stages__(stages)
    player.add_scheme(scheme, 'dancing_hut')
    player.set_dialog_handler(handle_dialogue)
    player.set_combat_handler(lambda slot: None)
    player.__exc_hook__ = lambda trace: finish(trace)
    player.push_scheme('dancing_hut')
    log('Dancing Hut Beta 0.98 / ' + ('Chapter 1' if ST.get('campaign') else 'Opening to Bone Castle'))
    player.execute()
