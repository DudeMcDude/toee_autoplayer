"""Focused regressions for chapter movement and dialogue pacing. Run with Python 3."""
import ast
import importlib.util
import math
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import MagicMock, patch

SCR = Path(__file__).resolve().parents[1] / 'scr'


def function_from_file(name, filename, namespace):
    tree = ast.parse((SCR / filename).read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[function], type_ignores=[]), filename, 'exec'), namespace)
    return namespace[name]


class Actor:
    radius = 24
    friendly = False
    active = True
    unconscious = False
    can_aoo = True
    acted = False
    hp = 64

    def __init__(self, x=0, y=0):
        self.location = (x, y)
        self.actions = []

    def stat_level_get(self, stat):
        return { 'stat_size': 5, 'stat_hp_current': self.hp, 'stat_hp_max': 64 }[stat]

    def obj_get_int(self, field):
        return 5 if field == 'obj_f_critter_reach' else 0

    def item_worn_at(self, slot):
        return None

    def distance_to(self, point):
        if isinstance(point, Actor):
            return max(0, self.distance_to(point.location) - point.radius / 12.0)
        return max(0, math.hypot(point[0] - self.location[0], point[1] - self.location[1]) * 2.357 - 2)

    def can_melee(self, target):
        return self.distance_to(target) <= 3

    def d20_query(self, query):
        return False

    def d20_query_with_object(self, query, actor):
        return self.can_aoo

    def is_friendly(self, actor):
        return self.friendly

    def is_active_combatant(self):
        return self.active

    def is_unconscious(self):
        return self.unconscious

    def object_flags_get(self):
        return 0

    def action_perform(self, action, target, point):
        self.actions.append((action, target, point))
        return 1


class MovementTests(unittest.TestCase):
    def setUp(self):
        toee = types.ModuleType('toee')
        names = ('stat_size stat_hp_current stat_hp_max obj_f_critter_reach obj_f_weapon_type '
                 'item_wear_weapon_primary wt_glaive wt_guisarme wt_longspear wt_ranseur wt_spike_chain '
                 'OLC_CRITTERS Q_AOOPossible Q_AOOWillTake Q_Prone D20A_5FOOTSTEP').split()
        for name in names:
            setattr(toee, name, name)
        toee.OF_OFF, toee.OF_DONTDRAW, toee.OF_CLICK_THROUGH = 1, 2, 4
        toee.TBSF_Movement, toee.TBSF_1 = 2, 1
        toee.OBJ_HANDLE_NULL = None
        self.actor = Actor()
        self.enemies = []
        toee.game = types.SimpleNamespace(party=[self.actor], obj_list_range=lambda *args: self.enemies)
        self.engine = toee
        self.status = types.SimpleNamespace(flags=0)
        modules = {
            'toee': toee,
            'utilities': types.SimpleNamespace(location_from_axis=lambda x, y: (x, y), location_to_axis=lambda p: p),
            'debug': types.SimpleNamespace(pathto=lambda *args: True),
            'tpactions': types.SimpleNamespace(cur_seq_reset=lambda actor: None),
        }
        self.mock_modules = patch.dict(sys.modules, modules)
        self.mock_modules.start()
        self.addCleanup(self.mock_modules.stop)
        spec = importlib.util.spec_from_file_location('tactics_under_test', SCR / 'chapter_combat.py')
        self.tactics = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.tactics)

    def test_move_from_threat_is_rejected_without_spending_action(self):
        self.assertFalse(self.tactics.allow_move(self.actor, (6, 0), [Actor(2, 0)]))
        self.assertEqual(self.actor.actions, [])

    def test_route_crossing_enemy_is_risky_even_when_start_is_safe(self):
        enemy = Actor(5, 0)
        self.assertFalse(enemy.can_melee(self.actor))
        self.assertFalse(self.tactics.allow_move(self.actor, (10, 0), [enemy]))

    def test_unthreatened_move_is_allowed(self):
        self.assertTrue(self.tactics.allow_move(self.actor, (8, 0), [Actor(0, 12)]))

    def test_exhausted_aoos_allies_and_unconscious_are_excluded(self):
        eligible, spent, friend, asleep = [Actor(2, 0) for _ in range(4)]
        spent.can_aoo = False
        friend.friendly = True
        asleep.unconscious = True
        self.enemies[:] = [eligible, spent, friend, asleep]
        self.assertEqual(self.tactics.opponents(self.actor), [eligible])

    def test_step_back_reduces_threats(self):
        enemy = Actor(2, 0)
        self.assertTrue(self.tactics.five_foot_step(self.actor, [enemy], self.status))
        action, target, point = self.actor.actions[0]
        self.assertEqual(action, 'D20A_5FOOTSTEP')
        self.assertFalse(self.tactics.threatens_at(enemy, self.actor, point))

    def test_step_forward_closes_melee_gap(self):
        target = Actor(4, 0)
        self.assertFalse(self.actor.can_melee(target))
        self.assertTrue(self.tactics.five_foot_step(self.actor, [target], self.status, target))
        self.assertGreater(self.actor.actions[0][2][0], 0)

    def test_step_does_not_replace_an_available_melee_attack(self):
        self.assertFalse(self.tactics.five_foot_step(self.actor, [], self.status, Actor(2, 0)))
        self.assertEqual(self.actor.actions, [])

    def test_no_second_step_or_step_after_moving(self):
        for flag in (1, 2):
            self.status.flags = flag
            self.assertFalse(self.tactics.five_foot_step(self.actor, [Actor(2, 0)], self.status))
        self.assertEqual(self.actor.actions, [])

    def test_one_risk_can_be_justified_only_for_healthy_rescuer(self):
        threats = [Actor(2, 0)]
        self.assertTrue(self.tactics.allow_move(self.actor, (5, 0), threats, rescue=True))
        self.actor.hp = 10
        self.assertFalse(self.tactics.allow_move(self.actor, (5, 0), threats, rescue=True))
        self.actor.hp = 64
        self.assertFalse(self.tactics.allow_move(self.actor, (5, 0), threats * 2, rescue=True))

    def test_failed_step_is_attempted_once(self):
        def failure(action, target, point):
            self.actor.actions.append(action)
            raise RuntimeError('blocked')
        self.actor.action_perform = failure
        self.assertFalse(self.tactics.five_foot_step(self.actor, [Actor(2, 0)], self.status))
        self.assertEqual(len(self.actor.actions), 1)


