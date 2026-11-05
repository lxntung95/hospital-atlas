# Agent answers

Server: http://localhost:8099. Captured 2026-11-05 12:36 UTC.

## Q1

**User:** For major hip/knee replacement without complications (DRG 470), which five NY hospitals had the highest average total Medicare payment in 2024, and how do they compare with the NY and national averages?

*13.9 s, rounds 2, audit {'removed_citations': 0, 'flagged_numbers': 0, 'dropped_claims': 0, 'attached_sources': 0, 'repaired': False, 'violations': 0}*

## In 2024, the five New York hospitals with the highest average total Medicare payment for major hip and knee replacement without complications (DRG 470) were Montefiore Medical Center, South Shore University Hospital, Brooklyn Hospital Center - Downtown Campus, Mount Sinai Hospital, and Lenox Hill Hospital.

Montefiore Medical Center had the highest average total payment at $31,015, which is +33.5% above the New York average and +78.6% above the national average [S1][S6].

South Shore University Hospital ranked second with an average total payment of $28,653, representing +23.3% above the New York average and +65.0% above the national average [S1][S6].

Brooklyn Hospital Center - Downtown Campus ranked third with an average total payment of $27,728, which is +19.3% above the New York average and +59.7% above the national average, though this is based on only 12 Medicare discharges and should be treated as unstable [S1][S6][S1].

Mount Sinai Hospital ranked fourth with an average total payment of $27,622, and Lenox Hill Hospital ranked fifth with $26,238 [S1].

For DRG 470, the New York average payment was $23,235 and the national average payment was $17,364 [S6].

**Cohort ranking by average total payment, DRG 470** (highest payment first; 56 ranked) [S8] [S9] [S1] [S6]

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

**Cost versus quality, DRG 470** [S8] [S9] [S1] [S6] [S7] [S3] [S4] [S5] [S2]

| Hospital | Avg total payment | Quality measure | Value | Group |
|---|---|---|---|---|
| Montefiore Medical Center | $31,015 | READM-30-HIP-KNEE-HRRP | 0.973 | higher cost / better quality |
| South Shore University  Hospital | $28,653 | READM-30-HIP-KNEE-HRRP | 0.866 | higher cost / better quality |
| Brooklyn Hospital Center - Downtown Campus | $27,728 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| Mount Sinai Hospital | $27,622 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| Lenox Hill Hospital | $26,238 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| North Shore University Hospital | $26,043 | READM-30-HIP-KNEE-HRRP | 0.793 | higher cost / better quality |
| Hospital For Special Surgery | $25,507 | READM-30-HIP-KNEE-HRRP | 0.674 | higher cost / better quality |
| Nyu Langone Hospitals | $25,403 | READM-30-HIP-KNEE-HRRP | 0.745 | higher cost / better quality |
| New York-Presbyterian Hospital | $24,852 | READM-30-HIP-KNEE-HRRP | 0.787 | higher cost / better quality |
| Mount Sinai West | $24,680 | READM-30-HIP-KNEE-HRRP | 1.260 | higher cost / worse quality |

### What the data can't tell you

- Why the average Medicare payments vary significantly among these top five New York hospitals.
- The out-of-pocket costs or specific insurance copayments individual patients experienced at these hospitals.
- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.
- 72 hospital(s) have no row for the requested DRG(s) (fewer than 11 discharges are suppressed): BRONXCARE HOSPITAL CENTER, ALBANY MEDICAL CENTER HOSPITAL, JAMAICA HOSPITAL MEDICAL CENTER, NEW YORK COMMUNITY HOSPITAL OF BROOKLYN, INC., VASSAR BROTHERS MEDICAL CENTER, NASSAU UNIVERSITY MEDICAL CENTER, RICHMOND UNIVERSITY MEDICAL CENTER, NEWARK-WAYNE COMMUNITY HOSPITAL....
- 8 figure(s) rest on small samples and are flagged unstable.
- Cost data is calendar 2024; quality measures cover different periods (Apr 2023 to Mar 2025; Jul 2021 to Jun 2024; Jul 2022 to Jun 2024; Oct 2024 to Sep 2025). Compare directionally.

### You could also ask

- What are the patient outcomes and readmission rates for DRG 470 at these five hospitals?
- How do the lengths of stay for DRG 470 compare across these specific providers?

### Sources

