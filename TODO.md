# TODO - RRHH: páginas faltantes + anticipos/préstamos

- [x] Revisar estado actual de `hr/views.py`, `hr/urls.py`, `hr/models.py` y menú.
- [x] Crear modelo `EmployeeLoanAdvance` en `hr/models.py`.
- [ ] Generar y aplicar migración de `hr`.
- [ ] Crear vistas RRHH faltantes (`vacaciones_permisos`, `prestamo_list`, `prestamo_create`, `nomina_create` funcional).
- [ ] Conectar rutas RRHH en `hr/urls.py`.
- [ ] Crear templates RRHH (`nomina_create.html`, `vacaciones_permisos.html`, `prestamo_list.html`, `prestamo_form.html`).
- [ ] Actualizar enlaces de menú RRHH en `templates/base.html`.
- [ ] Ejecutar pruebas (`makemigrations`, `migrate`, `check` + endpoints básicos).
- [ ] Bloque A: blindaje multiempresa (`middleware`, `switch_company`, settings producción).
- [ ] Bloque A: corregir modal/botón "Nuevo Empleado" en RRHH.
