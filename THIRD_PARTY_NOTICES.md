# Third-party components

The MIT license in this repository applies to RayRayElite's plugin code and documentation. It does not relicense third-party executables, libraries or tools. Source checkouts exclude encoder executables and Microsoft runtime DLLs; obtain them from their upstream distributions when building a runtime bundle.

## ImageMagick

ImageMagick is developed by ImageMagick Studio LLC and contributors. The existing local encoder is identified as coming from `ImageMagick-7.1.2-3-portable-Q8-x86.zip`. ImageMagick is a separate executable used to encode pages; it is not authored by this project.

- Upstream: https://imagemagick.org/
- License: https://imagemagick.org/script/license.php/
- Supplied license copy: [Magick/magick_License.txt](Magick/magick_License.txt)

ImageMagick's terms permit inclusion in other distributions with its license and attribution retained. Keep the applicable third-party/delegate notices supplied with the exact upstream binary distribution as well. This project does not imply ImageMagick Studio LLC endorses it.

## Microsoft Visual C++ runtime

The current local testing bundle contains `msvcp140.dll`, `vcomp140.dll` and `vcruntime140.dll`, identified as Microsoft Corporation version 14.44.35211.0. They are Microsoft components, not MIT-licensed plugin code. Their distribution is governed by applicable Microsoft terms, independently of ImageMagick's license.

- Redistribution documentation: https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170
- Official runtime downloads: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist?view=msvc-170

Before a public binary release, verify redistribution eligibility and required terms/notices for these exact DLLs, or use the official runtime installer as a prerequisite instead of shipping loose DLLs. This notice records provenance; it does not grant redistribution rights.

## External prerequisites

Python, Pillow, ComicRack CE, ComicRack's 7-Zip, optional cwebp and optional WinRAR are separate prerequisites with their own terms. They are not bundled by this repository's release builder, except for the explicitly listed ImageMagick files in a locally built runtime ZIP. Installing Pillow through requirements does not change Pillow's license.
