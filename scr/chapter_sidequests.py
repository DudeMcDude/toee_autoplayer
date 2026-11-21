"""Opening-town side quests. Every objective reads the converted game's own state."""
from toee import *
from utilities import location_from_axis, location_to_axis


def driver():
    import iwd_ch1_driver
    return iwd_ch1_driver


def has(item):
    import ie_itemrt
    return any(ie_itemrt.find(pc, item) for pc in game.party)


def flag(name, value):
    return lambda: driver().V(name) >= value


def journal(entry):
    import ie_journal
    number = ie_journal.JOURNAL.get(entry)
    return bool(number and game.quests[number[0]].state >= 2)


OUTCOMES = {
    'jhonen': lambda: driver().V('Siren_Quest') == 4 and has('misc36') and not has('jhoswd1'),
    'old_jed': flag('Drunk_Quest', 3),
    'grisella': flag('Grisella_Quest', 2),
    'apsel': flag('Apsel_Quest', 3),
    'damien': flag('Damien_Quest', 2),
    'gaspar': flag('Gaspar_Quest', 3),
    'reig': lambda: driver().V('Reig_Quest') == 2 and journal(1477),
    'hedron': lambda: driver().V('Hedron_Quest') == 4 and journal(2569),
    'garradun': lambda: driver().V('Garradun_Quest') >= 3 and driver().V('SPRITE_IS_DEADDoppelganger') > 0,
    'firtha_cat': lambda: journal(1346) and driver().V('Anson_Cat') == 3,
    'guthewulfe': lambda: driver().V('Guthewulfe_Game') == 2 and journal(7425),
    'niles': lambda: journal(10634),
    'caulder': lambda: driver().V('Catapult_Quest') == 3 and journal(14822),
    'brogan': flag('Iron_Collar_Quest', 3),
    'training': lambda: journal(7239),
    'recruits': flag('Recruit_Inspired ', 1),
    'archery': lambda: driver().V('Gable_Quest') == 6 and journal(12738),
    'tabard': flag('Tabard_Quest', 1),
    'veira': lambda: driver().V('Veira_Happy') == 1 and driver().V('Veira_Quest_End') == 1,
    'tears': flag('Elytharra_Tear', 1),
    'potion': flag('Potion_Quest', 2),
    'phaen': lambda: driver().V('Expose_Phaen_Quest') == 2 and driver().V('SPRITE_IS_DEADPhaen_of_the_Rags') > 0,
}


def dialogue(actor, area, goal, check, speaker=None):
    if speaker is None:
        abilities = {'10guthe': stat_constitution, '12drill': stat_charisma}
        skills = {'12caulde': skill_diplomacy, '12tabard': skill_bluff}
        if actor in abilities:
            speaker = lambda: max((p for p in game.party if not p.is_unconscious()),
                                  key=lambda p: p.stat_level_get(abilities[actor]))
        elif actor in skills:
            speaker = lambda: max((p for p in game.party if not p.is_unconscious()),
                                  key=lambda p: p.skill_level_get(skills[actor]))
        elif actor == '12weapon':
            speaker = lambda: max((p for p in game.party if not p.is_unconscious()),
                                  key=lambda p: p.stat_level_get(stat_level_fighter))
    return lambda st: driver().talk_step(st, actor, area, goal, check, speaker)


def quest_flag(actor, area, name, value):
    return dialogue(actor, area, r'SetGlobal\(c, "%s", "GLOBAL", %d\)' % (name, value), flag(name, value))


def arrive(st, area):
    d = driver()
    if d.get_current_map() == d.area_map(area):
        return True
    d.walk_to_area(st, area)
    return False


def approach(st, dest, radius=4):
    d = driver()
    return d.walk_party(st, dest, radius)


