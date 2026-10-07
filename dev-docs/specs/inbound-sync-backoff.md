# Inbound synchronization during a server outage

Only one inbound polling pass may run at a time. A slow download cannot start
another copy of the same batch at the next thirty-second tick.

GET and HEAD requests retry transient transport failures (including timeout)
and HTTP 5xx at most twice, with one- and two-second exponential delays and
twenty-percent jitter. Mutations and authorization failures are never retried.

A transient download failure stops the remaining file batch. Completed file
hashes survive, but the share watermark does not advance until the batch
finishes. Failed servers cool down for thirty seconds, doubling after each
failure up to five minutes, with jitter. A successful pass resets the cooldown.
Other servers continue polling during that cooldown.
