# Semantic correction — V3-LANL-STRUCT-001 / V3-LANL-REGSCALE-001

## Defect found before multi-day validation

The frozen `LANL_STRUCTURE_PROTOCOL.md` states that `H_login` represents person-associated login activity. Inspection of the actual upstream trajectory builder showed that the retained columns `logon_success_4624` and `logon_failure_4625` were incremented for every EventID 4624/4625 on a canonical host, without requiring a de-identified person account.

Therefore:

- the earlier day-02 `H_login` channel is a **generic login-event channel**;
- its predictive scores cannot be described as person-associated human evidence;
- machine/system login events may contribute to that channel;
- the P_process and T_network definitions are unaffected by this semantic defect;
- the earlier density/regularization-scale diagnostic remains useful as an engineering diagnostic, but any interpretation specifically attributing its H edges to human activity is withdrawn.

No earlier result file is deleted or rewritten.

## Forward correction

`V3-LANL-MULTIDAY-001` defines `H_person_login` as EventID 4624/4625 **and** `UserName`/`SubjectUserName` matching `^User[0-9]+$`. Machine accounts ending `$`, named/system accounts, and missing usernames cannot activate H.

Day 02 is rerun under the corrected definition as development-only. Days 03–05 use the corrected definition as out-of-development validation.

This correction was frozen before inspecting any day-03/day-04/day-05 model result.
