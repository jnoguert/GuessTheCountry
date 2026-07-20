-- pgTAP suite for the leaderboard RLS invariants only (NOT the scoring
-- formula or anti-abuse business logic -- that's covered by the Deno
-- integration tests in supabase/functions/submit-score/test.ts, which
-- exercise the real HTTP+JWT path that these SQL-role simulations bypass).
--
-- Run with: supabase test db
begin;
select plan(11);

-- A fixed "player" id to simulate an authenticated user's own row.
-- (Not a real auth.users row -- these tests only exercise RLS, not FKs
-- across schemas, so profiles/scores inserts here intentionally target
-- rows that would fail their FK in a real session; the assertions below
-- only care whether RLS lets the statement past, not whether it commits
-- cleanly against auth.users.)

------------------------------------------------------------------
-- Public reads: anon must be able to read everything readable
------------------------------------------------------------------
set local role anon;

select lives_ok(
  $$ select * from public.profiles limit 1 $$,
  'anon can select from profiles'
);

select lives_ok(
  $$ select * from public.scores limit 1 $$,
  'anon can select from scores'
);

select lives_ok(
  $$ select * from public.alltime_leaderboard limit 1 $$,
  'anon can select from the alltime_leaderboard view'
);

------------------------------------------------------------------
-- Writes: anon (no session at all) must be blocked from every write
------------------------------------------------------------------
select throws_ok(
  $$ insert into public.scores (user_id, puzzle_id, score, guesses, unlocks, won)
     values ('00000000-0000-0000-0000-000000000001', current_date, 100, 1, 0, true) $$,
  '42501',
  null,
  'anon cannot insert into scores (no insert policy exists at all)'
);

select throws_ok(
  $$ insert into public.profiles (id, username)
     values ('00000000-0000-0000-0000-000000000001', 'anonuser') $$,
  '42501',
  null,
  'anon cannot insert into profiles (insert policy requires auth.uid() = id)'
);

------------------------------------------------------------------
-- Authenticated as a specific uid: can claim their OWN profile row...
------------------------------------------------------------------
set local role authenticated;
set local "request.jwt.claims" to '{"sub":"00000000-0000-0000-0000-000000000002","role":"authenticated"}';

select lives_ok(
  $$ insert into public.profiles (id, username)
     values ('00000000-0000-0000-0000-000000000002', 'ownuser') $$,
  'authenticated user can insert a profile row matching their own auth.uid()'
);

-- ...but never anyone else's, even while authenticated
select throws_ok(
  $$ insert into public.profiles (id, username)
     values ('00000000-0000-0000-0000-000000000003', 'otheruser') $$,
  '42501',
  null,
  'authenticated user cannot insert a profile row for a different id'
);

-- No update policy at all -> a claimed username is immutable, even for
-- the row's own owner
select throws_ok(
  $$ update public.profiles set username = 'renamed' where id = '00000000-0000-0000-0000-000000000002' $$,
  '42501',
  null,
  'no one can update profiles.username, not even the row owner (no update policy)'
);

-- No delete policy at all
select throws_ok(
  $$ delete from public.profiles where id = '00000000-0000-0000-0000-000000000002' $$,
  '42501',
  null,
  'no one can delete a profile row (no delete policy)'
);

-- scores has NO insert policy for anyone, authenticated included -- the
-- Edge Function's service-role key is the only writer. This is the
-- single most important invariant in the whole schema: if this ever
-- starts passing, direct client score-forgery becomes possible again.
select throws_ok(
  $$ insert into public.scores (user_id, puzzle_id, score, guesses, unlocks, won)
     values ('00000000-0000-0000-0000-000000000002', current_date, 999, 0, 0, true) $$,
  '42501',
  null,
  'authenticated user cannot insert into scores directly, even for their own user_id'
);

select lives_ok(
  $$ select * from public.profiles where id = '00000000-0000-0000-0000-000000000002' $$,
  'authenticated user can read their own just-inserted profile row back'
);

select lives_ok(
  $$ select * from public.scores limit 1 $$,
  'authenticated user can select from scores (same public-read policy as anon)'
);

select * from finish();
rollback;
