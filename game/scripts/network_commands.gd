extends RefCounted
# The transport assigns side; the payload cannot select its player.
const SCHEMAS={"recruit":{"id":TYPE_STRING},"research":{"id":TYPE_STRING},"build":{"id":TYPE_STRING,"slot":TYPE_INT},"cast":{"id":TYPE_STRING,"x":TYPE_FLOAT,"y":TYPE_FLOAT,"target":TYPE_INT},"route":{"node":TYPE_STRING,"edge":TYPE_STRING},"mine_priority":{"mine":TYPE_STRING},"cancel_queue":{"index":TYPE_INT,"id":TYPE_STRING,"queue_revision":TYPE_INT}}
static func submit(sim,assigned_side: int,payload: Dictionary) -> Dictionary:
	if assigned_side not in [0,1]:return reject("invalid_side")
	if payload.size()!=3 or not payload.has_all(["sequence","kind","args"]):return reject("invalid_envelope")
	if typeof(payload.sequence)!=TYPE_INT or payload.sequence<=0 or payload.sequence>2147483647:return reject("invalid_sequence")
	if typeof(payload.kind)!=TYPE_STRING or not SCHEMAS.has(payload.kind) or typeof(payload.args)!=TYPE_DICTIONARY:return reject("invalid_command")
	var schema: Dictionary=SCHEMAS[payload.kind]
	for key in payload.args:
		if not schema.has(key):return reject("invalid_argument")
		var value=payload.args[key]
		if schema[key]==TYPE_FLOAT:
			if typeof(value) not in [TYPE_INT,TYPE_FLOAT] or not is_finite(float(value)) or absf(float(value))>10000:return reject("invalid_coordinate")
		elif typeof(value)!=schema[key]:return reject("invalid_type")
		if typeof(value)==TYPE_STRING and value.length()>128:return reject("invalid_string")
	if payload.kind in ["recruit","research","build","cast"] and not payload.args.has("id"):return reject("missing_id")
	if payload.kind=="route" and not payload.args.has_all(["node","edge"]):return reject("missing_route")
	return sim.command(assigned_side,payload.sequence,payload.kind,payload.args)
static func reject(reason: String) -> Dictionary:
	return {"ok":false,"error":reason}
