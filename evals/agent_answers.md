# Agent answers

Server: http://localhost:8080. Captured 2026-11-04 00:11 UTC.

## Q1

**User:** For major hip/knee replacement without complications (DRG 470), which five NY hospitals had the highest average total Medicare payment in 2024, and how do they compare with the NY and national averages?

*12.7 s, rounds 1, audit {'removed_citations': 0, 'flagged_numbers': 0, 'dropped_claims': 0, 'attached_sources': 0, 'repaired': False, 'violations': 0}*

## In 2024, the five New York hospitals with the highest average total Medicare payment for major hip or knee replacement without complications (DRG 470) were Montefiore Medical Center, South Shore University Hospital, Brooklyn Hospital Center - Downtown Campus, Mount Sinai Hospital, and Lenox Hill Hospital.

Montefiore Medical Center had the highest average total payment in the cohort at $31,015, which is +33.5% above the New York average and +78.6% above the national average [S4][S5].

South Shore University Hospital ranked #2 of 56 with an average total payment of $28,653, standing at +23.3% above the New York average and +65.0% above the national average [S4][S5].

Brooklyn Hospital Center - Downtown Campus ranked #3 of 56 with an average total payment of $27,728 (+19.3% above the New York average and +59.7% above the national average), though this figure rests on only 12 Medicare discharges and must be treated as unstable [S4][S5].

Mount Sinai Hospital ranked #4 of 56 with an average total payment of $27,622, representing +18.9% above the New York average and +59.1% above the national average [S4][S5].

Lenox Hill Hospital ranked #5 of 56 with an average total payment of $26,238, which is +12.9% above the New York average and +51.1% above the national average [S4][S5].

**Cohort ranking by average total payment, DRG 470** (highest payment first; 56 ranked) [S4] [S5]

| # | Hospital | City | Avg total payment | vs NY avg | Medicare discharges | Note |
|---|---|---|---|---|---|---|
| 1 | Montefiore Medical Center | Bronx | $31,015 | +33.5% | 186 | - |
| 2 | South Shore University  Hospital | Bay Shore | $28,653 | +23.3% | 102 | - |
| 3 | Brooklyn Hospital Center - Downtown Campus | Brooklyn | $27,728 | +19.3% | 12 | small sample |
| 4 | Mount Sinai Hospital | New York | $27,622 | +18.9% | 158 | - |
| 5 | Lenox Hill Hospital | New York | $26,238 | +12.9% | 136 | - |
| 6 | North Shore University Hospital | Manhasset | $26,043 | +12.1% | 242 | - |
| 7 | Hospital For Special Surgery | New York | $25,507 | +9.8% | 1332 | - |
| 8 | Nyu Langone Hospitals | New York | $25,403 | +9.3% | 940 | - |
| 9 | New York-Presbyterian Hospital | New York | $24,852 | +7.0% | 304 | - |
| 10 | Mount Sinai West | New York | $24,680 | +6.2% | 99 | - |

**Cost versus quality, DRG 470** [S4] [S5] [S1] [S2] [S3] [S6]

| Hospital | Avg total payment | Quality measure | Value | Group |
|---|---|---|---|---|
| Montefiore Medical Center | $31,015 | COMP_HIP_KNEE | 2.8% | higher cost / better quality |
| South Shore University  Hospital | $28,653 | COMP_HIP_KNEE | 2.5% | higher cost / better quality |
| Brooklyn Hospital Center - Downtown Campus | $27,728 | COMP_HIP_KNEE | - | insufficient data (fewer than 20 Medicare discharges) |
| Mount Sinai Hospital | $27,622 | COMP_HIP_KNEE | 2.7% | higher cost / better quality |
| Lenox Hill Hospital | $26,238 | COMP_HIP_KNEE | 2.8% | higher cost / better quality |
| North Shore University Hospital | $26,043 | COMP_HIP_KNEE | 3.0% | higher cost / better quality |
| Hospital For Special Surgery | $25,507 | COMP_HIP_KNEE | 2.9% | higher cost / better quality |
| Nyu Langone Hospitals | $25,403 | COMP_HIP_KNEE | 2.8% | higher cost / better quality |
| New York-Presbyterian Hospital | $24,852 | COMP_HIP_KNEE | 4.0% | higher cost / better quality |
| Mount Sinai West | $24,680 | COMP_HIP_KNEE | 3.1% | higher cost / better quality |

### What the data can't tell you

