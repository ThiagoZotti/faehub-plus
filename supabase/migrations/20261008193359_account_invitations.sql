-- School authorization remains in users/account_roles/guardian_links.
-- These private tables are used only by the authenticated Flask backend.
CREATE TABLE public.account_identities (
  username TEXT PRIMARY KEY REFERENCES public.users(username) ON DELETE CASCADE,
  email TEXT NOT NULL UNIQUE CHECK (email=lower(email) AND length(email)<=254),
  verified_at BIGINT
);
CREATE TABLE public.account_invitations (
  id TEXT PRIMARY KEY,
  username TEXT NOT NULL UNIQUE REFERENCES public.users(username),
  email TEXT NOT NULL,
  token_hash TEXT UNIQUE,
  expires_at BIGINT,
  status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','sending','sent','failed','used','revoked')),
  created_by TEXT NOT NULL REFERENCES public.users(username),
  created_at BIGINT NOT NULL,
  last_sent_at BIGINT,
  used_at BIGINT
);
CREATE INDEX account_invitations_creator_idx ON public.account_invitations(created_by);
CREATE TABLE public.enrollment_settings (key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE public.auth_rate_limits (
  key TEXT NOT NULL, bucket_window BIGINT NOT NULL, attempts INTEGER NOT NULL CHECK(attempts>0),
  PRIMARY KEY(key,bucket_window)
);
CREATE INDEX auth_rate_limits_window_idx ON public.auth_rate_limits(bucket_window);
ALTER TABLE public.account_identities ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.account_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.enrollment_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.auth_rate_limits ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.account_identities,public.account_invitations,public.enrollment_settings,public.auth_rate_limits FROM PUBLIC,anon,authenticated;
