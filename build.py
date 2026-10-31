#!/usr/bin/env python3
"""InClock static site generator. Run: python3 build.py  -> writes pages to the repo root"""
import os, shutil, html

OUT = "."
E = html.escape

NAV = [
    ("Services", "services.html", [
        ("Agentic AI", "agentic-ai.html"),
        ("Generative AI", "generative-ai.html"),
        ("AI Consulting & Strategy", "ai-consulting.html"),
        ("Machine Learning", "machine-learning.html"),
        ("Data & AI Engineering", "data-engineering.html"),
        ("AI Ops & Managed Run", "ai-ops.html"),
    ]),
    ("Industries", "industries.html", []),
    ("Case Studies", "case-studies.html", []),
    ("How We Work", "how-we-work.html", []),
    ("About", "about.html", []),
    ("Blog", "blog.html", []),
]

SERVICES = {
    "agentic-ai.html": dict(
        name="Agentic AI", icon="🤖",
        tag="Autonomous agents that plan, decide and act across your systems.",
        intro="We design multi-agent systems that take on whole workflows - not just answer questions - with guardrails, human-in-the-loop checkpoints and full audit trails.",
        offer=[("Multi-agent orchestration", "Planner, worker and reviewer agents coordinating through shared memory and tools."),
               ("Tool & API integration", "Agents that safely operate your CRM, ERP, ticketing, email and internal APIs."),
               ("Human-in-the-loop controls", "Approval gates, confidence thresholds and escalation paths built in."),
               ("Evaluation & observability", "Tracing, regression suites and cost/latency dashboards for every run."),
               ("Agent security", "Scoped credentials, sandboxing, prompt-injection defences and policy enforcement."),
               ("Agent platforms", "Reusable runtime, registry and governance so teams ship agents faster.")],
        uses=["Customer support resolution agents", "Sales research & outreach agents", "Finance close & reconciliation agents", "IT and DevOps incident-response agents", "Procurement and vendor-onboarding agents"]),
    "generative-ai.html": dict(
        name="Generative AI", icon="✨",
        tag="LLM-powered products grounded in your data.",
        intro="From RAG knowledge assistants to content and code copilots, we turn foundation models into dependable features your teams and customers actually use.",
        offer=[("RAG & enterprise search", "Grounded answers with citations over your documents, wikis and databases."),
               ("Copilots & assistants", "Embedded assistants for support, sales, ops, engineering and legal."),
               ("Document intelligence", "Extraction, summarisation and classification of contracts, invoices and reports."),
               ("Content generation", "Brand-safe text, image and report generation with review workflows."),
               ("Fine-tuning & prompt ops", "Model selection, evaluation, prompt versioning and cost optimisation."),
               ("Voice & multimodal", "Voice agents, vision and mixed-media understanding.")],
        uses=["Internal knowledge assistant", "Contract review copilot", "Automated report drafting", "Customer-facing chat and voice", "Developer productivity tools"]),
    "ai-consulting.html": dict(
        name="AI Consulting & Strategy", icon="🧭",
        tag="Discover where AI pays off on your clock - then prove it fast.",
        intro="We find the highest-ROI opportunities, validate them in weeks, and give leadership a roadmap that ties AI investment to measurable business outcomes.",
        offer=[("AI opportunity discovery", "Process mapping and use-case scoring by value, feasibility and risk."),
               ("Readiness assessment", "Data, architecture, talent and governance gap analysis."),
               ("Proof of value in 4 weeks", "Working prototype on your data with a clear go/no-go business case."),
               ("AI roadmap & business case", "Sequenced 12-24 month plan with budget, team and KPIs."),
               ("Responsible AI & governance", "Policy, risk controls and compliance aligned to your industry."),
               ("Build vs. buy advisory", "Vendor, model and platform selection without lock-in.")],
        uses=["Board-level AI strategy", "Use-case prioritisation workshops", "Vendor and model evaluation", "AI operating model design", "Cost and ROI modelling"]),
    "machine-learning.html": dict(
        name="Machine Learning", icon="📈",
        tag="Predictive models that move real operational numbers.",
        intro="Classical and deep learning for forecasting, scoring, anomaly detection and optimisation - engineered for production, not notebooks.",
        offer=[("Forecasting & demand planning", "Time-series models for demand, inventory, workforce and revenue."),
               ("Classification & scoring", "Churn, lead, credit and risk models with explainability."),
               ("Anomaly & fraud detection", "Real-time detection on streaming transactional data."),
               ("Computer vision", "Inspection, OCR, tracking and quality control."),
               ("Recommendation systems", "Personalisation across product, content and offers."),
               ("MLOps", "CI/CD for models, feature stores, monitoring and drift alerts.")],
        uses=["Demand forecasting", "Predictive maintenance", "Dynamic pricing", "Fraud detection", "Visual quality inspection"]),
    "data-engineering.html": dict(
        name="Data & AI Engineering", icon="🧱",
        tag="The data foundations and platforms AI depends on.",
        intro="Pipelines, lakehouses and vector stores built to be reliable, governed and cost-efficient - so every model and agent starts from trusted data.",
        offer=[("Modern data platforms", "Lakehouse and warehouse architecture on AWS, Azure or GCP."),
               ("Pipelines & streaming", "Batch and real-time ingestion with quality checks."),
               ("Vector & knowledge stores", "Embeddings, graph and hybrid search infrastructure."),
               ("Data governance", "Lineage, catalog, access control and PII handling."),
               ("Cloud & platform engineering", "Scalable, secure infrastructure as code."),
               ("Application engineering", "APIs, web and mobile apps that deliver AI to users.")],
        uses=["Unified customer data platform", "Real-time analytics", "RAG data pipelines", "Data migration & modernisation", "AI-ready application backends"]),
    "ai-ops.html": dict(
        name="AI Ops & Managed Run", icon="⏱️",
        tag="We run your AI in production - on clock time, 24/7.",
        intro="Shipping is the start. Our managed service monitors, tunes and improves your AI systems continuously, with SLAs and monthly business reviews.",
        offer=[("24/7 monitoring & support", "On-call coverage with defined SLAs for agents and models."),
               ("Quality & drift management", "Continuous evaluation, retraining and prompt tuning."),
               ("Cost optimisation (FinOps)", "Model routing, caching and right-sizing to cut inference spend."),
               ("Security & compliance ops", "Access reviews, audit logs and policy checks."),
               ("Release management", "Safe rollouts, A/B tests and rollback."),
               ("Dedicated AI pods", "Embedded engineers who extend your team on demand.")],
        uses=["Managed agent fleet", "LLM gateway & cost control", "Model monitoring", "Compliance reporting", "Capacity and roadmap reviews"]),
}

