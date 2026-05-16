# History Rewrite — Project Skeleton

## Ограничения (обязательно)
- **Local-only**: проект запускается только локально, без удалённого управления.
- **Manual approval only**: любые действия подтверждаются вручную.
- **No captcha bypass**: обход капчи запрещён.
- **No auto-apply**: автоматическое применение изменений/патчей запрещено.

## Структура
- `project/backend/{api,websocket,services,orchestration,providers,browser,patching,previews,queue,models,config,utils}`
- `project/frontend/{dashboard,components,cards,websocket}`
- `project/{previews,temp,patches,logs}`

## Быстрый старт
```bash
make install
make backend
make frontend
```
