# TODO - Fase 1 Reportería unificada (Excel/PDF)

- [x] Revisar rutas y vistas actuales de reportes en `accounting` y `core`.
- [ ] Implementar sección central de reportería (dashboard) en `core`.
- [ ] Agregar endpoint/flujo de exportación Excel para Libro Diario.
- [ ] Agregar endpoint/flujo de exportación Excel para Balance de Comprobación.
- [ ] Agregar versión PDF imprimible para ambos reportes.
- [ ] Actualizar botones y enlaces en templates de reportes contables.
- [ ] Ejecutar `python manage.py check`.
- [ ] Dejar lista base para escalar a otros módulos.

## TODO - Rediseño Reporte de Flotilla (Profesional)

- [x] Analizar vista/template actual de reporte de flotilla.
- [ ] Mejorar backend de filtros y clasificación para reporte flotilla.
- [ ] Crear endpoint PDF profesional de reporte de flotilla.
- [ ] Registrar ruta `reporte-flotilla/pdf/`.
- [ ] Rediseñar template con acciones: Generar, Imprimir, Descargar PDF.
- [ ] Aplicar estilos `@media print` para impresión profesional.
- [ ] Validar escenarios con/sin datos y filtros.

## TODO - Partida Manual (Libro Diario)

- [x] Crear vista `manual_journal_entry_create` en `accounting/views.py`.
- [x] Registrar ruta `accounting/manual-partida/` en `accounting/urls.py`.
- [x] Crear template `accounting/templates/accounting/manual_journal_entry_create.html`.
- [x] Agregar botón de acceso desde `accounting/templates/accounting/libro_diario.html`.
- [ ] Validar creación correcta con Debe = Haber.

## TODO - Nuevas páginas Tesorería/Bancos (faltantes menú)

- [x] Crear vistas: `cxc_dashboard_view`, `payment_schedule_view`, `credit_debit_notes_view` en `accounting/views.py`.
- [x] Registrar rutas: `cxc/`, `programacion-pagos/`, `notas-credito-debito/` en `accounting/urls.py`.
- [x] Crear templates: `cxc_dashboard.html`, `payment_schedule.html`, `credit_debit_notes.html`.
- [ ] Validar navegación desde menú lateral.

## TODO - Mes de Trabajo Seleccionable (Advertencia flexible)

- [ ] Agregar selector global de mes/año en navbar (`templates/base.html`).
- [ ] Validar en `manual_journal_entry_create` mes/año de fecha vs mes/año activo de sesión.
- [ ] Mostrar advertencia (sin bloquear guardado) cuando no coincida el período.
- [ ] Mostrar ayuda visual en formulario de partida manual.

## TODO - Compras + Proveedores + Scanner IA (sin afectar reporte por placa)

- [x] Crear modelo `Supplier` en `accounting/models.py` + migración.
- [x] Implementar CRUD básico de proveedores en `accounting/views.py`.
- [ ] Finalizar formulario funcional de `purchase_create` en `accounting/templates/accounting/purchase_create.html`.
- [ ] Convertir `suppliers_list.html` en listado + alta/edición básica de proveedores.
- [ ] Crear scanner de compras con IA (`purchase_scanner`) separado del scanner de flotilla.
- [x] Asegurar lógica contable: combustible sin placa => partida/cuenta separada sin afectar reportes por placa.
- [ ] Conectar rutas y botones de navegación rápida entre compras/proveedores/scanner IA.
- [x] Ejecutar `makemigrations`, `migrate` y `python manage.py check`.

## TODO - Fase 1 Chat IA Contable (ERP)

- [x] Crear función `responder_chat_contable` en `core/ai_brain.py`.
- [x] Crear endpoint `ai_accounting_chat` en `core/views.py`.
- [x] Registrar ruta `api/ia-contable/chat/` en `core/urls.py`.
- [x] Crear página `templates/core/ai_contable_chat.html`.
- [x] Agregar acceso en `templates/base.html`.
- [x] Ejecutar pruebas: `check` + curl + validación básica UI.

## TODO - Fase 2 Chat IA Contable (A+B)

- [x] Crear modelo `AIQueryLog` en `core/models.py` para auditoría.
- [x] Agregar tools IA en `core/ai_brain.py` (gastos, libro diario, proveedores, borrador partida).
- [x] Extender endpoint `ai_accounting_chat` con permisos por rol y ejecución de tools.
- [x] Registrar rutas API adicionales de Fase 2 en `core/urls.py`.
- [x] Mejorar UI `templates/core/ai_contable_chat.html` con acciones sugeridas y estructura de resultados.
- [x] Ejecutar pruebas exhaustivas: `makemigrations`, `migrate`, `check`, curl + validación UI.

## TODO - Fase 3 IA Contable (aprobación y aplicación controlada)

- [ ] Crear modelo `AIActionDraft` en `core/models.py`.
- [ ] Crear endpoints draft: create/list/approve/reject/apply en `core/views.py`.
- [ ] Registrar rutas Fase 3 en `core/urls.py`.
- [ ] Aplicar validaciones de segregación de funciones (quien crea no aplica) y roles.
- [ ] Aplicar lógica atómica para convertir borrador en `JournalEntry` + `JournalEntryLine`.
- [ ] Integrar auditoría en `AIQueryLog` para todo el ciclo del draft.
- [ ] Mejorar UI `templates/core/ai_contable_chat.html` con panel de pendientes y acciones.
- [ ] Ejecutar pruebas exhaustivas: migrate/check + curl de todos los casos + validación UI.

## TODO - Mejorar Libro Mayor (conexión Libro Diario)

- [ ] Ajustar `general_ledger` en `accounting/views.py` para leer exactamente `JournalEntryLine` + `JournalEntry`.
- [ ] Unificar filtros de empresa con compatibilidad legacy (`_current_company_key` + valor anterior).
- [ ] Corregir cálculo de saldo acumulado y orden cronológico consistente.
- [ ] Validar que movimientos del Libro Diario aparezcan en el Libro Mayor para la cuenta seleccionada.

## TODO - Fix enrutamiento reportes contables (Libro Mayor / ER / BG)

- [x] Detectar colisiones de rutas duplicadas en `accounting/urls.py` (`libro-diario`, `libro-mayor`, `balance-general`, `estado-resultados`).
- [x] Eliminar colisiones dejando rutas principales hacia vistas NIIF (`general_journal`, `general_ledger`, `balance_sheet`, `income_statement`).
- [x] Mantener rutas legacy sin colisión para compatibilidad.
- [ ] Validar navegación desde menú/reporting_hub y consistencia de `name=`.

## TODO - Fix IA Scanner (Gemini sin respuesta utilizable)

- [x] Revisar flujo `analyze_invoice_image` en `accounting/utils.py`.
- [x] Agregar robustez de `mime_type` real al enviar imagen a Gemini.
- [x] Añadir segundo intento de prompt (full + short) por modelo candidato.
- [x] Normalizar salida IA para tolerar claves alternas (`suggested_account` / `account_type`).
- [ ] Probar endpoint `api/analizar-factura/` con casos reales (imagen válida, imagen borrosa, sin texto).
