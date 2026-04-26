# TODO - Profesionalizar reportes contables (Mayor, Balance, Resultados)

- [x] Revisar origen de datos contables (`JournalEntryLine`) y desalineaciones.
- [ ] Leer y ajustar vistas en `accounting/views.py` para Libro Mayor, Balance General y Estado de Resultados.
- [ ] Leer y ajustar templates:
  - `accounting/templates/accounting/general_ledger.html`
  - `accounting/templates/accounting/balance_sheet.html`
  - `accounting/templates/accounting/income_statement.html`
- [ ] Estandarizar filtros por empresa/periodo y cálculos NIIF.
- [ ] Validar integridad con `python manage.py check`.
