extends SceneTree
# Normal App entry and both complete AI sides. Only the west autoplayer is enabled
# for observation; no free unlocks, units, resources, HP or positional fixtures.
const App=preload("res://scripts/main.gd")
var app
var folder: String
var checks: Array=[]
var captures: Array=[]
var investments: Array=[]
var spent: Array=[0.0,0.0]
var first: Dictionary={}
var first_hit: Dictionary={}
var east_first_order: float=-1
var next_unit_before_order: bool=false
func _initialize():call_deferred("run")
func verify(value: bool,note: String,details: Dictionary={}):
	checks.append({"passed":value,"name":note,"details":details})
func capture(name_value: String,own_uid: int=0):
	var owned: Dictionary=app.sim.actor(own_uid)
	if not owned.is_empty() and owned.side==0 and owned.hp>0:
		# Camera observation is limited to an owned living actor.
		app.view.follow_front=false;app.view.target_camera=owned.x
		app.view.direct_pan=true;app.view.update(0)
	else:
		app.view.follow_front=true;app.view.update(0)
	app.update_hud();app.view.queue_redraw()
	await process_frame;await process_frame;await RenderingServer.frame_post_draw
	var path: String=folder+"/"+name_value+".png"
	verify(root.get_texture().get_image().save_png(path)==OK,"save "+name_value)
	captures.append({"path":path,"sha256":FileAccess.get_sha256(path),"simulation_time":app.sim.time,
		"owned_focus_uid":own_uid,"camera_x":app.view.camera_x})
