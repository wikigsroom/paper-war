extends SceneTree
const Data=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
const Commands=preload("res://scripts/network_commands.gd")
var failures: Array=[]
var checks: int=0
func verify(ok: bool,note: String):
	checks+=1
	if not ok:failures.append(note)
func run():
	var s=Simulation.new(Data.new())
	s.start({"map":"map.01.01","faction":"yin","enemy":"mo","starting_gold":300,"full_tech":true})
	s.ai_enabled=[false,false]
	var p={"sequence":1,"kind":"recruit","args":{"id":"unit.yin.axe"}}
	verify(Commands.submit(s,0,p).ok and s.players[0].gold==255,"normal command pays authority cost")
	verify(not Commands.submit(s,0,p).ok and s.players[0].gold==255,"replay cannot charge or recruit twice")
	p.sequence=2;p["side"]=1
	verify(not Commands.submit(s,0,p).ok,"forged side rejected")
	p.erase("side");p.args["gold"]=9999
	verify(not Commands.submit(s,0,p).ok,"state mutation rejected")
	verify(s.players[0].sequence==1,"malformed payload does not consume sequence")
	verify(not Commands.submit(s,3,p).ok,"unassigned side rejected before indexing")
	p={"sequence":2,"kind":"cast","args":{"id":"spell.yin.lightning","x":INF,"y":0}}
	verify(not Commands.submit(s,0,p).ok,"infinite coordinates rejected")
	p.args.x=1;p.args.y=NAN
	verify(not Commands.submit(s,0,p).ok,"NaN rejected")
	p={"sequence":2,"kind":"recruit","args":{"id":"unit.mo.giant"}}
	verify(not Commands.submit(s,0,p).ok,"enemy roster rejected by simulation")
	p={"sequence":3,"kind":"cancel_queue","args":{"index":0,"id":"unit.yin.axe","queue_revision":"1"}}
	verify(not Commands.submit(s,0,p).ok and s.players[0].sequence==2,"queue version rejects wrong transport type")
	p.args.queue_revision=0
	verify(not Commands.submit(s,0,p).ok and s.players[0].queue.size()==1 and s.players[0].gold==255,"transport preserves stale queue protection")
	p.sequence=4;p.args.queue_revision=s.players[0].queue_revision
	verify(Commands.submit(s,0,p).ok and s.players[0].queue.is_empty() and s.players[0].gold==300,"transport accepts fresh cancellation and exact refund")
	print("NETWORK_COMMANDS: ",checks," checks; failures=",failures)
	quit(0 if failures.is_empty() else 1)
func _initialize():call_deferred("run")
