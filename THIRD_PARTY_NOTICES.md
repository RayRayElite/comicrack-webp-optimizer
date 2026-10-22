# Third-party components

The [MIT license](LICENSE) applies to RayRayElite's plugin code, documentation and original vector-based icons. It does not relicense third-party code. The single-download runtime package includes the following reviewed encoder components with their notices; Python/Pillow remain separately installed prerequisites.

## Bundled ImageMagick encoder

The runtime ZIP contains a **custom minimal ImageMagick 7.1.2-34 Q8 Windows x64** build, not an official upstream binary. ImageMagick is developed by ImageMagick Studio LLC and contributors; no endorsement is implied. Encoder and codec C/C++ algorithms are unmodified upstream sources. Generated build configuration is normalized for Windows paths/quoting, static archive handling and embedded configuration; see the [build recipe](Development/ENCODER_BUILD.md).

| Component | Version | Supplied terms/notices |
|---|---|---|
| ImageMagick | 7.1.2-34 | [ImageMagick license](Magick/magick_License.txt), [upstream NOTICE](Magick/NOTICE.txt) |
| libjpeg-turbo / Independent JPEG Group | 3.2.0 | [License](Magick/licenses/libjpeg-turbo-LICENSE.md), [IJG terms](Magick/licenses/libjpeg-turbo-README.ijg) |
| libwebp, libsharpyuv | 1.6.0 | [Copyright/license](Magick/licenses/libwebp-COPYING.txt), [authors](Magick/licenses/libwebp-AUTHORS.txt), [patent grant](Magick/licenses/libwebp-PATENTS.txt) |
| Little CMS | 2.19.1 | [MIT license](Magick/licenses/lcms2-LICENSE.txt); optional GPL plugins disabled |
| MinGW-w64 runtime, including winpthreads/header notices | 14.0.0 | [Collective notices](Magick/licenses/MinGW-w64-runtime.txt), including Wine-derived header terms; [referenced LGPL text](Magick/licenses/LGPL-2.1.txt) |
| GCC runtime portions, where linked | 16.2.0 | [GPL text](Magick/licenses/GCC-GPL-3.0.txt) with [GCC Runtime Library Exception 3.1](Magick/licenses/GCC-RUNTIME-EXCEPTION.txt) |

**This software is based in part on the work of the Independent JPEG Group.**

The compiler runtime's linking exception permits eligible compiled independent modules to retain their own licensing terms; it does not relicense the compiler itself. The compiler, assembler and other development tools are not included as user-facing plugin executables. The MinGW toolchain's [license guidance](https://github.com/skeeto/w64devkit/tree/v2.10.1#licenses) calls for retaining its collective notices; they are included in full, alongside the referenced GNU texts.

[Magick/build-info.json](Magick/build-info.json) records exact source/tool URLs and SHA-256 values, binary identity, license hashes and imported DLLs. [Magick/BUILD.md](Magick/BUILD.md) describes the build and attributions. The build uses only the three codec/color delegate libraries listed above; the version banner's Windows Ghostscript capability is a runtime loader, not a bundled or linked Ghostscript library.

## Microsoft runtime files

**No loose Microsoft runtime DLLs are included in the current package.** The minimal encoder's import table is restricted to Windows system libraries, including the operating system's MSVCRT.dll. These are supplied by Windows and are not copied or redistributed by this plugin. The prior locally tested Visual Studio encoder and its msvcp140.dll, vcomp140.dll and vcruntime140.dll have been retired from the runtime folder and excluded from the release allowlist.

This choice avoids relying on unestablished rights to redistribute those older loose DLLs. Microsoft's separate [Visual C++ redistribution guidance](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170) still governs anyone choosing to package them independently; the plugin MIT license does not grant those rights.

## Separate prerequisites and optional tools

Python, Pillow, ComicRack CE, ComicRack's 7-Zip, optional cwebp and optional WinRAR retain their own terms and are **not included** in the runtime ZIP. Installing Pillow for validation/color-managed previews does not change its license. WinRAR is needed only for CBR rebuilding, not CBR-to-CBZ conversion.

Source exports omit Magick/magick.exe while retaining the legal materials, source checksums and build recipe. Development fixtures, comic archives, downloaded build tools, historical encoder binaries and personal reports/settings are excluded from public source/runtime artifacts. Selected user-supplied UI screenshots are included as documentation examples; comic artwork visible in them remains the property of its respective creators and publishers and is not covered by the plugin MIT license.
