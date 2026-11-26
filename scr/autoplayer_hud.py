"""Build display lines from the live playtester stack, innermost goal first."""
import re

LABELS = {
    'next_region': 'Travel to the next region', 'arundel': 'Speak with Arundel',
    'vale': 'Enter the Vale of Shadows', 'bridge': 'Secure Shaengarne Bridge',
    'tomb': "Enter Kresselack's tomb",
    'tomb_descent': "Descend to the second tomb level",
    'tomb_foyer': 'Open the door at the foot of the stairs',
    'tomb_mausoleum_key': 'Find the Mausoleum Key', 'tomb_west_gate': 'Open the western mausoleum door',
    'tomb_room_key': 'Search the desk for the key', 'tomb_east_gate': 'Open the eastern mausoleum door',
    'tomb_inner_gate': 'Unlock the inner chamber', 'tomb_talisman': 'Recover the Black Wolf Talisman',
    'tomb_switch': 'Use the talisman at the hidden stairs', 'tomb_third_level': 'Descend to the third tomb level',
    'bridge_report': 'Report the bridge outcome to Lord Ulbrec',
    'fortress_scout': 'Find Ennelia at the goblin fortress',
    'warren_key': 'Recover the warren key', 'warren_gate': 'Unlock the side gate',
    'pondmuk': "Hear the goblin's offer", 'warren_spider': 'Bring Pondmuk a woolly spider',
    'spider_den': 'Open the spider den', 'warren_password': 'Learn the password',
    'warren_inner_gate': 'Open the guarded passage',
    'temple_approach': 'Find the Temple of the Forgotten God', 'temple_hall': 'Enter the temple',
    'temple_lower': 'Explore the lower temple', 'temple_altar_door': 'Open the inner temple door',
    'temple_altar': 'Reach the altar',
    'heartstone': 'Investigate the missing Heartstone', 'temple_report': 'Report back to Arundel',
    'dragons_eye': "Travel to Dragon's Eye",
    'warrens': 'Enter the warrens', 'deep_warrens': 'Cross the lower warrens',
    'fortress_courtyard': 'Reach the fortress outskirts', 'fortress_keep': 'Enter the inner fortress',
    'taskmaster_stone': "Recover the Taskmaster's wardstone", 'gumph_stone': "Recover Gumph's wardstone",
    'fortress_ward': 'Open the warded fortress door',
    'keep_key': "Recover the Old Orc's key", 'keep_inner_door': 'Open the inner keep door',
    'defeat_guthma': 'Defeat Guthma', 'braston_cell': "Open Braston's cell",
    'free_braston': 'Help Braston escape',
    'escort_keep': 'Lead Braston out of the keep', 'escort_courtyard': 'Escort Braston through the courtyard',
    'escort_approach': 'Bring Braston back to Ennelia', 'braston_reunion': 'Speak with Ennelia',
    'fortress_report': "Report Guthma's defeat to Ulbrec", 'oswald_flight': "Board Oswald's airship",
    'airship_arrival': "Arrive at Oswald's laboratory",
    'tomb_crypt': "Enter Kresselack's chamber", 'kresselack': 'Speak with Kresselack',
    'lysan': 'Find Lysan in the Vale', 'kresselack_report': 'Return to Kresselack',
    'vale_report': 'Tell Arundel what happened in the Vale',
    'tomb_symbol': 'Recover the holy symbol', 'tomb_symbol_gate': 'Open the sealed door with the holy symbol',
    'tomb_gate': 'Open the tomb gate', 'tomb_sanctum': 'Open the sanctum',
    'tomb_priest_key': 'Find the priest\'s key', 'tomb_priest_gate': 'Open the priest\'s gate',
    'gate_key': "Recover the Gate Key", 'sanctum_key': "Recover the Sanctum Key",
    'iwd_easthaven': 'Tour Easthaven', 'iwd2_targos': 'Tour Targos',
    'new_game': 'Start a new game', 'newgame': 'Enter the starting area',
    'normaldiff': 'Choose normal difficulty', 'align': 'Choose party alignment',
    'align_ok': 'Confirm party alignment', 'begin': 'Begin the adventure',
    'greet': 'Meet Hrothgar', 'posse': "Join Hrothgar's expedition",
    'caravan': 'Find the missing caravan', 'list': "Collect Hrothgar's supply list",
    'pomab': 'Deliver the list to Pomab', 'outfit': 'Equip the party at Pomab\'s',
    'ammunition': 'Stock up on ammunition', 'gaspar': 'Recover Gaspar\'s contract',
    'grisella': 'Clear the beetles from Grisella\'s cellar',
    'jhonen': 'Return Jhonen\'s sword', 'apsel': 'Help Apsel reclaim his workshop',
    'old_jed': 'Bring Old Jed his wine', 'depart': 'Depart with Hrothgar',
    'ar2000': 'Reach Kuldahar Pass', 'town_returns': 'Turn in open town quests',
    'dock_houses': 'Clear the dock buildings', 'docks': 'Secure the docks',
    'vellum': 'Investigate the goblin vellum', 'crane': 'Repair the dock crane',
    'shawford0': 'Ask Shawford about lumber', 'shawford1': 'Report to Shawford about arrows',
    'shawford2': 'Ask Shawford about the dead goblin', 'shawford3': 'Get the Iron Collar assignment',
    'shawford4': 'Hear Shawford\'s palisade briefing', 'palisade': 'Defend the palisade',
    'ulbrec': 'Report to Lord Ulbrec', 'supplies': 'Buy healing supplies',
    'open_worldmap': 'Open the world map', 'main': 'Play the adventure',
}


