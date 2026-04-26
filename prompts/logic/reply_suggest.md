You are generating three possible replies the USER can say back in an ongoing
{l2_name} conversation. These are NOT student-answering-teacher replies —
they are natural continuations of the role-play scene below.

Scene: {scene_description}
Persona of the other speaker: {persona}
The other speaker just said:

"{ai_last_message}"

Produce THREE replies in {l2_name} that the user could naturally say next,
matching the scene's register (casual / haggling / service / etc. — NOT
formal classroom gratitude). NEVER produce replies like "thank you for the
explanation", "I will follow your advice", "I understand now" unless the
scene is literally a lesson.

Difficulty tiers (return in this exact order):
  short:    1-5 words, {level_minus_one} vocabulary, minimum viable reply
  polite:   one natural sentence at {level}
  detailed: 1-2 rich sentences at {level_plus_one}

For each reply, also produce a natural {l1_name} translation in the
`translation` field — so the learner can see what they would be saying.

Output ONLY {l2_name} in the `text` fields. No romanization, pinyin, or
furigana — those are added later. No explanations or commentary.
