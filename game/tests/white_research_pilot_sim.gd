extends "res://tests/white_field_pilot_sim.gd"
# Explicit paid opening experiment; normal production and visibility remain intact.
func start(options: Dictionary):
	super.start(options)
	if options.get("experimental_white_early_research",false):
		for side in [0,1]:
			if players[side].faction=="bai":
				var result: Dictionary=request(side,"research",{"id":"tech.bai.unit.scribe"})
				assert(result.ok,"Paid experimental research must be accepted")