INDUSTRIES = [
    ("Financial Services", "🏦", "KYC automation, fraud detection, underwriting copilots and reconciliation agents."),
    ("Retail & eCommerce", "🛍️", "Demand forecasting, personalisation, support agents and catalog enrichment."),
    ("Manufacturing", "🏭", "Predictive maintenance, visual inspection and supply-chain planning agents."),
    ("Logistics & Supply Chain", "🚚", "Route optimisation, ETA prediction, freight document processing."),
    ("Insurance", "🛡️", "Claims triage, policy Q&A, fraud scoring and broker assistants."),
    ("Telecom", "📡", "Churn prediction, network anomaly detection and service-desk agents."),
    ("Education & EdTech", "🎓", "Adaptive tutors, content generation and admissions automation."),
    ("Real Estate & PropTech", "🏢", "Lead qualification, valuation models and lease abstraction."),
    ("Energy & Utilities", "⚡", "Load forecasting, asset monitoring and field-service copilots."),
    ("Travel & Hospitality", "✈️", "Dynamic pricing, concierge agents and review intelligence."),
    ("Legal & Professional Services", "⚖️", "Contract analysis, research assistants and matter automation."),
    ("SaaS & Technology", "💻", "Embedded copilots, agentic features and AI platform engineering."),
]

# Illustrative engagement examples (not real client results).
CASES = [
    ("Support Resolution Agents", "Retail & eCommerce", "Agentic AI",
     "A multi-agent system triages tickets, checks order systems, issues refunds within policy and escalates edge cases to humans.",
     ["Tier-1 tickets resolved autonomously", "Policy-bound refund actions with audit trail", "Human review on low-confidence cases"]),
    ("Contract Intelligence Copilot", "Legal & Professional Services", "Generative AI",
     "RAG assistant extracts clauses, flags risk and drafts redlines with citations back to source documents.",
     ["Clause extraction across thousands of contracts", "Cited, reviewable answers", "Integrated with the DMS"]),
    ("Demand Forecasting Platform", "Manufacturing", "Machine Learning",
     "SKU-level forecasting with automated retraining and drift monitoring to cut stock-outs and overstock.",
     ["SKU/location forecasts", "Automated MLOps pipeline", "Planner-facing explainability"]),
    ("Claims Triage Agent", "Insurance", "Agentic AI",
     "Agents read claim packets, validate coverage, score fraud risk and route to the right adjuster.",
     ["Document understanding", "Fraud-risk scoring", "Adjuster workbench"]),
    ("AI Roadmap & Proof of Value", "Financial Services", "AI Consulting",
     "Discovery across operations teams, ranked use-cases and a 4-week prototype that secured funding for rollout.",
     ["40+ use-cases scored", "Working prototype in 4 weeks", "Phased 18-month roadmap"]),
    ("Managed LLM Platform", "SaaS & Technology", "AI Ops",
     "Central LLM gateway with routing, caching, evaluation and spend controls across product teams.",
     ["Unified model gateway", "Cost dashboards per team", "Continuous evaluation"]),
]

