"""
_demo_en_nonprofit.py — 合成示範逐字稿：民間組織受訪者 6 位
=====================================================================
虛構資料。見 demo_transcripts_en.py 的完整聲明。

這一組的設計最不對稱，也最刻意：**參與維度大量正向、回應性維度大量負向**。
倡議組織談的是自己做了多少參與工作（P），以及那些工作換到了什麼（多半是 N）。
這個「參與 P + 回應性 N」的組合是四組裡最鮮明的樣態，共現分析與
交叉表都應該抓得到；分布是設計出來的，不得據此推論任何真實組織的行為。
"""


def build(R, Q, A, C, ANT, REF, ENG, RES):

    # =================================================================
    # N01 — 身障權益倡議組織秘書長
    # 樣態：參與極強、回應性極負、預期中
    # =================================================================
    R("N01", "General secretary, disability rights organisation",
      dict(institution_type="nonprofit", role_level="senior_management",
           sector="other", experience="over_20y"),
      [
        Q("When did your organisation first hear about this system?"),

        A("From a member, not from the council. She rang the office because "
          "the crossing she uses every day to get to dialysis had changed and "
          "she couldn't work out the pattern. That was three weeks after "
          "switch-on at her junction. We then found out there had been a "
          "consultation event eight months earlier that we hadn't been "
          "invited to.",
          C(ENG, "N", "Organisation not invited to the consultation",
            "We then found out there had been a "
            "consultation event eight months earlier that we hadn't been "
            "invited to.",
            "The most directly affected constituency was absent from the "
            "engagement because it was never contacted.")),

        Q("How did the council explain that?"),

        A("That it was advertised publicly. Which it was — in the council "
          "newsletter and on the website. I've stopped being angry about this "
          "particular thing because I've heard it forty times in twenty-six "
          "years. Advertising publicly and inviting are different acts. If "
          "you want disabled people in the room you write to the six "
          "organisations in this city that have disabled members, and there "
          "are six, and we all know each other, and it takes an afternoon.",
          C(ENG, "N", "Public advertisement treated as equivalent to invitation",
            "Advertising publicly and inviting are different acts.",
            "Names the specific mechanism by which formally open engagement "
            "systematically excludes."),
          C(ENG, "P", "Specifies exactly what adequate outreach would cost",
            "you write to the six "
            "organisations in this city that have disabled members, and there "
            "are six, and we all know each other, and it takes an afternoon",
            "Constructive specification of a workable alternative, making the "
            "omission harder to justify as impractical.")),

        Q("What did you do once you knew?"),

        A("What we always do. We collected accounts — we had thirty-one "
          "members describing specific junctions within a month, with times "
          "and dates, because our members are extremely used to documenting "
          "things nobody believes. We put it into a submission with "
          "photographs and a map. We asked for a meeting.",
          C(ENG, "P", "Structured evidence gathered from members",
            "we had thirty-one "
            "members describing specific junctions within a month, with times "
            "and dates",
            "Systematic, documented engagement work producing evidence the "
            "project's own monitoring did not have.")),

        Q("Did you get the meeting?"),

        A("Yes, after four months. It was a good meeting, I want to say that. "
          "Two officers, both engaged, both took notes. And then nothing "
          "happened for seven months, and then two crossings got audible "
          "confirmation, which was one of nine things we asked for and not "
          "one of the top three.",
          C(RES, "N", "Partial response to a minor item after long delay",
            "two crossings got audible "
            "confirmation, which was one of nine things we asked for and not "
            "one of the top three",
            "Adaptation occurred, but on the least demanding item, which "
            "leaves the substantive requests unaddressed."),
          C(RES, "P", "Some change did result from the submission",
            "two crossings got audible "
            "confirmation",
            "A documented, if minimal, change traceable to the "
            "organisation's engagement. Deliberately coded alongside the "
            "negative reading of the same quote so the review interface has a "
            "genuine disagreement to resolve.")),

        Q("What were the top three?"),

        A("Longer minimum crossing intervals as a floor the model cannot go "
          "below. A published statement of how the system treats slower "
          "pedestrians. And a named person we can contact who has authority "
          "to change a junction. Nothing on that list is technically hard. "
          "The third one costs nothing at all.",
          C(ENG, "P", "Requests framed as specific and actionable",
            "A published statement of how the system treats slower "
            "pedestrians. And a named person we can contact who has authority "
            "to change a junction.",
            "Engagement expressed as concrete asks rather than general "
            "objection, removing ambiguity about what response would count."),
          C(RES, "N", "Costless request also refused",
            "The third one costs nothing at all.",
            "The failure to act cannot be attributed to resource constraint "
            "in at least one instance.")),

        Q("Has this changed how you approach the next project?"),

        A("We now ask to be on the distribution list before there is a "
          "project. Not for consultations — for the list of things being "
          "considered. Consultation is too late by definition. I've said that "
          "in every submission I've written for a decade and I'll keep saying "
          "it until somebody puts it in a procedure.",
          C(ANT, "P", "Seeks involvement upstream of consultation",
            "We now ask to be on the distribution list before there is a "
            "project. Not for consultations — for the list of things being "
            "considered.",
            "Anticipatory strategy aimed at the point where influence is "
            "still possible.")),
      ],
      "The most affected constituency, and the one that learned of the system "
      "from a member rather than the council. The account turns on a "
      "distinction the respondent has made for twenty-six years: advertising "
      "publicly and inviting are different acts, and adequate outreach here "
      "would have taken an afternoon. Her organisation produced thirty-one "
      "documented member accounts within a month. Of nine requests, one was "
      "met — audible confirmation at two crossings — after eleven months, and "
      "not one of the top three, including one that costs nothing."),

    # =================================================================
    # N02 — 社區發展協會理事
    # 樣態：參與強、反思性中、對回應性負向、預期弱
    # =================================================================
    R("N02", "Board member, neighbourhood residents' association",
      dict(institution_type="nonprofit", role_level="other",
           sector="other", experience="6_10y"),
      [
        Q("How did your association get involved?"),

        A("We weren't, at first. Somebody forwarded the newsletter item to "
          "our group chat and about six of us went to the session out of "
          "curiosity. We're not a campaign group, we run a summer fair and "
          "argue about parking. But we're the only organised body in this "
          "part of town, so if we don't turn up nobody from here does.",
          C(ENG, "P", "Local body attends because no one else will",
            "we're the only organised body in this "
            "part of town, so if we don't turn up nobody from here does",
            "Voluntary engagement filling a structural gap in who is "
            "represented.")),

        Q("What was the session like?"),

        A("Professional. Slides, a model of a junction, sandwiches. Everyone "
          "was polite. What I noticed afterwards, walking home, was that we'd "
          "spent ninety minutes being told how it worked and about eleven "
          "minutes on questions, and both the questions that got detailed "
          "answers were from the man who turned out to be from a supplier.",
          C(ENG, "N", "Session structured overwhelmingly as transmission",
            "we'd "
            "spent ninety minutes being told how it worked and about eleven "
            "minutes on questions",
            "The format allocated almost all available time to explanation "
            "rather than to hearing."),
          C(REF, "P", "Notices who the format actually served",
            "both the questions that got detailed "
            "answers were from the man who turned out to be from a supplier",
            "Reflective observation about whose participation the setting "
            "was equipped to handle.")),

        Q("Did you raise anything?"),

        A("I asked whether the cameras could see into flats. I was told no, "
          "the field of view is set to the carriageway. Which I believe. But "
          "I'd asked because a neighbour asked me to ask, and when I went "
          "back and told her 'they said no', she said 'well they would'. And "
          "I had nothing. I couldn't show her anything. That's the bit that "
          "stayed with me — I was given an answer I couldn't pass on.",
          C(ENG, "N", "Answers not in a form that could be relayed",
            "I was given an answer I couldn't pass on.",
            "Engagement fails at the point of transmission back to the "
            "community, leaving the representative without standing."),
          C(REF, "P", "Recognises the limit of his own intermediary role",
            "I couldn't show her anything.",
            "Examines what his participation could and could not actually "
            "achieve for the person who sent him.")),

        Q("Has anyone from the council been back since?"),

        A("No. And in fairness we haven't asked them to. There's a thing that "
          "happens where both sides decide the relationship is over and "
          "nobody says so. I could email. I haven't emailed. It's been "
          "fourteen months.",
          C(RES, "N", "Relationship lapsed without either side ending it",
            "There's a thing that "
            "happens where both sides decide the relationship is over and "
            "nobody says so.",
            "No standing mechanism keeps the connection alive, so it decays "
            "by default."),
          C(REF, "P", "Includes his own inaction in the account",
            "I could email. I haven't emailed. It's been "
            "fourteen months.",
            "Refuses to place the failure entirely on the institution.")),

        Q("Would you go to the next one?"),

        A("Yes. Lower expectations, but yes. The thing I'd do differently is "
          "bring three people instead of six and give each of them one "
          "question written down beforehand, because what happened was six of "
          "us went and nobody asked the thing we'd all agreed in the group "
          "chat that somebody should ask.",
          C(ENG, "P", "Concrete tactical learning for the next engagement",
            "bring three people instead of six and give each of them one "
            "question written down beforehand",
            "Engagement capability developed through reflection on what went "
            "wrong last time.")),
      ],
      "A residents' association that attends because nobody else from the "
      "area will. The account is precise about format: ninety minutes of "
      "explanation, eleven minutes of questions, and the two questions "
      "answered in detail came from a supplier. His central difficulty is "
      "that he was given an answer he could not pass on — no document, "
      "nothing to show the neighbour who sent him. Fourteen months on, "
      "neither side has ended the relationship and neither has continued it, "
      "which he attributes partly to himself."),

    # =================================================================
    # N03 — 數位權利倡議者
    # 樣態：預期強、參與強、回應性極負、反思性中
    # =================================================================
    R("N03", "Campaigner, digital rights organisation",
      dict(institution_type="nonprofit", role_level="other",
           sector="ict_ai", experience="6_10y"),
      [
        Q("What's your organisation's interest here?"),

        A("Function creep, mainly. A camera installed to count pedestrians is "
          "a camera. The counting is a software decision and software "
          "decisions get revisited. Our position isn't that anyone here "
          "intends to do anything else with it — I've met these officers, "
          "they don't — it's that intent isn't a control. The people who make "
          "the decision in 2031 haven't been hired yet.",
          C(ANT, "P", "Function creep framed as a governance problem",
            "intent isn't a control. The people who make "
            "the decision in 2031 haven't been hired yet",
            "Anticipation directed at institutional continuity rather than "
            "at current actors' intentions."),
          C(REF, "P", "Separates the individuals from the structure",
            "Our position isn't that anyone here "
            "intends to do anything else with it — I've met these officers, "
            "they don't",
            "Deliberate refusal of an easy adversarial framing, locating the "
            "problem structurally.")),

        Q("What have you asked for?"),

        A("A purpose limitation clause in the contract with a technical "
          "control behind it — not just 'we won't', but a configuration the "
          "vendor cannot change without a council resolution. And an annual "
          "public statement of every purpose the data has been used for, "
          "including refused requests. Both are ordinary in other sectors.",
          C(ANT, "P", "Technical control proposed alongside the policy clause",
            "not just 'we won't', but a configuration the "
            "vendor cannot change without a council resolution",
            "Anticipates that a policy commitment without a technical "
            "constraint will not survive institutional turnover.")),

        Q("What response did you get?"),

        A("We got a two-page letter which restated the existing data "
          "protection position and did not address either request. I want to "
          "be precise: it wasn't a refusal. Nobody said no. The letter simply "
          "answered a different question. That's the most common response we "
          "get and it's the hardest to escalate, because on paper we were "
          "answered.",
          C(RES, "N", "Response answers a question that was not asked",
            "it wasn't a refusal. Nobody said no. The letter simply "
            "answered a different question.",
            "A specific failure mode of responsiveness: the appearance of "
            "reply without engagement with the substance."),
          C(RES, "N", "No escalation route from a non-answer",
            "That's the most common response we "
            "get and it's the hardest to escalate, because on paper we were "
            "answered.",
            "The absence of a mechanism to challenge a formally adequate but "
            "substantively empty reply.")),

        Q("Have you worked with other groups on this?"),

        A("Yes, and that's been the more productive part. We ran a joint "
          "session with the disability organisation and the residents' "
          "association — about forty people, in a community hall, no slides. "
          "We learned more in two hours than in a year of correspondence, and "
          "the disability group's point about slower pedestrians is now in "
          "everything we write, which it wasn't before.",
          C(ENG, "P", "Cross-organisation session shaped the campaign position",
            "the disability group's point about slower pedestrians is now in "
            "everything we write, which it wasn't before",
            "Engagement that visibly changed the engaging party's own "
            "position — the test the respondent applies to others."),
          C(REF, "P", "Applies to himself the standard applied to the council",
            "We learned more in two hours than in a year of correspondence",
            "Implicit scrutiny of the campaign's own prior methods.")),

        Q("What would count as success?"),

        A("A published purpose register that somebody outside the council "
          "updates. Not us — we're not neutral and we shouldn't be trusted "
          "with it either. That's the part campaigners get wrong: we ask for "
          "oversight and then assume we're the oversight.",
          C(REF, "P", "Declines to position his own organisation as oversight",
            "we're not neutral and we shouldn't be trusted "
            "with it either. That's the part campaigners get wrong",
            "Critical examination of a habit in the respondent's own "
            "advocacy community.")),
      ],
      "A campaigner who deliberately declines the adversarial framing: the "
      "officers do not intend function creep, but intent is not a control and "
      "the people deciding in 2031 have not been hired. His asks are precise "
      "— a purpose limitation with a technical control behind it, and an "
      "annual public statement of uses including refused requests. The reply "
      "was a two-page letter that answered a different question, which he "
      "identifies as the hardest response to escalate because on paper it "
      "counts as an answer. He applies his own standard to himself, declining "
      "to position his organisation as the oversight it demands."),

    # =================================================================
    # N04 — 高齡者服務機構主任
    # 樣態：參與強（實務）、回應性負、預期正（在地知識）
    # =================================================================
    R("N04", "Director, older people's community service",
      dict(institution_type="nonprofit", role_level="middle_management",
           sector="other", experience="11_20y"),
      [
        Q("How does this show up in your work?"),

        A("In cancelled appointments, mostly. We run a day centre and we "
          "started seeing people arrive flustered, or not arrive. When we "
          "asked, several described the crossing on Alder Street. Not that it "
          "was dangerous — that it was unpredictable, so they'd started "
          "leaving fifteen minutes earlier, and some had started not coming "
          "on bad weather days because the margin wasn't there.",
          C(ANT, "P", "Local knowledge surfaces an effect nobody measured",
            "some had started not coming "
            "on bad weather days because the margin wasn't there",
            "Identifies a real behavioural consequence — withdrawal from "
            "services — that no part of the project's assessment would have "
            "captured."),
          C(ANT, "N", "Unpredictability not treated as a design outcome",
            "Not that it "
            "was dangerous — that it was unpredictable",
            "The system was assessed for safety and throughput; "
            "predictability, which is what these users needed, was not an "
            "assessed property.")),

        Q("Did you report it?"),

        A("I wrote to the transport department with the numbers. Nineteen "
          "people, over six weeks, with the dates. I got an acknowledgement "
          "within two days and then nothing for five months, then a letter "
          "saying detection accuracy at that junction was within "
          "specification.",
          C(ENG, "P", "Quantified account submitted through a formal channel",
            "I wrote to the transport department with the numbers. Nineteen "
            "people, over six weeks, with the dates.",
            "Structured evidence provided in the form the institution asks "
            "for."),
          C(RES, "N", "Reply addressed accuracy, not the reported problem",
            "a letter "
            "saying detection accuracy at that junction was within "
            "specification",
            "The response answers a technical question that was not the one "
            "raised, leaving the described harm unaddressed.")),

        Q("What would have been a useful reply?"),

        A("Anything that engaged with unpredictability. 'We measure accuracy, "
          "we don't measure consistency, we'll look at whether we can.' That "
          "would have been a good answer and it costs nothing to write. I "
          "don't need them to fix it in a fortnight. I need to know the "
          "problem I described has been understood.",
          C(RES, "N", "No acknowledgement that the problem was understood",
            "I need to know the "
            "problem I described has been understood.",
            "The minimum condition for responsiveness — demonstrating "
            "comprehension of the input — was not met.")),

        Q("Have you found any other route?"),

        A("Our councillor. She raised it and something moved — the crossing "
          "minimum at Alder went up. I'm glad. I'm also aware that the route "
          "that worked was knowing a councillor, and most organisations like "
          "ours don't have that, and it shouldn't be how this works.",
          C(RES, "P", "Crossing minimum raised after political escalation",
            "She raised it and something moved — the crossing "
            "minimum at Alder went up.",
            "A concrete change occurred, traceable to the reported problem."),
          C(ENG, "N", "The effective route depends on personal access",
            "the route "
            "that worked was knowing a councillor, and most organisations like "
            "ours don't have that",
            "Influence is distributed by connection rather than by the "
            "substance of the concern.")),

        Q("Do the people who use your centre know any of this happened?"),

        A("Some do. I told the ones who'd told me, because that seemed like "
          "the least I could do. What I couldn't tell them is why it took "
          "eight months, because I don't know, and 'I don't know' after eight "
          "months is not a good thing to say to somebody who missed "
          "appointments over it.",
          C(ENG, "P", "Reports back to the people who raised the problem",
            "I told the ones who'd told me, because that seemed like "
            "the least I could do.",
            "Closing the loop with participants, which the institutions in "
            "this account did not do.")),
      ],
      "A service provider who noticed the system in cancelled appointments. "
      "Her clients did not find the crossing dangerous; they found it "
      "unpredictable, so they left earlier and, on bad weather days, stopped "
      "coming — a withdrawal from services that no project metric would "
      "capture. Nineteen documented cases produced a five-month silence and "
      "then a letter about detection accuracy. What eventually worked was "
      "knowing a councillor, which she is careful to say should not be how "
      "this works."),

    # =================================================================
    # N05 — 單車與行人倡議組織志工
    # 樣態：參與強、預期中、回應性混合、反思性正
    # =================================================================
    R("N05", "Volunteer coordinator, walking and cycling advocacy group",
      dict(institution_type="nonprofit", role_level="other",
           sector="other", experience="under_5y"),
      [
        Q("You did your own measurement, I understand."),

        A("We did. Twenty-two volunteers, four Saturdays, stopwatches and a "
          "clipboard at fourteen junctions. Deliberately low-tech, because we "
          "wanted anybody to be able to check what we'd done. We measured "
          "wait time from arrival at the kerb to green, which is the number "
          "that matters to a person and is not the number anybody publishes.",
          C(ENG, "P", "Volunteer measurement designed to be checkable",
            "Twenty-two volunteers, four Saturdays, stopwatches and a "
            "clipboard at fourteen junctions. Deliberately low-tech, because we "
            "wanted anybody to be able to check what we'd done.",
            "Engagement that produces evidence and, by design, makes the "
            "evidence contestable by others."),
          C(ANT, "P", "Measures the quantity that matters to pedestrians",
            "We measured "
            "wait time from arrival at the kerb to green, which is the number "
            "that matters to a person and is not the number anybody publishes.",
            "Identifies the gap between the published metric and the "
            "experienced one before any harm is formally recognised.")),

        Q("What did you find?"),

        A("Median wait went down. I'll say that first because it's what we "
          "found and it wasn't what we expected. Median wait went down by "
          "about nine seconds. The ninetieth percentile went up by about "
          "twenty-six. So most crossings got a bit better and the bad ones "
          "got noticeably worse, and if you only publish the median you would "
          "report this as a success.",
          C(REF, "P", "Reports the finding that contradicted expectation",
            "Median wait went down. I'll say that first because it's what we "
            "found and it wasn't what we expected.",
            "Willingness to lead with evidence against the group's own prior "
            "position."),
          C(ANT, "P", "Distributional finding in the tail",
            "The ninetieth percentile went up by about "
            "twenty-six. So most crossings got a bit better and the bad ones "
            "got noticeably worse",
            "Surfaces the concentration of harm that an aggregate measure "
            "conceals.")),

        Q("How was that received?"),

        A("Better than the campaigning stuff we've sent before, honestly, and "
          "I think it's because we led with the good news. An officer emailed "
          "and asked for our raw sheets, which we sent. Nothing changed at a "
          "junction as a result, but the ninetieth percentile now appears in "
          "the monthly summary, and it didn't before.",
          C(RES, "P", "Reporting practice changed to include the tail",
            "the ninetieth percentile now appears in "
            "the monthly summary, and it didn't before",
            "A durable change to what the institution measures and publishes, "
            "which affects every future assessment."),
          C(RES, "N", "No junction changed as a result",
            "Nothing changed at a junction as a result",
            "The substantive conditions the survey documented were not "
            "altered.")),

        Q("Will you repeat the survey?"),

        A("Yes, same four Saturdays next year, same junctions, same method — "
          "the point is the comparison, so we can't improve the method even "
          "where we now know it's weak. That's frustrating and it's the right "
          "call.",
          C(ANT, "P", "Method held constant to preserve comparability",
            "the point is the comparison, so we can't improve the method even "
            "where we now know it's weak",
            "Forward-looking design choice that trades present quality for "
            "the ability to detect change over time.")),

        Q("What's the weakness you'd fix if you could?"),

        A("Saturdays. We measure Saturdays because that's when volunteers are "
          "free, and Saturday is not when most people cross to get to work or "
          "school. Our entire dataset describes a day that isn't "
          "representative and I'd rather say that out loud than have somebody "
          "find it.",
          C(REF, "P", "States the sampling limitation unprompted",
            "Our entire dataset describes a day that isn't "
            "representative and I'd rather say that out loud than have somebody "
            "find it.",
            "Critical scrutiny of the group's own evidence, disclosed in "
            "advance of challenge.")),
      ],
      "The most methodologically self-aware of the community accounts. "
      "Twenty-two volunteers with stopwatches measured kerb-to-green wait "
      "time — the quantity that matters to a pedestrian and that nobody "
      "publishes — and found the median improved by nine seconds while the "
      "ninetieth percentile worsened by twenty-six. The group led with the "
      "finding that contradicted its own expectations, and got a durable "
      "result: the ninetieth percentile now appears in the monthly summary. "
      "No junction changed. He volunteers the sampling weakness before anyone "
      "can find it."),

    # =================================================================
    # N06 — 在地慈善組織執行長
    # 樣態：全面偏負向，對參與機制本身失去信心
    # =================================================================
    R("N06", "Chief executive, local community foundation",
      dict(institution_type="nonprofit", role_level="senior_management",
           sector="other", experience="11_20y"),
      [
        Q("Your foundation was named as a community partner. What did that "
          "involve?"),

        A("Being named. I mean that literally — I found out we were a "
          "community partner when I read it in the bid summary after the "
          "award. Somebody had listed us. Nobody had asked us. We'd had one "
          "phone call eighteen months earlier about something adjacent.",
          C(ENG, "N", "Partnership asserted without the partner's involvement",
            "I found out we were a "
            "community partner when I read it in the bid summary after the "
            "award. Somebody had listed us. Nobody had asked us.",
            "The appearance of community involvement is manufactured without "
            "any actual relationship.")),

        Q("Did you object?"),

        A("I wrote and asked to be removed, and we were, from the next "
          "version. But the version with our name in it is the one that won "
          "the contract, and there's no mechanism to unwind that. The bid was "
          "evaluated partly on community partnership that didn't exist.",
          C(RES, "N", "Correction cannot reach the decision it affected",
            "the version with our name in it is the one that won "
            "the contract, and there's no mechanism to unwind that",
            "A factual correction is accepted but has no effect on the "
            "outcome it should have altered.")),

        Q("Has anything happened since?"),

        A("We were invited to a launch event, which I didn't attend, and to a "
          "'community reference group' which met twice and then stopped. I "
          "don't know that it was cancelled. It simply stopped being "
          "scheduled. Nobody wrote to say it had ended.",
          C(ENG, "N", "Reference group lapsed without notice",
            "It simply stopped being "
            "scheduled. Nobody wrote to say it had ended.",
            "A participation structure disappears without a decision, notice "
            "or record.")),

        Q("Do you think the reference group could have worked?"),

        A("Possibly, with two changes. Somebody senior in the room, and a "
          "written response to whatever it produced within a fixed period. "
          "Without those two things a reference group is a mailing list with "
          "sandwiches. I've sat on eleven of them in this job and three "
          "worked, and all three had those two features.",
          C(ENG, "P", "Names the two conditions that distinguish working groups",
            "Somebody senior in the room, and a "
            "written response to whatever it produced within a fixed period.",
            "Constructive specification derived from the respondent's own "
            "comparative experience across eleven such groups."),
          C(REF, "P", "Grounds the judgement in a counted comparison",
            "I've sat on eleven of them in this job and three "
            "worked, and all three had those two features.",
            "The claim is offered with the evidence base and the failure rate "
            "attached rather than as a general complaint.")),

        Q("Would you take part in the next one?"),

        A("Probably not, and I've thought about whether that's the right "
          "call. My concern is that our attendance is what makes the process "
          "look legitimate. If we sit in the room and nothing changes, the "
          "report says the community was consulted, and our presence has been "
          "used against the people we exist to serve. Declining is also a bad "
          "option. There isn't a good one.",
          C(ENG, "N", "Participation risks legitimating an empty process",
            "If we sit in the room and nothing changes, the "
            "report says the community was consulted, and our presence has been "
            "used against the people we exist to serve.",
            "The engagement mechanism has become counterproductive for the "
            "participants it nominally serves."),
          C(REF, "P", "Weighs withdrawal as itself a costly choice",
            "Declining is also a bad "
            "option. There isn't a good one.",
            "Refuses a self-flattering resolution, holding both options open "
            "as damaging.")),
      ],
      "The account of a named community partner who was never asked. The "
      "bid that won the contract listed the foundation without contact, and "
      "although the name was removed from later versions there is no "
      "mechanism to unwind the evaluation it contributed to. A community "
      "reference group met twice and then simply stopped being scheduled, "
      "with no notice that it had ended. Drawing on eleven such groups, three "
      "of which worked, he specifies exactly what distinguishes them — and "
      "then sets out why participating and declining are both bad options.")
