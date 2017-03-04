from itertools import chain
from panda3d.core import Vec3, Vec2
from direct.showbase.InputStateGlobal import inputState
from yyagl.gameobject import Event
from yyagl.racing.race.event import NetMsgs
from yyagl.racing.weapon.rocket.rocket import Rocket


class CarEvent(Event):

    def __init__(self, mdt):
        Event.__init__(self, mdt)
        eng.phys.attach(self.on_collision)
        keys = game.options['settings']['keys']
        self.label_events = [
            ('forward', keys['forward']), ('left', keys['left']),
            ('reverse', keys['rear']), ('right', keys['right'])]
        watch = inputState.watchWithModifiers
        self.toks = map(lambda (lab, evt): watch(lab, evt), self.label_events)

    def start(self):
        eng.event.attach(self.on_frame)

    def on_collision(self, obj, obj_name):
        is_for_me = obj == self.mdt.gfx.nodepath.node()
        if is_for_me and obj_name.startswith('Respawn'):
            self.__process_respawn()
        if is_for_me and obj_name.startswith('PitStop'):
            self.mdt.gui.apply_damage(True)
            self.mdt.phys.apply_damage(True)
            self.mdt.gfx.apply_damage(True)

    def __process_respawn(self):
        start_wp_n, end_wp_n = self.mdt.logic.last_wp
        self.mdt.gfx.nodepath.setPos(start_wp_n.get_pos() + (0, 0, 2))

        wp_vec = Vec3(end_wp_n.getPos(start_wp_n).xy, 0)
        wp_vec.normalize()
        or_h = (wp_vec.xy).signedAngleDeg(Vec2(0, 1))
        self.mdt.gfx.nodepath.setHpr(-or_h, 0, 0)
        self.mdt.gfx.nodepath.node().setLinearVelocity(0)
        self.mdt.gfx.nodepath.node().setAngularVelocity(0)

    def on_frame(self):
        input_dct = self._get_input()
        if self.mdt.fsm.getCurrentOrNextState() in ['Loading', 'Countdown']:
            input_dct = {key: False for key in input_dct}
            self.mdt.logic.reset_car()
        self.mdt.logic.update(input_dct)
        if self.mdt.logic.is_upside_down:
            self.mdt.gfx.nodepath.setR(0)
        self.__update_contact_pos()
        self.mdt.phys.update_car_props()
        self.mdt.logic.update_waypoints()

    def __update_contact_pos(self):
        car_pos = self.mdt.gfx.nodepath.get_pos()
        top = (car_pos.x, car_pos.y, car_pos.z + 50)
        bottom = (car_pos.x, car_pos.y, car_pos.z - 50)
        hits = eng.phys.world_phys.rayTestAll(top, bottom).getHits()
        for hit in [hit for hit in hits if 'Road' in hit.getNode().getName()]:
            self.mdt.logic.last_wp = self.mdt.logic.closest_wp()

    def destroy(self):
        Event.destroy(self)
        eng.phys.detach(self.on_collision)
        eng.event.detach(self.on_frame)
        map(lambda tok: tok.release(), self.toks)


