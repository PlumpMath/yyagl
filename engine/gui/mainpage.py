from panda3d.core import TextNode
from direct.gui.OnscreenText import OnscreenText
from .page import Page, PageGui
from .imgbtn import ImageButton


class MainPageGui(PageGui):

    def build_page(self):
        self.__build_social()
        self.__build_version()
        self._set_buttons()
        self.transition_enter()

    def __build_social(self):
        sites = [
            ('facebook', 'http://www.facebook.com/Ya2Tech'),
            ('twitter', 'http://twitter.com/ya2tech'),
            ('google_plus', 'https://plus.google.com/118211180567488443153'),
            ('youtube',
             'http://www.youtube.com/user/ya2games?sub_confirmation=1'),
            ('pinterest', 'http://www.pinterest.com/ya2tech'),
            ('tumblr', 'http://ya2tech.tumblr.com'),
            ('feed', 'http://www.ya2.it/feed-following')]
        self.widgets += [
            ImageButton(
                parent=eng.base.a2dBottomRight,
                scale=.06,
                pos=(-1.0 + i*.15, 1, .1),
                frameColor=(1, 1, 1, 1),
                frameTexture=self.menu.gui.menu_args.social_path % site[0],
                command=eng.gui.open_browser,
                extraArgs=[site[1]],
                **self.menu.gui.imgbtn_args)
            for i, site in enumerate(sites)]

    def __build_version(self):
        self.widgets += [OnscreenText(
            text=_('version: ') + eng.logic.version,
            parent=eng.base.a2dBottomLeft, pos=(.02, .02), scale=.04,
            fg=(.8, .8, .8, 1), align=TextNode.ALeft,
            font=self.menu.gui.menu_args.font)]


class MainPage(Page):
    gui_cls = MainPageGui
