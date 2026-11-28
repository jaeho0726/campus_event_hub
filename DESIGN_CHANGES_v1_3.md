# Campus Event Hub – v1.3 Layout and Notification Decisions

This is a presentation/layout pass on top of v1.2; data storage, ticketing, event validation, and permissions have not been changed.

- The large yellow local-demo banner has been replaced by a quiet caption; **demo identities remain simulated** and the demo launcher must never be used publicly.
- Club portal displays the club name and category/size above the tabs. A user without a club sees only registration and a support-ticket expander. Existing owners see Publish event, My events, Support tickets. Registration of another club is an optional expander.
- Calendar day boundaries now use visible light-blue vertical separators and alternating backgrounds; event source colors are unchanged.
- Time inputs are labeled PT rather than PST, because Pacific Time observes PST in winter and PDT in summer. Actual values continue to represent San Diego local time.
- Student login is still optional for public browsing. `.ics` downloads, browser push, and revised notification preferences are **design ideas, not implemented** in this layout patch.
- A separate existing/new officer login question was deliberately not added: login authenticates the account, and the club management interface is conditional on existing ownership records.

## Run locally

```bash
bash start_demo.sh
```

For a live deployment, disable `MVP_DEMO_MODE`, configure Supabase, apply SQL migrations, and review authentication/RLS. No demo identity grants real-world officer authority.
