# Cambios seguros (sin reseteos accidentales)

## Objetivo
Evitar pérdida de trabajo y configuración al hacer cambios en código y despliegues.

## Flujo obligatorio antes de cambiar código

1. **Crear backup de base de datos**
   - Ejecutar:
     - `scripts\backup_db.bat`
   - Esto genera un JSON en `backups/`.

2. **Crear rama de trabajo**
   - `git checkout -b feature/nombre-cambio`

3. **Aplicar cambios y validar**
   - Revisar archivos.
   - Probar funcionalidad clave.

4. **Guardar cambios**
   - `git add .`
   - `git commit -m "Descripción del cambio"`

5. **Subir rama**
   - `git push -u origin feature/nombre-cambio`

6. **Merge controlado a main**
   - Hacer PR.
   - No trabajar directo sobre `main`.

---

## Restauración de datos (si algo falla)

- Ejecutar:
  - `scripts\restore_db.bat backups\db_backup_YYYYMMDD_HHMMSS.json`

---

## Reglas de operación recomendadas

- Nunca hacer `git reset --hard` en `main`.
- Nunca hacer cambios directos en producción sin backup previo.
- Hacer tag de versión estable antes de cambios grandes:
  - `git tag v1.0-base-estable`
  - `git push origin v1.0-base-estable`

---

## Protección en GitHub (recomendado)

En Settings > Branches > Branch protection rules para `main`:

- Require a pull request before merging.
- Require at least 1 approval.
- Restrict who can push to matching branches.
- (Opcional) Require status checks to pass.
