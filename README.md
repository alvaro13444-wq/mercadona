# Gasto Mercadona — versión nube (gratis)

Control de gastos de Mercadona 100 % automático y gratuito, en móvil y ordenador.

- **GitHub Actions** entra a Gmail varias veces al día, descarga los PDF de factura,
  los parsea y los guarda en Supabase.
- **Supabase** (Postgres) guarda los datos, protegidos por login.
- **GitHub Pages** sirve el dashboard (`docs/index.html`).

Dos cuentas, cero servidores que mantener. Una vez montado, funciona solo.

---

## Paso 1 — Supabase (base de datos)

1. Crea cuenta en https://supabase.com y un proyecto nuevo (región Europa).
2. Ve a **SQL Editor > New query**, pega el contenido de `supabase_schema.sql` y pulsa **Run**.
3. Ve a **Project Settings > API** y copia tres cosas:
   - `Project URL`  → será `SUPABASE_URL`
   - `anon public`  → irá en el dashboard (`docs/index.html`)
   - `service_role` → será `SUPABASE_SERVICE_KEY` (secreto, solo para la ingesta)
4. Crea tu usuario del dashboard: **Authentication > Users > Add user**, pon tu correo
   y una contraseña, y marca la casilla de auto-confirmar (Auto Confirm User).

## Paso 2 — El repositorio en GitHub

1. Crea un repositorio **privado** y sube estos archivos (o haz push de esta carpeta).
2. Edita `docs/index.html` y rellena las dos líneas del bloque CONFIGURA:
   `SUPABASE_URL` y `SUPABASE_ANON_KEY`. Haz commit.

## Paso 3 — Secretos y activar la ingesta

1. Antes, crea la **contraseña de aplicación** de Gmail: Google > Seguridad >
   Verificación en 2 pasos (actívala) > Contraseñas de aplicaciones. Guarda los 16 dígitos.
2. En el repo: **Settings > Secrets and variables > Actions > New repository secret**,
   crea cuatro:
   - `GMAIL_USER` = tu_correo@gmail.com
   - `GMAIL_APP_PASS` = la contraseña de aplicación (sin espacios)
   - `SUPABASE_URL` = el Project URL
   - `SUPABASE_SERVICE_KEY` = la clave service_role
3. Pestaña **Actions** > habilita los workflows si lo pide. Abre *Ingesta Mercadona*
   y pulsa **Run workflow** para la primera carga manual. Revisa el log: debe listar
   los tickets cargados.

## Paso 4 — Publicar el dashboard

1. **Settings > Pages**: en *Source* elige la rama `main` y la carpeta `/docs`. Guarda.
2. En un minuto tendrás la URL `https://TU_USUARIO.github.io/TU_REPO/`.
3. Ábrela, inicia sesión con el usuario que creaste en el Paso 1.4, y ahí está el dashboard.
4. En el iPhone: Compartir > **Añadir a pantalla de inicio** para instalarlo como app.

---

## Mantenimiento

- **No hay que refrescar nada.** El cron corre 4 veces al día por su cuenta.
- El workflow hace un commit vacío el día 1 de cada mes para que GitHub no
  desactive el cron por inactividad (límite de 60 días). Automático.
- GitHub te envía un email si una ejecución falla.
- La contraseña de aplicación de Gmail solo se rompe si cambias la contraseña de
  Google; entonces generas otra y actualizas el secreto `GMAIL_APP_PASS`.
- `normalize.py`: añade alias a mano de vez en cuando para afinar el seguimiento
  de precios (opcional; los totales funcionan igual).

## Horario del cron

Está en `.github/workflows/ingest.yml`, línea `cron:` (en UTC). Ajusta las horas
si quieres más o menos pasadas al día.