- [S1] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=470
- [S2] HCAHPS Patient Survey - Hospital — 2024-10-01 to 2025-09-30 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=hcahps_measure_id&conditions[1][value]=H_STAR_RATING&conditions[1][operator]=%3D&count=true
- [S3] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=COMP_HIP_KNEE&conditions[1][operator]=IN&count=true
- [S4] Complications and Deaths - National Data — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/qqw3-t4ie/0?count=true
- [S5] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=PSI_90&conditions[1][operator]=IN&count=true
- [S6] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=470
- [S7] Hospital Readmissions Reduction Program — 2021-07-01 to 2024-06-30 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/9n3s-kdb3/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_name&conditions[1][value][]=READM-30-HIP-KNEE-HRRP&conditions[1][operator]=IN&count=true
- [S8] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=469
- [S9] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=469

## Q2

**User:** How does Montefiore compare with other Bronx hospitals on heart failure — Medicare payment, 30-day readmissions and mortality?

*19.5 s, rounds 2, audit {'removed_citations': 0, 'flagged_numbers': 0, 'dropped_claims': 0, 'attached_sources': 0, 'repaired': True, 'violations': 0}*

## Montefiore Medical Center has lower Medicare payments, fewer readmissions than expected, and a lower mortality rate than the national rate for heart failure compared to other Bronx hospitals.

Montefiore Medical Center reports an average total payment of $24,163 for DRG 291, ranking #4 of 5 in the cohort [S1]. This payment is +50.7% above the New York average payment of $16,034 and +100.5% above the national average payment of $12,053 [S1][S8].

Among Bronx hospitals in the cohort, average payments range from $23,266 at Bronxcare Hospital Center to $31,893 at Lincoln Medical & Mental Health Center [S1]. New York and national average payments for DRG 291 are $16,034 and $12,053, respectively [S8].

For 30-day heart failure readmissions, Montefiore Medical Center has an excess readmission ratio of 0.935, which is categorized as better than expected [S3]. Other Bronx hospitals show mixed results, with excess readmission ratios ranging from 0.985 at Lincoln Medical & Mental Health Center to 1.187 at Bronxcare Hospital Center [S3].

Montefiore Medical Center records a heart failure mortality score of 5.2%, which is lower than the national rate (direction only: CMS publishes no confidence interval for this measure) [S4][S5]. The national mortality rate for heart failure is 11.1% [S4][S5].

**Cohort ranking by average total payment, DRG 291** (highest payment first; 5 ranked) [S1] [S8]

| # | Hospital | City | Avg total payment | vs NY avg | Medicare discharges | Note |
|---|---|---|---|---|---|---|
| 1 | Lincoln Medical & Mental Health Center | Bronx | $31,893 | +98.9% | 39 | - |
| 2 | Jacobi Medical Center | Bronx | $29,655 | +85.0% | 89 | - |
| 3 | St Barnabas Hospital | Bronx | $27,390 | +70.8% | 27 | - |
| 4 | Montefiore Medical Center (focus) | Bronx | $24,163 | +50.7% | 390 | - |
| 5 | Bronxcare Hospital Center | Bronx | $23,266 | +45.1% | 54 | - |

**Cost versus quality, DRG 291** [S1] [S8] [S3] [S4] [S5] [S7] [S6]

| Hospital | Avg total payment | Quality measure | Value | Group |
|---|---|---|---|---|
| Montefiore Medical Center | $24,163 | READM-30-HF-HRRP | 0.935 | lower cost / better quality |
| Lincoln Medical & Mental Health Center | $31,893 | READM-30-HF-HRRP | 0.985 | higher cost / better quality |
| Jacobi Medical Center | $29,655 | READM-30-HF-HRRP | 1.032 | higher cost / worse quality |
| St Barnabas Hospital | $27,390 | READM-30-HF-HRRP | 1.062 | lower cost / worse quality |
| Bronxcare Hospital Center | $23,266 | READM-30-HF-HRRP | 1.187 | lower cost / worse quality |

### What the data can't tell you

- The data cannot tell you why Montefiore Medical Center's Medicare payments are higher than the New York and national averages.
- The data cannot tell you whether patient outcomes differ by demographic subgroups or specific clinical severities within heart failure cohorts.
- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.
- Cost data is calendar 2024; quality measures cover different periods (Jul 2021 to Jun 2024; Jul 2022 to Jun 2024; Jul 2022 to Jun 2025; Oct 2024 to Sep 2025). Compare directionally.

### You could also ask

- How do heart failure readmission rates and payments change if sibling DRG 292 is included?
- What specific components drive the difference in payment amounts across Bronx hospitals for heart failure?

### Sources