class PendingSequenceTests(unittest.TestCase):
    def setUp(self):
        self.actor = MagicMock()
        self.actor.is_performing.return_value = False
        self.actor.stat_level_get.return_value = 0
        self.actor.can_melee.return_value = False
        self.actor.distance_to.return_value = 10
        self.actor.item_worn_at.return_value.obj_get_int.return_value = 80
        self.enemy = MagicMock()
        self.enemy.is_unconscious.return_value = False
        self.enemy.is_friendly.return_value = False
        self.enemy.object_flags_get.return_value = 0
        self.enemy.distance_to.return_value = 10
        self.enemy.stat_level_get.return_value = 12
        self.queued = ['stale move', 'stale shot']
        self.performed = []

        def perform(action, target, location):
            self.queued.append(action)
            self.performed.extend(self.queued)

        self.actor.action_perform.side_effect = perform
        self.status = types.SimpleNamespace(hourglass_state=4, flags=0)
        self.actions = types.SimpleNamespace(
            get_current_tb_actor=lambda: self.actor,
            get_cur_seq=lambda: types.SimpleNamespace(tb_status=self.status),
            cur_seq_reset=MagicMock(side_effect=lambda actor: self.queued.clear()))
        tactics = types.SimpleNamespace(opponents=lambda actor: [self.enemy], five_foot_step=lambda *args: False)
        state = {}
        self.slot = types.SimpleNamespace(get_scheme_state=lambda: state)
        ns = dict(game=types.SimpleNamespace(
            party=[self.actor], combat_is_active=lambda: True, combat_turn=1,
            obj_list_vicinity=lambda *args: [self.enemy]),
            OBJ_HANDLE_NULL=None, OLC_NPC=1, OF_DONTDRAW=1, OF_CLICK_THROUGH=2,
            OWF_RANGED_WEAPON=16, item_wear_weapon_primary=3, obj_f_weapon_flags=1,
            obj_f_weapon_range=2, stat_hp_current=3, sp_Sleep=4, D20A_TOTAL_DEFENSE='defense',
            obj_is_caster=lambda actor: False, obj_percent_hp=lambda actor: 100,
            location_to_axis=lambda location: (0, 0))
        self.handler = function_from_file('combat_action_handler', 'new_game_controller.py', ns)
        modules = patch.dict(sys.modules, tpactions=self.actions, chapter_combat=tactics)
        modules.start()
        self.addCleanup(modules.stop)

    def test_defense_discards_unexecuted_move_and_shot(self):
        self.handler(self.slot, chapter_log=lambda message: None)
        self.assertEqual(self.performed, ['defense'])
        self.assertEqual(self.status.hourglass_state, 4)

    def test_custom_turn_handoff_keeps_the_action_available(self):
        handoff = MagicMock()
        self.handler(self.slot, chapter_log=lambda message: None, end_turn=handoff)
        handoff.assert_called_once_with()
        self.assertEqual(self.performed, [])

    def test_running_animation_keeps_its_sequence(self):
        self.actor.is_performing.return_value = True
        self.handler(self.slot, chapter_log=lambda message: None)
        self.actions.cur_seq_reset.assert_not_called()
        self.assertEqual(self.performed, [])


