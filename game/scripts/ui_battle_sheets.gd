extends RefCounted
const Rules=preload("res://scripts/battle_command_rules.gd")
const Readiness=preload("res://scripts/recruitment_readiness.gd")
# Updates existing native controls. Queue callbacks keep an immutable revision;
# only structural changes retire rows, so countdowns never reset touch or focus.
var research_buttons: Dictionary={}
var build_buttons: Array=[]
var summary: Label
var summary_side: bool=false
var study: Label
var queue_empty: Control
var queue_factory: Callable
var queue_rows: Array=[]
var queue_revision: int=-1

static func caption(button: Button,value: String,disabled: bool):
	if button.text!=value:button.text=value
	if button.disabled!=disabled:button.disabled=disabled
	button.tooltip_text=value.replace("\n"," · ")
	button.accessibility_name=button.tooltip_text

static func research_caption(sim,side: int,id: String) -> String:
	var p: Dictionary=sim.players[side];var node: Dictionary=sim.db.tech(id)
	var suffix: String="%d 金 · %.0f 秒"%[node.gold,node.seconds]
	if p.studied.has(id):suffix="已完成"
	elif not p.research.is_empty() and p.research.id==id:suffix="研究中 · %.1f 秒"%p.research.left
	else:
		var missing: Array=[]
		for req in node.requires:
			if not p.studied.has(req):missing.append(sim.db.name_of(sim.db.tech(req).grant))
		if not missing.is_empty():suffix="前置："+"、".join(missing)
		elif not p.research.is_empty():suffix+=" · 等待当前研究"
		elif p.gold<float(node.gold):suffix+=" · 还差 %d 金"%ceili(float(node.gold)-p.gold)
	return sim.db.name_of(node.grant)+"\n"+suffix

static func update_research(sim,side: int,buttons: Dictionary,halted: bool=false):
	for id in buttons:
		var b=buttons[id]
		if is_instance_valid(b):caption(b,research_caption(sim,side,id),halted or sim.winner!=-2 or not Rules.research_error(sim,side,id).is_empty())

func bind_build(button: Button,id: String,slot: int,selection: bool=false,base_caption: String=""):
	build_buttons.append({"button":button,"id":id,"slot":slot,"selection":selection,"caption":base_caption})

func bind_queue(factory: Callable,empty: Control):
	queue_factory=factory;queue_empty=empty;queue_revision=-1

func refresh_queue(sim,side: int,halted: bool):
	if not queue_factory.is_valid():return
	var p: Dictionary=sim.players[side]
	if queue_revision!=int(p.queue_revision):
		var focus_index: int=-1
		for row in queue_rows:
			var b=row.button
			if not is_instance_valid(b):continue
			if b.has_focus():focus_index=int(row.index)
			b.disabled=true;b.set_pressed_no_signal(false);b.hide();b.queue_free()
		queue_rows.clear();queue_revision=int(p.queue_revision)
		for i in range(p.queue.size()):
			var id: String=p.queue[i]
			queue_rows.append({"index":i,"id":id,"button":queue_factory.call(i,id,queue_revision)})
		if focus_index>=0 and not queue_rows.is_empty():queue_rows[mini(focus_index,queue_rows.size()-1)].button.call_deferred("grab_focus")
	if is_instance_valid(queue_empty):queue_empty.visible=p.queue.is_empty()
	for row in queue_rows:
		var b=row.button
		if is_instance_valid(b):caption(b,"%d · %s\n%s · 退还 %d 金"%[int(row.index)+1,sim.db.name_of(row.id),Readiness.queue_notice(sim,side,int(row.index)),sim.db.balance.units[row.id].gold],halted or sim.winner!=-2)

func refresh(sim,side: int,halted: bool=false):
	if sim==null:return
	var p: Dictionary=sim.players[side]
	update_research(sim,side,research_buttons,halted)
	for entry in build_buttons:
		var b=entry.button
		if not is_instance_valid(b):continue
		var error: String=Rules.build_selection_error(sim,side,entry.id,entry.slot) if entry.selection else Rules.build_error(sim,side,entry.id,entry.slot)
		var text: String=entry.caption
		if text.is_empty():text=str(sim.slot_anchor(side,entry.slot).get("label","阵地"))+" · "+sim.db.name_of(entry.id)+" · %d 金"%sim.db.balance.buildings[entry.id].gold
		if not error.is_empty():
			if error=="建造金币不足":error="还差 %d 金"%ceili(float(sim.db.balance.buildings[entry.id].gold)-p.gold)
			text+="\n"+error
			if error=="该建筑位已占用":
				for actor in sim.buildings:
					if actor.side==side and actor.slot==entry.slot and actor.hp>0 and actor.state=="constructing":text+=" · 施工 %.1f 秒"%actor.construction;break
		caption(b,text,halted or sim.winner!=-2 or not error.is_empty())
	if is_instance_valid(summary):
		var first: String="玩家%d · 金%d · 法%d · 城%d"%[side+1,p.gold,p.mana,sim.bases[side].hp] if summary_side else "金%d · 法%d · 我城%d · 敌城%s"%[p.gold,p.mana,sim.bases[side].hp,str(int(sim.bases[1-side].hp)) if sim.visible_to(side,sim.bases[1-side]) else "未知"]
		summary.text=first+"\n兵%d · 工%d · 队%d · %02d:%02d"%[sim.population(side,false,false),sim.population(side,true,false),p.queue.size(),int(sim.time)/60,int(sim.time)%60]
	if is_instance_valid(study):
		study.visible=not p.research.is_empty()
		if study.visible:study.text="研究 "+sim.db.name_of(sim.db.tech(p.research.id).grant)+" · %.1f 秒"%p.research.left
	refresh_queue(sim,side,halted)
