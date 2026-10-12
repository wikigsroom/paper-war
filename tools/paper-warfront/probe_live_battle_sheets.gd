extends SceneTree
# Real mining, paid research/production and native controls. Read-only client
# snapshots are fed by local authority; this is not a TCP or hardware test.
const App=preload("res://scripts/main.gd")
const Mirror=preload("res://scripts/client_battle.gd")
const MatchProjection=preload("res://scripts/match_projection.gd")
var checks: Array=[]
var shots: Array=[]
var folder: String
var helper

func _initialize():call_deferred("run")
func verify(ok: bool,name_value: String,details: Dictionary={}):
	checks.append({"passed":ok,"name":name_value,"details":details})
	if not ok:print("LIVE_SHEET_FAIL ",name_value," ",JSON.stringify(details))
func settle(frames: int=4):
	for i in range(frames):await process_frame
func advance(sim,seconds: float):
	for i in range(ceili(seconds*60)):sim.tick(1.0/60.0)
func control(parent: Node,prefix: String):
	return helper.named(parent,prefix)
func pointer(node: Control,point: Vector2,down: bool):
	if node.get_viewport()==root and not OS.get_cmdline_user_args().has("--mobile-ui"):
		var e=InputEventMouseButton.new();e.button_index=MOUSE_BUTTON_LEFT;e.pressed=down;e.position=point
		node.get_viewport().push_input(e,true);await process_frame
	else:await helper.finger(node,point,down)
func reveal(node: Control,button: Control) -> Vector2:
	var parent=button.get_parent()
	while parent!=null:
		if parent is ScrollContainer:parent.ensure_control_visible(button);break
		parent=parent.get_parent()
	await settle()
	var point: Vector2=button.get_global_rect().get_center()
	if node.get_viewport()==root and not OS.get_cmdline_user_args().has("--mobile-ui"):
		point=button.get_global_transform_with_canvas()*(button.size*.5)
	return point
func tap(node: Control,button: Control):
	var point: Vector2=await reveal(node,button)
	await pointer(node,point,true);await pointer(node,point,false)
	await settle()
func shot(app,name_value: String):
	await settle();await app.qa_snapshot(folder,name_value);shots.append(name_value+".png")
func queue_buttons(parent: Node) -> Array:
	return parent.find_children("*","Button",true,false).filter(func(b):return b.is_visible_in_tree() and (b.text.contains("退款") or b.text.contains("退还")))
func summary_label(parent: Node):
	for l in parent.find_children("*","Label",true,false):
		if l.text.contains("队") and l.text.contains("兵"):return l
	return null
func empty_queue(parent: Node) -> bool:
	for l in parent.find_children("*","Label",true,false):
		if l.is_visible_in_tree() and l.text.contains("当前没有正在生产"):return true
	return false