- [S1] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=291
- [S3] Hospital Readmissions Reduction Program — 2021-07-01 to 2024-06-30 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/9n3s-kdb3/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_name&conditions[1][value][]=READM-30-HF-HRRP&conditions[1][operator]=IN&count=true
- [S4] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=MORT_30_HF&conditions[1][operator]=IN&count=true
- [S5] Complications and Deaths - National Data — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/qqw3-t4ie/0?count=true
- [S6] HCAHPS Patient Survey - Hospital — 2024-10-01 to 2025-09-30 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=hcahps_measure_id&conditions[1][value]=H_STAR_RATING&conditions[1][operator]=%3D&count=true
- [S7] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=PSI_90&conditions[1][operator]=IN&count=true
- [S8] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=291

_Audit: the draft was revised once after validation._

## Q3

**User:** Which NY hospitals are the best?

*1.1 s, rounds 0, audit None*

## What specific type of care or hospitals would you like to compare?

- Compare top hospitals for heart surgery in Manhattan
- Find the best-rated hospitals for hip replacement in Brooklyn
- Check quality scores for NYU Langone vs. Mount Sinai
- Look at top-ranked hospitals for cancer care in New York

Reply with one of these, or tell me the hospital, condition and region you care about.

**User:** Hip and knee replacement in New York City, both cost and quality.

*14.2 s, rounds 1, audit {'removed_citations': 0, 'flagged_numbers': 0, 'dropped_claims': 0, 'attached_sources': 0, 'repaired': False, 'violations': 0}*

## Hip and knee replacement costs in New York City vary widely across hospitals and generally exceed national averages, while specific readmission and quality outcomes differ by facility.

For major joint replacement or reattachment of lower extremity with major complication or comorbidity (DRG 469), the cohort volume-weighted mean payment is $39,725, with a median payment of $40,579 [S1]. The New York average payment for DRG 469 is $36,185 and the national average payment is $29,663 [S7].

For lower extremity joint replacement or reattachment without major complication or comorbidity (DRG 470), the cohort volume-weighted mean payment is $25,705 and the median payment is $25,127 [S2]. The New York average payment for DRG 470 is $23,235 and the national average payment is $17,364 [S8].

Montefiore Medical Center reports an average total payment of $31,015 for DRG 470, ranking #1 of 12 in its cohort [S2]. This payment is +33.5% compared with the New York average and +78.6% compared with the national average [S2][S8].

Mount Sinai Hospital has an average total payment of $44,085 for DRG 469 (only 11 Medicare discharges: treat as unstable), which ranks #1 of 4 and is +21.8% compared with the New York average and +48.6% compared with the national average [S1][S7].

Readmission measures for hip and knee procedures show varying performance, with the Hospital for Special Surgery reporting an excess readmission ratio of 0.674, which is better than expected [S3]. Conversely, Mount Sinai West has an excess readmission ratio of 1.260, which is worse than expected across 412 cases [S3].

**Cohort ranking by average total payment, DRG 470** (highest payment first; 12 ranked) [S1] [S7] [S2] [S8]

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

**Cost versus quality, DRG 470** [S1] [S7] [S2] [S8] [S3] [S4] [S5] [S6] [S9]

| Hospital | Avg total payment | Quality measure | Value | Group |
|---|---|---|---|---|
| Montefiore Medical Center | $31,015 | READM-30-HIP-KNEE-HRRP | 0.973 | higher cost / better quality |
| Brooklyn Hospital Center - Downtown Campus | $27,728 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| Mount Sinai Hospital | $27,622 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| New York-Presbyterian Hospital | $24,852 | READM-30-HIP-KNEE-HRRP | 0.787 | lower cost / better quality |
| Mount Sinai West | $24,680 | READM-30-HIP-KNEE-HRRP | 1.260 | lower cost / worse quality |
| New York-Presbyterian/Queens | $23,332 | READM-30-HIP-KNEE-HRRP | 0.914 | lower cost / better quality |
| Lenox Hill Hospital | $26,238 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| Hospital For Special Surgery | $25,507 | READM-30-HIP-KNEE-HRRP | 0.674 | higher cost / better quality |
| Nyu Langone Hospitals | $25,403 | READM-30-HIP-KNEE-HRRP | 0.745 | higher cost / better quality |
| Maimonides Medical Center | $24,051 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |

### What the data can't tell you

