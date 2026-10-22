# Real tunnel geometries and GNSS behaviour at tunnel portals

Research for issue #4. The question: what do real 500 m to 5 km road tunnels look like (curvature, grades, exits or forks inside, speed limits, traffic), and how does GNSS degrade on entry and recover on exit? The output is a set of reference tunnel profiles and a parametric GNSS degradation model for the simulator.

Every number has a label:

- **[S]** sourced: taken directly from the cited source.
- **[D]** derived: calculated from sourced numbers (the calculation is shown).
- **[A]** assumption: no primary source found. This is a reasoned default for the simulator to expose as a tunable parameter.

---

## 1. Design envelope from standards

| Parameter | Value | Label | Source |
|---|---|---|---|
| Max longitudinal grade, new tunnels | 5 %, unless no other geographically feasible solution exists | S | EU Directive 2004/54/EC, Annex I, 2.2.2 [1] |
| Grade above which extra safety measures are required | 3 % | S | 2004/54/EC Annex I, 2.2.3 [1] |
| Max spacing of emergency exits (where provided) | 500 m | S | 2004/54/EC Annex I, 2.3.8 [1] |
| Lay-by spacing (two-way tunnels over 1,500 m without emergency lanes) | at most 1,000 m | S | 2004/54/EC Annex I, 2.5.1 [1] |
| Radio rebroadcast for emergency services | tunnels over 1,000 m | S | 2004/54/EC Annex I, 2.16.1 [1] |
| Directive scope | TEN road tunnels over 500 m | S | 2004/54/EC Art. 1 [1] |
| Example urban-motorway tunnel design: main-line min radius / ramp min radius | 300 m at 70 km/h; 140 m on 50 km/h ramps | S | Södra länken design figures [4] |
| Example ramp grade | 6 % on ramps, 5 % on main line | S | Södra länken [4] |

Implications for the simulator:

- Grades of 0 to 5 % cover almost every real case. A 6 % ramp and one extreme legacy case (the Drammen Spiral, about 10 %, below) are the stress tests.
- Main-line curves inside motorway tunnels have a radius of 300 m or more. Ramps go down to about 140 m. Only legacy or special tunnels go tighter.
- The 500 m emergency-exit spacing means a 5 km tunnel has roughly 10 cross-passages. These are not navigable exits, but they are fixed known features (signs, lighting changes) at known chainages. Later map-matching work could use them.

---

## 2. Reference tunnel profiles

Each profile is simplified to one lane and one direction, as the simulator scope requires. Chainage 0 is the entry portal.

### P1: Straight baseline, Fort McHenry Tunnel (I-95, Baltimore, USA)

| Field | Value | Label |
|---|---|---|
| Length | "nearly 1.4 miles", about 2.2 km | S [5] |
| Curvature | Essentially straight (immersed tube). Model as R = infinity. | A |
| Grade | Immersed-tube sag: down about 4 %, flat, then up about 4 % | A (bounded by 5 % in [1]) |
| In-tunnel exits | None | S [5] (no ramps described) |
| Speed limit | "variable up to 55 mph" (88 km/h) | S [6] (2010 document; current signage not checked) |
| Purpose | Control case. Constant speed, no turns, so along-track error comes purely from speed-integration error. | |

### P2: Long urban tunnel with underground ramps, Södra länken (Stockholm, Sweden)

| Field | Value | Label |
|---|---|---|
| Length | 4.5 km in tunnel (6 km route) | S [3] |
| Cross-section | Twin tubes. Each has 2 through lanes plus 1 lane for access and exiting, 3.5 m lanes | S [4b] |
| Curvature | Main line R ≥ 300 m. Ramps R ≥ 140 m (50 km/h ramps) or ≥ 300 m (70 km/h ramps) | S [4] |
| Grade | Max 5 % main line, 6 % ramps | S [4] |
| In-tunnel exits | Several ramp tunnels branch underground. There are "eight underground bridges at crossings between ramp tunnels and main tunnels" | S [4b] |
| Suggested layout | Exit diverges at 1.6 km and 3.2 km. Ramp R = 140 m, 6 % up, 400 m to its own portal | A (consistent with [4]) |
| Speed limit | 70 km/h | S [4b] (construction-era source) |
| Traffic | About 155,000 vehicles/day. Entrances are closed when traffic slows, to prevent stationary queues, more than 200 closures in 2024 | S [7] |
| Purpose | Main scenario: exit callout inside the tunnel, plus a ramp with its own curve and grade after the diverge | |

