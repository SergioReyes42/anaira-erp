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