PROCESS = [
    ("Discover", "Weeks 1-2", "Map workflows, data and constraints. Score use-cases by value, feasibility and risk, and pick the first one to prove."),
    ("Design", "Weeks 2-3", "Architecture, agent and data design, success metrics, guardrails and a clear build plan with milestones."),
    ("Prove", "Weeks 3-6", "Working prototype on your real data, evaluated against agreed KPIs. Go / no-go with a business case."),
    ("Implement", "Weeks 6-14", "Production build with integrations, security, evaluation harnesses and change management."),
    ("Run", "Ongoing", "Managed operations on clock time: monitoring, tuning, cost control and monthly business reviews."),
]

POSTS = [
    ("What Is Agentic AI - and Where Should You Start?", "Agentic AI", "A practical primer on agents vs. chatbots, and how to pick a first workflow."),
    ("RAG vs. Fine-Tuning: Choosing the Right Approach", "Generative AI", "A decision framework based on data freshness, cost and accuracy needs."),
    ("Measuring the ROI of AI Agents", "Strategy", "Baselines, KPIs and the hidden costs most business cases miss."),
    ("Guardrails for Autonomous Agents", "Security", "Scopes, approvals and audit trails that keep agents safe in production."),
    ("From POC to Production: Why 80% of AI Pilots Stall", "Delivery", "The operational gaps between a demo and a dependable system."),
    ("LLM Cost Control: Routing, Caching and Evals", "AI Ops", "Cut inference spend without sacrificing quality."),
]

FAQ = [
    ("How quickly can we see results?", "Most clients have a working proof of value in 4-6 weeks, built on their own data and measured against agreed KPIs."),
    ("Do you work with our existing cloud and tools?", "Yes. We build on AWS, Azure or GCP and integrate with your existing CRM, ERP, ticketing and data stack. We stay model-agnostic to avoid lock-in."),
    ("How do you keep AI agents safe?", "Scoped credentials, approval gates, sandboxed tool access, evaluation suites and complete audit logs - designed in from day one."),
    ("Who owns the IP?", "You do. Code, prompts, data pipelines and evaluation assets built for you are yours."),
    ("What engagement models do you offer?", "Fixed-scope proof of value, time-and-materials delivery, dedicated AI pods, and managed run services with SLAs."),
]


def nav_html(active):
    items = []
    for label, href, sub in NAV:
        cls = ' class="active"' if active == href or any(active == h for _, h in sub) else ""
        if sub:
            dd = "".join(f'<a href="{h}">{E(l)}</a>' for l, h in sub)
            items.append(f'<li class="has-dd"><a href="{href}"{cls}>{E(label)} <span aria-hidden="true">▾</span></a><div class="dd">{dd}</div></li>')
        else:
            items.append(f'<li><a href="{href}"{cls}>{E(label)}</a></li>')
    return "".join(items)


def page(fname, title, desc, body, active=None):
    footer_services = "".join(f'<li><a href="{h}">{E(l)}</a></li>' for l, h in NAV[0][2])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site-header">
  <div class="container nav-wrap">
    <a class="logo" href="index.html" aria-label="InClock home"><span class="logo-mark">◔</span><span>In<b>Clock</b></span></a>
    <button class="menu-btn" aria-label="Toggle menu" aria-expanded="false">☰</button>
    <nav class="nav"><ul>{nav_html(active or fname)}</ul>
      <a class="btn btn-primary btn-sm" href="contact.html">Talk to an Expert</a></nav>
  </div>
</header>
<main>
{body}
</main>
<footer class="site-footer">
  <div class="container footer-grid">
    <div><a class="logo" href="index.html"><span class="logo-mark">◔</span><span>In<b>Clock</b></span></a>
      <p class="muted">We help businesses discover, implement and run AI and Agentic AI solutions - on clock time.</p></div>
    <div><h4>Services</h4><ul>{footer_services}</ul></div>
    <div><h4>Company</h4><ul><li><a href="about.html">About</a></li><li><a href="industries.html">Industries</a></li><li><a href="case-studies.html">Case Studies</a></li><li><a href="how-we-work.html">How We Work</a></li><li><a href="blog.html">Blog</a></li><li><a href="careers.html">Careers</a></li></ul></div>
    <div><h4>Contact</h4><ul><li><a href="contact.html">Get in touch</a></li><li><a href="mailto:hello@inclock.ai">hello@inclock.ai</a></li></ul></div>
  </div>
  <div class="container footer-bottom"><span>© <span id="yr">2026</span> InClock. All rights reserved.</span><span><a href="privacy.html">Privacy</a> · <a href="terms.html">Terms</a></span></div>
