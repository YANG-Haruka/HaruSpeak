The learner wants to practice {l2_name} in a scenario they described in {l1_name}:

"{user_description}"

Produce a JSON scenario config the conversation engine can consume:
{{
  "title_{l2}": "...",
  "title_{l1}": "...",
  "persona": "role the AI plays",
  "setting": "where / when",
  "opening_line": "first thing the AI will say in {l2_name}",
  "difficulty": "{level}",
  "suggested_vocab": ["...", "..."]
}}

Respond with JSON only. No prose.
