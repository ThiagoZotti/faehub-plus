-- Photos remain private to the Flask account session. No public Data API access.
CREATE TABLE public.profile_photos (
    username TEXT PRIMARY KEY REFERENCES public.users(username) ON DELETE CASCADE,
    content BYTEA NOT NULL CHECK(octet_length(content) BETWEEN 1 AND 196608),
    revision TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.profile_photos ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.profile_photos FROM PUBLIC, anon, authenticated;
