# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""Build the minimal bundled ImageMagick encoder in an explicit workspace.

See ENCODER_BUILD.md for the pinned inputs and preparation steps. No system
installation is performed. The bundle is staged for review, never installed
into a working ComicRack plugin automatically. --resume reuses this workspace.
"""
from pathlib import Path
import ctypes
import os
import subprocess
import time
import re
import json

import argparse
import hashlib
import sys
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--workspace', type=Path, required=True)
parser.add_argument('--resume', action='store_true', help='Reuse configured dependencies and sources for an incremental build')
args = parser.parse_args()
long_root = args.workspace.resolve()
manifest = json.loads(Path(__file__).with_name('encoder_sources.json').read_text())
for item in manifest['inputs']:
    path = long_root / item['name']
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        raise SystemExit('Missing/mismatched input: ' + item['name'] + '. See ENCODER_BUILD.md.')
buf = ctypes.create_unicode_buffer(32768)
ctypes.windll.kernel32.GetShortPathNameW(str(long_root), buf, len(buf))
root = Path(buf.value)
if not buf.value or any(c.isspace() for c in str(root)):
    raise SystemExit('A Windows workspace with usable short paths is required by the Autoconf build.')
tools = root / 'toolchain/w64devkit/bin'
prefix = root / 'prefix'
env = os.environ.copy()
env['PATH'] = os.pathsep.join([str(tools), str(root / 'toolchain/nasm-3.01'), r'C:\Program Files\CMake\bin', r'C:\Windows\System32', r'C:\Windows'])
env['CC'], env['CXX'] = 'gcc', 'g++'
env['PATH_SEPARATOR'] = ';'
env['AR'] = (tools / 'ar.exe').as_posix()
env['RANLIB'] = (tools / 'ranlib.exe').as_posix()
env['WinPathScript'] = (tools / 'sh.exe').as_posix() + ' ' + (root / 'sources/ImageMagick-7.1.2-34/winpath.sh').as_posix()
(root / 'tmp').mkdir(exist_ok=True)
env['TMPDIR'] = (root / 'tmp').as_posix()
env['CONFIG_SHELL'] = (tools / 'sh.exe').as_posix()
env['PKG_CONFIG_PATH'] = (prefix / 'lib/pkgconfig').as_posix()
env['CFLAGS'] = '-O2 -fno-ident'
env['CXXFLAGS'] = env['CFLAGS']
env['CPPFLAGS'] = '-I' + (prefix / 'include').as_posix()
env['LDFLAGS'] = '-L' + (prefix / 'lib').as_posix() + ' -static -static-libgcc'


def run(label, command, cwd=root, environment=None):
    print(label, flush=True)
    path = root / (label + '.log')
    with path.open('w', encoding='utf-8') as out:
        result = subprocess.run(command, cwd=cwd, env=environment or env, stdout=out, stderr=subprocess.STDOUT)
    if result.returncode:
        print(path.read_text(encoding='utf-8', errors='replace')[-6000:], flush=True)
        raise SystemExit(result.returncode)


# [E01] Static codec libraries; no optional GPL Little CMS plugins.
if not args.resume:
    for name, extra in [
        ('libjpeg-turbo-3.2.0', ['-DENABLE_SHARED=OFF', '-DENABLE_STATIC=ON', '-DWITH_TURBOJPEG=OFF', '-DWITH_SIMD=ON']),
        ('libwebp-1.6.0', ['-DBUILD_SHARED_LIBS=OFF', '-DWEBP_LINK_STATIC=ON'] + ['-DWEBP_BUILD_' + key + '=OFF' for key in ['ANIM_UTILS', 'CWEBP', 'DWEBP', 'GIF2WEBP', 'IMG2WEBP', 'VWEBP', 'WEBPINFO', 'WEBPMUX', 'EXTRAS']]),
        ('lcms2-2.19.1', ['-DBUILD_SHARED_LIBS=OFF', '-DLCMS2_WITH_FASTFLOAT=OFF', '-DLCMS2_WITH_THREADED_PLUGIN=OFF', '-DLCMS2_BUILD_SHARED=OFF', '-DLCMS2_BUILD_STATIC=ON', '-DLCMS2_BUILD_TOOLS=OFF', '-DLCMS2_BUILD_TESTS=OFF']),
    ]:
        source, build = root / 'sources' / name, root / 'build2' / name
        command = ['cmake', '-S', source.as_posix(), '-B', build.as_posix(), '-G', 'MinGW Makefiles', '-DCMAKE_MAKE_PROGRAM=' + (tools / 'make.exe').as_posix(), '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_INSTALL_PREFIX=' + prefix.as_posix(), '-DCMAKE_C_COMPILER=' + (tools / 'gcc.exe').as_posix(), '-DCMAKE_CXX_COMPILER=' + (tools / 'g++.exe').as_posix()]
        run(name + '-configure', command + extra)
        run(name + '-build', ['cmake', '--build', str(build), '-j', '8'])
        run(name + '-install', ['cmake', '--install', str(build)])

# CMake canonicalizes the install path; normalize generated .pc prefixes for
# Autoconf/pkg-config under this short-path workspace. No upstream source edits.
for pc in (prefix / 'lib/pkgconfig').glob('*.pc'):
    text = pc.read_text().replace((long_root / 'prefix').as_posix(), prefix.as_posix())
    import re
    pc.write_text(re.sub(r'^prefix=.*$', 'prefix=' + prefix.as_posix(), text, flags=re.M))
import shutil
shutil.copyfile(prefix / 'lib/liblcms2_static.a', prefix / 'lib/liblcms2.a')
source = root / 'sources/ImageMagick-7.1.2-34'
excluded = ['autotrace', 'bzlib', 'djvu', 'dps', 'fftw', 'fontconfig', 'fpx', 'freetype', 'gslib', 'gvc', 'heic', 'jbig', 'jxl', 'lqr', 'lzma', 'openexr', 'openjp2', 'pango', 'perl', 'png', 'raqm', 'raw', 'rsvg', 'tiff', 'uhdr', 'wmf', 'x', 'xml', 'zip', 'zlib', 'zstd']
magickenv = env.copy()
magickenv['PATH'] = r'C:\Program Files\Git\usr\bin' + os.pathsep + env['PATH']
magickenv['PATH_SEPARATOR'] = ':'
magickenv['CONFIG_SHELL'] = 'C:/PROGRA~1/Git/bin/bash.exe'
magickenv['PKG_CONFIG'] = (tools / 'pkg-config.exe').as_posix() + ' --static'
magickenv.pop('WinPathScript', None)
command = ['C:/PROGRA~1/Git/bin/bash.exe', './configure', '--build=x86_64-w64-mingw32', '--host=x86_64-w64-mingw32', '--prefix=/c/WebPOptimizerEncoder', '--enable-zero-configuration', '--with-gcc-arch=x86-64', '--disable-shared', '--enable-static', '--disable-openmp', '--disable-hdri', '--with-quantum-depth=8', '--without-magick-plus-plus', '--without-modules', '--with-jpeg=yes', '--with-webp=yes', '--with-lcms=yes']
command += ['--without-' + key for key in excluded]
# [E02] Minimal, embedded configuration; neutral install prefix is never installed.
if not args.resume:
    run('magick-configure', command, source, magickenv)
# The upstream MinGW path converter attempts to convert already-Windows
# installation paths twice under Git Bash. Normalize generated string macros;
# no encoder/codec source or algorithm is modified. Zero-configuration embeds
# defaults and does not load configuration from these neutral build paths.
for generated in ['config/config.h', 'MagickCore/magick-baseconfig.h']:
    import json
    header = source / generated
    lines = []
    for line in header.read_text().splitlines():
        if 'is not mounted' in line:
            found = re.search(r'path "([^"\n]*)" is not mounted', line)
            assert found, line
            line = ' '.join(line.split()[:2]) + ' ' + json.dumps(found.group(1) if found.group(1).startswith('C:/') else '')
        lines.append(line)
    header.write_text('\n'.join(lines) + '\n')
# Generate the embedded threshold map directly: native make/sed quoting on
# Windows otherwise turns escaped newlines into literal newlines in C strings.
xml = (source / 'config/thresholds.xml').read_text(encoding='utf-8')
(source / 'MagickCore/threshold-map.h').write_text('static const char *const\n  BuiltinMap=\n' + '\n'.join('    ' + json.dumps(line + '\n') for line in xml.splitlines()) + ';\n', encoding='utf-8')
# [E03] Native Windows libtool can truncate archive member lists; build
# objects/library targets first, then verify the complete core archive using
# an ar response file. Link explicitly so all static codec dependencies remain.
run('magick-objects', [(tools / 'make.exe').as_posix(), '-j8', 'MagickCore/libMagickCore-7.Q8.la', 'MagickWand/libMagickWand-7.Q8.la'], source, magickenv)
objects = list((source / 'MagickCore').glob('*.o')) + list((source / 'coders').glob('*.o')) + list((source / 'filters').glob('*.o'))
response = root / 'core-objects.rsp'
response.write_text('\n'.join('"' + p.as_posix() + '"' for p in objects))
archive = source / 'MagickCore/.libs/libMagickCore-7.Q8.a'
run('magick-core-archive', [str(tools / 'ar.exe'), 'rcs', str(archive), '@' + str(response)])
listing = subprocess.run([str(tools / 'ar.exe'), 't', str(archive)], capture_output=True, text=True, check=True).stdout.splitlines()
assert len(listing) == len(objects), 'Incomplete static archive'
link = [str(tools / 'g++.exe'), '-O2', '-static', '-static-libgcc', '-static-libstdc++', '-municode', '-pthread', '-o', str(source / 'utilities/magick.exe'), str(source / 'utilities/magick.o'), '-Wl,--start-group', str(archive), str(source / 'MagickWand/.libs/libMagickWand-7.Q8.a'), '-L' + str(prefix / 'lib'), '-llcms2', '-ljpeg', '-lwebpmux', '-lwebpdemux', '-lwebp', '-lsharpyuv', '-Wl,--end-group', '-lgdi32', '-luser32', '-lurlmon', '-lm']
run('magick-link', link, source)
run('magick-strip', [str(tools / 'strip.exe'), '--strip-all', str(source / 'utilities/magick.exe')])

# [E04] Stage binary, unmodified licenses and provenance; no live plugin writes.
from package_encoder import stage_bundle
stage_bundle(long_root)
