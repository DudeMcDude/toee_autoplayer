"""Continue Dancing Hut Beta 0.98 from Bone Castle through the Chapter 1 ending."""
from toee import *
from utilities import location_to_axis

import dancing_hut_driver as dh


INTERIOR, DUNGEON = 5004, 5005
SCROLLS = (9090, 9092, 9093)
CURES = (spell_cure_minor_wounds, spell_cure_light_wounds,
         spell_cure_moderate_wounds, spell_cure_serious_wounds, spell_cure_critical_wounds)
SALAZAAR_SCRIPTS = (802, 1802)
ARGENT_SCEPTER = 4236
EXITS = {119: INTERIOR, 122: DUNGEON, 185: dh.KEEP_OUTSIDE[0],
         889: dh.HALL, 354: dh.DORMITORIES, 356: dh.HALL}


def step(label, map_id, action, target=None, tile=None):
    return dh.Step(label, (map_id,), 'chapter_' + action, target, tile)


def path(map_id, label, points):
    return tuple(step('%s at %s' % (label, point), map_id, 'walk', tile=point)
                 for point in points)


ENTER = step('Enter Bone Castle', dh.CASTLE, 'exit', 119, (460, 445))
RECRUITS = (step('Recruit Darryk the warrior', dh.HALL, 'recruit', 508, (472, 469)),
            step('Recruit Darryk the adept', dh.HALL, 'recruit', 509, (472, 471)))
REINFORCEMENTS = (
    step('Head back to the main hall for reinforcements', dh.DORMITORIES, 'enlist', 356, (489, 488)),
) + RECRUITS + (
    step('Return to Franciscus before departing', dh.HALL, 'exit', 354, (484, 489)),
)
STAIRS = step('Descend to the dungeon', INTERIOR, 'exit', 122, (490, 471))
CLUE = step('Ask Mithridates about the castle', DUNGEON, 'clue', 420, (440, 408))
SUPPLIES = step('Recover the healing scrolls', DUNGEON, 'supplies', tile=(487, 537))
WRAITH = step('Resolve the castle encounter', DUNGEON, 'wraith', 655, (474, 548))
ESCAPE = step('Leave the dungeon through the cave', DUNGEON, 'exit', 185, (529, 567))
RETURN = step('Return to Loche Skye', dh.KEEP_OUTSIDE[0], 'exit', 889, (479, 487))
DORMS = step('Return to the dormitories', dh.HALL, 'exit', 354, (484, 489))
REPORT = step('Report to Franciscus', dh.DORMITORIES, 'report', 412, (490, 512))
HALL = step('Return to the main hall', dh.DORMITORIES, 'exit', 356, (489, 488))
DINNER = step('Attend the meeting with Godfrey', dh.HALL, 'dinner', 510, (498, 487))
DAWN = step('Wait until morning', dh.HALL, 'dawn')
ENDING = step('Meet the travelers in the main hall', dh.HALL, 'ending', 510, (498, 487))

APPROACH = path(dh.CASTLE, 'Approach the castle from the west',
                ((462, 539), (446, 535), (443, 519), (445, 504), (456, 496),
                 (470, 480), (470, 462), (470, 450)))
OUTBOUND = path(DUNGEON, 'Traverse the dungeon',
                ((423, 419), (415, 437), (418, 449), (425, 465), (432, 482),
                 (450, 492), (471, 494), (485, 493), (505, 502), (520, 510),
                 (526, 526), (529, 533), (516, 547), (513, 548), (493, 542), (487, 537)))
INBOUND = path(DUNGEON, 'Head to the cave exit', ((495, 548), (513, 548), (532, 555)))
ROUTE = (APPROACH + (ENTER, STAIRS, CLUE) + OUTBOUND + (SUPPLIES, WRAITH) + INBOUND +
         (ESCAPE, RETURN, DORMS, REPORT, HALL, DINNER, DAWN, ENDING))

