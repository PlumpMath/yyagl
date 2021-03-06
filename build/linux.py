from os import remove, system, makedirs, walk
from os.path import basename, dirname, realpath, exists, abspath
from shutil import move, rmtree, copytree, copy
from .build import ver, bld_dpath, branch, InsideDir, size, \
    bld_cmd
from .deployng import bld_ng


def bld_linux(target, source, env):
    if env['NG']:
        bld_ng(env['APPNAME'], linux_64=True)
        return
    ico_fpath = env['ICO_FPATH']
    nointernet = '-s' if env['NOINTERNET'] else ''
    int_str = '-nointernet' if env['NOINTERNET'] else ''
    p3d_fpath = env['P3D_PATH'][:-4] + 'nopygame.p3d'
    cmd = bld_cmd.format(
        dst_dir=bld_dpath, appname=env['APPNAME'], AppName=env['APPNAME'].capitalize(),
        version=ver, p3d_fpath=p3d_fpath, platform='linux_' + env['PLATFORM'],
        nointernet=nointernet)
    system(cmd)
    start_dir = abspath('.') + '/'
    with InsideDir(bld_dpath + 'linux_' + env['PLATFORM']):
        __prepare(start_dir, env['PLATFORM'])
        __bld(env['APPNAME'], start_dir, env['PLATFORM'], ico_fpath)
        if nointernet:
            __bld_full_pkg(env['APPNAME'], env['PLATFORM'], ico_fpath, p3d_fpath,
                           nointernet)
        __bld_pckgs(env['APPNAME'], env['PLATFORM'], int_str)
    rmtree(bld_dpath + 'linux_' + env['PLATFORM'])


def __prepare(start_path, platform):
    makedirs('img/data')
    curr_path = dirname(realpath(__file__)) + '/'
    copytree(curr_path + 'mojosetup/meta', 'img/meta')
    copytree(curr_path + 'mojosetup/scripts', 'img/scripts')
    copytree(curr_path + '../licenses', 'img/data/licenses')
    copy(start_path + 'license.txt', 'img/data/license.txt')
    copy(curr_path + 'mojosetup/mojosetup_' + platform, '.')
    if not exists(curr_path + 'mojosetup/guis'):
        return
    makedirs('img/guis')
    libfpath = curr_path + 'mojosetup/guis/%s/libmojosetupgui_gtkplus2.so'
    dst_dpath = 'img/guis/libmojosetupgui_gtkplus2.so'
    copy(start_path + libfpath % platform, dst_dpath)


def __bld(appname, start_path, platform, ico_fpath):
    arch = {'i386': 'i686', 'amd64': 'x86_64'}
    tmpl = 'tar -zxvf %s-%s-1-%s.pkg.tar.gz'
    system(tmpl % (appname, ver, arch[platform]))
    remove('.PKGINFO')
    move('usr/bin/' + appname, 'img/data/' + appname)
    copy(start_path + ico_fpath % '48', 'img/data/icon.png')
    seds = ['version', 'size', 'appname', 'AppName', 'vendorsite']
    seds = ' '.join(["-e 's/<%s>/{%s}/'" % (sed, sed) for sed in seds])
    tmpl = 'sed -i.bak %s img/scripts/config.lua' % seds
    cmd = tmpl.format(version=branch, size=size('img'),
                          appname=appname, AppName=appname.capitalize(),
                          vendorsite='ya2.it')
    system(cmd)


def __bld_full_pkg(appname, platform, ico_fpath, p3d_fpath, nointernet):
    copytree('usr/lib/' + appname, 'img/data/lib')
    copytree('../../assets', 'img/data/assets')
    copytree('../../yyagl/assets', 'img/data/yyagl/assets')
    for root, _, fnames in walk('img/data/assets'):
        for fname in fnames:
            fpath = root + '/' + fname
            rm_ext = ['psd', 'po', 'pot', 'egg']
            if any(fpath.endswith('.' + ext) for ext in rm_ext):
                remove(fpath)
            rm_ext = ['png', 'jpg']
            if 'assets/models/' in fpath and any(fpath.endswith('.' + ext) for ext in rm_ext):
                remove(fpath)
            if 'assets/models/tracks/' in fpath and \
                    fpath.endswith('.bam') and not \
                    any(fpath.endswith(concl + '.bam')
                        for concl in ['/track_all', '/collision', 'Anim']):
                remove(fpath)
    tmpl = 'pdeploy -o  . {nointernet} -t host_dir=./lib ' + \
        '-t verify_contents=never -n {appname} -N {AppName} -v {version} ' + \
        '-a ya2.it -A "Ya2" -l "GPLv3" -L license.txt -e flavio@ya2.it ' + \
        '-t width=800 -t height=600 -P {platform} {icons} ../{p3d_fpath} ' + \
        'standalone'
    dims = ['16', '32', '48', '128', '256']
    ico_str = ''.join(["-i '" + ico_fpath % dim + "' " for dim in dims])
    cmd = tmpl.format(
        path=bld_dpath, appname=appname, AppName=appname.capitalize(), version=ver,
        p3d_fpath=basename(p3d_fpath), platform='linux_'+platform,
        nointernet=nointernet, icons=ico_str)
    system(cmd)
    move('linux_' + platform + '/' + appname, 'img/data/' + appname)


def __bld_pckgs(appname, platform, int_str):
    with InsideDir('img'):
        system('zip -9r ../pdata.zip *')
    system('cat pdata.zip >> ./mojosetup_' + platform)
    fdst = '%s-%s%s-linux_%s' % (appname, branch, int_str, platform)
    move('mojosetup_' + platform, fdst)
    system('chmod +x %s-%s%s-linux_%s' % (appname, branch, int_str, platform))
    fsrc = '%s-%s%s-linux_%s' % (appname, branch, int_str, platform)
    move(fsrc, '../%s-%s%s-linux_%s' % (appname, branch, int_str, platform))
