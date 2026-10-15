# Literature due diligence: "How fast does the Lightning Network patch?"

Searched 2026-10-14. Sources: WebSearch, plus arXiv (abs pages and export API), publisher pages (Springer, USENIX), Crossref and OpenAlex metadata, and the full-text PDFs where we could fetch them (arXiv, authors' pages). ACM DL, IEEE Xplore and ScienceDirect returned 403 to the fetcher, so for those papers the citation metadata was checked against Crossref (the DOI registry the publisher feeds) and the abstract against OpenAlex. Each entry says how it was verified.

Verification legend:
- **[full text]**: we opened the PDF and read or grepped the relevant passages.
- **[publisher page]**: we opened the publisher or arXiv landing page (title, authors, venue, abstract).
- **[Crossref+abstract]**: Crossref DOI record for the metadata, OpenAlex for the abstract. Publisher page not reachable.
- **[grey]**: blog or industry report, opened directly. Not peer reviewed.
- **[UNVERIFIED]**: seen only in search snippets or news. Do not cite without checking.

## Has anyone measured LN node software versions or upgrade/patch dynamics?

**Partially, and only for implementations.** We found no published work, peer-reviewed or preprint up to 2026-10, that infers the **release line/version** of Lightning nodes, measures **upgrade/patch adoption** in the LN, or quantifies **exposure windows** after LN security advisories. The closest works are:

1. **Zabka, Foerster, Schmid, Decker (ICDCN 2021; extended in Pervasive and Mobile Computing 2022).** They classify nodes by **implementation** (LND / C-Lightning / Eclair, 99.9% of nodes) from default parameters in gossip. They also give the single prior LN "upgrade" observation we found. LND changed its default `cltv_expiry_delta` from 144 to 40 in March 2019, and they report that the new value overtook the old one only around mid-December 2019, so the change took about 9 months to reach most LND nodes. This is a proxy measurement of a default value in channel_updates, not a version inference. Their motivation even names "planning the distribution of critical software updates," but they never measure it.
2. **Espinasa-Vilarrasa, Sanvicente, Pérez-Solà, Herrera-Joancomartí (MDAI 2024, LNCS 14986).** Decision-tree inference of the **implementation** (LND/CLN/Eclair) from gossip traffic or from BOLT #9 **feature bits** in node_announcements, with 87-100% accuracy. This is the nearest methodological neighbour (feature bits as a fingerprint), but it stops at the client family. The landing page and its feature-bit footnote say nothing about versions or releases.
3. **Kim et al., "Measuring Ethereum Network Peers" (IMC 2018).** This is the closest analogue in another blockchain P2P network. It tracks Geth and Parity **version distributions over time**, the age of clients against their release dates, and outdated clients that are still exposed to patched bugs or incompatible with a hard fork. Versions there are self-reported in the handshake, so no inference is needed.

Also relevant: Kappos et al. (FC 2021) state explicitly that their LN gossip snapshots "did not include information about software versions," so they scraped 1ML owner-info fields (370 nodes) to estimate even the implementation mix. Non-academic sources describe LN version risk only qualitatively. Lightning Labs (2019) were "surprised to find many nodes running very old versions" during the CVE-2019-12999 disclosure but published no numbers. The fixes for Bitcoin full nodes are measured in blogs (Lopp 2024) and in Neudecker (2019), and for Ethereum in SRLabs (2019).

---

## A. Lightning Network: implementation inference and measurement

### A1. Implementation / client inference (closest prior work)

**Zabka, P., Foerster, K.-T., Schmid, S., Decker, C. "Node Classification and Geographical Analysis of the Lightning Cryptocurrency Network." ICDCN 2021 (22nd Int. Conf. on Distributed Computing and Networking), ACM, pp. 126-135. doi:10.1145/3427796.3427837.** [full text]
- URL opened: https://schmiste.github.io/icdcn21ln.pdf (author copy). Crossref record checked.
- What they measured: almost two years of gossip (more than 40,000 node_announcements and over 6.4M channel_updates). Implementation is classified from default values (cltv_expiry_delta, fee_base_msat, htlc_minimum_msat, fee_proportional_millionths, colours/aliases), and 99.9% of nodes are classified (about 87% LND). Section 3.1 tracks the LND default `cltv_expiry_delta` change from 144 to 40 (March 2019) and concludes it took about 9 months for the update to reach most LND nodes.
- How we differ: we infer the **release line** (e.g. LND 0.19 vs 0.20), not just the family. We use node_announcement feature bits, which change with releases, rather than channel defaults that operators can override. We validate against self-declared versions and our own node, and we measure adoption per release over 2023-2026 instead of one default change.

**Zabka, P., Foerster, K.-T., Schmid, S., Decker, C. "Empirical evaluation of nodes and channels of the lightning network." Pervasive and Mobile Computing 83 (2022), 101584. doi:10.1016/j.pmcj.2022.101584.** [Crossref+abstract]
- URL: https://doi.org/10.1016/j.pmcj.2022.101584 (ScienceDirect returned 403; abstract via OpenAlex).
- This is the journal extension of the ICDCN paper: the same classification approach (99.9%) plus channel behaviour analyses. Its abstract repeats the motivation that implementation knowledge "can help when planning the distribution of critical software updates."
- How we differ: same as above. They name software-update planning as a motivation, and we are the first to measure it.

**Espinasa-Vilarrasa, P., Sanvicente, S., Pérez-Solà, C., Herrera-Joancomartí, J. "Decision Tree Based Inference of Lightning Network Client Implementations." In Modeling Decisions for Artificial Intelligence (MDAI 2024), LNCS (LNAI) vol. 14986, Springer, pp. 103-114. doi:10.1007/978-3-031-68208-7_9.** [publisher page]
- URL opened: https://link.springer.com/chapter/10.1007/978-3-031-68208-7_9 (full text is paywalled; the UAB repository copy at ddd.uab.cat is behind bot protection).
- What they measured: two decision-tree classifiers, one using gossip traffic and one using announced BOLT #9 features, infer the LND/CLN/Eclair implementation with 87-100% accuracy. Applied to the live network, they find that LND dominates. Footnote 4 lists implementation-specific bits (LND: 0, 9, 12, 31, 2023; Eclair: 39; CLN: 47, 51, 55). Their motivation is that inferring the client is "the first step in many known attacks."
- How we differ: we go one level deeper, from **implementation to release line**, using the fact that feature-bit sets change between releases. We add a validation set of 16,748 self-declared node-days plus ground truth from our own node. They take one or a few snapshots, whereas we run a longitudinal daily panel used for hazard analysis. From the landing page, their work does not address versions, upgrades or patching. **We must cite this and state the difference precisely.** If we can get the full text, we should confirm that it has no version-level results.

**Kappos, G., Yousaf, H., Piotrowska, A., Kanjalkar, S., Delgado-Segura, S., Miller, A., Meiklejohn, S. "An Empirical Analysis of Privacy in the Lightning Network." FC 2021, LNCS, Springer, pp. 167-186. doi:10.1007/978-3-662-64322-8_8. arXiv:2003.12470.** [full text]
- URL opened: https://arxiv.org/abs/2003.12470 (PDF grepped).
- What they measured: privacy attacks on the LN (balance discovery, path inference). For the "software versions" parameter of their simulation, they write that their "collected snapshots did not include information about software versions," so they scraped 1ML Owner Info. That field was empty 91% of the time, leaving 370 nodes: 292 lnd, 54 c-lightning and 24 eclair.
- How we differ: this documents that version and implementation information was missing from gossip-based LN datasets in prior work, and our inference fills that gap.

### A2. LN topology / gossip measurement (cite as background on LN gossip datasets)

**Rohrer, E., Malliaris, J., Tschorsch, F. "Discharged Payment Channels: Quantifying the Lightning Network's Resilience to Topology-Based Attacks." IEEE EuroS&P Workshops (S&B) 2019, pp. 347-356. doi:10.1109/EuroSPW.2019.00045. arXiv:1904.10253.** [publisher page] (arXiv abs + Crossref)
- Shows that the LN graph is small-world and scale-free, and quantifies its resilience to node-removal and channel-exhaustion attacks. It is topology only, with no software dimension.

**Seres, I. A., Gulyás, L., Nagy, D. A., Burcsi, P. "Topological Analysis of Bitcoin's Lightning Network." In Mathematical Research for Blockchain Economy (MARBLE 2019), Springer Proceedings in Business and Economics, 2020, pp. 1-12. doi:10.1007/978-3-030-37110-4_1. arXiv:1901.04972.** [publisher page] (arXiv abs + Crossref)
- Topological robustness of LN snapshots. It is topology only.

**Lin, J.-H., Primicerio, K., Squartini, T., Decker, C., Tessone, C. J. "Lightning network: a second path towards centralisation of the Bitcoin economy." New Journal of Physics 22 (2020), 083022. doi:10.1088/1367-2630/aba062. arXiv:2002.02819.** [publisher page] (arXiv abs + Crossref; note a 2021 corrigendum, doi:10.1088/1367-2630/ac122d)
- Takes daily and weekly snapshots from Jan 2018 to Jul 2019 and finds that wealth is concentrated (Gini about 0.88). The daily-snapshot design is a precedent for ours, but it is about topology and economics, not software.

**Martinazzi, S., Flori, A. "The evolving topology of the Lightning Network: Centralization, efficiency, robustness, synchronization, and anonymity." PLOS ONE 15(1) (2020), e0225966. doi:10.1371/journal.pone.0225966.** [Crossref+abstract]
- Longitudinal topology evolution. It is topology only.

**Romiti, M., Victor, F., Moreno-Sanchez, P., Nordholt, P. S., Haslhofer, B., Maffei, M. "Cross-Layer Deanonymization Methods in the Lightning Protocol." FC 2021, LNCS, Springer, pp. 187-204. doi:10.1007/978-3-662-64322-8_9. arXiv:2007.00764.** [publisher page] (arXiv abs + Crossref)
- Clusters LN nodes by alias and hosting data, and links 45.97% of LN nodes to on-chain addresses. It uses node_announcement metadata (aliases, IPs) but not features or versions.

**Zabka, P., Foerster, K.-T., Decker, C., Schmid, S. "A centrality analysis of the Lightning Network." Telecommunications Policy 48 (2024), 102696. doi:10.1016/j.telpol.2023.102696.** Short version: "Short Paper: A Centrality Analysis of the Lightning Network," FC 2022, LNCS, pp. 374-385, doi:10.1007/978-3-031-18283-9_18; arXiv:2201.07746. [Crossref+abstract] (arXiv abs opened)
- Uses a "TimeMachine" tool to replay gossip and study betweenness centrality over time. This is the precedent for replaying the gossip graph over time, but with no software dimension.

**Casas, P., Romiti, M., Holzer, P., Ben Mariem, S., Donnet, B., Haslhofer, B. "Where is the Light(ning) in the Taproot Dawn? Unveiling the Bitcoin Lightning (IP) Network." IEEE CloudNet 2021, pp. 87-90. doi:10.1109/CloudNet53349.2021.9657121.** [Crossref+abstract]
- A 10-month crawl of LN node IPs: mostly customer networks, and more than 40% of nodes reachable over Tor. It is infrastructure only. It is useful context for our "platform" story (home-node distributions).

**Grötschla, F., Heimbach, L., Richner, S., Wattenhofer, R. "On the Lifecycle of a Lightning Network Payment Channel." arXiv:2409.15930 (2024).** [full text]
- Combines gossip with on-chain data to study channel lifecycles. It does not study software and cites Zabka for implementations. It is relevant as related work on joining gossip with on-chain data.

**Gögge, N., Rohrer, E., Tschorsch, F. "On the Routing Convergence Delay in the Lightning Network." arXiv:2205.12737 (2022).** [publisher page] (arXiv abs)
- Measures gossip propagation and convergence delay, and notes that rate limiting differs between implementations. Relevant to our **announcement lag** metric, because a node_announcement that reflects a new release is subject to gossip delay and staggered broadcast.

**Waugh, F., Holz, R. "An empirical study of availability and reliability properties of the Bitcoin Lightning Network." arXiv:2006.14358 (2020).** [full text]
- Measures payment reachability and node availability. Software versions are not studied. Optional citation.

**Valko, D., Marx Gómez, J.:** "Geolocated Lightning Network topology snapshots: A dataset covering 2019-2023," Scientific Data 12 (2025), doi:10.1038/s41597-025-06413-7 [Crossref]; "Topological and Temporal Stability Analysis of the Lightning Network," arXiv:2512.20641 (2025/2026) [publisher page]; "Shared Channel Capacity and Node Lifetime: An Empirical Study of the Lightning Network," arXiv:2606.20566 (2026) [publisher page].
- These are the most recent (2025-2026) longitudinal LN works. They cover topology, stability and node lifetime, and none of them studies software versions (we checked the abstracts and grepped 2512.20641). Cite them to show that recent longitudinal LN work still ignores software.

**Antonelli, S., Davis, V., Rush, H., Potdevin, A., Shrader, J., Singh, V., Rossi, E. "Predicting Channel Closures in the Lightning Network with Machine Learning." arXiv:2605.12759 (2026), accepted at IEEE BCCA 2026.** [publisher page]
- Uses more than two years of gossip data as ML features for closure prediction, with no version analysis. Optional citation.

### A3. LN security context (attacks whose first step is client identification)

The Espinasa-Vilarrasa paper cites Flood & Loot (Harris & Zohar, arXiv:2006.08513), Congestion Attacks (Mizrahi & Zohar, FC 2021, arXiv:2002.06564), Hijacking Routes (Tochner, Zohar & Schmid, arXiv:1909.06890) and Time-Dilation Attacks (Riard & Naumenko, arXiv:2006.01418). We saw all of them in arXiv API listings but **did not open them for this note**, so check them before citing.

### A4. Grey literature on LN versions (not peer reviewed)

- **Osuntokun, O., Fromknecht, C. "Staying Safe from the Recent Lightning Vulnerability." Lightning Labs blog, 2019-09-27.** [grey] https://blog.lightning.engineering/security/2019/09/27/cve-2019-12999.html. About CVE-2019-12999 (fixed in lnd v0.7.1), they were "surprised to find many nodes running very old versions relative to the age of the software." They give no numbers and no method. This is good motivation for our paper.
- **ekzyis, "lightning-vulns" (GitHub list of LN security advisories).** [UNVERIFIED, search snippet only] https://github.com/ekzyis/lightning-vulns. It may help us assemble the advisory/fix-version table.
- **Core Lightning advisory (Sep/Oct 2026: nodes on 26.06.7 or earlier targeted, fixed in 26.06.8).** [UNVERIFIED, crypto news only] This is a candidate second case study for §3. It must be checked against the primary CLN release notes or advisory.

---

## B. Version and upgrade dynamics in other blockchain P2P networks

**Kim, S. K., Ma, Z., Murali, S., Mason, J., Miller, A., Bailey, M. "Measuring Ethereum Network Peers." IMC 2018, ACM, pp. 91-104. doi:10.1145/3278532.3278542.** [full text]
- URL opened: https://faculty.cc.gatech.edu/~mbailey/publications/imc18_ethereum.pdf
- What they measured: NodeFinder crawls DEVp2p for three months. In §6.2 they show Geth/Parity version distributions over time (Fig. 10) and find 68.3% of Geth nodes more than two releases behind and 3.5% older than v1.7.1, which could not pass the Byzantium fork. In §7.3 they measure client age against release dates: about 75% of Geth and about 50% of Parity clients are less than 3 months old. They recommend automatic updates.
- How we differ: Ethereum clients **self-report** versions in the handshake, while the LN has no version field, so we **infer** it from feature bits and validate the inference. They cover 3 months and we cover 3+ years. We add hazard models, node-size stratification, platform-driven waves and exposure windows tied to specific advisories. **This is the main methodological precedent to cite.**

**Zeisberg, S., Ulitzsch, V. (Security Research Labs). "The blockchain ecosystem has a patch problem." SRLabs blog, 2019-05-17.** [grey] https://srlabs.de/blog/blockchain-patch-gap
- Ethernodes data (about 11,000 nodes, 2019-03-21): about 40% of Parity nodes still vulnerable one month after a crash-bug advisory, about 44% of Geth nodes below the security release v1.8.20, and about 7% of Parity nodes lacking a consensus-critical patch 9 months later. They coin the term "patch gap" for blockchains.
- How we differ: theirs is a single snapshot built on self-reported versions. Ours is longitudinal, uses inferred versions, and is about the LN. Cite it as grey literature because it is the clearest prior statement of the blockchain "patch gap."

**Neudecker, T. "Characterization of the Bitcoin Peer-to-Peer Network (2015-2018)." Karlsruhe Reports in Informatics 2019,1, Karlsruhe Institute of Technology, 2019.** [full text] https://publikationen.bibliothek.kit.edu/1000091933
- Measured version strings of Bitcoin peers from 2016 to 2018 (Fig. 5). New bitcoind versions roll out gradually, with most of the uptake in the first two months, and the paper attributes this to many independent operators each choosing when to upgrade. By contrast, peers running Bitcoin ABC (Bitcoin Cash) rose from 0 to more than 700 **within one day**, which the paper investigates as Sybil-like coordinated behaviour.
- How we differ: Bitcoin versions are self-reported. That single-day jump is a direct precedent for our "771 nodes moved to LND 0.20 on one day" finding. We attribute such jumps to node-platform (app store) pushes and have to separate those from Sybil-style explanations.

**Park, S., Im, S., Seol, Y., Paek, J. "Nodes in the Bitcoin Network: Comparative Measurement Study and Survey." IEEE Access 7 (2019), 57009-57022. doi:10.1109/ACCESS.2019.2914098.** [Crossref+abstract]
- A 37-day scan in 2018 compared with 2013-2016 data. Among other things it covers protocol and client versions. It is a snapshot comparison, not upgrade dynamics.

**Eisenbarth, J.-P., Cholez, T., Perrin, O. "A Comprehensive Study of the Bitcoin P2P Network." BRAINS 2021 (3rd Conf. on Blockchain Research & Applications for Innovative Networks and Services), IEEE, pp. 105-112. doi:10.1109/BRAINS52497.2021.9569782.** [Crossref+abstract] (HAL copy hal-03380595 is behind bot protection)
- The abstract covers the "distribution and security assessment of the clients' versions," as well as churn and Sybil detection. It is the closest Bitcoin analogue to our exposure analysis: it maps versions to known vulnerabilities.
- How we differ: LN instead of Bitcoin, inferred versions, and longitudinal hazard and exposure-window analysis.

**Saad, M., Cook, V., Nguyen, L., Thai, M. T., Mohaisen, A. "Partitioning Attacks on Bitcoin: Colliding Space, Time, and Logic." IEEE ICDCS 2019, pp. 1175-1187. doi:10.1109/ICDCS.2019.00119.** The preprint is "Exploring Spatial, Temporal, and Logical Attacks on the Bitcoin Network," arXiv:1902.03636. [full text of arXiv preprint; ICDCS metadata via Crossref]
- Table II of the preprint lists the top Bitcoin Core versions with their release-date lag and user share (2018). It argues that version diversity ("logical" partitioning) is an attack surface. One snapshot.

**Saad, M., Spaulding, J., Njilla, L., Kamhoua, C., Shetty, S., Nyang, D., Mohaisen, D. "Exploring the Attack Surface of Blockchain: A Comprehensive Survey." IEEE Communications Surveys & Tutorials 22(3) (2020), 1977-2008. doi:10.1109/COMST.2020.2975999.** arXiv:1904.03487. [full text of arXiv version]
- Notes that only about 36% of Bitcoin nodes ran v0.16.0, the release that fixed a DoS bug, so the rest stayed exposed. One snapshot. Optional citation.

**Lopp, J. "When do Bitcoin Node Operators Upgrade?" Blog, 2024-02-04.** [grey] https://blog.lopp.net/when-do-bitcoin-node-operators-upgrade/
- About a decade of weekly Bitnodes user-agent snapshots. The time for 95% of a version's peak nodes to move on was about 1 year before mid-2018 and about 2 years after, and may now be about 3 years. He attributes the slowdown partly to plug-and-play node hardware and Lightning operators. It is grey literature but directly relevant to our "platform-driven upgrades" framing.

**Bitcoin Optech, "CVE-2018-17144" topic page.** [grey] https://bitcoinops.org/en/topics/cve-2018-17144/
- Says only that "an overwhelming majority" of full nodes updated after CVE-2018-17144, with no measurement. The searches turned up **no peer-reviewed measurement of CVE-2018-17144 exposure**.

**Daniel, E., Rohrer, E., Tschorsch, F. "Map-Z: Exposing the Zcash Network in Times of Transition." IEEE LCN 2019, pp. 84-92. doi:10.1109/LCN44214.2019.8990796. arXiv:1907.09755.** [full text]
- Long-term Zcash crawl through the Overwinter and Sapling network upgrades. Fig. 1 shows announced version strings over time, and the paper discusses Zcash's **end-of-support (EoS) halting**, which forces upgrades (clients stop after 16 weeks).
- How we differ: Zcash forces upgrades by built-in expiry, while the LN has none. This makes a useful contrast in the discussion.

**Kiffer, L., Heimbach, L., Trautwein, D., Vonlanthen, Y., Gasser, O. "Multiple Sides of 36 Coins: Measuring Peer-to-Peer Infrastructure Across Cryptocurrencies." arXiv:2511.15388 (2025); per arXiv comment, in Proc. ACM SIGMETRICS 2026.** [full text]
- A 9-month longitudinal crawl of 36 networks, splitting sub-networks by version and client strings. It mentions the LN only as topology-related work and does not study upgrade dynamics. Cite it as the most recent cross-chain P2P measurement and confirm its final venue before submission.

**Kiffer, L., Levin, D., Mislove, A. "Stick a fork in it: Analyzing the Ethereum network partition." ACM HotNets 2017, pp. 94-100. doi:10.1145/3152434.3152449.** [Crossref only] Optional. It analyses the ETH/ETC partition, where client software decides which side a node follows. We have not opened the content.

**Cao, T., Yu, J., Decouchant, J., Luo, X., Verissimo, P. "Exploring the Monero Peer-to-Peer Network." FC 2020, LNCS, pp. 578-594. doi:10.1007/978-3-030-51280-4_31.** [Crossref only] A Monero P2P measurement. We did not verify whether it covers versions. Optional.

**Cortes-Goicoechea, M., Bautista-Gomez, L. "Discovering the Ethereum2 P2P Network." IEEE BCCA 2021, pp. 81-88. doi:10.1109/BCCA53669.2021.9657041. arXiv:2012.14728.** [Crossref+abstract] A crawl of the early beacon chain covering client distribution. Optional citation for post-merge client diversity. Note that consensus-layer client-diversity figures today come mainly from dashboards (clientdiversity.org, Miga Labs), not peer-reviewed papers.

**Not found:** a peer-reviewed longitudinal study of **Ethereum post-merge client version upgrade lag**, or one of **Geth patch adoption after CVE-2021-39137** (the Aug 2021 chain split). Only news and dashboards exist.

---

## C. Classic patch-deployment and vulnerability-lifecycle measurement

**Arbaugh, W. A., Fithen, W. L., McHugh, J. "Windows of Vulnerability: A Case Study Analysis." IEEE Computer 33(12) (2000), 52-59. doi:10.1109/2.889093.** [full text] (author PDF https://www.cs.umd.edu/~waa/pubs/Windows_of_Vulnerability.pdf; note that **Crossref lists the authors in reverse order**, but the printed article has Arbaugh first)
- Proposes the vulnerability life-cycle model (birth, discovery, disclosure, fix, publication, scripting) and shows that hosts stay vulnerable long after fixes ship. Our §3 "exposure window" is this concept, applied to LN releases.

**Rescorla, E. "Security holes... Who cares?" 12th USENIX Security Symposium, 2003.** [publisher page] https://usenix.org/conference/12th-usenix-security-symposium/security-holes-who-cares
- Repeatedly probed servers vulnerable to the OpenSSL bugs of July 2002. More than two-thirds were still vulnerable two weeks after disclosure, and the worm changed the patching pattern. This is the canonical decay curve for patching. Ours is the first such curve for LN nodes.

**Provos, N., Honeyman, P. "ScanSSH: Scanning the Internet for SSH Servers." LISA 2001 (15th Systems Administration Conference), USENIX, pp. 25-30.** [full text] (USENIX HTML)
- Monthly Internet-wide scans of SSH banners. OpenSSH grew from 1.7% to 30% of SSHv2 servers, and the share of vulnerable university SSH servers fell from about 90% to under 20% within two months of notification. This is the classic version-from-banner measurement. We do the same from a non-banner signal (feature bits).

**Frei, S., May, M., Fiedler, U., Plattner, B. "Large-scale vulnerability analysis." SIGCOMM Workshop on Large-Scale Attack Defense (LSAD) 2006, ACM, pp. 131-138. doi:10.1145/1162666.1162671.** [Crossref+abstract]
- Studies 80,000+ advisories and quantifies the gap between exploit availability and patch availability. It covers vendor-side lifecycle, not deployment.

**Frei, S., Duebendorfer, T., Plattner, B. "Firefox (In)security update dynamics exposed." ACM SIGCOMM Computer Communication Review 39(1) (2009), 16-22. doi:10.1145/1496091.1496094.** [Crossref+abstract]
- Measures browser patch levels from Google's User-Agent logs over more than a year. The patch level is set mainly by the auto-update design: most Firefox users updated within 3 days, yet the latest version's share never exceeded 80%. This is the closest classic analogue to our **platform-driven waves**: the distribution channel's update ergonomics (Umbrel, Start9 and similar app stores) dominate operator behaviour.

**Nappa, A., Johnson, R., Bilge, L., Caballero, J., Dumitras, T. "The Attack of the Clones: A Study of the Impact of Shared Code on Vulnerability Patching." IEEE S&P 2015, pp. 692-708. doi:10.1109/SP.2015.48.** [full text] (https://www.umiacs.umd.edu/~tdumitra/papers/OAKLAND-2015.pdf)
- Covers 5 years and 8.4M hosts (Symantec WINE), with patch deployment for 1,593 vulnerabilities across 10 client applications. It uses **survival analysis** (Kaplan-Meier style) to model time to patch. This is our methodological template for upgrade hazard curves.

**Durumeric, Z., Li, F., Kasten, J., Amann, J., Beekman, J., Payer, M., Weaver, N., Adrian, D., Paxson, V., Bailey, M., Halderman, J. A. "The Matter of Heartbleed." IMC 2014, ACM, pp. 475-488. doi:10.1145/2663716.2663755.** [full text] (https://jhalderm.com/pub/papers/heartbleed-imc14.pdf)
- Tracks the vulnerable population and patching over time after Heartbleed, and runs a notification experiment (150k hosts, about 50% more patching). It is the reference design for measuring exposure after disclosure.

**Zhang, L., Choffnes, D., Levin, D., Dumitras, T., Mislove, A., Schulman, A., Wilson, C. "Analysis of SSL Certificate Reissues and Revocations in the Wake of Heartbleed." IMC 2014, ACM, pp. 489-502. doi:10.1145/2663716.2663758.** [Crossref only] (CACM version 2018, doi:10.1145/3176244) Optional. It covers the slow remediation tail: certificates that were not reissued or revoked.

**Li, F., Paxson, V. "A Large-Scale Empirical Study of Security Patches." ACM CCS 2017, pp. 2201-2215. doi:10.1145/3133956.3134072.** [full text]
- Studies **patch development** (4,000+ fixes, 3,000+ CVEs, 682 projects): vulnerability lifetimes in code and the timeliness of fixes. Note that this is the upstream half of the lifecycle. We measure the downstream half (deployment), so cite it as complementary.

**Li, F., Durumeric, Z., Czyz, J., Karami, M., Bailey, M., McCoy, D., Savage, S., Paxson, V. "You've Got Vulnerability: Exploring Effective Vulnerability Notifications." 25th USENIX Security Symposium, 2016, pp. 1033-1050.** [publisher page]
- Notification experiments: most contacts never act, and fixes are partial. Relevant if we discuss whether LN advisories reach operators.

**Kotzias, P., Bilge, L., Vervier, P.-A., Caballero, J. "Mind Your Own Business: A Longitudinal Study of Threats and Vulnerabilities in Enterprises." NDSS 2019. doi:10.14722/ndss.2019.23522.** [Crossref+abstract]
- 3 years, 28K enterprises: a longitudinal analysis of patching behaviour. It supports the claim that patching is slow even where professional administrators run the machines.

**Sarabi, A., Zhu, Z., Xiao, C., Liu, M., Dumitras, T. "Patch Me If You Can: A Study on the Effects of Individual User Behavior on the End-Host Vulnerability State." PAM 2017, LNCS vol. 10176, Springer, pp. 113-125. doi:10.1007/978-3-319-54328-4_9.** [publisher page]
- Covers more than 400k Windows hosts. Users' promptness in patching matters, but less than disclosure frequency and vendor patch speed. Relevant to splitting LN exposure between release cadence and operator behaviour.

**Bilge, L., Dumitras, T. "Before We Knew It: An Empirical Study of Zero-Day Attacks in the Real World." ACM CCS 2012, pp. 833-844. doi:10.1145/2382196.2382284.** [Crossref+abstract] Optional. Covers the pre-disclosure part of the window.

**Li, F., Rogers, L., Mathur, A., Malkin, N., Chetty, M. "Keepers of the Machines: Examining How System Administrators Manage Software Updates For Multiple Machines." SOUPS 2019, USENIX, pp. 273-288.** [publisher page]
- Survey (102) and interviews (17) of system administrators about how they handle updates. Relevant if we discuss why large routing nodes upgrade differently (our by-node-size analysis).

**Ozment, A., Schechter, S. E. "Milk or Wine: Does Software Security Improve with Age?" 15th USENIX Security Symposium, 2006.** [publisher page] Optional. Vulnerability lifetimes in OpenBSD (median 2.6 years or more). It is about code-side lifetimes, not deployment.

**Zerouali, A., Constantinou, E., Mens, T., Robles, G., González-Barahona, J. "An Empirical Analysis of Technical Lag in npm Package Dependencies." ICSR 2018 (New Opportunities for Software Reuse), LNCS, Springer, pp. 95-110. doi:10.1007/978-3-319-90421-4_6.** [Crossref only] Optional. Defines the "technical lag" concept, which we could use when we define how far a node lags behind the latest release line.

**Survival-analysis methodology:**
- Kaplan, E. L., Meier, P. "Nonparametric Estimation from Incomplete Observations." JASA 53(282) (1958), 457-481. doi:10.1080/01621459.1958.10501452. [Crossref]
- Cox, D. R. "Regression Models and Life-Tables." JRSS-B 34(2) (1972), 187-202. doi:10.1111/j.2517-6161.1972.tb00899.x. [Crossref] (Crossref gives pages 187-202; the paper with its discussion runs to 220.)

**Not found / not pursued:** a canonical "Debian OpenSSH version from banners" longitudinal paper beyond ScanSSH. IoT firmware update measurement (we found only an unverified ResearchGate item, "A Large-Scale Analysis of IoT Firmware Version Distribution in the Wild," and arXiv:2209.09855 "Towards Characterizing IoT Software Update Practices," neither opened). Add these only after checking them.

---

## Positioning

Prior LN measurement either stops at the **implementation family** (Zabka et al. 2021/2022 from channel defaults; Espinasa-Vilarrasa et al. 2024 from feature bits) or treats the network as a graph with no software at all (topology, centrality, privacy and lifecycle studies through 2026). Prior work on blockchain versions (Kim et al. 2018 for Ethereum; Neudecker 2019 and Eisenbarth et al. 2021 for Bitcoin; Map-Z 2019 for Zcash) depends on **self-reported** version strings that the LN does not carry. Classic patch studies (Rescorla, Heartbleed, Nappa et al.) measure servers and end hosts, not payment-channel nodes. We are the first to (i) infer the **release line** of every public LN node from node_announcement feature bits, with an explicit validation set; (ii) estimate **upgrade hazards** per client and node size over a multi-year daily panel, including platform-driven single-day waves (cf. Neudecker's one-day Bitcoin ABC jump and Frei et al.'s auto-update effect) and pre-release builds; and (iii) turn advisories whose fix boundary is a release line into measured **exposure windows** (Arbaugh et al.'s windows of vulnerability) for a financial P2P network where unpatched nodes put channel funds at risk.

---

## BibTeX (verified entries only)

Every entry below was checked against the publisher or arXiv page, the full text, or the Crossref DOI record, as marked above. Grey-literature entries use `@misc`. Unverified items are excluded.

```bibtex
@inproceedings{zabka2021nodeclassification,
  author    = {Zabka, Philipp and Foerster, Klaus-Tycho and Schmid, Stefan and Decker, Christian},
  title     = {Node Classification and Geographical Analysis of the Lightning Cryptocurrency Network},
  booktitle = {Proceedings of the 22nd International Conference on Distributed Computing and Networking (ICDCN)},
  pages     = {126--135},
  publisher = {ACM},
  year      = {2021},
  doi       = {10.1145/3427796.3427837}
}

@article{zabka2022empirical,
  author  = {Zabka, Philipp and Foerster, Klaus-Tycho and Schmid, Stefan and Decker, Christian},
  title   = {Empirical evaluation of nodes and channels of the lightning network},
  journal = {Pervasive and Mobile Computing},
  volume  = {83},
  pages   = {101584},
  year    = {2022},
  doi     = {10.1016/j.pmcj.2022.101584}
}

@inproceedings{espinasa2024decisiontree,
  author    = {Espinasa-Vilarrasa, Pol and Sanvicente, S{\'i}lvia and P{\'e}rez-Sol{\`a}, Cristina and Herrera-Joancomart{\'i}, Jordi},
  title     = {Decision Tree Based Inference of Lightning Network Client Implementations},
  booktitle = {Modeling Decisions for Artificial Intelligence (MDAI 2024)},
  series    = {Lecture Notes in Computer Science},
  volume    = {14986},
  pages     = {103--114},
  publisher = {Springer},
  year      = {2024},
  doi       = {10.1007/978-3-031-68208-7_9}
}

@inproceedings{kappos2021privacy,
  author    = {Kappos, George and Yousaf, Haaroon and Piotrowska, Ania and Kanjalkar, Sanket and Delgado-Segura, Sergi and Miller, Andrew and Meiklejohn, Sarah},
  title     = {An Empirical Analysis of Privacy in the Lightning Network},
  booktitle = {Financial Cryptography and Data Security (FC 2021)},
  series    = {Lecture Notes in Computer Science},
  pages     = {167--186},
  publisher = {Springer},
  year      = {2021},
  doi       = {10.1007/978-3-662-64322-8_8}
}

@inproceedings{romiti2021crosslayer,
  author    = {Romiti, Matteo and Victor, Friedhelm and Moreno-Sanchez, Pedro and Nordholt, Peter Sebastian and Haslhofer, Bernhard and Maffei, Matteo},
  title     = {Cross-Layer Deanonymization Methods in the Lightning Protocol},
  booktitle = {Financial Cryptography and Data Security (FC 2021)},
  series    = {Lecture Notes in Computer Science},
  pages     = {187--204},
  publisher = {Springer},
  year      = {2021},
  doi       = {10.1007/978-3-662-64322-8_9}
}

@inproceedings{rohrer2019discharged,
  author    = {Rohrer, Elias and Malliaris, Julian and Tschorsch, Florian},
  title     = {Discharged Payment Channels: Quantifying the Lightning Network's Resilience to Topology-Based Attacks},
  booktitle = {2019 IEEE European Symposium on Security and Privacy Workshops (EuroS\&PW)},
  pages     = {347--356},
  publisher = {IEEE},
  year      = {2019},
  doi       = {10.1109/EuroSPW.2019.00045}
}

@inproceedings{seres2020topological,
  author    = {Seres, Istv{\'a}n Andr{\'a}s and Guly{\'a}s, L{\'a}szl{\'o} and Nagy, D{\'a}niel A. and Burcsi, P{\'e}ter},
  title     = {Topological Analysis of Bitcoin's Lightning Network},
  booktitle = {Mathematical Research for Blockchain Economy (MARBLE 2019)},
  series    = {Springer Proceedings in Business and Economics},
  pages     = {1--12},
  publisher = {Springer},
  year      = {2020},
  doi       = {10.1007/978-3-030-37110-4_1}
}

@article{lin2020secondpath,
  author  = {Lin, Jian-Hong and Primicerio, Kevin and Squartini, Tiziano and Decker, Christian and Tessone, Claudio J.},
  title   = {Lightning network: a second path towards centralisation of the {Bitcoin} economy},
  journal = {New Journal of Physics},
  volume  = {22},
  pages   = {083022},
  year    = {2020},
  doi     = {10.1088/1367-2630/aba062}
}

@article{martinazzi2020evolving,
  author  = {Martinazzi, Stefano and Flori, Andrea},
  title   = {The evolving topology of the {Lightning Network}: Centralization, efficiency, robustness, synchronization, and anonymity},
  journal = {PLOS ONE},
  volume  = {15},
  number  = {1},
  pages   = {e0225966},
  year    = {2020},
  doi     = {10.1371/journal.pone.0225966}
}

@article{zabka2024centrality,
  author  = {Zabka, Philipp and Foerster, Klaus-Tycho and Decker, Christian and Schmid, Stefan},
  title   = {A centrality analysis of the {Lightning Network}},
  journal = {Telecommunications Policy},
  volume  = {48},
  pages   = {102696},
  year    = {2024},
  doi     = {10.1016/j.telpol.2023.102696}
}

@inproceedings{casas2021taproot,
  author    = {Casas, Pedro and Romiti, Matteo and Holzer, Peter and Ben Mariem, Sami and Donnet, Benoit and Haslhofer, Bernhard},
  title     = {Where is the Light(ning) in the Taproot Dawn? {U}nveiling the {Bitcoin} {Lightning} ({IP}) Network},
  booktitle = {2021 IEEE 10th International Conference on Cloud Networking (CloudNet)},
  pages     = {87--90},
  publisher = {IEEE},
  year      = {2021},
  doi       = {10.1109/CloudNet53349.2021.9657121}
}

@misc{grotschla2024lifecycle,
  author        = {Gr{\"o}tschla, Florian and Heimbach, Lioba and Richner, Severin and Wattenhofer, Roger},
  title         = {On the Lifecycle of a Lightning Network Payment Channel},
  year          = {2024},
  eprint        = {2409.15930},
  archivePrefix = {arXiv}
}

@misc{gogge2022convergence,
  author        = {G{\"o}gge, Niklas and Rohrer, Elias and Tschorsch, Florian},
  title         = {On the Routing Convergence Delay in the Lightning Network},
  year          = {2022},
  eprint        = {2205.12737},
  archivePrefix = {arXiv}
}

@misc{waugh2020availability,
  author        = {Waugh, Finnegan and Holz, Ralph},
  title         = {An empirical study of availability and reliability properties of the {Bitcoin} {Lightning} Network},
  year          = {2020},
  eprint        = {2006.14358},
  archivePrefix = {arXiv}
}

@article{valko2025geolocated,
  author  = {Valko, Danila and Marx G{\'o}mez, Jorge},
  title   = {Geolocated {Lightning Network} topology snapshots: A dataset covering 2019--2023},
  journal = {Scientific Data},
  volume  = {12},
  year    = {2025},
  doi     = {10.1038/s41597-025-06413-7}
}

@misc{valko2025stability,
  author        = {Valko, Danila and Marx G{\'o}mez, Jorge},
  title         = {Topological and Temporal Stability Analysis of the {Lightning Network}},
  year          = {2025},
  eprint        = {2512.20641},
  archivePrefix = {arXiv},
  primaryClass  = {cs.SI}
}

@misc{valko2026lifetime,
  author        = {Valko, Danila and Marx G{\'o}mez, Jorge},
  title         = {Shared Channel Capacity and Node Lifetime: An Empirical Study of the {Lightning Network}},
  year          = {2026},
  eprint        = {2606.20566},
  archivePrefix = {arXiv},
  primaryClass  = {cs.NI}
}

@misc{antonelli2026closures,
  author        = {Antonelli, Simone and Davis, Vincent and Rush, Harrison and Potdevin, Anthony and Shrader, Jesse and Singh, Vikash and Rossi, Emanuele},
  title         = {Predicting Channel Closures in the {Lightning Network} with Machine Learning},
  year          = {2026},
  eprint        = {2605.12759},
  archivePrefix = {arXiv},
  note          = {Accepted at IEEE BCCA 2026}
}

@misc{lightninglabs2019cve,
  author       = {Osuntokun, Olaoluwa and Fromknecht, Conner},
  title        = {Staying Safe from the Recent Lightning Vulnerability},
  howpublished = {Lightning Labs blog},
  year         = {2019},
  month        = sep,
  note         = {\url{https://blog.lightning.engineering/security/2019/09/27/cve-2019-12999.html}}
}

@inproceedings{kim2018ethereum,
  author    = {Kim, Seoung Kyun and Ma, Zane and Murali, Siddharth and Mason, Joshua and Miller, Andrew and Bailey, Michael},
  title     = {Measuring {Ethereum} Network Peers},
  booktitle = {Proceedings of the Internet Measurement Conference (IMC 2018)},
  pages     = {91--104},
  publisher = {ACM},
  year      = {2018},
  doi       = {10.1145/3278532.3278542}
}

@misc{srlabs2019patchgap,
  author       = {Zeisberg, Stephan and Ulitzsch, Vincent},
  title        = {The blockchain ecosystem has a patch problem},
  howpublished = {Security Research Labs blog},
  year         = {2019},
  month        = may,
  note         = {\url{https://srlabs.de/blog/blockchain-patch-gap}}
}

@techreport{neudecker2019characterization,
  author      = {Neudecker, Till},
  title       = {Characterization of the {Bitcoin} Peer-to-Peer Network (2015--2018)},
  institution = {Karlsruhe Institute of Technology},
  type        = {Karlsruhe Reports in Informatics},
  number      = {2019,1},
  year        = {2019},
  url         = {https://publikationen.bibliothek.kit.edu/1000091933}
}

@article{park2019bitcoinnodes,
  author  = {Park, Sehyun and Im, Seongwon and Seol, Youhwan and Paek, Jeongyeup},
  title   = {Nodes in the {Bitcoin} Network: Comparative Measurement Study and Survey},
  journal = {IEEE Access},
  volume  = {7},
  pages   = {57009--57022},
  year    = {2019},
  doi     = {10.1109/ACCESS.2019.2914098}
}

@inproceedings{eisenbarth2021bitcoin,
  author    = {Eisenbarth, Jean-Philippe and Cholez, Thibault and Perrin, Olivier},
  title     = {A Comprehensive Study of the {Bitcoin} {P2P} Network},
  booktitle = {2021 3rd Conference on Blockchain Research \& Applications for Innovative Networks and Services (BRAINS)},
  pages     = {105--112},
  publisher = {IEEE},
  year      = {2021},
  doi       = {10.1109/BRAINS52497.2021.9569782}
}

@inproceedings{saad2019partitioning,
  author    = {Saad, Muhammad and Cook, Victor and Nguyen, Lan and Thai, My T. and Mohaisen, Aziz},
  title     = {Partitioning Attacks on {Bitcoin}: Colliding Space, Time, and Logic},
  booktitle = {2019 IEEE 39th International Conference on Distributed Computing Systems (ICDCS)},
  pages     = {1175--1187},
  publisher = {IEEE},
  year      = {2019},
  doi       = {10.1109/ICDCS.2019.00119}
}

@article{saad2020attacksurface,
  author  = {Saad, Muhammad and Spaulding, Jeffrey and Njilla, Laurent and Kamhoua, Charles and Shetty, Sachin and Nyang, DaeHun and Mohaisen, David},
  title   = {Exploring the Attack Surface of Blockchain: A Comprehensive Survey},
  journal = {IEEE Communications Surveys \& Tutorials},
  volume  = {22},
  number  = {3},
  pages   = {1977--2008},
  year    = {2020},
  doi     = {10.1109/COMST.2020.2975999}
}

@misc{lopp2024upgrade,
  author       = {Lopp, Jameson},
  title        = {When do {Bitcoin} Node Operators Upgrade?},
  howpublished = {Blog post},
  year         = {2024},
  month        = feb,
  note         = {\url{https://blog.lopp.net/when-do-bitcoin-node-operators-upgrade/}}
}

@inproceedings{daniel2019mapz,
  author    = {Daniel, Erik and Rohrer, Elias and Tschorsch, Florian},
  title     = {Map-{Z}: Exposing the {Zcash} Network in Times of Transition},
  booktitle = {2019 IEEE 44th Conference on Local Computer Networks (LCN)},
  pages     = {84--92},
  publisher = {IEEE},
  year      = {2019},
  doi       = {10.1109/LCN44214.2019.8990796}
}

@misc{kiffer2025coins,
  author        = {Kiffer, Lucianna and Heimbach, Lioba and Trautwein, Dennis and Vonlanthen, Yann and Gasser, Oliver},
  title         = {Multiple Sides of 36 Coins: Measuring Peer-to-Peer Infrastructure Across Cryptocurrencies},
  year          = {2025},
  eprint        = {2511.15388},
  archivePrefix = {arXiv},
  note          = {To appear in Proc. ACM SIGMETRICS 2026 (per arXiv comment)}
}

@inproceedings{kiffer2017fork,
  author    = {Kiffer, Lucianna and Levin, Dave and Mislove, Alan},
  title     = {Stick a fork in it: Analyzing the {Ethereum} network partition},
  booktitle = {Proceedings of the 16th ACM Workshop on Hot Topics in Networks (HotNets)},
  pages     = {94--100},
  publisher = {ACM},
  year      = {2017},
  doi       = {10.1145/3152434.3152449}
}

@inproceedings{cao2020monero,
  author    = {Cao, Tong and Yu, Jiangshan and Decouchant, J{\'e}r{\'e}mie and Luo, Xiapu and Verissimo, Paulo},
  title     = {Exploring the {Monero} Peer-to-Peer Network},
  booktitle = {Financial Cryptography and Data Security (FC 2020)},
  series    = {Lecture Notes in Computer Science},
  pages     = {578--594},
  publisher = {Springer},
  year      = {2020},
  doi       = {10.1007/978-3-030-51280-4_31}
}

@inproceedings{cortes2021eth2,
  author    = {Cortes-Goicoechea, Mikel and Bautista-Gomez, Leonardo},
  title     = {Discovering the {Ethereum2} {P2P} Network},
  booktitle = {2021 Third International Conference on Blockchain Computing and Applications (BCCA)},
  pages     = {81--88},
  publisher = {IEEE},
  year      = {2021},
  doi       = {10.1109/BCCA53669.2021.9657041}
}

@article{arbaugh2000windows,
  author  = {Arbaugh, William A. and Fithen, William L. and McHugh, John},
  title   = {Windows of Vulnerability: A Case Study Analysis},
  journal = {IEEE Computer},
  volume  = {33},
  number  = {12},
  pages   = {52--59},
  year    = {2000},
  doi     = {10.1109/2.889093}
}

@inproceedings{rescorla2003securityholes,
  author    = {Rescorla, Eric},
  title     = {Security Holes\ldots{} Who Cares?},
  booktitle = {Proceedings of the 12th USENIX Security Symposium},
  publisher = {USENIX Association},
  year      = {2003}
}

@inproceedings{provos2001scanssh,
  author    = {Provos, Niels and Honeyman, Peter},
  title     = {{ScanSSH}: Scanning the {Internet} for {SSH} Servers},
  booktitle = {Proceedings of the 15th Systems Administration Conference (LISA 2001)},
  pages     = {25--30},
  publisher = {USENIX Association},
  year      = {2001}
}

@inproceedings{frei2006largescale,
  author    = {Frei, Stefan and May, Martin and Fiedler, Ulrich and Plattner, Bernhard},
  title     = {Large-scale vulnerability analysis},
  booktitle = {Proceedings of the 2006 SIGCOMM Workshop on Large-Scale Attack Defense (LSAD)},
  pages     = {131--138},
  publisher = {ACM},
  year      = {2006},
  doi       = {10.1145/1162666.1162671}
}

@article{frei2009firefox,
  author  = {Frei, Stefan and Duebendorfer, Thomas and Plattner, Bernhard},
  title   = {Firefox (In)security update dynamics exposed},
  journal = {ACM SIGCOMM Computer Communication Review},
  volume  = {39},
  number  = {1},
  pages   = {16--22},
  year    = {2009},
  doi     = {10.1145/1496091.1496094}
}

@inproceedings{nappa2015clones,
  author    = {Nappa, Antonio and Johnson, Richard and Bilge, Leyla and Caballero, Juan and Dumitras, Tudor},
  title     = {The Attack of the Clones: A Study of the Impact of Shared Code on Vulnerability Patching},
  booktitle = {2015 IEEE Symposium on Security and Privacy (S\&P)},
  pages     = {692--708},
  publisher = {IEEE},
  year      = {2015},
  doi       = {10.1109/SP.2015.48}
}

@inproceedings{durumeric2014heartbleed,
  author    = {Durumeric, Zakir and Li, Frank and Kasten, James and Amann, Johanna and Beekman, Jethro and Payer, Mathias and Weaver, Nicolas and Adrian, David and Paxson, Vern and Bailey, Michael and Halderman, J. Alex},
  title     = {The Matter of {Heartbleed}},
  booktitle = {Proceedings of the 2014 Internet Measurement Conference (IMC)},
  pages     = {475--488},
  publisher = {ACM},
  year      = {2014},
  doi       = {10.1145/2663716.2663755}
}

@inproceedings{zhang2014heartbleedcerts,
  author    = {Zhang, Liang and Choffnes, David and Levin, Dave and Dumitras, Tudor and Mislove, Alan and Schulman, Aaron and Wilson, Christo},
  title     = {Analysis of {SSL} Certificate Reissues and Revocations in the Wake of {Heartbleed}},
  booktitle = {Proceedings of the 2014 Internet Measurement Conference (IMC)},
  pages     = {489--502},
  publisher = {ACM},
  year      = {2014},
  doi       = {10.1145/2663716.2663758}
}

@inproceedings{li2017patches,
  author    = {Li, Frank and Paxson, Vern},
  title     = {A Large-Scale Empirical Study of Security Patches},
  booktitle = {Proceedings of the 2017 ACM SIGSAC Conference on Computer and Communications Security (CCS)},
  pages     = {2201--2215},
  publisher = {ACM},
  year      = {2017},
  doi       = {10.1145/3133956.3134072}
}

@inproceedings{li2016notifications,
  author    = {Li, Frank and Durumeric, Zakir and Czyz, Jakub and Karami, Mohammad and Bailey, Michael and McCoy, Damon and Savage, Stefan and Paxson, Vern},
  title     = {You've Got Vulnerability: Exploring Effective Vulnerability Notifications},
  booktitle = {25th USENIX Security Symposium},
  pages     = {1033--1050},
  publisher = {USENIX Association},
  year      = {2016}
}

@inproceedings{kotzias2019enterprises,
  author    = {Kotzias, Platon and Bilge, Leyla and Vervier, Pierre-Antoine and Caballero, Juan},
  title     = {Mind Your Own Business: A Longitudinal Study of Threats and Vulnerabilities in Enterprises},
  booktitle = {Network and Distributed System Security Symposium (NDSS)},
  year      = {2019},
  doi       = {10.14722/ndss.2019.23522}
}

@inproceedings{sarabi2017patchme,
  author    = {Sarabi, Armin and Zhu, Ziyun and Xiao, Chaowei and Liu, Mingyan and Dumitra{\c{s}}, Tudor},
  title     = {Patch Me If You Can: A Study on the Effects of Individual User Behavior on the End-Host Vulnerability State},
  booktitle = {Passive and Active Measurement (PAM 2017)},
  series    = {Lecture Notes in Computer Science},
  volume    = {10176},
  pages     = {113--125},
  publisher = {Springer},
  year      = {2017},
  doi       = {10.1007/978-3-319-54328-4_9}
}

@inproceedings{bilge2012zeroday,
  author    = {Bilge, Leyla and Dumitra{\c{s}}, Tudor},
  title     = {Before We Knew It: An Empirical Study of Zero-Day Attacks in the Real World},
  booktitle = {Proceedings of the 2012 ACM Conference on Computer and Communications Security (CCS)},
  pages     = {833--844},
  publisher = {ACM},
  year      = {2012},
  doi       = {10.1145/2382196.2382284}
}

@inproceedings{li2019keepers,
  author    = {Li, Frank and Rogers, Lisa and Mathur, Arunesh and Malkin, Nathan and Chetty, Marshini},
  title     = {Keepers of the Machines: Examining How System Administrators Manage Software Updates For Multiple Machines},
  booktitle = {Fifteenth Symposium on Usable Privacy and Security (SOUPS 2019)},
  pages     = {273--288},
  publisher = {USENIX Association},
  year      = {2019}
}

@inproceedings{ozment2006milk,
  author    = {Ozment, Andy and Schechter, Stuart E.},
  title     = {Milk or Wine: Does Software Security Improve with Age?},
  booktitle = {15th USENIX Security Symposium},
  publisher = {USENIX Association},
  year      = {2006}
}

@inproceedings{zerouali2018techlag,
  author    = {Zerouali, Ahmed and Constantinou, Eleni and Mens, Tom and Robles, Gregorio and Gonz{\'a}lez-Barahona, Jes{\'u}s},
  title     = {An Empirical Analysis of Technical Lag in npm Package Dependencies},
  booktitle = {New Opportunities for Software Reuse (ICSR 2018)},
  series    = {Lecture Notes in Computer Science},
  pages     = {95--110},
  publisher = {Springer},
  year      = {2018},
  doi       = {10.1007/978-3-319-90421-4_6}
}

@article{kaplan1958km,
  author  = {Kaplan, E. L. and Meier, Paul},
  title   = {Nonparametric Estimation from Incomplete Observations},
  journal = {Journal of the American Statistical Association},
  volume  = {53},
  number  = {282},
  pages   = {457--481},
  year    = {1958},
  doi     = {10.1080/01621459.1958.10501452}
}

@article{cox1972regression,
  author  = {Cox, D. R.},
  title   = {Regression Models and Life-Tables},
  journal = {Journal of the Royal Statistical Society: Series B (Methodological)},
  volume  = {34},
  number  = {2},
  pages   = {187--202},
  year    = {1972},
  doi     = {10.1111/j.2517-6161.1972.tb00899.x}
}
```

### Open items before submission
- Get the full text of Espinasa-Vilarrasa et al. (2024) and Zabka et al. (PMC 2022) to confirm that neither reports version-level results. The landing pages and abstracts suggest they do not.
- Confirm the final venue, volume and pages for Kiffer et al. (SIGMETRICS 2026 / POMACS) and Antonelli et al. (BCCA 2026).
- FC 2021 LNCS volume numbers for Kappos and Romiti were not checked, so they are left out of the BibTeX.
- Check the primary sources for the 2026 Core Lightning advisory and for the Lightning Labs 2026-08-11 LND advisories (our case studies). They are not literature, but they must be cited from primary pages.
- Open and verify the LN attack papers (Flood & Loot, Congestion Attacks, Hijacking Routes, Time-Dilation) if we cite them in the motivation.