class CarPlayerEvent(CarEvent):

    def __init__(self, mdt):
        CarEvent.__init__(self, mdt)
        self.accept('f11', self.mdt.gui.toggle)
        self.has_weapon = False
        self.last_b = False
        self.crash_tsk = None

    def on_frame(self):
        CarEvent.on_frame(self)
        self.mdt.logic.camera.update_cam()
        self.mdt.audio.update(self._get_input())

    def on_collision(self, obj, obj_name):
        CarEvent.on_collision(self, obj, obj_name)
        if obj != self.mdt.gfx.nodepath.node():
            return
        if obj_name.startswith('Wall'):
            self.__process_wall()
        if any(obj_name.startswith(s) for s in ['Road', 'Offroad']):
            eng.audio.play(self.mdt.audio.landing_sfx)
        if obj_name.startswith('Goal'):
            self.__process_goal()
        if obj_name.startswith('Bonus'):
            self.on_bonus()

    def on_bonus(self):
        if not self.mdt.logic.weapon:
            self.mdt.logic.weapon = Rocket(self.mdt)
            btn = game.options['settings']['keys']['button']
            self.accept(btn, self.on_fire)
            self.has_weapon = True

    def on_fire(self):
        self.ignore(game.options['settings']['keys']['button'])
        self.mdt.logic.fire()
        self.has_weapon = False

    def __process_wall(self):
        eng.audio.play(self.mdt.audio.crash_sfx)
        args = .1, lambda tsk: self.mdt.gfx.crash_sfx(), 'crash sfx'
        self.crash_tsk = taskMgr.doMethodLater(*args)

    def __process_nonstart_goals(self, lap_number, laps):
        curr_lap = min(laps, lap_number)
        self.mdt.gui.lap_txt.setText(str(curr_lap)+'/'+str(laps))
        eng.audio.play(self.mdt.audio.lap_sfx)

    def _process_end_goal(self):
        self.notify('on_end_race')

    def __process_goal(self):
        if self.mdt.logic.last_time_start and not self.mdt.logic.correct_lap:
            return
        self.mdt.logic.reset_waypoints()
        if self.mdt.gui.time_txt.getText():
            lap_time = self.mdt.logic.lap_time
            self.mdt.logic.lap_times += [lap_time]
        lap_number = 1 + len(self.mdt.logic.lap_times)
        not_started = self.mdt.logic.last_time_start
        best_txt = self.mdt.gui.best_txt
        first_lap = not self.mdt.logic.lap_times
        is_best_txt = first_lap or min(self.mdt.logic.lap_times) > lap_time
        if not_started and (first_lap or is_best_txt):
            self.mdt.gui.best_txt.setText(self.mdt.gui.time_txt.getText())
        laps = self.mdt.laps
        if self.mdt.logic.last_time_start:
            self.__process_nonstart_goals(lap_number, laps)
        self.mdt.logic.last_time_start = globalClock.getFrameTime()
        if lap_number == laps + 1:
            self._process_end_goal()

    def _get_input(self):
        if self.mdt.fsm.getCurrentOrNextState() == 'Results':
            return self.mdt.ai.get_input()
        elif not game.options['settings']['joystick']:
            keys = ['forward', 'left', 'reverse', 'right']
            return {key: inputState.isSet(key) for key in keys}
        else:
            x, y, a, b = eng.event.joystick.get_joystick()
            if b and not self.last_b and self.has_weapon:
                self.on_fire()
            return {'forward': y < -.4, 'reverse': y > .4 or a,
                    'left': x < -.4, 'right': x > .4}

    def destroy(self):
        if self.crash_tsk:
            taskMgr.remove(self.crash_tsk)
        map(self.ignore, ['f11', game.options['settings']['keys']['button']])
        CarEvent.destroy(self)


class CarPlayerEventServer(CarPlayerEvent):

    def __init__(self, mdt):
        CarPlayerEvent.__init__(self, mdt)

    def _process_end_goal(self):
        eng.server.send([NetMsgs.end_race])
        CarPlayerEvent._process_end_goal(self)


class CarPlayerEventClient(CarPlayerEvent):

    def __init__(self, mdt):
        CarPlayerEvent.__init__(self, mdt)
        self.last_sent = globalClock.getFrameTime()

    def on_frame(self):
        CarPlayerEvent.on_frame(self)
        pos = self.mdt.gfx.nodepath.getPos()
        hpr = self.mdt.gfx.nodepath.getHpr()
        velocity = self.mdt.phys.vehicle.getChassis().getLinearVelocity()
        packet = list(chain([NetMsgs.player_info], pos, hpr, velocity))
        if globalClock.getFrameTime() - self.last_sent > .2:
            eng.client.send(packet)
            self.last_sent = globalClock.getFrameTime()

    def _process_end_goal(self):
        eng.client.send([NetMsgs.end_race_player])
        CarPlayerEvent._process_end_goal(self)


class CarNetworkEvent(CarEvent):

    def _get_input(self):
        return {key: False for key in ['forward', 'left', 'reverse', 'right']}


class CarAiEvent(CarEvent):

    def _get_input(self):
        return self.mdt.ai.get_input()
