# Optional bounded coaching — coaching-session/v1

Normal requests produce the requested artifact directly. Use this optional practice mode only when the person asks to work through the task together; it adds no tool, provider, standing agent or dependency. The person can say “just finish” to end teaching and return to already authorized artifact work. That does not expand execution authority.

Name the person or role and real job, an observable goal, the starting artifact and a preserved baseline. Agree on allowed changes, available time, what must survive, and one domain-specific feedback checkpoint. Default to at most two practice rounds unless the person chooses a smaller cap. Technical retries are separate from practice rounds.

The speaker states the idea and audience, chooses one rehearsal change, and checks the argument; HTML/export conformance remains a separate software check.

Make one bounded attempt, ask for that specific feedback, and record actual reasons, useful changes and regressions. Keep/revert is a human-reviewed proposal; act within the authorization already given and do not infer permission for a new external action. If the person is unavailable, leave assumptions or questions rather than simulating feedback, learning or growth.

Stop at the goal, a user exit at any time, the agreed cap, stalled/no meaningful gain, missing authority/input, or a critical failed/unknown condition. Stop teaching without abandoning useful authorized work or turning an unfinished task into an automatic recurring loop.

A private task trace is optional and saved nowhere by default. Save it only to an explicitly chosen location with a retention choice. Never copy a private trace into the skill, public examples or a shared knowledge store implicitly. This skill has no memory or telemetry service.

A documented walkthrough is only Claimed. Seen or Repeated evidence requires authentic outside use, not authored examples, teammate reviews or agent fixtures. No stronger usefulness claim is created by this guide.

A minimal optional note (documentation convention, not a runtime API):

```json
{
  "contract": "coaching-session/v1",
  "user_role": "fictional example author",
  "job": "one selected writing task",
  "goal": "one observable improvement",
  "baseline": "chosen local draft",
  "practice_round_cap": 2,
  "preserve": [
    "approved facts",
    "privacy boundary"
  ],
  "checkpoint": "The speaker states the idea and audience, chooses one rehearsal change, and checks the argument; HTML/export conformance remains a separate software check.",
  "decision": "pending human review",
  "recording": {
    "enabled": false,
    "location": null,
    "retention": null
  },
  "evidence_level": "Claimed"
}
```
