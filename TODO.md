# TODO - Activar IA en Smart Scanner (configuración nueva)

- [x] Revisar `core/gemini_config.py`, `accounting/utils.py` y `accounting/views.py`.
- [x] Implementar configuración dual de Gemini en `core/gemini_config.py` (SDK nuevo + fallback).
- [x] Adaptar `analyze_invoice_image` en `accounting/utils.py` para cliente dual.
- [x] Reactivar IA en `smart_scanner` (`accounting/views.py`) con fallback operativo sin pérdida.
- [x] Ajustar mensajes de éxito/advertencia según modo IA o sin IA.
- [x] Ejecutar `python manage.py check`.
- [x] Marcar TODO completado.
