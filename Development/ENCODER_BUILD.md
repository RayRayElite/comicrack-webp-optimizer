# Building the bundled encoder

The runtime ZIP contains a custom **ImageMagick 7.1.2-34 Q8 Windows x64** executable with statically linked libjpeg-turbo 3.2.0, libwebp/libsharpyuv 1.6.0 and Little CMS 2.19.1. It imports only Windows system DLLs. Separate Visual C++, OpenMP and codec DLLs are not shipped. Python/Pillow remain external prerequisites.

The C/C++ encoder and codec algorithms are unmodified upstream sources. This is a custom build, not an official ImageMagick binary. Generated build files are normalized for native Windows command-line/path handling. See [package_encoder.py](package_encoder.py) for the exact notices collected and `Magick/build-info.json` in a bundle for source URLs, SHA-256 hashes, imports and license-file hashes.

## Prepare an isolated workspace

Use Windows x64, Python 3, CMake and Git for Windows with Git Bash. No system-wide compiler installation is required. The current recipe uses Windows short paths to keep Autoconf library flags free of spaces; use a drive/directory with working 8.3 short-path support. All generated outputs belong in the workspace, never a production comic directory.

1. Download every input listed in [encoder_sources.json](encoder_sources.json) into the workspace root. Verify its SHA-256. These are official source/tool release URLs, pinned rather than automatically following latest releases. License downloads are plain text.
2. Extract the w64devkit archive with 7-Zip into `toolchain/`, producing `toolchain/w64devkit/`. Do not launch its self-extracting installer. Extract the NASM ZIP there too, producing `toolchain/nasm-3.01/`. These tools are for building only and are not part of the user package.
3. Extract the four source archives under `sources/`, preserving the versioned top-level directory names. Check archive members stay under that directory before extraction.
4. Run the build from the repository root, choosing your workspace:

```powershell
python Development/build_encoder.py --workspace "Development/Test Environment/Encoder Build"
```

`--resume` skips codec/configure steps for an already configured development workspace. Use a newly prepared workspace for an independent full rebuild. The build verifies all pinned input files before executing tools. It stages its result under `<workspace>/bundle/Magick`; it does not replace a working plugin's encoder.

## What the recipe does

- Builds static codec libraries with JPEG SIMD enabled. Optional GPL Little CMS plugins are explicitly disabled.
- Configures Q8, no HDRI/OpenMP/modules/Magick++, embedded configuration, and no optional external delegate libraries beyond JPEG, WebP and Little CMS. The Windows Ghostscript capability banner is a runtime loader, not a bundled Ghostscript library.
- Normalizes generated pkg-config paths; fixes generated configuration string paths after the upstream MinGW converter processes already-Windows paths; creates the embedded threshold-map header with correctly escaped C strings. No codec/encoder C/C++ algorithm is patched.
- Builds the core/wand objects, verifies the complete core archive using an `ar` response file to avoid Windows command-length truncation, then explicitly links all static dependencies. Strips symbol/debug tables so developer paths are not retained there.
- Rejects unexpected DLL imports and missing codec/configuration flags; stages the binary, unmodified license/notice files, attribution and input/binary/license hashes.

The GCC runtime uses its linking exception. MinGW's collective notices include runtime, winpthreads and Wine-derived header terms; the referenced LGPL text is included. The toolchain's Dockerfile pins its own GCC 16.2.0 and MinGW-w64 14.0.0 source versions and hashes. See [w64devkit's license guidance](https://github.com/skeeto/w64devkit/tree/v2.10.1#licenses), [GCC's runtime exception](https://www.gnu.org/licenses/gcc-exception-3.1.en.html), and the actual included texts. Source/build tools are not bundled as plugin runtime executables.

## Verify before adoption

```powershell
python Development/inspect_pe.py "<workspace>/bundle/Magick/magick.exe"
python Development/test_bundled_encoder.py --tool "<workspace>/bundle/Magick/magick.exe" --reference-tool "<previous encoder>/magick.exe"
```

The generated checks cover RGB/grayscale/CMYK, available Adobe RGB fixtures, Q60–Q90, resize, ICC retention, real helper conversions and concurrency. A reference comparison records encoded bytes and decoded pixels rather than assuming a compiler/dependency update preserves them. Include the normal safety, long-path, color, native UI/history and package tests before releasing. Matching these fixtures is not a promise about every image or machine. Timing comparisons must run without a compiler or other heavy workload running concurrently.

Only copy a reviewed staged bundle into `Magick` after verification, retaining the prior encoder privately for comparison. Build the plugin/source ZIPs with their explicit allowlists and inspect their manifests. Do not put compiler tools, source workspaces, private fixtures or old Microsoft DLLs in user packages.
