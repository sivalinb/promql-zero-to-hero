# Learning guide: from a number to an investigation

The foundations course (`foundations-v2`) assumes no PromQL or SQL knowledge. Each concept has a definition, analogy, five-step animation, worked explanation, optional SQL bridge, vocabulary, an ungraded prediction question, and a takeaway. The learner controls playback and can review previous concepts.

## The four stages

- **Levels 0–2: understand measurements.** Samples and series, counters and gauges, then observations and cumulative histogram buckets.
- **Levels 3–5: read and calculate.** Select series, understand a time window, convert counter totals into speed, and compare over-time functions.
- **Levels 6–8: combine and interpret.** Reduce the right axis, preserve labels, handle missing data, and estimate percentiles.
- **Levels 9–10: investigate.** Compare history, reuse queries, understand alerts and cardinality, then explain reliability with aligned evidence.

## Complete concept map

### Level 0 · What is a time series?

1. **A number needs a meaning** — Always identify what is measured, its unit, and the time before interpreting a number.
2. **Samples become a time series** — More timestamps add history to a series. They do not change its identity.
3. **Labels tell similar measurements apart** — Same metric name plus the same full label set means the same series.

Badge: **Measurement Explorer**. Practical challenge: Return every active-session series at the evaluation time.

### Level 1 · Counters and gauges

1. **Counter: how many so far?** — A counter value is a cumulative total, not a per-second rate.
2. **Gauge: how much right now?** — A normal decrease in a gauge is not a counter reset.
3. **A restart is different from a falling gauge** — The metric’s meaning determines the function; an increasing-looking line alone is not enough.

Badge: **Metric Type Detective**. Practical challenge: Return all request-counter series at the evaluation time.

### Level 2 · Histograms, one observation at a time

1. **Why one average is not the whole story** — A histogram describes many measured events; one average hides the shape of their distribution.
2. **A bucket is a counting rule** — A bucket boundary is a measured-value limit; its stored value is a count.
3. **Prometheus buckets are cumulative** — One observation may increment several buckets. +Inf already counts all observations.
4. **Read _bucket, _count, and _sum** — _count counts observations; _sum adds measured values; _sum/_count gives a mean, not a percentile.

Badge: **Bucket Builder**. Practical challenge: Return all classic request-duration bucket series.

### Level 3 · Read your first PromQL expressions

1. **One moment versus a window** — Metric types describe meaning. Query result types describe the shape of an expression’s result.
2. **Filter labels before doing arithmetic** — Choose a population before calculating a statistic about it.
3. **A window has exact boundaries** — A time window controls which samples are inputs; it does not guarantee a sample count.

Badge: **Query Reader**. Practical challenge: Select the availability series for the API service only.

### Level 4 · From totals to speed

1. **Change divided by time is a speed** — Rate has units of events per second. It measures change, not the size of the counter.
2. **rate() and irate() look at different evidence** — irate means latest-two-sample rate, not “rate divided by the window size”.
3. **Handle resets before combining counters** — Calculate rate on original counter series before aggregating their results.
4. **increase() answers “how many during this window?”** — increase estimates events in the window; it can be fractional because boundaries are estimated.

Badge: **Rate Reasoner**. Practical challenge: Calculate the recent per-second rate for each original request-counter series using a five-minute window.

### Level 5 · Calculate over time

1. **sum_over_time() adds samples, not new events** — sum_over_time adds samples within a series. It does not count counter events or unique people.
2. **avg_over_time() describes the average sample** — avg_over_time is an equal-sample average, not a per-second counter rate.
3. **Minimum, maximum, and sample count** — A maximum is an observed peak. A sample count is not an event count.
4. **Gauge change is not counter rate** — Choose rate for counters; delta and deriv preserve meaningful upward or downward gauge changes.

Badge: **Window Thinker**. Practical challenge: Sum the queue-depth samples over the last five minutes, separately for each original series.

### Level 6 · Combine series without losing meaning

1. **sum() and sum_over_time() use different axes** — sum reduces across series; sum_over_time reduces across time within each series.
2. **by() and without() define the remaining groups** — Grouping controls both which values combine and which labels survive.
3. **Build ratios from the same population** — Combine counts or rates before dividing; do not average percentages from unequal populations.

Badge: **Aggregation Guide**. Practical challenge: Calculate the five-minute request rate per service, handling each original counter before aggregation.

### Level 7 · Match labels and handle missing data

