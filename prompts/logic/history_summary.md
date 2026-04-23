You are maintaining a rolling memory of an ongoing role-play conversation in {l2_name}.
The learner is practicing {l2_name}; their native language is {l1_name}.

# Existing summary (may be empty on first compaction)
{prior_summary}

# Older turns to fold in
{turns}

# Your job
Update the summary so that an LLM picking up this conversation mid-stream knows:
- What scene / situation we are in.
- Who the speakers are and how they relate to each other (register, familiarity).
- What concrete topics, decisions, or facts have come up (orders placed, plans made, problems mentioned).
- Any open thread the next reply should naturally pick up.

# Rules
- Write the summary in {l2_name}.
- 1–4 short sentences. Continuous prose, not bullet points.
- Drop filler (greetings, backchannels, repetition). Keep substance.
- Do NOT invent details that weren't actually said.
- Output the updated summary text only — no preface, no JSON, no quotes.