- The data cannot tell you what patients actually pay out-of-pocket for these procedures.
- The data cannot tell you the quality of post-operative care or long-term functional recovery outcomes for these specific patients.
- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.
- 72 hospital(s) have no row for the requested DRG(s) (fewer than 11 discharges are suppressed): BRONXCARE HOSPITAL CENTER, ALBANY MEDICAL CENTER HOSPITAL, JAMAICA HOSPITAL MEDICAL CENTER, NEW YORK COMMUNITY HOSPITAL OF BROOKLYN, INC., VASSAR BROTHERS MEDICAL CENTER, NASSAU UNIVERSITY MEDICAL CENTER, RICHMOND UNIVERSITY MEDICAL CENTER, NEWARK-WAYNE COMMUNITY HOSPITAL....
- 1 figure(s) rest on small samples and are flagged unstable.
- Cost data is calendar 2024; quality measures cover different periods (Apr 2023 to Mar 2025; Jul 2022 to Jun 2024; Oct 2024 to Sep 2025). Compare directionally.

### You could also ask

- What are the patient readmission rates for these specific five hospitals under DRG 470?
- How do private insurance payments compare to Medicare fee-for-service payments for these hospitals?

### Sources

- [S1] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=COMP_HIP_KNEE&conditions[1][operator]=IN&count=true
- [S2] Complications and Deaths - National Data — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/qqw3-t4ie/0?count=true
- [S3] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=PSI_90&conditions[1][operator]=IN&count=true
- [S4] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=470
- [S5] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=470
- [S6] HCAHPS Patient Survey - Hospital — 2024-10-01 to 2025-09-30 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=hcahps_measure_id&conditions[1][value]=H_STAR_RATING&conditions[1][operator]=%3D&count=true

## Q2

**User:** How does Montefiore compare with other Bronx hospitals on heart failure — Medicare payment, 30-day readmissions and mortality?

*10.7 s, rounds 1, audit {'removed_citations': 0, 'flagged_numbers': 0, 'dropped_claims': 0, 'attached_sources': 0, 'repaired': False, 'violations': 0}*

## Montefiore Medical Center has lower Medicare payments and better readmission ratios for heart failure compared to most Bronx hospitals, alongside lower mortality rates than the national rate.

Montefiore Medical Center reports a DRG 291 average total payment of $24,163, ranking #4 of 5 in the cohort at the 25th percentile [S6]. This payment is +50.7% above the New York average and +100.5% above the national average [S6][S8].

For 30-day heart failure readmissions, Montefiore Medical Center has an excess readmission ratio of 0.935, which is categorized as better than expected [S1]. Across the cohort of 5 hospitals, ratios range with a cohort median excess readmission ratio of 1.032 [S1].

Montefiore Medical Center records a heart failure mortality score of 5.2%, which has a difference of -5.9 pp from the national rate and is lower than the national rate (direction only) [S2][S3].

**Cohort ranking by average total payment, DRG 291** (highest payment first; 5 ranked) [S6] [S8]

| # | Hospital | City | Avg total payment | vs NY avg | Medicare discharges | Note |
|---|---|---|---|---|---|---|
| 1 | Lincoln Medical & Mental Health Center | Bronx | $31,893 | +98.9% | 39 | - |
| 2 | Jacobi Medical Center | Bronx | $29,655 | +85.0% | 89 | - |
| 3 | St Barnabas Hospital | Bronx | $27,390 | +70.8% | 27 | - |
| 4 | Montefiore Medical Center (focus) | Bronx | $24,163 | +50.7% | 390 | - |
| 5 | Bronxcare Hospital Center | Bronx | $23,266 | +45.1% | 54 | - |

**Cost versus quality, DRG 291** [S6] [S8] [S1] [S2] [S3] [S5] [S4]

| Hospital | Avg total payment | Quality measure | Value | Group |
|---|---|---|---|---|
| Montefiore Medical Center | $24,163 | READM-30-HF-HRRP | 0.935 | lower cost / better quality |

### What the data can't tell you

- The data cannot tell you why Montefiore's submitted charge to payment ratio is 7.0x while other Bronx hospitals range from 1.0x to 2.1x.
- The data cannot tell you patient-level clinical nuances or severity differences between Montefiore's 390 Medicare discharges and other cohort hospitals.
- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.
- Cost data is calendar 2024; quality measures cover different periods (Jul 2021 to Jun 2024; Jul 2022 to Jun 2024; Jul 2022 to Jun 2025; Oct 2024 to Sep 2025). Compare directionally.