DIALOGUE = {
    317: {20: 25, 25: 0, 30: 0},
    420: {1: 10, 10: 20, 20: 30, 30: 40, 40: 60, 60: 70, 70: 73,
          73: 75, 75: 80, 80: 90, 90: 100, 100: 0, 200: 205, 205: 0},
    426: {1: 10, 10: 20, 20: 25, 25: 30, 30: 0},
    508: {1: 10, 10: 20, 20: 30, 30: 0, 40: 30},
    509: {1: 10, 10: 20, 20: 30, 30: 0, 40: 30},
    655: {1: 5, 5: 10, 10: 40, 40: 0, 100: 105, 105: 110, 110: 120, 120: 122,
          122: 125, 125: 130, 130: 132, 132: 135, 135: 137, 137: 140, 140: 0},
    656: {20: 50, 50: 55, 55: 60, 60: 70, 70: 75, 75: 85, 85: 90, 90: 100,
          100: 105, 105: 110, 110: 115, 115: 120, 120: 125, 125: 0,
          130: 135, 135: 140, 140: 0, 200: (210, 220), 210: 215, 215: 220, 220: 0},
}
SALAZAAR = {100: 110, 110: 120, 120: 130, 130: 140, 140: 150, 150: 160, 160: 170,
            170: 175, 175: 180, 180: 185, 185: 190, 190: 195, 195: 0}
FRANCISCUS = {1: 500, 500: 510, 510: 520, 520: 540, 540: 550, 550: (580, 570),
             570: 574, 574: 577, 577: 0, 580: 585, 585: 590, 590: 600, 600: 605, 605: 550,
             700: 0, 710: 715, 715: 720, 720: 722, 722: 725, 725: 730,
             730: 735, 735: 740, 740: 745, 745: 750, 750: 0}
MAITRE = {100: 150, 150: (160, 165, 180), 160: 170, 165: 170, 170: 200, 180: 200,
          200: 210, 210: 220, 220: 0, 250: 0}
EFFECTS = {(426, 30): 'npc.attack', (655, 40): 'npc.attack', (655, 137): 'create_item_in_inventory',
           (412, 590): 'party_transfer_to', (510, 220): 'switch_to_godfrey',
           (510, 250): 'switch_to_godfrey', (656, 125): 'switch_to_franciscus',
           (412, 700): 'switch_to_godfrey', (656, 140): 'switch_to_franciscus',
           (656, 220): 'switch_to_salazaar'}


def knows(sid):
    return sid in DIALOGUE or sid in SALAZAAR_SCRIPTS or sid in (412, 510)


def reply_plan(sid, line, action, opening):
    choices = DIALOGUE.get(sid, opening)
    if sid in SALAZAAR_SCRIPTS:
        choices = SALAZAAR
    if action and action.startswith('chapter_'):
        if sid == 412:
            choices = FRANCISCUS
        elif sid == 510:
            choices = MAITRE.copy()
            if action == 'chapter_ending':
                choices[100] = 250
    return choices, EFFECTS.get((sid, line))


def spells_for(actor):
    return [spell for spell in actor.spells_memorized if spell.spell_enum in CURES
            and not spell.is_used_up() and actor.can_cast_spell(spell)]


def healer():
    def priority(member):
        distance = dh.distance(location_to_axis(member.location), SUPPLIES.tile)
        return (member.stat_level_get(stat_level_cleric) > 0,
                sum(bool(member.item_find_by_proto(proto)) for proto in SCROLLS),
                distance <= 16, member.stat_level_get(stat_level_cleric), -distance)

    return max((member for member in game.party if not member.is_unconscious()),
               key=priority)


def recruited(script_id):
    return game.leader.follower_atmax() or any(member.scripts[san_dialog] == script_id
                                               for member in game.party)


def passed(current, map_id):
    action = current.action
    if action == 'chapter_exit':
        return map_id == EXITS[current.target]
    if action == 'chapter_walk':
        return dh.distance(location_to_axis(dh.party_pcs()[0].location), current.tile) <= 4
    if action == 'chapter_clue':
        return bool(game.global_flags[512])
    if action == 'chapter_enlist':
        return map_id == dh.HALL or all(recruited(recruit.target) for recruit in RECRUITS)
    if action == 'chapter_recruit':
        return recruited(current.target)
    if action == 'chapter_supplies':
        return all(healer().item_find_by_proto(proto) for proto in SCROLLS)
    if action == 'chapter_wraith':
        return dh.quest(118, qs_completed) and bool(game.global_flags[511])
    if action == 'chapter_report':
        return bool(game.global_flags[930] or game.global_flags[931])
    if action == 'chapter_dinner':
        return bool(game.global_flags[931])
    if action == 'chapter_dawn':
        return bool(game.is_daytime())
    return bool(dh.ST.get('ending_seen'))


