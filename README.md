# Measure the Windows component store with DISM analysis

An educational Windows analysis capture plus a narrow Python parser. No cleanup command is run. This does not leave Windows byte-for-byte unchanged: report/log files are created and DISM/Windows may write servicing logs/state.

## Run

Use a NEW empty local lesson folder and save the three source files there. Python 3.10+ runs the parser/tests. Capture needs Windows and an administrator terminal. Follow local execution policy; if scripts are blocked, stop and review local policy rather than bypassing it blindly.

    python --version
    python -m unittest -v test_winsxs
    powershell -NoProfile -File capture_winsxs.ps1
    python summarize_winsxs.py results/dism-report.txt

Capture creates a NEW results/ directory and passes /Online /English /Cleanup-Image /AnalyzeComponentStore to Windows DISM, with a lesson-local log path. It does not run StartComponentCleanup or ResetBase. Existing results files/folders refuse before DISM. A second run is expected to fail, preserving the first report/log. Partial outputs remain on failure; no automatic delete, reset or rollback. Use another NEW empty folder for another analysis.

## Interpretation

DISM actual size factors hard links but includes Shared with Windows. Backups/disabled features and cache/temporary data are overhead categories, not a guarantee of reclaimable space. Sizes retain the reported number and unit without converting them to exact allocated bytes or deletion allowances. The parser requires the expected English fields exactly once and successful completion text; it does not authenticate provenance. Keep the original report for local inspection.

Folder names, machine versions and logs may be private. No upload/network code is included, but Windows servicing/network behavior and sync software are outside the parser's control. Stop editors/sync. Refusing links/reparse points, hardlinks and traversal is best-effort, not a hostile-race security boundary. Do not run against untrusted folders. The parser caps the input report at 1 MB; no whole-system resource guarantee.

## Tests and evidence

31 small tests: 27 Python parser/filesystem cases and four Windows administrator capture-preflight cases. Linux skips Windows preflight; Windows skips Unix pipe. Symlink creation may skip if unavailable. Actual Windows DISM captures are separate from synthetic parser fixtures. Ubuntu cannot validate Windows DISM or system servicing. Two Windows and two Ubuntu full replays are verified. Windows pair differs in unittest time, unique temporary refusal paths and native progress lines; report fields and command results match after those differences. Ubuntu pair differs only in unittest time. Both platforms exercise symlinks. Windows actual analysis and repeat-preservation checks passed twice. CI runs actual DISM capture/parser on Windows only, plus the shared fixtures on both systems.

The lesson does not size Installer/PackageCache, offer cleanup advice or claim all component-store files are hardlinked. Never hand-delete component-store files.

Sources:
- https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/determine-the-actual-size-of-the-winsxs-folder?view=windows-11
- https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/dism-global-options-for-command-line-syntax?view=windows-11
- https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/clean-up-the-winsxs-folder?view=windows-11

MIT license for this code only; Microsoft Windows/DISM and Python belong to their owners and are not included. Educational example, no warranty.
