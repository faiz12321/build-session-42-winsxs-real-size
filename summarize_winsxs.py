"""Summarize one successful English DISM /AnalyzeComponentStore text report.
Not a disk scanner, cleanup command, or measurement of freeable space.
"""
import re
import stat
import sys
from decimal import Decimal
from pathlib import Path

FIELDS = ('Windows Explorer Reported Size of Component Store',
          'Actual Size of Component Store', 'Shared with Windows',
          'Backups and Disabled Features', 'Cache and Temporary Data')
UNITS = ('B', 'bytes', 'KB', 'MB', 'GB', 'TB')


def parse(text):
    if len(text) > 1_000_000 or '\x00' in text:
        raise ValueError('Unsupported report size or NUL bytes.')
    if not re.search(r'^\s*The operation completed successfully\.\s*$', text, re.M):
        raise ValueError('Successful English DISM completion line missing.')
    result = {}
    for field in FIELDS:
        found = re.findall(r'^\s*'+re.escape(field)+r'\s*:\s*(\d+(?:\.\d+)?)\s+(B|bytes|KB|MB|GB|TB)\s*$', text, re.M)
        if len(found) != 1:
            raise ValueError('Expected exactly one English size field: '+field)
        amount, unit = found[0]
        result[field] = (Decimal(amount), unit)
    flags = re.findall(r'^\s*Component Store Cleanup Recommended\s*:\s*(Yes|No)\s*$', text, re.M)
    if len(flags) != 1:
        raise ValueError('Expected one English cleanup recommendation.')
    result['Cleanup recommended'] = flags[0]
    return result


def read_report(value):
    path = Path(value).absolute()
    if '..' in path.parts:
        raise OSError('Parent-traversal paths are unsupported.')
    for part in [*reversed(path.parents), path]:
        info = part.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise OSError('Links/reparse points are unsupported.')
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 1_000_000:
        raise OSError('Expected an ordinary singly linked report under 1 MB.')
    return path.read_text(encoding='utf-8-sig')


def main(argv):
    if len(argv) != 2:
        print('Usage: python summarize_winsxs.py results/dism-report.txt')
        return 2
    try:
        report = parse(read_report(argv[1]))
    except (OSError, ValueError, UnicodeError) as error:
        print('Refused:', error)
        return 2
    for name in FIELDS:
        print(name+': '+str(report[name][0])+' '+report[name][1]+' (as reported, rounded)')
    print('Cleanup recommended:', report['Cleanup recommended'])
    print('Actual includes Shared with Windows. These are not freeable-byte estimates.')
    print('No cleanup or deletion was requested by this parser.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
