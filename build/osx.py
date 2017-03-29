from os import system
from shutil import rmtree
from .build import ver, path, ver_branch, bld_cmd


def build_osx(target, source, env):
    nointernet = '-s' if env['NOINTERNET'] else ''
    int_str = '-nointernet' if env['NOINTERNET'] else ''
    build_command = bld_cmd(env['SUPERMIRROR']).format(
        path=path, name=env['NAME'], Name=env['NAME'].capitalize(),
        version=ver, p3d_path=env['P3D_PATH'][:-4] + 'nopygame.p3d',
        platform='osx_i386', nointernet=nointernet)
    system(build_command)
    osx_path = '{Name}.app'
    osx_tgt = '{name}-{version}{int_str}-osx.zip'
    osx_cmd_tmpl = 'cd ' + path + 'osx_i386 && zip -r ../' + osx_tgt + ' ' + \
        osx_path + ' && cd ../..'
    osx_cmd = osx_cmd_tmpl.format(
        Name=env['NAME'].capitalize(), name=env['NAME'], version=ver_branch,
        int_str=int_str)
    system(osx_cmd)
    rmtree('%sosx_i386' % path)
