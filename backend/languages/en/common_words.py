"""Tiny frequency list used to decide whether a word needs IPA help.

A ~500-word core is enough for MVP: if the word isn't here, we consider
it "possibly new" and attach IPA. Phase 5 can swap in a real 5000-word
frequency list from a corpus.
"""
from __future__ import annotations

_CORE = """
the be to of and a in that have i it for not on with he as you do at
this but his by from they we say her she or an will my one all would there their
what so up out if about who get which go me when make can like time no just him know take
people into year your good some could them see other than then now look only come its over think also
back after use two how our work first well way even new want because any these give day most us
is are was were been being am has had having did does done said went got gotten making putting
going coming taking getting giving seeing looking wanting working thinking saying needing
very really pretty actually sure okay please thanks thank sorry yes no maybe perhaps yeah
man woman child boy girl person people family friend house home school office car bus
cat dog bird horse cow pig sheep mouse rabbit chicken duck
room door window table chair bed book pen paper phone computer
street road city town country park store shop market hospital
day night morning afternoon evening week month year today yesterday tomorrow
water food coffee tea beer wine bread meat fish rice egg fruit apple orange
red blue green yellow black white big small long short high low old new
happy sad angry tired hungry thirsty cold hot warm cool
go come eat drink sleep read write talk speak listen hear play walk run stand sit
yes no hello hi goodbye bye thanks welcome excuse sorry okay right wrong true false
one two three four five six seven eight nine ten eleven twelve twenty thirty forty fifty hundred thousand
today tomorrow yesterday always never sometimes often usually rarely
where when why how who what which whose whom
me you him us them mine yours his hers theirs ours
a an the some any all many much few little more less most least
very quite rather too so such enough just only still already yet
and or but nor for because since if unless while although though however therefore thus
in on at by with without through during before after until from to into onto upon above below inside outside
""".split()

COMMON_WORDS: frozenset[str] = frozenset(w.lower() for w in _CORE if w)
