# TODO - Fix NoReverseMatch + flujo Smart Scanner

- [x] Revisar rutas en `accounting/urls.py` y confirmar `app_name = 'accounting'`.
- [x] Localizar usos de `vehicle_list` y redirecciones sin namespace.
- [x] Corregir redirecciones en `accounting/views.py` para usar namespaced URLs.
- [x] Verificar consistencia de rutas relacionadas (`bank_*`, `chart_of_accounts`, `fiscal_close`, `opening_balance`, `home`).
- [x] Agregar guard en `vehicle_create` cuando `current_company` es nulo.
- [ ] Hacer resiliente `smart_scanner` cuando falle Gemini/API key (guardar pendiente mínimo).
- [ ] Probar POST de scanner con falla IA y validar creación en `Expense` con `status='PENDING'`.
- [ ] Documentar pasos de Railway para corregir `GEMINI_API_KEY`.