class DialogueTests(unittest.TestCase):
    def setUp(self):
        self.now = 0
        self.replies = []
        self.dialogue = types.SimpleNamespace(script_id=1, line_number=10, reply_count=1, get_npc_reply_id=lambda i: 20)
        self.ns = {
            'dlg': types.SimpleNamespace(get_current_state=lambda: self.dialogue),
            'TALK': {'cur': None}, 'ST': {'shot_dlg_1': True},
            'time': types.SimpleNamespace(time=lambda: self.now),
            'dialogue_delay': lambda sid, line: 3,
            'find_attack_lines': lambda state: [],
            'dlg_reply': self.replies.append, 'log': lambda message: None,
        }
        self.tick = function_from_file('ch1_dialog_handler', 'iwd_ch1_driver.py', self.ns)

    def test_first_and_subsequent_lines_wait_three_seconds(self):
        self.assertEqual(self.tick(None), 3000)
        self.now = 0.75
        self.tick(None)
        self.assertEqual(self.replies, [])
        self.now = 3
        self.assertEqual(self.tick(None), 150)
        self.assertEqual(self.replies, [0])
        self.dialogue.line_number = 20
        self.assertEqual(self.tick(None), 3000)
        self.assertEqual(self.replies, [0])

    def test_converted_voice_can_outlast_the_reading_pause(self):
        import glob
        import re
        with tempfile.TemporaryDirectory() as tmp:
            core = Path(tmp) / 'IWD_core'
            (core / 'dlg').mkdir(parents=True)
            (core / 'dlg/00001ie_npc.dlg').write_text(
                '{10}{Greetings.}{Greetings.}{}{30}{}{}\n{20}{Welcome.}{Welcome.}{}{40}{}{}\n')
            speech = Path(tmp) / 'IWD/sound/speech/00001'
            speech.mkdir(parents=True)
            (speech / 'v30_m.mp3').write_bytes(bytes(80000))
            ns = dict(os=os, glob=glob, re=re, E=types.SimpleNamespace(find_core=lambda: str(core)), _dialogue_lengths={})
            delay = function_from_file('dialogue_delay', 'iwd_ch1_driver.py', ns)
            self.assertAlmostEqual(delay(1, 10), 10.25)
            self.assertEqual(delay(1, 20), 3.0)

    def test_same_line_reply_is_paced_again(self):
        self.tick(None)
        self.now = 3
        self.tick(None)
        self.assertEqual(self.tick(None), 3000)
        self.assertEqual(self.replies, [0])

    def test_long_lines_are_capped(self):
        import glob
        import re
        with tempfile.TemporaryDirectory() as core:
            directory = Path(core) / 'dlg'
            directory.mkdir()
            (directory / '00001npc.dlg').write_text('{10}{Hello}\n{20}{' + 'x' * 1000 + '}\n')
            ns = dict(os=os, glob=glob, re=re, E=types.SimpleNamespace(find_core=lambda: core), _dialogue_lengths={})
            delay = function_from_file('dialogue_delay', 'iwd_ch1_driver.py', ns)
            self.assertEqual(delay(1, 10), 3)
            self.assertEqual(delay(1, 20), 7.5)
            self.assertEqual(delay(9, 10), 3)

    def test_incidental_menu_tries_another_peaceful_reply_on_return(self):
        self.dialogue.reply_count = 3
        self.ns['find_attack_lines'] = lambda state: [1]
        for _ in range(2):
            self.tick(None)
            self.now += 3
            self.tick(None)
        self.assertEqual(self.replies, [0, 2])


class CheckpointTests(unittest.TestCase):
    def test_post_battle_save_retries_after_cooldown_on_the_same_map(self):
        game = MagicMock(party=[])
        state = {'i': 2, 'checkpoint': (2, 5093)}
        step = types.SimpleNamespace(kind='tomb_descent', n=10, next_save_attempt=30)
        namespace = dict(game=game, ST=state, GAME={'g': 'iwd'}, OLC_NPC=0,
                         get_current_map=lambda: 5093, dlg=types.SimpleNamespace(is_engaged=lambda: False),
                         log=lambda message: None)
        save = function_from_file('checkpoint_party', 'iwd_ch1_driver.py', namespace)
        with patch.dict(sys.modules, ie_cutscene=types.SimpleNamespace(active=lambda: False)):
            save(step, True)
            game.savegame.assert_not_called()
            step.n = 30
            save(step, False)
            save(step, False)
        game.savegame.assert_called_once_with('IEAP_Chapter_iwd', 'Chapter autoplayer recovery')


