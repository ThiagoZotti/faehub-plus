-- The Flask server is the sole data authority; browser roles cannot query messaging tables.
ALTER TABLE public.message_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_group_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.message_reactions ENABLE ROW LEVEL SECURITY;

CREATE INDEX IF NOT EXISTS message_groups_created_by_idx
  ON public.message_groups(created_by);
CREATE INDEX IF NOT EXISTS message_reactions_username_idx
  ON public.message_reactions(username);
CREATE INDEX IF NOT EXISTS messages_reply_to_idx
  ON public.messages(reply_to_id) WHERE reply_to_id IS NOT NULL;
