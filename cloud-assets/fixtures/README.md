# Synthetic collector snapshot

`demo-snapshot.json` uses the same fields as `collector.py` output. It is fabricated
for testing, not a record fetched from AWS. Its `limitations` identify that fact
and all names use a `demo-` prefix.

Included scenarios:

- Four EC2 instances: low CPU, high CPU, stopped with no CPU samples, and a new
  instance with missing metrics.
- Five gp3 EBS volumes: three attached and two unattached (50 and 200 GiB).
- A 14-day metric window, with no RAM, pricing, billing or RDS data.

The uploaded test copy lives under `testing/synthetic/` in the configured bucket,
separate from collector snapshots and existing objects. The backend's local
`S3_OBJECT_KEY` selects the specific uploaded copy. Restart the backend after
changing configuration. The previous object key is preserved as a comment in the
local `.env`; restore it when you want to stop using synthetic data.

Suggested questions:

- Which demo EC2 instances need further utilization review?
- Which volumes are unattached, and what should I verify before deleting them?
- Which resources lack metrics?
- Can exact cost savings be calculated from this snapshot? (No: pricing and
  billing data are absent.)

Answers should explicitly recognize the data as synthetic and avoid assuming
that low CPU alone proves a resource can safely be downsized.
