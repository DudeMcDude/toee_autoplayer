"""Spend earned levels through the character editor on the opening chapter routes."""
import re
import time

import autoui
import char_editor
from toee import *
import controller_ui_util as ui


CLASSES = ((stat_level_fighter, 'Fighter'), (stat_level_barbarian, 'Barbarian'),
           (stat_level_rogue, 'Rogue'), (stat_level_cleric, 'Cleric'), (stat_level_wizard, 'Wizard'))
SKILLS = {'Fighter': ('Intimidate', 'Heal', 'Diplomacy'), 'Barbarian': ('Intimidate', 'Listen', 'Heal'),
          'Rogue': ('Disable Device', 'Open Lock', 'Diplomacy', 'Bluff'),
          'Cleric': ('Concentration', 'Heal', 'Diplomacy'), 'Wizard': ('Concentration', 'Spellcraft')}
SECOND_LEVEL_ATTACKS = ((spell_melfs_acid_arrow, "Melf's Acid Arrow"), (spell_scorching_ray, 'Scorching Ray'))


def children(panel):
    widgets = (autoui.TWidget(w) for w in panel.children_ids or ())
    return [widget for widget in widgets if widget.visible]


def click(w, button=0):
    ui.move_mouse_to_widget(w)
    game.mouse_click(button)


def panel_with(panels, name):
    return next((w for w in panels if w.name == name), None)


def spend_skill(panel, state):
    buttons = children(panel)
    names = dict((int(w), name.strip()) for w, name in
                 re.findall(r'\[WID=(\d+)\]([^\[\n]+)', panel.rendered_text) if name.strip() and name[0].isalpha())
    page = tuple(sorted(names.items()))
    if state.get('skills_page') != page:
        state['blocked_skills'] = set()
        state.pop('ranks', None)
        state['skills_page'] = page
    plus = [w for w in buttons if w.name == 'char_editor_skills_ui.c 493' and w.is_button_enabled]
    ranks = tuple(w.rendered_text for w in buttons if w.name == 'char_editor_skills_ui.c 472')
    blocked = state.setdefault('blocked_skills', set())
    if state.get('ranks') == ranks:
        blocked.add(state.get('last_skill'))
    plus = [w for w in plus if w.id not in blocked]
    if not plus:
        # A final point may buy only a class skill. Search the remaining rows
        # when the visible class skills are capped and cross-class rows are grey.
        if page and page != state.get('scroll_page'):
            state['scroll_page'] = page
            row = next((w for w in buttons if w.name == 'char_editor_skills_ui.c 472'), None)
            if row:
                ui.move_mouse_to_widget(row)
                game.mouse_scroll(-3)
                return True
        return False
    state['ranks'] = ranks
    preferred = SKILLS[state['class']]
    def preference(w):
        row = next((r for r in buttons if r.name == 'char_editor_skills_ui.c 472' and abs(r.y-w.y)<6), None)
        name = names.get(row.id) if row else None
        return preferred.index(name) if name in preferred else len(preferred)
    choice = min(plus, key=preference)
    state['last_skill'] = choice.id
    click(choice)
    return True


