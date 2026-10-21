import importlib.util,tempfile,zipfile,sys
sys.dont_write_bytecode = True
from pathlib import Path
spec=importlib.util.spec_from_file_location('helper',Path(__file__).resolve().parent.parent / 'webp_convert_helper.py')
h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
 root=Path(tmp)/'pages';root.mkdir()
 h.Image.new('RGB',(32,48),'white').save(root/'001.jpg')
 (root/'note.txt').write_text('preserve me')
 h.convert_pages(h.walk_page_files(root),'85%','Pillow','No Resize')
 out=Path(tmp)/'test.cbz';h.rebuild_cbz(root,out);h.validate_output(out,'',root)
 try:h.rebuild_cbz(root,out)
 except FileExistsError:pass
 else:raise AssertionError('overwrote existing output')
 h.Image.new('RGB',(32,48),'white').save(root/'001.jpg')
 try:h.convert_pages(h.walk_page_files(root),'85%','Pillow','No Resize')
 except RuntimeError as e:assert 'collision' in str(e)
 else:raise AssertionError('missed collision')
 with zipfile.ZipFile(out,'a') as z:z.writestr('extra.txt','unexpected')
 try:h.validate_output(out,'',root)
 except RuntimeError:pass
 else:raise AssertionError('missed invalid manifest')
print('PASS: conversion, dimensions, archive validation, output collision, page collision, altered manifest')