- The data cannot tell you the out-of-pocket costs or copayments individual patients will pay for hip and knee replacements.
- The data cannot tell you about patient-reported functional outcomes or pain relief following surgery.
- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.
- 21 hospital(s) have no row for the requested DRG(s) (fewer than 11 discharges are suppressed): BRONXCARE HOSPITAL CENTER, JAMAICA HOSPITAL MEDICAL CENTER, NEW YORK COMMUNITY HOSPITAL OF BROOKLYN, INC., RICHMOND UNIVERSITY MEDICAL CENTER, LINCOLN MEDICAL & MENTAL HEALTH CENTER, NY EYE AND EAR INFIRMARY OF MOUNT SINAI, JACOBI MEDICAL CENTER, ELMHURST HOSPITAL CENTER....
- 7 figure(s) rest on small samples and are flagged unstable.
- Cost data is calendar 2024; quality measures cover different periods (Apr 2023 to Mar 2025; Jul 2021 to Jun 2024; Jul 2022 to Jun 2024; Oct 2024 to Sep 2025). Compare directionally.

### You could also ask

- What are the specific patient-reported functional improvement scores for hip and knee replacements at these New York City hospitals?
- How do complication rates other than readmissions compare across all hospitals performing hip and knee replacements in New York City?
- What are the median out-of-pocket costs for Medicare beneficiaries receiving hip and knee replacements at these facilities?

### Sources

- [S1] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=469
- [S2] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=470
- [S3] Hospital Readmissions Reduction Program — 2021-07-01 to 2024-06-30 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/9n3s-kdb3/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_name&conditions[1][value][]=READM-30-HIP-KNEE-HRRP&conditions[1][operator]=IN&count=true
- [S4] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=PSI_90&conditions[1][value][]=PSI_12&conditions[1][value][]=PSI_09&conditions[1][operator]=IN&count=true
- [S5] Complications and Deaths - National Data — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/qqw3-t4ie/0?count=true
- [S6] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=COMP_HIP_KNEE&conditions[1][operator]=IN&count=true
- [S7] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=469
- [S8] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=470
- [S9] HCAHPS Patient Survey - Hospital — 2024-10-01 to 2025-09-30 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=hcahps_measure_id&conditions[1][value]=H_STAR_RATING&conditions[1][operator]=%3D&count=true

## More 1

**User:** What will I pay out of pocket for a knee replacement at NYU?

*11.6 s, rounds 1, audit {'removed_citations': 0, 'flagged_numbers': 0, 'dropped_claims': 0, 'attached_sources': 8, 'repaired': False, 'violations': 0}*

## The provided data does not show out-of-pocket costs for a knee replacement at NYU Langone Hospitals, but it does list average Medicare fee-for-service payments.

For knee replacement procedures, NYU Langone Hospitals has an average total payment of $38,267 for DRG 469 and $25,403 for DRG 470. [S1][S2]

Compared to state and national averages for DRG 469, NYU Langone Hospitals's average payment of $38,267 compares to a New York average payment of $36,185 and a national average payment of $29,663. [S1][S8]

For DRG 470, NYU Langone Hospitals's average payment of $25,403 compares to a New York average payment of $23,235 and a national average payment of $17,364. [S2][S9]

The submitted charge to payment ratio at NYU Langone Hospitals is 7.2x for DRG 469 and 8.8x for DRG 470, with the caveat that charges are list prices, not what anyone pays. [S1][S2]

**Cohort ranking by average total payment, DRG 470** (highest payment first; 7 ranked) [S1] [S8] [S2] [S9]

| # | Hospital | City | Avg total payment | vs NY avg | Medicare discharges | Note |
|---|---|---|---|---|---|---|
| 1 | Mount Sinai Hospital | New York | $27,622 | +18.9% | 158 | - |
| 2 | Lenox Hill Hospital | New York | $26,238 | +12.9% | 136 | - |
| 3 | Hospital For Special Surgery | New York | $25,507 | +9.8% | 1332 | - |
| 4 | Nyu Langone Hospitals (focus) | New York | $25,403 | +9.3% | 940 | - |
| 5 | New York-Presbyterian Hospital | New York | $24,852 | +7.0% | 304 | - |
| 6 | Mount Sinai West | New York | $24,680 | +6.2% | 99 | - |
| 7 | Mount Sinai Beth Israel | New York | $23,380 | +0.6% | 11 | small sample |

**Cost versus quality, DRG 470** [S1] [S8] [S2] [S9] [S6] [S4] [S5] [S7] [S3]

