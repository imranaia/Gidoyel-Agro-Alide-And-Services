FARM MANAGEMENT SYSTEM
Poultry Stock, Egg Production, Sales & Profit Tracking
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  LOGGING IN / TESTING ACCOUNT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The first time the app runs (locally or on Vercel) it auto-creates one
Super Admin account so you have something to log in and test with:

      Username : admin
      Password : admin1234

Go to My Profile afterwards and change the name, username and password
before handing the system to the real owner/staff.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  WHO CAN DO WHAT (3 account levels)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  SUPER ADMIN (the owner/uncle)
    - Sees everything, everywhere, at any time
    - Only one who can create other Admin accounts
    - Only one who can change farm-wide settings (alert thresholds)

  ADMIN (day-to-day manager)
    - Everything staff can do, PLUS:
    - Create/close batches, record purchases (chickens, feed, tools)
    - Record sales, expenses, run reports & predictive pricing
    - Create/manage Staff accounts

  STAFF (farm workers)
    - Daily operations only: mortality, water, feed given out,
      body weight, medication, vaccination, egg collection
    - Cannot see money figures, cannot make sales or purchases

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HOW THE SYSTEM IS ORGANIZED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  BATCHES
    Every time you buy new chickens, create a new Batch. Enter the
    number you ordered/paid for AND the number you actually received
    (sellers often add extra birds "for free" - record the real count).
    You can have several batches running at once (e.g. an older batch
    already laying eggs, and a newly bought batch still growing).

  DAILY LOG (per batch)
    Mortality (deaths), water used, and remarks - fill this in every
    day. If something did not happen, say so in the remarks.

  FEED
    "Feed In" = bags bought into the store (Admin only - this is a
    purchase). "Feed Out" = bags given to a batch that day (any staff
    can log this). The system tracks the running store balance and
    warns you when it's running low.

  BODY WEIGHT / MEDICATION / VACCINATION
    Add entries whenever you actually do them - weekly, monthly,
    whatever fits your routine. Nothing forces a fixed schedule.

  EGGS
    Set up your Pens first (how many pens, which batch is laying in
    each). Then log crates collected and cracked eggs each day, with
    a note on what was done with the cracked ones.

  SALES
    Record every chicken sale and every egg-crate sale as its own
    transaction with buyer name/phone - this is what feeds the
    profit reports and receipt history.

  TOOLS & EQUIPMENT / EXPENSES
    Anything bought for the farm that isn't feed, chickens, meds or
    vaccines goes here (categorized), plus general running costs
    (labor, transport, utilities).

  FINANCE & PRICING
    Shows cost vs revenue vs profit per batch and for the whole farm.
    The Predictive Pricing calculator: pick a batch, say whether
    you're pricing chickens or egg crates, enter your target profit %,
    and it tells you what price per bird/crate you need to charge.
    Note: cost is shared across a batch's whole life (birds + feed +
    meds + vaccines), so if a batch is earning from BOTH bird sales
    and egg sales at the same time, treat the suggested price as a
    guide, not gospel - it splits total cost across whichever side
    you're pricing that moment.

  DASHBOARD
    At-a-glance view for everyone, with alerts for low feed stock,
    unusually high mortality on a given day, and batches missing
    today's log.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  RUNNING IT LOCALLY (optional, before pushing to GitHub)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Install Python from https://www.python.org/downloads/
  2. pip install -r requirements.txt
  3. python run.py
  Your browser opens at http://localhost:5000 automatically.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DEPLOYING TO VERCEL (so you can check the farm from anywhere)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This project is set up to deploy straight to Vercel:
    vercel.json    -> tells Vercel this is a Python app
    api/index.py   -> the entry point Vercel runs

  STEPS:
  1. Push this project to a GitHub repo (see below).
  2. Go to https://vercel.com, sign in, click "Add New... Project",
     and import that GitHub repo.
  3. Vercel auto-detects the Python config and deploys - no build/
     start command needed, it's already in vercel.json.
  4. (Optional) Add a SECRET_KEY environment variable in the Vercel
     project settings - any long random text you make up.
  5. Deploy. Vercel gives you a permanent web address (like
     https://yourfarm.vercel.app) reachable from any phone or
     computer with internet, anywhere.

  NOTE ON DATA: this deploy uses SQLite for now, stored in Vercel's
  /tmp folder. That's fine for testing and demos, but /tmp doesn't
  persist reliably between deploys/cold starts, so don't rely on it
  for real farm records long-term - ask to switch to a proper hosted
  Postgres database (e.g. Neon, Vercel Postgres) when you're ready to
  go live with real data.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PUSHING TO GITHUB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  1. Create a new (private, if you prefer) repo on https://github.com
  2. In this folder, run:
       git init
       git add .
       git commit -m "Farm management system"
       git remote add origin <your-repo-url>
       git push -u origin main
  3. Then follow the Vercel steps above to import that repo.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FILES IN THIS FOLDER
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  run.py                  -> Local launcher (optional, for testing before push)
  api/index.py             -> Entry point Vercel runs in production
  vercel.json               -> Vercel deployment config
  requirements.txt        -> Python packages needed
  app/                     -> All application code
  farm.db                  -> Your database (auto-created, local mode only)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Farm Management System
  Built with Python Flask + SQLAlchemy
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