def recover_drop(st, area, ident, res):
    """Find the quest item on its fallen owner, in a loot pile, or on the ground."""
    import ie_itemrt
    d = driver()
    party = [pc for pc in game.party if not pc.is_unconscious()]
    if not party or d.get_current_map() != d.area_map(area):
        return False
    if has(res):
        return True
    if not hasattr(st, 'drop_guids'):
        try:
            data = __import__('ie_bake_' + area.lower()).OBJS
        except ImportError:
            data = {}
        st.drop_guids = [g for g,o in data.items() if o.get('k') == 'npc' and
                         ident in (o['spec'].get('ident'),o['spec'].get('resref'))]
    sources = []
    for guid in st.drop_guids:
        body = game.get_obj_by_id(guid)
        if body and body != OBJ_HANDLE_NULL and not body.object_flags_get() & OF_OFF and body.is_unconscious():
            item = ie_itemrt.find(body,res)
            if item:
                sources.append((body,item))
    if not sources:
        entry = ie_itemrt.entry(res)
        for obj in game.obj_list_range(party[0].location, 320, OLC_ALL):
            if obj.object_flags_get() & OF_OFF:
                continue
            if entry and obj.proto == entry['p'] and (not entry.get('n') or obj.obj_get_int(ie_itemrt._field('obj_f_description')) == entry['n']):
                sources.append((obj,obj))
            elif obj.type == obj_t_container:
                item = ie_itemrt.find(obj,res)
                if item:
                    sources.append((obj,item))
    if not sources:
        return False
    # A nearer party member can be behind a wall or on the far side of a corpse.
    # Try everyone who can already see and reach the item before moving the party.
    choices = [(pc, source, item) for source, item in sources for pc in party]
    choices.sort(key=lambda choice: choice[0].distance_to(choice[1]))
    for pc, source, item in choices:
        if pc.distance_to(source) <= 9 and pc.has_los(source):
            getattr(ie_itemrt, 'transfer', lambda holder, obj: holder.item_get(obj))(pc, item)
            if has(res):
                d.log('LOOT %s recovered by %s from %s' % (res, pc, source))
                return True
    pc, source, item = next((choice for choice in choices if choice[0].has_los(choice[1])), choices[0])
    d.walk_party(st, location_to_axis(source.location), 1, pc)
    return True


def encounter(area, ident, ie_point, check, loot=None, archery=False):
    """Approach a placed quest opponent and recover a real item from its body."""
    def run(st):
        import ie_itemrt, ie_runtime
        d = driver()
        if check():
            d.ST.pop('practice', None)
            return True
        training = ident in ('12kegmel','12kegarc_ar1200')
        if not training and not getattr(st, 'prepared', False):
            if d.get_current_map() != d.area_map(area) and d.recover_after_battle(st, prepare=True):
                return False
            import time
            from controller_callbacks_common import obj_can_cast
            if time.time() < getattr(st, 'armor_wait', 0):
                return False
            if not hasattr(st, 'armor_wait'):
                for caster in game.party:
                    if caster.is_unconscious() or caster.d20_query_has_spell_condition(sp_Mage_Armor):
                        continue
                    if any(s.spell_enum == spell_mage_armor and obj_can_cast(caster, s.spell_enum, s.spell_class, s.spell_level)
                           for s in caster.spells_memorized):
                        caster.cast_spell(spell_mage_armor, caster)
                        d.log('OPENING %s casts Mage Armor before approaching %s' % (caster, ident))
                        st.armor_wait = time.time() + 3
                        return False
            st.prepared = True
        if not arrive(st, area) or st.n % 10 != 1:
            return False
        if loot and recover_drop(st,area,ident,loot):
            return check()
        raw_area = area[-6:]
        tile = ie_runtime.ie_to_tile(raw_area, *ie_point)
        if not hasattr(st, 'sid'):
            st.sid = d.npc_script(ident, raw_area)[0]
            if st.sid is None:
                return d.fail('no script for ' + ident)
            st.ids = {st.sid}
            if ident == 'ehbeetle':
                placed = __import__('ie_creatures_' + raw_area.lower()).CREATURES
                st.ids.update(c['script_id'] for c in placed if c.get('resref') == ident)
        party = [pc for pc in game.party if not pc.is_unconscious()]
        if d.rally_before_fight(st,party[0]):
            return False
        st.close_formation = True
        actors = [o for o in game.obj_list_range(party[0].location, 320, OLC_NPC)
                  if (o.scripts[san_dialog] in st.ids or o.scripts[san_dying] in st.ids)
                  and not o.object_flags_get() & OF_OFF]
        if st.n % 100 == 1:
            d.log('ENCOUNTER %s at %s targets %s' % (ident, location_to_axis(party[0].location),
                  [(location_to_axis(o.location), o.stat_level_get(stat_hp_current)) for o in actors]))
        if actors:
            target = min(actors, key=lambda o: (o.is_unconscious(), party[0].distance_to(o)))
            tile = location_to_axis(target.location)
        if ident not in ('12kegmel','12kegarc_ar1200') and not (actors and target.is_unconscious()):
            # Engage the nearest guards from the party's formation before closing on the quest target.
            guards = [o for o in game.obj_list_range(party[0].location, 75, OLC_NPC)
                      if d.targos_enemy(o) and any(pc.has_los(o) for pc in party)]
            if guards:
                from controller_callbacks_common import obj_can_cast
                from new_game_controller import sleep_target
                if st.n >= getattr(st, 'next_opener', 0):
                    for caster in party:
                        if not any(s.spell_enum == spell_sleep and obj_can_cast(caster,s.spell_enum,s.spell_class,s.spell_level)
                                   for s in caster.spells_memorized):
                            continue
                        victim = sleep_target(caster,guards)
                        if victim and caster.distance_to(victim) <= 60:
                            d.log('OPENING %s casts Sleep on %s' % (caster,victim))
                            caster.cast_spell(spell_sleep,victim)
                            st.next_opener = st.n + 50
                            return False
                target = min(guards,key=lambda o: party[0].distance_to(o))
                actors, tile = [target],location_to_axis(target.location)
        if not actors:
            approach(st, tile, 3)
            return False
        if loot and target.is_unconscious():
            looter = min(party, key=lambda pc: pc.distance_to(target))
            if not d.walk_party(st, tile, 3, looter):
                return False
            item = ie_itemrt.find(target, loot)
            if item:
                looter.item_get(item)
                d.log('LOOT %s from %s' % (loot, ident))
        elif not target.is_unconscious():
            if ident in ('12kegmel', '12kegarc_ar1200'):
                d.ST['practice'] = (target.id, archery)
            attackers = [pc for pc in party if not pc.is_performing() and pc.has_los(target)]
            ranged = [pc for pc in attackers if pc.item_worn_at(item_wear_weapon_primary) and
                      pc.item_worn_at(item_wear_weapon_primary).obj_get_int(obj_f_weapon_flags) & OWF_RANGED_WEAPON
                      and pc.distance_to(target) <= 60]
            melee = [pc for pc in attackers if pc not in ranged and pc.can_melee(target)]
            if ident == '12kegmel':
                attackers = melee
            else:
                attackers = ranged if archery else melee + ranged
            if not attackers:
                approach(st, tile, 12 if archery else 2)
                return False
            pc = min(attackers, key=lambda pc: pc.distance_to(target))
            d.chapter_camera.frame(pc, target)
            try:
                pc.action_perform(D20A_UNSPECIFIED_ATTACK, target, 0)
            except RuntimeError:
                # Let the engine's world picker issue a normal attack between turns.
                if not archery and d.targos_enemy(target):
                    import controller_ui_util
                    controller_ui_util.verified_click(target, 'attack', fallback=None)
                return False
        return check()
    return run