### You could also ask

- How do complication rates like PSI 04 and PSI 90 specifically impact overall hospital quality rankings in the Bronx?
- What are the specific patient outcomes for sibling heart failure DRG 292 across these hospitals?

### Sources

- [S1] Hospital Readmissions Reduction Program — 2021-07-01 to 2024-06-30 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/9n3s-kdb3/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_name&conditions[1][value][]=READM-30-HF-HRRP&conditions[1][operator]=IN&count=true
- [S2] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=MORT_30_HF&conditions[1][operator]=IN&count=true
- [S3] Complications and Deaths - National Data — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/qqw3-t4ie/0?count=true
- [S4] HCAHPS Patient Survey - Hospital — 2024-10-01 to 2025-09-30 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=hcahps_measure_id&conditions[1][value]=H_STAR_RATING&conditions[1][operator]=%3D&count=true
- [S5] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=PSI_04&conditions[1][value][]=PSI_90&conditions[1][operator]=IN&count=true
- [S6] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=291
- [S8] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=291

## Q3

**User:** Which NY hospitals are the best?

*1.2 s, rounds 0, audit None*

## Which specific medical service or region would you like to focus on for New York hospitals?

- Heart surgery outcomes in Manhattan hospitals
- Orthopedic (knee/hip) replacement costs in Brooklyn
- Cancer care quality at Memorial Sloan Kettering vs. Mount Sinai
- Overall top-rated hospitals in Upstate New York

Reply with one of these, or tell me the hospital, condition and region you care about.

**User:** Hip and knee replacement in New York City, both cost and quality.

*11.5 s, rounds 1, audit {'removed_citations': 0, 'flagged_numbers': 0, 'dropped_claims': 0, 'attached_sources': 0, 'repaired': False, 'violations': 0}*

## Hip and knee replacement costs in New York City vary widely by hospital, while quality measures such as readmission ratios and complication scores show a mix of better- and worse-than-expected performance.

For major joint replacement or reattachment of lower extremity with major complication or comorbidity (DRG 469), the cohort volume-weighted mean payment is $39,725 [S4]. Specific hospital average total payments in this category include $44,085 for Mount Sinai Hospital, $40,931 for New York-Presbyterian Hospital, $40,227 for Hospital For Special Surgery, and $38,267 for Nyu Langone Hospitals [S4]. Note that Mount Sinai Hospital and New York-Presbyterian Hospital payments are based on only 11 and 15 Medicare discharges respectively, and should be treated as unstable [S4].

For lower extremity joint replacement or reattachment without major complication or comorbidity (DRG 470), the cohort volume-weighted mean payment is $25,705 [S5]. Average total payments range across reporting hospitals, such as $31,015 for Montefiore Medical Center, $25,507 for Hospital For Special Surgery, and $24,852 for New York-Presbyterian Hospital [S5].

Regarding readmissions under the Hospital Readmissions Reduction Program, the cohort median excess readmission ratio is 0.965 across 13 hospitals with a ratio [S1]. Specific excess readmission ratios include 0.745 for NYU Langone Hospitals, 0.674 for Hospital For Special Surgery, and 1.260 for Mount Sinai West [S1].

Complication scores for hip and knee replacement vary across institutions, with Mount Sinai Hospital reporting a score of 2.7% which is lower than the national rate (direction only), while Richmond University Medical Center reports a score of 5.2% which is higher than the national rate (direction only) [S2][S3].

**Cohort ranking by average total payment, DRG 470** (highest payment first; 12 ranked) [S4] [S8] [S5] [S9]

| # | Hospital | City | Avg total payment | vs NY avg | Medicare discharges | Note |
|---|---|---|---|---|---|---|
| 1 | Montefiore Medical Center (focus) | Bronx | $31,015 | +33.5% | 186 | - |
| 2 | Brooklyn Hospital Center - Downtown Campus (focus) | Brooklyn | $27,728 | +19.3% | 12 | small sample |
| 3 | Mount Sinai Hospital (focus) | New York | $27,622 | +18.9% | 158 | - |
| 4 | Lenox Hill Hospital | New York | $26,238 | +12.9% | 136 | - |
| 5 | Hospital For Special Surgery | New York | $25,507 | +9.8% | 1332 | - |
| 6 | Nyu Langone Hospitals | New York | $25,403 | +9.3% | 940 | - |
| 7 | New York-Presbyterian Hospital (focus) | New York | $24,852 | +7.0% | 304 | - |
| 8 | Mount Sinai West (focus) | New York | $24,680 | +6.2% | 99 | - |
| 9 | Maimonides Medical Center | Brooklyn | $24,051 | +3.5% | 50 | - |
| 10 | Mount Sinai Beth Israel | New York | $23,380 | +0.6% | 11 | small sample |
| 12 | New York-Presbyterian/Queens (focus) | Flushing | $23,332 | +0.4% | 124 | - |

