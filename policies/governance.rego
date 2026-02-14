package gov

import rego.v1

default allow := true

findings := input.findings
exceptions := input.exceptions

# Parse "YYYY-MM-DD" into nanoseconds at midnight UTC by appending RFC3339 time.
parse_day_ns(d) := ns if {
  ts := sprintf("%sT00:00:00Z", [d])
  ns := time.parse_rfc3339_ns(ts)
}

today_ns := time.now_ns()

has_valid_exception(model) if {
  some i
  e := exceptions[i]
  lower(e.model) == lower(model)
  e.expiry != ""
  parse_day_ns(e.expiry) >= today_ns
}

is_gold_tier(layer) if { lower(layer) == "gold" }
is_gold_tier(layer) if { lower(layer) == "gold_restricted" }

deny contains msg if {
  some i
  f := findings[i]
  f.type == "pii_detected"
  lower(f.layer) == "gold"
  msg := sprintf("PII detected in GOLD model '%s' columns=%v", [f.model, f.details.columns])
}

deny contains msg if {
  some i
  f := findings[i]
  f.type == "pii_detected"
  lower(f.layer) == "gold_restricted"
  not has_valid_exception(f.model)
  msg := sprintf("PII in GOLD_RESTRICTED model '%s' requires a non-expired approval in standards/exceptions.yml", [f.model])
}

deny contains msg if {
  some i
  f := findings[i]
  f.type == "missing_meta"
  is_gold_tier(f.layer)
  msg := sprintf("Missing required meta on model '%s': %v", [f.model, f.details.missing])
}

allow := count(deny) == 0
reasons := [m | m := deny[_]]
