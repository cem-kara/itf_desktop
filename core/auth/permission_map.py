from __future__ import annotations

# Map UI routes/titles to permission keys.
# Keep this separate so UI can import without touching DB layer.

PAGE_PERMISSIONS: dict[str, str] = {
    "Admin Panel": "admin.panel",
}