1. **Arithmetic needs matching series** — Labels define arithmetic pairs; result ordering does not.
2. **group_left() allows many-to-one matching** — group_left permits a many-to-one match; the one side must still be unique.
3. **Missing is different from zero** — No observation is not the same evidence as an observed zero.

Badge: **Label Matchmaker**. Practical challenge: Return total active sessions per service, enriched with the owning team.

### Level 8 · From buckets to latency percentiles

1. **What p95 actually means** — A histogram percentile is estimated from bucket boundaries and counts.
2. **Combine bucket evidence, not instance p95 values** — For classic histogram aggregation, preserve le until histogram_quantile consumes the buckets.
3. **Classic histograms, native histograms, and summaries** — Classic buckets, native histogram samples, and summary quantiles require different query handling.

Badge: **Distribution Detective**. Practical challenge: Estimate p95 request duration per service from the classic histogram.

### Level 9 · Build trustworthy signals

1. **offset changes which history you look at** — offset changes the reference time of the evidence, not the physical timestamps stored in the database.
2. **Subqueries and recording rules reuse calculations** — A subquery resolution controls derived evaluations, not how often Prometheus scrapes the source.
3. **An alert window is not an alert hold timer** — The range duration selects data; the for duration tracks persistence of the alert condition.
4. **More label combinations mean more series** — Each distinct label combination is a separate series; aggregating later does not undo ingestion cost.

Badge: **Signal Engineer**. Practical challenge: Count the currently failing, present targets for each service. Healthy services should be absent.

### Level 10 · Explain an incident with evidence

1. **Read traffic, errors, latency, and availability together** — Align populations and windows, then combine signals; one correlation does not establish a cause.
2. **An SLO defines the reliability goal** — An SLO needs a good-event definition, a population, a target, and an assessment period.
3. **Burn rate turns an error fraction into budget pressure** — Burn rate is a ratio of fractions. Remaining time requires additional assumptions.

Badge: **PromQL Hero**. Practical challenge: Find services whose five-minute error fraction exceeds 5%. Keep the error fraction as the value; healthy services must disappear. Your query must work in both normal traffic and the incident.

## What the animations calculate

| Worked example | Assumptions and result |
|---|---|
| Rate vs. irate | Counter samples 100, 110, 120, 130, 190 at 0, 15, 30, 45, 60 seconds. A 75s window ending at 60s includes all five. Rate = 1.5 requests/s after extrapolation for this setup; irate = 4 requests/s. |
| Increase | The same 75s window estimates 1.5 × 75 = 112.5 requests. Stored first-to-last change is 90 over 60s; those are different quantities. |
| Counter reset | 100, 115, 5, 20, 35 contributes +15, +5, +15, +15 = 50 observed events. Unobserved pre-restart activity cannot be reconstructed. |
| Over time | The selected gauge samples 2, 4, 6 produce sum 12, average 4, minimum 2, maximum 6, count 3. Sample sums are neither unique people nor automatically time integrals. |
| Across series | At the final time, instances a and b are 6 and 5; sum is 11. Across their separate histories, sums are 12 and 9. |
| Histogram | Durations 0.12, 0.42, 0.8, 1.4s produce cumulative counts 0, 2, 3, 4 at bounds 0.1, 0.5, 1, +Inf. |
| Percentile | 100 observations with cumulative counts 20, 60, 90, 100, 100 at 0.1, 0.5, 1, 2, +Inf. The 95th rank interpolates to 1.5s in the 1–2s bucket. |

Animations use small, illustrative teaching data. The real-query lab uses a separate, richer reproducible fixture. The JavaScript arithmetic is not a replacement PromQL engine; runnable queries are evaluated by Prometheus.

## Assessment and saved progress

Reading marks are self-reported and do not award XP. A level quiz samples five questions from its seven-question bank. All answers receive explanations after submission. A first pass of at least 80% plus the practical check in both scenarios awards one badge and 100 XP. Repeated submissions are idempotent; an attempted future level is rejected by the server.

Version 1 completion and attempt tables remain untouched. Version 2 uses `completions_v2`, `attempts_v2`, and `lesson_reads_v2`. Old attempts cannot grade new questions, old badges cannot accidentally unlock unrelated new levels, and old achievements remain visible under their original names. Profile recovery and conversation history are preserved.

## Sources

Metric types and query semantics were checked against the official [metric types](https://prometheus.io/docs/concepts/metric_types/), [query basics](https://prometheus.io/docs/prometheus/latest/querying/basics/), [functions](https://prometheus.io/docs/prometheus/latest/querying/functions/), and [histogram guidance](https://prometheus.io/docs/practices/histograms/). Each level links to its sources in the app.