**Cost versus quality, DRG 470** [S4] [S8] [S5] [S9] [S1] [S2] [S3] [S6] [S7]

| Hospital | Avg total payment | Quality measure | Value | Group |
|---|---|---|---|---|
| Montefiore Medical Center | $31,015 | READM-30-HIP-KNEE-HRRP | 0.973 | higher cost / better quality |
| Brooklyn Hospital Center - Downtown Campus | $27,728 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| Mount Sinai Hospital | $27,622 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| New York-Presbyterian Hospital | $24,852 | READM-30-HIP-KNEE-HRRP | 0.787 | lower cost / better quality |
| Mount Sinai West | $24,680 | READM-30-HIP-KNEE-HRRP | 1.260 | lower cost / worse quality |
| New York-Presbyterian/Queens | $23,332 | READM-30-HIP-KNEE-HRRP | 0.914 | lower cost / better quality |

### What the data can't tell you

- The data cannot tell you patient functional outcomes or pain scores following hip and knee replacement surgery.
- The data cannot tell you out-of-pocket costs or private insurance reimbursement rates for these procedures.
- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.
- 21 hospital(s) have no row for the requested DRG(s) (fewer than 11 discharges are suppressed): BRONXCARE HOSPITAL CENTER, JAMAICA HOSPITAL MEDICAL CENTER, NEW YORK COMMUNITY HOSPITAL OF BROOKLYN, INC., RICHMOND UNIVERSITY MEDICAL CENTER, LINCOLN MEDICAL & MENTAL HEALTH CENTER, NY EYE AND EAR INFIRMARY OF MOUNT SINAI, JACOBI MEDICAL CENTER, ELMHURST HOSPITAL CENTER....
- 7 figure(s) rest on small samples and are flagged unstable.
- Cost data is calendar 2024; quality measures cover different periods (Apr 2023 to Mar 2025; Jul 2021 to Jun 2024; Jul 2022 to Jun 2024; Oct 2024 to Sep 2025). Compare directionally.

### You could also ask

- What are the patient experience and HCAHPS survey scores for these specific hospitals?
- How do complication and readmission rates change over a longer multi-year period?

### Sources

- [S1] Hospital Readmissions Reduction Program — 2021-07-01 to 2024-06-30 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/9n3s-kdb3/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_name&conditions[1][value][]=READM-30-HIP-KNEE-HRRP&conditions[1][operator]=IN&count=true
- [S2] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=COMP_HIP_KNEE&conditions[1][operator]=IN&count=true
- [S3] Complications and Deaths - National Data — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/qqw3-t4ie/0?count=true
- [S4] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=469
- [S5] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=470
- [S6] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=PSI_09&conditions[1][value][]=PSI_12&conditions[1][value][]=PSI_90&conditions[1][operator]=IN&count=true
- [S7] HCAHPS Patient Survey - Hospital — 2024-10-01 to 2025-09-30 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=hcahps_measure_id&conditions[1][value]=H_STAR_RATING&conditions[1][operator]=%3D&count=true
- [S8] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=469
- [S9] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=470

## More 1

**User:** What will I pay out of pocket for a knee replacement at NYU?

*13.9 s, rounds 1, audit {'removed_citations': 0, 'flagged_numbers': 0, 'dropped_claims': 0, 'attached_sources': 0, 'repaired': True, 'violations': 0}*

## The provided data does not show out-of-pocket patient costs, but lists average Medicare payments for knee replacements at NYU Langone Hospitals.

For major joint replacement or reattachment of lower extremity with major complications or comorbidities (DRG 469), NYU Langone Hospitals recorded an average total payment of $38,267 [S2]. This payment was +5.8% above the New York average and +29.0% above the national average [S2][S7].

For lower extremity joint replacement or reattachment without major complications or comorbidities (DRG 470), NYU Langone Hospitals recorded an average total payment of $25,403 [S3]. This payment was +9.3% above the New York average and +46.3% above the national average [S3][S8].

