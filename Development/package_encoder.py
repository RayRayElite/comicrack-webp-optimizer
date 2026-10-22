# Copyright (c) 2026 RayRayElite
# SPDX-License-Identifier: MIT
"""Stage the reviewed encoder with its actual licenses and build provenance."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

from inspect_pe import imports

SYSTEM_DLLS = {'advapi32.dll', 'gdi32.dll', 'kernel32.dll', 'msvcrt.dll', 'urlmon.dll', 'user32.dll'}
LICENSE_FILES = [
    ('sources/ImageMagick-7.1.2-34/LICENSE', 'magick_License.txt'),
    ('sources/ImageMagick-7.1.2-34/NOTICE', 'NOTICE.txt'),
    ('sources/libjpeg-turbo-3.2.0/LICENSE.md', 'licenses/libjpeg-turbo-LICENSE.md'),
    ('sources/libjpeg-turbo-3.2.0/README.ijg', 'licenses/libjpeg-turbo-README.ijg'),
    ('sources/libwebp-1.6.0/COPYING', 'licenses/libwebp-COPYING.txt'),
    ('sources/libwebp-1.6.0/PATENTS', 'licenses/libwebp-PATENTS.txt'),
    ('sources/libwebp-1.6.0/AUTHORS', 'licenses/libwebp-AUTHORS.txt'),
    ('sources/lcms2-2.19.1/LICENSE', 'licenses/lcms2-LICENSE.txt'),
    ('toolchain/w64devkit/COPYING.MinGW-w64-runtime.txt', 'licenses/MinGW-w64-runtime.txt'),
    ('GCC-COPYING.RUNTIME', 'licenses/GCC-RUNTIME-EXCEPTION.txt'),
    ('GCC-COPYING3', 'licenses/GCC-GPL-3.0.txt'),
    ('LGPL-2.1.txt', 'licenses/LGPL-2.1.txt'),
]


def stage_bundle(workspace):
    workspace = Path(workspace).resolve()
    source = workspace / 'sources/ImageMagick-7.1.2-34/utilities/magick.exe'
    binary = source.read_bytes()
    dependencies = imports(source)
    assert dependencies['architecture'] == 'x64'
    assert set(dependencies['dlls']) <= SYSTEM_DLLS, dependencies
    assert not any(token in binary for token in [b'Users/me', b'Users\\me', b'COMICR~1', b'ComicRack Community Edition'])
    cache = (workspace / 'build2/lcms2-2.19.1/CMakeCache.txt').read_text()
    for option in ['LCMS2_WITH_FASTFLOAT', 'LCMS2_WITH_THREADED_PLUGIN']:
        assert option + ':BOOL=OFF' in cache
    configuration = (workspace / 'sources/ImageMagick-7.1.2-34/config/config.h').read_text()
    for option in ['JPEG_DELEGATE', 'LCMS_DELEGATE', 'WEBP_DELEGATE', 'ZERO_CONFIGURATION_SUPPORT']:
        assert '#define ' + option + ' 1' in configuration
    assert '#define OPENMP_SUPPORT 1' not in configuration
    stage = workspace / 'bundle/Magick'
    stage.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, stage / 'magick.exe')
    for original, target in LICENSE_FILES:
        destination = stage / target
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(workspace / original, destination)
    inputs = json.loads(Path(__file__).with_name('encoder_sources.json').read_text())['inputs']
    for item in inputs:
        assert hashlib.sha256((workspace / item['name']).read_bytes()).hexdigest() == item['sha256']
    version = subprocess.run([str(source), '-version'], capture_output=True, text=True, check=True).stdout
    info = {'name': 'ImageMagick minimal Q8 encoder', 'version': '7.1.2-34',
            'architecture': 'Windows x64', 'binary_sha256': hashlib.sha256(binary).hexdigest(),
            'binary_bytes': len(binary), 'dll_imports': dependencies['dlls'], 'version_output': version,
            'compiled_dependencies': ['libjpeg-turbo 3.2.0', 'libwebp/libsharpyuv 1.6.0', 'Little CMS 2.19.1', 'MinGW-w64 runtime 14.0.0', 'GCC runtime 16.2.0'],
            'compiler': 'w64devkit 2.10.1, GCC 16.2.0; NASM 3.01 for JPEG SIMD',
            'configuration': 'Q8; static; no HDRI/OpenMP/modules/Magick++; embedded configuration; optional external delegates disabled',
            'source_changes': 'No encoder/codec C or C++ algorithm changes. Generated .pc paths and configuration path macros normalized; embedded threshold header generated with escaped C strings; core archive verified using a response file; explicit static link and symbol stripping.',
            'rebuild_recipe': 'Development/ENCODER_BUILD.md and Development/build_encoder.py in the source repository',
            'inputs': inputs,
            'license_files': {target: hashlib.sha256((stage / target).read_bytes()).hexdigest() for _, target in LICENSE_FILES}}
    (stage / 'build-info.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
    (stage / 'BUILD.md').write_text('''# Bundled encoder

This is a custom minimal **ImageMagick 7.1.2-34 Q8 Windows x64** build for WebP Optimizer, compiled from the pinned upstream sources listed in build-info.json. It is not an official upstream binary and is not endorsed by ImageMagick Studio LLC. The plugin's own MIT license does not relicense these components.

It statically links JPEG, WebP and Little CMS color management. No separate Visual C++/OpenMP or codec DLLs are bundled or imported. Windows supplies the system DLLs listed in build-info.json, including MSVCRT.dll; do not copy operating-system DLLs into this folder. Ghostscript and other external format tools are not bundled. The version banner's Windows Ghostscript capability indicates a runtime loader, not a linked/bundled Ghostscript library.

## Attribution and licenses

- ImageMagick Studio LLC and contributors: magick_License.txt and NOTICE.txt, preserved from the source distribution.
- libjpeg-turbo and the Independent JPEG Group: licenses/libjpeg-turbo-LICENSE.md and licenses/libjpeg-turbo-README.ijg. **This software is based in part on the work of the Independent JPEG Group.**
- Google and WebP contributors, including libsharpyuv: licenses/libwebp-COPYING.txt, libwebp-AUTHORS.txt and libwebp-PATENTS.txt.
- Marti Maria Saguer / Little CMS: licenses/lcms2-LICENSE.txt. Optional GPL Little CMS plugins are disabled.
- MinGW-w64 contributors: licenses/MinGW-w64-runtime.txt, including the collective runtime, winpthreads and Wine-derived header notices; LGPL-2.1.txt supplies the referenced license text.
- GCC runtime: licenses/GCC-GPL-3.0.txt with GCC-RUNTIME-EXCEPTION.txt. The linking exception permits eligible compiled independent modules under their own terms; the compiler tools themselves are not included in the plugin ZIP.

Python, Pillow, ComicRack CE, its 7-Zip, and optional WinRAR/cwebp remain separate prerequisites with their own terms. No modified decoder or encoder algorithms are introduced by this build. Build tooling, exact source URLs/checksums, generated-file normalization and static-link steps are documented in Development/ENCODER_BUILD.md in the source repository. A new build must pass the output/color/profile and DLL-import tests before packaging.
''', encoding='utf-8')
    print('Staged reviewed encoder:', stage)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    stage_bundle(parser.parse_args().workspace)