</footer>
<script src="assets/main.js"></script>
</body>
</html>
"""


def cta(title="Ready to put AI on the clock?", sub="Tell us the workflow that costs you the most time. We'll show you what an agent can do with it."):
    return f"""<section class="cta"><div class="container"><h2>{E(title)}</h2><p>{E(sub)}</p>
<a class="btn btn-light" href="contact.html">Book a free AI discovery call</a></div></section>"""


def hero(h1, sub, ctas=True, eyebrow=""):
    eb = f'<span class="eyebrow">{E(eyebrow)}</span>' if eyebrow else ""
    btns = '<div class="hero-cta"><a class="btn btn-primary" href="contact.html">Book a Discovery Call</a><a class="btn btn-ghost" href="case-studies.html">See What We Build</a></div>' if ctas else ""
    return f'<section class="hero"><div class="container">{eb}<h1>{h1}</h1><p class="lead">{E(sub)}</p>{btns}</div></section>'


def faq_html(items):
    return '<div class="faq">' + "".join(f"<details><summary>{E(q)}</summary><p>{E(a)}</p></details>" for q, a in items) + "</div>"


def build_home():
    svc = "".join(
        f'<a class="card" href="{f}"><div class="ico">{s["icon"]}</div><h3>{E(s["name"])}</h3><p>{E(s["tag"])}</p><span class="more">Learn more →</span></a>'
        for f, s in SERVICES.items())
    ind = "".join(f'<a class="chip" href="industries.html">{i} {E(n)}</a>' for n, i, _ in INDUSTRIES)
    cases = "".join(
        f'<a class="card case" href="case-studies.html"><span class="tag">{E(c[2])}</span><h3>{E(c[0])}</h3><p class="muted">{E(c[1])}</p><p>{E(c[3])}</p></a>'
        for c in CASES[:3])
    steps = "".join(
        f'<li><span class="num">{i+1}</span><div><h3>{E(n)} <small>{E(t)}</small></h3><p>{E(d)}</p></div></li>'
        for i, (n, t, d) in enumerate(PROCESS))
    body = f"""
<section class="hero hero-home"><div class="container">
  <span class="eyebrow">AI &amp; Agentic AI Solutions</span>
  <h1>Discover, implement and run <span class="grad">AI on clock time.</span></h1>
  <p class="lead">InClock helps businesses find where AI and autonomous agents pay off, ship them in weeks not quarters, and keep them performing in production.</p>
  <div class="hero-cta"><a class="btn btn-primary" href="contact.html">Book a Discovery Call</a><a class="btn btn-ghost" href="services.html">Explore Services</a></div>
  <ul class="stats">
    <li><b>4 wks</b><span>to proof of value</span></li>
    <li><b>24/7</b><span>managed AI operations</span></li>
    <li><b>3 steps</b><span>discover · implement · run</span></li>
    <li><b>100%</b><span>IP owned by you</span></li>
  </ul>
</div></section>

<section class="section"><div class="container">
  <div class="section-head"><span class="eyebrow">What we do</span><h2>End-to-end AI, from idea to operations</h2>
  <p class="muted">One partner for strategy, engineering and the ongoing run of your AI systems.</p></div>
  <div class="grid grid-3">{svc}</div>
</div></section>

<section class="section alt"><div class="container">
  <div class="section-head"><span class="eyebrow">Our model</span><h2>Discover. Implement. Run.</h2></div>
  <div class="grid grid-3">
    <div class="card"><div class="ico">🔍</div><h3>Discover</h3><p>Find the workflows where AI and agents deliver measurable return, and prove it with a working prototype.</p></div>
    <div class="card"><div class="ico">🛠️</div><h3>Implement</h3><p>Production-grade agents, models and data platforms integrated with your systems, secured and evaluated.</p></div>
    <div class="card"><div class="ico">⏱️</div><h3>Run</h3><p>We monitor, tune and improve continuously - on clock time - with SLAs and monthly business reviews.</p></div>
  </div>
</div></section>

<section class="section"><div class="container">
  <div class="section-head"><span class="eyebrow">Industries</span><h2>Built for the way your industry works</h2></div>
  <div class="chips">{ind}</div>
</div></section>

<section class="section alt"><div class="container">
  <div class="section-head"><span class="eyebrow">Work</span><h2>What we build</h2><p class="muted">Representative engagements - illustrative examples of our delivery.</p></div>
  <div class="grid grid-3">{cases}</div>
  <p class="center"><a class="btn btn-ghost" href="case-studies.html">All case studies</a></p>
</div></section>

<section class="section"><div class="container narrow">
  <div class="section-head"><span class="eyebrow">Process</span><h2>From first call to production in weeks</h2></div>
  <ol class="steps">{steps}</ol>
</div></section>

<section class="section alt"><div class="container narrow">
  <div class="section-head"><h2>Frequently asked questions</h2></div>{faq_html(FAQ)}
