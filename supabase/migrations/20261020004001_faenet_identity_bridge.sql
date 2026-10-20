BEGIN;
CREATE TABLE public.faenet_subjects (
  username text PRIMARY KEY REFERENCES public.users(username),
  subject text NOT NULL UNIQUE
);
CREATE TABLE public.faenet_grants (
  code_hash text PRIMARY KEY,
  username text NOT NULL REFERENCES public.users(username),
  auth_version bigint NOT NULL,
  challenge text NOT NULL,
  expires_at bigint NOT NULL,
  token_hash text UNIQUE,
  token_expires_at bigint
);
ALTER TABLE public.faenet_subjects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.faenet_grants ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.faenet_subjects,public.faenet_grants FROM PUBLIC,anon,authenticated;
COMMIT;