NYU Langone Hospitals reported a submitted charge to payment ratio of 7.2x for DRG 469 and 8.8x for DRG 470, though charges are list prices and not what anyone pays [S2][S3].

For quality and safety, NYU Langone Hospitals had an excess readmission ratio of 0.745, which is better than expected [S1]. Their hip/knee complication rate was 2.8%, which is lower than the national rate (direction only) and represents a difference of -1.3 pp from the national rate [S9][S5].

**Cohort ranking by average total payment, DRG 470** (highest payment first; 7 ranked) [S2] [S7] [S3] [S8]

| # | Hospital | City | Avg total payment | vs NY avg | Medicare discharges | Note |
|---|---|---|---|---|---|---|
| 1 | Mount Sinai Hospital | New York | $27,622 | +18.9% | 158 | - |
| 2 | Lenox Hill Hospital | New York | $26,238 | +12.9% | 136 | - |
| 3 | Hospital For Special Surgery | New York | $25,507 | +9.8% | 1332 | - |
| 4 | Nyu Langone Hospitals (focus) | New York | $25,403 | +9.3% | 940 | - |
| 5 | New York-Presbyterian Hospital | New York | $24,852 | +7.0% | 304 | - |
| 6 | Mount Sinai West | New York | $24,680 | +6.2% | 99 | - |
| 7 | Mount Sinai Beth Israel | New York | $23,380 | +0.6% | 11 | small sample |

**Cost versus quality, DRG 470** [S2] [S7] [S3] [S8] [S1] [S4] [S5] [S9] [S6]

| Hospital | Avg total payment | Quality measure | Value | Group |
|---|---|---|---|---|
| Nyu Langone Hospitals | $25,403 | READM-30-HIP-KNEE-HRRP | 0.745 | lower cost / better quality |

### What the data can't tell you

- The data cannot tell you what an individual patient will pay out of pocket, as it only shows average Medicare fee-for-service payments and list charges.
- The data cannot tell you what patients with private insurance or commercial health plans will be charged or expected to pay.
- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.
- 4 hospital(s) have no row for the requested DRG(s) (fewer than 11 discharges are suppressed): NY EYE AND EAR INFIRMARY OF MOUNT SINAI, METROPOLITAN HOSPITAL CENTER, BELLEVUE HOSPITAL CENTER, HARLEM HOSPITAL CENTER.
- 5 figure(s) rest on small samples and are flagged unstable.
- Cost data is calendar 2024; quality measures cover different periods (Apr 2023 to Mar 2025; Jul 2021 to Jun 2024; Jul 2022 to Jun 2024; Oct 2024 to Sep 2025). Compare directionally.

### You could also ask

- What are the specific out-of-pocket deductible and coinsurance requirements for my specific insurance plan at NYU Langone Hospitals?
- How do NYU Langone Hospitals' out-patient knee replacement costs compare to their inpatient costs?

### Sources

- [S1] Hospital Readmissions Reduction Program — 2021-07-01 to 2024-06-30 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/9n3s-kdb3/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_name&conditions[1][value][]=READM-30-HIP-KNEE-HRRP&conditions[1][operator]=IN&count=true
- [S2] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=469
- [S3] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=470
- [S4] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=PSI_09&conditions[1][value][]=PSI_12&conditions[1][value][]=PSI_90&conditions[1][operator]=IN&count=true
- [S5] Complications and Deaths - National Data — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/qqw3-t4ie/0?count=true
- [S6] HCAHPS Patient Survey - Hospital — 2024-10-01 to 2025-09-30 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=hcahps_measure_id&conditions[1][value]=H_STAR_RATING&conditions[1][operator]=%3D&count=true
- [S7] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=469
- [S8] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-04 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=470
- [S9] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-04 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=COMP_HIP_KNEE&conditions[1][operator]=IN&count=true

_Audit: the draft was revised once after validation._

## More 2

**User:** Cheapest knee replacement in Boston?

*3.9 s, rounds 0, audit None*

## This question is outside what the data can answer

Data is limited to New York hospitals, so we cannot provide information for Boston.

Could not resolve:
- Boston hospitals: outside NY scope

Hospital Atlas covers New York hospitals using CMS Medicare data: inpatient payments by DRG (CY2024), readmission and mortality measures, patient safety indicators and patient-survey star ratings.

### What the data can't tell you

- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.

### Sources

No dataset was queried for this answer.