</div></section>
{cta()}
"""
    return page("index.html", "InClock | AI & Agentic AI Solutions - Discover, Implement, Run",
                "InClock helps businesses discover, implement and run AI and Agentic AI solutions on clock time.", body)


def build_services():
    cards = "".join(
        f'<a class="card" href="{f}"><div class="ico">{s["icon"]}</div><h3>{E(s["name"])}</h3><p>{E(s["intro"])}</p><span class="more">Learn more →</span></a>'
        for f, s in SERVICES.items())
    body = hero("AI services across the <span class='grad'>full lifecycle</span>", "Strategy, engineering and managed operations for AI and Agentic AI.", eyebrow="Services") + \
        f'<section class="section"><div class="container"><div class="grid grid-3">{cards}</div></div></section>' + cta()
    return page("services.html", "AI Services | InClock", "AI and Agentic AI services: consulting, generative AI, machine learning, data engineering and managed AI operations.", body)


def build_service(f, s):
    offer = "".join(f'<div class="card"><h3>{E(t)}</h3><p>{E(d)}</p></div>' for t, d in s["offer"])
    uses = "".join(f"<li>{E(u)}</li>" for u in s["uses"])
    body = hero(E(s["name"]), s["tag"], eyebrow="Services") + f"""
<section class="section"><div class="container narrow"><p class="lead-dark">{E(s["intro"])}</p></div></section>
<section class="section alt"><div class="container"><div class="section-head"><h2>What we deliver</h2></div><div class="grid grid-3">{offer}</div></div></section>
<section class="section"><div class="container narrow"><div class="section-head"><h2>Common use cases</h2></div><ul class="ticks">{uses}</ul></div></section>
<section class="section alt"><div class="container narrow"><div class="section-head"><h2>How we engage</h2></div>
<div class="grid grid-3"><div class="card"><h3>Proof of Value</h3><p>Fixed-scope, 4-6 weeks, on your data.</p></div><div class="card"><h3>Build &amp; Integrate</h3><p>Delivery team to production with milestones.</p></div><div class="card"><h3>Run</h3><p>Managed operations with SLAs.</p></div></div></div></section>
{cta()}"""
    return page(f, f'{s["name"]} | InClock', s["tag"], body, active=f)


def build_industries():
    cards = "".join(f'<div class="card"><div class="ico">{i}</div><h3>{E(n)}</h3><p>{E(d)}</p></div>' for n, i, d in INDUSTRIES)
    body = hero("AI tailored to <span class='grad'>your industry</span>", "Domain-aware solutions with the right data, compliance and workflow context.", eyebrow="Industries") + \
        f'<section class="section"><div class="container"><div class="grid grid-3">{cards}</div></div></section>' + cta()
    return page("industries.html", "Industries | InClock", "AI and agentic solutions for finance, retail, manufacturing, logistics, insurance and more.", body)


def build_cases():
    cards = "".join(
        f'<article class="card case"><span class="tag">{E(c[2])}</span><h3>{E(c[0])}</h3><p class="muted">{E(c[1])}</p><p>{E(c[3])}</p><ul class="ticks">{"".join(f"<li>{E(x)}</li>" for x in c[4])}</ul></article>'
        for c in CASES)
    body = hero("Case <span class='grad'>studies</span>", "Representative engagements showing how we deliver.", eyebrow="Work") + \
        f'<section class="section"><div class="container"><p class="note">These are illustrative examples of the kinds of solutions we build; client names and metrics are withheld.</p><div class="grid grid-2">{cards}</div></div></section>' + cta()
    return page("case-studies.html", "Case Studies | InClock", "Examples of AI and agentic AI solutions delivered by InClock.", body)


def build_how():
    steps = "".join(
        f'<li><span class="num">{i+1}</span><div><h3>{E(n)} <small>{E(t)}</small></h3><p>{E(d)}</p></div></li>'
        for i, (n, t, d) in enumerate(PROCESS))
    models = [("Proof of Value", "Fixed scope, 4-6 weeks."), ("Project Delivery", "Milestone-based build to production."), ("Dedicated AI Pod", "Embedded team that extends yours."), ("Managed Run", "SLA-backed operations and improvement.")]
    m = "".join(f'<div class="card"><h3>{E(a)}</h3><p>{E(b)}</p></div>' for a, b in models)
    body = hero("How we <span class='grad'>work</span>", "A transparent process that gets to value fast and keeps it there.", eyebrow="Process") + f"""
