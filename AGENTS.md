# Agent rules

- Read `IMPLEMENTATION_PLAN.md` before changing architecture.
- Keep Telegram code in `adapters/telegram`, persistence in `infrastructure`, and media algorithms in plugins/services.
- Do not commit secrets, `/data`, generated media, or user inputs.
- Verify every implemented stage with the relevant offline checks; list live Telegram checks that could not run.
- Record substantial deviations from the implementation plan in `docs/decisions/`.
