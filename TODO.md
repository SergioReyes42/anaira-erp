# TODO - Fix Libro Diario Debe/Haber

- [x] Revisar flujo de aprobación y origen de datos contables (`JournalEntryLine`).
- [x] Identificar desalineación en template (`entry.items` vs `entry.lines`).
- [x] Corregir `accounting/templates/accounting/libro_diario.html` para usar `entry.lines.all`.
- [x] Ajustar render de “Sumas Iguales” sin `entry.total`.
- [x] Validar integridad con `python manage.py check`.
