"""
platforms.py — dated releases of node platforms that ship LND or Core Lightning to their users.

A platform release puts a new implementation version in front of every node that runs on the platform, so upgrades
that follow it are the platform's schedule, not each operator's. Two platforms can be dated to the minute from
public records:

  Umbrel   its app store is a git repository (github.com/getumbrel/umbrel-apps); a device sees a new app version
           once the pull request that changes `version:` in lightning/umbrel-app.yml (LND) or
           core-lightning/umbrel-app.yml (CLN) is merged. `utc` = the merge time of that pull request (or of the
           direct commit). Every version change from 2024 to the cutoff is listed, including Umbrel packaging
           patches ("-patch.N"), since each makes devices pull the app again.
  BTCPay   a BTCPay Server deployment updates only when its operator runs the update, which installs the LND or CLN
           version pinned in github.com/btcpayserver/btcpayserver-docker at that moment; routine version bumps
           therefore reach nodes over weeks and are not listed. The 2.4.2 security release (exploited Greenfield API
           bug) asked every operator to update at once; `utc` = its GitHub release publication. An update after it
           installed LND 0.21.0 (0.21.1 from PR #1073, merged 20:59 UTC the same day; both line 0.21) or CLN 26.06.1
           (pinned since 15 July 2026).

Other platforms (Start9, RaspiBlitz, myNode, hosted services) publish packages through registries or images
whose availability date we cannot establish; they are not listed.

`line` is the release-line label (ln_release_features.json) of the version shipped.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd


@dataclass(frozen=True)
class PlatformRelease:
    platform: str
    client: str
    utc: str          # ISO 8601, UTC
    version: str      # implementation version shipped
    line: str         # release-line label of that version
    source: str       # commit or release URL
    note: str = ""

    @property
    def ts(self) -> pd.Timestamp:
        return pd.Timestamp(self.utc.replace("Z", ""))


_U = "https://github.com/getumbrel/umbrel-apps/commit/"
L, C = "LND", "CLN"

PLATFORM_RELEASES: List[PlatformRelease] = [
    # --- Umbrel, Lightning Node app (LND) -----------------------------------------------------------------------
    PlatformRelease("Umbrel", L, "2024-02-15T18:39:56Z", "0.17.4", "0.15.1–0.17", _U + "b7ae6f5d9beb"),
    PlatformRelease("Umbrel", L, "2024-05-02T08:32:56Z", "0.17.5", "0.15.1–0.17", _U + "4e7f2ea00f85"),
    PlatformRelease("Umbrel", L, "2024-06-17T04:14:19Z", "0.18.0", "0.18", _U + "16676fc51046", "PR #1159"),
    PlatformRelease("Umbrel", L, "2024-10-29T23:58:42Z", "0.18.3", "0.18", _U + "20a9f0db940f"),
    PlatformRelease("Umbrel", L, "2025-02-19T00:44:49Z", "0.18.5", "0.18", _U + "44b598944942"),
    PlatformRelease("Umbrel", L, "2025-07-02T01:33:40Z", "0.19.1", "0.19", _U + "dbcb052f802d", "PR #3119"),
    PlatformRelease("Umbrel", L, "2025-07-28T23:51:05Z", "0.19.2", "0.19", _U + "88448101f1c5", "PR #3283"),
    PlatformRelease("Umbrel", L, "2025-09-30T00:12:07Z", "0.19.3", "0.19", _U + "b592e700a091", "PR #3700"),
    PlatformRelease("Umbrel", L, "2025-12-09T01:49:40Z", "0.20.0", "0.20", _U + "d36a08d54679", "PR #4198"),
    PlatformRelease("Umbrel", L, "2026-05-01T03:51:30Z", "0.20.1", "0.20", _U + "b742905485d9", "PR #5526"),
    PlatformRelease("Umbrel", L, "2026-06-26T23:03:33Z", "0.21.1", "0.21", _U + "c94779142fff", "PR #5766"),
    PlatformRelease("Umbrel", L, "2026-07-14T03:50:53Z", "0.21.1", "0.21", _U + "c3ef5634c137", "packaging patch.2"),
    PlatformRelease("Umbrel", L, "2026-08-17T03:49:11Z", "0.21.2", "0.21", _U + "13af6be96d20"),
    PlatformRelease("Umbrel", L, "2026-09-04T01:34:31Z", "0.21.3", "0.21", _U + "0a710562943b"),
    PlatformRelease("Umbrel", L, "2026-10-12T03:17:03Z", "0.21.4", "0.21", _U + "fc53c0c6b6eb"),
    # --- BTCPay Server security release: updating installs the pinned LND or CLN --------------------------------------
    PlatformRelease("BTCPay", L, "2026-08-07T15:31:16Z", "0.21.1", "0.21",
                    "https://github.com/btcpayserver/btcpayserver/releases/tag/v2.4.2",
                    "BTCPay 2.4.2 security release; LND 0.21.0 until 20:59 UTC, then 0.21.1"),
    PlatformRelease("BTCPay", C, "2026-08-07T15:31:16Z", "26.06.1", "26.04–26.06",
                    "https://github.com/btcpayserver/btcpayserver/releases/tag/v2.4.2",
                    "BTCPay 2.4.2 security release; pinned CLN 26.06.1-1"),
    # --- Umbrel, Core Lightning app ---------------------------------------------------------------------------------
    PlatformRelease("Umbrel", C, "2024-05-31T00:36:14Z", "24.02.2", "24.02.2–24.05", _U + "260a643551b8"),
    PlatformRelease("Umbrel", C, "2024-07-09T01:07:27Z", "24.05", "24.02.2–24.05", _U + "11b019c6f256"),
    PlatformRelease("Umbrel", C, "2025-01-21T11:00:25Z", "24.11.1", "24.11–25.02", _U + "e8780e294f5c"),
    PlatformRelease("Umbrel", C, "2025-02-24T04:27:32Z", "24.11.1", "24.11–25.02", _U + "bfc6bba992b3", "gRPC build"),
    PlatformRelease("Umbrel", C, "2025-06-30T00:08:52Z", "25.05", "25.05", _U + "3477b4453be5"),
    PlatformRelease("Umbrel", C, "2025-11-07T04:08:48Z", "25.09.3", "25.09–25.12", _U + "35e19228d8e3"),
    PlatformRelease("Umbrel", C, "2025-11-11T01:12:35Z", "25.09.3", "25.09–25.12", _U + "f85e3a58605b", "hotfix.1"),
    PlatformRelease("Umbrel", C, "2026-05-18T01:14:08Z", "26.04.1", "26.04–26.06", _U + "4ec5c2432f30", "PR #5667"),
    PlatformRelease("Umbrel", C, "2026-06-04T23:38:25Z", "26.06", "26.04–26.06", _U + "ed954cfee07d"),
    PlatformRelease("Umbrel", C, "2026-06-06T00:25:14Z", "26.06.1", "26.04–26.06", _U + "cc7674aa21ed"),
    PlatformRelease("Umbrel", C, "2026-07-05T23:48:05Z", "26.06.2", "26.04–26.06", _U + "ef35edc881fd"),
    PlatformRelease("Umbrel", C, "2026-07-23T01:01:02Z", "26.06.6", "26.04–26.06", _U + "d07a7acd26d4"),
    PlatformRelease("Umbrel", C, "2026-08-27T00:09:03Z", "26.06.6", "26.04–26.06", _U + "e8535eacdb38",
                    "temporary offline mitigation (patch.1)"),
    PlatformRelease("Umbrel", C, "2026-08-28T22:14:36Z", "26.06.7", "26.04–26.06", _U + "dcf27325b33e"),
    PlatformRelease("Umbrel", C, "2026-09-02T00:48:52Z", "26.06.7", "26.04–26.06", _U + "d2725ceac21c", "patch.1"),
    PlatformRelease("Umbrel", C, "2026-09-24T22:30:23Z", "26.06.8", "26.04–26.06", _U + "f82432ccf8bd"),
    PlatformRelease("Umbrel", C, "2026-10-07T21:50:53Z", "26.06.9", "26.04–26.06", _U + "52bbabd63440"),
]


def releases(client: str) -> List[PlatformRelease]:
    return [r for r in PLATFORM_RELEASES if r.client == client]


def after_release(client: str, signed: pd.Series, line_idx: pd.Series, hours: float = 48) -> pd.Series:
    """Whether each upgrade (announcement signed at `signed`, onto release line `line_idx`) falls within `hours`
    after a platform release of `client` that ships that line or a later one."""
    from . import version_fingerprint as vf
    index = {ln.label: ln.index for ln in vf.lines(client)}
    out = pd.Series(False, index=signed.index)
    for r in releases(client):
        d = (signed - r.ts).dt.total_seconds() / 3600
        out |= (d >= 0) & (d <= hours) & (line_idx <= index[r.line])
    return out
