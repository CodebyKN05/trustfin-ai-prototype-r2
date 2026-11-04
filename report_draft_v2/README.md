# TrustFin AI report draft v2

Primary editable source: TrustFin_AI_Report_v2.md.

From the repository root, build the PDF and regenerate the LaTeX export with the existing project Python environment:

    .\venv\Scripts\python.exe -B report_draft_v2\build_report.py

The Markdown uses @figure, @chart and @sample directives understood by the supplied renderer. All original diagrams are in assets/; integrity hashes are in evidence/source_integrity.json. The SVG is rendered only to a derivative for PDF/LaTeX embedding, while its original bytes are preserved. Graphs are generated from recorded numeric evidence, not image synthesis.

prepare_report.py reconstructs the initial v2 content from the original PDF plus reviewed additions. It is a provenance/build-preparation script, not the normal editing entry point: edit Markdown and run build_report.py. Do not rerun preparation after manual edits unless intentionally regenerating the draft.

No original matching LaTeX source or compiler was available. The PDF is produced with installed ReportLab; the exported .tex is an editable alternative, not a verified LaTeX build. Read REMAINING_ITEMS.md before final submission.

The download bundle and temporary build/cache files are excluded from Git. Original report-preparation paths in the archival preparation script refer to the drafting workstation; normal rebuilding uses build_report.py and the checked-in source/assets.
