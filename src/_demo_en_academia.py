"""
_demo_en_academia.py — 合成示範逐字稿：學術界受訪者 6 位
=====================================================================
虛構資料。見 demo_transcripts_en.py 的完整聲明。

這一組刻意偏正向（約六成五 P），且反思性維度的密度明顯高於其他組。
分布是**設計出來的**，用來讓交叉表與對數勝算比的特徵詞誘導有訊號可抓；
不得據此推論任何真實學術社群的行為。

刻意保留的爭議點：學者談的多半是「應該怎麼做」而非「做了什麼」。
若編碼者採嚴格標準（只有實際發生的實踐才算），有數段會從 P 變成 N。
這正是「編碼複核」頁籤與信度檢定該有的爭議對象。
"""


def build(R, Q, A, C, ANT, REF, ENG, RES):

    # =================================================================
    # A01 — 交通工程教授
    # 樣態：預期強、反思性強、對參與有具體實踐
    # =================================================================
    R("A01", "Professor of transport engineering",
      dict(institution_type="academia", role_level="researcher",
           sector="ict_ai", experience="over_20y"),
      [
        Q("You advised the city early on. What did you push for?"),

        A("Two things, and I got one of them. The one I got was a baseline "
          "measurement period — six months of data before anything was "
          "switched on, at all thirty junctions and at twelve control "
          "junctions elsewhere in the city. Without that you can never say "
          "what the system did, only what happened afterwards. Cities almost "
          "never do this because it delays the ribbon-cutting by six months, "
          "and I was quite obnoxious about it.",
          C(ANT, "P", "Baseline and control junctions secured before rollout",
            "The one I got was a baseline "
            "measurement period — six months of data before anything was "
            "switched on, at all thirty junctions and at twelve control "
            "junctions elsewhere in the city.",
            "Foresight expressed as a concrete design decision that preserves "
            "the ability to evaluate the intervention later.")),

        Q("And the one you didn't get?"),

        A("A pre-registered evaluation protocol. I wanted us to write down, "
          "before switch-on, what would count as the system working and what "
          "would count as it failing. Including the failure conditions. That "
          "was seen as — I think the word used was 'unhelpful framing'. So "
          "now the evaluation criteria are whatever the annual report says "
          "they are, which means the system has never failed and never will.",
          C(ANT, "P", "Pre-registration of success and failure criteria",
            "I wanted us to write down, "
            "before switch-on, what would count as the system working and what "
            "would count as it failing. Including the failure conditions.",
            "An anticipatory mechanism aimed at preventing retrospective "
            "redefinition of success."),
          C(RES, "N", "Absence of criteria makes failure undetectable",
            "the evaluation criteria are whatever the annual report says "
            "they are, which means the system has never failed and never will",
            "Without pre-set criteria there is no state of the world that "
            "would trigger adaptation — a structural failure of "
            "responsiveness.")),

        Q("How do you assess your own role in this? You're an adviser but "
          "also, in a sense, part of the project."),

        A("Uncomfortably. I'm in the acknowledgements of the annual report, "
          "which means my name lends the thing credibility whether or not I "
          "agree with what it says. I raised that. I was told I could ask to "
          "be removed. But if I take my name off I lose the meetings, and if "
          "I lose the meetings I can't argue for the baseline next time. So I "
          "stayed, and I'm aware that's a rationalisation as well as a "
          "reason.",
          C(REF, "P", "Examines own complicity in lending credibility",
            "my name lends the thing credibility whether or not I "
            "agree with what it says",
            "Direct scrutiny of the respondent's own position in the "
            "arrangement rather than of the project alone."),
          C(REF, "P", "Recognises the rationalisation as a rationalisation",
            "I'm aware that's a rationalisation as well as a "
            "reason",
            "Second-order reflexivity: examining the reasoning used to "
            "justify staying, not just the decision.")),

        Q("Did you involve residents in your own evaluation work?"),

        A("We ran walking interviews. Fourteen people, each walked a route "
          "they normally walk, with a researcher, talking about the "
          "junctions as they crossed them. It's slow and it costs almost "
          "nothing and it surfaced things no dashboard would. Two people "
          "described waiting at a junction and not knowing whether the system "
          "had seen them. That's not a detection failure, the detection was "
          "fine — it's a legibility failure, and it wasn't in anybody's "
          "requirements.",
          C(ENG, "P", "Walking interviews as a method of surfacing experience",
            "We ran walking interviews. Fourteen people, each walked a route "
            "they normally walk, with a researcher, talking about the "
            "junctions as they crossed them.",
            "Substantive engagement that generates knowledge the project "
            "could not otherwise obtain."),
          C(ANT, "P", "Identifies legibility as a distinct failure class",
            "it's a legibility failure, and it wasn't in anybody's "
            "requirements",
            "Names a category of harm that the project's own framing could "
            "not see.")),

        Q("Did that reach the city?"),

        A("It's in a paper. Whether a paper reaches a city is a separate "
          "question and the honest answer is usually no. I sent the "
          "preprint to two people in the transport department. One replied.",
          C(RES, "N", "Findings routed through publication rather than practice",
            "Whether a paper reaches a city is a separate "
            "question and the honest answer is usually no.",
            "Knowledge is produced but not channelled into a form that could "
            "change the system.")),

        Q("What would you tell a city about to do this?"),

        A("Spend the six months. Write down what failure looks like. And "
          "budget for someone whose job is to be wrong about the thing — not "
          "a critic, a person inside the project whose performance review "
          "rewards finding problems. Every project I've seen has ten people "
          "paid to make it work and nobody paid to find out whether it does.",
          C(ANT, "P", "Proposes an institutional role for finding problems",
            "budget for someone whose job is to be wrong about the thing — not "
            "a critic, a person inside the project whose performance review "
            "rewards finding problems",
            "Forward-looking institutional design aimed at building "
            "self-correction into future projects.")),
      ],
      "An adviser who secured a baseline and control-junction measurement "
      "period but lost the argument for pre-registered evaluation criteria, "
      "with the consequence that no observation can now count as failure. "
      "Notably reflexive about his own position: he examines how his name in "
      "the acknowledgements lends credibility, and then examines the "
      "reasoning by which he justified staying. His walking-interview method "
      "surfaced a legibility failure invisible to the project's own metrics, "
      "which reached a journal rather than the transport department."),

    # =================================================================
    # A02 — 科技與社會研究博士後
    # 樣態：反思性與參與極強；對回應性悲觀
    # =================================================================
    R("A02", "Postdoctoral researcher, science and technology studies",
      dict(institution_type="academia", role_level="researcher",
           sector="ict_ai", experience="under_5y"),
      [
        Q("How did you come to study this deployment?"),

        A("I was going to study something else entirely and then I moved to "
          "Port Calder and started noticing that the junction outside my flat "
          "behaved differently on different days. That's an embarrassing "
          "origin story for a research programme but it's the true one. I "
          "should say that up front because where a question comes from "
          "shapes what you look at, and I was already annoyed before I "
          "started.",
          C(REF, "P", "Discloses the standpoint the research began from",
            "where a question comes from "
            "shapes what you look at, and I was already annoyed before I "
            "started",
            "Explicit positioning of the researcher's own situatedness as "
            "something that shapes the inquiry.")),

        Q("What have you found?"),

        A("The thing I keep coming back to is who gets asked to adapt. The "
          "system optimises flow. Flow is measured in vehicles. So when the "
          "model has a choice between holding twelve cars and holding one "
          "person with a walking frame, the arithmetic is not close. Nobody "
          "chose that. It falls out of what got counted.",
          C(REF, "P", "Traces distributive effects to what the metric counts",
            "The "
            "system optimises flow. Flow is measured in vehicles.",
            "Critical examination of how an apparently technical measurement "
            "choice encodes a value judgement."),
          C(ANT, "N", "Distributive consequence unanticipated by the project",
            "Nobody chose that. It falls out of what got counted.",
            "A significant equity effect arises without ever having been "
            "considered, indicating absent foresight in the project design.")),

        Q("Have you worked with residents directly?"),

        A("Yes, that's most of what I do now. We set up a group with a "
          "disability advocacy organisation and a residents' association — "
          "eleven people, meeting monthly, and they set the agenda, not me. "
          "The first three meetings I talked too much and one of them told "
          "me so, which was the most useful supervision I've had.",
          C(ENG, "P", "Sustained group with agenda set by participants",
            "eleven people, meeting monthly, and they set the agenda, not me",
            "Engagement in which participants hold procedural control rather "
            "than being consulted on a researcher's terms."),
          C(REF, "P", "Accepts correction on own conduct within the group",
            "The first three meetings I talked too much and one of them told "
            "me so, which was the most useful supervision I've had.",
            "Reflexivity enacted in practice, with the researcher's own "
            "behaviour treated as available for critique.")),

        Q("Has any of it changed the system?"),

        A("No. And I want to be careful here because there's a genre of "
          "research where the conclusion is 'more participation is needed' "
          "and everyone nods and nothing happens. The group has produced two "
          "documents. Both were received warmly. Neither changed a parameter. "
          "At some point warm reception without change is its own kind of "
          "dismissal and I don't yet know what to do about it.",
          C(RES, "N", "Warm reception substitutes for change",
            "The group has produced two "
            "documents. Both were received warmly. Neither changed a parameter.",
            "Input is accepted at the level of courtesy while the system "
            "remains unaltered."),
          C(REF, "P", "Refuses the reflex conclusion of her own field",
            "there's a genre of "
            "research where the conclusion is 'more participation is needed' "
            "and everyone nods and nothing happens",
            "Critical scrutiny directed at the respondent's own disciplinary "
            "conventions.")),

        Q("Is there anything the city does well here?"),

        A("They answer emails. I'm not being sarcastic — compared with the "
          "vendors, the department is reachable and the people in it are "
          "thoughtful and underfunded. The problem isn't that they don't care. "
          "It's that caring isn't a mechanism. There's no point in the "
          "process where what the group says has to be answered in writing "
          "before something proceeds. Without that, everything depends on "
          "whether the person in post that year happens to be receptive.",
          C(RES, "N", "Responsiveness depends on individuals, not mechanism",
            "There's no point in the "
            "process where what the group says has to be answered in writing "
            "before something proceeds.",
            "Identifies the absence of a procedural trigger as the reason "
            "goodwill does not translate into adaptation."),
          C(ENG, "P", "Credits the department's accessibility",
            "compared with the "
            "vendors, the department is reachable and the people in it are "
            "thoughtful and underfunded",
            "Recognition of genuine openness on the part of one actor, "
            "distinguishing willingness from capacity.")),
      ],
      "The most methodologically reflexive account in the corpus. The "
      "respondent discloses her own standpoint, submits her conduct in a "
      "participant-led group to correction, and refuses her field's reflex "
      "conclusion that more participation is the answer. Her central "
      "analytical claim — that the equity effect follows from measuring flow "
      "in vehicles, and that nobody chose it — is a clear case of a "
      "consequential outcome nobody anticipated. She is pointed about the "
      "limit: warm reception without change is its own kind of dismissal."),

    # =================================================================
    # A03 — 資料科學家（大學研究中心）
    # 樣態：預期強、反思性中等、參與弱、回應性有一個具體實例
    # =================================================================
    R("A03", "Research fellow, urban data science centre",
      dict(institution_type="academia", role_level="rnd_staff",
           sector="ict_ai", experience="6_10y"),
      [
        Q("You audited the system's performance. How did you approach it?"),

        A("I asked for the raw detection logs and I was given aggregates. "
          "That took four months to resolve and it was resolved because a "
          "councillor asked the same question in a committee meeting, not "
          "because I asked. Once I had the logs the audit itself took three "
          "weeks.",
          C(ENG, "N", "Access to evidence required political leverage",
            "That took four months to resolve and it was resolved because a "
            "councillor asked the same question in a committee meeting, not "
            "because I asked.",
            "Independent scrutiny was possible only through an escalation "
            "route unavailable to most parties.")),

        Q("What did the audit show?"),

        A("Two things. The headline accuracy held up, that was fine. But "
          "detection latency was distributed unevenly by time of day in a way "
          "that mapped onto lighting, and the junctions with the worst "
          "lighting are in the two lowest-income wards. So the people most "
          "likely to be waiting longer for a crossing signal are also the "
          "people least likely to own a car. I want to be careful: that's an "
          "association in one city over eleven months, it is not a law of "
          "nature.",
          C(ANT, "P", "Distributional audit across wards",
            "detection latency was distributed unevenly by time of day in a way "
            "that mapped onto lighting, and the junctions with the worst "
            "lighting are in the two lowest-income wards",
            "Systematic examination of how the system's performance is "
            "distributed across a population, not only in aggregate."),
          C(REF, "P", "States the limits of the inference",
            "that's an "
            "association in one city over eleven months, it is not a law of "
            "nature",
            "Careful scrutiny of what the respondent's own evidence can and "
            "cannot support.")),

        Q("What happened when you reported it?"),

        A("Better than I expected, actually. The transport department took it "
          "seriously and it turned into a street-lighting upgrade at nine "
          "junctions. That's a real outcome and I should say so. What it "
          "didn't turn into was any change to the detection model or to how "
          "performance gets reported. So the symptom got fixed in the cheapest "
          "available place.",
          C(RES, "P", "Audit produced a concrete lighting upgrade",
            "The transport department took it "
            "seriously and it turned into a street-lighting upgrade at nine "
            "junctions.",
            "Documented adaptation in response to external evidence."),
          C(RES, "N", "Reporting practice left unchanged",
            "What it "
            "didn't turn into was any change to the detection model or to how "
            "performance gets reported.",
            "The response addresses the instance without altering the "
            "mechanism that allowed the disparity to go unnoticed.")),

        Q("Should performance reporting be different?"),

        A("Yes, and it's not complicated. Report the worst decile, not the "
          "mean. Every dashboard I have ever seen for a public system reports "
          "the mean, and the mean is exactly the statistic that hides the "
          "people you should be worried about. It costs nothing to add a "
          "column.",
          C(ANT, "P", "Proposes a reporting change that surfaces harm",
            "Report the worst decile, not the "
            "mean.",
            "A concrete, low-cost proposal aimed at making future problems "
            "visible before they accumulate.")),

        Q("Were residents involved in the audit at any point?"),

        A("No. It was a data exercise. In hindsight the lighting finding "
          "would have taken about a week instead of three months if I'd asked "
          "twenty people in those wards whether crossing felt different at "
          "night, and I didn't think to.",
          C(ENG, "N", "Audit conducted without contact with affected residents",
            "It was a data exercise.",
            "Independent scrutiny reproduced the project's own exclusion of "
            "the affected population."),
          C(REF, "P", "Recognises the cost of the methodological choice",
            "the lighting finding "
            "would have taken about a week instead of three months if I'd asked "
            "twenty people in those wards",
            "Reflexive assessment of how the respondent's own method delayed "
            "the finding.")),
      ],
      "An audit account with an unusually clear outcome: a distributional "
      "finding linking detection latency, street lighting and ward income "
      "produced a lighting upgrade at nine junctions. The respondent is "
      "careful about what one city over eleven months can support, and "
      "pointed about what did not change — the detection model and the "
      "reporting practice that let the disparity go unnoticed. He notes that "
      "his own data-only method took three months to find what twenty "
      "conversations would have surfaced in a week."),

    # =================================================================
    # A04 — 都市計畫學者
    # 樣態：預期強（長期）、參與中等、對回應性中立
    # =================================================================
    R("A04", "Associate professor of urban planning",
      dict(institution_type="academia", role_level="researcher",
           sector="energy_sustainability", experience="11_20y"),
      [
        Q("What's your reading of what this system does to the city?"),

        A("It makes driving slightly better, which over ten years makes "
          "driving slightly more attractive, which puts more cars on the "
          "road, which uses up the capacity the system created. Traffic "
          "engineers have known this since the sixties and it has a name, "
          "induced demand, and it gets left out of every business case I have "
          "ever read including this one.",
          C(ANT, "P", "Applies induced demand to the ten-year horizon",
            "It makes driving slightly better, which over ten years makes "
            "driving slightly more attractive, which puts more cars on the "
            "road, which uses up the capacity the system created.",
            "Long-horizon systemic reasoning about second-order effects, "
            "grounded in an established mechanism."),
          C(ANT, "N", "Known mechanism omitted from the business case",
            "it gets left out of every business case I have "
            "ever read including this one",
            "A well-established effect is absent from the project's own "
            "forward assessment.")),

        Q("Was that raised during planning?"),

        A("I raised it at a workshop. The response was that the system is "
          "signal timing, not transport policy, and induced demand is a "
          "policy question. Which is true and also a way of ensuring nobody "
          "owns it. Every actor here has a defensible reason why the "
          "long-term question belongs to someone else, and the sum of those "
          "defensible reasons is that it belongs to nobody.",
          C(ANT, "N", "Long-term question distributed until unowned",
            "Every actor here has a defensible reason why the "
            "long-term question belongs to someone else, and the sum of those "
            "defensible reasons is that it belongs to nobody.",
            "Diagnoses how a division of scope systematically produces an "
            "absence of anticipation.")),

        Q("You ran a scenario workshop yourself, I think?"),

        A("We did, with about thirty people — planners, two councillors, a "
          "bus operator, four residents, a freight association. Three "
          "scenarios out to 2040. The useful part wasn't the scenarios, it "
          "was that the freight association and the disability group ended up "
          "agreeing about kerb space, which neither of them expected and "
          "neither would have discovered in a consultation questionnaire.",
          C(ENG, "P", "Scenario workshop across conflicting interests",
            "We did, with about thirty people — planners, two councillors, a "
            "bus operator, four residents, a freight association.",
            "Engagement designed to bring differently-positioned actors into "
            "the same deliberation."),
          C(ANT, "P", "Scenarios surfaced an unexpected alignment",
            "the freight association and the disability group ended up "
            "agreeing about kerb space, which neither of them expected",
            "The anticipatory exercise produced knowledge that no party held "
            "beforehand.")),

        Q("Did the workshop output go anywhere?"),

        A("Into the local plan consultation, where it sits alongside four "
          "hundred other submissions. I'd call that neither success nor "
          "failure. It's in the record. Sometimes things in the record get "
          "picked up years later by someone you've never met. I've stopped "
          "measuring impact on a three-year cycle because nothing in planning "
          "works on a three-year cycle.",
          C(RES, "P", "Treats the record as a slow-acting channel",
            "Sometimes things in the record get "
            "picked up years later by someone you've never met.",
            "A weak but genuine account of how adaptation happens on planning "
            "timescales. A second coder might reasonably code this as neutral or "
            "negative — the deliberate ambiguity is retained.")),

        Q("If the city asked you what to change tomorrow, what would you say?"),

        A("Publish the objective function. One page, plain language: here is "
          "what the system is trying to maximise, here is what it treats as a "
          "cost, here is who decided. Nobody can argue with a system whose "
          "goals are undisclosed, and at the moment nobody outside the "
          "vendor knows what it is optimising.",
          C(ENG, "P", "Publication of the objective function as a precondition",
            "Publish the objective function. One page, plain language: here is "
            "what the system is trying to maximise, here is what it treats as a "
            "cost, here is who decided.",
            "Proposes the informational condition without which meaningful "
            "public deliberation is impossible.")),
      ],
      "A long-horizon account built on induced demand: the system makes "
      "driving marginally better and therefore, over a decade, consumes the "
      "capacity it created. The respondent's sharpest observation is "
      "structural — every actor has a defensible reason why the long-term "
      "question belongs to someone else, and the sum of those reasons is that "
      "it belongs to nobody. His scenario workshop produced an alignment "
      "between freight and disability interests that no questionnaire would "
      "have found."),

    # =================================================================
    # A05 — 研究倫理審查委員
    # 樣態：反思性強、參與中、預期中；對制度限制有具體診斷
    # =================================================================
    R("A05", "Chair, university research ethics committee",
      dict(institution_type="academia", role_level="policy_maker",
           sector="other", experience="over_20y"),
      [
        Q("Did any part of this deployment come before your committee?"),

        A("Only the research on it, not the system itself. That distinction "
          "is the whole problem in one sentence. If a doctoral student wants "
          "to interview twelve people about the cameras, that comes to me and "
          "I will spend forty minutes on the consent form. The decision to "
          "install the cameras and point them at a hundred thousand people "
          "went through a procurement committee. Nobody thinks this is "
          "strange except the people who say it out loud.",
          C(REF, "P", "Names the asymmetry between research and deployment review",
            "If a doctoral student wants "
            "to interview twelve people about the cameras, that comes to me and "
            "I will spend forty minutes on the consent form. The decision to "
            "install the cameras and point them at a hundred thousand people "
            "went through a procurement committee.",
            "Critical scrutiny of the institutional arrangement the "
            "respondent himself administers.")),

        Q("Could your committee's remit cover deployments?"),

        A("Not as constituted. We have no authority over the city and no "
          "capacity if we did — we're eleven academics and an administrator, "
          "meeting six times a year, and we're already behind. I mention the "
          "capacity because people propose expanding ethics review as though "
          "review were free.",
          C(REF, "P", "Refuses a proposal that ignores capacity",
            "people propose expanding ethics review as though "
            "review were free",
            "Examines the practicality of a reform commonly proposed in the "
            "respondent's own field.")),

        Q("What have you seen change in the studies that do come to you?"),

        A("More applications now include a data-protection impact assessment, "
          "which is progress. What I still almost never see is a plan for "
          "what the researcher will do if the finding is inconvenient to the "
          "funder. I've started asking for it. Roughly a third of applicants "
          "have no answer and about a fifth are visibly irritated that I "
          "asked.",
          C(ANT, "P", "Requires a plan for inconvenient findings",
            "What I still almost never see is a plan for "
            "what the researcher will do if the finding is inconvenient to the "
            "funder. I've started asking for it.",
            "An anticipatory requirement introduced into a standing process, "
            "aimed at a foreseeable conflict."),
          C(RES, "P", "Changed committee practice on the basis of a pattern",
            "I've started asking for it.",
            "The respondent altered a standing procedure in response to a "
            "repeated observation.")),

        Q("Do affected communities have any voice in your process?"),

        A("We have one lay member. One, out of twelve. She is excellent and "
          "she is also one person doing the work of a category. When she can't "
          "attend, the public perspective is simply absent from that meeting "
          "and we proceed anyway. We should not proceed anyway.",
          C(ENG, "N", "Public representation reduced to a single member",
            "We have one lay member. One, out of twelve.",
            "Structural under-representation of the affected public in a "
            "body whose function is to protect them."),
          C(REF, "P", "States that current practice is not defensible",
            "When she can't "
            "attend, the public perspective is simply absent from that meeting "
            "and we proceed anyway. We should not proceed anyway.",
            "Explicit judgement against the respondent's own committee's "
            "practice.")),
      ],
      "An ethics chair whose central observation is an institutional "
      "asymmetry: interviewing twelve people about the cameras requires "
      "ethics review, while pointing the cameras at a hundred thousand people "
      "requires a procurement committee. He resists the easy reform — "
      "expanding review as though review were free — and has instead changed "
      "one concrete practice, asking applicants what they will do if a "
      "finding is inconvenient to the funder. He states plainly that "
      "proceeding without the single lay member is not defensible."),

    # =================================================================
    # A06 — 博士生（研究助理）
    # 樣態：參與強、反思性強、預期弱、回應性負向
    # =================================================================
    R("A06", "Doctoral researcher and project research assistant",
      dict(institution_type="academia", role_level="researcher",
           sector="ict_ai", experience="under_5y"),
      [
        Q("What's your role on the project?"),

        A("Officially I do the fieldwork. Unofficially I'm the person who "
          "sits in the community meetings and then writes the paragraph that "
          "gets cut from the report. I've counted. Four times now.",
          C(RES, "N", "Community input systematically removed at write-up",
            "I'm the person who "
            "sits in the community meetings and then writes the paragraph that "
            "gets cut from the report. I've counted. Four times now.",
            "A specific, countable mechanism by which engagement fails to "
            "reach the output.")),

        Q("On what grounds is it cut?"),

        A("Length, usually. Sometimes 'this belongs in the appendix'. Once, "
          "quite honestly, 'we don't want to give them ammunition'. That was "
          "said in a meeting and nobody objected, including me, and I've "
          "thought about that a lot since.",
          C(REF, "P", "Owns her own silence in the meeting",
            "That was "
            "said in a meeting and nobody objected, including me, and I've "
            "thought about that a lot since.",
            "Reflexive attention to the respondent's own participation in the "
            "practice she is describing."),
          C(RES, "N", "Findings suppressed to avoid providing ammunition",
            "'we don't want to give them ammunition'",
            "Explicit refusal to let evidence circulate where it might "
            "support opposition.")),

        Q("Tell me about the fieldwork itself."),

        A("Sixty-one street intercepts and nine longer interviews, over four "
          "months, at eight junctions chosen to vary by ward income and "
          "footfall. I did evenings and weekends as well because the daytime "
          "sample was retired people and parents, which is a real population "
          "but not the whole one.",
          C(ENG, "P", "Sampling designed to reach beyond convenient hours",
            "I did evenings and weekends as well because the daytime "
            "sample was retired people and parents, which is a real population "
            "but not the whole one.",
            "Engagement designed against the grain of what is easy to "
            "collect."),
          C(REF, "P", "Interrogates who the convenient sample represents",
            "the daytime "
            "sample was retired people and parents, which is a real population "
            "but not the whole one",
            "Examination of how the method shapes whose voice is captured.")),

        Q("Did anything surprise you?"),

        A("How few people knew there was a system. Roughly two in three had "
          "no idea the junctions had changed at all. Which reframes the whole "
          "consultation question, doesn't it — you can't consult people about "
          "a thing they don't know exists, and the consultation was "
          "advertised in the places you'd look if you already knew.",
          C(ENG, "N", "Consultation reached only the already-informed",
            "the consultation was "
            "advertised in the places you'd look if you already knew",
            "The engagement channel systematically excluded the majority who "
            "were unaware of the system."),
          C(ANT, "N", "Public awareness never treated as a design variable",
            "Roughly two in three had "
            "no idea the junctions had changed at all.",
            "The project did not anticipate that the population it intended "
            "to consult would not know the system existed.")),

        Q("What will you do with the material that gets cut?"),

        A("Put it in the thesis, where four people will read it. I know how "
          "that sounds. I'm also, and I go back and forth on whether this is "
          "appropriate, giving the community group a plain-language summary "
          "of my own findings directly, because they gave me the data and I "
          "don't think a paywall is a good reason for them not to have it.",
          C(ENG, "P", "Returns findings directly to participants",
            "giving the community group a plain-language summary "
            "of my own findings directly, because they gave me the data and I "
            "don't think a paywall is a good reason for them not to have it",
            "Reciprocity toward participants enacted as a practice, not "
            "merely endorsed."),
          C(REF, "P", "Unsettled about whether the practice is appropriate",
            "I go back and forth on whether this is "
            "appropriate",
            "Ongoing scrutiny of her own decision rather than settled "
            "self-justification.")),
      ],
      "The junior member of the project team, and the one with the most "
      "direct contact with residents. Her fieldwork found that two in three "
      "people did not know the system existed, which undercuts the premise of "
      "the consultation that was run. She reports a countable mechanism of "
      "suppression — four community paragraphs cut from reports, once "
      "explicitly to avoid giving opponents ammunition — and holds herself to "
      "account for not objecting. She now returns plain-language findings to "
      "participants directly, while remaining unsettled about whether that is "
      "her call to make.")
