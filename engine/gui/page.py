from inspect import getmro
from panda3d.core import LPoint3f
from direct.gui.DirectButton import DirectButton
from direct.interval.LerpInterval import LerpPosInterval
from direct.interval.MetaInterval import Sequence
from direct.interval.FunctionInterval import Wait, Func
from direct.gui.DirectGuiGlobals import ENTER, EXIT, DISABLED
from direct.gui.DirectOptionMenu import DirectOptionMenu
from direct.gui.DirectCheckButton import DirectCheckButton
from direct.gui.DirectSlider import DirectSlider
from direct.gui.DirectEntry import DirectEntry
from ...gameobject import GameObject, Gui, Event
from .imgbtn import ImageButton
from .widget import Widget


class PageGui(Gui):

    def __init__(self, mdt, menu):
        # don't pass the menu
        Gui.__init__(self, mdt)
        self.menu = menu
        self.widgets = []
        # infer widgets: attach widgets to page's root nodes (center and
        # corners) and detect them with getChildren()
        self.build_page()
        self.update_texts()
        self.curr_wdg = self.get_next_widget((-.1, 0, -1), (-3.6, 1, 1))
        if self.curr_wdg:
            self.curr_wdg.on_wdg_enter()

    def build_page(self, back_btn=True):
        if back_btn:
            self.__build_back_btn()
        self._set_buttons()
        self.transition_enter()
        eng.cursor_top()

    def add_widget(self, wdg):
        self.widgets += [wdg]

    def on_arrow(self, direction):
        if not self.curr_wdg:
            return
        if not self.curr_wdg.on_arrow(direction):
            next_wdg = self.get_next_widget(direction)
            if next_wdg:
                self.curr_wdg.on_wdg_exit()
                self.curr_wdg = next_wdg
                self.curr_wdg.on_wdg_enter()

    def on_enter(self):
        if not self.curr_wdg:
            return
        if self.curr_wdg.on_enter():
            self.enable()

    def __get_dot(self, wdg, direction, start=None):
        start_pos = start if start else self.curr_wdg.get_pos(aspect2d)
        vec = wdg.get_pos(aspect2d) - start_pos
        vec.normalize()
        return vec.dot(direction)

    def __next_factor(self, wdg, direction, start=None):
        start_pos = start if start else self.curr_wdg.get_pos(aspect2d)
        dot = self.__get_dot(wdg, direction, start)
        wdg_pos = wdg.get_pos(aspect2d)
        if wdg.__class__ == DirectSlider:
            wdg_pos = LPoint3f(wdg_pos[0], 1, wdg_pos[2])
        if direction in [(-1, 0, 0), (1, 0, 0)]:
            proj_dist = abs(wdg_pos[0] - start_pos[0])
        else:
            proj_dist = abs(wdg_pos[2] - start_pos[2])
        if direction in [(-1, 0, 0), (1, 0, 0)]:
            weights = [.5, .5]
        else:
            weights = [.1, .9]
        return weights[0] * (dot * dot) + weights[1] * (1 - proj_dist)

    def get_next_widget(self, direction, start=None):
        clss = [DirectButton, DirectCheckButton, DirectSlider,
                DirectOptionMenu, ImageButton, DirectEntry]
        inter = lambda wdg: any(pcl in clss for pcl in getmro(wdg.__class__))
        wdgs = [wdg for wdg in self.widgets if inter(wdg)]
        wdgs = filter(lambda wdg: wdg['state'] != DISABLED, wdgs)
        if hasattr(self, 'curr_wdg') and self.curr_wdg:
            wdgs.remove(self.curr_wdg)
        pos_dot = lambda wdg: self.__get_dot(wdg, direction, start) > .1
        wdgs = filter(pos_dot, wdgs)
        if not wdgs:
            return
        n_f = lambda wdg: self.__next_factor(wdg, direction, start)
        return max(wdgs, key=n_f)

    def _set_buttons(self):
        for wdg in self.widgets:
            cname = wdg.__class__.__name__ + 'Widget'
            wdg.__class__ = type(cname, (wdg.__class__, Widget), {})
            wdg.init(wdg)
            if hasattr(wdg, 'bind'):
                wdg.bind(ENTER, wdg.on_wdg_enter)
                wdg.bind(EXIT, wdg.on_wdg_exit)

    def transition_enter(self):
        self.update_texts()
        for wdg in self.widgets:
            pos = wdg.get_pos()
            start_pos = (pos[0] - 3.6, pos[1], pos[2])
            wdg.set_pos(start_pos)
            Sequence(
                Wait(abs(pos[2] - 1) / 4),
                LerpPosInterval(wdg, .5, pos, blendType='easeInOut')
            ).start()
        self.enable()

    def enable(self):
        self.mdt.event.accept('arrow_left-up', self.on_arrow, [(-1, 0, 0)])
        self.mdt.event.accept('arrow_right-up', self.on_arrow, [(1, 0, 0)])
        self.mdt.event.accept('arrow_up-up', self.on_arrow, [(0, 0, 1)])
        self.mdt.event.accept('arrow_down-up', self.on_arrow, [(0, 0, -1)])
        self.mdt.event.accept('enter-up', self.on_enter)

    def transition_exit(self, destroy=True):
        for wdg in self.widgets:
            pos = wdg.get_pos()
            end_pos = (pos[0] + 3.6, pos[1], pos[2])
            seq = Sequence(
                Wait(abs(pos[2] - 1) / 4),
                LerpPosInterval(wdg, .5, end_pos, blendType='easeInOut'),
                Func(wdg.destroy if destroy else wdg.hide))
            if not destroy:
                seq.append(Func(wdg.set_pos, pos))
            seq.start()

    @staticmethod
    def transl_text(obj, text_src, text_transl):
        obj.__text_src = text_src
        obj.__class__.transl_text = property(lambda self: _(self.__text_src))

    def update_texts(self):
        tr_wdg = [wdg for wdg in self.widgets if hasattr(wdg, 'transl_text')]
        for wdg in tr_wdg:
            wdg['text'] = wdg.transl_text

    def __build_back_btn(self):
        self.widgets += [DirectButton(
            text='', pos=(0, 1, -.8), command=self.__on_back,
            **self.menu.gui.btn_args)]
        PageGui.transl_text(self.widgets[-1], 'Back', _('Back'))
        self.widgets[-1]['text'] = self.widgets[-1].transl_text

    def __on_back(self):
        self.mdt.event.on_back()
        self.notify('on_back')

    def show(self):
        map(lambda wdg: wdg.show(), self.widgets)
        self.transition_enter()

    def hide(self):
        self.transition_exit(False)
        self.mdt.event.ignoreAll()

    def destroy(self):
        self.menu = None
        self.transition_exit()


class PageEvent(Event):

    def on_back(self):
        pass


class Page(GameObject):
    gui_cls = PageGui
    event_cls = PageEvent

    def __init__(self, menu):
        self.menu = menu
        GameObject.__init__(self, self.init_lst)

    @property
    def init_lst(self):
        return [
            [('event', self.event_cls, [self])],
            [('gui', self.gui_cls, [self, self.menu])]]