def label(key):
    key = str(key)
    if key.startswith('add_pcs'):
        return 'Assemble the party'
    pick = re.match(r'^pick_\d+_(.+)$', key)
    if pick:
        return 'Recruit a ' + pick.group(1)
    return LABELS.get(key, key.replace('_', ' ').strip().capitalize())


def goal_lines(player):
    if not player or not player.is_active():
        return []
    stack = player.__goal_slot__.goal_stack
    if not stack:
        return []
    from toee import game, OBJ_HANDLE_NULL
    import gamedialog
    import tpgui
    parents = []
    for entry in reversed(stack):
        name = label(entry.scheme_id)
        if entry.scheme_id == 'iwd_ch1':
            import iwd_ch1_driver as chapter
            area = (chapter.area_of(game.leader.map) or '') if game.party else ''
            if area == 'I2AR4001':
                name = "Oswald's laboratory / Chapter 2"
            elif area == 'AR4000':
                name = "Dragon's Eye / Chapter 2"
            elif area.startswith('I2AR3'):
                name = 'Horde Fortress / Chapter 1'
            elif area.startswith('I2AR2'):
                name = 'Shaengarne / Chapter 1'
            elif area.startswith('AR36'):
                name = 'Temple of the Forgotten God / Chapter 1'
            elif area.startswith('AR3'):
                name = 'Vale of Shadows / Chapter 1'
            elif area.startswith('AR2'):
                name = 'Kuldahar / Chapter 1'
            elif chapter.GAME['g'] == 'iwd2' and chapter.V('Chapter') == 1:
                name = 'Targos / Chapter 1'
            else:
                name = 'Targos / Prologue' if chapter.GAME['g'] == 'iwd2' else 'Easthaven / Prologue'
        parents.append(name)
    current = stack[0]
    stage = current.get_cur_stage_id()
    if current.scheme_id == 'iwd_ch1' and chapter.ST.get('steps'):
        state = chapter.ST
        if state.get('done') or state.get('fail') or state['i'] >= len(state['steps']):
            return []
        step = state['steps'][state['i']]
        parents.append(label(step.kind))
        if hasattr(step, 'index') and getattr(step, 'sidequest', False):
            parents.append('Objective %d' % (step.index + 1))
        if state.get('restarting'):
            parents.append('Reload the checkpoint')
        elif state.get('scene_started'):
            parents.append('Watch the cutscene')
        elif state.get('cave_regroup'):
            parents.append('Regroup and heal at the cave entrance')
        elif state.get('camp'):
            parents.append('Rest and recover')
        elif state.get('walking_to'):
            area = state['walking_to']
            destination = {'AR1000': 'Easthaven', 'AR1201': 'the orc cave',
                           'I2AR1000': 'the docks', 'I2AR1100': 'Targos town',
                           'I2AR1200': 'the palisade', 'I2AR1201': 'Shawford',
                           'AR2100': 'Kuldahar', 'AR4000': "Dragon's Eye",
                           'AR3501': "Kresselack's tomb", 'AR3502': 'the second tomb level',
                           'I2AR2000': 'Shaengarne Ford', 'I2AR2001': 'the orc camp',
                           'I2AR2102': 'Shaengarne Bridge'}.get(area, area)
            parents.append('Walk to ' + destination)
    elif current.scheme_id in ('iwd_easthaven', 'iwd2_targos'):
        import iwd_easthaven_controller as tour
        plan = tour.ST.get('plan') or []
        index = tour.ST['i']
        if stage == 'end' or (plan and index >= len(plan)):
            return []
        if plan:
            step = plan[index]
            person = tour.ST['givers'].get(getattr(step, 'sid', None), {})
            parents.append('Talk to ' + person['ident'] if step.kind == 'talk' and person
                           else (label(step.kind) + ' ' + getattr(step, 'area', '')).strip())
    elif stage not in ('start', 'end', 'ch1'):
        parents.append(label(stage))

    if not tpgui.game_is_focused():
        parents.append('Wait for game focus')
    elif gamedialog.is_engaged():
        parents.append('Read dialogue and choose a reply')
    elif game.combat_is_active():
        import tpactions
        actor = tpactions.get_current_tb_actor()
        parents.append("Combat / %s's turn" % actor.description
                       if actor and actor != OBJ_HANDLE_NULL else 'In combat')
    rows = list(reversed(parents))
    return ['Now / ' + rows[0]] + ['  ' + row for row in rows[1:]]
