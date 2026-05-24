# v1.x UI Workflow Report

## Summary

- Session: `plan-832a931b`
- Requirement: `Validate the Agent Team Console workflow`
- Linked run: `run-20d4aaea`
- Final session status: `accepted`
- Validation date: 2026-05-24

## Workflow

1. Created a real planning session with `team start`.
2. Executed the approved plan with `team execute --mode success_first`.
3. Started the local Agent Team Console on `127.0.0.1:8765`.
4. Opened the console in the in-app browser and verified the operator surface.

## Browser Checks

- Console title rendered: `Agent 团队控制台`
- Session text was visible for `Validate the Agent Team Console workflow`
- Accepted/completed state was visible
- Governance summary mounted and populated
- Operator summary mounted and populated
- Plan tree mounted with nodes
- Jobs area mounted
- Job action mount existed for send/cancel controls

## Result

The real workflow completed successfully. The Console could display the session, execution state, governance information, operator summary, plan tree, job surface, and job action controls without API or rendering errors.

## Follow-Up Notes

- The current smoke validation confirms core operator surfaces and real workflow visibility.
- Deeper visual polish can be handled separately after CLI output format and stream behavior are stabilized.
