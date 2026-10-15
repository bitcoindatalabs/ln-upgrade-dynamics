# Courtesy note to Lightning Labs and CLN maintainers (draft, local only)

Optional heads-up (decision D3, revised 2026-10-15). Send the matching half to each project a few days before upload.

---

**Subject:** Heads-up: measurement paper on Lightning upgrade speed and post-advisory exposure

Hi,

I'm about to post a measurement paper on arXiv about how fast public Lightning nodes upgrade, and how many were
still running affected releases after each public security advisory. It reports no new vulnerabilities. Every
advisory it covers was already public, and it publishes aggregates only, with no lists or labels of individual nodes.

We infer a node's release *line* (not its patch level) from its node_announcement feature bits, using daily gossip
snapshots from May 2023 to 13 October 2026. Checked against CLN developer aliases that state the version, the
inferred line is exact on 98% of node-days.

[LND] Results that concern LND:
- 2026-08-11 batch (fixed in 0.19.0): at disclosure, 14.9% of live LND nodes (6.4% of capacity) were on earlier
  lines. The rate at which they left those lines was the same before and after disclosure (6.9% vs 6.2% per 30
  days). Two months later, 71% of the nodes exposed at disclosure were still on an affected line.
- Across LND and CLN advisories, the fix shipped a median of 256 days before disclosure.
- Half of live LND nodes reach a new line within 72–88 days of its release.

[CLN] Results that concern CLN:
- After the 2026-07-19 disclosures, the rate at which nodes left affected lines rose from 5.8% to 24.0% per 30 days
  (gossipd) and from 8.3% to 20.0% (connectd). Exposure on the gossipd fix fell from 66.6% to 24.2% of live CLN
  nodes by the cutoff, partly through upgrades and partly through nodes going offline.

The paper will be at https://github.com/bitcoindatalabs/ln-upgrade-dynamics, and I'm happy to send the PDF first.
If anything in the framing looks wrong to you, I'd be glad to hear it.

Saurabh Kumar
Bitcoin Data Labs
