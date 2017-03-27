from os.path import exists
from panda3d.core import AmbientLight, BitMask32, Spotlight, NodePath, \
    OmniBoundingVolume
from direct.actor.Actor import Actor
from yyagl.gameobject import Gfx
from .signs import Signs


class TrackGfxProps(object):

    def __init__(
            self, name, path, model_name, empty_name, anim_name, omni_tag,
            shaders, thanks, sign_name, shadow_src):
        self.name = name
        self.path = path
        self.model_name = model_name
        self.empty_name = empty_name
        self.anim_name = anim_name
        self.omni_tag = omni_tag
        self.shaders = shaders
        self.thanks = thanks
        self.sign_name = sign_name
        self.shadow_src = shadow_src


class TrackGfx(Gfx):

    def __init__(
            self, mdt, trackgfx_props):
        self.ambient_np = None
        self.spot_lgt = None
        self.model = None
        self.loaders = []
        self.__actors = []
        self.__flat_roots = {}
        self.has_flattened = False
        self.props = trackgfx_props
        Gfx.__init__(self, mdt)

    def async_build(self):
        self.__set_model()
        self.__set_light()

    def __set_model(self):
        eng.log('loading track model')
        time = globalClock.getFrameTime()
        filename = self.props.name + '_' + eng.version + '.bam'
        if exists(filename):
            eng.log('loading ' + filename)
            eng.load_model(filename, callback=self.end_loading)
        else:
            path = self.props.path + '/' + self.props.model_name
            s_m = self.__set_submod
            eng.load_model(path, callback=s_m, extra_args=[time])

    def __set_submod(self, model, time):
        d_t = round(globalClock.getFrameTime() - time, 2)
        eng.log('loaded track model (%s seconds)' % str(d_t))
        self.model = model
        for submodel in self.model.getChildren():
            self.__flat_sm(submodel)
        self.model.hide(BitMask32.bit(0))
        self.__load_empties()

    def __flat_sm(self, submodel):
        s_n = submodel.getName()
        if not s_n.startswith(self.props.empty_name):
            submodel.flattenLight()

    def __load_empties(self):
        eng.log('loading track submodels')
        empty_name = '**/%s*' % self.props.empty_name
        self.empty_models = self.model.findAllMatches(empty_name)

        def load_models():
            self.__process_models(list(self.empty_models))
        e_m = self.empty_models
        names = [model.getName().split('.')[0][5:] for model in e_m]
        self.__preload_models(list(set(list(names))), load_models)

    def __preload_models(self, models, callback, model='', time=0):
        curr_t = globalClock.getFrameTime()
        d_t = curr_t - time
        if model:
            eng.log('loaded model: %s (%s seconds)' % (model, d_t))
        if not models:
            callback()
            return
        model = models.pop(0)
        path = self.props.path + '/' + model
        if model.endswith(self.props.anim_name):
            anim_path = '%s-%s' % (path, self.props.anim_name)
            self.__actors += [Actor(path, {'anim': anim_path})]
            self.__preload_models(models, callback, model, curr_t)
        else:
            def p_l(model):
                self.__preload_models(models, callback, model, curr_t)
            loader.loadModel(path, callback=p_l)

    def __process_models(self, models):
        empty_name = self.props.empty_name
        for model in models:
            model_name = model.getName().split('.')[0][len(empty_name):]
            if not model_name.endswith(self.props.anim_name):
                self.__process_static(model)
        self.flattening()

    def __process_static(self, model):
        empty_name = self.props.empty_name
        model_name = model.getName().split('.')[0][len(empty_name):]
        if model_name not in self.__flat_roots:
            flat_root = self.model.attachNewNode(model_name)
            self.__flat_roots[model_name] = flat_root
        model_subname = model.getName().split('.')[0][len(empty_name):]
        path = '%s/%s' % (self.props.path, model_subname)
        loader.loadModel(path).reparent_to(model)
        left, right, top, bottom = self.mdt.phys.lrtb
        model.reparentTo(self.__flat_roots[model_name])

    def flattening(self):
        eng.log('track flattening')
        flat_cores = 1  # max(1, multiprocessing.cpu_count() / 2)
        eng.log('flattening using %s cores' % flat_cores)
        self.in_loading = []
        self.models_to_load = self.__flat_roots.values()
        for i in range(flat_cores):
            self.__flat_models()
        self.end_loading()

    def __flat_models(self, model='', time=0, nodes=0):
        if model:
            str_tmpl = 'flattened model: %s (%s seconds, %s nodes)'
            self.in_loading.remove(model)
            d_t = round(globalClock.getFrameTime() - time, 2)
            eng.log(str_tmpl % (model, d_t, nodes))
        if self.models_to_load:
            mod = self.models_to_load.pop()
            self.__process_flat_models(mod, self.end_flattening)
        elif not self.in_loading:
            self.end_flattening()

    def __process_flat_models(self, mod, callback):
        curr_t = globalClock.getFrameTime()
        node = mod
        node.clearModelNodes()

        def process_flat(flatten_node, orig_node, model, time, nodes,
                         remove=True):
            flatten_node.reparent_to(orig_node.get_parent())
            if remove:
                orig_node.remove_node()  # remove 1.9.3
            self.__flat_models(model, time, nodes)
        nname = node.get_name()
        self.in_loading += [nname]
        loa = loader.asyncFlattenStrong(
            node, callback=process_flat, inPlace=False,
            extraArgs=[node, nname, curr_t, len(node.get_children())])
        self.loaders += [loa]

    def end_loading(self, model=None):
        if model:
            self.model = model
        anim_name = '**/%s*%s*' % (self.props.empty_name, self.props.anim_name)
        for model in self.model.findAllMatches(anim_name):
            # bam files don't contain actor info
            new_root = NodePath(model.get_name())
            new_root.reparent_to(model.get_parent())
            new_root.set_pos(model.get_pos())
            new_root.set_hpr(model.get_hpr())
            new_root.set_scale(model.get_scale())
            model_subname = model.get_name()[len(self.props.empty_name):]
            path = '%s/%s' % (self.props.path, model_subname)
            if '.' in path:
                path = path.split('.')[0]
            anim_path = '%s-%s' % (path, self.props.anim_name)
            self.__actors += [Actor(path, {'anim': anim_path})]
            self.__actors[-1].loop('anim')
            self.__actors[-1].setPlayRate(.5, 'anim')
            self.__actors[-1].reparent_to(new_root)
            has_omni = model.has_tag(self.props.omni_tag)
            if has_omni and model.get_tag(self.props.omni_tag):
                new_root.set_tag(self.props.omni_tag, 'True')
                a_n = self.__actors[-1].get_name()
                eng.log('set omni for ' + a_n)
                self.__actors[-1].node().setBounds(OmniBoundingVolume())
                self.__actors[-1].node().setFinal(True)
            model.remove_node()
        self.signs = Signs(self.model, self.props.sign_name, self.props.thanks)
        self.signs.set_signs()
        self.model.prepareScene(eng.base.win.getGsg())
        Gfx.async_build(self)

    def end_flattening(self, model=None):
        self.has_flattened = True

    def __set_light(self):
        if self.props.shaders:
            eng.set_amb_lgt((.15, .15, .15, 1))
            eng.set_dir_lgt((.8, .8, .8, 1), (-25, -65, 0))
            return
        ambient_lgt = AmbientLight('ambient light')
        ambient_lgt.setColor((.7, .7, .55, 1))
        self.ambient_np = render.attachNewNode(ambient_lgt)
        render.setLight(self.ambient_np)

        self.spot_lgt = render.attachNewNode(Spotlight('Spot'))
        self.spot_lgt.node().setScene(render)
        self.spot_lgt.node().setShadowCaster(True, 1024, 1024)
        self.spot_lgt.node().getLens().setFov(40)
        self.spot_lgt.node().getLens().setNearFar(20, 200)
        self.spot_lgt.node().setCameraMask(BitMask32.bit(0))
        self.spot_lgt.setPos(*self.props.shadow_src)
        self.spot_lgt.lookAt(0, 0, 0)
        render.setLight(self.spot_lgt)
        render.setShaderAuto()

    def destroy(self):
        if self.has_flattened:
            filename = self.props.name + '_' + eng.version + '.bam'
            if not exists(filename):
                eng.log('writing ' + filename)
                self.model.writeBamFile(filename)
        self.model.removeNode()
        if not self.props.shaders:
            render.clearLight(self.ambient_np)
            render.clearLight(self.spot_lgt)
            self.ambient_np.removeNode()
            self.spot_lgt.removeNode()
        else:
            eng.clear_lights()
        self.__actors = self.__flat_roots = None
        self.signs.destroy()
        self.empty_models = None
        map(loader.cancelRequest, self.loaders)
