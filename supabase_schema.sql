-- Trading Journal — Supabase Schema
-- Einmalig im Supabase SQL-Editor ausführen (Project -> SQL Editor -> New query).

-- 1) Tabelle für Trades --------------------------------------------------------
create table if not exists public.trades (
    id              uuid primary key default gen_random_uuid(),
    created_at      timestamptz not null default now(),
    location_slug   text        not null,
    datum           date        not null default current_date,
    richtung        text        not null,            -- 'Long' | 'Short'
    instrument      text        not null,            -- 'ES', 'NQ', ...
    kontrakte       numeric     not null,
    entry           numeric     not null,
    sl              numeric,
    tp              numeric,
    bias            text,                             -- 'Ja' | 'Nein'
    status          text        not null,            -- 'offen' | 'TP getroffen' | 'SL getroffen' | 'manueller Exit'
    exit_preis      numeric,
    einstiegsgruende jsonb      not null default '[]'::jsonb,
    notiz           text,
    screenshot_path text,                             -- Pfad im Storage-Bucket 'screenshots'
    pnl_eur         numeric,
    mentor_feedback text,
    mentor_model    text
);

create index if not exists trades_location_idx on public.trades (location_slug);
create index if not exists trades_created_idx  on public.trades (created_at desc);

-- 2) Storage-Bucket für Screenshots (privat) -----------------------------------
insert into storage.buckets (id, name, public)
values ('screenshots', 'screenshots', false)
on conflict (id) do nothing;

-- HINWEIS ----------------------------------------------------------------------
-- Die App verbindet sich mit dem service_role-Key (server-seitig in den
-- Streamlit-Secrets). Damit ist Row Level Security nicht erforderlich und der
-- Zugriff erfolgt ausschließlich über die passwortgeschützte App.
-- RLS bleibt daher deaktiviert (Default). Der App-Zugang wird über APP_PASSWORD
-- geschützt. service_role-Key NIEMALS im Frontend/öffentlich verwenden.
