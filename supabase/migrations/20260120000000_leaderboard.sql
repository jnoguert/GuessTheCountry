-- Leaderboard schema: anonymous-auth identity (profiles) + daily scores.
-- See supabase/functions/submit-score/index.ts for the only write path into
-- `scores` -- there is deliberately no INSERT policy on that table at all.

create extension if not exists citext with schema extensions;

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  -- Schema-qualified: on hosted Supabase the `extensions` schema isn't in the
  -- migration search_path, so a bare `citext` fails to resolve (SQLSTATE 42704).
  username extensions.citext unique not null
    check (char_length(username) between 3 and 20 and username ~ '^[A-Za-z0-9_-]+$'),
  created_at timestamptz not null default now()
);

create table public.scores (
  user_id    uuid not null references public.profiles(id) on delete cascade,
  puzzle_id  date not null,
  score      int not null check (score >= 0),
  guesses    int not null check (guesses between 0 and 5),
  unlocks    int not null check (unlocks between 0 and 3),
  won        boolean not null,
  easy_mode  boolean not null default false,
  created_at timestamptz not null default now(),
  primary key (user_id, puzzle_id)
);

create index idx_scores_leaderboard on public.scores (puzzle_id, score desc, guesses asc, created_at asc);

alter table public.profiles enable row level security;
alter table public.scores enable row level security;

create policy "profiles are publicly readable" on public.profiles for select using (true);
create policy "users can insert their own profile" on public.profiles for insert with check (auth.uid() = id);
-- No update/delete policy on profiles -> a claimed username is immutable.

create policy "scores are publicly readable" on public.scores for select using (true);
-- No insert policy on scores at all -> only the Edge Function, using the
-- service-role key, can write. This is the entire security boundary for
-- writes; see supabase/tests/database/rls.test.sql for the invariant test.

grant select on public.profiles, public.scores to anon, authenticated;

create view public.alltime_leaderboard as
  select p.username, sum(s.score) as total_score, sum(s.won::int) as wins, count(*) as games
  from public.scores s join public.profiles p on p.id = s.user_id
  group by p.username
  order by total_score desc, wins desc, games asc;

grant select on public.alltime_leaderboard to anon, authenticated;