def resume_index(map_id):
    accepted = dh.quest(118, qs_accepted, qs_completed)
    complete = dh.quest(118, qs_completed)
    if not accepted:
        return None
    if map_id == dh.CASTLE:
        current = nearest_waypoint(APPROACH + (ENTER,))
    elif map_id == INTERIOR:
        current = STAIRS
    elif map_id == DUNGEON:
        if complete:
            current = nearest_waypoint(INBOUND + (ESCAPE,))
        elif game.global_vars[926] or passed(SUPPLIES, map_id):
            current = WRAITH
        elif game.global_flags[512]:
            current = nearest_waypoint(OUTBOUND)
        else:
            current = CLUE
    elif complete and map_id == dh.KEEP_OUTSIDE[0]:
        current = RETURN
    elif complete and map_id == dh.DORMITORIES:
        current = HALL if passed(REPORT, map_id) else REPORT
    elif complete and map_id == dh.HALL:
        current = DAWN if game.global_flags[931] else DINNER if game.global_flags[930] else DORMS
    else:
        return None
    return dh.ST['route'].index(current)


def nearest_waypoint(points):
    x, y = location_to_axis(dh.party_pcs()[0].location)
    return min(points, key=lambda p: (p.tile[0] - x) ** 2 + (p.tile[1] - y) ** 2)


def open_route_door(actor, tile, now):
    """Open an unlocked portal between the party and the current dungeon waypoint."""
    import debug
    if actor.is_performing() or now < dh.ST.get('act_at', 0) or debug.pathto(actor, *tile):
        return False
    x, y = location_to_axis(actor.location)
    dx, dy = tile[0] - x, tile[1] - y
    length = dx * dx + dy * dy
    for door in game.obj_list_range(actor.location, 24, OLC_PORTAL):
        if door.portal_flags_get() & (OPF_OPEN | OPF_LOCKED):
            continue
        px, py = location_to_axis(door.location)
        vx, vy = px - x, py - y
        if not (-2 <= vx * dx + vy * dy <= length + 3) or (vx * dy - vy * dx) ** 2 > 16 * length:
            continue
        if actor.distance_to(door) > 8:
            continue
        dh.log('ACT Open dungeon door at %s' % ((px, py),))
        dh.ST['act_at'] = now + 1
        actor.anim_goal_use_object(door)
        return True
    return False


def gather_scrolls(actor, now):
    priest = healer()
    needed, scroll = next_scroll(priest)
    if needed is None:
        return
    tile = location_to_axis(scroll.location) if scroll else SUPPLIES.tile
    if not dh.walk(priest, tile, 1, now) or priest.is_performing() or now < dh.ST.get('act_at', 0):
        return
    if scroll:
        dh.ST['act_at'] = now + 1
        take_scroll(priest, needed, scroll)
    elif dh.distance(location_to_axis(actor.location), tile) <= 5:
        dh.finish('could not find the quest scroll with prototype %d' % needed)


def next_scroll(priest):
    needed = next((proto for proto in SCROLLS if not priest.item_find_by_proto(proto)), None)
    return needed, dh.nearby(priest, OLC_ITEMS, lambda item: item.proto == needed) if needed else None


def take_scroll(priest, proto, scroll):
    dh.log('ACT %s picks up scroll %d' % (priest.description, proto))
    priest.action_perform(D20A_PICKUP_OBJECT, scroll, scroll.location)


def cast_cure(actor, target, attempted):
    if actor.distance_to(target) > 5 or not actor.has_los(target):
        return False
    prepared = next((spell for spell in spells_for(actor) if spell.spell_enum not in attempted), None)
    if prepared:
        attempted.add(prepared.spell_enum)
        dh.log('ACT %s casts %s on the wraith' % (actor.description, prepared))
        actor.cast_spell(prepared.spell_enum, target)
        return True
    for proto in SCROLLS:
        scroll = actor.item_find_by_proto(proto)
        if scroll and proto not in attempted:
            attempted.add(proto)
            result = actor.use_item(scroll, target)
            dh.log('ACT %s uses scroll %d on the wraith, result %s' % (actor.description, proto, result))
            if not result:
                return True
    return False


