# Copyright (c) 2026 RayRayElite; SPDX-License-Identifier: MIT
# Native discovery checks: no registry/environment/Program Files writes.
def test_archive_discovery():
    fixture = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Archive Discovery', System.Guid.NewGuid().ToString('N'))
    Directory.CreateDirectory(fixture)
    def folder(name):
        path = Path.Combine(fixture, name)
        Directory.CreateDirectory(path)
        return path
    def marker(root, name):
        path = Path.Combine(root, name)
        File.WriteAllText(path, 'Discovery-only marker, never executed')
        return path
    resources = folder('resources')
    installed = folder('Program Files 64 bit')
    custom = folder(u'Custom & Portable \u00e9')
    on_path = folder('path tools')
    empty = folder('empty resources')
    registered = marker(custom, '7z.exe')
    standard = marker(installed, '7z.exe')
    path_tool = marker(on_path, '7z.exe')
    # Simulate an installation where ComicRack has no archive tool.
    assert _find_archive_tool([empty], [installed], [], '') == standard
    assert _find_archive_tool([empty], [], [custom], '') == registered
    assert _find_archive_tool([empty], [], [], '"' + on_path + '"') == path_tool
    assert _find_archive_tool([empty], [], [], ';relative-folder;;') is None
    assert _find_archive_tool([empty], [Path.Combine(fixture, 'missing')], [], '') is None
    assert _find_archive_tool([empty], [installed], [custom], on_path) == standard
    # Missing 7za64 in the AppDomain Resources search was another omission.
    resource_tool = marker(resources, '7za64.exe')
    assert _find_archive_tool([resources], [installed], [custom], on_path) == resource_tool
    full = marker(resources, '7z.exe')
    assert _find_archive_tool([resources], [], [], '') == full
    assert 'PATH' in _archive_tool_missing_message() and 'restart ComicRack' in _archive_tool_missing_message()
    assert isinstance(_archive_registry_roots(), list)
    # A real standalone-shaped folder, including companion DLLs, must list a
    # generated CBZ through the discovered absolute path (not shell file associations).
    actual = _find_archive_tool()
    assert actual, 'Harness requires an available real 7-Zip tool'
    real_folder = folder('Real standalone 7-Zip')
    File.Copy(actual, Path.Combine(real_folder, '7z.exe'))
    for dll in Directory.GetFiles(Path.GetDirectoryName(actual), '7z*.dll'):
        File.Copy(dll, Path.Combine(real_folder, Path.GetFileName(dll)))
    tool = _find_archive_tool([empty], [real_folder], [], '')
    trial_root = Path.Combine(SCRIPT_DIR, 'Development', 'Test Environment', 'Trial Helper Checks')
    samples = [Path.Combine(p, 'original.cbz') for p in Directory.GetDirectories(trial_root) if File.Exists(Path.Combine(p, 'original.cbz'))]
    assert samples, 'Run test_trial_helper.py first'
    status, output, errors = _run_archive_list(tool, samples[0])
    assert status == 0, errors
    assert _parse_archive_listing(output, samples[0])
    print('PASS: missing ComicRack resources, standard/x64/custom/PATH discovery, quoted Unicode paths, resource precedence, missing tools and real standalone-shaped 7-Zip CBZ listing')
test_archive_discovery()