<section class="section"><div class="container narrow"><ol class="steps">{steps}</ol></div></section>
<section class="section alt"><div class="container"><div class="section-head"><h2>Engagement models</h2></div><div class="grid grid-4">{m}</div></div></section>
<section class="section"><div class="container narrow"><div class="section-head"><h2>FAQ</h2></div>{faq_html(FAQ)}</div></section>{cta()}"""
    return page("how-we-work.html", "How We Work | InClock", "InClock's discover, implement, run process and engagement models.", body)


def build_about():
    vals = [("Clock-time delivery", "Weeks, not quarters. We time-box everything and show working software early."),
            ("Outcomes over demos", "Every project starts with a measurable business KPI."),
            ("Safe by design", "Guardrails, evaluation and audit built in, never bolted on."),
            ("Model-agnostic", "We pick the best tool for the job - no vendor lock-in."),]
    v = "".join(f'<div class="card"><h3>{E(a)}</h3><p>{E(b)}</p></div>' for a, b in vals)
    body = hero("About <span class='grad'>InClock</span>", "We exist to help businesses get real, measurable value from AI - quickly and responsibly.", eyebrow="Company") + f"""
<section class="section"><div class="container narrow"><p class="lead-dark">InClock is an AI company that helps businesses discover, implement and run AI and Agentic AI solutions. Our name is our promise: we work on clock time - fast to prove, fast to ship, and always-on once running.</p>
<p>We combine strategy, engineering and operations in one team, so ideas don't die between the slide deck and production.</p></div></section>
<section class="section alt"><div class="container"><div class="section-head"><h2>What we believe</h2></div><div class="grid grid-4">{v}</div></div></section>{cta("Let's build something that runs.")}"""
    return page("about.html", "About | InClock", "About InClock - an AI and Agentic AI company that works on clock time.", body)


def build_blog():
    cards = "".join(f'<article class="card"><span class="tag">{E(c)}</span><h3>{E(t)}</h3><p>{E(d)}</p><span class="more muted">Coming soon</span></article>' for t, c, d in POSTS)
    body = hero("Insights", "Practical thinking on AI, agents and running them in production.", ctas=False, eyebrow="Blog") + \
        f'<section class="section"><div class="container"><div class="grid grid-3">{cards}</div></div></section>' + cta()
    return page("blog.html", "Blog | InClock", "Insights on AI, agentic AI and operating AI in production.", body)


def build_careers():
    roles = [("AI / ML Engineer", "Build production agents and models."), ("Agentic AI Architect", "Design multi-agent systems and platforms."),
             ("Data Engineer", "Pipelines, lakehouses and vector stores."), ("AI Solutions Consultant", "Lead discovery with clients."),
             ("Full-Stack Engineer", "Ship AI-powered products.")]
    r = "".join(f'<div class="card"><h3>{E(a)}</h3><p>{E(b)}</p><a class="more" href="mailto:careers@inclock.ai?subject={E(a)}">Apply →</a></div>' for a, b in roles)
    body = hero("Build AI that <span class='grad'>actually runs</span>", "Join a small, senior team shipping agents and models into production.", ctas=False, eyebrow="Careers") + \
        f'<section class="section"><div class="container"><div class="section-head"><h2>Open roles</h2></div><div class="grid grid-3">{r}</div></div></section>' + \
        cta("Don't see your role?", "Send us your profile at careers@inclock.ai.")
    return page("careers.html", "Careers | InClock", "Careers at InClock.", body)


def build_contact():
    body = hero("Let's talk <span class='grad'>AI</span>", "Tell us about the workflow, and we'll reply within one business day.", ctas=False, eyebrow="Contact") + """
<section class="section"><div class="container grid grid-2">
  <form class="form" id="contact-form" action="mailto:hello@inclock.ai" method="post" enctype="text/plain">
    <label>Name<input name="name" required></label>
    <label>Work email<input name="email" type="email" required></label>
    <label>Company<input name="company"></label>
    <label>I'm interested in
      <select name="interest"><option>AI Consulting & Strategy</option><option>Agentic AI</option><option>Generative AI</option><option>Machine Learning</option><option>Data & AI Engineering</option><option>AI Ops & Managed Run</option></select></label>
    <label>How can we help?<textarea name="message" rows="5" required></textarea></label>
    <button class="btn btn-primary" type="submit">Send message</button>
    <p class="muted small">This form opens your email client. Wire it to your backend or form service before launch.</p>
  </form>
  <div><div class="card"><h3>Email</h3><p><a href="mailto:hello@inclock.ai">hello@inclock.ai</a></p></div>
  <div class="card" style="margin-top:16px"><h3>What happens next</h3><ul class="ticks"><li>We reply within 1 business day</li><li>30-minute discovery call</li><li>Written opportunity summary and proposal</li></ul></div></div>
