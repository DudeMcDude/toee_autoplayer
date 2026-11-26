"""Threat-aware movement for the chapter controller."""
import math
from toee import *
from utilities import location_from_axis, location_to_axis
import debug


def opponents(actor):
    """Use the engine's AoO eligibility, including remaining attacks this round."""
    return [enemy for enemy in game.obj_list_range(actor.location, 100, OLC_CRITTERS)
            if enemy != actor and enemy not in game.party and not enemy.is_friendly(actor)
            and enemy.is_active_combatant() and not enemy.is_unconscious()
            and not enemy.object_flags_get() & (OF_OFF | OF_DONTDRAW | OF_CLICK_THROUGH)
            and enemy.d20_query_with_object(Q_AOOPossible, actor)
            and enemy.d20_query_with_object(Q_AOOWillTake, actor)]


def reach(actor):
    # Mirror the engine's natural reach and polearm allowance conservatively.
    size = actor.stat_level_get(stat_size)
    natural = max(actor.obj_get_int(obj_f_critter_reach), {6: 10, 7: 15, 8: 20, 9: 30}.get(size, 5))
    weapon = actor.item_worn_at(item_wear_weapon_primary)
    extra = 0
    if weapon and weapon.obj_get_int(obj_f_weapon_type) in (wt_glaive, wt_guisarme, wt_longspear, wt_ranseur, wt_spike_chain):
        extra = 5
    return natural + extra - min(2.0, actor.radius / 12.0)


def threatens_at(enemy, actor, point):
    return enemy.distance_to(location_from_axis(*point)) <= reach(enemy) + actor.radius / 12.0


def movement_threats(actor, point, enemies):
    """Estimate exposure along a short waypoint segment before committing a move.

    Python exposes reach queries at the current position, but no native path/AoO
    preview. Include current threats and sample the proposed segment conservatively.
    """
    x, y = location_to_axis(actor.location)
    dx, dy = point[0] - x, point[1] - y
    count = max(1, int(math.ceil(math.hypot(dx, dy))))
    samples = [(int(round(x + dx * i / float(count))),
                int(round(y + dy * i / float(count)))) for i in range(count)]
    return [enemy for enemy in enemies if enemy.can_melee(actor)
            or any(threatens_at(enemy, actor, sample) for sample in samples)]


def five_foot_step(actor, enemies, tb_status, target=None):
    """Escape a threat or close on a target without provoking."""
    if tb_status.flags & (TBSF_Movement | TBSF_1) or actor.d20_query(Q_Prone):
        return False
    x, y = location_to_axis(actor.location)
    current = sum(bool(enemy.can_melee(actor)) for enemy in enemies)
    if target is None and not current:
        return False
    if target is not None and actor.can_melee(target):
        return False
    candidates = []
    for dx in range(-2, 3):
        for dy in range(-2, 3):
            if not 0 < dx * dx + dy * dy <= 4:
                continue
            point = (x + dx, y + dy)
            threats = sum(threatens_at(enemy, actor, point) for enemy in enemies)
            if target is None:
                if threats >= current:
                    continue
                rank = (threats, dx * dx + dy * dy)
            else:
                distance = target.distance_to(location_from_axis(*point))
                in_reach = distance <= reach(actor) + actor.radius / 12.0
                if not in_reach and (not current or distance >= target.distance_to(actor.location)):
                    continue
                rank = (not in_reach, threats, distance)
            candidates.append((rank, point))
    for rank, point in sorted(candidates):
        if not debug.pathto(actor, *point):
            continue
        try:
            if actor.action_perform(D20A_5FOOTSTEP, OBJ_HANDLE_NULL, location_from_axis(*point)):
                return True
        except RuntimeError:
            # A failed native sequence must not contaminate the next candidate.
            import tpactions
            tpactions.cur_seq_reset(actor)
            return False
    return False


def allow_move(actor, point, enemies, log=None, rescue=False, engage=None):
    risks = movement_threats(actor, point, enemies)
    closes = engage is not None and engage in risks and (
        engage.distance_to(location_from_axis(*point)) < engage.distance_to(actor.location))
    justified = (rescue or closes) and len(risks) == 1 and actor.stat_level_get(stat_hp_current) > max(
        20, actor.stat_level_get(stat_hp_max) * 0.6)
    if risks and not justified:
        if log:
            log('COMBAT %s holds position instead of risking movement AoOs from %s' %
                (actor, ', '.join(str(enemy) for enemy in risks)))
        return False
    if risks and log:
        log('COMBAT %s risks one movement AoO to reach %s' % (actor, engage or 'a dying ally'))
    return True
