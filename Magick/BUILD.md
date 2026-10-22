# Bundled encoder

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