def container_item(area, box_name, item):
    def run(st):
        import ie_itemrt
        d = driver()
        if has(item):
            return True
        if not arrive(st, area) or st.n % 10 != 1:
            return False
        containers = ie_itemrt.CONTAINERS.get(area, ie_itemrt.CONTAINERS.get(area[-6:], []))
        spec = next(c for c in containers if c['name'].lower() == box_name.lower())
        x, y = map(int, spec['toee'])
        boxes = [b for b in game.obj_list_vicinity(location_from_axis(x,y), OLC_CONTAINER)
                 if b.proto == spec['proto'] and location_to_axis(b.location) == (x,y)]
        if len(boxes) != 1:
            return d.fail('missing container ' + box_name)
        box = boxes[0]
        party = [pc for pc in game.party if not pc.is_unconscious()]
        pc = min(party, key=lambda member: member.distance_to(box))
        # Distance to the container includes its radius. Its tile centre can be inside
        # a wall even when the party can reach the side facing the room.
        if pc.distance_to(box) > 10 or not pc.has_los(box):
            d.walk_party(st, (x,y), 2, pc)
            return False
        if box.container_flags_get() & OCOF_LOCKED:
            rogue = max(party, key=lambda member: member.skill_level_get(skill_open_lock))
            if st.n >= getattr(st,'next_unlock',0) and not rogue.is_performing():
                st.next_unlock = st.n + 100
                rogue.action_perform(D20A_OPEN_LOCK, box, 0)
            return False
        obj = ie_itemrt.find(box, item)
        if not obj:
            return d.fail(item + ' missing in ' + box_name)
        transfer = getattr(ie_itemrt, 'transfer', None)
        if transfer:
            transfer(pc, obj)
        else:
            pc.item_get(obj)
        if not has(item):
            return d.fail('could not transfer %s from %s to %s' % (item, box_name, pc))
        d.log('LOOT %s from %s' % (item, box_name))
        return True
    return run