| Hospital | Avg total payment | Quality measure | Value | Group |
|---|---|---|---|---|
| Nyu Langone Hospitals | $25,403 | READM-30-HIP-KNEE-HRRP | 0.745 | lower cost / better quality |
| Mount Sinai Hospital | $27,622 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| Lenox Hill Hospital | $26,238 | READM-30-HIP-KNEE-HRRP | - | insufficient data (fewer than 25 readmission cases) |
| Hospital For Special Surgery | $25,507 | READM-30-HIP-KNEE-HRRP | 0.674 | higher cost / better quality |
| New York-Presbyterian Hospital | $24,852 | READM-30-HIP-KNEE-HRRP | 0.787 | lower cost / better quality |
| Mount Sinai West | $24,680 | READM-30-HIP-KNEE-HRRP | 1.260 | lower cost / worse quality |
| Mount Sinai Beth Israel | $23,380 | READM-30-HIP-KNEE-HRRP | - | insufficient data (no readmission ratio) |

### What the data can't tell you

- What an individual patient will pay out of pocket, as the data only shows average Medicare fee-for-service payments rather than individual copays, deductibles, or private insurance rates.
- What patient-specific out-of-pocket expenses would be for non-Medicare or uninsured patients.
- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.
- 4 hospital(s) have no row for the requested DRG(s) (fewer than 11 discharges are suppressed): NY EYE AND EAR INFIRMARY OF MOUNT SINAI, METROPOLITAN HOSPITAL CENTER, BELLEVUE HOSPITAL CENTER, HARLEM HOSPITAL CENTER.
- 5 figure(s) rest on small samples and are flagged unstable.
- Cost data is calendar 2024; quality measures cover different periods (Apr 2023 to Mar 2025; Jul 2021 to Jun 2024; Jul 2022 to Jun 2024; Oct 2024 to Sep 2025). Compare directionally.

### You could also ask

- What are the specific copay and deductible requirements for my specific insurance plan at NYU Langone Hospitals?
- How do NYU Langone Hospitals's complication rates for hip and knee surgeries compare nationally?

### Sources

- [S1] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=469
- [S2] Medicare Inpatient Hospitals by Provider and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/690ddc6c-2767-4618-b277-420ffb2bf27c/data?filter[Rndrng_Prvdr_State_Abrvtn]=NY&filter[DRG_Cd]=470
- [S3] HCAHPS Patient Survey - Hospital — 2024-10-01 to 2025-09-30 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/dgck-syfz/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=hcahps_measure_id&conditions[1][value]=H_STAR_RATING&conditions[1][operator]=%3D&count=true
- [S4] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=PSI_09&conditions[1][value][]=PSI_12&conditions[1][value][]=PSI_90&conditions[1][operator]=IN&count=true
- [S5] Complications and Deaths - National Data — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/qqw3-t4ie/0?count=true
- [S6] Hospital Readmissions Reduction Program — 2021-07-01 to 2024-06-30 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/9n3s-kdb3/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_name&conditions[1][value][]=READM-30-HIP-KNEE-HRRP&conditions[1][operator]=IN&count=true
- [S7] Complications and Deaths - Hospital — 2023-04-01 to 2025-03-31 — retrieved 2026-11-05 — https://data.cms.gov/provider-data/api/1/datastore/query/ynj2-r877/0?conditions[0][property]=state&conditions[0][value]=NY&conditions[0][operator]=%3D&conditions[1][property]=measure_id&conditions[1][value][]=COMP_HIP_KNEE&conditions[1][operator]=IN&count=true
- [S8] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=469
- [S9] Medicare Inpatient Hospitals by Geography and Service — CY2024 — retrieved 2026-11-05 — https://data.cms.gov/data-api/v1/dataset/2941ab09-8cee-49d8-9703-f3c5b854e388/data?filter[DRG_Cd]=470

## More 2

**User:** Cheapest knee replacement in Boston?

*3.9 s, rounds 0, audit None*

## This question is outside what the data can answer

Boston is outside New York State, so hospital cost and quality data is not available in our New York Medicare database.

Could not resolve:
- Boston: outside NY scope

Hospital Atlas covers New York hospitals using CMS Medicare data: inpatient payments by DRG (CY2024), readmission and mortality measures, patient safety indicators and patient-survey star ratings.

### What the data can't tell you

- Cost figures are Medicare fee-for-service inpatient payments for calendar year 2024; commercial insurance prices and what patients pay out of pocket are not in this data.
- Hospital charges are list prices, not what anyone pays; CMS suppresses hospital-DRG rows with fewer than 11 discharges.
- Quality measures cover periods that differ from the payment year, and the data cannot show whether a procedure was right for an individual patient.

### Sources

No dataset was queried for this answer.
