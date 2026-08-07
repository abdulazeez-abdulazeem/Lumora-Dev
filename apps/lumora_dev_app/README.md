# Lumora Dev App v1.1

Official Flutter client for **Lumora Dev v4.0**.

## What's new in 1.1

- Authentication & backend profiles
- Live status polling on the dashboard
- Chat search, pin, edit, regenerate, export
- Project favorites / recent / duplicate
- Editor autosave
- Font scaling & cache management

## Setup

```bash
flutter pub get
flutter run
```

Configure backend on the **Login** screen or in **Settings**.

## Architecture

Unchanged from v1.0: feature-first Clean Architecture, Riverpod, GoRouter, Dio → Lumora REST.
