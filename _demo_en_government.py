"""
_demo_en_government.py — 合成示範逐字稿：政府部門受訪者 6 位
=====================================================================
虛構資料。見 demo_transcripts_en.py 的完整聲明。

這一組刻意做成混合分布（約五五開，略偏 N），且回應性維度的密度最高——
公部門受訪者最常談的就是「收到反映之後做了什麼／沒做什麼」。
分布是**設計出來的**，不得據此推論任何真實公部門的行為。

刻意保留的爭議點：資源限制造成的不作為，究竟該編為「回應性 N」
（沒有回應）還是不編碼（能力問題而非意願問題）？這一組裡有數段
正是為此而寫，讓信度檢定有真實的分歧來源。
"""


def build(R, Q, A, C, ANT, REF, ENG, RES):

    # =================================================================
    # G01 — 交通局科長
    # 樣態：反思性強、回應性有正有負、參與受資源限制
    # =================================================================
    R("G01", "Section chief, city transport department",
      dict(institution_type="government", role_level="middle_management",
           sector="ict_ai", experience="11_20y"),
      [
        Q("Where did the pressure to do this project come from?"),

        A("Congestion numbers and a manifesto commitment, in that order of "
          "how it's talked about and the reverse order of how it actually "
          "worked. The commitment came first. Then we went looking for the "
          "intervention that fitted it. I don't think that's unusual and I "
          "don't think it's illegitimate — that's what elections are for — "
          "but it does mean the question 'is this the right thing to do' was "
          "settled before my department was involved.",
          C(REF, "P", "Names the real sequence behind the stated rationale",
            "The commitment came first. Then we went looking for the "
            "intervention that fitted it.",
            "Candid examination of how the problem definition was arrived at, "
            "against the official account."),
          C(ANT, "N", "Option appraisal foreclosed by prior commitment",
            "the question 'is this the right thing to do' was "
            "settled before my department was involved",
            "The space in which alternatives could have been considered was "
            "closed before technical assessment began.")),

        Q("How did you approach consultation?"),

        A("Badly, and I'll explain why rather than defend it. Ideally you run "
          "several sessions for different groups — disability organisations "
          "one evening, ward councillors another, commuters another. Each one "
          "takes about two weeks of preparation. We ran one combined session "
          "because I have four staff and two of them were on the tram "
          "project. It's a resourcing answer, not a values answer, but the "
          "effect on residents is identical either way.",
          C(ENG, "N", "Differentiated consultation collapsed into one session",
            "We ran one combined session "
            "because I have four staff and two of them were on the tram "
            "project.",
            "Engagement reduced to a single generic event, with the "
            "respondent clear that the cause is capacity."),
          C(REF, "P", "Distinguishes the cause from the effect on residents",
            "It's a resourcing answer, not a values answer, but the "
            "effect on residents is identical either way.",
            "Refuses to let the explanation function as an excuse — a "
            "reflexive move about his own account.")),

        Q("What was raised at that session?"),

        A("Crossing times, mostly, and one long argument about cameras that "
          "I handled poorly. Somebody asked whether the footage could be "
          "requested by police and I said I'd check. I did check. The answer "
          "is yes, under a specific statutory route, and I never went back "
          "and told the room. Nobody chased me. That's the bit I'm not "
          "comfortable with — the absence of anyone chasing me is not the "
          "same as it being fine.",
          C(RES, "N", "Undertaking to report back not fulfilled",
            "The answer "
            "is yes, under a specific statutory route, and I never went back "
            "and told the room.",
            "A concrete commitment made in a consultation setting was not "
            "honoured."),
          C(REF, "P", "Refuses the absence of complaint as absolution",
            "the absence of anyone chasing me is not the "
            "same as it being fine",
            "Self-scrutiny that does not depend on external challenge.")),

        Q("Has anything about the system changed since it went live?"),

        A("Yes, three things. The pedestrian minimum went up at five "
          "junctions. We added an audible confirmation at two crossings after "
          "the sight-loss charity asked for it — that one took eleven months "
          "and it should have taken three. And we publish a monthly summary "
          "now, which nobody reads, but it exists and when a councillor asks "
          "a question I can point at it.",
          C(RES, "P", "Concrete changes made in response to external requests",
            "The pedestrian minimum went up at five "
            "junctions. We added an audible confirmation at two crossings after "
            "the sight-loss charity asked for it",
            "Documented adaptation traceable to specific external input."),
          C(RES, "N", "Adaptation delayed far beyond what was necessary",
            "that one took eleven months "
            "and it should have taken three",
            "The respondent's own judgement that the response, while real, "
            "was too slow to count as adequate.")),

        Q("What made the eleven months?"),

        A("Two of it was us not knowing who owned the decision. Three was "
          "the vendor's change-control process. The rest was that it needed a "
          "small budget line and small budget lines are harder than large "
          "ones because nobody has a process for them. I've since written a "
          "standing note about who owns crossing-parameter changes, which "
          "removes the first two months next time.",
          C(RES, "P", "Structural fix applied to the delay itself",
            "I've since written a "
            "standing note about who owns crossing-parameter changes, which "
            "removes the first two months next time.",
            "Learning converted into a procedural change rather than remaining "
            "an individual insight.")),

        Q("What do you wish you had done at the start?"),

        A("Written down who has to be told what, and by when, before anything "
          "was switched on. Everything that went wrong here went wrong in the "
          "gaps between organisations, and none of those gaps were technical.",
          C(ANT, "P", "Identifies inter-organisational gaps as the failure locus",
            "Everything that went wrong here went wrong in the "
            "gaps between organisations, and none of those gaps were technical.",
            "Forward-looking diagnosis directed at the coordination design "
            "rather than the technology.")),
      ],
      "A candid departmental account. Consultation was collapsed into a "
      "single session for capacity reasons, which the respondent explains "
      "without allowing the explanation to function as a defence. He reports "
      "a specific broken undertaking — checking whether police could request "
      "footage, and never returning to the room with the answer — and refuses "
      "to treat the absence of complaint as absolution. Three real changes "
      "followed go-live, one of them eleven months late, and he has since "
      "written a standing note that removes two of those months next time."),

    # =================================================================
    # G02 — 都市資訊長
    # 樣態：預期中、參與弱、回應性弱、反思性弱（防禦性）
    # =================================================================
    R("G02", "Chief information officer, city council",
      dict(institution_type="government", role_level="senior_management",
           sector="ict_ai", experience="over_20y"),
      [
        Q("How does a system like this get governed once it's running?"),

        A("Through the standard route. It's on the corporate risk register, "
          "it has a senior responsible owner, it reports into the digital "
          "board quarterly. That's the same governance any major system gets "
          "and I'd resist the idea that it needs something special. Once you "
          "start creating bespoke oversight for anything with a model in it, "
          "you end up with forty committees and no capacity.",
          C(ANT, "N", "Novel risks assimilated to standard IT governance",
            "That's the same governance any major system gets "
            "and I'd resist the idea that it needs something special.",
            "Governance is set by analogy to prior systems, without "
            "assessment of what is different about an adaptive model acting "
            "on the street.")),

        Q("Does the digital board have the expertise to interrogate a model?"),

        A("It has me. And a non-executive with a technology background. Is "
          "that enough to interrogate a detection model in detail? No, "
          "probably not. What we do instead is rely on the vendor's assurance "
          "documentation and on the acceptance testing.",
          C(REF, "P", "Concedes the oversight body cannot interrogate the model",
            "Is "
            "that enough to interrogate a detection model in detail? No, "
            "probably not.",
            "Honest assessment of a capability gap in the respondent's own "
            "governance arrangement."),
          C(RES, "N", "Reliance on vendor self-assurance",
            "What we do instead is rely on the vendor's assurance "
            "documentation and on the acceptance testing.",
            "The mechanism for detecting problems is supplied by the party "
            "whose product would be found wanting.")),

        Q("Has the public asked for information about the system?"),

        A("We've had — I want to say six or seven freedom of information "
          "requests. Most were about camera locations and we answered those. "
          "Two asked for the algorithm and we refused those on commercial "
          "confidentiality grounds, which is the vendor's position and "
          "legally sound.",
          C(ENG, "N", "Algorithmic detail withheld as commercial confidence",
            "Two asked for the algorithm and we refused those on commercial "
            "confidentiality grounds",
            "The information needed for public scrutiny is contractually "
            "unavailable, foreclosing informed engagement.")),

        Q("Did the council consider negotiating that at procurement?"),

        A("I don't believe transparency terms were in the specification. "
          "That's a fair criticism and I'd expect it to be in the next one. "
          "The honest position is that in 2022 we weren't thinking about it, "
          "and by the time you're arguing about disclosure you've already "
          "signed.",
          C(ANT, "N", "Transparency terms not anticipated at procurement",
            "in 2022 we weren't thinking about it, "
            "and by the time you're arguing about disclosure you've already "
            "signed",
            "A foreseeable governance requirement was not built in at the "
            "only point where it was available."),
          C(REF, "P", "Accepts the criticism as fair",
            "That's a fair criticism and I'd expect it to be in the next one.",
            "Acknowledgement without deflection, though it produces a "
            "commitment about future contracts rather than this one.")),

        Q("Is there a route for a resident to challenge how a junction "
          "behaves?"),

        A("There's the general complaints process. It routes to transport, "
          "not to us. Whether transport can then change a parameter depends "
          "on the change-control terms, which — I'd have to look. I don't "
          "know the answer to that off the top of my head, which I appreciate "
          "is not a great answer.",
          C(RES, "N", "No identified route from complaint to parameter change",
            "Whether transport can then change a parameter depends "
            "on the change-control terms, which — I'd have to look.",
            "The senior officer responsible cannot describe the path by which "
            "a resident's complaint could alter system behaviour.")),
      ],
      "A governance account organised around treating the system as ordinary "
      "corporate IT. The respondent concedes that neither he nor the digital "
      "board can interrogate a detection model, and that assurance therefore "
      "rests on documentation supplied by the vendor. Algorithmic detail is "
      "withheld from freedom-of-information requests on commercial grounds — "
      "transparency terms were not in the specification, which he accepts as "
      "fair criticism. He cannot describe how a resident complaint could "
      "reach a system parameter."),

    # =================================================================
    # G03 — 市議員
    # 樣態：參與強（選區）、回應性中、預期弱、反思性中
    # =================================================================
    R("G03", "Ward councillor, city council",
      dict(institution_type="government", role_level="policy_maker",
           sector="other", experience="6_10y"),
      [
        Q("How does this reach you as a councillor?"),

        A("Through my surgery, every other Saturday, three hours, anybody can "
          "come. In the first year after switch-on I'd say a dozen people "
          "raised the junctions. Not organised, not a campaign — individual "
          "people describing something specific about a crossing they use. "
          "That's the most reliable data I get about anything and it doesn't "
          "appear in any report.",
          C(ENG, "P", "Open surgery as a standing channel for residents",
            "Through my surgery, every other Saturday, three hours, anybody can "
            "come.",
            "A low-barrier, sustained route by which affected residents reach "
            "a decision-maker."),
          C(ANT, "N", "Most reliable signal absent from formal reporting",
            "That's the most reliable data I get about anything and it doesn't "
            "appear in any report.",
            "The project's monitoring design does not capture the information "
            "the respondent considers most trustworthy.")),

        Q("What did people describe?"),

        A("Two themes. One was crossing time, particularly for older "
          "residents on the Alder Street junction. The other, which I didn't "
          "expect, was uncertainty — people saying they didn't know if it had "
          "seen them, so they'd press the button again, or step forward to be "
          "noticed, which is exactly what you don't want people doing.",
          C(ANT, "N", "Safety-relevant behaviour change not foreseen",
            "so they'd press the button again, or step forward to be "
            "noticed, which is exactly what you don't want people doing",
            "An adaptive behaviour with direct safety implications that no "
            "part of the assessment anticipated.")),

        Q("What did you do with it?"),

        A("Raised it in committee twice. The first time I got a written "
          "answer about detection accuracy, which wasn't the question I'd "
          "asked. The second time I asked for the raw logs and that's what "
          "eventually got the university their data. So it moved, but it "
          "moved because I had a committee to stand up in. A resident with "
          "the same observation has nowhere to go.",
          C(RES, "P", "Escalation produced access to evidence",
            "The second time I asked for the raw logs and that's what "
            "eventually got the university their data.",
            "Persistence through a formal channel produced a concrete "
            "outcome."),
          C(ENG, "N", "The same route is unavailable to residents",
            "it moved because I had a committee to stand up in. A resident with "
            "the same observation has nowhere to go",
            "The effective channel depends on institutional position rather "
            "than on the merit of the observation.")),

        Q("Do you feel you understand the system well enough to scrutinise it?"),

        A("No. I'm a councillor, I do this alongside a job. I get a "
          "hundred-page pack the Friday before a Tuesday committee. I've read "
          "enough to ask about crossing times because a constituent taught me "
          "what to ask. I could not tell you how the model weighs a bus "
          "against a pedestrian and I've never been offered a briefing that "
          "would tell me.",
          C(REF, "P", "Names his own scrutiny capacity honestly",
            "I could not tell you how the model weighs a bus "
            "against a pedestrian and I've never been offered a briefing that "
            "would tell me.",
            "Explicit assessment of the limits of the respondent's own "
            "oversight role."),
          C(ENG, "N", "No briefing provided to elected scrutineers",
            "I've never been offered a briefing that "
            "would tell me",
            "Those formally charged with scrutiny are not equipped to "
            "perform it.")),

        Q("What would help?"),

        A("Somebody independent who answers to the committee rather than to "
          "the department, with enough hours to actually read things. Every "
          "authority has internal audit for money. There's no equivalent for "
          "this, and this is now making decisions about people all day.",
          C(ANT, "P", "Proposes an audit function for algorithmic systems",
            "Every "
            "authority has internal audit for money. There's no equivalent for "
            "this, and this is now making decisions about people all day.",
            "Institutional proposal aimed at building standing scrutiny "
            "capacity for future systems.")),
      ],
      "The elected scrutineer's view. His fortnightly surgery is the most "
      "reliable signal he receives and appears in no report; through it he "
      "learned of pedestrians stepping forward to be noticed, a safety-"
      "relevant behaviour nobody anticipated. His escalation eventually "
      "produced the raw logs the university needed, which he is quick to "
      "point out worked only because he had a committee to stand up in. He is "
      "candid that he cannot say how the model weighs a bus against a "
      "pedestrian and has never been offered a briefing that would tell him."),

    # =================================================================
    # G04 — 中央部會政策分析師
    # 樣態：預期強（政策層次）、參與弱、回應性弱
    # =================================================================
    R("G04", "Policy analyst, national transport ministry",
      dict(institution_type="government", role_level="policy_maker",
           sector="ict_ai", experience="6_10y"),
      [
        Q("How does central government see deployments like Port Calder's?"),

        A("As a pilot we can learn from, officially. In practice as a thing "
          "that happened which we now have to write guidance about "
          "retrospectively. Eleven authorities did something in this space "
          "before there was any national position, and the guidance we're now "
          "drafting has to be compatible with all eleven, which means it will "
          "be weak.",
          C(ANT, "N", "National position arrived after the deployments",
            "Eleven authorities did something in this space "
            "before there was any national position, and the guidance we're now "
            "drafting has to be compatible with all eleven, which means it will "
            "be weak.",
            "Foresight failure at the system level: the window for shaping "
            "practice closed before the guidance existed.")),

        Q("Could the ministry have moved earlier?"),

        A("Yes. There was a submission in 2021 recommending exactly that and "
          "it wasn't prioritised. I've read it. It's a good submission. The "
          "reason it wasn't prioritised is that nothing had gone wrong yet, "
          "and our attention is allocated by what has gone wrong. That's the "
          "honest mechanism and it's not specific to this file.",
          C(REF, "P", "Names the attention mechanism candidly",
            "The "
            "reason it wasn't prioritised is that nothing had gone wrong yet, "
            "and our attention is allocated by what has gone wrong.",
            "Critical examination of how the respondent's own institution "
            "allocates capacity, generalised beyond the immediate case."),
          C(RES, "N", "Institution only responds after harm",
            "our attention is allocated by what has gone wrong",
            "Adaptation is structurally reactive; there is no trigger short "
            "of failure.")),

        Q("What's going into the guidance?"),

        A("A requirement to publish what the system optimises. A requirement "
          "for a documented fallback that is tested annually, because "
          "everyone has a fallback on paper and nobody tests it. And a "
          "requirement to report performance disaggregated by pedestrian "
          "type, which is the one that will get pushed back on hardest "
          "because it's the one that would show something.",
          C(ANT, "P", "Annual testing of the fallback required",
            "A requirement "
            "for a documented fallback that is tested annually, because "
            "everyone has a fallback on paper and nobody tests it.",
            "Targets the specific mechanism by which reversibility is quietly "
            "lost."),
          C(ANT, "P", "Disaggregated performance reporting required",
            "a requirement to report performance disaggregated by pedestrian "
            "type",
            "Anticipates that aggregate reporting will continue to conceal "
            "distributional harm unless the requirement is explicit.")),

        Q("Will it have teeth?"),

        A("It's guidance. Authorities must have regard to it. In practice "
          "that means the ones already doing it will cite it and the ones who "
          "aren't will note that they've had regard to it and carry on. "
          "Making it statutory requires primary legislation and there is no "
          "legislative slot.",
          C(RES, "N", "Instrument chosen cannot compel adaptation",
            "the ones already doing it will cite it and the ones who "
            "aren't will note that they've had regard to it and carry on",
            "The respondent's own assessment that the policy instrument will "
            "not produce change where change is needed.")),

        Q("Was anyone outside government involved in drafting?"),

        A("A working group — five authorities, three vendors, two academics. "
          "No disability organisations, no residents. I raised it. I was told "
          "the timeline didn't allow for a public consultation, which is "
          "true, and also we set the timeline.",
          C(ENG, "N", "Affected groups absent from the drafting group",
            "No disability organisations, no residents.",
            "The population most affected by the guidance has no part in "
            "writing it."),
          C(REF, "P", "Points out the timeline was self-imposed",
            "I was told "
            "the timeline didn't allow for a public consultation, which is "
            "true, and also we set the timeline.",
            "Refuses a constraint framing where the constraint was chosen by "
            "the institution invoking it.")),
      ],
      "The national view, and the clearest case in the corpus of anticipation "
      "failing at system level: eleven authorities acted before any national "
      "position existed, so the guidance now being drafted must be compatible "
      "with all of them and will be weak. A 2021 submission recommending "
      "earlier action was not prioritised because nothing had gone wrong yet "
      "— a mechanism the respondent names without defending. The guidance "
      "targets the right things, including annual fallback testing, but he "
      "expects it to change nothing where it matters, and the drafting group "
      "contains no disability organisations or residents."),

    # =================================================================
    # G05 — 市府採購主管
    # 樣態：全面偏負向但坦率；對制度限制診斷精確
    # =================================================================
    R("G05", "Procurement manager, city council",
      dict(institution_type="government", role_level="middle_management",
           sector="other", experience="over_20y"),
      [
        Q("Walk me through how this was bought."),

        A("Open tender, three bidders, evaluated on price at sixty percent "
          "and quality at forty. Within the quality forty there was a "
          "sustainability and social value section worth eight, and inside "
          "that there was a subsection about stakeholder engagement worth "
          "about two and a half percent overall. That two and a half percent "
          "is the entire weight the process placed on whether anyone would be "
          "consulted.",
          C(ENG, "N", "Engagement carried 2.5% of the evaluation weight",
            "That two and a half percent "
            "is the entire weight the process placed on whether anyone would be "
            "consulted.",
            "The procurement design made engagement quality nearly irrelevant "
            "to who won.")),

        Q("Could it have been weighted differently?"),

        A("Yes, and I'd have supported it. The obstacle is that everything in "
          "the quality score has to be assessable in a way that survives a "
          "challenge. Price is easy to defend. 'This bidder's engagement plan "
          "is better' is exactly the kind of judgement a losing bidder takes "
          "to review, and a review costs us more than the contract's margin. "
          "So we weight what we can defend, not what matters most.",
          C(REF, "P", "Names the defensibility bias precisely",
            "So we weight what we can defend, not what matters most.",
            "A sharp structural diagnosis of why procurement systematically "
            "underweights qualitative commitments."),
          C(ANT, "N", "Evaluation design cannot register future practice",
            "'This bidder's engagement plan "
            "is better' is exactly the kind of judgement a losing bidder takes "
            "to review",
            "The process is unable to assess the thing that would determine "
            "how the system is developed.")),

        Q("Is there any mechanism to check what was promised was delivered?"),

        A("Contract management, in theory. In practice the contract manager "
          "checks the deliverables schedule, and the engagement plan wasn't "
          "in the deliverables schedule, it was in the quality submission. "
          "Those are different documents and only one of them is monitored. "
          "That's a real gap and it exists on most of our contracts, not just "
          "this one.",
          C(RES, "N", "Promised engagement never entered the monitored schedule",
            "the engagement plan wasn't "
            "in the deliverables schedule, it was in the quality submission. "
            "Those are different documents and only one of them is monitored.",
            "A specific, generalisable mechanism by which commitments made to "
            "win work are never checked.")),

        Q("Has anything changed as a result of this project?"),

        A("One thing. We now copy the top-scoring quality commitments into "
          "the deliverables schedule as contract terms. It was a two-line "
          "change to a template. I've been trying to get it done for six "
          "years and this project is what finally carried it, because a "
          "councillor asked about it in public.",
          C(RES, "P", "Template change closes the monitoring gap",
            "We now copy the top-scoring quality commitments into "
            "the deliverables schedule as contract terms.",
            "A concrete, durable procedural change that makes future "
            "commitments enforceable."),
          C(REF, "P", "Notes what actually caused the change",
            "I've been trying to get it done for six "
            "years and this project is what finally carried it, because a "
            "councillor asked about it in public.",
            "Reflexive attention to the real mechanism of institutional "
            "change, as distinct from the merits of the proposal.")),

        Q("Would you buy this system the same way again?"),

        A("With the template change, yes. Without it, I'd have said the "
          "process was fine and I'd have been wrong, which is worth noting — "
          "for six years I'd have told you our process was fine.",
          C(REF, "P", "Recognises he would have defended the flawed process",
            "for six years I'd have told you our process was fine",
            "Examination of how confident and wrong the respondent had "
            "previously been about his own domain.")),
      ],
      "The procurement view, and the most precise structural diagnosis in the "
      "corpus. Stakeholder engagement carried two and a half percent of the "
      "evaluation weight, and the engagement plan sat in the quality "
      "submission rather than the monitored deliverables schedule — so it was "
      "never checked. The respondent explains why: the process weights what "
      "can be defended against a losing bidder's challenge, not what matters "
      "most. A two-line template change now copies quality commitments into "
      "the contract; he had been trying to make it for six years."),

    # =================================================================
    # G06 — 資料保護官
    # 樣態：預期中、參與弱、反思性中、回應性負向
    # =================================================================
    R("G06", "Data protection officer, city council",
      dict(institution_type="government", role_level="middle_management",
           sector="other", experience="11_20y"),
      [
        Q("Was a data protection impact assessment done?"),

        A("Yes, and it's a decent one, I'll defend it. It covers lawful "
          "basis, retention, access, the security arrangement, the "
          "processor terms. Where I'd now say it's thin is that it assesses "
          "the system as a camera system. It doesn't really assess it as a "
          "system that makes decisions about people in real time, because in "
          "2022 the template I had didn't have a section for that.",
          C(REF, "P", "Identifies the framing limit of his own assessment",
            "it assesses "
            "the system as a camera system. It doesn't really assess it as a "
            "system that makes decisions about people in real time",
            "Critical scrutiny of the categories the respondent's own "
            "instrument imposed on the object.")),

        Q("Has the assessment been revisited?"),

        A("No. It's a live document in the sense that the policy says it's a "
          "live document. Nobody has opened it since sign-off. There's no "
          "trigger — no review date, no event that causes someone to look at "
          "it again. I could set one. I haven't.",
          C(RES, "N", "No trigger causes the assessment to be revisited",
            "There's no "
            "trigger — no review date, no event that causes someone to look at "
            "it again. I could set one. I haven't.",
            "The absence of a review mechanism is stated plainly, including "
            "the respondent's own inaction.")),

        Q("How is retention handled in practice?"),

        A("Seventy-two hours for the raw video, indefinite for the derived "
          "counts. The derived counts are the interesting part and nobody "
          "asks about them because they're described as anonymous. They are "
          "anonymous. They are also a complete record of how many people "
          "crossed which junction at what time for two years, and I'm not "
          "sure 'anonymous' is doing the work people think it's doing there.",
          C(ANT, "P", "Questions whether anonymity covers the derived data",
            "They are also a complete record of how many people "
            "crossed which junction at what time for two years, and I'm not "
            "sure 'anonymous' is doing the work people think it's doing there.",
            "Anticipates a risk that the current framing renders invisible.")),

        Q("Have you raised that?"),

        A("In a footnote. I know how that sounds after what I just said "
          "about the risk register. I think the honest position is that I "
          "raise things in the strongest form I think will still get read, "
          "and I'm probably calibrating that too cautiously.",
          C(RES, "N", "Concern raised in a form unlikely to prompt action",
            "In a footnote.",
            "The respondent's own foresight is expressed in a channel he "
            "expects to be ineffective."),
          C(REF, "P", "Examines his own calibration of what to raise",
            "I raise things in the strongest form I think will still get read, "
            "and I'm probably calibrating that too cautiously",
            "Reflexive scrutiny of the respondent's own strategic self-"
            "censorship.")),

        Q("Do residents have a route to see what data concerns them?"),

        A("Subject access, in principle. In practice, to make a subject "
          "access request about camera footage you need to tell us "
          "approximately when and where you were, and most people can't, and "
          "the footage is gone in seventy-two hours anyway. So the right "
          "exists and is close to unexercisable. I've had two requests in two "
          "years and I couldn't fulfil either.",
          C(ENG, "N", "Access right exists but is practically unexercisable",
            "the right "
            "exists and is close to unexercisable. I've had two requests in two "
            "years and I couldn't fulfil either",
            "The formal route for individuals to obtain information about "
            "themselves cannot in practice be used.")),
      ],
      "A data protection officer who defends his impact assessment while "
      "naming its framing limit: it assesses a camera system, not a system "
      "making real-time decisions about people, because the 2022 template had "
      "no section for that. The assessment has not been reopened since "
      "sign-off and no trigger exists that would cause it to be — he notes he "
      "could set one and has not. His sharpest observation concerns the "
      "derived counts, indefinitely retained and described as anonymous, "
      "which he raised in a footnote.")