def turn_undead(actor):
    import tpactions
    if actor.stat_level_get(stat_level_cleric) < 1 and actor.stat_level_get(stat_level_paladin) < 4:
        return False
    stamp = (game.combat_turn, actor.id)
    hourglass = tpactions.get_cur_seq().tb_status.hourglass_state
    if dh.ST.get('turn_undead_at') == stamp or hourglass < 2:
        return False
    enemies = [npc for npc in game.obj_list_range(actor.location, 60, OLC_NPC)
               if npc.is_category_type(mc_type_undead) and not is_wraith(npc)
               and npc.is_active_combatant() and not npc.is_friendly(actor)
               and not npc.is_unconscious() and not npc.d20_query(Q_Turned)
               and actor.has_los(npc)]
    if len(enemies) < 2 and not any(npc.is_category_subtype(mc_subtype_incorporeal) for npc in enemies):
        return False
    dh.ST['turn_undead_at'] = stamp
    tpactions.cur_seq_reset(actor)
    try:
        actor.action_perform(D20A_TURN_UNDEAD, OBJ_HANDLE_NULL, 0)
    except RuntimeError:
        tpactions.cur_seq_reset(actor)
        return False
    if actor.is_performing() or tpactions.get_cur_seq().tb_status.hourglass_state < hourglass:
        dh.log('COMBAT %s turns undead' % actor.description)
        return True
    return False


def is_wraith(npc):
    return npc.proto == 14849 and npc.scripts[san_dialog] == 655 and not npc.is_unconscious()


def combat_target(npc):
    return not is_wraith(npc)


def advance_during_combat(actor):
    """Keep moving when distant enemies hold the party in initiative."""
    import chapter_combat
    import tpactions
    from iwd_ch1_driver import local_waypoint
    from new_game_controller import chapter_combat_move

    current = dh.current_step()
    while current and (current.action == 'chapter_exit' or actor.map in current.maps and
                       current.action in ('chapter_walk', 'chapter_supplies')) and passed(current, actor.map):
        dh.log('COMPLETE ' + current.label)
        dh.ST['index'] += 1
        current = dh.current_step()
    if not current or actor.map not in current.maps:
        return False
    if current.action not in ('chapter_walk', 'chapter_exit', 'chapter_supplies', 'chapter_wraith'):
        return False
    status = tpactions.get_cur_seq().tb_status
    if status.hourglass_state < 1:
        return False
    weapon = actor.item_worn_at(item_wear_weapon_primary)
    if weapon and weapon.proto == ARGENT_SCEPTER and dh.nearby(
            actor, OLC_NPC, lambda npc: npc.is_active_combatant()
            and not npc.is_friendly(actor) and not npc.is_unconscious()
            and npc.is_category_subtype(mc_subtype_incorporeal) and actor.distance_to(npc) <= 35):
        return False
    destination = current.tile
    if current.action == 'chapter_supplies':
        if actor != healer():
            return False
        needed, scroll = next_scroll(actor)
        if not scroll:
            return False
        destination = location_to_axis(scroll.location)
        if actor.distance_to(scroll) <= 5:
            tpactions.cur_seq_reset(actor)
            try:
                take_scroll(actor, needed, scroll)
                return True
            except RuntimeError:
                tpactions.cur_seq_reset(actor)
                return False
    threats = chapter_combat.opponents(actor)
    distance = dh.distance(location_to_axis(actor.location), destination)
    if distance <= (1 if current.action == 'chapter_supplies' else 4):
        if actor != dh.party_pcs()[0] or any(enemy.can_melee(actor) for enemy in threats):
            return False
        if current.action == 'chapter_exit' and dh.ST.get('combat_exit') != current:
            exit_object = dh.nearby(actor, OLC_SCENERY, lambda obj:
                                    obj.obj_get_int(obj_f_scenery_teleport_to) == current.target)
            if exit_object and actor.distance_to(exit_object) <= 8:
                dh.ST['combat_exit'] = current
                actor.anim_goal_use_object(exit_object)
                dh.log('COMBAT %s tries the exit' % actor.description)
                return True
        if current.action == 'chapter_wraith' and not dh.ST.get('wraith_started'):
            target = dh.nearby(actor, OLC_NPC, is_wraith)
            if target and actor.has_los(target) and actor.distance_to(target) <= 16:
                dh.ST['wraith_started'] = True
                dh.log('ACT Speak to the wraith')
                target.object_script_execute(actor, san_dialog)
                return True
        return False
    tpactions.cur_seq_reset(actor)
    if chapter_combat_move(actor, destination, status.hourglass_state, threats, None, local_waypoint):
        dh.log('COMBAT %s advances toward %s' % (actor.description, destination))
        return True
    if chapter_combat.five_foot_step(actor, threats, status):
        dh.log('COMBAT %s takes a five-foot step out of reach' % actor.description)
        return True
    return False