def advance(state, log):
    pc = game.party[state['index']]
    if pc.stat_level_get(stat_level) > state['level']:
        log('LEVEL %s advanced to %s %d' % (pc,state['class'],pc.stat_level_get(stat_level)))
        return True
    panels = [autoui.TWidget(i) for i in autoui.get_active_windows()]
    nav = panel_with(panels, 'char_ui.c 5217')
    if not nav:
        if state['ticks'] < 15 and state['ticks'] % 5 == 1:
            icon = ui.obtain_widget(ui.WID_IDEN.PARTY_UI_LEVELUP_BTNS[state['index']])
            if icon:
                click(icon)
        return False
    nav_buttons = dict((w.rendered_text.upper(), w) for w in children(nav) if w.is_button)
    phase = state['phase']
    if phase == 'CLASS':
        panel = panel_with(panels, 'char_editor_class_ui.c 193')
        if panel:
            w = next((w for w in children(panel) if w.name == 'Class btn' and
                      w.rendered_text.upper() == state['class'].upper() and w.is_button_enabled), None)
            if w:
                click(w)
                state['phase'] = 'SKILLS'
        return False
    if phase == 'SKILLS':
        panel = panel_with(panels, 'char_editor_skills_ui.c 430')
        if not panel:
            click(nav_buttons['SKILLS'])
            return False
        if spend_skill(panel, state):
            return False
        state['phase'] = phase = 'FEATS'
    if phase == 'FEATS':
        next_level = state['level'] + 1
        need = next_level % 3 == 0 or (state['class'] == 'Fighter' and next_level % 2 == 0)
        if need:
            panel = panel_with(panels, 'Char Editor Feats Wnd')
            if not panel:
                click(nav_buttons['FEATS'])
                return False
            # The native editor includes pending selections in get_feats().
            # Each supported level asks for exactly one regular or bonus feat.
            feat_count = len(char_editor.get_feats())
            if feat_count > state.setdefault('original_feat_count', feat_count):
                state['phase'] = 'SPELLS'
                return False
            feats = children(panel)
            choices = (('Cleave','Combat Reflexes','Blind-fight','Dodge') if state['class'] in ('Fighter','Barbarian')
                       else ('Combat Casting','Combat Reflexes','Alertness') if state['class'] in ('Wizard','Cleric')
                       else ('Combat Reflexes','Dodge','Alertness'))
            remaining = [name for name in choices if name not in state['tried']]
            for name in remaining:
                w = next((w for w in feats if w.name == 'Feats Available btn' and w.rendered_text == name), None)
                if w:
                    state['tried'].add(name)
                    click(w, 1)
                    return False
        state['phase'] = phase = 'SPELLS'
    if phase == 'SPELLS' and state['class'] == 'Wizard' and nav_buttons['SPELLS'].is_button_enabled:
        # Opening the page initializes the class's list of spells to learn.
        # Before initialization an empty list can satisfy the native check.
        rows = [w for p in panels if p.is_window for w in children(p)
                if w.name=='Spell Available btn' and w.rendered_text.strip()]
        if not rows:
            click(nav_buttons['SPELLS'])
            return False
        if char_editor.spells_check_complete(pc, stat_level_wizard):
            click(nav_buttons['FINISH'])
            return False
        if state['level'] in (1, 2):
            # The available list starts at cantrips. Search later pages for
            # the defensive or offensive spells used by the chapter party.
            known = set(s.spell_enum for s in pc.spells_known)
            offered = set(s.spell_enum for s in char_editor.get_available_spells())
            goals = SECOND_LEVEL_ATTACKS if state['level'] == 2 else ((spell_mage_armor, 'Mage Armor'),)
            wanted = [name for spell, name in goals if spell in offered
                      and spell not in known and name not in state['tried']]
            for row in rows:
                if row.rendered_text in wanted:
                    state['tried'].add(row.rendered_text)
                    click(row, 1)
                    return False
            page = tuple(w.rendered_text for w in rows)
            if wanted and page != state.get('last_spell_page'):
                state['last_spell_page'] = page
                ui.move_mouse_to_widget(rows[len(rows) // 2])
                game.mouse_scroll(-3)
                return False
        priorities = ('Scorching Ray', "Melf's Acid Arrow", 'Sleep', 'Magic Missile', 'Color Spray', 'Grease', 'Shield')
        rows.sort(key=lambda w: priorities.index(w.rendered_text) if w.rendered_text in priorities else len(priorities))
        for w in rows:
            label = w.rendered_text
            if label not in state['tried']:
                state['tried'].add(label)
                click(w, 1)
                return False
        ui.move_mouse_to_widget(rows[len(rows) // 2])
        game.mouse_scroll(-1)
        return False
    click(nav_buttons['FINISH'])
    return False


def tick(st):
    import iwd_ch1_driver as driver
    now = time.time()
    state = driver.ST.get('levelup')
    if now < driver.ST.get('next_level_check', 0):
        return bool(state)
    driver.ST['next_level_check'] = now + (0.25 if state else 2)
    if not state:
        if game.char_ui_display_type or driver.ST.get('camp') or st.kind in ('newgame','greet'):
            return False
        for i, pc in enumerate(game.party):
            level = pc.stat_level_get(stat_level)
            if pc.is_unconscious() or level not in (1, 2) or pc.stat_level_get(stat_experience) < 500 * level * (level + 1):
                continue
            icon = ui.obtain_widget(ui.WID_IDEN.PARTY_UI_LEVELUP_BTNS[i])
            if not icon or not icon.visible:
                continue
            if any(driver.targos_enemy(o) and pc.distance_to(o) < 45 for o in game.obj_list_vicinity(pc.location, OLC_NPC)):
                continue
            class_name = next((name for code, name in CLASSES if pc.stat_level_get(code) == level), None)
            if not class_name:
                continue
            state = driver.ST['levelup'] = dict(index=i, level=level, phase='CLASS', ticks=0, tried=set())
            state['class'] = class_name
            driver.log('LEVEL %s opening editor for %s %d' % (pc, class_name, level + 1))
            break
    if not state:
        return False
    state['ticks'] += 1
    if advance(state, driver.log):
        if state['class'] in ('Wizard', 'Cleric'):
            driver.ST['check_new_spells'] = True
            driver.ST.pop('last_camp', None)
        del driver.ST['levelup']
        driver.ST['next_level_check'] = 0
    elif state['ticks'] >= 100:
        driver.fail('level-up editor did not finish %s for %s' % (state['phase'], game.party[state['index']]))
    return True