func run():
	var args=OS.get_cmdline_user_args();folder=args[args.find("--output")+1];DirAccess.make_dir_recursive_absolute(folder)
	helper=load(args[args.find("--touch-helper")+1])
	var app=App.new();root.add_child(app);await settle(8)
	app.mode="skirmish";app.start_battle({"title":"实时军令检查","map":"map.01.04","faction":"yin","enemy":"mo","starting_gold":300,"full_tech":false})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000;app.toast_left=0
	for i in range(3):verify(app.sim.recruit(0,"unit.yin.axe")=="","Single-player pays for queue order "+str(i))
	app.open_queue();await settle()
	var before_count: int=queue_buttons(app.overlay).size()
	advance(app.sim,2.2);app.update_hud();await settle(8)
	verify(app.sim.players[0].queue.size()==2,"Single-player production really completes")
	verify(before_count==3 and queue_buttons(app.overlay).size()==2,"Open single-player queue removes produced order without a click",{"rows":queue_buttons(app.overlay).size()})
	var b=queue_buttons(app.overlay)[0];var old_text: String=b.text
	advance(app.sim,.5);app.update_hud();await settle()
	verify(b.text!=old_text,"Single-player remaining production time updates on the same row")
	await shot(app,"01-live-single-queue")
	var held: Vector2=await reveal(app.ui,queue_buttons(app.overlay)[1])
	await pointer(app.ui,held,true)
	advance(app.sim,1);app.update_hud();await settle()
	var money: float=app.sim.players[0].gold
	verify(app.sim.players[0].queue.size()==1,"Single-player held queue press overlaps actual production")
	await pointer(app.ui,held,false);await settle()
	verify(app.sim.players[0].queue.size()==1 and is_equal_approx(app.sim.players[0].gold,money),"Releasing retired single-player row cannot refund its replacement")
	await tap(app.ui,queue_buttons(app.overlay)[0])
	verify(app.sim.players[0].queue.is_empty() and is_equal_approx(app.sim.players[0].gold-money,45),"Fresh native single-player tap refunds exactly one remaining order")
	verify(queue_buttons(app.overlay).is_empty() and empty_queue(app.overlay),"Single-player queue becomes visibly empty without reopening")
	app.close_overlay()
	app.open_orders();await settle()
	var summary=summary_label(app.overlay);var orders_sheet=app.overlay
	old_text=summary.text;advance(app.sim,2);app.update_hud();await settle()
	verify(app.overlay==orders_sheet and summary.text!=old_text,"Single-player orders update time and resources on the same paper")
	app.close_overlay()
	app.main_menu();app.start_battle({"title":"实时建筑选择检查","map":"map.01.04","faction":"yin","enemy":"mo","starting_gold":45,"full_tech":false})
	app.sim.ai_enabled=[false,false];app.accumulator=-100000;app.open_build(1);await settle()
	var blueprint=control(app.overlay,app.db.name_of("building.yin.mana"))
	verify(blueprint.disabled and blueprint.text.contains("还差"),"Single-player blueprint shows actual construction gold deficit")
	var overlap: bool=false
	var intersections: Array=[]
	var visible_buttons=app.overlay.find_children("*","Button",true,false).filter(func(x):return x.is_visible_in_tree())
	for i in range(visible_buttons.size()):
		for j in range(i+1,visible_buttons.size()):
			if visible_buttons[i].get_global_rect().intersects(visible_buttons[j].get_global_rect()):
				overlap=true;intersections.append({"a":visible_buttons[i].text,"a_rect":str(visible_buttons[i].get_global_rect()),"b":visible_buttons[j].text,"b_rect":str(visible_buttons[j].get_global_rect())})
	verify(not overlap,"Construction states keep native buttons separate",{"intersections":intersections})
	await shot(app,"05-single-build-deficit")
	money=app.sim.players[0].gold;await tap(app.ui,blueprint)
	verify(is_instance_valid(app.overlay) and app.modal=="build" and app.view.selected_building=="" and is_equal_approx(app.sim.players[0].gold,money),"Unaffordable blueprint native tap keeps paper without charge or selection")
	if not is_instance_valid(app.overlay):app.open_build(1);await settle()
	blueprint=control(app.overlay,app.db.name_of("building.yin.mana"));orders_sheet=app.overlay
	var waited_for_gold: float=0
	while app.sim.players[0].gold<55 and waited_for_gold<60:advance(app.sim,1);waited_for_gold+=1
	app.update_hud();await settle()
	verify(app.sim.stats[0].gold_delivered>0,"Blueprint affordability comes from actual miner unloading")
	verify(app.overlay==orders_sheet and not blueprint.disabled,"Mining reenables single-player blueprint on the same paper")
	await shot(app,"05-single-build-ready")
	money=app.sim.players[0].gold;await tap(app.ui,blueprint)
	verify(app.view.selected_building=="building.yin.mana" and not is_instance_valid(app.overlay) and is_equal_approx(app.sim.players[0].gold,money),"Native blueprint choice navigates without charging construction")
	app.cancel_selection();verify(app.view.selected_building=="" and is_equal_approx(app.sim.players[0].gold,money),"Cancelling blueprint remains free")
	# Own Yin side on each authority and client projection. Client cannot tick,
	# buy, or expose opponent money; only native button sends pay the authority.
	for side in [0,1]:
		app.main_menu();app.start_battle({"title":"实时共享军令","map":"map.01.04","faction":"yin","enemy":"yin","starting_gold":45,"enemy_starting_gold":45,"full_tech":false})
		var authority=app.sim;authority.ai_enabled=[false,false];app.accumulator=-100000
		var mirror=Mirror.new(app.db);mirror.start(authority.config);mirror.observer=side
		verify(mirror.apply_snapshot(MatchProjection.snapshot(authority,side)),"Client applies owned projection "+str(side))
		var duel=app.LocalDuel.new();duel.size=app.ui.size;duel.theme=app.theme;app.ui.add_child(duel)
		duel.initialize_network(app.db,mirror,side,func(kind,data):return authority.request(side,kind,data))
		duel.set_process(false);duel._process(0);await settle()
		var panel: Dictionary=duel.panels[side];duel.open_sheet(side,"research");await settle()
		duel.open_sheet(side,"build");await settle()
		var lamp_slot: int=1
		var lamp=control(panel.overlay,str(authority.slot_anchor(side,lamp_slot).label))
		verify(lamp!=null and lamp.disabled,"Shared visible lamp shows insufficient construction gold "+str(side))
		var first_gold: float=authority.players[side].gold
		await tap(panel.root,lamp)
		verify(is_instance_valid(panel.overlay) and authority.buildings.is_empty() and is_equal_approx(authority.players[side].gold,first_gold),"Unaffordable native construction keeps paper and treasury "+str(side))
		duel.open_sheet(side,"research");await settle()
		var hammer=control(panel.overlay,app.db.name_of("unit.yin.hammer"))
		verify(hammer!=null,"Shared hammer research row is present "+str(side))
		var gold: float=authority.players[side].gold
		verify(hammer.disabled,"Shared research shows insufficient gold "+str(side),{"gold":gold,"text":hammer.text})
		await tap(panel.root,hammer)
		verify(is_instance_valid(panel.overlay) and authority.players[side].research.is_empty() and is_equal_approx(authority.players[side].gold,gold),"Unaffordable native tap keeps sheet and treasury "+str(side))
		if not is_instance_valid(panel.overlay):duel.open_sheet(side,"research");await settle()
		hammer=control(panel.overlay,app.db.name_of("unit.yin.hammer"))
		var sheet=panel.overlay
		advance(authority,45);verify(authority.stats[side].gold_delivered>=24,"Gold really arrives from miners "+str(side))
		verify(mirror.apply_snapshot(MatchProjection.snapshot(authority,side)),"New own income snapshot accepted "+str(side));duel._process(0);await settle()
		verify(panel.overlay==sheet and not hammer.disabled,"Income reenables research without reopening "+str(side),{"gold":mirror.players[side].gold,"text":hammer.text})
		await shot(app,"02-shared-income-"+str(side))
		gold=authority.players[side].gold;await tap(panel.root,hammer)
		verify(not authority.players[side].research.is_empty() and is_equal_approx(gold-authority.players[side].gold,66),"Native shared research pays exactly 66 gold "+str(side))
		advance(authority,1.0/60.0)
		verify(mirror.apply_snapshot(MatchProjection.snapshot(authority,side)),"Research-start projection accepted "+str(side))
		duel.open_sheet(side,"research");duel._process(0);await settle()
		var ram=control(panel.overlay,app.db.name_of("unit.yin.cannon"));sheet=panel.overlay
		verify(ram!=null and ram.disabled,"Dependent research stays locked during actual parent research "+str(side))
		advance(authority,5.2);verify(authority.players[side].unlocked.has("unit.yin.hammer"),"Paid native study really unlocks hammer "+str(side))
		var waited: float=0
		while authority.players[side].gold<105 and waited<120:advance(authority,1);waited+=1
		verify(authority.players[side].gold>=105,"Dependent study is actually affordable from mining "+str(side))
		verify(mirror.apply_snapshot(MatchProjection.snapshot(authority,side)),"Study-done projection accepted "+str(side));duel._process(0);await settle()
		verify(panel.overlay==sheet and not ram.disabled,"Study completion reenables its dependent without reopening "+str(side))
		hammer=control(panel.overlay,app.db.name_of("unit.yin.hammer"))
		verify(hammer!=null and hammer.disabled and hammer.text.contains("已完成"),"Completed research is visibly marked and disabled "+str(side))
		duel.close_sheet(side);duel.open_sheet(side,"build");await settle()
		lamp=control(panel.overlay,str(authority.slot_anchor(side,lamp_slot).label))
		verify(lamp!=null and not lamp.disabled,"Owned visible affordable lamp site is buildable "+str(side))
		gold=authority.players[side].gold;await tap(panel.root,lamp)
		verify(is_equal_approx(gold-authority.players[side].gold,55),"Native shared lamp pays exactly 55 gold "+str(side))
		advance(authority,1.0/60.0);verify(mirror.apply_snapshot(MatchProjection.snapshot(authority,side)),"Building projection accepted "+str(side))
		duel.open_sheet(side,"build");duel._process(0);await settle()
		lamp=control(panel.overlay,str(authority.slot_anchor(side,lamp_slot).label))
		verify(lamp!=null and lamp.disabled,"Occupied shared facility cannot look buildable "+str(side))
		await shot(app,"03-shared-occupied-"+str(side))
		verify(not mirror.players[1-side].has("gold") and not mirror.players[1-side].has("queue"),"Shared readiness uses projection with private opponent data absent "+str(side))
		duel.close_sheet(side);duel.open_sheet(side,"orders");await settle()
		summary=summary_label(panel.overlay);old_text=summary.text;sheet=panel.overlay
		advance(authority,2);verify(mirror.apply_snapshot(MatchProjection.snapshot(authority,side)),"Orders time projection accepted "+str(side));duel._process(0);await settle()
		verify(panel.overlay==sheet and summary.text!=old_text,"Shared orders update owned resources and time without reopening "+str(side))
		waited=0
		while authority.players[side].gold<135 and waited<120:advance(authority,1);waited+=1
		for i in range(3):verify(authority.request(side,"recruit",{"id":"unit.yin.axe"}).ok,"Shared queue pays real order "+str(side)+"/"+str(i))
		advance(authority,1.0/60.0);verify(mirror.apply_snapshot(MatchProjection.snapshot(authority,side)),"Paid queue projection accepted "+str(side))
		duel.close_sheet(side);duel.open_sheet(side,"queue");duel._process(0);await settle()
		sheet=panel.overlay;held=await reveal(panel.root,queue_buttons(panel.overlay)[1]);await pointer(panel.root,held,true)
		advance(authority,1.9);verify(authority.players[side].queue.size()==2,"Shared held press overlaps actual paid production "+str(side))
		verify(mirror.apply_snapshot(MatchProjection.snapshot(authority,side)),"Produced queue projection accepted "+str(side));duel._process(0);await settle()
		gold=authority.players[side].gold;await pointer(panel.root,held,false);await settle()
		verify(authority.players[side].queue.size()==2 and is_equal_approx(authority.players[side].gold,gold),"Retired shared native row cannot refund identical replacement "+str(side))
		verify(is_instance_valid(panel.overlay) and panel.overlay==sheet and queue_buttons(panel.overlay).size()==2,"Shared production removes row on the same sheet "+str(side))
		if not is_instance_valid(panel.overlay):duel.open_sheet(side,"queue");duel._process(0);await settle()
		b=queue_buttons(panel.overlay)[0];old_text=b.text
		advance(authority,.4);mirror.apply_snapshot(MatchProjection.snapshot(authority,side));duel._process(0);await settle()
		verify(is_instance_valid(b) and b.text!=old_text,"Shared countdown updates without replacing row "+str(side))
		gold=authority.players[side].gold;await tap(panel.root,queue_buttons(panel.overlay)[1])
		verify(authority.players[side].queue.size()==1 and is_equal_approx(authority.players[side].gold-gold,45),"Fresh shared native row refunds exact 45 gold "+str(side))
		advance(authority,1.0/60.0);mirror.apply_snapshot(MatchProjection.snapshot(authority,side));duel._process(0);await settle()
		if not is_instance_valid(panel.overlay):duel.open_sheet(side,"queue");duel._process(0);await settle()
		await shot(app,"04-shared-live-queue-"+str(side))
		advance(authority,2);mirror.apply_snapshot(MatchProjection.snapshot(authority,side));duel._process(0);await settle()
		verify(panel.overlay==sheet and queue_buttons(panel.overlay).is_empty() and empty_queue(panel.overlay),"Shared last paid order leaves live empty state "+str(side))
		duel.build();await settle()
		verify(duel.sim==mirror and duel.panels[side].overlay==null and mirror.players[side].queue==authority.players[side].queue,"Shared viewport rebuild preserves authority queue and closes old paper "+str(side))
		duel.hide();duel.queue_free();await settle()
	var inputs: Dictionary={}
	for name in ["main","mobile_ui","local_duel","battle_sim","client_battle","match_projection","recruitment_readiness","battle_command_rules","ui_battle_sheets"]:
		var path: String="res://scripts/"+name+".gd";var actual: String=path if FileAccess.file_exists(path) else path+"c"
		if FileAccess.file_exists(actual):inputs[actual]=FileAccess.get_sha256(actual)
	var passed: bool=checks.all(func(c):return c.passed)
	var f=FileAccess.open(folder+"/report.json",FileAccess.WRITE);f.store_string(JSON.stringify({"passed":passed,"version":ProjectSettings.get_setting("application/config/version"),"checks":checks,"shots":shots,"inputs":inputs,"scope":"Native Windows UI, actual mining, paid research and production, both own-side client projections with local authority sender. Not TCP/human play or Android hardware."},"\t"));f.close()
	print("LIVE_BATTLE_SHEETS ",checks.size()," checks; passed=",passed);app.queue_free();await process_frame;quit(0 if passed else 1)
