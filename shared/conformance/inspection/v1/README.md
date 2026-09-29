# Range inspection corpus v1

This separate, synthetic corpus specifies the additive range-inspection diagnostic boundary. It is not codec corpus v1 and does not change its schema, fixtures, npm exports, or comparison rules. `fixtures.json` is deliberately literal synthetic byte data; a candidate which is structurally valid is not proof of a device's physical unit, selected profile, conformance, or permission to issue a control.

The selected profile is always caller-owned. A selected decode can be malformed while another candidate is valid; implementations must report that fact without automatic selection. Runners compare every fixture's selected profile, observed and expected lengths, selected status, and candidate profile/status/raw values. `v1` names this inspection comparison contract, not an FTMS or package version.

There are exactly **9 cases**, each with a complete literal `expected` report.
Both runners compare the entire report, including top-level `value`, candidate
order, all raw value fields and explicit nulls. For resistance, candidate order
is `uint8Whole`, then `signed16Tenths`; other kinds have one canonical candidate.
The C adapter maps kind/profile/status enums to contract strings and represents
non-valid values as null. In the native API, `status` discriminates whether the
zero-initialized value storage is meaningful. Tests must not treat it as a valid
zero range. C runner without a driver fails rather than silently skipping.
