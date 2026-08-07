# Lumora Dev App v1.1 — Production Polish & Real-Time Experience

## Summary

Extended v1.0 without architecture redesign. Added authentication, realtime polling, chat productivity features, project management polish, editor autosave, and expanded settings.

## Added

### Authentication
- Login screen with backend URL, optional token, named profiles
- Auto session restore via secure storage
- Logout + auth-gated GoRouter redirect
- Multiple backend profiles (save / switch)

### Realtime
- `RealtimeService` polling (8s) for system health, multi-agent, deployment, tasks
- StreamProviders for live dashboard widgets
- Graceful failure (no crash when backend offline)

### Chat
- Message search
- Pin messages
- Edit user prompts
- Regenerate last assistant reply
- Export conversation to clipboard
- Persistent history (Hive)

### Projects
- Favorites / Recent filters
- Search, swipe-to-delete
- Duplicate & rename
- Persistent project list

### Editor
- Autosave after 2s idle
- Dirty indicator in title

### Settings
- Backend profiles list
- Font scale
- Cache clear
- Session / logout

## Compatibility

Fully compatible with Lumora Dev v4.0 REST APIs. No backend changes required.

## Tests

Expanded unit suite targeting 150+ assertions/cases.

## APK

Flutter SDK was unavailable in the build environment; APK not generated here.
Run locally: `flutter build apk --release`
