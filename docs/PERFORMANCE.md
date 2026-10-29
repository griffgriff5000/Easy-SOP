# UI performance verification — 29 October 2026

Measured with `python scripts/profile_studio.py <label>` using the short Python environment documented in VALIDATION.md. The script uses isolated preferences and an 80-step synthetic SOP sharing one 1600×900 screenshot, plus 12 reusable annotation designs. It profiles UI construction, project loading, text changes, selections, navigation and resizing; it excludes native Word conversion. Results below compare warm filesystem runs under cProfile on the same machine.

| Operation | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| Load the 80-step shared-image SOP | 0.653 s | 0.245 s | 62% |
| Select 20 steps | 0.341 s | 0.098 s | 71% |
| Navigate 12 screens | 0.515 s | 0.206 s | 60% |
| Construct the UI | 1.351 s | 1.281 s | 5% |

These are workload-specific measurements, not promises for every document. Cold startup is strongly affected by Python/module filesystem caching. Typing and resize timings did not establish a meaningful improvement. First-time decoding of unique large screenshots and native Word operations still have their underlying costs.

Changes:

- UI screenshot decoding and rendered previews use bounded LRU caches: 64 MiB of RGB source images, 32 MiB of rendered pixmaps and 256 small thumbnails. Keys include file metadata and every rendering input; annotation, marker and numbering changes invalidate results. Annotation keys are hashed to avoid retaining large artwork JSON strings. Export rendering still uses original files directly.
- Annotation library packs cache validated contents with defensive copies, a 16 MiB/64-entry bound and file metadata invalidation. Unchanged library visits do not reconstruct rendered previews. New/edited/deleted entries change the signature and refresh the gallery.
- Unchanged workspace JSON is not written again during navigation or layout notifications. Changed preferences retain atomic writes; failed writes are not marked saved.
- Default workspace appearance inherits the shared stylesheet instead of installing the full stylesheet repeatedly on every screen. Custom appearance remains supported.
- Revision Word previews are invalidated by changes and generated only when Preview is opened, rather than rebuilding DOCX/HTML after every placement. Preview entry saves the native Word document first; final saves do not restart preview work during closure.

Regression coverage tests reuse/invalidation, source immutability under redaction, library changes, unchanged writes and lazy preview/save lifecycle. See VALIDATION.md for full-suite and packaged checks.