### P3: Downtown tunnel with exits inside, Thomas P. O'Neill Jr. Tunnel (I-93, Boston, USA)

| Field | Value | Label |
|---|---|---|
| Length | 1.5 mi (2.4 km) | S [8] |
| Curvature | Gentle S-curves following the old elevated artery alignment. Model as R about 600 to 1,000 m | A |
| Grade | 0 to 3 % | A |
| In-tunnel exits | "Two exits are located in the tunnel" | S [9] (diverge chainages not verified; place at 0.9 km and 1.9 km) |
| Speed limit | 45 mph (72 km/h) | S [9] |
| Traffic | Corridor carried about 200,000 veh/day by the early 1990s (pre-tunnel artery). Expect frequent stop-and-go. | S [8] (historic figure) |
| Purpose | Short tunnel with exits close to the portal. Tests whether the estimator converges before the first callout. | |

### P4: Chained tunnel system with a fork and a mid-route daylight gap, Opera Tunnel (Oslo, Norway)

| Field | Value | Label |
|---|---|---|
| Length | Signposted 5,767 m continuous route. The four tubes total 15,938 m. | S [10] |
| Components | Festning Tunnel 1.8 km (deepest −45 m) → Bjørvika Tunnel 1.1 km (675 m below sea level, 2 × 3 lanes) → 111 m open-air gap → Ekeberg → Svartdal | S [10][11] |
| Vertical profile | Pronounced sag under the harbour: down to −45 m and back up. Grade about 4 to 5 % | D/A: 45 m depth over about 1 km ≈ 4.5 % |
| Forks | The Bjørvika Tunnel ends in an intersection where it splits into E18 (Mosseveien) and the Ekeberg Tunnel | S [11] |
| Ramps | Additional on/off ramps of about 200 m each near Havnelageret | S [12] |
| Speed limit | Not verified. Use 70 km/h. | A |
| Purpose | (a) A fork where the wrong branch must be detected after exit. (b) A 111 m daylight gap where GNSS may partly reacquire for about 5 s at 70 km/h ([D]: 111 m / 19.4 m/s ≈ 5.7 s). This is a realistic trap: a short burst of poor fixes that the estimator must not over-trust. | |

### P5: Extreme curvature and grade, Drammen Spiral (Spiralen, Drammen, Norway)

| Field | Value | Label |
|---|---|---|
| Length | 1,650 m | S [13] |
| Curvature | 6 turns (municipal text: 6.5), diameter 70 m, so R ≈ 35 m | S [13]/D |
| Grade | 22 m rise per turn over a circumference of 2π·35 ≈ 220 m, so about 10 % | D from [13] |
| In-tunnel exits | None | S |
| Speed limit | Not verified. Use 30 km/h. | A |
| Purpose | Stress test for gyro heading integration and the 2D/3D speed mismatch. At 10 % grade, horizontal distance is 0.995 × path length. This is small, but it compounds with heading error over a 360° × 6 rotation. Grade and curvature here lie outside modern design rules [1], so it is a stress case only. | |

### Reference for exit density (outside the length range): Madrid M30-Río

16.4 km of twin tubes with 21 entries and 25 exits [14]. That works out to about one diverge every 650 m per direction ([D]: 16.4 km / 25 ≈ 0.66 km). It is useful as an upper bound on how closely in-tunnel exits are spaced in a dense urban network. Detail figures (grades, radii) could not be retrieved because the source PDF was access-blocked.

---

## 3. GNSS behaviour around tunnels: evidence

### 3.1 Baseline accuracy outside the tunnel

- An automotive-grade L1 multi-constellation receiver on 27,500 km of North American highways had these horizontal errors [S, 15]:

  | Error component | 68 % | 95 % | 99 % |
  |---|---|---|---|
  | Horizontal | 3.07 m | 5.30 m | 9.38 m |
  | Longitudinal (along-track) | 2.11 m | 4.44 m | 7.95 m |
  | Lateral | 1.92 m | 3.88 m | 5.74 m |

  Longitudinal error was slightly worse than lateral, which the authors partly attribute to timing latency.
- Smartphone in an urban environment: average errors of about 7 to 13 m, driven mainly by buildings and multipath [S, 16].
- Urban-canyon NLOS: a modelled hypothesis-based solution still has about 6.3 m horizontal error after NLOS modelling [S, 17]. Unmitigated NLOS pseudorange errors are larger. A map-aided correction patent treats fixes more than 30 m off after a tunnel as correctable outliers [S, 18].

