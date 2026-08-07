# App Architecture

```
lib/
  core/          theme, network, storage, router, widgets, constants
  features/      home, chat, projects, tasks, settings, knowledge,
                 memory, vision, browser, multiagent, deployment,
                 system, files, editor
```

Each feature: `presentation/screens` (+ optional providers/widgets).

State: Riverpod. Navigation: GoRouter shell + drawer. API: Dio via `LumoraApi`.
