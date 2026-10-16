import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import summarize_winsxs as tool

# Synthetic report, not a captured machine measurement.
FIXTURE = '''Component Store (WinSxS) information:
Windows Explorer Reported Size of Component Store : 7.12 GB
Actual Size of Component Store : 6.20 GB
Shared with Windows : 5.00 GB
Backups and Disabled Features : 1.00 GB
Cache and Temporary Data : 204.80 MB
Component Store Cleanup Recommended : No
The operation completed successfully.
'''

class Parser(unittest.TestCase):
    def test_gb_and_mb(self):
        data = tool.parse(FIXTURE)
        self.assertEqual(data[tool.FIELDS[1]], (tool.Decimal('6.20'),'GB'))
        self.assertEqual(data[tool.FIELDS[4]], (tool.Decimal('204.80'),'MB'))
    def test_actual_dism_zero_bytes_unit(self):
        self.assertEqual(tool.parse(FIXTURE.replace('204.80 MB', ' 0 bytes'))[tool.FIELDS[4]], (tool.Decimal(0),'bytes'))
    def test_yes(self): self.assertEqual(tool.parse(FIXTURE.replace(': No', ': Yes'))['Cleanup recommended'], 'Yes')
    def test_crlf(self): self.assertEqual(tool.parse(FIXTURE.replace('\n','\r\n')), tool.parse(FIXTURE))
    def test_zero_is_valid(self): self.assertEqual(tool.parse(FIXTURE.replace('6.20 GB','0 B'))[tool.FIELDS[1]],(tool.Decimal(0),'B'))
    def test_units(self):
        for unit in tool.UNITS:
            self.assertEqual(tool.parse(FIXTURE.replace('6.20 GB','2 '+unit))[tool.FIELDS[1]],(tool.Decimal(2),unit))
    def test_missing_fields(self):
        for field in tool.FIELDS:
            with self.assertRaises(ValueError): tool.parse(FIXTURE.replace(field,'unknown'))
    def test_duplicate_field(self):
        with self.assertRaises(ValueError): tool.parse(FIXTURE+tool.FIELDS[0]+': 1 GB\n')
    def test_missing_success(self):
        with self.assertRaises(ValueError): tool.parse(FIXTURE.replace('The operation completed successfully.','Error: 87'))
    def test_localized_unsupported(self):
        with self.assertRaises(ValueError): tool.parse(FIXTURE.replace('6.20','6,20'))
    def test_unknown_units(self):
        with self.assertRaises(ValueError): tool.parse(FIXTURE.replace('6.20 GB','6.20 GiB'))
    def test_negative_refused(self):
        with self.assertRaises(ValueError): tool.parse(FIXTURE.replace('6.20','-6.20'))
    def test_duplicate_flag(self):
        with self.assertRaises(ValueError): tool.parse(FIXTURE+'Component Store Cleanup Recommended : Yes\n')
    def test_nul_refused(self):
        with self.assertRaises(ValueError): tool.parse(FIXTURE+'\0')
    def test_large_refused(self):
        with self.assertRaises(ValueError): tool.parse('x'*1_000_001)