### 3.2 Short outages are common and are not tunnels

- On highways, 95 % of standard positioning outages lasted under 7 s (mostly overpasses and signs) [S, 15]. The probability of losing standard positioning within a 4 s window was 0.045 [S, 15].
- Implication: the estimator should not declare "tunnel mode" from a few seconds without a fix. It should combine the gap with map knowledge of the portal.

### 3.3 Entry

- Inside a tunnel the sky is fully masked, and simulators model this as complete blockage of all satellites [S, 19]. Near the portal and the first part of the tube, reflections off the walls and lining cause severe attenuation and strong near-field multipath [S, 20].
- No peer-reviewed measurement of fade distance versus portal chainage was found (see Gaps). The model below treats it as a parameter.

### 3.4 Exit and reacquisition

- A receiver that tracked before the tunnel keeps valid ephemeris, so the exit is effectively a hot start. In a documented tunnel-exit experiment, waiting just 1 s after exit raised the satellites available from 4 to 6. A one-shot least-squares fix then "showed no relevant errors" [S, 21].
- In the same experiment, a conventional Kalman-filter fix from the first 4 satellites at the exit was about **180 m** off, because the filter's history was corrupted by the outage [S, 21]. A second patent describes precision staying low from the tunnel exit onward when the receiver re-locks into a multipath-affected section [S, 22].
- Worst-case bound: marine GNSS performance standards require re-acquisition within 2 min after a 60 s power interruption [S, 23]. That is far looser than a phone with retained ephemeris achieves, but it sets an upper bound for a "bad phone" scenario.

### 3.5 What a web app actually receives (stale fixes and accuracy semantics)

The simulator is a web app, so the phone-side interface is the W3C Geolocation API:

- `accuracy` is defined at the **95 %** confidence level, in metres [S, 24].
- `timestamp` is "the time when the geographic position of the device was acquired" [S, 24]. It is not the delivery time, so a stale fix keeps its old timestamp.
- `maximumAge` lets the browser return a cached position up to that age [S, 24]. Only the last position is cached.
- `watchPosition` updates fire on a "significant change" that the implementation defines, and may be rate-limited [S, 24]. In a tunnel this means **callbacks may simply stop**, rather than arriving with large accuracy.
- `speed` and `heading` may be null [S, 24].
- On Android, the native `Location.getAccuracy()` is a **68 %** radius [S, 25]. A browser on Android may pass this value through. Treat the stated confidence level as uncertain: σ ≈ accuracy/1 (68 %) or σ ≈ accuracy/2.45 (95 %, 2D Rayleigh). The simulator should be able to emit either convention.

---

## 4. Parametric GNSS degradation model for the simulator

Distances are along-track chainage `s`. The entry portal is at `s = 0` and the exit portal at `s = L`. The model emits one fix per epoch (1 Hz default), or no fix.

| # | Phase | Region | Behaviour | Parameters (default; range) |
|---|---|---|---|---|
| 1 | Open road | s < −d_in | Gaussian errors, split along/cross-track. Optional slow bias (random walk). | σ_along = 2.1 m, σ_cross = 1.9 m (68 %, automotive [15]). Phone preset σ_h = 5 m (open road); 10 m urban approach [16] [S/A] |
| 2 | Approach fade | −d_in ≤ s < 0 | σ grows linearly up to k_fade × nominal. Reported accuracy lags the true error. | d_in = 50 m (0–150) [A]; k_fade = 3 (1–5) [A] |
| 3 | Portal multipath | 0 ≤ s < d_mp | Fixes still appear, but with probability p_out they are NLOS outliers biased **along-track toward the portal** (an apparent lag). | d_mp = 30 m (0–100) [A]; p_out = 0.3 [A]; outlier bias 10–50 m [A, anchored on 30 m threshold in [18]] |
| 4 | Coast | until t_coast after the last real fix | The chipset/OS emits extrapolated fixes (constant velocity) with reported accuracy that grows slowly. These look valid but are fake. | t_coast = 3 s (0–10) [A]; compatible with outages under 7 s being routine [15] |
| 5 | Dark | inside the tunnel after coast | Choose a mode: (a) no callbacks, (b) the cached last fix is repeated with its old `timestamp` (stale), (c) rare spurious fixes. | mode = (a) default [S: behaviour allowed by 24]; p_spurious = 0.01/s [A] |
| 6 | Exit reacquisition | s ≥ L | First fix after t_first. The first k_bad fixes come from a filter corrupted by the outage: bias along-track (the filter coasted at the old velocity) with magnitude up to B_exit. | t_first = 1 s (1–5) [S: 1 s in 21; range A]; k_bad = 2 (0–5) [A]; B_exit = 30 m (0–180) [S: 180 m worst case in 21] |
| 7 | Converge | L + until t_good | σ decays exponentially from the exit level to nominal. Reported accuracy is optimistic during this phase (under-reports the error). | t_good = 5 s (3–15) [A]; optimism factor 0.5 [A] |
| 8 | Daylight gap (P4) | gap shorter than d_gap | Runs phases 6–7 truncated to the gap duration, then phases 2–5 again. | gap length from profile |

