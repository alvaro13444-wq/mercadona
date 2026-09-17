-- Esquema para el control de gastos de Mercadona en Supabase (Postgres).
-- Pégalo en Supabase > SQL Editor > New query > Run.

create table if not exists tickets (
    factura_id  text primary key,
    fecha       timestamptz not null,
    tienda      text,
    direccion   text,
    cp          text,
    ciudad      text,
    total       numeric,
    forma_pago  text,
    source_file text,
    created_at  timestamptz default now()
);

create table if not exists lineas (
    id            bigint generated always as identity primary key,
    factura_id    text references tickets(factura_id) on delete cascade,
    fecha         timestamptz not null,
    descripcion   text not null,
    producto_norm text not null,
    cantidad      numeric,
    precio_unit   numeric,
    importe       numeric,
    por_peso      boolean default false
);

create index if not exists idx_lineas_norm   on lineas(producto_norm);
create index if not exists idx_lineas_fecha  on lineas(fecha);
create index if not exists idx_tickets_fecha on tickets(fecha);

-- Seguridad: nadie lee sin estar autenticado.
alter table tickets enable row level security;
alter table lineas  enable row level security;

-- Los usuarios autenticados (tú, tras iniciar sesión) pueden LEER.
create policy "auth read tickets" on tickets for select to authenticated using (true);
create policy "auth read lineas"  on lineas  for select to authenticated using (true);

-- La ESCRITURA la hace la ingesta con la clave service_role, que salta RLS.
-- Por eso no hace falta ninguna policy de insert: el anónimo no puede ni leer
-- ni escribir, y el dashboard solo lee cuando has iniciado sesión.
