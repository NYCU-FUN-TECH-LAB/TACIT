"""
_demo_en_industry.py — 合成示範逐字稿：產業界受訪者 6 位
=====================================================================
虛構資料。見 demo_transcripts_en.py 的完整聲明。

這一組刻意偏負向（約七成 N）。真實研究裡承包商與供應商確實較常把
社會影響劃在守備範圍之外，但這裡的分布是**設計出來的**，目的是讓
機構類型 × 極性的交叉表有東西可看；不得據此推論任何真實產業的行為。
"""


def build(R, Q, A, C, ANT, REF, ENG, RES):

    # =================================================================
    # P01 — 系統整合商 專案總監
    # 樣態：技術決定論、以專業權威排除外部意見、把參與當成告知
    # =================================================================
    R("P01", "Project director, systems integration contractor",
      dict(institution_type="industry", role_level="senior_management",
           sector="ict_ai", experience="11_20y"),
      [
        Q("Let's start with the beginning of the project. When Port Calder "
          "brought you in, how did you assess what this system might do to "
          "the city?"),

        A("Right, so — I want to split that into two parts, because people "
          "conflate them. On the technical side, absolutely, we ran a full "
          "assessment. False positive rate, detection accuracy under rain, "
          "night performance, we have an internal acceptance standard that's "
          "frankly stricter than what the city asked for. That part I'm "
          "confident about. But social impact, what it does to the city as a "
          "city — honestly, that's not our remit. We're a contractor. The "
          "city writes a specification, we build to the specification. "
          "That's the arrangement.",
          C(ANT, "N", "Impact assessment scoped to technical performance only",
            "social impact, what it does to the city as a city — honestly, "
            "that's not our remit. We're a contractor. The "
            "city writes a specification, we build to the specification.",
            "Anticipation is confined to engineering metrics; wider "
            "consequences are explicitly placed outside the frame of "
            "responsibility rather than being explored.")),

        Q("Was there any discussion early on about unintended consequences?"),

        A("Unintended consequences. Look, I'll probably sound naive saying "
          "this, but smart infrastructure is where everything is going. Every "
          "city in the region is doing it. If we don't do it someone else "
          "will, so it's a question of when, not whether. Sitting around "
          "imagining what might go wrong is, in my experience, a way of not "
          "shipping anything. Build it, see what breaks, fix what breaks. "
          "And a lot of the concerns people raise, with respect, come from "
          "not understanding the technology. Once the thing is running and "
          "people's commutes get shorter, that noise dies down on its own.",
          C(ANT, "N", "Technological inevitability closes off foresight",
            "smart infrastructure is where everything is going. Every "
            "city in the region is doing it. If we don't do it someone else "
            "will, so it's a question of when, not whether.",
            "Framing deployment as inevitable removes the space in which "
            "alternative futures could be considered — the defining move of "
            "deterministic, non-anticipatory reasoning."),
          C(REF, "N", "Concerns attributed to public ignorance",
            "a lot of the concerns people raise, with respect, come from "
            "not understanding the technology",
            "The respondent locates the problem entirely in the public's "
            "comprehension rather than examining the assumptions built into "
            "his own team's work.")),

        Q("Were community groups or residents involved in the design?"),

        A("Yes, there was a public information session. The city organised "
          "it — March last year, I think, in the council building. We "
          "presented the system, what it does, the expected benefits. "
          "Turnout was modest, twenty-five, thirty people.",
          C(ENG, "N", "Engagement realised as a one-way briefing",
            "there was a public information session. The city organised "
            "it — March last year, I think, in the council building. We "
            "presented the system, what it does, the expected benefits.",
            "The only engagement described is a presentation of a finished "
            "design; there is no mechanism by which attendees could shape "
            "anything.")),

        Q("Was that before or after the design was finalised?"),

        A("After. The specification was locked by then, it had to be, because "
          "you can't tender against a moving target. Once the tender "
          "documents go out, that's it. So the session was more about — "
          "letting people know what was coming. Changing the design in that "
          "room wasn't realistic. The whole procurement would have to start "
          "again and somebody would have to answer for that.",
          C(ENG, "N", "Procurement timing forecloses influence",
            "The specification was locked by then, it had to be, because "
            "you can't tender against a moving target.",
            "Engagement is scheduled after the point at which it could "
            "affect the outcome, making it structurally incapable of "
            "influencing design."),
          C(RES, "N", "Institutional cost cited as a reason not to adapt",
            "The whole procurement would have to start "
            "again and somebody would have to answer for that.",
            "Capacity to respond is described as blocked by procedure, with "
            "no attempt to find a route within it.")),

        Q("Did anyone at that session raise an objection?"),

        A("One woman, a wheelchair user, said the pedestrian crossing "
          "interval wasn't long enough for her. That stuck with me, actually. "
          "But the interval is set by national regulation — we can't just "
          "change it. So we explained that this was a regulatory matter, not "
          "a system matter, and that she should raise it with the ministry.",
          C(RES, "N", "Concern redirected rather than absorbed",
            "we explained that this was a regulatory matter, not "
            "a system matter, and that she should raise it with the ministry",
            "A substantive access concern is redirected to another body. "
            "Note the ambiguity: the regulatory constraint is real, so a "
            "second coder might reasonably argue this is a limit on capacity "
            "rather than a refusal to respond.")),

        Q("Looking back, is there anything you'd do differently?"),

        A("Differently. Hmm. Maybe the documentation, we could have written "
          "the user-facing documentation better. But the engineering, no. "
          "The system does what it was specified to do, within tolerance, on "
          "budget. I'd sign the same contract tomorrow.",
          C(REF, "N", "Retrospective limited to delivery performance",
            "The system does what it was specified to do, within tolerance, on "
            "budget. I'd sign the same contract tomorrow.",
            "Self-examination is bounded by contractual success criteria; "
            "the values embedded in the specification are not questioned.")),

        Q("One more — the camera data. Who holds it?"),

        A("The city holds it. We process it. There's a data-sharing agreement, "
          "it went through their legal team and ours. I couldn't tell you the "
          "retention period off the top of my head, it's in the schedule. "
          "That's genuinely not something I get asked about often, which now "
          "that you say it out loud is maybe a bit odd.",
          C(REF, "P", "Momentary recognition of an unexamined area",
            "That's genuinely not something I get asked about often, which now "
            "that you say it out loud is maybe a bit odd.",
            "A brief reflexive turn prompted by the interview itself. Coded "
            "positive but weak — it produces recognition, not action.")),
      ],
      "A contractor's account organised around scope of responsibility. "
      "Anticipation is confined to engineering tolerances and further "
      "foresight is closed off by an inevitability framing. Engagement is "
      "described sincerely but realised as a post-specification briefing, and "
      "the one substantive objection raised there is redirected to a "
      "regulator. A single reflexive moment surfaces only when the "
      "interviewer asks about data holding.")

    # =================================================================
    # P02 — AI 新創技術長
    # 樣態：預期能力強但只用於商業風險；反思性低；速度優先
    # =================================================================
    R("P02", "Chief technology officer, AI perception startup",
      dict(institution_type="industry", role_level="senior_management",
           sector="ict_ai", experience="6_10y"),
      [
        Q("Your company supplied the detection models. How do you think about "
          "what could go wrong with them?"),

        A("Constantly. That's most of my job. We model failure modes in a lot "
          "of detail — occlusion, low light, unusual gaits, people pushing "
          "strollers, cyclists dismounting. We built a whole synthetic test "
          "set for edge cases because the real data didn't have enough of "
          "them. If a detector misses a person in a wheelchair at dusk, that "
          "is a catastrophic failure for us, commercially and otherwise.",
          C(ANT, "P", "Systematic modelling of failure modes",
            "We model failure modes in a lot "
            "of detail — occlusion, low light, unusual gaits, people pushing "
            "strollers, cyclists dismounting. We built a whole synthetic test "
            "set for edge cases because the real data didn't have enough of "
            "them.",
            "Concrete, structured foresight about how the technology could "
            "fail in use. Note the ambiguity a second coder may want to argue "
            "over: the stated motivation is partly commercial exposure.")),

        Q("Beyond detection accuracy — did you look at longer-term effects? "
          "How the system might change the street over five or ten years?"),

        A("Honestly, no. We're a thirty-person company. Our runway is "
          "eighteen months. Ten-year urban effects is a question for someone "
          "with tenure. I don't say that dismissively, it's genuinely a "
          "different job from mine and I'm not equipped for it.",
          C(ANT, "N", "Long-horizon effects treated as out of scope",
            "Ten-year urban effects is a question for someone "
            "with tenure. I don't say that dismissively, it's genuinely a "
            "different job from mine and I'm not equipped for it.",
            "Long-range anticipation is displaced to other actors. The candour "
            "is notable but the effect is that no one in the project holds it.")),

        Q("Was there anyone in the consortium who did hold that question?"),

        A("Not that I saw. There was a university partner on the original "
          "bid but they dropped out over funding. After that it was three "
          "vendors and the city. Everyone in the room was optimising their "
          "own deliverable.",
          C(ANT, "N", "Foresight capacity lost without replacement",
            "There was a university partner on the original "
            "bid but they dropped out over funding. After that it was three "
            "vendors and the city.",
            "The departure of the partner most likely to raise long-horizon "
            "questions is described without any attempt to replace that role.")),

        Q("How did you decide what counted as acceptable performance?"),

        A("The city gave us a target and we beat it. Ninety-eight point five "
          "on detection, we shipped at ninety-nine point one. Where it gets "
          "uncomfortable is that the aggregate number hides the distribution. "
          "Our worst subgroup was people using mobility aids, and that number "
          "was materially lower. We flagged it, we put it in the report, and "
          "then — nobody asked about it, and we moved on. In hindsight "
          "flagging it in an appendix isn't the same as raising it.",
          C(REF, "P", "Recognises that aggregate metrics conceal distribution",
            "the aggregate number hides the distribution. "
            "Our worst subgroup was people using mobility aids, and that number "
            "was materially lower.",
            "Critical scrutiny of the team's own headline metric and what it "
            "obscures about who bears the error."),
          C(RES, "N", "Known disparity documented but not acted on",
            "We flagged it, we put it in the report, and "
            "then — nobody asked about it, and we moved on. In hindsight "
            "flagging it in an appendix isn't the same as raising it.",
            "A known inequity is recorded in a way that discharges "
            "responsibility without changing anything. The respondent's own "
            "hindsight makes this a clear case.")),

        Q("Did you speak to any disability organisations directly?"),

        A("No. We had the city's requirements document and we built to it. "
          "In retrospect that's a strange way to build something that has to "
          "detect people, isn't it — we never met any of the people the "
          "system was hardest for.",
          C(ENG, "N", "No contact with the group most affected by error",
            "We had the city's requirements document and we built to it.",
            "Requirements are received entirely through the client; the "
            "affected public has no channel into the technical work."),
          C(REF, "P", "Names the oddity of building without contact",
            "we never met any of the people the "
            "system was hardest for",
            "Reflexive recognition that the development process excluded "
            "precisely the group whose experience mattered most.")),

        Q("What would have had to be different for that to happen?"),

        A("Someone would have had to put it in the contract and pay for it. "
          "I know how that sounds. But we bid against two other firms on "
          "price. If I'd priced in a user research programme we wouldn't have "
          "won, and then you'd be interviewing whoever did.",
          C(ENG, "N", "Competitive procurement crowds out engagement",
            "we bid against two other firms on "
            "price. If I'd priced in a user research programme we wouldn't have "
            "won",
            "Engagement is described as economically irrational under the "
            "procurement design — a structural rather than attitudinal "
            "barrier, but negative in effect.")),
      ],
      "A technically sophisticated account in which anticipation is strong "
      "but bounded: failure modes are modelled in detail while long-horizon "
      "urban effects are displaced onto absent actors. The respondent shows "
      "real reflexivity about a subgroup disparity his own metrics concealed, "
      "yet the disparity was documented rather than acted on. Engagement is "
      "absent and is explained by the economics of competitive tendering.")

    # =================================================================
    # P03 — 硬體供應商 產品經理
    # 樣態：回應性有實例（修過一次），但預期與參與弱
    # =================================================================
    R("P03", "Product manager, roadside camera hardware vendor",
      dict(institution_type="industry", role_level="middle_management",
           sector="manufacturing", experience="6_10y"),
      [
        Q("Tell me about your part of the deployment."),

        A("We supply the roadside units — the housing, the sensor, the local "
          "compute. Thirty intersections, two units each, some with three "
          "where the geometry is awkward. My job is that they work in the "
          "weather and don't need a truck roll every month.",
          ),

        Q("Did anything come up after installation that you hadn't expected?"),

        A("Yes, and it's the thing I always tell people about now. About four "
          "months in we started getting complaints from residents on Fenwick "
          "Street. Turned out the units have a status LED, a small blue one, "
          "and at the height we'd mounted them on that street it was shining "
          "straight into second-floor bedrooms all night. Nobody had thought "
          "about it. It's not in any specification anywhere.",
          C(ANT, "N", "Everyday lived effects absent from specification",
            "the units have a status LED, a small blue one, "
            "and at the height we'd mounted them on that street it was shining "
            "straight into second-floor bedrooms all night. Nobody had thought "
            "about it.",
            "A mundane but real impact on residents that no part of the "
            "process anticipated, illustrating how narrow the foresight frame "
            "was.")),

        Q("What happened then?"),

        A("We fixed it. Took about six weeks. We had a shroud designed, 3D "
          "printed a batch to test, then had them injection moulded, and a "
          "crew went round and retrofitted every unit in the city, not just "
          "that street. I pushed for all of them because if it's happening "
          "there it's happening somewhere else and nobody's called yet. And "
          "we changed the mounting guidance for future installs.",
          C(RES, "P", "Substantive fix extended beyond the reported case",
            "a crew went round and retrofitted every unit in the city, not just "
            "that street. I pushed for all of them because if it's happening "
            "there it's happening somewhere else and nobody's called yet.",
            "Concrete adaptation that goes beyond the specific complaint, "
            "treating the report as evidence of a general problem."),
          C(RES, "P", "Learning fed back into standing practice",
            "we changed the mounting guidance for future installs",
            "The response is institutionalised rather than treated as a "
            "one-off remedy.")),

        Q("How did those residents reach you?"),

        A("Through the city, eventually. It went to the council, the council "
          "sat on it for a while because nobody knew whose problem it was, "
          "then it came to us. I think the first complaint was maybe five "
          "weeks before I heard about it. There's no direct line from a "
          "resident to the people who can actually fix the thing.",
          C(ENG, "N", "No direct channel between residents and builders",
            "There's no direct line from a "
            "resident to the people who can actually fix the thing.",
            "Structural absence of a route from affected residents to the "
            "party with technical capacity to act.")),

        Q("Was there consultation before installation about where units went?"),

        A("Placement was decided on traffic engineering grounds — sight "
          "lines, pole availability, power. I don't believe anyone asked "
          "residents. To be fair I'm not sure what you'd ask them. 'Do you "
          "mind a camera here' — most people would say yes they mind, and "
          "then what?",
          C(ENG, "N", "Consultation dismissed as unanswerable",
            "I don't believe anyone asked "
            "residents. To be fair I'm not sure what you'd ask them.",
            "Engagement is not merely absent but treated as having no "
            "workable form, which forecloses looking for one.")),

        Q("Has the LED episode changed how you think about new products?"),

        A("A bit. We now have a line in our design review that says 'what "
          "does this look like to somebody who lives next to it'. One line. "
          "It's not a methodology. But it's caught two things since, so I'll "
          "take it.",
          C(REF, "P", "Incident converted into a standing design question",
            "We now have a line in our design review that says 'what "
            "does this look like to somebody who lives next to it'.",
            "Modest but genuine change to how the team examines its own "
            "assumptions, with the respondent honest about its limits.")),
      ],
      "The clearest case of responsiveness in the industry group. An "
      "unanticipated everyday impact — light spill from status LEDs — was "
      "fixed thoroughly, extended to unreported sites and written into "
      "standing guidance. The same account shows why it took so long: there "
      "is no direct route from residents to the people who can act, and "
      "pre-installation consultation was dismissed as having no workable "
      "form.")

    # =================================================================
    # P04 — 法遵主管
    # 樣態：反思性強（職務使然），但參與弱；預期偏向法律風險
    # =================================================================
    R("P04", "Head of compliance, mobility technology group",
      dict(institution_type="industry", role_level="middle_management",
           sector="ict_ai", experience="over_20y"),
      [
        Q("What does responsible deployment mean in your role?"),

        A("In practice it means I am the person who asks the questions "
          "nobody wants asked, three weeks before launch, when it is "
          "expensive. I've made peace with being unpopular. The honest "
          "version is that most of what I do is legal risk, not ethics. "
          "Those overlap but they are not the same thing and I try not to "
          "pretend otherwise.",
          C(REF, "P", "Distinguishes legal risk from ethical scrutiny",
            "most of what I do is legal risk, not ethics. "
            "Those overlap but they are not the same thing and I try not to "
            "pretend otherwise.",
            "Explicit critical awareness of the limits of the respondent's "
            "own function — refusing the common conflation of compliance "
            "with responsibility.")),

        Q("What did you ask on this project?"),

        A("Three things, mainly. What happens to footage of people who "
          "aren't the subject of any incident. Whether the detection "
          "performance is uniform across body types and mobility aids. And "
          "whether the city can switch it off if it turns out to be wrong. "
          "The third one is the one nobody has a good answer to, ever.",
          C(ANT, "P", "Reversibility raised as a design question",
            "whether the city can switch it off if it turns out to be wrong. "
            "The third one is the one nobody has a good answer to, ever.",
            "Anticipating the need for an exit route is a strong form of "
            "keeping options open against lock-in."),
          C(ANT, "P", "Distributional performance queried before launch",
            "Whether the detection "
            "performance is uniform across body types and mobility aids.",
            "Foresight directed at who would bear the cost of error, not "
            "only at aggregate reliability.")),

        Q("What answer did you get on switching it off?"),

        A("A version of 'why would we'. Which isn't an answer. Once the "
          "signal timing is adaptive, the fixed-time plans that used to run "
          "the junctions get out of date within a year or two — nobody "
          "maintains them any more. So the fallback decays. In two years "
          "turning it off means the traffic gets worse than it was before "
          "you started, and at that point nobody will turn it off. That is "
          "lock-in and it is happening quietly.",
          C(ANT, "P", "Identifies a specific mechanism of lock-in",
            "the fixed-time plans that used to run "
            "the junctions get out of date within a year or two — nobody "
            "maintains them any more. So the fallback decays.",
            "A precise, mechanism-level account of how reversibility is lost "
            "over time — anticipation at its strongest.")),

        Q("Did that get escalated?"),

        A("I wrote it up. It went into the risk register. The risk register "
          "is where things go to be filed. I don't think it reached anyone "
          "who could have changed the design, and I didn't push it beyond "
          "the register, which I'll own.",
          C(RES, "N", "Risk documented into an inert register",
            "It went into the risk register. The risk register "
            "is where things go to be filed.",
            "A well-founded anticipatory finding produces no change in the "
            "project — the failure is in responsiveness, not foresight."),
          C(REF, "P", "Owns his own part in the non-escalation",
            "I didn't push it beyond "
            "the register, which I'll own.",
            "Reflexive attribution of responsibility to himself rather than "
            "only to the system around him.")),

        Q("Was there any external input into these questions?"),

        A("No. It's me and a junior analyst. We don't have an ethics board, "
          "we don't have community input, we have me reading and worrying. "
          "For a system that watches thirty intersections that is a thin "
          "basis and I would say that on the record.",
          C(ENG, "N", "Scrutiny rests on one internal function",
            "We don't have an ethics board, "
            "we don't have community input, we have me reading and worrying.",
            "No external or public input into the assessment of a system with "
            "city-wide reach.")),
      ],
      "The strongest anticipation in the industry group, and the clearest "
      "illustration that anticipation without responsiveness changes nothing. "
      "The respondent identifies a concrete lock-in mechanism — decay of the "
      "fixed-time fallback plans — and files it in a risk register that he "
      "himself describes as inert. He is unusually reflexive about both the "
      "limits of compliance-as-ethics and his own failure to escalate.")

    # =================================================================
    # P05 — 號誌製造商 資深工程師
    # 樣態：預期弱（信任既有規範）、回應性中等、參與極弱
    # =================================================================
    R("P05", "Senior engineer, traffic signal manufacturer",
      dict(institution_type="industry", role_level="rnd_staff",
           sector="manufacturing", experience="over_20y"),
      [
        Q("You've been in signals a long time. How is this project different?"),

        A("Twenty-six years. The difference is that the box used to do what "
          "the timing plan said, and now the box decides. That sounds "
          "dramatic but operationally it's a big change, because when "
          "somebody complains about a junction I used to be able to open the "
          "plan and show them the numbers. Now the answer is 'the model "
          "decided', and I can't show anybody anything.",
          C(REF, "P", "Names the loss of explainability as a real change",
            "when "
            "somebody complains about a junction I used to be able to open the "
            "plan and show them the numbers. Now the answer is 'the model "
            "decided', and I can't show anybody anything.",
            "Critical reflection on how the shift to adaptive control removes "
            "the accountability mechanism the respondent used to rely on.")),

        Q("Does that worry you?"),

        A("It bothers me more than it worries me, if that distinction makes "
          "sense. The standards are good. Signal engineering has a hundred "
          "years of standards behind it and they were written in blood, most "
          "of them. If we build to standard the safety case is sound. I don't "
          "lie awake about it.",
          C(ANT, "N", "Existing standards treated as sufficient foresight",
            "The standards are good. Signal engineering has a hundred "
            "years of standards behind it and they were written in blood, most "
            "of them. If we build to standard the safety case is sound.",
            "Reliance on established standards displaces forward-looking "
            "assessment of what is novel about the adaptive system.")),

        Q("Do the standards cover adaptive control?"),

        A("Partly. They cover the physical layer, the fail-safe behaviour, "
          "conflict monitoring — all of that still applies and it's what "
          "keeps people alive. What they don't cover is how the model should "
          "trade off a bus against six pedestrians. There's no standard for "
          "that. We just — implemented something. The weights came from a "
          "workshop. Four of us in a room.",
          C(ANT, "N", "Value trade-offs settled informally",
            "What they don't cover is how the model should "
            "trade off a bus against six pedestrians. There's no standard for "
            "that. We just — implemented something. The weights came from a "
            "workshop. Four of us in a room.",
            "A consequential distributive decision is made without any "
            "structured consideration of alternatives or affected interests."),
          C(ENG, "N", "Distributive weighting decided by four engineers",
            "The weights came from a "
            "workshop. Four of us in a room.",
            "Those who bear the consequences of the trade-off have no part in "
            "setting it.")),

        Q("Has anything been changed since go-live?"),

        A("The pedestrian minimum, yes. It came up that the crossing at "
          "Alder and Third was clearing people too tight when the adaptive "
          "logic was pushing throughput. We raised the floor at that junction "
          "and then at four others with similar geometry. It wasn't a "
          "regulation issue, we just set the floor higher than the regulation "
          "requires.",
          C(RES, "P", "Pedestrian minimum raised above regulatory floor",
            "We raised the floor at that junction "
            "and then at four others with similar geometry.",
            "Concrete change made on the basis of observed effect, going "
            "beyond the minimum the regulation would have permitted.")),

        Q("Who noticed it was too tight?"),

        A("One of our own technicians, on site for something else. Not a "
          "complaint, not the monitoring dashboard. A man standing at a "
          "junction with a stopwatch because something looked wrong to him. "
          "I don't have a system that replaces that and it bothers me.",
          C(REF, "P", "Recognises reliance on informal noticing",
            "A man standing at a "
            "junction with a stopwatch because something looked wrong to him. "
            "I don't have a system that replaces that and it bothers me.",
            "Reflexive awareness that the project's detection of its own "
            "problems is unsystematic and depends on individual judgement.")),
      ],
      "An experienced engineer whose foresight rests on the sufficiency of "
      "established standards, while acknowledging that the standards are "
      "silent on precisely the novel question — how the model weighs "
      "competing road users. That weighting was settled by four engineers in "
      "a workshop. Responsiveness is real: a pedestrian clearance problem was "
      "found and fixed above the regulatory minimum, but it was found by "
      "chance.")

    # =================================================================
    # P06 — 財團法人／聯盟 業務發展主管（產業界）
    # 樣態：全面偏負向，把負責任創新視為行銷語彙
    # =================================================================
    R("P06", "Business development lead, consortium partner",
      dict(institution_type="industry", role_level="senior_management",
           sector="ict_ai", experience="11_20y"),
      [
        Q("The bid documents mention responsible innovation. How did that "
          "shape the work?"),

        A("I'll be straight with you because I don't think there's much point "
          "otherwise. That language is in the bid because the evaluation "
          "matrix had a section for it worth eight percent. We wrote what "
          "scored well. I'm not saying nobody believes it, I'm saying the "
          "reason it's in the document is the eight percent.",
          C(REF, "N", "Framework language adopted for scoring",
            "That language is in the bid because the evaluation "
            "matrix had a section for it worth eight percent. We wrote what "
            "scored well.",
            "The vocabulary of responsible innovation is treated as a "
            "procurement instrument. Coded negative for reflexivity, though "
            "the candour itself is a reflexive act — a genuinely arguable "
            "case for the review interface.")),

        Q("Was there anything behind the language?"),

        A("There was a stakeholder engagement plan. It was two pages. It "
          "committed us to a launch event and a feedback email address. Both "
          "happened. The email address got nine messages in eighteen months, "
          "seven of them about a pothole.",
          C(ENG, "N", "Engagement commitment met at minimum viable level",
            "It "
            "committed us to a launch event and a feedback email address. Both "
            "happened. The email address got nine messages in eighteen months",
            "Formal commitments are discharged in a form that predictably "
            "produces almost no input.")),

        Q("Did anyone review whether the plan was working?"),

        A("No. There was no review point in the contract. Contracts have "
          "review points for things somebody intends to check.",
          C(RES, "N", "No mechanism to detect or correct failure",
            "There was no review point in the contract. Contracts have "
            "review points for things somebody intends to check.",
            "Absence of any feedback loop by which the engagement commitment "
            "could be found wanting and adjusted.")),

        Q("Do you think the project should have been done differently?"),

        A("Differently, probably. Would a different consortium have done it "
          "better? I doubt it. Everybody bidding on municipal AI work is "
          "structured the same way, with the same incentives, answering the "
          "same matrix. If you want a different outcome you have to change "
          "the matrix, not lecture the bidders.",
          C(REF, "P", "Locates the problem in procurement incentives",
            "If you want a different outcome you have to change "
            "the matrix, not lecture the bidders.",
            "A structural diagnosis rather than an individual one. Coded "
            "positive: it examines the conditions producing the behaviour, "
            "even though it also deflects personal responsibility.")),

        Q("What would a better matrix ask for?"),

        A("Evidence, not intentions. Don't ask me what my engagement plan is, "
          "ask me for the minutes of the last three times a plan like this "
          "changed a design decision. I couldn't produce them. Neither could "
          "my competitors. That would be a real filter.",
          C(ANT, "P", "Proposes a verifiable procurement test",
            "Don't ask me what my engagement plan is, "
            "ask me for the minutes of the last three times a plan like this "
            "changed a design decision.",
            "Forward-looking proposal aimed at changing the conditions of "
            "future projects rather than the present one."),
          C(ENG, "N", "Admits no plan has ever changed a decision",
            "I couldn't produce them. Neither could "
            "my competitors.",
            "Direct admission that engagement has never influenced design "
            "across the sector as the respondent knows it.")),
      ],
      "The most openly instrumental account in the corpus: responsible "
      "innovation language entered the bid because it carried eight percent "
      "of the evaluation score. Engagement commitments were met at the "
      "minimum that could be called met, with no review point to notice they "
      "were not working. The respondent's candour produces a structural "
      "diagnosis — change the procurement matrix, not the bidders — and a "
      "concrete, testable proposal for doing so.")
