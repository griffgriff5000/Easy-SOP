# Consistent application workspace

Goal: apply the agreed canvas-first approach throughout the existing desktop application, retaining capture, annotations, project persistence, templates, shortcuts and exports.

Design: compact 168px app navigation, clear page titles, shared 32px controls and 8/16px spacing, single action bar per screen, muted surfaces with teal primary actions and accessible light/dark themes. Editor uses steps at left, screenshot centre and collapsible Instructions/Annotation inspector at right. Secondary step/screenshot operations move to labelled menus. Studio uses a drawing rail, large canvas and tabbed Properties/Layers/Library inspector; library/file operations move out of crowded button rows. Settings and Document split long forms into labelled categories. Templates use a catalogue plus tabbed properties and consistent save/apply bars. Help/review/shortcut dialogs inherit the same typography, panels and controls.

Architecture: ui/components.py provides headers, menu buttons, tool icons/palette and form helpers; theme.py owns colours/spacing/control styling. Existing widget attributes/callbacks stay stable while layouts are rebuilt. Category-aware focus routing reveals hidden fields when a review item is fixed. Screenshot and studio canvases receive Fit/zoom controls with drag panning. No data format or export changes.

- [x] Add regression checks for canvas workspace size, relevant inspector fields, form/category navigation and zoom mapping.
- [x] Implement shared style/components, main navigation and editor workspace.
- [x] Standardise capture/document/settings/templates, studio and supporting dialogs.
- [x] Run full tests, independent review and visual QA at 1000/1280/1440 widths in light/dark; update docs, rebuild Windows package, smoke-test.
