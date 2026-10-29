# Custom workspaces

Approved: independent screen layouts; movable/resizable/hideable/floating panels; custom action toolbars and existing shortcut editor; named saved layouts; theme, text size and spacing; layout lock/reset. Copy compatible layout settings to chosen screens or all screens without changing content or losing tools. Clean defaults keep screenshots/documents central. Layouts are local user preferences, never project data.

Implementation: nested Qt QMainWindow hosts per screen with stable QDockWidget roles, native state for exact same-screen restore and portable role-based placement for cross-screen copy. A Workspace menu and dialog expose panels, toolbar order/actions, appearance, named presets and selective copying. Copy only roles present on both sides; retain incompatible destination panels/actions. Clamp floating windows to available screens. Persist schema-validated JSON under local app data. Existing page indices/controls/data lifecycles remain intact.