func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1]
	DirAccess.make_dir_recursive_absolute(folder)
	app=App.new();root.add_child(app);await process_frame;app.set_process(false)
	app.audio.silent=true;app.audio.set_background(true);app.mode="skirmish"
	var enemy: String=args[args.find("--enemy")+1] if args.has("--enemy") else "yin"
	app.start_battle({"title":"遭遇战","map":"map.01.04","faction":"yin","enemy":enemy,"seed":137,
		"difficulty":1,"ai_style":"counter","starting_gold":300,"enemy_starting_gold":300,"full_tech":false,"win":"destroy_base"})
	app.accumulator=-100000;app.sim.ai_enabled=[true,true]
	verify(not app.sim.config.get("full_tech",true),"normal entry does not unlock full technology")
	verify(app.sim.config.get("ai_warmup",4)==4,"normal enemy uses four-second warmup")
	for side in [0,1]:
		verify(app.sim.players[side].roster==app.db.all_unit_ids(app.sim.players[side].faction),"App preserves six legal researchable faction units / "+str(side))
		verify(app.sim.players[side].gold==300,"normal starting treasury / "+str(side))
	app.sim.drain_events();await capture("01-normal-opening")
	for step in range(240*60):
		var focus_actor: Dictionary=app.sim.actor(int(first.get("uid",0)))
		if not focus_actor.is_empty() and focus_actor.side==0 and focus_actor.hp>0:
			app.view.target_camera=focus_actor.x;app.view.update(0)
		app.sim.tick(1.0/60)
		var emitted: Array=app.sim.drain_events()
		var shot: String=""
		for event in emitted:
			var side: int=int(event.get("side",-1))
			if event.kind in ["recruit","research_start","build"]:
				var cost: float=0
				if event.kind=="recruit":cost=float(app.db.balance.units[event.id].gold)
				elif event.kind=="research_start":cost=float(app.db.tech(event.id).gold)
				else:cost=float(app.db.balance.buildings[event.id].gold)
				spent[side]+=cost
				investments.append({"side":side,"kind":event.kind,"id":event.id,"time":event.time,"gold_spent":cost})
				if side==1 and east_first_order<0:east_first_order=event.time
			if event.kind=="research_start" and side==0:
				var study: Dictionary=app.db.tech(event.id)
				if str(study.grant).begins_with("unit."):
					if first.is_empty():
						first={"tech":study.id,"grant":study.grant,"research_price":study.gold,"unit_price":app.db.balance.units[study.grant].gold,"research_started":event.time}
						shot="02-paid-research"
					elif not first.has("ordered") and study.grant!=first.grant:next_unit_before_order=true
			if not first.is_empty():
				if event.kind=="research_done" and side==0 and event.id==first.grant:
					first["completed"]=event.time;shot="03-research-complete"
				if event.kind=="recruit" and side==0 and event.id==first.grant and not first.has("ordered"):
					first["ordered"]=event.time
				if event.kind=="spawn" and side==0 and event.id==first.grant and event.get("origin","")=="production" and not first.has("uid"):
					first["uid"]=event.uid;first["born"]=event.time;shot="04-first-paid-production"
				if event.kind=="hit" and first.has("uid") and event.get("source_uid",0)==first.uid and event.get("attacker_side",-1)==0 and float(event.get("amount",0))>0:
					first_hit=event.duplicate(true);shot="05-first-unit-impact"
			if app.sim.event_visible(0,event):app.view.on_event(event)
		app.view.update(1.0/60,false)
		if not shot.is_empty():await capture(shot,int(first.get("uid",0)))
		if not first_hit.is_empty() or app.sim.winner!=-2:break
	verify(east_first_order>=4,"enemy paid decisions retain actual menu warmup",{"first_order":east_first_order})
	verify(not first.is_empty(),"normal AI pays for a new unit study")
	verify(first.has("completed"),"study completes through the real timer")
	verify(first.has("ordered"),"completed study receives an actual paid recruitment")
	verify(first.has("uid"),"first paid recruit completes production")
	verify(not first_hit.is_empty(),"first researched unit causes positive hostile damage")
	verify(not next_unit_before_order,"another unit study does not consume its first-order budget")
	if first.has("uid"):
		var study: Dictionary=app.db.tech(first.tech)
		verify(float(first.completed)>=float(first.research_started)+float(study.seconds)-.02,"study time is preserved")
		verify(float(first.ordered)>=float(first.completed),"order follows the completed unlock")
		verify(float(first.born)>=float(first.ordered)+float(app.db.balance.units[first.grant].production_seconds)-.02,"production time is preserved")
		verify(float(first_hit.get("time",0))>=float(first.born),"impact follows production and automatic march")
	for side in [0,1]:
		var difference: float=300+float(app.sim.stats[side].gold_delivered)-float(spent[side])-float(app.sim.players[side].gold)
		verify(absf(difference)<.001,"actual starting gold and mine deliveries fund every investment / "+str(side),{"spent":spent[side],"delivered":app.sim.stats[side].gold_delivered,"remaining":app.sim.players[side].gold,"difference":difference})
	verify(captures.size()==5,"opening, research, completion, production and impact are rendered")
	var inputs: Dictionary={}
	for name_value in ["main","battle_sim","tactical_ai","battle_view","battle_visibility","map_runtime","mobile_ui","theatre_fog","battle_command_rules"]:
		var path: String="res://scripts/"+name_value+(".gd" if FileAccess.file_exists("res://scripts/"+name_value+".gd") else ".gdc")
		inputs[path]=FileAccess.get_sha256(path)
	var report: Dictionary={"passed":checks.all(func(c):return c.passed),"version":ProjectSettings.get_setting("application/config/version"),
		"checks":checks,"inputs":inputs,"observer_sha256":FileAccess.get_sha256(get_script().resource_path),"config":app.sim.config,
		"mobile":app.mobile_ui,"time":app.sim.time,"first_paid_unit":first,"first_impact":first_hit,"investments":investments,
		"captures":captures,"unit_height_logical":app.view.unit_height(str(first.get("grant","unit.yin.axe"))),
		"unit_height_ui_units":app.view.unit_height(str(first.get("grant","unit.yin.axe")))*app.view.scale.y,
		"unit_height_pixels":app.view.unit_height(str(first.get("grant","unit.yin.axe")))*app.view.scale.y*root.get_stretch_transform().y.length(),
		"height_scope":"Authored draw rectangle, including viewport stretch; not the tight opaque-pixel silhouette of an individual frame.",
		"scope":"Actual App entry, selected legal Yin faction matchup recorded in config on map01.04, normal300 gold, six-unit research roster, counter style, difficulty1, enemy warmup4. West AI is an explicit autoplayer observer. Native Windows GPU with injected phone metrics; synchronized snapshots are not Android hardware, human play, FPS or full-balance evidence. No free unlocks, units, income, HP or actor placement."}
	FileAccess.open(folder+"/report.json",FileAccess.WRITE).store_string(JSON.stringify(report,"  "))
	print("PAID_FIELDING_RENDER ",report.passed," checks=",checks.size())
	for check in checks:
		if not check.passed:print(check)
	quit(0 if report.passed else 1)