Design notes:

- **The along-track bias sign matters.** Phase 3 (fixes lag behind the car) and phase 6 (a filter coasting at the old speed overshoots or undershoots after a speed change in the tunnel) both put the error along-track. That is the error axis that decides the exit-callout timing.
- **Ground-truth comparisons** should use the stated confidence convention (68 % vs 95 %) consistently. See 3.5.
- **Accept/reject logic** to evaluate: an estimator that trusts the first exit fix will jump by up to B_exit. A good estimator gates new fixes against its dead-reckoning prediction for a few epochs (the same idea as the 1 s wait and least-squares fix in [21]).

---

## 5. Traffic behaviour inside tunnels

- **Speed limits** in urban-motorway tunnels are typically 70 to 90 km/h (Södra länken 70 km/h [4b], O'Neill 72 km/h [9], Fort McHenry variable up to 88 km/h [6]). Spiral and legacy tunnels are much lower [A].
- **Entry slowdown.** Drivers tend to slow at the tunnel entrance and speed up again near the exit. In a driving-simulator study, entrance-zone speed-reduction markings produced speed differences of about 10 km/h by day and 5 km/h at night compared with no markings, and drivers without markings accelerated at the exit [S, 26]. A field study found strobe lights and information boards cut speed by about 3.1 % [S, 26b].
- **Congestion and capacity drop.** Tunnels and sags are recognised bottlenecks. Queue discharge flow falls by roughly 10 % once congestion forms [S, 27b], attributed mainly to sluggish acceleration out of the queue [S, 27]. Operators of heavily used tunnels close entrances to keep queues from standing inside: Södra länken was closed more than 200 times in 2024 for this reason [S, 7].
- **Speed profiles for the simulator:**
  1. Free flow: constant speed at the limit, ±5 % noise.
  2. Entry dip: −10 km/h over the first 200 m, then recovery [A, sized from 26].
  3. Stop-and-go: shockwaves with a period of 30–120 s, speed 0–40 km/h [A].
  4. Full stop of 1–5 min inside (closure or incident) [A, motivated by 7].

  Profiles 3 and 4 matter most: wheel-less smartphone speed estimation tends to fail at stops and restarts, and long standstills accumulate IMU drift.

---

## 6. Gaps and confidence

- **No peer-reviewed field measurement was found** of smartphone GNSS fade distance at a road-tunnel portal, or of seconds-to-good-fix after a road-tunnel exit. The exit figures (1 s to 6 satellites, a 180 m Kalman outlier) come from a patent's documented experiment [21], which is a primary but not peer-reviewed source. All [A] parameters should be exposed as sliders and swept.
- Speed limits for the Opera Tunnel and the Drammen Spiral, the diverge chainages in P2/P3, and the Fort McHenry grade are assumptions.
- The Södra länken 70 km/h limit and the 5 %/6 % and 300/140 m figures come from construction-era trade articles summarising the design [4][4b]. Current signage was not verified.
- Sources that were access-blocked, so their details were not used: the PIARC M30 appendix PDF (only the length and access counts quoted in its listing were used), and a 2025 smartphone tunnel dead-reckoning paper (*Satellite Navigation*, doi:10.1186/s43020-025-00168-7).

---

## References

1. Directive 2004/54/EC on minimum safety requirements for tunnels in the Trans-European Road Network, Annex I. https://www.legislation.gov.uk/eudr/2004/54/annex/I/adopted
3. Södra länken overview, citing the Swedish Road Administration's project brochure, pp. 4–5. https://en.wikipedia.org/wiki/S%C3%B6dra_l%C3%A4nken
4. "Stockholm's Southern Link" design summary (gradients, radii, design speeds). https://tunnelsandtunnelling.com/?p=276
4b. Southern Link tunnel contracts (lanes, speed limit, underground ramp crossings). https://tunnelsandtunnelling.com/?p=446
5. Maryland Transportation Authority, Fort McHenry Tunnel facility page. https://mdta.maryland.gov/index.php/Toll_Facilities/FMT.html
6. Virginia Division of Legislative Services, tunnel comparison (2010). https://dls.virginia.gov/GROUPS/transaccount/meetings/092010/HRBT.pdf
7. Trafikverket, "Södra länken får förbättrat brandskydd i den nationella planen" (2026). https://www.trafikverket.se/om-oss/nyheter/lansnyheter/stockholm/20262/2026-04/sodra-lanken-far-forbattrat-brandskydd-i-den-nationella-planen/
8. Thomas P. O'Neill Jr. Tunnel. https://en.wikipedia.org/wiki/O%27Neill_Tunnel
9. Interstate 93, Massachusetts section. https://en.wikipedia.org/wiki/Interstate_93
10. Opera Tunnel. https://en.wikipedia.org/wiki/Opera_Tunnel ; Norwegian local-history entry: https://lokalhistoriewiki.no/wiki/Operatunnelen
11. Bjørvika Tunnel / Festning Tunnel. https://en.wikipedia.org/wiki/Bj%C3%B8rvika_Tunnel , https://en.wikipedia.org/wiki/Festning_Tunnel
12. Teknisk Ukeblad, new ramps at Havnelageret (2012). https://www.tu.no/artikler/lettere-adkomst-til-oslo-sentrum/195504
13. Drammen Spiral. https://en.wikipedia.org/wiki/Drammen_Spiral ; municipal description quoted in https://www.tu.no/artikler/spiralen-skal-fa-ny-portal-i-ovre-ende/514775
14. PIARC Road Tunnels Manual, Appendix 2.17 "Madrid – Túnel M30-Río". https://tunnelsmanual.piarc.org/es/system/files/media/file/apendice_2.17_-_espana_-_madrid_-_tunel_m30-rio.pdf
15. Reid, T. G. R. et al., "Standalone and RTK GNSS on 30,000 km of North American Highways," ION GNSS+ 2019, pp. 2135–2158. https://arxiv.org/abs/1906.08180 (Table 3; Conclusion)
16. Merry, K. & Bettinger, P., "Smartphone GPS accuracy study in an urban environment," PLOS ONE 14(7): e0219890, 2019. https://doi.org/10.1371/journal.pone.0219890
17. Hsu, L.-T., "Analysis and modeling GPS NLOS effect in highly urbanized area," GPS Solutions 22:7, 2018. https://doi.org/10.1007/s10291-017-0667-9
18. US Patent 11,402,514, "Geographical feature/artificial structures detection and application for GNSS navigation with map information." https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11402514
19. "On the Road under Real-Time Signal Denial," GPS World (tunnel modelled as complete sky mask). https://www.gpsworld.com/on-the-road-under-real-time-signal-denial/
20. Pseudolite deployment for tunnel positioning (PMC, tunnel attenuation and near-field multipath). https://pmc.ncbi.nlm.nih.gov/articles/PMC13165580/
21. US Patent 8,125,380, "Position computing method, receiving apparatus and navigation satellite system employing the method" (tunnel-exit experiment). https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/8125380
22. US Patent 11,441,907, "Positioning device and positioning method." https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/11441907
23. IMO Resolution MSC.112(73), performance standards for shipborne GPS receiver equipment. https://www.navcen.uscg.gov/sites/default/files/pdf/marcomms/imo/msc_resolutions/MSC73-21a3-25.pdf
24. W3C, Geolocation API (Recommendation), §6.5, §6.6, §7.2, §7.3, §8.2. https://www.w3.org/TR/geolocation/
25. Android API reference, `android.location.Location#getAccuracy()`. https://developer.android.com/reference/android/location/Location
26. "Evaluation of Effectiveness of Speed Reduction Markings on Driving Speed in Highway Tunnel Entrance and Exit Areas," Promet – Traffic & Transportation, 2020. https://traffic.fpz.hr/index.php/PROMTT/article/view/3203
26b. Promet study on strobe lights and information boards at tunnel entrances. https://hrcak.srce.hr/index.php/clanak/340607
27. "Empirical Validation of Continuum Traffic Flow Model of Capacity Drop at Sag and Tunnel Bottlenecks," arXiv:2511.16962. https://arxiv.org/pdf/2511.16962
27b. Wada et al., extended abstract on queue discharge flow at sag and tunnel bottlenecks, ISTDM 2025. https://symposia.cirrelt.ca/ISTDM2025/en/schedule/view_document/12690
