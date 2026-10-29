# Structured template preservation and assistance

Goal: keep relevant company cover pages, tables, section layouts, Word fields/content-control bindings and styles; remove recognisable authoring guidance/examples; insert SOP content and assist filling retained company fields. User explicitly replaced the blanket-clear policy after supplying a structured second template.

Approach: conservative recognition, retaining unknown content. Remove explicit guidance blocks and clear Lorem ipsum sample text, remove named style-demo sections/tables, retain every other structure and section break. Add a standalone steps anchor at the first removed demonstration section, or append if absent. Structured profiles record a preparation version; old cleared/legacy assets remain unchanged. Template text patches continue storing user values without new schema. Add a labelled Template fields view, fill recognised metadata from project values, and update bound custom XML and repeated controls consistently. Update contents/figures/tables through installed Word for PDF and direct editing.

- [x] Regression tests for cover/tables/sections/unknown structures retained, known guidance removed and SOP placement.
- [x] Implement conservative preparation and linked field handling, retaining original assets and styles.
- [x] Add labelled company field assistance and hook metadata/default filling into generation.
- [x] Verify both supplied real templates, visual output, bindings/contents, independent review, full tests and Windows package.

Validation: both actual supplied MEH templates passed Word/PDF generation (simple 1 page; structured 7 pages, 6 retained tables and 2 sections). Linked title/reference/revision and manually supplied Teamcenter propagated to the cover. Cover, details/approval/revision tables, contents and generated procedure were visually inspected. Nine structured regression tests cover preservation, unknown headings, forms, linked controls and insertion markers. Final full suite 173 tests passed with exit 0. Frozen startup, template preparation, native editing and DOCX/PDF export checks passed. Independent review issues were fixed and rechecked.

Ruling: company-specific status codes, protective markings and sign-off details are not guessed. The assistant offers retained fields and native editing; source values apply on generation/rebuild, preserving direct edits until explicit confirmation. Cached contents entries are cleared while their fields are retained, and desktop Word refreshes contents/figures/tables for preview/PDF/editing.
