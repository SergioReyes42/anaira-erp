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