def buy_wine(st):
    """Buy one bottle from Pomab's finite converted stock at the IE store price."""
    import ie_itemrt
    d = driver()
    if has('wine'):
        return True
    if not arrive(st, 'AR1007'):
        return False
    merchant = d.find_obj(d.npc_script('pomab', 'AR1007')[0])
    if not merchant or not approach(st, location_to_axis(merchant.location), 9):
        return False
    box = merchant.substitute_inventory
    item = ie_itemrt.find(box, 'wine') if box else None
    if not item:
        return d.fail('Pomab has no wine in stock')
    pc = next(pc for pc in game.party if not pc.is_unconscious())
    worth = item.obj_get_int(obj_f_item_worth)
    price = max(1, (worth * ie_itemrt.STORES['ehpomab']['sell'] + 99) // 100)
    if pc.money_get() < price:
        return d.fail('party cannot afford wine at %d copper' % price)
    pc.item_get(item)
    if not has('wine'):
        return d.fail('could not collect wine from Pomab')
    pc.money_adj(-price)
    d.log('PURCHASE wine from Pomab for %d copper' % price)
    return True


def ammunition(pc):
    import ie_itemrt
    weapon = pc.item_worn_at(item_wear_weapon_primary)
    if not weapon or not weapon.obj_get_int(obj_f_weapon_flags) & OWF_RANGED_WEAPON:
        return None, []
    kind = weapon.obj_get_int(obj_f_weapon_ammo_type)
    stacks = {item.id: item for item in ie_itemrt._inv(pc) if item.type == obj_t_ammo
              and item.obj_get_int(obj_f_ammo_type) == kind}
    return kind, list(stacks.values())


def stock_ammunition(st):
    """Equip matching rounds and buy affordable bundles from the original merchant."""
    import ie_itemrt
    d = driver()
    area, ident, store, prefix = ('I2AR1102', '11deird', '11deird', '00') if d.GAME['g'] == 'iwd2' else (
        'AR1007', 'pomab', 'ehpomab', '')
    for pc in game.party:
        kind, stacks = ammunition(pc)
        if pc.is_unconscious() or kind not in (0, 1, 2):
            continue
        if stacks and not pc.get_ammo_used():
            pc.item_wield(stacks[0], item_wear_ammo)
        carried = sum(item.obj_get_int(obj_f_ammo_quantity) for item in stacks)
        if carried >= 40:
            continue
        if not arrive(st, area):
            return False
        merchant = d.find_obj(d.npc_script(ident, area[-6:])[0])
        if not merchant or not approach(st, location_to_axis(merchant.location), 7):
            return False
        box = merchant.substitute_inventory or ie_itemrt.stock_store(merchant, store)
        res = prefix + ('arow01', 'bolt01', 'bull01')[kind]
        stock = box and ie_itemrt.find(box, res)
        if not stock:
            continue
        available = stock.obj_get_int(obj_f_ammo_quantity)
        price = max(1, (ie_itemrt.entry(res)['w'] * ie_itemrt.STORES[store]['sell'] + 99) // 100)
        count = min(20, 40 - carried, available, pc.money_get() // price)
        if not count:
            continue
        bundle = stock if count == available else ie_itemrt.make(res, box.location, count)
        if not bundle:
            return d.fail('unable to prepare the ammunition at ' + store)
        ie_itemrt.transfer(pc, bundle)
        after = ammunition(pc)[1]
        if sum(item.obj_get_int(obj_f_ammo_quantity) for item in after) != carried + count:
            if count < available:
                bundle.destroy()
            return d.fail('ammunition transfer failed at ' + store)
        if count < available:
            stock.obj_set_int(obj_f_ammo_quantity, available - count)
        pc.money_adj(-count * price)
        if not pc.get_ammo_used():
            pc.item_wield(after[0], item_wear_ammo)
        d.log('PURCHASE %s bought %d %s at %s for %d copper' % (pc, count, res, store, count * price))
        return False
    return True


def outfit_at_pomab(st):
    """Use Pomab's actual stock and prices to improve the party's starting armour."""
    import ie_itemrt
    d = driver()
    if not arrive(st, 'AR1007'):
        return False
    merchant = d.find_obj(d.npc_script('pomab', 'AR1007')[0])
    if not merchant or not approach(st, location_to_axis(merchant.location), 7):
        return False
    box = merchant.substitute_inventory or ie_itemrt.stock_store(merchant, 'ehpomab')
    if not box:
        return True
    markup = ie_itemrt.STORES['ehpomab']['sell']
    for pc in game.party:
        if pc.is_unconscious() or pc.stat_level_get(stat_level_wizard):
            continue
        worn = pc.item_worn_at(item_wear_armor)
        dex = (pc.stat_level_get(stat_dexterity) - 10) // 2
        def protection(item):
            if not item:
                return dex
            cap = item.obj_get_int(obj_f_armor_max_dex_bonus)
            # Temple+ gets the base AC from the item's Armor Bonus condition.
            base_ac = item.item_d20_query(Q_Armor_Get_AC_Bonus) & 255
            return base_ac + (dex if cap < 0 else min(cap, dex))
        options = ['leat04']
        if pc.stat_level_get(stat_level_fighter) or pc.stat_level_get(stat_level_cleric):
            options += ['chan01', 'chan04']
        elif pc.stat_level_get(stat_level_barbarian):
            options += ['chan01']
        if worn and worn.item_flags_get() & OIF_IS_MAGICAL:
            options = []
        offers = []
        for res in options:
            item = ie_itemrt.find(box, res)
            if not item:
                continue
            price = (item.obj_get_int(obj_f_item_worth) * markup + 99) // 100
            gain = protection(item) - protection(worn)
            if gain > 0 and 0 < price <= pc.money_get():
                offers.append((gain, -price, res, item, item_wear_armor))
        weapon = pc.item_worn_at(item_wear_weapon_primary)
        if (pc.has_feat(feat_shield_proficiency) and weapon and pc.get_wield_type(weapon) < 2
                and not weapon.obj_get_int(obj_f_weapon_flags) & OWF_RANGED_WEAPON
                and not pc.item_worn_at(item_wear_weapon_secondary) and not pc.item_worn_at(item_wear_shield)):
            shield = ie_itemrt.find(box, 'shld01')
            if shield:
                gain = shield.item_d20_query(Q_Armor_Get_AC_Bonus) & 255
                price = (shield.obj_get_int(obj_f_item_worth) * markup + 99) // 100
                if gain > 0 and 0 < price <= pc.money_get():
                    offers.append((gain, -price, 'shld01', shield, item_wear_shield))
        if not offers:
            continue
        gain, negative_price, res, item, slot = max(offers, key=lambda offer: offer[:2])
        ie_itemrt.transfer(pc, item)
        pc.item_wield(item, slot)
        if pc.item_worn_at(slot) != item:
            ie_itemrt.transfer(box, item)
            return d.fail('could not equip %s from Pomab on %s' % (res, pc))
        pc.money_adj(negative_price)
        d.log('PURCHASE %s from Pomab for %d copper, %s gained %d armour class' % (res, -negative_price, pc, gain))
        return False
    return True


def buy_healing_supplies(st):
    """Restock from the local merchant, first serving characters who have no healing."""
    import ie_itemrt
    from new_game_controller import kit_healing_potions
    d = driver()
    def carried(pc):
        return sum(max(1, item.obj_get_int(obj_f_item_quantity)) for item in kit_healing_potions(pc))
    reserve = 2 if d.GAME['g'] == 'iwd2' else 1
    missing = [(carried(pc), pc) for pc in game.party if not pc.is_unconscious()]
    missing = sorted((entry for entry in missing if entry[0] < reserve), key=lambda entry: entry[0])
    if not missing:
        return True
    if d.GAME['g'] == 'iwd2':
        area, ident, shop, potion, name = 'I2AR1100', '11oswald', '11oswald', '00potn04', 'Oswald'
    else:
        area, ident, shop, potion, name = 'AR1001', 'everard', 'ehtemple', 'potn08', 'Everard'
    store = ie_itemrt.STORES[shop]
    price = max(1, (ie_itemrt.entry(potion)['w'] * store['sell'] + 99) // 100)
    funds = game.party[0].money_get()
    if funds < price:
        d.log('SUPPLIES party has %d copper; %s charges %d per healing potion' % (funds, name, price))
        return True
    if not arrive(st, area):
        return False
    merchant = d.find_obj(d.npc_script(ident, area[-6:])[0])
    if not merchant or not approach(st, location_to_axis(merchant.location), 7):
        return False
    box = merchant.substitute_inventory or ie_itemrt.stock_store(merchant, shop)
    stock = ie_itemrt.find(box, potion) if box else None
    if not stock:
        d.log('SUPPLIES %s has no healing potions left' % name)
        return True
    count = max(1, stock.obj_get_int(obj_f_item_quantity))
    before, buyer = missing[0]
    # Temple+ can combine the merchant's five original bottles into one
    # inventory stack. Sell a single bottle at the displayed unit price.
    bottle = stock if count == 1 else ie_itemrt.make(potion, box.location)
    if not bottle:
        return d.fail('could not split a healing potion from %s' % name)
    ie_itemrt.transfer(buyer, bottle)
    if carried(buyer) != before + 1:
        if count > 1:
            bottle.destroy()
        return d.fail('%s could not transfer the healing potion' % name)
    if count > 1:
        stock.obj_set_int(obj_f_item_quantity, count - 1)
    buyer.money_adj(-price)
    d.log('PURCHASE healing potion from %s for %d copper, carried by %s' % (name, price, buyer))
    return False


def wait_for_night(st):
    if not arrive(st, 'I2AR1105'):
        return False
    hour = game.time.time_game_in_hours(game.time)
    if hour > 19 or hour < 7:
        return True
    if not getattr(st, 'waited', False):
        st.waited = True
        driver().log('WAIT at the inn until 20:00 to meet Veira')
        game.fade((20 - hour) * 3600, 0, 0, 1)
    return False


def enter_keyed_room(area, key):
    """Use the innkeeper's key on the door carrying its original IE key reference."""
    def run(st):
        import ie_doors, ie_itemrt
        d = driver()
        if not arrive(st, area):
            return False
        if ie_doors._area != area:
            ie_doors.start(area)
        doors = __import__('ie_doors_' + area.lower()).DOORS
        matches = [door for door in doors if door.get('key','').lower() == key]
        if len(matches) != 1:
            return d.fail('expected one %s door for %s' % (area,key))
        door = matches[0]
        portal = ie_doors._find_portal(*door['loc'])
        if not portal:
            return d.fail('missing door ' + door['name'])
        if ie_doors._is_open(portal):
            return True
        carrier = next((p for p in game.party if ie_itemrt.find(p,key) and not p.is_unconscious()),None)
        if carrier is None:
            return d.fail('missing room key ' + key)
        if carrier.distance_to(portal) > 6:
            d.walk_party(st, door['toggle_tile'], 1, carrier)
            return False
        if portal.portal_flags_get() & OPF_LOCKED:
            portal.portal_flag_unset(OPF_LOCKED)
        portal.portal_toggle_open()
        d.log('UNLOCK %s with %s carried by %s' % (door['name'],key,carrier))
        return False
    return run


def identified(res):
    import ie_itemrt
    return any(it.item_flags_get() & OIF_IDENTIFIED for pc in game.party
               for it in (ie_itemrt.find(pc, res),) if it)


def identify_at_shop(res):
    def run(st):
        import ie_itemrt
        if getattr(st, 'service_error', None):
            return driver().fail(st.service_error)
        if identified(res):
            return True
        holder = next((pc for pc in game.party if ie_itemrt.find(pc, res)), None)
        if not holder:
            return driver().fail('missing item for identification: ' + res)
        if holder.is_unconscious():
            return driver().fail('the character carrying %s needs healing before visiting the merchant' % res)
        if not getattr(st,'service',None):
            driver().log('IDENTIFY %s carried by %s, party purse %d copper' % (res,holder,holder.money_get()))
        st.service = res
        st.customer = holder
        return driver().talk_step(st, '11elytha', 'I2AR1101', r'StartStore\(c, "11Elytha"',
                                  lambda: identified(res), lambda: holder)
    return run


def shop_service(st):
    """Use the merchant's identify button and the actual inventory slot; verify the item flag."""
    import controller_ui_util as ui
    import ie_itemrt
    res = st.service
    if identified(res):
        driver().log('IDENTIFIED %s by Elytharra' % res)
        del st.service
        return False
    ticks = st.shop_ticks = getattr(st, 'shop_ticks', 0) + 1
    if ticks == 1:
        button = ui.obtain_widget(ui.WID_IDEN.CHAR_LOOTING_UI_TAKE_ALL_BTN)
    elif ticks == 6:
        pc = st.customer
        item = ie_itemrt.find(pc, res)
        idx = next((i for i in range(24) if item and pc.inventory_item(i) == item), None)
        if idx is None:
            st.service_error = 'identification item is outside the displayed backpack'
            del st.service
            return False
        button = ui.obtain_widget(ui.WID_IDEN.CHAR_UI_INVENTORY_BTNS[idx])
    elif ticks > 25:
        st.service_error = 'merchant did not identify %s (party money %d copper)' % (res, game.party[0].money_get())
        del st.service
        return False
    else:
        return True
    if button:
        ui.move_mouse_to_widget(button)
        game.mouse_click()
    return True


def quest(name, tasks):
    def run(st):
        d = driver()
        st.sidequest = True
        if not hasattr(st, 'index'):
            if OUTCOMES[name]():
                d.log('SIDEQUEST PASS %s (already completed)' % name)
                return True
            st.index = 0
        if not hasattr(st, 'part'):
            st.part = d.Step(name)
            d.log('SIDEQUEST %s objective %d/%d' % (name, st.index+1, len(tasks)))
        st.part.n += 1
        if st.part.n > 3600:
            return d.fail('%s timed out at objective %d' % (name, st.index+1))
        if tasks[st.index](st.part) and not d.ST['fail']:
            st.index += 1
            del st.part
            if st.index == len(tasks):
                if not OUTCOMES[name]():
                    return d.fail('missing turn-in for ' + name)
                d.log('SIDEQUEST PASS ' + name)
                return True
        return False
    return (name, run)


def easthaven(before_cave=()):
    return [
        quest('jhonen', [
            quest_flag('jhonen','AR1000','Siren_Quest',1),
            dialogue('elisia','AR1000',r'GiveItemCreate\(c, "JhoSwd1"',lambda: has('jhoswd1') or driver().V('Siren_Quest') >= 3),
            dialogue('jhonen','AR1000',r'TakePartyItem\(c, "JhoSwd1"',lambda: driver().V('Siren_Quest') == 3 and not has('jhoswd1')),
            dialogue('elisia','AR1000',r'AddJournalEntry\(c, 16320,',lambda: driver().V('Elisia_Vanish') and has('misc36'))]),
        quest('grisella', [
            quest_flag('townsperson','AR1006','Grisella_Quest',1),
            encounter('AR1015','ehbeetle',(740,576),flag('SPRITE_IS_DEADEHBEETLE',4)),
            quest_flag('townsperson','AR1006','Grisella_Quest',2)]),
        quest('apsel', [
            quest_flag('scrimshander','AR1000','Apsel_Quest',1),
            encounter('AR1010','ehwolf',(527,453),flag('SPRITE_IS_DEADEHWolf',1)),
            quest_flag('scrimshander','AR1000','Apsel_Quest',3)]),
        quest('old_jed', [quest_flag('eholdjed','AR1009','Drunk_Quest',1), buy_wine,
                          dialogue('eholdjed','AR1009',r'AddJournalEntry\(c, 34194,',flag('Drunk_Quest',3))]),
        quest('damien', [
            dialogue('damien','AR1000',r'AddJournalEntry\(c, 34144,',lambda: journal(34144)),
            buy_healing_supplies,
            encounter('AR1000','goblinbowelitequ',(2927,2481),lambda: has('fish'),'fish'),
            quest_flag('damien','AR1000','Damien_Quest',2)])] + list(before_cave) + [
        quest('gaspar', [
            quest_flag('gaspar','AR1005','Gaspar_Quest',1),
            quest_flag('gaspar','AR1005','Gaspar_Quest',2),
            buy_healing_supplies,
            encounter('AR1201','ogre',(1348,1895),lambda: has('contract'),'contract'),
            quest_flag('gaspar','AR1005','Gaspar_Quest',3)])]


def targos_docks():
    return [
        quest('hedron', [quest_flag('10hedron','I2AR1000','Hedron_Quest',1),
                         quest_flag('10firth','I2AR1004','Hedron_Quest',3),
                         dialogue('10hedron','I2AR1000',r'journal=\(2569,',flag('Hedron_Quest',4))])]

def targos_before_docks_clear():
    return [quest('brogan', [
        quest_flag('10brogan','I2AR1000','Iron_Collar_Quest',1),
        quest_flag('10black','I2AR1003','Iron_Collar_Quest',2),
        quest_flag('10brogan','I2AR1000','Iron_Collar_Quest',3)]),
        quest('reig', [quest_flag('10reig','I2AR1000','Reig_Quest',1),
                       container_item('I2AR1001','Crate 1','00potn04'),
                       quest_flag('10reig','I2AR1000','Reig_Quest',2)])]


def targos_town(phase=None):
    market = [
        quest('guthewulfe', [dialogue('10guthe','I2AR1003',r'journal=\(7425,',flag('Guthewulfe_Game',2))]),
        quest('garradun', [quest_flag('11garrad','I2AR1103','Garradun_Quest',1),
                           dialogue('11denham','I2AR1103',r'GiveItemCreate\(c, "11GenDen',lambda: has('11genden')),
                           quest_flag('11garrad','I2AR1103','Garradun_Quest',3),
                           encounter('I2AR1103','doppelganger',(314,446),OUTCOMES['garradun'])])]
    palisade = [
        quest('niles', [dialogue('12niles','I2AR1200',r'journal=\(10634,',OUTCOMES['niles'])]),
        quest('caulder', [quest_flag('12caulde','I2AR1200','Catapult_Quest',2),
                          container_item('I2AR1006','Steel Locker','00hamm01'),
                          dialogue('12caulde','I2AR1200',r'journal=\(14822,',OUTCOMES['caulder'])]),
        quest('tabard', [quest_flag('12tabard','I2AR1200','Tabard_Quest',1)]),
        quest('recruits', [dialogue('12drill','I2AR1200',r'journal=\(242(79|80),',OUTCOMES['recruits'])]),
        quest('training', [
            encounter('I2AR1200','12kegmel',(2286,2185),flag('SPRITE_IS_DEADTRAINING_KEG',1)),
            dialogue('12weapon','I2AR1200',r'journal=\(7239,',OUTCOMES['training'])]),
        quest('archery', [
            dialogue('12gable','I2AR1200',r'journal=\(12737,',flag('Gable_Quest',1)),
            encounter('I2AR1200','12kegarc_ar1200',(3180,606),flag('SPRITE_IS_DEAD12KegArc',1),archery=True),
            dialogue('12gable','I2AR1200',r'journal=\(12738,',OUTCOMES['archery'])]),
        quest('firtha_cat', [quest_flag('12anson','I2AR1200','Anson_Cat',1),
                             dialogue('10firth','I2AR1004',r'journal=\(1346,',lambda: journal(1346)),
                             quest_flag('10firth','I2AR1004','Anson_Cat',2),
                             quest_flag('12anson','I2AR1200','Anson_Cat',3)])]
    returns = [
        quest('potion', [
            quest_flag('11koluhm','I2AR1107','Know_Koluhm_Inn',1),
            quest_flag('11cahlhy','I2AR1104','Potion_Quest',1), identify_at_shop('10gengbo'),
            quest_flag('11cahlhy','I2AR1104','Potion_Quest',2)]),
        quest('veira', [
            quest_flag('11cahlhy','I2AR1104','Veira_Quest',1), wait_for_night,
            enter_keyed_room('I2AR1105','11keyww2'),
            quest_flag('11veira','I2AR1105','Donovan_Q',1),
            quest_flag('11cahlhy','I2AR1104','Gohar_Direction',1),
            dialogue('10gohar','I2AR1003',r'GiveItemCreate\(c, "10GenDon',lambda: has('10gendon') or journal(28052)),
            wait_for_night,
            enter_keyed_room('I2AR1105','11keyww2'),
            dialogue('11veira','I2AR1105',r'AddXPVar\(c, "Level_1_Average", 28072\)',lambda: has('10genvbo') and driver().V('Veira_Happy') == 1),
            quest_flag('11cahlhy','I2AR1104','Veira_Quest_End',1)]),
        quest('tears', [quest_flag('11elytha','I2AR1101','Elytharra_Tear',1)]),
        quest('phaen', [
            encounter('I2AR1007','10rukwu',(572,564),lambda: has('10vellum'),'10vellum'),
            identify_at_shop('10vellum'),
            quest_flag('11elytha','I2AR1101','Expose_Phaen_Quest',1),
            quest_flag('11phaen','I2AR1106','Phaen_Loses_It',1),
            encounter('I2AR1106','11phaen',(400,264),flag('SPRITE_IS_DEADPhaen_of_the_Rags',1)),
            quest_flag('11elytha','I2AR1101','Expose_Phaen_Quest',2)])]
    return {None: market+palisade+returns, 'market': market, 'palisade': palisade, 'returns': returns}[phase]
