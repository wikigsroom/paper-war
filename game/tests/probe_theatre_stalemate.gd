extends SceneTree
const Store=preload("res://scripts/data_store.gd")
const Simulation=preload("res://scripts/battle_sim.gd")
func _init():
	var db=Store.new();var rows: Array=[]
	for index in [50,56]:
		var sim=Simulation.new(db);sim.start(db.campaign[index]);sim.ai_enabled=[true,true]
		for tick in range(60*540):
			sim.tick(1.0/60.0);sim.drain_events()
			if sim.winner!=-2:break
		var actors: Array=[]
		for u in sim.units:
			if db.balance.units[u.id].get("economy",false):continue
			actors.append({"id":u.id,"side":u.side,"hp":u.hp,"edge":u.edge,"s":u.s,"x":u.x,"y":u.y,"anim":u.anim,"target":u.target,"statuses":u.statuses})
		rows.append({"map":db.campaign[index].map,"time":sim.time,"winner":sim.winner,"actors":actors,"players":sim.players,"stats":sim.stats,"bases":sim.bases})
		print("STALEMATE ",db.campaign[index].map," winner ",sim.winner," units ",actors.size())
	var file=FileAccess.open("res://tests/theatre-stalemate-probe.json",FileAccess.WRITE);file.store_string(JSON.stringify(rows,"\t"));file.close();quit()