class ApproachTests(unittest.TestCase):
    def test_missing_speaker_without_spawn_hint_gets_search_grace(self):
        now = [0]
        failures = []
        actor = Actor()
        ns = dict(time=types.SimpleNamespace(time=lambda: now[0]),
                  game=types.SimpleNamespace(party=[actor]), OBJ_HANDLE_NULL=None,
                  get_current_map=lambda: 1, area_map=lambda area: 1,
                  dlg=types.SimpleNamespace(is_engaged=lambda: False),
                  find_obj=lambda sid: None, location_to_axis=lambda p: p,
                  E=types.SimpleNamespace(spawn_tiles=lambda *args: []),
                  fail=lambda message: failures.append(message) or 1)
        talk = function_from_file('talk_step', 'iwd_ch1_driver.py', ns)
        state = types.SimpleNamespace(n=0, sid=1, goals=[1], talks=0)
        self.assertEqual(talk(state, 'speaker', 'area', 'goal', lambda: False), 0)
        self.assertEqual(failures, [])
        now[0], state.n = 21, 10
        self.assertEqual(talk(state, 'speaker', 'area', 'goal', lambda: False), 1)
        self.assertEqual(len(failures), 1)


class MovieTests(unittest.TestCase):
    def test_chapter_default_show_explicit_skip_and_restore(self):
        calls = []
        movie = types.ModuleType('ie_movies_rt')
        movie.FLAG_VAR = 990
        movie.play = lambda key: calls.append(key)
        movie.play_intro = lambda: calls.append('intro')
        movie.prologue = lambda key: calls.append('prologue-' + key)
        ns = dict(os=os, game=types.SimpleNamespace(global_vars={990: 0}), log=lambda message: None)
        configure = function_from_file('no_movies', 'iwd_easthaven_controller.py', ns)
        with patch.dict(sys.modules, ie_movies_rt=movie), patch.dict(os.environ, {}, clear=True):
            configure(show=True)
            movie.play('avalanche')
            self.assertEqual(calls, ['avalanche'])
            os.environ['IWDAP_MOVIES'] = '0'
            configure(show=True)
            movie.play_intro()
            movie.prologue('chapter1')
            self.assertEqual(calls, ['avalanche'])
            del os.environ['IWDAP_MOVIES']
            configure(show=True)
            movie.prologue('chapter1')
            self.assertEqual(calls, ['avalanche', 'prologue-chapter1'])

    def test_old_converted_module_without_prologue(self):
        movie = types.ModuleType('ie_movies_rt')
        movie.play = movie.play_intro = lambda *args: 1
        ns = dict(os=os, log=lambda message: None)
        configure = function_from_file('no_movies', 'iwd_easthaven_controller.py', ns)
        with patch.dict(sys.modules, ie_movies_rt=movie), patch.dict(os.environ, {}, clear=True):
            configure(show=True)
            self.assertEqual(movie.play('intro'), 1)


class FordTrailTests(unittest.TestCase):
    def test_party_only_breaks_a_placed_keg_ahead_after_progress_stops(self):
        hero = Actor(10, 10)
        hero.is_performing = lambda: False
        hero.has_los = lambda target: True
        hero.action_perform = lambda action, target, unused: hero.actions.append(target)
        objects = {'behind': Actor(11, 10), 'blocking': Actor(8, 10),
                   'explosive': Actor(9, 10), 'npc': Actor(9, 10)}
        for guid, obj in objects.items():
            obj.id = guid
        placements = {key: {'spec': {'resref': resref}} for key, resref in
                      [('behind', '20keg1'), ('blocking', '20keg2'), ('explosive', 'dynokeg'), ('npc', '20dereth')]}
        game = types.SimpleNamespace(party=[hero], get_obj_by_id=objects.get)
        clock = types.SimpleNamespace(time=lambda: 100)
        check = function_from_file('clear_ford_keg', 'iwd_ch1_driver.py',
                                   dict(game=game, time=clock, location_to_axis=lambda p: p, OF_OFF=1, OF_DONTDRAW=2,
                                        D20A_UNSPECIFIED_ATTACK=0, stat_hp_current='stat_hp_current',
                                        log=lambda message: None))
        step = types.SimpleNamespace()
        with patch.dict(sys.modules, ie_bake_i2ar2000=types.SimpleNamespace(OBJS=placements)):
            self.assertFalse(check(step, (0, 10)))
            clock.time = lambda: 108
            self.assertTrue(check(step, (0, 10)))
            self.assertEqual(hero.actions, [objects['blocking']])
            self.assertFalse(check(step, (20, 10)))
            clock.time = lambda: 116
            self.assertTrue(check(step, (20, 10)))
            self.assertEqual(hero.actions[-1], objects['behind'])


if __name__ == '__main__':
    unittest.main()