def combat_turn(actor):
    import chapter_combat
    import tpactions
    from iwd_ch1_driver import local_waypoint
    from new_game_controller import chapter_combat_move
    if not actor or actor not in game.party or actor.map not in (dh.CASTLE, INTERIOR, DUNGEON):
        return False
    if actor.is_performing():
        return True
    target = dh.nearby(actor, OLC_NPC, is_wraith) if actor.map == DUNGEON else None
    if not target or not target.is_active_combatant() or dh.quest(118, qs_completed):
        return turn_undead(actor) or advance_during_combat(actor)
    stamp = (game.combat_turn, actor.id)
    if dh.ST.get('wraith_turn') != stamp:
        dh.ST.update(wraith_turn=stamp, wraith_attempts=set())
    attempted = dh.ST['wraith_attempts']
    status = tpactions.get_cur_seq().tb_status
    tpactions.cur_seq_reset(actor)
    if (game.global_vars[926] >= 3 and actor.type == obj_t_pc and
            actor.has_los(target) and actor.distance_to(target) <= 18):
        if 'dialogue' not in attempted:
            attempted.add('dialogue')
            dh.log('ACT Reopen the castle dialogue after three cures')
            target.object_script_execute(actor, san_dialog)
            return True
    elif actor == healer() or spells_for(actor):
        if status.hourglass_state >= 2 and cast_cure(actor, target, attempted):
            return True
        if 'step' not in attempted:
            attempted.add('step')
            if chapter_combat.five_foot_step(actor, chapter_combat.opponents(actor), status, target):
                return True
        if status.hourglass_state >= 1 and chapter_combat_move(
                actor, location_to_axis(target.location), status.hourglass_state,
                chapter_log=dh.log, waypoint=local_waypoint):
            return True
    else:
        return False
    dh.ready_or_end_turn()
    return True


def act(current, actor, now):
    action = current.action
    if actor.map == DUNGEON and not dh.ST.get('scepter_checked'):
        dh.ST['scepter_checked'] = True
        equip_scepter()
    if action == 'chapter_walk':
        if actor.map != DUNGEON or not open_route_door(actor, current.tile, now):
            dh.walk(actor, current.tile, 4, now)
    elif action == 'chapter_supplies':
        gather_scrolls(actor, now)
    elif action == 'chapter_dawn':
        if now >= dh.ST.get('act_at', 0):
            dh.ST['act_at'] = now + 0.4
            game.gametime_add(60 * 60 * 1000)
    elif action in ('chapter_exit', 'chapter_enlist'):
        dh.act(current._replace(action='exit'), actor, now)
    else:
        dh.act(current._replace(action='talk'), actor, now)


def equip_scepter():
    for holder in game.party:
        scepter = holder.item_find_by_proto(ARGENT_SCEPTER)
        if not scepter:
            continue
        wielder = max((member for member in game.party if not member.is_unconscious()),
                      key=lambda member: (member.stat_level_get(stat_strength),
                                          member.stat_level_get(stat_hp_current)))
        if wielder != holder:
            holder.item_transfer_to_by_proto(wielder, ARGENT_SCEPTER)
        scepter = wielder.item_find_by_proto(ARGENT_SCEPTER)
        if scepter:
            wielder.item_wield(scepter, item_wear_weapon_primary)
            if wielder.item_worn_at(item_wear_weapon_primary) == scepter:
                dh.log('ACT %s equips the Argent Scepter' % wielder.description)
        break


def save_ending():
    if game.savegame('DancingHut_Chapter1', 'Dancing Hut - Chapter 1 complete'):
        dh.finish('completed the Chapter 1 main story and saved DancingHut_Chapter1', True)
    else:
        dh.finish('completed the Chapter 1 main story, but the checkpoint could not be saved')
