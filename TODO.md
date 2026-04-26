# TODO - Refactor Smart Scanner y subida de gasto

- [x] Revisar `accounting/views.py` y detectar duplicación/fragilidad en scanner.
- [x] Agregar helpers reutilizables en `accounting/utils.py` para normalizar imagen y construir payload.
- [x] Simplificar `smart_scanner` en `accounting/views.py` usando helpers, manteniendo fallback actual.
- [x] Unificar validaciones/mensajes básicos en flujos de subida de gasto.
- [x] Corregir typo de ruta legacy `accountig:smart_hub` -> `accounting:smart_hub`.
- [x] Ejecutar verificación mínima (`python manage.py check`).
- [x] Marcar TODO finalizado.