</div></section>"""
    return page("contact.html", "Contact | InClock", "Contact InClock to discuss AI and Agentic AI solutions.", body)


def build_legal(f, title):
    body = hero(title, "Placeholder - replace with your reviewed legal text before launch.", ctas=False) + \
        '<section class="section"><div class="container narrow"><p>This page is a placeholder. Have counsel provide the final policy before going live.</p></div></section>'
    return page(f, f"{title} | InClock", title, body)


CSS = """
:root{--bg:#fff;--fg:#0f172a;--muted:#5b6475;--line:#e5e8ef;--alt:#f6f8fc;--brand:#4f46e5;--brand2:#06b6d4;--dark:#0b1020;--radius:14px}
@media(prefers-color-scheme:dark){:root{--bg:#0b1020;--fg:#e8ecf6;--muted:#98a2b8;--line:#232a40;--alt:#10172b;--dark:#070b16}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font:16px/1.65 Inter,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--fg);background:var(--bg)}
a{color:inherit;text-decoration:none}img{max-width:100%}
.container{max-width:1160px;margin:0 auto;padding:0 20px}.narrow{max-width:820px}
.muted{color:var(--muted)}.small{font-size:13px}.center{text-align:center;margin-top:32px}
h1,h2,h3{line-height:1.2;margin:0 0 .5em}h1{font-size:clamp(2.1rem,5vw,3.6rem);letter-spacing:-.02em}h2{font-size:clamp(1.6rem,3vw,2.3rem)}h3{font-size:1.15rem}
.grad{background:linear-gradient(90deg,var(--brand),var(--brand2));-webkit-background-clip:text;background-clip:text;color:transparent}
.site-header{position:sticky;top:0;z-index:50;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.nav-wrap{display:flex;align-items:center;justify-content:space-between;height:68px}
.logo{font-size:1.4rem;font-weight:600;display:flex;align-items:center;gap:6px}.logo b{color:var(--brand)}.logo-mark{color:var(--brand2);font-size:1.5rem}
.nav{display:flex;align-items:center;gap:20px}.nav ul{display:flex;gap:6px;list-style:none;margin:0;padding:0}
.nav ul>li>a{padding:8px 12px;border-radius:8px;font-weight:500;display:block}.nav ul>li>a:hover,.nav a.active{color:var(--brand)}
.has-dd{position:relative}.dd{display:none;position:absolute;top:100%;left:0;min-width:240px;background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:8px;box-shadow:0 12px 32px rgba(0,0,0,.12)}
.dd a{display:block;padding:9px 12px;border-radius:8px}.dd a:hover{background:var(--alt)}.has-dd:hover .dd,.has-dd:focus-within .dd{display:block}
.menu-btn{display:none;background:none;border:1px solid var(--line);border-radius:8px;font-size:1.3rem;padding:4px 10px;color:var(--fg)}
.btn{display:inline-block;padding:13px 24px;border-radius:999px;font-weight:600;border:1px solid transparent;cursor:pointer;font-size:1rem;transition:.2s}
.btn-sm{padding:9px 18px;font-size:.92rem}.btn-primary{background:linear-gradient(90deg,var(--brand),#7c3aed);color:#fff}.btn-primary:hover{transform:translateY(-1px);box-shadow:0 8px 22px rgba(79,70,229,.35)}
.btn-ghost{border-color:var(--line);color:var(--fg)}.btn-ghost:hover{border-color:var(--brand);color:var(--brand)}.btn-light{background:#fff;color:#1e1b4b}
.hero{padding:84px 0 64px;background:radial-gradient(900px 400px at 80% -10%,rgba(79,70,229,.18),transparent),radial-gradient(700px 360px at 0% 0%,rgba(6,182,212,.14),transparent)}
.hero-home{padding:110px 0 80px}.lead{font-size:1.2rem;color:var(--muted);max-width:720px}.lead-dark{font-size:1.25rem}
.eyebrow{display:inline-block;font-size:.8rem;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--brand);margin-bottom:12px}
.hero-cta{display:flex;gap:12px;flex-wrap:wrap;margin-top:28px}
.stats{list-style:none;padding:0;margin:56px 0 0;display:grid;grid-template-columns:repeat(4,1fr);gap:16px}
.stats li{border:1px solid var(--line);border-radius:var(--radius);padding:18px;background:var(--bg)}.stats b{display:block;font-size:1.8rem;color:var(--brand)}.stats span{color:var(--muted);font-size:.9rem}
.section{padding:80px 0}.alt{background:var(--alt)}.section-head{max-width:720px;margin:0 auto 40px;text-align:center}
.grid{display:grid;gap:20px}.grid-2{grid-template-columns:repeat(2,1fr)}.grid-3{grid-template-columns:repeat(3,1fr)}.grid-4{grid-template-columns:repeat(4,1fr)}
.card{display:block;border:1px solid var(--line);border-radius:var(--radius);padding:26px;background:var(--bg);transition:.2s}
a.card:hover{border-color:var(--brand);transform:translateY(-3px);box-shadow:0 14px 34px rgba(79,70,229,.12)}
.card p{color:var(--muted);margin:.3em 0 0}.ico{font-size:1.8rem;margin-bottom:10px}.more{display:inline-block;margin-top:14px;color:var(--brand);font-weight:600}
.tag{display:inline-block;font-size:.75rem;font-weight:700;background:rgba(79,70,229,.1);color:var(--brand);padding:3px 10px;border-radius:999px;margin-bottom:10px}
.chips{display:flex;flex-wrap:wrap;gap:10px;justify-content:center}.chip{border:1px solid var(--line);border-radius:999px;padding:10px 18px}.chip:hover{border-color:var(--brand);color:var(--brand)}
.steps{list-style:none;padding:0;margin:0;display:grid;gap:18px}.steps li{display:flex;gap:18px;border:1px solid var(--line);border-radius:var(--radius);padding:22px;background:var(--bg)}
.steps p{margin:.2em 0 0;color:var(--muted)}.steps small{font-weight:500;color:var(--muted);font-size:.8rem;margin-left:8px}
.num{flex:none;width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,var(--brand),var(--brand2));color:#fff;display:grid;place-items:center;font-weight:700}
.ticks{list-style:none;padding:0;margin:12px 0 0}.ticks li{padding:6px 0 6px 28px;position:relative}.ticks li:before{content:"✓";position:absolute;left:0;color:var(--brand2);font-weight:700}
.faq details{border:1px solid var(--line);border-radius:12px;padding:16px 20px;margin-bottom:12px;background:var(--bg)}.faq summary{cursor:pointer;font-weight:600}.faq p{color:var(--muted);margin:10px 0 0}
.cta{background:linear-gradient(120deg,#312e81,#4f46e5 55%,#0891b2);color:#fff;text-align:center;padding:76px 0}.cta p{opacity:.9;max-width:620px;margin:0 auto 26px}
.note{background:var(--alt);border:1px dashed var(--line);border-radius:10px;padding:12px 16px;color:var(--muted);margin-bottom:24px;font-size:.92rem}
.form{display:grid;gap:16px}.form label{display:grid;gap:6px;font-weight:600;font-size:.92rem}
.form input,.form select,.form textarea{font:inherit;padding:12px 14px;border:1px solid var(--line);border-radius:10px;background:var(--bg);color:var(--fg)}
.form input:focus,.form select:focus,.form textarea:focus{outline:2px solid var(--brand);border-color:transparent}
.site-footer{background:var(--dark);color:#cbd2e4;padding:56px 0 20px}.site-footer h4{color:#fff;margin:0 0 12px}.site-footer ul{list-style:none;padding:0;margin:0}.site-footer li{margin:7px 0}.site-footer a:hover{color:#fff}
.site-footer .logo{color:#fff}.site-footer .muted{color:#a9b3cc}.footer-grid{display:grid;grid-template-columns:1.5fr 1fr 1fr 1fr;gap:32px}
.footer-bottom{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;border-top:1px solid #1f2742;margin-top:36px;padding-top:18px;font-size:.88rem}
@media(max-width:900px){.grid-3,.grid-4{grid-template-columns:repeat(2,1fr)}.stats{grid-template-columns:repeat(2,1fr)}.footer-grid{grid-template-columns:1fr 1fr}}
@media(max-width:720px){
 .menu-btn{display:block}.nav{display:none;position:absolute;top:68px;left:0;right:0;background:var(--bg);border-bottom:1px solid var(--line);flex-direction:column;align-items:stretch;padding:12px 20px 20px}
 .nav.open{display:flex}.nav ul{flex-direction:column}.dd{display:block;position:static;border:0;box-shadow:none;padding:0 0 0 14px}
 .grid-2,.grid-3,.grid-4{grid-template-columns:1fr}.section{padding:56px 0}.hero{padding:56px 0 44px}.footer-grid{grid-template-columns:1fr}}
"""

JS = """(function(){
  var b=document.querySelector('.menu-btn'),n=document.querySelector('.nav');
  if(b&&n)b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)});
  var y=document.getElementById('yr');if(y)y.textContent=new Date().getFullYear();
})();
"""


def main():
    os.makedirs(f"{OUT}/assets", exist_ok=True)
    pages = {"index.html": build_home(), "services.html": build_services(), "industries.html": build_industries(),
             "case-studies.html": build_cases(), "how-we-work.html": build_how(), "about.html": build_about(),
             "blog.html": build_blog(), "careers.html": build_careers(), "contact.html": build_contact(),
             "privacy.html": build_legal("privacy.html", "Privacy Policy"), "terms.html": build_legal("terms.html", "Terms of Service")}
    for f, s in SERVICES.items():
        pages[f] = build_service(f, s)
    for f, h in pages.items():
        open(f"{OUT}/{f}", "w", encoding="utf-8").write(h)
    open(f"{OUT}/assets/style.css", "w").write(CSS.strip() + "\n")
    open(f"{OUT}/assets/main.js", "w").write(JS)
    print(f"Built {len(pages)} pages in repo root")


if __name__ == "__main__":
    main()