class Files(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name); self.report=self.root/'report.txt';self.report.write_text(FIXTURE,encoding='utf-8')
    def run_tool(self,path):
        out=io.StringIO()
        with contextlib.redirect_stdout(out): code=tool.main(['summarize_winsxs.py',str(path)])
        return code,out.getvalue()
    def test_read_preserves_bytes_mtime(self):
        before=self.report.read_bytes(),self.report.stat().st_mtime_ns
        code,out=self.run_tool(self.report)
        self.assertEqual(code,0);self.assertIn('not freeable-byte',out)
        self.assertEqual(before,(self.report.read_bytes(),self.report.stat().st_mtime_ns))
    def test_bom(self): self.report.write_bytes(b'\xef\xbb\xbf'+FIXTURE.encode());self.assertEqual(self.run_tool(self.report)[0],0)
    def test_invalid_utf8(self): self.report.write_bytes(b'\xff');self.assertEqual(self.run_tool(self.report)[0],2)
    def test_missing(self): self.assertEqual(self.run_tool(self.root/'absent')[0],2)
    def test_directory(self): self.assertEqual(self.run_tool(self.root)[0],2)
    def test_hardlink(self):
        link=self.root/'hard';os.link(self.report,link);self.assertEqual(self.run_tool(link)[0],2)
    def test_symlink_existing_dangling_and_loop(self):
        link=self.root/'link'
        for target in [self.report,self.root/'absent',link]:
            try: link.symlink_to(target)
            except OSError: self.skipTest('Symlink creation unavailable')
            self.assertEqual(self.run_tool(link)[0],2);link.unlink()
    def test_linked_parent(self):
        link=self.root/'linked'
        try: link.symlink_to(self.root,target_is_directory=True)
        except OSError: self.skipTest('Symlink creation unavailable')
        self.assertEqual(self.run_tool(link/'report.txt')[0],2)
    def test_pipe(self):
        if not hasattr(os,'mkfifo'):self.skipTest('Unix pipe unavailable')
        pipe=self.root/'pipe';os.mkfifo(pipe);self.assertEqual(self.run_tool(pipe)[0],2)
    def test_traversal(self): self.assertEqual(self.run_tool(self.root/'..'/self.root.name/'report.txt')[0],2)
    def test_oversize(self): self.report.write_bytes(b'x'*1_000_001);self.assertEqual(self.run_tool(self.report)[0],2)
    def test_usage(self):
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(tool.main(['script']),2)

class WindowsCapturePreflight(unittest.TestCase):
    def setUp(self):
        if os.name != 'nt': self.skipTest('Windows capture preflight only')
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin(): self.skipTest('Admin capture preflight unavailable')
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.script=self.root/'capture_winsxs.ps1'
        self.script.write_bytes(Path(__file__).with_name('capture_winsxs.ps1').read_bytes())
    def capture(self,script=None):
        import subprocess
        result=subprocess.run(['powershell','-NoProfile','-File',str(script or self.script)],capture_output=True,text=True,timeout=30)
        self.assertNotEqual(result.returncode,0)
        self.assertNotIn('Running DISM component-store analysis',result.stdout)
    def test_existing_results_file_preserved(self):
        target=self.root/'results';target.write_bytes(b'KEEP')
        before=target.read_bytes(),target.stat().st_mtime_ns
        self.capture();self.assertEqual(before,(target.read_bytes(),target.stat().st_mtime_ns))
    def test_existing_results_folder_preserved(self):
        target=self.root/'results';target.mkdir();keep=target/'keep';keep.write_bytes(b'KEEP')
        before=keep.read_bytes(),keep.stat().st_mtime_ns
        self.capture();self.assertEqual(before,(keep.read_bytes(),keep.stat().st_mtime_ns))
        self.assertEqual([p.name for p in target.iterdir()],['keep'])
    def test_linked_lesson_parent_refused(self):
        link=self.root/'linked'
        try: link.symlink_to(self.root,target_is_directory=True)
        except OSError: self.skipTest('Symlink creation unavailable')
        self.capture(link/'capture_winsxs.ps1')
        self.assertFalse((self.root/'results').exists())
    def test_linked_results_refused(self):
        target=self.root/'target';target.mkdir();keep=target/'keep';keep.write_bytes(b'KEEP')
        link=self.root/'results'
        try: link.symlink_to(target,target_is_directory=True)
        except OSError: self.skipTest('Symlink creation unavailable')
        before=keep.read_bytes(),keep.stat().st_mtime_ns
        self.capture();self.assertEqual(before,(keep.read_bytes(),keep.stat().st_mtime_ns))
        self.assertEqual([p.name for p in target.iterdir()],['keep'])

if __name__ == '__main__': unittest.main()
